"""Tests for global storage backend configuration.

Spec 009 Phase 9: User Story 7 - Global Storage Backend Configuration

Tests backend selection via:
- M2PY_GLOBAL_BACKEND environment variable
- MUMPSRuntime(global_storage=...) programmatic API

Acceptance Scenarios from spec.md:
1. M2PY_GLOBAL_BACKEND=inmemory → InMemoryGlobalStorage used
2. MUMPSRuntime(global_storage=...) → programmatic backend used
3. No configuration → InMemoryGlobalStorage (default)
4. M2PY_GLOBAL_BACKEND=yottadb (not installed) → ImportError with message
"""

import pytest


@pytest.mark.runtime
class TestBackendEnvVar:
    """Test M2PY_GLOBAL_BACKEND environment variable configuration."""

    def test_inmemory_backend_explicit(self, monkeypatch):
        """Scenario 1: M2PY_GLOBAL_BACKEND=inmemory selects InMemoryGlobalStorage."""
        from m2py.runtime import get_global_storage, InMemoryGlobalStorage

        monkeypatch.setenv("M2PY_GLOBAL_BACKEND", "inmemory")
        backend = get_global_storage()
        assert isinstance(backend, InMemoryGlobalStorage)

    def test_default_backend_inmemory(self, monkeypatch):
        """Scenario 3: No configuration defaults to InMemoryGlobalStorage."""
        from m2py.runtime import get_global_storage, InMemoryGlobalStorage

        # Remove env var if set
        monkeypatch.delenv("M2PY_GLOBAL_BACKEND", raising=False)
        backend = get_global_storage()
        assert isinstance(backend, InMemoryGlobalStorage)

    def test_yottadb_backend_not_installed(self, monkeypatch):
        """Scenario 4: M2PY_GLOBAL_BACKEND=yottadb raises ImportError."""
        from m2py.runtime import get_global_storage

        monkeypatch.setenv("M2PY_GLOBAL_BACKEND", "yottadb")
        with pytest.raises(ImportError) as exc_info:
            get_global_storage()
        assert "YottaDB" in str(exc_info.value)

    def test_iris_backend_not_installed(self, monkeypatch):
        """IRIS backend raises ImportError when not installed."""
        from m2py.runtime import get_global_storage

        monkeypatch.setenv("M2PY_GLOBAL_BACKEND", "iris")
        with pytest.raises(ImportError) as exc_info:
            get_global_storage()
        assert "IRIS" in str(exc_info.value)

    def test_unknown_backend_raises_value_error(self, monkeypatch):
        """Unknown backend name raises ValueError with valid options."""
        from m2py.runtime import get_global_storage

        monkeypatch.setenv("M2PY_GLOBAL_BACKEND", "unknown")
        with pytest.raises(ValueError) as exc_info:
            get_global_storage()
        assert "Unknown" in str(exc_info.value)
        assert "inmemory" in str(exc_info.value)

    def test_case_insensitive_backend_name(self, monkeypatch):
        """Backend names are case-insensitive."""
        from m2py.runtime import get_global_storage, InMemoryGlobalStorage

        monkeypatch.setenv("M2PY_GLOBAL_BACKEND", "INMEMORY")
        backend = get_global_storage()
        assert isinstance(backend, InMemoryGlobalStorage)


@pytest.mark.runtime
class TestBackendProgrammaticAPI:
    """Test MUMPSRuntime(global_storage=...) programmatic configuration."""

    def test_explicit_backend_parameter(self):
        """Scenario 2: MUMPSRuntime(global_storage=...) uses provided backend."""
        from m2py.runtime import MUMPSRuntime, InMemoryGlobalStorage

        custom_backend = InMemoryGlobalStorage()
        rt = MUMPSRuntime(global_storage=custom_backend)
        assert rt.globals is custom_backend

    def test_default_uses_factory(self, monkeypatch):
        """MUMPSRuntime without global_storage uses get_global_storage()."""
        from m2py.runtime import MUMPSRuntime, InMemoryGlobalStorage

        monkeypatch.delenv("M2PY_GLOBAL_BACKEND", raising=False)
        rt = MUMPSRuntime()
        assert isinstance(rt.globals, InMemoryGlobalStorage)


