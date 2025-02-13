from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

import duckdb

from leettools.common import exceptions
from leettools.common.logging import logger
from leettools.common.singleton_meta import SingletonMeta
from leettools.settings import SystemSettings


class SingletonMetaDuckDB(SingletonMeta):
    _lock: Lock = Lock()


class DuckDBClient(metaclass=SingletonMetaDuckDB):
    def __init__(self, settings: SystemSettings):
        if not hasattr(
            self, "initialized"
        ):  # This ensures __init__ is only called once
            self.initialized = True
            self.db_path = Path(settings.DUCKDB_PATH) / settings.DUCKDB_FILE
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self.created_tables: Dict[str, str] = {}
            self._lock = Lock()
            self.table_locks = {}

            logger().info(f"Connecting to DuckDB at {self.db_path}")

            try:
                self.conn = duckdb.connect(str(self.db_path))
            except Exception as e:
                logger().error(f"Error connecting to DuckDB: {e}")
                raise exceptions.UnexpectedOperationFailureException(
                    operation_desc="Error connecting to DuckDB", error=str(e)
                )

    def _get_table_lock(self, table_name: str) -> Lock:
        """Retrieve or create a lock for the specified table, ensuring thread safety."""
        with self._lock:
            if table_name not in self.table_locks:
                self.table_locks[table_name] = Lock()
            return self.table_locks[table_name]

    def batch_insert_into_table(
        self, table_name: str, column_list: List[str], values: List[List[Any]]
    ) -> None:
        """
        Insert multiple rows into a table.

        Args:
        - table_name: The table name.
        - column_list: The list of column names.
        - values: The list of values as dictionaries to insert.

        Returns:
        - None
        """
        if not values:
            return

        if not column_list:
            raise exceptions.UnexpectedCaseException(
                "column_list cannot be empty when inserting values"
            )
        with self.conn.cursor() as cursor:
            # Create a string of placeholders for each row
            placeholders = ",".join(
                ["(" + ",".join(["?"] * len(column_list)) + ")"] * len(values)
            )
            # Flatten the list of values for the executemany function
            flattened_values: List[Any] = []
            for sublist in values:
                for item in sublist:
                    flattened_values.append(item)
            insert_sql = f"""
                INSERT INTO {table_name} ({",".join(column_list)})
                VALUES {placeholders}
            """
            logger().noop(
                f"SQL Statement batch_insert_into_table: {insert_sql}", noop_lvl=2
            )
            with self._get_table_lock(table_name):
                cursor.execute(insert_sql, flattened_values)

    def get_table(
        self,
        schema_name: str,
        table_name: str,
    ) -> str:
        if schema_name is None:
            raise ValueError("schema_name cannot be None")
        if table_name is None:
            raise ValueError("table_name cannot be None")
        table_key = f"{schema_name}.{table_name}"
        with self._get_table_lock(table_name):
            table_name_in_db = self.created_tables.get(table_key)
            if table_name_in_db is not None:
                return table_name_in_db
            return None

    def create_table_if_not_exists(
        self,
        schema_name: str,
        table_name: str,
        columns: Dict[str, str],
        create_sequence_sql: str = None,
    ) -> str:
        """
        Create a table if it does not exist.

        Args:
        - schema_name: The schema name.
        - table_name: The table name.
        - columns: The columns of the table as a name-type dictionary.
        - create_sequence_sql: The SQL to create a sequence after the table is created.

        Returns:
        - The table name.
        """
        err_msgs = []
        if schema_name is None:
            err_msgs.append("schema_name cannot be None")
        if table_name is None:
            err_msgs.append("table_name cannot be None")
        if err_msgs:
            raise exceptions.ParametersValidationException(err_msgs)

        table_key = f"{schema_name}.{table_name}"

        # Since multiple threads will be creating tables at the same time,
        # we need to gurantee that only one thread will be creating the table.
        with self._get_table_lock(table_name):
            table_name_in_db = self.created_tables.get(table_key)
            if table_name_in_db is not None:
                return table_name_in_db

            new_schema_name = schema_name.lower().replace("-", "_")
            new_table_name = table_name.lower().replace("-", "_")
            if new_table_name[0].isdigit():
                new_table_name = "t" + new_table_name

            with self.conn.cursor() as cursor:
                result = cursor.execute(
                    f"""
                    SELECT name 
                    FROM sqlite_master 
                    WHERE sql like '%{new_schema_name}.{new_table_name}%'
                    """,
                ).fetchone()

                if result is None:
                    if create_sequence_sql is not None:
                        cursor.execute(create_sequence_sql)

                    create_table_sql = self._get_create_table_sql(
                        new_schema_name, new_table_name, columns
                    )
                    logger().noop(
                        f"SQL Statement create_table_sql: {create_table_sql}",
                        noop_lvl=2,
                    )
                    cursor.execute(create_table_sql)
                self.created_tables[table_key] = f"{new_schema_name}.{new_table_name}"
                return self.created_tables[table_key]

    def delete_from_table(
        self, table_name: str, where_clause: str = None, value_list: List[Any] = None
    ) -> None:
        with self.conn.cursor() as cursor:
            delete_sql = f"DELETE FROM {table_name}"
            if where_clause is not None:
                delete_sql += f" {where_clause}"
            logger().noop(f"SQL Statement delete_sql: {delete_sql}", noop_lvl=2)
            with self._get_table_lock(table_name):
                if value_list is not None:
                    cursor.execute(delete_sql, value_list)
                else:
                    cursor.execute(delete_sql)

    def _get_create_table_sql(
        self, schema_name: str, table_name: str, columns: Dict[str, str]
    ) -> str:
        create_table_sql = f"CREATE SCHEMA IF NOT EXISTS {schema_name};"
        columns = [f"{name} {type_}" for name, type_ in columns.items()]
        return f"""
            {create_table_sql}
            CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} ({','.join(columns)})
        """

    def execute_sql(self, sql: str, value_list: List[Any] = None) -> None:
        with self.conn.cursor() as cursor:
            if value_list is not None:
                cursor.execute(sql, value_list)
            else:
                cursor.execute(sql)

    def execute_and_fetch_all(
        self, sql: str, value_list: List[Any] = None
    ) -> List[Dict[str, Any]]:
        with self.conn.cursor() as cursor:
            if value_list is not None:
                results = cursor.execute(sql, value_list).fetchall()
            else:
                results = cursor.execute(sql).fetchall()
            column_names = [desc[0] for desc in cursor.description]
            value = [dict(zip(column_names, row)) for row in results]
            return value

    def fetch_all_from_table(
        self,
        table_name: str,
        column_list: List[str] = None,
        value_list: List[Any] = None,
        where_clause: str = None,
    ) -> List[Dict[str, Any]]:
        if column_list is None:
            column_str = "*"
        else:
            column_str = ",".join(column_list)

        if where_clause is None:
            where_clause = ""

        with self.conn.cursor() as cursor:
            select_sql = f"""
                SELECT {column_str} FROM {table_name} 
                {where_clause}
                """
            logger().noop(f"SQL Statement select_sql: {select_sql}", noop_lvl=2)
            with self._get_table_lock(table_name):
                if value_list is not None:
                    results = cursor.execute(select_sql, value_list).fetchall()
                else:
                    results = cursor.execute(select_sql).fetchall()

            column_names = [desc[0] for desc in cursor.description]
            value = [dict(zip(column_names, row)) for row in results]
            return value

    def fetch_one_from_table(
        self,
        table_name: str,
        column_list: List[str] = None,
        value_list: List[Any] = None,
        where_clause: str = None,
    ) -> Optional[Dict[str, Any]]:

        if column_list is None:
            column_str = "*"
        else:
            column_str = ",".join(column_list)

        if where_clause is None:
            where_clause = ""

        with self.conn.cursor() as cursor:
            select_sql = f"""
                SELECT {column_str} FROM {table_name} 
                {where_clause}
                """
            with self._get_table_lock(table_name):
                if value_list is not None:
                    result = cursor.execute(select_sql, value_list).fetchone()
                else:
                    result = cursor.execute(select_sql).fetchone()

            column_names = [desc[0] for desc in cursor.description]
            value = dict(zip(column_names, result)) if result else None
            return value

    def fetch_sequence_current_value(self, sequence_name: str) -> int:
        with self.conn.cursor() as cursor:
            return cursor.execute(
                f"SELECT currval('{sequence_name}') as currval"
            ).fetchone()[0]

    def insert_into_table(
        self, table_name: str, column_list: List[str], value_list: List[Any]
    ) -> None:
        with self.conn.cursor() as cursor:
            with self._get_table_lock(table_name):
                cursor.execute(
                    f"""
                INSERT INTO {table_name} ({",".join(column_list)})
                VALUES ({",".join(["?"] * len(column_list))})
                """,
                    value_list,
                )

    def update_table(
        self,
        table_name: str,
        column_list: List[str],
        value_list: List[Any],
        where_clause: str = None,
    ) -> None:
        with self.conn.cursor() as cursor:
            set_clause = ",".join([f"{k} = ?" for k in column_list])
            update_sql = f"UPDATE {table_name} SET {set_clause} "
            if where_clause is not None:
                update_sql += f"{where_clause}"
            logger().noop(f"SQL Statement update_sql: {update_sql}", noop_lvl=2)
            with self._get_table_lock(table_name):
                cursor.execute(update_sql, value_list)
