"""
PostgreSQL connection handler
"""

import psycopg2
import logging
from typing import List, Dict, Any
from .base import DatabaseConnection

# Configure logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('postgres_connection.log'),
        logging.StreamHandler()
    ]
)

class PostgresConnection(DatabaseConnection):
    def connect(self) -> None:
        try:
            # Parse server string for host and port
            host = self.config['server']
            port = '5432'  # Default PostgreSQL port
            
            if ':' in self.config['server']:
                host, port = self.config['server'].split(':')
            
            logger.info(f"Attempting PostgreSQL connection to {host}:{port}")
            logger.info(f"Database: {self.config['database']}")
            logger.info(f"Username: {self.config['username']}")
            
            # Build connection parameters
            conn_params = {
                'host': host,
                'port': port,
                'database': self.config['database'],
                'user': self.config['username'],
                'password': self.config['password'],
                'connect_timeout': 30,
                'client_encoding': 'utf8'
            }
            
            # Log connection parameters (excluding password)
            safe_params = {k: v for k, v in conn_params.items() if k != 'password'}
            logger.debug(f"Connection parameters: {safe_params}")
            
            # Attempt connection
            self.connection = psycopg2.connect(**conn_params)
            
            # Test the connection
            cursor = self.connection.cursor()
            cursor.execute('SELECT version()')
            version = cursor.fetchone()[0]
            logger.info(f"Successfully connected to PostgreSQL. Version: {version}")
            
        except psycopg2.OperationalError as e:
            error_msg = str(e).strip()
            logger.error(f"PostgreSQL OperationalError: {error_msg}")
            
            if "connection refused" in error_msg.lower():
                raise Exception(f"Connection refused to {host}:{port}. Please verify the server is running and accessible.")
            elif "password authentication failed" in error_msg.lower():
                raise Exception("Invalid username or password.")
            elif "database" in error_msg.lower() and "does not exist" in error_msg.lower():
                raise Exception(f"Database '{self.config['database']}' does not exist.")
            else:
                raise Exception(f"Failed to connect to PostgreSQL: {error_msg}")
                
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL Error: {e.__class__.__name__} - {str(e)}")
            raise Exception(f"PostgreSQL error: {str(e)}")
            
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}", exc_info=True)
            raise Exception(f"Unexpected error connecting to PostgreSQL: {str(e)}")

    def disconnect(self) -> None:
        if self.connection:
            try:
                self.connection.close()
                logger.info("PostgreSQL connection closed successfully")
            except Exception as e:
                logger.error(f"Error closing PostgreSQL connection: {str(e)}")

    def get_tables(self) -> List[str]:
        try:
            cursor = self.connection.cursor()
            logger.debug("Fetching table list")
            
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            logger.info(f"Successfully retrieved {len(tables)} tables")
            return tables
            
        except psycopg2.Error as e:
            logger.error(f"Error fetching tables: {str(e)}")
            raise Exception(f"Failed to fetch tables: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching tables: {str(e)}")
            raise Exception(f"Unexpected error fetching tables: {str(e)}")

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        try:
            cursor = self.connection.cursor()
            logger.debug(f"Fetching schema for table: {table_name}")
            
            cursor.execute("""
                WITH pk_columns AS (
                    SELECT 
                        kcu.column_name,
                        tc.constraint_type
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                        AND kcu.table_name = %s
                        AND tc.table_schema = 'public'
                ),
                fk_columns AS (
                    SELECT 
                        kcu.column_name,
                        ccu.table_name AS referenced_table,
                        ccu.column_name AS referenced_column
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage ccu
                        ON tc.constraint_name = ccu.constraint_name
                        AND tc.table_schema = ccu.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND kcu.table_name = %s
                        AND tc.table_schema = 'public'
                )
                SELECT 
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    CASE WHEN pk.column_name IS NOT NULL THEN 'Yes' ELSE 'No' END as is_primary_key,
                    CASE WHEN fk.column_name IS NOT NULL THEN 'Yes' ELSE 'No' END as is_foreign_key,
                    c.column_default,
                    fk.referenced_table,
                    fk.referenced_column,
                    c.character_maximum_length,
                    c.numeric_precision,
                    c.numeric_scale,
                    c.udt_name
                FROM information_schema.columns c
                LEFT JOIN pk_columns pk ON c.column_name = pk.column_name
                LEFT JOIN fk_columns fk ON c.column_name = fk.column_name
                WHERE c.table_name = %s
                    AND c.table_schema = 'public'
                ORDER BY c.ordinal_position
            """, (table_name, table_name, table_name))
            
            columns = cursor.fetchall()
            logger.info(f"Successfully retrieved schema for {len(columns)} columns in table {table_name}")
            
            return [{
                "fieldName": col[0],
                "dataType": self._format_data_type(col[1], col[8], col[9], col[10], col[11]),
                "isNullable": col[2],
                "isPrimaryKey": col[3],
                "isForeignKey": col[4],
                "defaultValue": col[5],
                "referencedTable": col[6],
                "referencedColumn": col[7]
            } for col in columns]
            
        except psycopg2.Error as e:
            logger.error(f"Error fetching schema for table {table_name}: {str(e)}")
            raise Exception(f"Failed to fetch schema for table {table_name}: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error fetching schema: {str(e)}")
            raise Exception(f"Unexpected error fetching schema: {str(e)}")

    def _format_data_type(self, data_type: str, max_length: int, precision: int, scale: int, udt_name: str) -> str:
        """Format the data type with proper length/precision/scale."""
        if data_type in ('character varying', 'character', 'varchar', 'char'):
            if max_length is not None:
                return f"{data_type}({max_length})"
        elif data_type in ('numeric', 'decimal'):
            if precision is not None:
                if scale is not None and scale > 0:
                    return f"{data_type}({precision},{scale})"
                return f"{data_type}({precision})"
        elif data_type == 'ARRAY':
            return f"{udt_name}[]"
        return data_type

    def get_connection_string(self) -> str:
        # This method is not used anymore as we're using connection parameters
        # but kept for compatibility with the base class
        return ""