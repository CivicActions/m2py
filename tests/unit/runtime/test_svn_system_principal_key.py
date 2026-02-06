"""Tests for runtime $SYSTEM, $PRINCIPAL, $KEY methods.

Phase 23: Verify runtime methods for new special variables.
"""

import pytest

from m2py.runtime import MArray, MUMPSRuntime


@pytest.mark.runtime
class TestRuntimeSystemMethod:
    """Tests for runtime.system() method."""

    def test_system_returns_string(self):
        """system() returns a string."""
        rt = MUMPSRuntime()
        result = rt.system()
        assert isinstance(result, str)

    def test_system_format(self):
        """system() returns 'V,S' format with numeric V."""
        rt = MUMPSRuntime()
        result = rt.system()
        assert "," in result
        parts = result.split(",", 1)
        assert parts[0].isdigit()
        assert len(parts[1]) > 0

    def test_system_value(self):
        """system() returns '47,M2PY'."""
        rt = MUMPSRuntime()
        assert rt.system() == "47,M2PY"


@pytest.mark.runtime
class TestRuntimePrincipalMethod:
    """Tests for runtime.principal() method."""

    def test_principal_returns_string(self):
        """principal() returns a string."""
        rt = MUMPSRuntime()
        result = rt.principal()
        assert isinstance(result, str)

    def test_principal_default_value(self):
        """principal() returns '0' by default."""
        rt = MUMPSRuntime()
        assert rt.principal() == "0"

    def test_principal_equals_io(self):
        """principal() equals io() at process start."""
        rt = MUMPSRuntime()
        assert rt.principal() == rt.io()


@pytest.mark.runtime
class TestRuntimeKeyMethod:
    """Tests for runtime.key() method."""

    def test_key_returns_string(self):
        """key() returns a string."""
        rt = MUMPSRuntime()
        result = rt.key()
        assert isinstance(result, str)

    def test_key_default_empty(self):
        """key() returns empty string when no READ has occurred."""
        rt = MUMPSRuntime()
        assert rt.key() == ""


@pytest.mark.runtime
class TestRuntimeGetIndirectedMarray:
    """Tests for runtime.get_indirected_marray() method."""

    def test_get_indirected_marray_returns_marray(self):
        """get_indirected_marray() returns an MArray object."""

        rt = MUMPSRuntime()
        scope = {"X": MArray()}
        scope["X"].value = "hello"
        # IX contains the name "X"
        ix = MArray()
        ix.value = "X"
        scope["IX"] = ix
        result = rt.get_indirected_marray("IX", scope, levels=1)
        assert isinstance(result, MArray)

    def test_get_indirected_marray_shares_reference(self):
        """get_indirected_marray() returns same MArray object (not copy)."""

        rt = MUMPSRuntime()
        original = MArray()
        original.value = "value"
        original[1] = "sub1"
        ix = MArray()
        ix.value = "X"
        scope = {"X": original, "IX": ix}
        result = rt.get_indirected_marray("IX", scope, levels=1)
        assert result is original  # Same object, not a copy

    def test_get_indirected_marray_creates_new_if_missing(self):
        """get_indirected_marray() returns new MArray if variable not in scope."""

        rt = MUMPSRuntime()
        ix = MArray()
        ix.value = "Y"  # Points to Y, which doesn't exist
        scope = {"IX": ix}
        result = rt.get_indirected_marray("IX", scope, levels=1)
        # Returns a fresh MArray (default) since Y not in scope
        assert isinstance(result, MArray)
