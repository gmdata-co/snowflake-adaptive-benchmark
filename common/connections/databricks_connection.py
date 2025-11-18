"""Databricks connection implementation."""

from typing import Any

from databricks import sql

from .base_connection import BaseConnection

# Initialize centralized logging
from ..logging_config import get_logger

logger = get_logger(__name__)


class DatabricksConnection(BaseConnection):
    """Databricks database connection implementation."""

    def __init__(
        self,
        host: str,
        token: str,
        warehouse_id: str,
        catalog: str,
        schema: str,
    ):
        """
        Initialize Databricks connection.

        Args:
            host: Databricks workspace URL (e.g., https://dbc-xxxx.cloud.databricks.com)
            token: Personal access token for authentication
            warehouse_id: SQL warehouse ID
            catalog: Catalog name
            schema: Schema name
        """
        config = {
            "host": host,
            "token": token,
            "warehouse_id": warehouse_id,
            "catalog": catalog,
            "schema": schema,
        }
        super().__init__(config)
        self.host = host
        self.token = token
        self.warehouse_id = warehouse_id
        self.catalog = catalog
        self.schema = schema

    @property
    def platform_name(self) -> str:
        """Return platform name."""
        return "databricks"

    def connect(self) -> None:
        """
        Establish connection to Databricks.

        Raises:
            ConnectionError: If connection cannot be established
        """
        logger.info(f"Connecting to Databricks warehouse: {self.warehouse_id}")

        try:
            # Clean hostname (remove https:// prefix if present)
            hostname = self.host.replace("https://", "").replace("http://", "")

            # Build HTTP path for warehouse
            http_path = f"/sql/1.0/warehouses/{self.warehouse_id}"

            # Connect to Databricks
            self.connection = sql.connect(
                server_hostname=hostname,
                http_path=http_path,
                access_token=self.token,
            )

            # Set catalog and schema for this connection
            cursor = self.connection.cursor()
            cursor.execute(f"USE CATALOG {self.catalog}")
            cursor.execute(f"USE SCHEMA {self.schema}")
            cursor.close()

            logger.info("✅ Connected to Databricks")
            logger.info(f"✅ Warehouse: {self.warehouse_id}")
            logger.info(f"✅ Catalog: {self.catalog}")
            logger.info(f"✅ Schema: {self.schema}")

        except Exception as e:
            logger.error(f"❌ Failed to connect to Databricks: {e}")
            raise ConnectionError(f"Databricks connection failed: {e}") from e

    def disconnect(self) -> None:
        """Close Databricks connection."""
        if self.connection:
            try:
                # Close connection with a short timeout to prevent hanging during shutdown
                self.connection.close()
                logger.info("✅ Disconnected from Databricks")
            except Exception as e:
                # During Python shutdown, sys.meta_path may be None
                # Log warning but don't fail - connection will be cleaned up by OS
                logger.warning(f"⚠️  Error during Databricks disconnect (may be normal during shutdown): {e}")
            finally:
                self.connection = None

    def execute_query(self, query: str, **kwargs) -> Any:
        """
        Execute a SQL query.

        Args:
            query: SQL query string to execute
            **kwargs: Additional query execution parameters

        Returns:
            Databricks SQL cursor object

        Raises:
            RuntimeError: If not connected
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Databricks. Call connect() first.")

        cursor = self.connection.cursor()
        cursor.execute(query)
        return cursor

    def get_cursor(self) -> Any:
        """
        Get a cursor for direct query execution.

        Returns:
            Databricks SQL cursor object

        Raises:
            RuntimeError: If not connected
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Databricks. Call connect() first.")

        return self.connection.cursor()
