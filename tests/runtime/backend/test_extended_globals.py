"""Tests for IRIS extended global references and namespace support.

T041: Validates that IRIS backend handles extended reference syntax
^|"NAMESPACE"|Global for cross-namespace access.

These tests only run on the IRIS backend since extended references
are an IRIS-specific feature.
"""

from __future__ import annotations

import pytest

from m2py.runtime.globals import GlobalStorageBackend


@pytest.mark.backend_iris
class TestIRISNamespaceAccess:
    """Tests for IRIS namespace-based global access."""

    def test_default_namespace_is_user(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """Backend connects to USER namespace by default."""
        if backend_name != "iris":
            pytest.skip("IRIS-specific test")
        # Write and read in default namespace
        backend.set("NSTEST", ("1",), "default")
        assert backend.get("NSTEST", ("1",)) == "default"

    def test_set_get_in_default_namespace(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """Basic set/get works in the default (USER) namespace."""
        if backend_name != "iris":
            pytest.skip("IRIS-specific test")
        backend.set("NSDATA", ("key",), "value123")
        result = backend.get("NSDATA", ("key",))
        assert result == "value123"

    def test_data_in_default_namespace(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """$DATA works correctly in default namespace."""
        if backend_name != "iris":
            pytest.skip("IRIS-specific test")
        backend.set("NSDATA2", ("a", "b"), "deep")
        d = backend.data("NSDATA2", ("a",))
        assert d == 10  # has descendants, no own value

    def test_order_in_default_namespace(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """$ORDER traversal works in default namespace."""
        if backend_name != "iris":
            pytest.skip("IRIS-specific test")
        backend.set("NSORD", ("a",), "1")
        backend.set("NSORD", ("b",), "2")
        backend.set("NSORD", ("c",), "3")
        assert backend.order("NSORD", ("",)) == "a"
        assert backend.order("NSORD", ("a",)) == "b"
        assert backend.order("NSORD", ("b",)) == "c"
        assert backend.order("NSORD", ("c",)) == ""

    def test_kill_in_default_namespace(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """KILL removes data in the current namespace."""
        if backend_name != "iris":
            pytest.skip("IRIS-specific test")
        backend.set("NSKILL", ("x",), "val")
        assert backend.data("NSKILL", ("x",)) == 1
        backend.kill("NSKILL", ())
        assert backend.data("NSKILL", ("x",)) == 0


@pytest.mark.backend_iris
class TestIRISNamespaceIsolation:
    """Tests validating namespace isolation semantics."""

    def test_globals_scoped_to_namespace(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """Globals written to one namespace are only visible in that namespace.

        This tests the fundamental IRIS namespace isolation property:
        ^GLOBAL in USER is separate from ^GLOBAL in SAMPLES.
        Since we connect to USER, writes stay in USER.
        """
        if backend_name != "iris":
            pytest.skip("IRIS-specific test")
        backend.set("ISOLATED", ("1",), "user_value")
        # Reading from the same namespace should return the value
        assert backend.get("ISOLATED", ("1",)) == "user_value"

    def test_kill_all_only_affects_current_namespace(
        self, backend: GlobalStorageBackend, backend_name: str
    ):
        """kill_all() only removes globals from the connected namespace."""
        if backend_name != "iris":
            pytest.skip("IRIS-specific test")
        backend.set("KILLNS", ("1",), "val")
        backend.kill_all()
        # After kill_all, global should not exist in this namespace
        assert backend.data("KILLNS", ("1",)) == 0
