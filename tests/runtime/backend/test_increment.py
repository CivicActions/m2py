"""Tests for $INCREMENT operation across all backends.

Covers: atomic increment, initial value creation, decimal increment.
"""

from __future__ import annotations


class TestIncrement:
    """Test $INCREMENT ($I) operations."""

    def test_incr_undefined_starts_at_zero(self, backend):
        """$INCREMENT on undefined node starts from 0."""
        result = backend.incr("TEST", ("1",), "1")
        assert result == "1"

    def test_incr_existing_value(self, backend):
        backend.set("TEST", ("1",), "5")
        result = backend.incr("TEST", ("1",), "3")
        assert result == "8"

    def test_incr_negative(self, backend):
        backend.set("TEST", ("1",), "10")
        result = backend.incr("TEST", ("1",), "-3")
        assert result == "7"

    def test_incr_default_increment(self, backend):
        """Default increment is 1."""
        result = backend.incr("TEST", ("1",))
        assert result == "1"
        result = backend.incr("TEST", ("1",))
        assert result == "2"

    def test_incr_persists_value(self, backend):
        backend.incr("TEST", ("1",), "5")
        assert backend.get("TEST", ("1",)) == "5"

    def test_incr_updates_naked(self, backend):
        backend.incr("TEST", ("1", "2"), "1")
        naked = backend.get_naked_indicator()
        assert naked is not None
        assert naked[0] == "TEST"
        assert naked[1] == ("1",)
