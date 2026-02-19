"""Tests for backend connection lifecycle and error handling.

Covers: lazy initialization, factory selection, environment configuration,
programmatic API, exception hierarchy.
"""

from __future__ import annotations

import pytest


class TestLazyInitialization:
    """Test that backends defer SDK import until first use."""

    def test_backend_creates_without_error(self, backend):
        """Backend should initialize without errors (even if SDK missing for inmemory)."""
        # The fixture already created the backend.
        assert backend is not None

    def test_backend_works_after_creation(self, backend):
        """Basic operations work after creation."""
        backend.set("TEST", ("1",), "value")
        assert backend.get("TEST", ("1",)) == "value"


class TestFactorySelection:
    """Test backend factory selection via environment variable."""

    def test_inmemory_by_default(self, monkeypatch):
        """No configuration defaults to InMemoryGlobalStorage."""
        from m2py.runtime import get_global_storage
        from m2py.runtime.globals import InMemoryGlobalStorage

        monkeypatch.delenv("M2PY_GLOBAL_BACKEND", raising=False)
        b = get_global_storage()
        assert isinstance(b, InMemoryGlobalStorage)

    def test_inmemory_explicit(self, monkeypatch):
        """M2PY_GLOBAL_BACKEND=inmemory selects InMemoryGlobalStorage."""
        from m2py.runtime import get_global_storage
        from m2py.runtime.globals import InMemoryGlobalStorage

        monkeypatch.setenv("M2PY_GLOBAL_BACKEND", "inmemory")
        b = get_global_storage()
        assert isinstance(b, InMemoryGlobalStorage)

    def test_inmemory_explicit_param(self):
        from m2py.runtime import get_global_storage
        from m2py.runtime.globals import InMemoryGlobalStorage

        b = get_global_storage("inmemory")
        assert isinstance(b, InMemoryGlobalStorage)

    def test_unknown_backend_raises(self):
        from m2py.runtime import get_global_storage

        with pytest.raises(ValueError, match="Unknown global storage backend"):
            get_global_storage("nonexistent")

    def test_case_insensitive_backend_name(self, monkeypatch):
        """Backend names are case-insensitive."""
        from m2py.runtime import get_global_storage
        from m2py.runtime.globals import InMemoryGlobalStorage

        monkeypatch.setenv("M2PY_GLOBAL_BACKEND", "INMEMORY")
        b = get_global_storage()
        assert isinstance(b, InMemoryGlobalStorage)

    def test_explicit_param_overrides_env(self, monkeypatch):
        """Explicit backend parameter takes precedence over env var."""
        from m2py.runtime import get_global_storage
        from m2py.runtime.globals import InMemoryGlobalStorage

        monkeypatch.setenv("M2PY_GLOBAL_BACKEND", "nonexistent_backend_xyz")
        backend = get_global_storage("inmemory")
        assert isinstance(backend, InMemoryGlobalStorage)

    def test_factory_returns_new_instance_each_call(self):
        """Each call to get_global_storage() returns a new instance."""
        from m2py.runtime import get_global_storage

        backend1 = get_global_storage("inmemory")
        backend2 = get_global_storage("inmemory")
        assert backend1 is not backend2

    def test_yottadb_factory_creates_backend(self):
        """Factory creates YottaDBGlobalStorage (lazy — no SDK needed)."""
        from m2py.runtime import get_global_storage
        from m2py.runtime.yottadb_backend import YottaDBGlobalStorage

        b = get_global_storage("yottadb")
        assert isinstance(b, YottaDBGlobalStorage)

    def test_iris_factory_creates_backend(self):
        """Factory creates IRISGlobalStorage (lazy — no connection needed)."""
        from m2py.runtime import get_global_storage
        from m2py.runtime.iris_backend import IRISGlobalStorage

        b = get_global_storage("iris")
        assert isinstance(b, IRISGlobalStorage)


class TestProgrammaticAPI:
    """Test MUMPSRuntime(global_storage=...) programmatic configuration."""

    def test_explicit_backend_parameter(self):
        """MUMPSRuntime(global_storage=...) uses provided backend."""
        from m2py.runtime import MUMPSRuntime
        from m2py.runtime.globals import InMemoryGlobalStorage

        custom_backend = InMemoryGlobalStorage()
        rt = MUMPSRuntime(global_storage=custom_backend)
        assert rt.globals is custom_backend

    def test_default_uses_factory(self, monkeypatch):
        """MUMPSRuntime without global_storage uses get_global_storage()."""
        from m2py.runtime import MUMPSRuntime
        from m2py.runtime.globals import InMemoryGlobalStorage

        monkeypatch.delenv("M2PY_GLOBAL_BACKEND", raising=False)
        rt = MUMPSRuntime()
        assert isinstance(rt.globals, InMemoryGlobalStorage)


