#!/usr/bin/env python3

import cx_Oracle
import pyodbc
import json
import logging
import platform
import os
import time
from typing import List, Dict, Any
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OracleConnection:
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.connection = None
        self.checkpoint_dir = Path('/tmp/oracle_checkpoints')
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._setup_checkpoint_file()

    def _setup_checkpoint_file(self):
        """Setup checkpoint file for tracking progress."""
        schema = self.config.get('schema', '').upper()
        db = self.config.get('database', '')
        self.checkpoint_file = self.checkpoint_dir / f"{schema}_{db}_checkpoint.json"
        
        if not self.checkpoint_file.exists():
            self._save_checkpoint({
                'last_offset': 0,
                'processed_views': [],
                'failed_views': [],
                'in_progress': False
            })

    def _save_checkpoint(self, data: Dict):
        """Save checkpoint data to file."""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(data, f)

    def _load_checkpoint(self) -> Dict:
        """Load checkpoint data from file."""
        try:
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {
                'last_offset': 0,
                'processed_views': [],
                'failed_views': [],
                'in_progress': False
            }

    def _check_oracle_client(self) -> None:
        """Check Oracle Client configuration and provide detailed feedback."""
        system = platform.system().lower()
        try:
            cx_Oracle.clientversion()  # triggers an exception if libraries are not found
        except Exception as e:
            error_msg = str(e)
            if system == 'windows':
                client_paths = [
                    r'C:\Oracle\instantclient_19_19',
                    r'C:\Oracle\instantclient_21_10',
                    os.environ.get('ORACLE_HOME', '')
                ]
                paths_str = '\n   - '.join(filter(None, client_paths))
                raise Exception(
                    "Oracle Instant Client not found. For Windows:\n"
                    "1. Download Oracle Instant Client from:\n"
                    "   https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html\n"
                    "2. Extract to a directory (e.g., C:\\Oracle\\instantclient_19_19)\n"
                    "3. Add the directory to the PATH environment variable\n"
                    "\nChecked paths:\n   - " + paths_str
                )
            else:
                raise Exception(
                    "Oracle Instant Client not found. For Linux:\n"
                    "1. Install using package manager:\n"
                    "   sudo apt-get install oracle-instantclient\n"
                    "   or\n"
                    "   sudo yum install oracle-instantclient\n"
                    "2. Set required environment variables:\n"
                    "   export LD_LIBRARY_PATH=/usr/lib/oracle/<version>/client64/lib:$LD_LIBRARY_PATH"
                )

    def connect(self) -> None:
        """Establish the Oracle database connection."""
        try:
            self._check_oracle_client()
            schema = self.config.get('schema', '').upper() if 'schema' in self.config else None
            conn_str = self.get_connection_string()

            logger.info(f"Attempting Oracle connection to {self.config['server']}")
            logger.info(f"Database (service): {self.config['database']}")
            logger.info(f"Username: {self.config['username']}")

            # Connect
            self.connection = cx_Oracle.connect(
                conn_str,
                encoding="UTF-8",
                nencoding="UTF-8"
            )

            cursor = self.connection.cursor()
            cursor.arraysize = 1000

            # Set date/time formats
            cursor.execute("""
                ALTER SESSION SET 
                NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS'
                NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF'
            """)

            # Verify connection
            cursor.execute("SELECT * FROM v$version")
            version = cursor.fetchone()[0]
            logger.info(f"Successfully connected to Oracle. Version: {version}")

            # Check current schema
            cursor.execute("SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM DUAL")
            current_schema = cursor.fetchone()[0]
            logger.info(f"Currently in schema: {current_schema}")

            # Switch schema if provided
            if schema:
                self._validate_and_switch_schema(cursor, schema)

        except cx_Oracle.DatabaseError as e:
            error_msg = str(e)
            if "DPI-1047" in error_msg:
                raise Exception(
                    "Oracle Client libraries are not properly configured. Please ensure:\n"
                    "1. Oracle Instant Client is installed\n"
                    "2. The correct version (32/64 bit) matches your Python\n"
                    "3. Environment variables are set correctly"
                )
            elif "ORA-12541" in error_msg:
                raise Exception(f"Could not connect to Oracle server at {self.config['server']}. "
                                "Please verify the server address and port.")
            elif "ORA-01017" in error_msg:
                raise Exception("Invalid Oracle credentials. Please check username and password.")
            elif "ORA-12514" in error_msg:
                raise Exception(f"Database service '{self.config['database']}' not found. "
                                "Please verify the database/service name.")
            else:
                raise Exception(f"Oracle connection error: {error_msg}")

        except Exception as e:
            logger.error(f"Unexpected error connecting to Oracle: {str(e)}", exc_info=True)
            raise Exception(f"Failed to connect to Oracle: {str(e)}")

    def _validate_and_switch_schema(self, cursor, schema: str):
        """Validate the schema existence and switch to it."""
        try:
            # Only check if the user (schema) exists in ALL_USERS
            cursor.execute("""
                SELECT username
                FROM all_users
                WHERE username = :schema
            """, schema=schema)
            user_info = cursor.fetchone()

            if not user_info:
                raise Exception(f"Schema {schema} does not exist")

            logger.info(f"Found schema {schema}.")
            
            # Switch schema
            cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {schema}")
            logger.info(f"Successfully switched to schema: {schema}")

        except cx_Oracle.DatabaseError as e:
            error_msg = str(e)
            logger.error(f"Failed to switch to schema {schema}: {error_msg}")
            raise Exception(f"Failed to access schema {schema}: {error_msg}")

    def disconnect(self) -> None:
        """Close the Oracle connection."""
        if self.connection:
            try:
                self.connection.close()
                logger.info("Oracle connection closed successfully.")
            except Exception as e:
                logger.error(f"Error closing Oracle connection: {str(e)}")
                raise Exception(f"Failed to close connection: {str(e)}")

    def get_connection_string(self) -> str:
        """Generate Oracle connection string."""
        try:
            if '/' in self.config['server']:
                # If server includes service name or uses Easy Connect string
                return f"{self.config['username']}/{self.config['password']}@{self.config['server']}"
            else:
                # Typical host:port/service or host:port/SID scenario
                return f"{self.config['username']}/{self.config['password']}@" \
                       f"{self.config['server']}/{self.config['database']}"
        except KeyError as e:
            raise Exception(f"Missing required configuration parameter: {str(e)}")

    def get_tables(self, batch_size: int = 1000) -> List[str]:
        """
        Return list of all VIEW names in the connected schema.
        Uses a checkpoint file to resume if connection is lost mid-way.
        """
        checkpoint = self._load_checkpoint()
        
        # If a previous run was "in_progress", resume
        if checkpoint['in_progress']:
            logger.info("Resuming previous extraction from checkpoint...")
            offset = checkpoint['last_offset']
            views = checkpoint['processed_views']
        else:
            offset = 0
            views = []
            # Mark as in progress
            checkpoint['in_progress'] = True
            checkpoint['last_offset'] = offset
            checkpoint['processed_views'] = views
            self._save_checkpoint(checkpoint)

        cursor = self.connection.cursor()
        cursor.arraysize = batch_size

        # Determine schema in use
        schema = self.config.get('schema', '').upper() if 'schema' in self.config else None
        if not schema:
            cursor.execute("SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM DUAL")
            schema = cursor.fetchone()[0]

        logger.info(f"Starting view extraction for schema: {schema}")

        while True:
            try:
                query = """
                    SELECT object_name
                    FROM (
                        SELECT a.*, ROWNUM rnum
                        FROM (
                            SELECT object_name
                            FROM all_objects
                            WHERE owner = :schema
                              AND object_type = 'VIEW'
                              AND object_name NOT LIKE 'BIN$%'
                            ORDER BY object_name
                        ) a
                        WHERE ROWNUM <= :end_row
                    )
                    WHERE rnum > :start_row
                """

                cursor.execute(query, {
                    'schema': schema,
                    'start_row': offset,
                    'end_row': offset + batch_size
                })
                batch = cursor.fetchall()

                if not batch:
                    # no more data
                    break

                new_views = [row[0] for row in batch]
                views.extend(new_views)
                offset += len(batch)

                # Save checkpoint after each batch
                checkpoint['last_offset'] = offset
                checkpoint['processed_views'] = views
                checkpoint['in_progress'] = True
                self._save_checkpoint(checkpoint)

                logger.info(f"Processed {len(views)} views so far...")

                if len(batch) < batch_size:
                    # we've reached the end
                    break

                # small delay
                time.sleep(0.1)

            except cx_Oracle.DatabaseError as e:
                # Handle lost connection
                if "ORA-03113" in str(e) or "ORA-03114" in str(e):
                    logger.warning("Connection lost. Reconnecting and retrying...")
                    self.connect()
                    cursor = self.connection.cursor()
                    cursor.arraysize = batch_size
                    continue
                else:
                    raise

        # Mark the checkpoint as finished
        checkpoint['in_progress'] = False
        self._save_checkpoint(checkpoint)

        logger.info(f"Completed view extraction. Total views: {len(views)}")
        return views

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Fetch column definitions (schema) for a given Oracle table or view.
        """
        try:
            cursor = self.connection.cursor()
            schema = self.config.get('schema', '').upper() if 'schema' in self.config else None
            if not schema:
                cursor.execute("SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM DUAL")
                schema = cursor.fetchone()[0]

            # Check if table/view actually exists
            cursor.execute("""
                SELECT object_type
                FROM all_objects
                WHERE owner = :schema
                  AND object_name = :object_name
                  AND object_type IN ('TABLE', 'VIEW')
            """, schema=schema, object_name=table_name.upper())
            result = cursor.fetchone()

            if not result:
                raise Exception(f"Table or view '{table_name}' not found in schema {schema}.")

            # Enhanced query to detect PKs and FKs
            cursor.execute("""
                WITH pk_columns AS (
                    SELECT column_name
                    FROM all_constraints ac
                    JOIN all_cons_columns acc ON ac.constraint_name = acc.constraint_name
                        AND ac.owner = acc.owner
                    WHERE ac.constraint_type = 'P'
                        AND ac.table_name = :table_name
                        AND ac.owner = :schema
                ),
                fk_columns AS (
                    SELECT 
                        acc.column_name,
                        ac.r_owner as referenced_owner,
                        ac_pk.table_name as referenced_table,
                        acc_pk.column_name as referenced_column
                    FROM all_constraints ac
                    JOIN all_cons_columns acc ON ac.constraint_name = acc.constraint_name
                    JOIN all_constraints ac_pk ON ac.r_constraint_name = ac_pk.constraint_name
                    JOIN all_cons_columns acc_pk ON ac_pk.constraint_name = acc_pk.constraint_name
                    WHERE ac.constraint_type = 'R'
                        AND ac.table_name = :table_name
                        AND ac.owner = :schema
                )
                SELECT 
                    c.column_name,
                    c.data_type,
                    c.nullable,
                    CASE WHEN pk.column_name IS NOT NULL THEN 'Yes' ELSE 'No' END as is_primary_key,
                    CASE WHEN fk.column_name IS NOT NULL THEN 'Yes' ELSE 'No' END as is_foreign_key,
                    c.data_default,
                    c.data_length,
                    c.data_precision,
                    c.data_scale,
                    c.char_used,
                    c.column_id,
                    fk.referenced_table as fk_referenced_table,
                    fk.referenced_column as fk_referenced_column
                FROM all_tab_columns c
                LEFT JOIN pk_columns pk ON c.column_name = pk.column_name
                LEFT JOIN fk_columns fk ON c.column_name = fk.column_name
                WHERE c.owner = :schema
                  AND c.table_name = :table_name
                ORDER BY c.column_id
            """, schema=schema, table_name=table_name.upper())

            columns = cursor.fetchall()
            if not columns:
                raise Exception(f"No columns found for {table_name} in schema {schema}.")

            # Format the columns
            schema_info = []
            for col in columns:
                fieldName       = col[0]
                dataType        = self._format_data_type(col[1], col[6], col[7], col[8])
                isNullable      = col[2]
                isPrimaryKey    = col[3]
                isForeignKey    = col[4]
                defaultValue    = col[5]
                referencedTable = col[11] if col[11] else None
                referencedCol   = col[12] if col[12] else None

                schema_info.append({
                    "tableName": table_name,
                    "fieldName": fieldName,
                    "dataType": dataType,
                    "isNullable": isNullable,
                    "isPrimaryKey": isPrimaryKey,
                    "isForeignKey": isForeignKey,
                    "defaultValue": defaultValue,
                    "referencedTable": referencedTable,
                    "referencedColumn": referencedCol
                })
            return schema_info

        except cx_Oracle.DatabaseError as e:
            error_msg = str(e)
            logger.error(f"Oracle error fetching schema for {table_name}: {error_msg}")
            raise Exception(f"Failed to fetch schema: {error_msg}")
        except Exception as e:
            logger.error(f"Unexpected error fetching schema for {table_name}: {str(e)}")
            raise

    def _format_data_type(self, data_type: str, length: int, precision: int, scale: int) -> str:
        """Format the data type with proper length/precision/scale for display."""
        if data_type in ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR'):
            return f"{data_type}({length})"
        elif data_type in ('NUMBER', 'DECIMAL'):
            if precision is not None:
                if scale is not None and scale > 0:
                    return f"{data_type}({precision},{scale})"
                return f"{data_type}({precision})"
            return data_type
        return data_type


def main():
    # -------------------------------
    # 1. Configure Oracle connection
    # -------------------------------
    oracle_config = {
        "server":   "10.24.37.96",       # IP or host for Oracle
        "database": "t24prod",           # Service name (t24prod)
        "username": "T24",
        "password": "T24Pass.123#",
        "schema":   "T24"                # Explicitly set schema if desired
    }

    # -----------------------------
    # 2. Connect to Oracle
    # -----------------------------
    oracle_conn = OracleConnection(oracle_config)
    oracle_conn.connect()

    # -----------------------------
    # 3. Fetch all views
    # -----------------------------
    all_views = oracle_conn.get_tables()  # returns all view names in the schema

    # Filter for views that start with "V_FBNK"
    target_views = [v for v in all_views if v.upper().startswith("V_FBNK")]
    logger.info(f"Found {len(target_views)} views starting with 'V_FBNK'.")

    # -----------------------------
    # 4. Connect to SQL Server
    # -----------------------------
    sql_server_connection_string = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=10.24.37.99;"
        "DATABASE=DATA-DICTIONARY;"
        "UID=bk-pay;"
        "PWD=b9{OwX/^1[^8{rKs;"
    )
    sql_conn = pyodbc.connect(sql_server_connection_string)
    sql_cursor = sql_conn.cursor()
    
    # -----------------------------
    # 5. Create table (if needed)
    # -----------------------------
    create_table_sql = """
    IF NOT EXISTS (
        SELECT 1 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME = 'OracleSchemaMetadata'
    )
    BEGIN
        CREATE TABLE OracleSchemaMetadata (
            table_name        VARCHAR(128),
            field_name        VARCHAR(128),
            data_type         VARCHAR(128),
            is_nullable       VARCHAR(10),
            is_primary_key    VARCHAR(10),
            is_foreign_key    VARCHAR(10),
            default_value     VARCHAR(MAX),
            referenced_table  VARCHAR(128),
            referenced_column VARCHAR(128)
        );
    END;
    """
    sql_cursor.execute(create_table_sql)
    sql_conn.commit()

    # -----------------------------
    # 6. Fetch schema & insert rows
    # -----------------------------
    insert_sql = """
    INSERT INTO OracleSchemaMetadata (
        table_name,
        field_name,
        data_type,
        is_nullable,
        is_primary_key,
        is_foreign_key,
        default_value,
        referenced_table,
        referenced_column
    )
    VALUES (?,?,?,?,?,?,?,?,?)
    """

    for view_name in target_views:
        logger.info(f"Fetching schema for view: {view_name}")
        try:
            schema_info = oracle_conn.get_table_schema(view_name)
            for col in schema_info:
                sql_cursor.execute(
                    insert_sql,
                    col["tableName"],
                    col["fieldName"],
                    col["dataType"],
                    col["isNullable"],
                    col["isPrimaryKey"],
                    col["isForeignKey"],
                    col["defaultValue"],
                    col["referencedTable"],
                    col["referencedColumn"]
                )
            sql_conn.commit()
            logger.info(f"Inserted {len(schema_info)} columns for {view_name}.")
        except Exception as ex:
            logger.error(f"Failed to process {view_name}: {ex}")

    # -----------------------------
    # 7. Clean up
    # -----------------------------
    sql_cursor.close()
    sql_conn.close()
    oracle_conn.disconnect()
    logger.info("Done.")

if __name__ == "__main__":
    main()
