"""Tests for $INCREMENT runtime helpers and global storage.

Tests the runtime-level functions for $INCREMENT:
- m_increment: Local variable increment
- m_increment_global: Global variable increment
- InMemoryGlobalStorage.incr: Backend-level atomic increment
- InMemoryGlobalStorage.kill_all: Global reset (also restored)
"""

import pytest

from m2py.runtime import MArray
from m2py.runtime.helpers import m_increment, m_increment_global
from m2py.runtime.globals import InMemoryGlobalStorage


# =========================================================================
# m_increment — local variable helper
# =========================================================================


@pytest.mark.runtime
class TestMIncrementUndefined:
    """m_increment behavior with undefined variables."""

    def test_undefined_with_scope(self):
        """Undefined variable is created in scope and incremented from 0."""
        scope = {}
        result = m_increment(None, (), "1", scope=scope, var_name="X")
        assert result == "1"
        # Variable should now exist in scope
        assert "X" in scope
        assert scope["X"]._value == "1"

    def test_undefined_without_scope(self):
        """Undefined variable without scope returns increment value."""
        result = m_increment(None, (), "1")
        assert result == "1"

    def test_undefined_custom_increment(self):
        """Undefined var treated as 0, incremented by custom amount."""
        scope = {}
        result = m_increment(None, (), "5", scope=scope, var_name="X")
        assert result == "5"
        assert scope["X"]._value == "5"


@pytest.mark.runtime
class TestMIncrementDefined:
    """m_increment on defined local variables."""

    def test_simple_increment(self):
        """Basic increment by 1."""
        arr = MArray()
        arr._value = "10"
        result = m_increment(arr, (), "1")
        assert result == "11"
        assert arr._value == "11"

    def test_custom_increment(self):
        """Increment by custom amount."""
        arr = MArray()
        arr._value = "5"
        result = m_increment(arr, (), "3")
        assert result == "8"
        assert arr._value == "8"

    def test_negative_increment(self):
        """Negative increment (decrement)."""
        arr = MArray()
        arr._value = "10"
        result = m_increment(arr, (), "-3")
        assert result == "7"
        assert arr._value == "7"

    def test_decimal_increment(self):
        """Decimal increment."""
        arr = MArray()
        arr._value = "0"
        result = m_increment(arr, (), "2.5")
        assert result == "2.5"
        assert arr._value == "2.5"

    def test_zero_increment(self):
        """Zero increment returns current value."""
        arr = MArray()
        arr._value = "42"
        result = m_increment(arr, (), "0")
        assert result == "42"
        assert arr._value == "42"

    def test_nonnumeric_string(self):
        """Non-numeric string treated as 0 before incrementing."""
        arr = MArray()
        arr._value = "abc"
        result = m_increment(arr, (), "1")
        assert result == "1"
        assert arr._value == "1"

    def test_numeric_leading_string(self):
        """String starting with number — MUMPS extracts leading numeric."""
        arr = MArray()
        arr._value = "3abc"
        result = m_increment(arr, (), "1")
        assert result == "4"
        assert arr._value == "4"

    def test_multiple_increments(self):
        """Multiple increments accumulate."""
        arr = MArray()
        arr._value = "0"
        m_increment(arr, (), "1")
        m_increment(arr, (), "1")
        result = m_increment(arr, (), "1")
        assert result == "3"
        assert arr._value == "3"


@pytest.mark.runtime
class TestMIncrementSubscripted:
    """m_increment on subscripted local variables."""

    def test_subscript_creates_path(self):
        """Creates subscript path if not existing."""
        arr = MArray()
        result = m_increment(arr, ("1", "2"), "1")
        assert result == "1"
        # Verify the subscript tree was created
        assert "1" in arr._children
        assert "2" in arr._children["1"]._children
        assert arr._children["1"]._children["2"]._value == "1"

    def test_subscript_existing(self):
        """Increment existing subscripted value."""
        arr = MArray()
        child1 = MArray()
        child2 = MArray()
        child2._value = "5"
        child1._children["2"] = child2
        arr._children["1"] = child1
        result = m_increment(arr, ("1", "2"), "10")
        assert result == "15"

    def test_parent_value_preserved(self):
        """Incrementing subscripted node doesn't affect parent."""
        arr = MArray()
        arr._value = "root"
        m_increment(arr, ("1",), "1")
        assert arr._value == "root"
        assert arr._children["1"]._value == "1"