@pytest.mark.runtime
class TestBackendFactoryFunction:
    """Test get_global_storage() factory function directly."""

    def test_explicit_parameter_overrides_env(self, monkeypatch):
        """Explicit backend parameter takes precedence over env var."""
        from m2py.runtime import get_global_storage, InMemoryGlobalStorage

        # Set env to something that would fail
        monkeypatch.setenv("M2PY_GLOBAL_BACKEND", "yottadb")
        # But explicit parameter should override
        backend = get_global_storage("inmemory")
        assert isinstance(backend, InMemoryGlobalStorage)

    def test_factory_returns_new_instance_each_call(self):
        """Each call to get_global_storage() returns a new instance."""
        from m2py.runtime import get_global_storage

        backend1 = get_global_storage("inmemory")
        backend2 = get_global_storage("inmemory")
        assert backend1 is not backend2


@pytest.mark.runtime
class TestInMemoryGlobalStorageProtocol:
    """Test protocol methods on InMemoryGlobalStorage (T062-T066)."""

    def test_order_stub_returns_empty(self):
        """order() stub returns empty string."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "A")
        result = backend.order("G", ("1",))
        assert result == ""

    def test_query_stub_returns_empty(self):
        """query() stub returns empty string."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "A")
        result = backend.query("G", ("1",))
        assert result == ""

    def test_incr_increments_undefined_value(self):
        """incr() treats undefined value as 0."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        result = backend.incr("G", ("1",))
        assert result == "1"
        assert backend.get("G", ("1",)) == "1"

    def test_incr_increments_existing_value(self):
        """incr() adds to existing numeric value."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "5")
        result = backend.incr("G", ("1",), "3")
        assert result == "8"

    def test_kill_node_preserves_descendants(self):
        """kill_node() removes value but keeps children."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "parent")
        backend.set("G", ("1", "2"), "child")

        # $D before kill_node
        assert backend.data("G", ("1",)) == 11  # value + children

        backend.kill_node("G", ("1",))

        # $D after kill_node - should still have children
        assert backend.data("G", ("1",)) == 10  # no value, has children
        assert backend.get("G", ("1", "2")) == "child"


@pytest.mark.runtime
class TestBackendStubClasses:
    """Test YottaDBGlobalStorage and IRISGlobalStorage stub classes (T067-T068)."""

    def test_yottadb_stub_raises_import_error(self):
        """YottaDBGlobalStorage raises ImportError when yottadb package missing."""
        from m2py.runtime.globals import YottaDBGlobalStorage

        with pytest.raises(ImportError) as exc_info:
            YottaDBGlobalStorage()
        assert "yottadb" in str(exc_info.value).lower()

    def test_iris_stub_raises_import_error(self):
        """IRISGlobalStorage raises ImportError when iris package missing."""
        from m2py.runtime.globals import IRISGlobalStorage

        with pytest.raises(ImportError) as exc_info:
            IRISGlobalStorage()
        assert "iris" in str(exc_info.value).lower()


@pytest.mark.runtime
class TestInMemoryGlobalStorageEdgeCases:
    """Additional tests for InMemoryGlobalStorage edge cases."""

    def test_incr_with_float_values(self):
        """incr() handles float values correctly."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "1.5")
        result = backend.incr("G", ("1",), "2.5")
        # 1.5 + 2.5 = 4.0, but whole numbers are converted to int
        assert result == "4"

    def test_incr_with_non_numeric_value(self):
        """incr() treats non-numeric as 0."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "ABC")
        result = backend.incr("G", ("1",), "5")
        # Non-numeric treated as 0, so result is just the increment
        assert result == "5"

    def test_kill_node_nonexistent_global(self):
        """kill_node() on nonexistent global does nothing."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        # Should not raise
        backend.kill_node("NONEXISTENT", ("1",))

    def test_kill_node_nonexistent_path(self):
        """kill_node() on nonexistent path does nothing."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "value")
        # Path (1, 2, 3) doesn't exist
        backend.kill_node("G", ("1", "2", "3"))
        # Original value should be unchanged
        assert backend.get("G", ("1",)) == "value"

    def test_kill_node_at_root(self):
        """kill_node() at root removes value but keeps children."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("G", (), "root_value")
        backend.set("G", ("1",), "child")

        backend.kill_node("G", ())

        assert backend.get("G", ()) is None
        assert backend.get("G", ("1",)) == "child"

    def test_order_updates_naked_indicator(self):
        """order() updates naked indicator."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "A")
        backend.order("G", ("1", "2"))

        indicator = backend.get_naked_indicator()
        assert indicator is not None
        assert indicator[0] == "G"

    def test_query_updates_naked_indicator(self):
        """query() updates naked indicator."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "A")
        backend.query("G", ("1", "2"))

        indicator = backend.get_naked_indicator()
        assert indicator is not None
        assert indicator[0] == "G"


