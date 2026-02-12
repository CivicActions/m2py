"""Unit tests for namespace-aware global operations (extended globals).

Spec 021 Phase 15: Tests for _ns_name(), set_ns(), get_ns(), data_ns(),
order_ns(), kill_ns(), query_ns() methods in InMemoryGlobalStorage.
"""

import pytest

from m2py.runtime.globals import InMemoryGlobalStorage


@pytest.fixture
def storage():
    """Create a fresh InMemoryGlobalStorage instance."""
    return InMemoryGlobalStorage()


class TestNsName:
    """Tests for _ns_name() helper that creates namespace-prefixed keys."""

    def test_empty_namespace_returns_name(self, storage):
        assert storage._ns_name("GLO", "") == "GLO"

    def test_namespace_prefixes_name(self, storage):
        assert storage._ns_name("GLO", "MYNS") == "MYNS:GLO"

    def test_different_namespaces_different_keys(self, storage):
        k1 = storage._ns_name("X", "NS1")
        k2 = storage._ns_name("X", "NS2")
        assert k1 != k2


class TestSetGetNs:
    """Tests for set_ns() and get_ns() methods."""

    def test_set_and_get_basic(self, storage):
        """Set and get a value in a namespace."""
        storage.set_ns("GLO", (), "hello", namespace="MYNS")
        assert storage.get_ns("GLO", (), namespace="MYNS") == "hello"

    def test_namespace_isolation(self, storage):
        """Values in different namespaces are isolated."""
        storage.set_ns("GLO", (), "ns1val", namespace="NS1")
        storage.set_ns("GLO", (), "ns2val", namespace="NS2")
        assert storage.get_ns("GLO", (), namespace="NS1") == "ns1val"
        assert storage.get_ns("GLO", (), namespace="NS2") == "ns2val"

    def test_namespace_isolated_from_default(self, storage):
        """Namespace values don't interfere with default namespace."""
        storage.set("GLO", (), "default")
        storage.set_ns("GLO", (), "ns1val", namespace="NS1")
        assert storage.get("GLO", ()) == "default"
        assert storage.get_ns("GLO", (), namespace="NS1") == "ns1val"

    def test_subscripted_set_get(self, storage):
        """Set and get with subscripts in namespace."""
        storage.set_ns("GLO", ("1",), "val1", namespace="MYNS")
        storage.set_ns("GLO", ("2",), "val2", namespace="MYNS")
        assert storage.get_ns("GLO", ("1",), namespace="MYNS") == "val1"
        assert storage.get_ns("GLO", ("2",), namespace="MYNS") == "val2"

    def test_empty_namespace_is_default(self, storage):
        """Empty namespace routes to default storage."""
        storage.set("GLO", (), "default")
        assert storage.get_ns("GLO", (), namespace="") == "default"

    def test_get_undefined_returns_none(self, storage):
        """Getting undefined namespace variable returns None."""
        assert storage.get_ns("GLO", (), namespace="MYNS") is None


class TestDataNs:
    """Tests for data_ns() - $DATA for namespace-qualified globals."""

    def test_defined_value_returns_1(self, storage):
        storage.set_ns("X", (), "hello", namespace="NS1")
        assert storage.data_ns("X", (), namespace="NS1") == 1

    def test_undefined_returns_0(self, storage):
        assert storage.data_ns("X", (), namespace="NS1") == 0

    def test_has_children_returns_10(self, storage):
        storage.set_ns("X", ("1",), "child", namespace="NS1")
        assert storage.data_ns("X", (), namespace="NS1") == 10

    def test_value_and_children_returns_11(self, storage):
        storage.set_ns("X", (), "root", namespace="NS1")
        storage.set_ns("X", ("1",), "child", namespace="NS1")
        assert storage.data_ns("X", (), namespace="NS1") == 11


class TestOrderNs:
    """Tests for order_ns() - $ORDER for namespace-qualified globals."""

    def test_order_forward(self, storage):
        storage.set_ns("X", ("a",), "1", namespace="NS")
        storage.set_ns("X", ("b",), "2", namespace="NS")
        storage.set_ns("X", ("c",), "3", namespace="NS")
        assert storage.order_ns("X", ("",), direction=1, namespace="NS") == "a"
        assert storage.order_ns("X", ("a",), direction=1, namespace="NS") == "b"
        assert storage.order_ns("X", ("b",), direction=1, namespace="NS") == "c"
        assert storage.order_ns("X", ("c",), direction=1, namespace="NS") == ""

    def test_order_reverse(self, storage):
        storage.set_ns("X", ("a",), "1", namespace="NS")
        storage.set_ns("X", ("b",), "2", namespace="NS")
        assert storage.order_ns("X", ("",), direction=-1, namespace="NS") == "b"
        assert storage.order_ns("X", ("b",), direction=-1, namespace="NS") == "a"

    def test_order_isolated_from_other_ns(self, storage):
        storage.set_ns("X", ("a",), "1", namespace="NS1")
        storage.set_ns("X", ("b",), "2", namespace="NS2")
        # NS1 only has "a"
        assert storage.order_ns("X", ("",), direction=1, namespace="NS1") == "a"
        assert storage.order_ns("X", ("a",), direction=1, namespace="NS1") == ""


class TestKillNs:
    """Tests for kill_ns() - KILL for namespace-qualified globals."""

    def test_kill_entire_global(self, storage):
        storage.set_ns("X", (), "root", namespace="NS")
        storage.set_ns("X", ("1",), "child", namespace="NS")
        storage.kill_ns("X", (), namespace="NS")
        assert storage.data_ns("X", (), namespace="NS") == 0

    def test_kill_subscript(self, storage):
        storage.set_ns("X", (), "root", namespace="NS")
        storage.set_ns("X", ("1",), "child", namespace="NS")
        storage.kill_ns("X", ("1",), namespace="NS")
        assert storage.data_ns("X", (), namespace="NS") == 1
        assert storage.data_ns("X", ("1",), namespace="NS") == 0

    def test_kill_does_not_affect_other_ns(self, storage):
        storage.set_ns("X", (), "val1", namespace="NS1")
        storage.set_ns("X", (), "val2", namespace="NS2")
        storage.kill_ns("X", (), namespace="NS1")
        assert storage.data_ns("X", (), namespace="NS1") == 0
        assert storage.get_ns("X", (), namespace="NS2") == "val2"


class TestQueryNs:
    """Tests for query_ns() - $QUERY for namespace-qualified globals."""

    def test_query_traversal(self, storage):
        storage.set_ns("X", ("a",), "1", namespace="NS")
        storage.set_ns("X", ("b",), "2", namespace="NS")
        # $QUERY from ("",) should return first node
        result = storage.query_ns("X", ("",), direction=1, namespace="NS")
        assert result != ""
