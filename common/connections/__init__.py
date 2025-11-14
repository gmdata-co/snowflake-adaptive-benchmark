"""Connection abstractions for different data platforms."""

from .base_connection import BaseConnection
from .snowflake_connection import SnowflakeConnection

__all__ = ["BaseConnection", "SnowflakeConnection"]
