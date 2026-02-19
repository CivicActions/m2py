"""Environment configuration helpers for database backends.

Reads connection parameters from environment variables with sensible defaults
matching the Docker container configurations (ydb.sh / iris.sh).

All configuration errors raise BackendConfigurationError with actionable guidance.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class IRISConfig:
    """IRIS connection parameters read from environment."""

    host: str
    port: int
    namespace: str
    username: str
    password: str

    @classmethod
    def from_env(cls) -> "IRISConfig":
        """Read IRIS configuration from environment variables.

        Environment variables (with defaults matching iris.sh):
            IRIS_HOST      (default: localhost)
            IRIS_PORT      (default: 1972)
            IRIS_NAMESPACE (default: USER)
            IRIS_USER      (default: _SYSTEM)
            IRIS_PASSWORD  (default: SYS)

        Raises:
            BackendConfigurationError: If IRIS_PORT is not a valid integer
        """
        port_str = os.environ.get("IRIS_PORT", "1972")
        try:
            port = int(port_str)
        except ValueError:
            from m2py.runtime.backend_exceptions import BackendConfigurationError

            raise BackendConfigurationError(
                f"IRIS_PORT must be a valid integer, got: {port_str!r}. "
                "Default is 1972. Set via: export IRIS_PORT=1972"
            )
        if port < 1 or port > 65535:
            from m2py.runtime.backend_exceptions import BackendConfigurationError

            raise BackendConfigurationError(
                f"IRIS_PORT must be between 1 and 65535, got: {port}. "
                "Default is 1972. Set via: export IRIS_PORT=1972"
            )
        return cls(
            host=os.environ.get("IRIS_HOST", "localhost"),
            port=port,
            namespace=os.environ.get("IRIS_NAMESPACE", "USER"),
            username=os.environ.get("IRIS_USER", "_SYSTEM"),
            password=os.environ.get("IRIS_PASSWORD", "SYS"),
        )


@dataclass(frozen=True)
class YottaDBConfig:
    """YottaDB configuration (mostly automatic inside the container)."""

    ydb_dist: str | None

    @classmethod
    def from_env(cls) -> "YottaDBConfig":
        """Read YottaDB configuration from environment.

        Inside the YDB container, ydb_env_set automatically sets:
            ydb_dist, ydb_gbldir, ydb_routines, etc.
        """
        return cls(
            ydb_dist=os.environ.get("ydb_dist"),
        )
