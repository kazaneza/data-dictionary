"""
Database connection handlers for different database types
"""

from .mssql import MSSQLConnection
from .oracle import OracleConnection
from .postgres import PostgresConnection
from .mysql import MySQLConnection

# Factory function to get the appropriate connection handler
def get_connection_handler(db_type: str):
    handlers = {
        'MSSQL': MSSQLConnection,
        'Oracle': OracleConnection,
        'PostgreSQL': PostgresConnection,
        'MySQL': MySQLConnection
    }
    
    handler = handlers.get(db_type)
    if not handler:
        raise ValueError(f"Unsupported database type: {db_type}")
    
    return handler