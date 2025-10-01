"""
Microsoft SQL Server connection handler
"""

import pyodbc
from typing import List, Dict, Any
from .base import DatabaseConnection

class MSSQLConnection(DatabaseConnection):
    def connect(self) -> None:
        conn_str = self.get_connection_string()
        self.connection = pyodbc.connect(conn_str, timeout=30)
        
        # Switch to the specified database
        self.connection.execute(f"USE [{self.config['database']}]")

    def disconnect(self) -> None:
        if self.connection:
            self.connection.close()

    def get_tables(self) -> List[str]:
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        return [row[0] for row in cursor.fetchall()]

    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        cursor = self.connection.cursor()
        cursor.execute("""
            WITH pk_columns AS (
                SELECT 
                    kcu.COLUMN_NAME,
                    tc.CONSTRAINT_TYPE
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
                    ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                    AND kcu.TABLE_NAME = ?
            ),
            fk_columns AS (
                SELECT 
                    kcu.COLUMN_NAME,
                    kcu2.TABLE_NAME as REFERENCED_TABLE,
                    kcu2.COLUMN_NAME as REFERENCED_COLUMN
                FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu 
                    ON rc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu2
                    ON rc.UNIQUE_CONSTRAINT_NAME = kcu2.CONSTRAINT_NAME
                WHERE kcu.TABLE_NAME = ?
            )
            SELECT 
                c.COLUMN_NAME as "Field Name",
                c.DATA_TYPE as "Data Type",
                c.IS_NULLABLE as "Nullable",
                CASE WHEN pk.COLUMN_NAME IS NOT NULL THEN 'Yes' ELSE 'No' END as "Primary Key",
                CASE WHEN fk.COLUMN_NAME IS NOT NULL THEN 'Yes' ELSE 'No' END as "Foreign Key",
                c.COLUMN_DEFAULT as "Default Value",
                fk.REFERENCED_TABLE as "Referenced Table",
                fk.REFERENCED_COLUMN as "Referenced Column",
                c.CHARACTER_MAXIMUM_LENGTH as "Max Length",
                c.NUMERIC_PRECISION as "Precision",
                c.NUMERIC_SCALE as "Scale"
            FROM INFORMATION_SCHEMA.COLUMNS c
            LEFT JOIN pk_columns pk ON c.COLUMN_NAME = pk.COLUMN_NAME
            LEFT JOIN fk_columns fk ON c.COLUMN_NAME = fk.COLUMN_NAME
            WHERE c.TABLE_NAME = ?
            ORDER BY c.ORDINAL_POSITION
        """, table_name, table_name, table_name)
        
        columns = cursor.fetchall()
        return [{
            "fieldName": col[0],
            "dataType": self._format_data_type(col[1], col[8], col[9], col[10]),
            "isNullable": col[2],
            "isPrimaryKey": col[3],
            "isForeignKey": col[4],
            "defaultValue": col[5],
            "referencedTable": col[6],
            "referencedColumn": col[7]
        } for col in columns]

    def _format_data_type(self, data_type: str, max_length: int, precision: int, scale: int) -> str:
        """Format the data type with proper length/precision/scale."""
        if data_type in ('char', 'varchar', 'nchar', 'nvarchar'):
            if max_length == -1:
                return f"{data_type}(max)"
            return f"{data_type}({max_length})"
        elif data_type in ('decimal', 'numeric'):
            if precision is not None:
                if scale is not None and scale > 0:
                    return f"{data_type}({precision},{scale})"
                return f"{data_type}({precision})"
        return data_type

    def get_connection_string(self) -> str:
        return (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.config['server']};"
            f"DATABASE={self.config['database']};"
            f"UID={self.config['username']};"
            f"PWD={self.config['password']};"
            "TrustServerCertificate=yes;"
            "Encrypt=yes;"
            "Connection Timeout=30;"
        )

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