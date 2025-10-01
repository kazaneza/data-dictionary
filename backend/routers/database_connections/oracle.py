"""
Oracle database connection handler with background processing support
"""

import cx_Oracle
import logging
import platform
import os
import json
from typing import List, Dict, Any
from .base import DatabaseConnection
from pathlib import Path
import time

# Configure logging
logger = logging.getLogger(__name__)
from typing import List

class OracleConnection(DatabaseConnection):
    def __init__(self, config: Dict[str, str]):
        super().__init__(config)
        self.checkpoint_dir = Path('/tmp/oracle_checkpoints')
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._setup_checkpoint_file()

    def _setup_checkpoint_file(self):
        """Setup checkpoint file for tracking progress"""
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
        """Save checkpoint data to file"""
        with open(self.checkpoint_file, 'w') as f:
            json.dump(data, f)

    def _load_checkpoint(self) -> Dict:
        """Load checkpoint data from file"""
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
            cx_Oracle.clientversion()
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
                    "3. Add the directory to PATH environment variable\n"
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
        try:
            self._check_oracle_client()
            
            schema = self.config.get('schema', '').upper() if 'schema' in self.config else None
            
            # Try multiple connection string formats
            connection_attempts = self._get_connection_attempts()
            
            logger.info(f"Attempting Oracle connection to {self.config['server']}")
            logger.info(f"Database: {self.config['database']}")
            logger.info(f"Username: {self.config['username']}")
            
            last_error = None
            for i, conn_str in enumerate(connection_attempts):
                try:
                    logger.info(f"Trying connection format {i+1}: {conn_str.replace(self.config['password'], '***')}")
                    self.connection = cx_Oracle.connect(
                        conn_str,
                        encoding="UTF-8",
                        nencoding="UTF-8"
                    )
                    logger.info(f"Successfully connected using format {i+1}")
                    break
                except cx_Oracle.DatabaseError as e:
                    last_error = e
                    logger.warning(f"Connection format {i+1} failed: {str(e)}")
                    continue
            
            if not self.connection:
                # All connection attempts failed, raise the last error
                raise last_error
            
            cursor = self.connection.cursor()
            cursor.arraysize = 1000
            
            cursor.execute("""
                ALTER SESSION SET 
                NLS_DATE_FORMAT = 'YYYY-MM-DD HH24:MI:SS'
                NLS_TIMESTAMP_FORMAT = 'YYYY-MM-DD HH24:MI:SS.FF'
            """)
            
            cursor.execute("SELECT * FROM v$version")
            version = cursor.fetchone()[0]
            logger.info(f"Successfully connected to Oracle. Version: {version}")
            
            cursor.execute("SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM DUAL")
            current_schema = cursor.fetchone()[0]
            logger.info(f"Connected to schema: {current_schema}")
            
            if schema:
                try:
                    cursor.execute("""
                        SELECT username, account_status 
                        FROM all_users 
                        WHERE username = :schema
                    """, schema=schema)
                    
                    user_info = cursor.fetchone()
                    if not user_info:
                        raise Exception(f"Schema {schema} does not exist")
                    
                    if user_info[1] != 'OPEN':
                        raise Exception(f"Schema {schema} is not accessible (status: {user_info[1]})")
                    
                    logger.info(f"Found schema {schema}. Status: {user_info[1]}")
                    
                    cursor.execute("""
                        SELECT DISTINCT privilege 
                        FROM all_tab_privs 
                        WHERE owner = :schema 
                          AND grantee IN (USER, 'PUBLIC')
                    """, schema=schema)
                    
                    privileges = cursor.fetchall()
                    if privileges:
                        logger.info(f"Privileges on schema {schema}: {', '.join(p[0] for p in privileges)}")
                    else:
                        logger.warning(f"No explicit privileges found on schema {schema}")
                    
                    cursor.execute(f"ALTER SESSION SET CURRENT_SCHEMA = {schema}")
                    logger.info(f"Successfully switched to schema: {schema}")
                    
                except cx_Oracle.DatabaseError as e:
                    error_msg = str(e)
                    logger.error(f"Failed to switch to schema {schema}: {error_msg}")
                    raise Exception(f"Failed to access schema {schema}: {error_msg}")
            
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

    def disconnect(self) -> None:
        if self.connection:
            try:
                self.connection.close()
                logger.info("Oracle connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing Oracle connection: {str(e)}")
                raise Exception(f"Failed to close connection: {str(e)}")

    def _get_connection_attempts(self) -> List[str]:
        """Generate multiple connection string formats to try"""
        server = self.config['server']
        database = self.config['database']
        username = self.config['username']
        password = self.config['password']
        
        attempts = []
        
        # Format 1: Direct service name (most common for Oracle 12c+)
        attempts.append(f"{username}/{password}@{server}:1521/{database}")
        
        # Format 2: TNS Easy Connect with explicit port
        attempts.append(f"{username}/{password}@{server}:1521/{database}")
        
        # Format 3: SID format (older Oracle versions)
        attempts.append(f"{username}/{password}@{server}:1521:{database}")
        
        # Format 4: If server already includes port
        if ':' in server:
            attempts.append(f"{username}/{password}@{server}/{database}")
            attempts.append(f"{username}/{password}@{server}:{database}")
        
        # Format 5: If server already includes service
        if '/' in server:
            attempts.append(f"{username}/{password}@{server}")
        
        # Format 6: Simple format without port (uses default 1521)
        attempts.append(f"{username}/{password}@{server}/{database}")
        
        # Format 7: Alternative service format
        attempts.append(f"{username}/{password}@//{server}:1521/{database}")
        
        return attempts

    def get_tables(self, batch_size: int = 1000) -> List[str]:
        """
        Get list of views with background processing and checkpointing support.
        Continues processing even if connection is lost.
        """
        checkpoint = self._load_checkpoint()
        
        # If already in progress, return processed views
        if checkpoint['in_progress']:
            logger.info("Resuming previous extraction...")
            return checkpoint['processed_views']
        
        try:
            # Mark as in progress
            checkpoint['in_progress'] = True
            self._save_checkpoint(checkpoint)
            
            cursor = self.connection.cursor()
            cursor.arraysize = batch_size
            
            schema = self.config.get('schema', '').upper() if 'schema' in self.config else None
            
            if not schema:
                cursor.execute("SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM DUAL")
                schema = cursor.fetchone()[0]
            
            logger.info(f"Starting view extraction for schema: {schema}")
            
            views = checkpoint['processed_views']
            offset = checkpoint['last_offset']
            
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
                        break
                    
                    new_views = [row[0] for row in batch]
                    views.extend(new_views)
                    offset += len(batch)
                    
                    # Save checkpoint after each batch
                    checkpoint.update({
                        'last_offset': offset,
                        'processed_views': views,
                        'in_progress': True
                    })
                    self._save_checkpoint(checkpoint)
                    
                    logger.info(f"Processed {len(views)} views so far...")
                    
                    if len(batch) < batch_size:
                        break
                    
                    # Small delay to prevent overwhelming the server
                    time.sleep(0.1)
                    
                except cx_Oracle.DatabaseError as e:
                    if "ORA-03113" in str(e) or "ORA-03114" in str(e):
                        # Connection lost - save checkpoint and reconnect
                        logger.warning("Connection lost. Attempting to reconnect...")
                        self.connect()
                        cursor = self.connection.cursor()
                        cursor.arraysize = batch_size
                        continue
                    else:
                        raise
            
            # Mark as complete
            checkpoint['in_progress'] = False
            self._save_checkpoint(checkpoint)
            
            logger.info(f"Completed view extraction. Total views: {len(views)}")
            return views
            
        except Exception as e:
            logger.error(f"Error during view extraction: {str(e)}")
            checkpoint['failed_views'].append({
                'offset': offset,
                'error': str(e)
            })
            self._save_checkpoint(checkpoint)
            raise

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        try:
            cursor = self.connection.cursor()
            schema = self.config.get('schema', '').upper() if 'schema' in self.config else None
            
            if not schema:
                cursor.execute("SELECT SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') FROM DUAL")
                schema = cursor.fetchone()[0]
            
            logger.debug(f"Fetching schema for {table_name} in schema {schema}")
            
            # First check if the table/view exists and get its type
            cursor.execute("""
                SELECT object_type
                FROM all_objects
                WHERE owner = :schema
                  AND object_name = :object_name
                  AND object_type IN ('TABLE', 'VIEW')
            """, schema=schema, object_name=table_name.upper())
            
            result = cursor.fetchone()
            if not result:
                cursor.execute("""
                    SELECT owner, object_type
                    FROM all_objects
                    WHERE object_name = :object_name
                      AND object_type IN ('TABLE', 'VIEW')
                """, object_name=table_name.upper())
                
                other_schemas = cursor.fetchall()
                if other_schemas:
                    schemas_str = ', '.join(f"{row[0]} ({row[1]})" for row in other_schemas)
                    raise Exception(
                        f"Table or view '{table_name}' not found in schema {schema}. "
                        f"However, it exists in the following schemas: {schemas_str}"
                    )
                else:
                    raise Exception(f"Table or view '{table_name}' not found in any accessible schema.")
            
            object_type = result[0]
            logger.info(f"Found {object_type}: {table_name}")
            
            try:
                # Enhanced query to properly detect primary and foreign keys
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
                    raise Exception(f"No columns found for {table_name} in schema {schema}")
                
                logger.info(f"Retrieved {len(columns)} columns for {object_type} {table_name}")
                
                return [{
                    "fieldName": col[0],
                    "dataType": self._format_data_type(col[1], col[6], col[7], col[8]),
                    "isNullable": col[2],
                    "isPrimaryKey": col[3],
                    "isForeignKey": col[4],
                    "defaultValue": col[5],
                    "referencedTable": col[11] if col[11] else None,
                    "referencedColumn": col[12] if col[12] else None
                } for col in columns]
                
            except cx_Oracle.DatabaseError as e:
                error_msg = str(e)
                logger.error(f"Oracle error fetching schema for {table_name}: {error_msg}")
                raise Exception(f"Failed to fetch schema: {error_msg}")
                
        except Exception as e:
            logger.error(f"Unexpected error fetching schema: {str(e)}")
            raise Exception(f"Failed to fetch schema: {str(e)}")

    def _format_data_type(self, data_type: str, length: int, precision: int, scale: int) -> str:
        """Format the data type with proper length/precision/scale."""
        if data_type in ('VARCHAR2', 'CHAR', 'NVARCHAR2', 'NCHAR'):
            return f"{data_type}({length})"
        elif data_type in ('NUMBER', 'DECIMAL'):
            if precision is not None:
                if scale is not None and scale > 0:
                    return f"{data_type}({precision},{scale})"
                return f"{data_type}({precision})"
            return data_type
        return data_type

    def get_connection_string(self) -> str:
        """Generate Oracle connection string."""
        try:
            server = self.config['server']
            database = self.config['database']
            username = self.config['username']
            password = self.config['password']
            
            # Try different connection string formats based on the server configuration
            if '/' in server:
                # Server already includes service name (e.g., "10.24.37.96/t24prod")
                return f"{username}/{password}@{server}"
            elif ':' in server:
                # Server includes port (e.g., "10.24.37.96:1521")
                return f"{username}/{password}@{server}/{database}"
            else:
                # Try multiple formats for Oracle connection
                # Format 1: Direct service connection
                return f"{username}/{password}@{server}:1521/{database}"

        except KeyError as e:
            raise Exception(f"Missing required configuration parameter: {str(e)}")

    def get_table_count(self, table_name: str) -> int:
        """Get the number of records in a table"""
        try:
            cursor = self.connection.cursor()
            # Use RECID as specified by user, fallback to COUNT(*) if RECID doesn't exist
            try:
                query = f"SELECT COUNT(RECID) FROM {table_name}"
                cursor.execute(query)
                count = cursor.fetchone()[0]
            except:
                # Fallback to COUNT(*) if RECID column doesn't exist
                query = f"SELECT COUNT(*) FROM {table_name}"
                cursor.execute(query)
                count = cursor.fetchone()[0]

            cursor.close()
            logger.info(f"Table {table_name} has {count} records")
            return count
        except Exception as e:
            logger.error(f"Error counting records in {table_name}: {str(e)}")
            return 0