@pytest.mark.runtime
class TestInMemoryGlobalStorageGetTree:
    """Tests for get_tree() method used by MERGE command."""

    def test_get_tree_returns_marray(self):
        """get_tree() returns an MArray with subtree contents."""
        from m2py.runtime import InMemoryGlobalStorage, MArray

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "value1")
        backend.set("G", ("2",), "value2")

        result = backend.get_tree("G", ())
        assert isinstance(result, MArray)
        assert result.get(1) == "value1"
        assert result.get(2) == "value2"

    def test_get_tree_nonexistent_returns_none(self):
        """get_tree() returns None for nonexistent global."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        result = backend.get_tree("NONEXISTENT", ())
        assert result is None

    def test_get_tree_nonexistent_subscript_returns_none(self):
        """get_tree() returns None for nonexistent subscript path."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "value")
        result = backend.get_tree("G", ("2", "3"))
        assert result is None

    def test_get_tree_with_subscripts(self):
        """get_tree() can get a subtree at a subscripted path."""
        from m2py.runtime import InMemoryGlobalStorage, MArray

        backend = InMemoryGlobalStorage()
        backend.set("G", ("A", "1"), "v1")
        backend.set("G", ("A", "2"), "v2")
        backend.set("G", ("B", "1"), "other")

        result = backend.get_tree("G", ("A",))
        assert isinstance(result, MArray)
        assert result.get(1) == "v1"
        assert result.get(2) == "v2"

    def test_get_tree_preserves_nested_structure(self):
        """get_tree() deep copies nested subscripts."""
        from m2py.runtime import InMemoryGlobalStorage, MArray

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1", "A"), "nested")

        result = backend.get_tree("G", ("1",))
        assert isinstance(result, MArray)
        assert result.get("A") == "nested"

    def test_get_tree_converts_numeric_string_keys(self):
        """get_tree() converts numeric string keys to int/float."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "int_key")
        backend.set("G", ("1.5",), "float_key")
        backend.set("G", ("text",), "string_key")

        result = backend.get_tree("G", ())
        # Access using numeric keys (should work for numeric strings)
        assert result.get(1) == "int_key"
        assert result.get(1.5) == "float_key"
        assert result.get("text") == "string_key"

    def test_get_tree_updates_naked_indicator(self):
        """get_tree() updates the naked indicator."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "value")
        backend.get_tree("G", ("1",))

        indicator = backend.get_naked_indicator()
        assert indicator is not None
        assert indicator[0] == "G"


@pytest.mark.runtime
class TestLockOperations:
    """Test LOCK operations (Spec 013 FR-019)."""

    def test_lock_acquire(self):
        """Lock acquire returns True and increments count."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        result = backend.lock("PATIENT", ("123",), lock_type="+")
        assert result is True
        assert ("PATIENT", ("123",)) in backend._lock_table
        assert backend._lock_table[("PATIENT", ("123",))] == 1

    def test_lock_increment(self):
        """Multiple lock acquires increment the count."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.lock("PATIENT", ("123",), lock_type="+")
        backend.lock("PATIENT", ("123",), lock_type="+")
        assert backend._lock_table[("PATIENT", ("123",))] == 2

    def test_lock_decrement(self):
        """Lock release decrements the count."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.lock("PATIENT", ("123",), lock_type="+")
        backend.lock("PATIENT", ("123",), lock_type="+")
        backend.lock("PATIENT", ("123",), lock_type="-")
        assert backend._lock_table[("PATIENT", ("123",))] == 1

    def test_lock_release_removes_entry(self):
        """Lock release to 0 removes the entry."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.lock("PATIENT", ("123",), lock_type="+")
        backend.lock("PATIENT", ("123",), lock_type="-")
        assert ("PATIENT", ("123",)) not in backend._lock_table

    def test_unlock(self):
        """unlock() decrements lock count."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.lock("X", (), lock_type="+")
        backend.lock("X", (), lock_type="+")
        backend.unlock("X", ())
        assert backend._lock_table[("X", ())] == 1

    def test_unlock_all(self):
        """unlock_all() clears all locks."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.lock("A", (), lock_type="+")
        backend.lock("B", ("1",), lock_type="+")
        backend.lock("C", ("1", "2"), lock_type="+")
        backend.unlock_all()
        assert len(backend._lock_table) == 0


