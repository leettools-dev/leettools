from pathlib import Path
from threading import Lock
from typing import Any, Dict, List, Optional

import duckdb

from leettools.common.exceptions import UnexpectedOperationFailureException
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

            try:
                self.conn = duckdb.connect(str(self.db_path))
            except Exception as e:
                logger().error(f"Error connecting to DuckDB: {e}")
                raise UnexpectedOperationFailureException(
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
        try:
            with self.conn.cursor() as cursor:
                # Create a string of placeholders for each row
                placeholders = ",".join(
                    ["(" + ",".join(["?"] * len(column_list)) + ")"] * len(values)
                )
                # Flatten the list of values for the executemany function
                flattened_values = [item for sublist in values for item in sublist]
                insert_sql = f"""
                    INSERT INTO {table_name} ({",".join(column_list)})
                    VALUES {placeholders}
                """
                with self._get_table_lock(table_name):
                    cursor.execute(insert_sql, flattened_values)
        except Exception as e:
            raise UnexpectedOperationFailureException(
                operation_desc=f"Error inserting into table {table_name}", error=str(e)
            )

    def create_table_if_not_exists(
        self,
        schema_name: str,
        table_name: str,
        columns: Dict[str, str],
        create_sequence_sql: str = None,
    ) -> str:
        try:
            if schema_name is None:
                raise ValueError("schema_name cannot be None")
            if table_name is None:
                raise ValueError("table_name cannot be None")

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
                    if create_sequence_sql is not None:
                        cursor.execute(create_sequence_sql)

                    result = cursor.execute(
                        f"""
                        SELECT name 
                        FROM sqlite_master 
                        WHERE sql like '%{new_schema_name}.{new_table_name}%'
                        """,
                    ).fetchone()

                    if result is None:
                        create_table_sql = self._get_create_table_sql(
                            new_schema_name, new_table_name, columns
                        )
                        cursor.execute(create_table_sql)
                    self.created_tables[table_key] = (
                        f"{new_schema_name}.{new_table_name}"
                    )
                    return self.created_tables[table_key]
        except Exception as e:
            raise UnexpectedOperationFailureException(
                operation_desc=f"Error initializing table {table_name}", error=str(e)
            )

    def delete_from_table(
        self, table_name: str, where_clause: str = None, value_list: List[Any] = None
    ) -> None:
        try:
            with self.conn.cursor() as cursor:
                delete_sql = f"DELETE FROM {table_name}"
                if where_clause is not None:
                    delete_sql += f" {where_clause}"
                with self._get_table_lock(table_name):
                    if value_list is not None:
                        cursor.execute(delete_sql, value_list)
                    else:
                        cursor.execute(delete_sql)
        except Exception as e:
            raise UnexpectedOperationFailureException(
                operation_desc=f"Error deleting from table {table_name}", error=str(e)
            )

    def _get_create_table_sql(
        self, schema_name: str, table_name: str, columns: Dict[str, str]
    ) -> str:
        create_table_sql = f"CREATE SCHEMA IF NOT EXISTS {schema_name};"
        columns = [f"{name} {type_}" for name, type_ in columns.items()]
        return f"""
            {create_table_sql}
            CREATE TABLE IF NOT EXISTS {schema_name}.{table_name} ({','.join(columns)})
        """

    def fetch_all_from_table(
        self,
        table_name: str,
        column_list: List[str] = None,
        value_list: List[Any] = None,
        where_clause: str = None,
    ) -> List[Dict[str, Any]]:
        try:
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
                logger().debug(f"select_sql: {select_sql}")
                with self._get_table_lock(table_name):
                    if value_list is not None:
                        results = cursor.execute(select_sql, value_list).fetchall()
                    else:
                        results = cursor.execute(select_sql).fetchall()

                column_names = [desc[0] for desc in cursor.description]
                return [dict(zip(column_names, row)) for row in results]
        except Exception as e:
            raise UnexpectedOperationFailureException(
                operation_desc=f"Error fetching all from table {table_name}",
                error=str(e),
            )

    def fetch_one_from_table(
        self,
        table_name: str,
        column_list: List[str] = None,
        value_list: List[Any] = None,
        where_clause: str = None,
    ) -> Optional[Dict[str, Any]]:
        try:
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
                return dict(zip(column_names, result)) if result else None
        except Exception as e:
            raise UnexpectedOperationFailureException(
                operation_desc=f"Error fetching all from table {table_name}",
                error=str(e),
            )

    def fetch_sequence_current_value(self, sequence_name: str) -> int:
        with self.conn.cursor() as cursor:
            return cursor.execute(
                f"SELECT currval('{sequence_name}') as currval"
            ).fetchone()[0]

    def insert_into_table(
        self, table_name: str, column_list: List[str], value_list: List[Any]
    ) -> None:
        try:
            with self.conn.cursor() as cursor:
                with self._get_table_lock(table_name):
                    cursor.execute(
                        f"""
                    INSERT INTO {table_name} ({",".join(column_list)})
                    VALUES ({",".join(["?"] * len(column_list))})
                    """,
                        value_list,
                    )
        except Exception as e:
            raise UnexpectedOperationFailureException(
                operation_desc=f"Error inserting into table {table_name}", error=str(e)
            )

    def update_table(
        self,
        table_name: str,
        column_list: List[str],
        value_list: List[Any],
        where_clause: str = None,
    ) -> None:
        try:
            with self.conn.cursor() as cursor:
                set_clause = ",".join([f"{k} = ?" for k in column_list])
                update_sql = f"UPDATE {table_name} SET {set_clause}"
                if where_clause is not None:
                    update_sql += f"{where_clause}"
                logger().debug(f"update_sql: {update_sql}")
                with self._get_table_lock(table_name):
                    cursor.execute(update_sql, value_list)
        except Exception as e:
            raise UnexpectedOperationFailureException(
                operation_desc=f"Error updating table {table_name}", error=str(e)
            )
