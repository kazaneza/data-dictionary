"""
Base class for database connections
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class DatabaseConnection(ABC):
    def __init__(self, config: Dict[str, str]):
        self.config = config
        self.connection = None

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the database"""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close the database connection"""
        pass

    @abstractmethod
    def get_tables(self) -> List[str]:
        """Get list of tables in the database"""
        pass

    @abstractmethod
    def get_table_schema(self, table_name: str) -> List[Dict[str, Any]]:
        """Get schema information for a specific table"""
        pass

    @abstractmethod
    def get_connection_string(self) -> str:
        """Get the connection string for the database"""
        pass

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()