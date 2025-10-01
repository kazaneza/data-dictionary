"""
MySQL connection handler
"""

import mysql.connector
from typing import List, Dict, Any
import logging
from .base import DatabaseConnection

# Configure logging
logger = logging.getLogger(__name__)

class MySQLConnection(DatabaseConnection):
    def connect(self) -> None:
        try:
            # Parse server string for host and port
            host = self.config['server']
            port = '3306'  # Default MySQL port
            
            if ':' in self.config['server']:
                host, port = self.config['server'].split(':')
            
            logger.info(f"Attempting MySQL connection to {host}:{port}")
            logger.info(f"Database: {self.config['database']}")
            logger.info(f"Username: {self.config['username']}")
            
            self.connection = mysql.connector.connect(
                host=host,
                port=int(port),
                user=self.config['username'],
                password=self.config['password'],
                database=self.config['database']
            )
            
            cursor = self.connection.cursor()
            cursor.execute('SELECT VERSION()')
            version = cursor.fetchone()[0]
            logger.info(f"Successfully connected to MySQL. Version: {version}")
            
        except mysql.connector.Error as e:
            error_msg = str(e)
            logger.error(f"MySQL Error: {error_msg}")
            
            if "Access denied" in error_msg:
                raise Exception("Invalid username or password")
            elif "Unknown database" in error_msg:
                raise Exception(f"Database '{self.config['database']}' does not exist")
            elif "Can't connect" in error_msg:
                raise Exception(f"Cannot connect to MySQL server at {host}:{port}")
            else:
                raise Exception(f"MySQL connection error: {error_msg}")

    def disconnect(self) -> None:
        if self.connection:
            try:
                self.connection.close()
                logger.info("MySQL connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing MySQL connection: {str(e)}")

    def get_tables(self) -> List[str]:
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM information_schema.TABLES 
                WHERE TABLE_SCHEMA = %s 
                AND TABLE_TYPE = 'BASE TABLE'
                ORDER BY TABLE_NAME
            """, (self.config['database'],))
            
            tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"Retrieved {len(tables)} tables")
            return tables
            
        except mysql.connector.Error as e:
            logger.error(f"Error fetching tables: {str(e)}")
            raise Exception(f"Failed to fetch tables: {str(e)}")

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        try:
            cursor = self.connection.cursor(dictionary=True)
            
            # Get primary keys
            cursor.execute("""
                SELECT k.COLUMN_NAME
                FROM information_schema.TABLE_CONSTRAINTS t
                JOIN information_schema.KEY_COLUMN_USAGE k
                ON t.CONSTRAINT_NAME = k.CONSTRAINT_NAME
                WHERE t.CONSTRAINT_TYPE = 'PRIMARY KEY'
                AND t.TABLE_SCHEMA = %s
                AND t.TABLE_NAME = %s
            """, (self.config['database'], table_name))
            
            primary_keys = {row['COLUMN_NAME'] for row in cursor.fetchall()}
            
            # Get foreign keys
            cursor.execute("""
                SELECT 
                    k.COLUMN_NAME,
                    k.REFERENCED_TABLE_NAME,
                    k.REFERENCED_COLUMN_NAME
                FROM information_schema.KEY_COLUMN_USAGE k
                WHERE k.TABLE_SCHEMA = %s
                AND k.TABLE_NAME = %s
                AND k.REFERENCED_TABLE_NAME IS NOT NULL
            """, (self.config['database'], table_name))
            
            foreign_keys = {
                row['COLUMN_NAME']: {
                    'referenced_table': row['REFERENCED_TABLE_NAME'],
                    'referenced_column': row['REFERENCED_COLUMN_NAME']
                }
                for row in cursor.fetchall()
            }
            
            # Get column information
            cursor.execute("""
                SELECT 
                    COLUMN_NAME,
                    DATA_TYPE,
                    IS_NULLABLE,
                    COLUMN_DEFAULT,
                    CHARACTER_MAXIMUM_LENGTH,
                    NUMERIC_PRECISION,
                    NUMERIC_SCALE,
                    COLUMN_TYPE
                FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = %s
                AND TABLE_NAME = %s
                ORDER BY ORDINAL_POSITION
            """, (self.config['database'], table_name))
            
            columns = cursor.fetchall()
            
            return [{
                "fieldName": col['COLUMN_NAME'],
                "dataType": self._format_data_type(
                    col['DATA_TYPE'],
                    col['CHARACTER_MAXIMUM_LENGTH'],
                    col['NUMERIC_PRECISION'],
                    col['NUMERIC_SCALE'],
                    col['COLUMN_TYPE']
                ),
                "isNullable": col['IS_NULLABLE'],  # Already returns 'YES' or 'NO'
                "isPrimaryKey": 'YES' if col['COLUMN_NAME'] in primary_keys else 'NO',
                "isForeignKey": 'YES' if col['COLUMN_NAME'] in foreign_keys else 'NO',
                "defaultValue": col['COLUMN_DEFAULT'],
                "referencedTable": foreign_keys.get(col['COLUMN_NAME'], {}).get('referenced_table'),
                "referencedColumn": foreign_keys.get(col['COLUMN_NAME'], {}).get('referenced_column')
            } for col in columns]
            
        except mysql.connector.Error as e:
            logger.error(f"Error fetching schema for table {table_name}: {str(e)}")
            raise Exception(f"Failed to fetch schema: {str(e)}")

    def _format_data_type(self, data_type: str, max_length: int, precision: int, scale: int, column_type: str) -> str:
        """Format the data type with proper length/precision/scale."""
        # Special handling for ENUM types
        if data_type.lower() == 'enum':
            return 'ENUM'  # Simplified representation
            
        if column_type and not column_type.lower().startswith('enum'):
            return column_type.upper()
        
        if data_type in ('char', 'varchar', 'binary', 'varbinary'):
            if max_length == -1:
                return f"{data_type}(max)"
            return f"{data_type}({max_length})"
        elif data_type in ('decimal', 'numeric'):
            if precision is not None:
                if scale is not None and scale > 0:
                    return f"{data_type}({precision},{scale})"
                return f"{data_type}({precision})"
        return data_type.upper()

    def get_connection_string(self) -> str:
        """Generate MySQL connection string."""
        try:
            host = self.config['server']
            if ':' in host:
                host, port = host.split(':')
            else:
                port = '3306'

            return f"mysql://{self.config['username']}:{self.config['password']}@{host}:{port}/{self.config['database']}"
        except KeyError as e:
            raise Exception(f"Missing required configuration parameter: {str(e)}")

    def get_table_count(self, table_name: str) -> int:
        """Get the number of records in a table"""
        try:
            cursor = self.connection.cursor()
            query = f"SELECT COUNT(*) FROM {table_name}"
            cursor.execute(query)
            count = cursor.fetchone()[0]
            cursor.close()
            return count
        except Exception as e:
            return 0