# =========================================================================
# InMemoryGlobalStorage.incr
# =========================================================================


@pytest.mark.runtime
class TestGlobalStorageIncr:
    """Tests for InMemoryGlobalStorage.incr method."""

    def test_incr_undefined(self):
        """Increment undefined global — treated as 0."""
        backend = InMemoryGlobalStorage()
        result = backend.incr("G", ())
        assert result == "1"
        assert backend.get("G", ()) == "1"

    def test_incr_defined(self):
        """Increment defined global."""
        backend = InMemoryGlobalStorage()
        backend.set("G", (), "10")
        result = backend.incr("G", (), "1")
        assert result == "11"
        assert backend.get("G", ()) == "11"

    def test_incr_custom_amount(self):
        """Increment by custom amount."""
        backend = InMemoryGlobalStorage()
        backend.set("G", (), "5")
        result = backend.incr("G", (), "3")
        assert result == "8"

    def test_incr_negative(self):
        """Increment by negative amount (decrement)."""
        backend = InMemoryGlobalStorage()
        backend.set("G", (), "10")
        result = backend.incr("G", (), "-3")
        assert result == "7"

    def test_incr_subscripted(self):
        """Increment subscripted global."""
        backend = InMemoryGlobalStorage()
        backend.set("G", ("1", "2"), "5")
        result = backend.incr("G", ("1", "2"), "10")
        assert result == "15"

    def test_incr_nonnumeric(self):
        """Increment non-numeric global value."""
        backend = InMemoryGlobalStorage()
        backend.set("G", (), "abc")
        result = backend.incr("G", (), "1")
        assert result == "1"

    def test_incr_updates_naked_indicator(self):
        """Incr updates the naked indicator for naked global references."""
        backend = InMemoryGlobalStorage()
        backend.incr("G", ("1",))
        naked = backend.get_naked_indicator()
        # After ^G(1): naked indicator = ("G", ()) — last subscript stripped
        assert naked[0] == "G"
        assert naked[1] == ()

    def test_incr_default_increment(self):
        """Default increment is 1."""
        backend = InMemoryGlobalStorage()
        result = backend.incr("G", ())
        assert result == "1"
        result = backend.incr("G", ())
        assert result == "2"


# =========================================================================
# InMemoryGlobalStorage.kill_all
# =========================================================================


@pytest.mark.runtime
class TestGlobalStorageKillAll:
    """Tests for InMemoryGlobalStorage.kill_all method."""

    def test_kill_all_clears_data(self):
        """kill_all removes all global data."""
        backend = InMemoryGlobalStorage()
        backend.set("G", (), "1")
        backend.set("H", ("1",), "2")
        backend.kill_all()
        assert backend.get("G", ()) is None
        assert backend.get("H", ("1",)) is None

    def test_kill_all_resets_naked(self):
        """kill_all clears the naked indicator."""
        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "value")
        backend.kill_all()
        naked = backend.get_naked_indicator()
        # kill_all calls _update_naked_indicator("", ()) → None (no subscripts)
        assert naked is None

    def test_kill_all_empty_is_noop(self):
        """kill_all on empty storage doesn't error."""
        backend = InMemoryGlobalStorage()
        backend.kill_all()  # Should not raise


# =========================================================================
# m_increment_global — delegation helper
# =========================================================================


@pytest.mark.runtime
class TestMIncrementGlobal:
    """Tests for m_increment_global helper function."""

    def test_delegates_to_backend(self):
        """m_increment_global delegates to backend.incr()."""
        backend = InMemoryGlobalStorage()
        result = m_increment_global(backend, "G", (), "1")
        assert result == "1"
        assert backend.get("G", ()) == "1"

    def test_subscripted_global(self):
        """m_increment_global handles subscripted globals."""
        backend = InMemoryGlobalStorage()
        backend.set("G", ("1",), "5")
        result = m_increment_global(backend, "G", ("1",), "10")
        assert result == "15"

    def test_custom_increment(self):
        """m_increment_global with custom increment."""
        backend = InMemoryGlobalStorage()
        result = m_increment_global(backend, "G", (), "42")
        assert result == "42"
