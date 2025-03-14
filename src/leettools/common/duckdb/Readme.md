| **Alias** | **Canonical Type** | **Notes** |
| --------------- | ------------------------ | --------------- |
| **TEXT** | VARCHAR | Often seen in SQL engines as `TEXT`. Internally mapped to a variable-length string. |
| **CHAR** ,**CHARACTER** | VARCHAR | If you specify `CHAR(n)`, DuckDB still treats it internally as a `VARCHAR`. |
| **VARCHAR** | VARCHAR | Already canonical. |
| **STRING** | VARCHAR | Recognized alias, same as `TEXT`/`CHAR`. |
| **BOOLEAN** | BOOLEAN | Same name internally. |
| **TINYINT** | INTEGER (INT8) | 8-bit integer range. |
| **SMALLINT** | INTEGER (INT16) | 16-bit integer range. |
| **INT2** | INTEGER (INT16) | Synonym for `SMALLINT`. |
| **INT** ,**INTEGER** | INTEGER (INT32) | 32-bit integer range. |
| **INT4** | INTEGER (INT32) | Another name for `INTEGER`. |
| **BIGINT** | BIGINT (INT64) | 64-bit integer range. |
| **INT8** | BIGINT (INT64) | Synonym for `BIGINT`. |
| **FLOAT** ,**REAL** | REAL (FLOAT4) | Single-precision 32-bit floating-point. |
| **DOUBLE** ,**DOUBLE PRECISION** | DOUBLE (FLOAT8) | Double-precision 64-bit floating-point. |
| **DECIMAL(p,s)** ,**NUMERIC(p,s)** | DECIMAL(p,s) | Alias for the standard decimal type (precision/scale). |
| **BLOB** | BLOB | Raw byte storage type. |
| **DATE** | DATE | Same name internally. |
| **TIME** | TIME | Same name internally. |
| **TIMESTAMP** ,**DATETIME** | TIMESTAMP | Timestamp without time zone. |
| **TIMESTAMPTZ** | TIMESTAMP WITH TIME ZONE | DuckDB currently treats time zones a bit differently; still recognized. |
| **INTERVAL** | INTERVAL | Same name internally (interval of days, months, microseconds, etc.). |
| **UUID** | UUID | 128-bit UUID. |
