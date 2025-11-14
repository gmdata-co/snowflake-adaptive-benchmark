"""Connection abstractions for different data platforms."""

from .base_connection import BaseConnection
from .snowflake_connection import SnowflakeConnection
from .databricks_connection import DatabricksConnection

__all__ = ["BaseConnection", "SnowflakeConnection", "DatabricksConnection"]