class TestExceptionTranslation:
    """Test that backend exceptions are properly translated."""

    def test_backend_exception_hierarchy(self):
        """Verify exception classes exist and inherit correctly."""
        from m2py.runtime.backend_exceptions import (
            BackendError,
            BackendConnectionError,
            BackendTimeoutError,
            BackendPermissionError,
            BackendConfigurationError,
        )
        from m2py.runtime.exceptions import MRuntimeError

        assert issubclass(BackendError, MRuntimeError)
        assert issubclass(BackendConnectionError, BackendError)
        assert issubclass(BackendTimeoutError, BackendError)
        assert issubclass(BackendPermissionError, BackendError)
        assert issubclass(BackendConfigurationError, BackendError)

    def test_backend_error_has_code(self):
        from m2py.runtime.backend_exceptions import BackendError

        err = BackendError("TESTCODE", "test message")
        assert "TESTCODE" in str(err) or hasattr(err, "code")


class TestConfigValidation:
    """Test environment configuration validation (T090-T094)."""

    def test_iris_config_defaults(self, monkeypatch):
        """IRIS config uses sensible defaults when no env vars set."""
        from m2py.runtime.backend_config import IRISConfig

        monkeypatch.delenv("IRIS_HOST", raising=False)
        monkeypatch.delenv("IRIS_PORT", raising=False)
        monkeypatch.delenv("IRIS_NAMESPACE", raising=False)
        monkeypatch.delenv("IRIS_USER", raising=False)
        monkeypatch.delenv("IRIS_PASSWORD", raising=False)
        config = IRISConfig.from_env()
        assert config.host == "localhost"
        assert config.port == 1972
        assert config.namespace == "USER"
        assert config.username == "_SYSTEM"
        assert config.password == "SYS"

    def test_iris_config_from_env(self, monkeypatch):
        """IRIS config reads from environment variables."""
        from m2py.runtime.backend_config import IRISConfig

        monkeypatch.setenv("IRIS_HOST", "myhost")
        monkeypatch.setenv("IRIS_PORT", "9999")
        monkeypatch.setenv("IRIS_NAMESPACE", "MYNS")
        monkeypatch.setenv("IRIS_USER", "admin")
        monkeypatch.setenv("IRIS_PASSWORD", "secret")
        config = IRISConfig.from_env()
        assert config.host == "myhost"
        assert config.port == 9999
        assert config.namespace == "MYNS"
        assert config.username == "admin"
        assert config.password == "secret"

    def test_iris_config_invalid_port_raises(self, monkeypatch):
        """Non-numeric IRIS_PORT raises BackendConfigurationError."""
        from m2py.runtime.backend_config import IRISConfig
        from m2py.runtime.backend_exceptions import BackendConfigurationError

        monkeypatch.setenv("IRIS_PORT", "not_a_number")
        with pytest.raises(BackendConfigurationError, match="IRIS_PORT"):
            IRISConfig.from_env()

    def test_iris_config_port_out_of_range(self, monkeypatch):
        """Port number out of range raises BackendConfigurationError."""
        from m2py.runtime.backend_config import IRISConfig
        from m2py.runtime.backend_exceptions import BackendConfigurationError

        monkeypatch.setenv("IRIS_PORT", "99999")
        with pytest.raises(BackendConfigurationError, match="IRIS_PORT"):
            IRISConfig.from_env()

    def test_yottadb_config_defaults(self, monkeypatch):
        """YottaDB config reads ydb_dist from environment."""
        from m2py.runtime.backend_config import YottaDBConfig

        monkeypatch.delenv("ydb_dist", raising=False)
        config = YottaDBConfig.from_env()
        assert config.ydb_dist is None

    def test_yottadb_config_from_env(self, monkeypatch):
        """YottaDB config reads ydb_dist from environment."""
        from m2py.runtime.backend_config import YottaDBConfig

        monkeypatch.setenv("ydb_dist", "/opt/yottadb")
        config = YottaDBConfig.from_env()
        assert config.ydb_dist == "/opt/yottadb"

    def test_backend_switching_via_env(self, monkeypatch):
        """Setting M2PY_GLOBAL_BACKEND selects correct backend."""
        from m2py.runtime import get_global_storage
        from m2py.runtime.globals import InMemoryGlobalStorage

        monkeypatch.setenv("M2PY_GLOBAL_BACKEND", "inmemory")
        b = get_global_storage()
        assert isinstance(b, InMemoryGlobalStorage)

    def test_unknown_backend_error_message(self):
        """Unknown backend includes valid options in error."""
        from m2py.runtime import get_global_storage

        with pytest.raises(ValueError, match="inmemory.*sqlite.*yottadb.*iris"):
            get_global_storage("bogus")

    def test_error_messages_have_guidance(self):
        """BackendConfigurationError messages include actionable guidance."""
        from m2py.runtime.backend_exceptions import BackendConfigurationError

        # Verify the error preserves messages
        err = BackendConfigurationError(
            "Missing IRIS_PASSWORD. Set via: export IRIS_PASSWORD=<password>"
        )
        assert "IRIS_PASSWORD" in str(err)
        assert "export" in str(err)