@pytest.mark.runtime
class TestTransactionOperations:
    """Test transaction operations (Spec 013 FR-015)."""

    def test_transaction_start_increments_tlevel(self):
        """TSTART increments $TLEVEL."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        assert backend.get_tlevel() == 0
        backend.transaction_start()
        assert backend.get_tlevel() == 1
        backend.transaction_start()
        assert backend.get_tlevel() == 2

    def test_transaction_commit_decrements_tlevel(self):
        """TCOMMIT decrements $TLEVEL."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.transaction_start()
        backend.transaction_start()
        backend.transaction_commit()
        assert backend.get_tlevel() == 1
        backend.transaction_commit()
        assert backend.get_tlevel() == 0

    def test_transaction_commit_without_tstart_raises(self):
        """TCOMMIT without TSTART raises M44 error."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        with pytest.raises(RuntimeError) as exc:
            backend.transaction_commit()
        assert "M44" in str(exc.value)

    def test_transaction_rollback_restores_state(self):
        """TROLLBACK restores global state."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("A", (), "1")
        backend.transaction_start()
        backend.set("A", (), "2")
        assert backend.get("A", ()) == "2"
        backend.transaction_rollback()
        assert backend.get("A", ()) == "1"

    def test_transaction_rollback_without_tstart_raises(self):
        """TROLLBACK without TSTART raises M44 error."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        with pytest.raises(RuntimeError) as exc:
            backend.transaction_rollback()
        assert "M44" in str(exc.value)

    def test_nested_transaction_commit(self):
        """Nested TCOMMIT only commits on outer level."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("A", (), "initial")
        backend.transaction_start()
        backend.set("A", (), "level1")
        backend.transaction_start()
        backend.set("A", (), "level2")
        backend.transaction_commit()  # Inner commit
        assert backend.get("A", ()) == "level2"  # Changes persisted
        assert backend.get_tlevel() == 1
        backend.transaction_commit()  # Outer commit
        assert backend.get_tlevel() == 0


@pytest.mark.runtime
class TestSSVNOperations:
    """Test SSVN operations (Spec 013 FR-029)."""

    def test_ssvn_global_exists(self):
        """^$GLOBAL returns '1' for existing globals."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.set("TEST", (), "value")
        assert backend.ssvn_global("TEST") == "1"

    def test_ssvn_global_not_exists(self):
        """^$GLOBAL returns '' for non-existent globals."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        assert backend.ssvn_global("NOTEXIST") == ""

    def test_ssvn_job_current_process(self):
        """^$JOB returns '1' for current process."""
        import os
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        assert backend.ssvn_job(str(os.getpid())) == "1"

    def test_ssvn_job_other_process(self):
        """^$JOB returns '' for other processes."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        assert backend.ssvn_job("99999") == ""

    def test_ssvn_lock_locked(self):
        """^$LOCK returns count for locked resource."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        backend.lock("TEST", (), lock_type="+")
        backend.lock("TEST", (), lock_type="+")
        assert backend.ssvn_lock("TEST") == "2"

    def test_ssvn_lock_unlocked(self):
        """^$LOCK returns '' for unlocked resource."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        assert backend.ssvn_lock("TEST") == ""

    def test_ssvn_routine(self):
        """^$ROUTINE returns '' (not implemented in memory backend)."""
        from m2py.runtime import InMemoryGlobalStorage

        backend = InMemoryGlobalStorage()
        assert backend.ssvn_routine("ANYNAME") == ""


@pytest.mark.runtime
class TestRuntimeTlevel:
    """Test $TLEVEL access via MUMPSRuntime."""

    def test_runtime_tlevel(self):
        """MUMPSRuntime.tlevel() delegates to backend."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt.tlevel() == 0
        rt._globals.transaction_start()
        assert rt.tlevel() == 1
        rt._globals.transaction_commit()
        assert rt.tlevel() == 0
