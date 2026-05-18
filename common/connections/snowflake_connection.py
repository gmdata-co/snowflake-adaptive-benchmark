"""Snowflake connection implementation."""

from pathlib import Path

import toml
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization

from .base_connection import BaseConnection

# Initialize centralized logging
from ..logging_config import get_logger

logger = get_logger(__name__)


class SnowflakeConnection(BaseConnection):
    """Snowflake database connection implementation."""

    def __init__(
        self,
        connection_name: str,
        role: str,
        database: str,
        schema: str,
    ):
        """
        Initialize Snowflake connection.

        Args:
            connection_name: Name of connection in ~/.snowflake/connections.toml
            role: Snowflake role to use
            database: Database name
            schema: Schema name
        """
        config = {
            "connection_name": connection_name,
            "role": role,
            "database": database,
            "schema": schema,
        }
        super().__init__(config)
        self.connection_name = connection_name
        self.role = role
        self.database = database
        self.schema = schema

    @property
    def platform_name(self) -> str:
        """Return platform name."""
        return "snowflake"

    def _load_connection_config(self, connection_name: str) -> dict:
        """
        Load connection configuration from the standard Snowflake locations.

        Supports two formats so the framework works with both the legacy
        Snowflake connector layout and the current Snowflake CLI v2 layout:

          1. ~/.snowflake/connections.toml   — flat `[<connection_name>]` sections.
          2. ~/.snowflake/config.toml        — CLI v2 `[connections.<name>]` sections
                                               (this is what `snow connection add` writes).
        """
        snowflake_dir = Path.home() / ".snowflake"
        connections_file = snowflake_dir / "connections.toml"
        config_file = snowflake_dir / "config.toml"

        if connections_file.exists():
            config = toml.load(connections_file)
            if connection_name in config:
                return config[connection_name]

        if config_file.exists():
            config = toml.load(config_file)
            nested = config.get("connections", {})
            if connection_name in nested:
                return nested[connection_name]

        if not connections_file.exists() and not config_file.exists():
            raise FileNotFoundError(
                f"Snowflake config not found. Expected one of:\n"
                f"  {connections_file}\n"
                f"  {config_file}\n"
                f"Run `snow connection add` or create connections.toml manually."
            )

        searched = [str(connections_file), str(config_file)]
        raise ValueError(
            f"Connection '{connection_name}' not found in any of: {searched}"
        )

    def _load_private_key(self, private_key_path: str) -> bytes:
        """
        Load and decode the private key for JWT authentication.

        Args:
            private_key_path: Path to the private key file

        Returns:
            Private key bytes in DER format
        """
        with open(private_key_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(), password=None, backend=default_backend()
            )

        return private_key.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def connect(self) -> None:
        """
        Establish connection to Snowflake.

        Raises:
            ConnectionError: If connection cannot be established
        """
        logger.info(f"Connecting to Snowflake using connection: {self.connection_name}")

        # Load connection configuration from ~/.snowflake/connections.toml
        conn_config = self._load_connection_config(self.connection_name)

        # Prepare connection parameters
        connect_params = {
            "account": conn_config["account"],
            "user": conn_config["user"],
            "role": self.role,
            "database": self.database,
            "schema": self.schema,
        }

        # Handle JWT authentication if configured
        if conn_config.get("authenticator") == "SNOWFLAKE_JWT":
            private_key_path = conn_config.get("private_key_path") or conn_config.get(
                "private_key_file"
            )
            if private_key_path:
                connect_params["private_key"] = self._load_private_key(private_key_path)

        # Connect to Snowflake
        self.connection = snowflake.connector.connect(**connect_params)

        # Result caching is disabled at the USER level
        # (ALTER USER ... SET USE_CACHED_RESULT = FALSE), so every session
        # inherits FALSE without a per-connection ALTER SESSION. This removed
        # the per-connection statement flood in the concurrent scenario
        # (one connection per query).

        logger.info("✅ Connected to Snowflake")
        logger.info(f"✅ Using role: {self.role}")
        logger.info(f"✅ Database: {self.database}")

    def disconnect(self) -> None:
        """Close Snowflake connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("✅ Disconnected from Snowflake")

    def execute_query(
        self, query: str, async_exec: bool = False, **kwargs
    ) -> snowflake.connector.cursor.SnowflakeCursor:
        """
        Execute a SQL query.

        Args:
            query: SQL query string to execute
            async_exec: If True, execute asynchronously
            **kwargs: Additional cursor parameters (e.g., cursor_class)

        Returns:
            Snowflake cursor object

        Raises:
            RuntimeError: If not connected
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Snowflake. Call connect() first.")

        cursor_class = kwargs.get("cursor_class")
        if cursor_class:
            cursor = self.connection.cursor(cursor_class)
        else:
            cursor = self.connection.cursor()

        cursor.execute(query, _no_results=async_exec)
        return cursor

    def get_cursor(self, cursor_class=None) -> snowflake.connector.cursor.SnowflakeCursor:
        """
        Get a cursor for direct query execution.

        Args:
            cursor_class: Optional cursor class (e.g., DictCursor)

        Returns:
            Snowflake cursor object

        Raises:
            RuntimeError: If not connected
        """
        if not self.is_connected():
            raise RuntimeError("Not connected to Snowflake. Call connect() first.")

        if cursor_class:
            return self.connection.cursor(cursor_class)
        return self.connection.cursor()
