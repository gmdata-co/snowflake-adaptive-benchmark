"""Abstract base class for database connections."""

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseConnection(ABC):
    """Abstract base class for database platform connections."""

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the connection.

        Args:
            config: Configuration dictionary containing connection parameters
        """
        self.config = config
        self.connection: Optional[Any] = None

    @abstractmethod
    def connect(self) -> None:
        """
        Establish connection to the database platform.

        Raises:
            ConnectionError: If connection cannot be established
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close the database connection."""
        pass

    @abstractmethod
    def execute_query(self, query: str, **kwargs) -> Any:
        """
        Execute a SQL query.

        Args:
            query: SQL query string to execute
            **kwargs: Additional query execution parameters

        Returns:
            Query result object

        Raises:
            RuntimeError: If not connected or query fails
        """
        pass

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Return the platform name (e.g., 'snowflake', 'databricks')."""
        pass

    def is_connected(self) -> bool:
        """
        Check if connection is active.

        Returns:
            True if connected, False otherwise
        """
        return self.connection is not None

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
