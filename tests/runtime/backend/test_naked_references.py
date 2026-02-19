"""Tests for naked reference tracking across all backends.

Covers: naked indicator get/set, resolve_naked, $ZREFERENCE tracking.
"""

from __future__ import annotations

import pytest


class TestNakedIndicator:
    """Test naked indicator tracking."""

    def test_initial_state_is_none(self, backend):
        assert backend.get_naked_indicator() is None

    def test_set_updates_naked(self, backend):
        backend.set("TEST", ("1", "2"), "value")
        naked = backend.get_naked_indicator()
        assert naked is not None
        assert naked[0] == "TEST"
        assert naked[1] == ("1",)

    def test_get_updates_naked(self, backend):
        backend.set("TEST", ("1", "2"), "value")
        # Reset naked
        backend.set("OTHER", ("x",), "other")
        # Now get should update naked
        backend.get("TEST", ("1", "2"))
        naked = backend.get_naked_indicator()
        assert naked is not None
        assert naked[0] == "TEST"
        assert naked[1] == ("1",)

    def test_kill_updates_naked(self, backend):
        backend.set("TEST", ("1", "2"), "value")
        backend.kill("TEST", ("1", "2"))
        naked = backend.get_naked_indicator()
        assert naked is not None
        assert naked[0] == "TEST"
        assert naked[1] == ("1",)

    def test_no_subscripts_clears_naked(self, backend):
        """Accessing ^G (no subscripts) sets naked to None."""
        backend.set("TEST", ("1",), "value")
        naked = backend.get_naked_indicator()
        assert naked is not None
        backend.set("TEST", (), "root")
        naked = backend.get_naked_indicator()
        assert naked is None

    def test_set_naked_indicator_explicit(self, backend):
        backend.set_naked_indicator("TEST", ("a", "b"))
        naked = backend.get_naked_indicator()
        assert naked == ("TEST", ("a", "b"))


class TestResolveNaked:
    """Test naked reference resolution."""

    def test_resolve_naked(self, backend):
        backend.set("TEST", ("1", "2", "3"), "value")
        # After ^TEST(1,2,3): naked = ("TEST", ("1","2"))
        name, subs = backend.resolve_naked(("4",))
        assert name == "TEST"
        assert subs == ("1", "2", "4")

    def test_resolve_naked_no_prior_access(self, backend):
        """Resolving naked without prior access raises error."""
        with pytest.raises(RuntimeError, match="NAKEDERR"):
            backend.resolve_naked(("1",))

    def test_resolve_naked_after_no_subscripts(self, backend):
        """After ^G (no subs), naked is None, resolve should fail."""
        backend.set("TEST", (), "value")
        with pytest.raises(RuntimeError, match="NAKEDERR"):
            backend.resolve_naked(("1",))


class TestLastGlobalRef:
    """Test $ZREFERENCE tracking."""

    def test_set_updates_ref(self, backend):
        backend.set("TEST", ("1", "2"), "value")
        ref = backend.last_global_ref
        assert "TEST" in ref
        assert "1" in ref

    def test_ref_changes_on_access(self, backend):
        backend.set("TEST", ("1",), "value")
        ref1 = backend.last_global_ref
        backend.set("OTHER", ("2",), "value2")
        ref2 = backend.last_global_ref
        assert ref1 != ref2
        assert "OTHER" in ref2
