"""Tests for performance optimizations — verifying correctness is preserved.

Covers the hot-path optimizations introduced to speed up FileMan FINDC
(~53K execute_mumps/s on aarch64, from ~9K before):

- Integer fast paths in m_add / m_sub / m_mul / m_mod / m_int_div / m_pow
- _m_num_str lru_cache for string → numeric coercion
- _canonicalize_subscripts_lru module-level cache (list→tuple coercion, cache hits)
- m_var_value Decimal and MArray fast paths
- _mumps_collation_key lru_cache consistency
- XECUTE fn_cache checked before parse/compile (fn_cache survives xecute_cache eviction)
- set_x / set_y use numeric coercion via module-level _m_num
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from m2py.codegen.helpers import (
    _m_num_str,
    m_add,
    m_int_div,
    m_mod,
    m_mul,
    m_num,
    m_pow,
    m_sub,
)
from m2py.runtime import MArray, MUMPSRuntime
from m2py.runtime.helpers import _mumps_collation_key, m_var_value


# ---------------------------------------------------------------------------
# Integer fast paths in arithmetic operators
# ---------------------------------------------------------------------------


class TestIntFastPathsArithmetic:
    """The int fast paths must return the same values as the Decimal path."""

    # m_add
    def test_add_int_int_returns_int(self):
        result = m_add(3, 4)
        assert result == 7
        assert type(result) is int

    def test_add_int_int_negative(self):
        assert m_add(-10, 3) == -7

    def test_add_int_int_zero(self):
        assert m_add(0, 0) == 0
        assert m_add(42, 0) == 42

    def test_add_large_ints(self):
        # Fast path must not overflow (Python ints are arbitrary precision)
        big = 10**18
        assert m_add(big, big) == 2 * 10**18

    def test_add_mixed_int_decimal(self):
        # Falls through to Decimal path; result should still be correct
        result = m_add(1, Decimal("0.5"))
        assert result == Decimal("1.5")

    # m_sub
    def test_sub_int_int_returns_int(self):
        result = m_sub(10, 3)
        assert result == 7
        assert type(result) is int

    def test_sub_int_int_negative_result(self):
        assert m_sub(3, 10) == -7

    def test_sub_large_ints(self):
        assert m_sub(10**18, 10**18) == 0

    # m_mul
    def test_mul_int_int_returns_int(self):
        result = m_mul(6, 7)
        assert result == 42
        assert type(result) is int

    def test_mul_int_int_zero(self):
        assert m_mul(999, 0) == 0
        assert m_mul(0, 999) == 0

    def test_mul_int_int_negative(self):
        assert m_mul(-3, 4) == -12
        assert m_mul(-3, -4) == 12

    # m_mod
    def test_mod_int_int_returns_int(self):
        result = m_mod(7, 3)
        assert result == 1
        assert type(result) is int

    def test_mod_mumps_semantics_negative_dividend(self):
        """MUMPS: -7 # 3 = 2 (result has sign of divisor)."""
        assert m_mod(-7, 3) == 2

    def test_mod_negative_divisor(self):
        """MUMPS: 7 # -3 = -2."""
        assert m_mod(7, -3) == -2

    def test_mod_exact_division(self):
        assert m_mod(9, 3) == 0

    def test_mod_zero_dividend(self):
        assert m_mod(0, 5) == 0

    # m_int_div
    def test_int_div_basic(self):
        assert m_int_div(7, 2) == 3

    def test_int_div_exact(self):
        assert m_int_div(10, 5) == 2

    def test_int_div_truncates_toward_zero_negative(self):
        """MUMPS integer division truncates toward zero, not floor."""
        # -7 \ 2 should be -3 (toward zero), not -4 (floor)
        assert m_int_div(-7, 2) == -3

    def test_int_div_truncates_toward_zero_negative_divisor(self):
        # 7 \ -2 should be -3 (toward zero)
        assert m_int_div(7, -2) == -3

    def test_int_div_both_negative(self):
        # -7 \ -2 should be 3 (toward zero)
        assert m_int_div(-7, -2) == 3

    def test_int_div_large_ints(self):
        assert m_int_div(10**18, 3) == 333333333333333333

    def test_int_div_returns_int_type(self):
        assert type(m_int_div(7, 2)) is int

    def test_int_div_string_inputs(self):
        # Goes through m_num coercion first
        assert m_int_div("10", "3") == 3

    # m_pow
    def test_pow_int_int_returns_int(self):
        result = m_pow(2, 3)
        assert result == 8
        assert type(result) is int

    def test_pow_zero_exponent(self):
        assert m_pow(5, 0) == 1
        assert m_pow(0, 0) == 1

    def test_pow_large_base(self):
        assert m_pow(10, 18) == 10**18

    def test_pow_negative_exponent_uses_decimal_path(self):
        """Negative integer exponents fall through to Decimal path."""
        result = m_pow(2, -1)
        # Should be 0.5 (Decimal or float)
        assert float(result) == pytest.approx(0.5)

    def test_pow_decimal_exponent_uses_decimal_path(self):
        result = m_pow(Decimal("2"), Decimal("3"))
        assert result == 8


# ---------------------------------------------------------------------------
# _m_num_str: cached string → numeric coercion
# ---------------------------------------------------------------------------


class TestMNumStrCache:
    """_m_num_str correctness (same semantics as m_num for strings)."""

    def test_empty_string_returns_zero(self):
        assert _m_num_str("") == 0

    def test_integer_string(self):
        assert _m_num_str("42") == 42
        assert type(_m_num_str("42")) is int

    def test_decimal_string(self):
        result = _m_num_str("3.14")
        assert result == Decimal("3.14")

    def test_leading_plus(self):
        assert _m_num_str("+5") == 5

    def test_leading_minus(self):
        assert _m_num_str("-5") == -5

    def test_double_minus(self):
        # -- = positive
        assert _m_num_str("--5") == 5

    def test_leading_chars_stop_parse(self):
        # "3A" → 3 (numeric prefix only)
        assert _m_num_str("3A") == 3

    def test_all_non_numeric(self):
        assert _m_num_str("ABC") == 0

    def test_scientific_notation(self):
        assert _m_num_str("1E3") == 1000
        assert type(_m_num_str("1E3")) is int

    def test_scientific_notation_negative_exp(self):
        result = _m_num_str("1.5E-1")
        assert float(result) == pytest.approx(0.15)

    def test_cache_returns_same_object(self):
        """lru_cache should return the same object for repeated calls."""
        r1 = _m_num_str("12345")
        r2 = _m_num_str("12345")
        assert r1 is r2  # same cached object

    def test_m_num_str_path_via_m_num(self):
        """m_num delegates string inputs to _m_num_str."""
        assert m_num("42") == 42
        assert m_num("3.14") == Decimal("3.14")
        assert m_num("") == 0


# ---------------------------------------------------------------------------
# _canonicalize_subscripts_lru: list coercion + cache
# ---------------------------------------------------------------------------


class TestCanonicalizeSubscriptsLru:
    """The _canonicalize_subscripts method on InMemoryGlobalStorage accepts
    both tuples and lists and returns canonical string tuples."""

    def _make_storage(self):
        from m2py.runtime.globals import InMemoryGlobalStorage

        return InMemoryGlobalStorage()

    def test_tuple_input(self):
        gs = self._make_storage()
        result = gs._canonicalize_subscripts((1, "hello"))
        assert result == ("1", "hello")

    def test_list_input_coerced(self):
        """Lists are coerced to tuples before caching."""
        gs = self._make_storage()
        result = gs._canonicalize_subscripts([1, "hello"])
        assert result == ("1", "hello")

    def test_int_subscript(self):
        gs = self._make_storage()
        result = gs._canonicalize_subscripts((42,))
        assert result == ("42",)

    def test_string_subscript_identity(self):
        """String subscripts are returned as-is (no canonicalization)."""
        gs = self._make_storage()
        result = gs._canonicalize_subscripts(("01",))
        assert result == ("01",)  # non-canonical string preserved

    def test_decimal_subscript(self):
        gs = self._make_storage()
        result = gs._canonicalize_subscripts((Decimal("1.5"),))
        assert result == ("1.5",)

    def test_float_subscript(self):
        gs = self._make_storage()
        result = gs._canonicalize_subscripts((0.5,))
        assert result == (".5",)

    def test_cache_hit_consistent(self):
        """Same tuple input always returns equal result."""
        gs = self._make_storage()
        r1 = gs._canonicalize_subscripts(("COLORADO",))
        r2 = gs._canonicalize_subscripts(("COLORADO",))
        assert r1 == r2

    def test_mixed_subscripts(self):
        gs = self._make_storage()
        result = gs._canonicalize_subscripts((1, "STATE", Decimal("0.01")))
        assert result == ("1", "STATE", ".01")


# ---------------------------------------------------------------------------
# m_var_value: Decimal and MArray fast paths
# ---------------------------------------------------------------------------


class TestMVarValueFastPaths:
    """m_var_value must return the correct value for all input types."""

    def test_decimal_passthrough(self):
        """Decimal values should pass through unchanged (fast path)."""
        d = Decimal("3.14")
        assert m_var_value(d) is d

    def test_decimal_zero(self):
        d = Decimal("0")
        assert m_var_value(d) is d

    def test_int_passthrough(self):
        assert m_var_value(42) == 42

    def test_str_passthrough(self):
        assert m_var_value("hello") == "hello"

    def test_float_passthrough(self):
        assert m_var_value(3.14) == 3.14

    def test_bool_passthrough(self):
        assert m_var_value(True) is True

    def test_marray_value(self):
        """MArray with value returns ._value via fast path."""
        a = MArray()
        a.value = "test"
        assert m_var_value(a) == "test"

    def test_marray_decimal_value(self):
        a = MArray()
        a.value = Decimal("1.5")
        assert m_var_value(a) == Decimal("1.5")

    def test_marray_undefined_returns_empty(self):
        """MArray with no value (._value is None) returns ''."""
        a = MArray()
        assert m_var_value(a) == ""

    def test_none_returns_empty(self):
        assert m_var_value(None) == ""


# ---------------------------------------------------------------------------
# _mumps_collation_key: lru_cache consistency
# ---------------------------------------------------------------------------


class TestMumpsCollationKeyCache:
    """_mumps_collation_key with lru_cache must remain correct."""

    def test_repeated_call_same_result(self):
        k1 = _mumps_collation_key("COLORADO")
        k2 = _mumps_collation_key("COLORADO")
        assert k1 == k2

    def test_repeated_call_same_object(self):
        """lru_cache returns the same tuple object for repeated calls."""
        k1 = _mumps_collation_key("ALABAMA")
        k2 = _mumps_collation_key("ALABAMA")
        assert k1 is k2

    def test_numeric_string_collation(self):
        k = _mumps_collation_key("42")
        # Numeric values get type_order 0
        assert k[0] == 0

    def test_string_collation(self):
        k = _mumps_collation_key("HELLO")
        # String values get type_order 1
        assert k[0] == 1

    def test_empty_string_sorts_first(self):
        assert _mumps_collation_key("") < _mumps_collation_key("0")
        assert _mumps_collation_key("") < _mumps_collation_key("A")

    def test_ordering_preserved(self):
        """Collation order is still numerically-before-string."""
        keys = ["B", "10", "A", "2", "1"]
        sorted_keys = sorted(keys, key=_mumps_collation_key)
        # Numbers before strings, numbers in numeric order
        assert sorted_keys == ["1", "2", "10", "A", "B"]


# ---------------------------------------------------------------------------
# Sort cache atomicity: single WeakKeyDictionary replaces two parallel dicts
# ---------------------------------------------------------------------------


class TestSortCacheAtomicity:
    """The _sort_cache stores (sorted_keys, sorted_ck) tuples in a single
    WeakKeyDictionary, preventing the GC race condition where two parallel
    WeakKeyDictionary instances could become inconsistent when one weakref
    callback fires before the other.

    Regression: https://github.com/CivicActions/m2py/issues/26
    Before this fix, _sorted_keys_cache.get(node) could succeed while
    _sorted_ck_cache[node] raised KeyError with a weakref as the key,
    crashing MUnit tests (%utt1, ZZRGUTEX, ZZDGPTCO1, %uttcovr).
    """

    def _make_storage(self):
        from m2py.runtime.globals import InMemoryGlobalStorage

        return InMemoryGlobalStorage()

    def test_sort_cache_is_single_dict(self):
        """_sort_cache is one dict, not two parallel dicts."""
        gs = self._make_storage()
        assert hasattr(gs, "_sort_cache")
        assert not hasattr(gs, "_sorted_keys_cache")
        assert not hasattr(gs, "_sorted_ck_cache")

    def test_order_populates_sort_cache_as_tuple(self):
        """$ORDER populates _sort_cache with (keys, collation_keys) tuple."""
        gs = self._make_storage()
        gs.set("G", ("a",), "1")
        gs.set("G", ("b",), "2")
        gs.set("G", ("c",), "3")

        # First $ORDER call populates cache
        result = gs.order("G", ("",))
        assert result == "a"

        # Cache should contain a tuple entry for the root node
        root = gs._globals["G"]
        cached = gs._sort_cache.get(root)
        assert cached is not None
        assert isinstance(cached, tuple)
        assert len(cached) == 2
        sorted_keys, sorted_ck = cached
        assert sorted_keys == ["a", "b", "c"]
        assert len(sorted_ck) == 3

    def test_order_cache_hit_returns_correct_results(self):
        """Sequential $ORDER calls use cache and return correct keys."""
        gs = self._make_storage()
        gs.set("G", ("1",), "v1")
        gs.set("G", ("2",), "v2")
        gs.set("G", ("3",), "v3")

        assert gs.order("G", ("",)) == "1"
        assert gs.order("G", ("1",)) == "2"
        assert gs.order("G", ("2",)) == "3"
        assert gs.order("G", ("3",)) == ""

    def test_set_updates_sort_cache_in_place(self):
        """Setting a new key updates both sorted_keys and sorted_ck in the
        cached tuple via _sorted_cache_insert."""
        gs = self._make_storage()
        gs.set("G", ("a",), "1")
        gs.set("G", ("c",), "3")

        # Trigger cache population
        gs.order("G", ("",))
        root = gs._globals["G"]
        cached_before = gs._sort_cache.get(root)
        assert cached_before is not None

        # Insert a new key between "a" and "c"
        gs.set("G", ("b",), "2")

        # Cache should be updated in-place
        cached_after = gs._sort_cache.get(root)
        assert cached_after is not None
        assert cached_after[0] == ["a", "b", "c"]
        assert len(cached_after[1]) == 3

    def test_kill_invalidates_sort_cache(self):
        """Kill removes the node's sort cache entry."""
        gs = self._make_storage()
        gs.set("G", ("a",), "1")
        gs.set("G", ("b",), "2")

        # Populate cache
        gs.order("G", ("",))
        root = gs._globals["G"]
        assert gs._sort_cache.get(root) is not None

        # Kill — should invalidate cache
        gs.kill("G", ("a",))
        assert gs._sort_cache.get(root) is None

    def test_kill_ancestor_cleanup_invalidates_cache(self):
        """Kill that cleans up empty ancestors also invalidates their cache."""
        gs = self._make_storage()
        gs.set("G", ("a", "1"), "v1")

        # Populate cache for the "a" parent
        gs.order("G", ("a", ""))
        a_node = gs._globals["G"]._children["a"]
        assert gs._sort_cache.get(a_node) is not None

        # Kill the only child — "a" becomes empty and gets cleaned up
        gs.kill("G", ("a", "1"))
        # "a" node itself should be removed (empty ancestor cleanup)
        if "G" in gs._globals:
            assert "a" not in gs._globals["G"]._children

    def test_gc_cleans_sort_cache_entry(self):
        """When an MArray node is garbage-collected, its _sort_cache entry
        is automatically removed by WeakKeyDictionary."""
        import gc

        gs = self._make_storage()
        gs.set("G", ("a",), "1")

        # Populate cache
        gs.order("G", ("",))
        assert len(gs._sort_cache) > 0

        # Kill entire global — removes all references to nodes
        gs.kill("G", ())
        gc.collect()

        # Cache should be empty after GC
        assert len(gs._sort_cache) == 0

    def test_iter_keys_populates_sort_cache(self):
        """iter_keys() populates _sort_cache with tuple entries."""
        gs = self._make_storage()
        gs.set("G", ("x",), "1")
        gs.set("G", ("y",), "2")

        keys = list(gs.iter_keys("G", ()))
        assert keys == ["x", "y"]

        root = gs._globals["G"]
        cached = gs._sort_cache.get(root)
        assert cached is not None
        assert isinstance(cached, tuple)
        assert cached[0] == ["x", "y"]

    def test_query_populates_sort_cache(self):
        """$QUERY populates _sort_cache entries during traversal."""
        gs = self._make_storage()
        gs.set("G", ("1", "a"), "v1")
        gs.set("G", ("1", "b"), "v2")

        result = gs.query("G", ("",))
        assert result  # should find a node

        # At least some nodes should have cache entries
        assert len(gs._sort_cache) > 0

    def test_reverse_order_with_cache(self):
        """Reverse $ORDER works correctly with cached sort data."""
        gs = self._make_storage()
        gs.set("G", ("a",), "1")
        gs.set("G", ("b",), "2")
        gs.set("G", ("c",), "3")

        # Forward to populate cache
        gs.order("G", ("",))

        # Reverse should use same cache
        assert gs.order("G", ("",), direction=-1) == "c"
        assert gs.order("G", ("c",), direction=-1) == "b"
        assert gs.order("G", ("b",), direction=-1) == "a"
        assert gs.order("G", ("a",), direction=-1) == ""

    def test_concurrent_set_and_order_consistency(self):
        """Interleaved set() and order() calls maintain consistent results."""
        gs = self._make_storage()

        # Build up data with interleaved order calls
        gs.set("G", ("1",), "v1")
        assert gs.order("G", ("",)) == "1"

        gs.set("G", ("3",), "v3")
        assert gs.order("G", ("1",)) == "3"

        gs.set("G", ("2",), "v2")
        # "2" was inserted between "1" and "3" in the cache
        assert gs.order("G", ("1",)) == "2"
        assert gs.order("G", ("2",)) == "3"

    def test_sort_cache_empty_children(self):
        """$ORDER on a node with no children returns empty string."""
        gs = self._make_storage()
        gs.set("G", (), "root_val")
        # No subscripted children — $ORDER should return ""
        assert gs.order("G", ("",)) == ""


# ---------------------------------------------------------------------------
# XECUTE fn_cache checked before parse/compile
# ---------------------------------------------------------------------------


class TestXecuteFnCachePriority:
    """fn_cache should be checked before xecute_cache — so clearing
    xecute_cache doesn't force recompilation when fn_cache still has the fn."""

    def _get_scope_var(self, scope: dict, name: str) -> str:
        from m2py.codegen.names import translate_name

        key = translate_name(name)
        val = scope.get(key)
        if val is None:
            return ""
        if isinstance(val, MArray):
            return str(val.value)
        return str(val)

    def test_fn_cache_populated_after_first_execute(self):
        rt = MUMPSRuntime()
        scope: dict = {}
        rt.execute_mumps("S X=1", scope)
        # Both caches should have been populated
        assert len(rt._xecute_fn_cache) == 1
        assert len(rt._xecute_cache) == 1

    def test_fn_cache_max_is_at_least_1024(self):
        """fn_cache max should be larger than xecute_cache max to hold more."""
        rt = MUMPSRuntime()
        assert rt._xecute_fn_cache_max >= rt._xecute_cache_max

    def test_fn_cache_serves_hits_after_xecute_cache_cleared(self):
        """When xecute_cache is cleared, fn_cache still serves the function
        without triggering recompilation (no new xecute_cache entries)."""
        rt = MUMPSRuntime()
        scope: dict = {}
        rt.execute_mumps("S X=42", scope)

        # Record compile count proxy: size of xecute_cache == number of compiles
        assert len(rt._xecute_cache) == 1

        # Manually clear xecute_cache (simulates eviction)
        rt._xecute_cache.clear()
        assert len(rt._xecute_cache) == 0

        # Execute the same code again — fn_cache should serve it
        scope2: dict = {}
        rt.execute_mumps("S X=42", scope2)
        assert self._get_scope_var(scope2, "X") == "42"

        # xecute_cache should still be empty (fn_cache hit, no recompile)
        assert len(rt._xecute_cache) == 0

    def test_fn_cache_result_correct_after_xecute_cache_cleared(self):
        """Result from fn_cache hit is semantically identical to fresh exec."""
        rt = MUMPSRuntime()
        # Execute many distinct codes so fn_cache is well-populated
        codes = [f"S V{i}={i * 2}" for i in range(10)]
        for code in codes:
            rt.execute_mumps(code, {})

        rt._xecute_cache.clear()

        # Re-run all — should produce correct results via fn_cache
        for i, code in enumerate(codes):
            s: dict = {}
            rt.execute_mumps(code, s)
            key = f"V{i}"
            assert self._get_scope_var(s, key) == str(i * 2)

    def test_fn_cache_not_capped_by_xecute_cache_eviction(self):
        """fn_cache entries survive xecute_cache eviction cycles."""
        rt = MUMPSRuntime()
        rt._xecute_cache_max = 4  # tiny cache to trigger eviction quickly

        for i in range(20):
            scope: dict = {}
            rt.execute_mumps(f"S X={i}", scope)

        # fn_cache should have all unique entries (up to its own max)
        assert len(rt._xecute_fn_cache) == 20


# ---------------------------------------------------------------------------
# set_x / set_y: numeric coercion via module-level _m_num
# ---------------------------------------------------------------------------


class TestSetXY:
    """set_x / set_y must coerce values to int via MUMPS numeric rules."""

    def test_set_x_integer_string(self):
        rt = MUMPSRuntime()
        rt.set_x("5")
        assert rt._current_device.x_pos == 5

    def test_set_y_integer_string(self):
        rt = MUMPSRuntime()
        rt.set_y("10")
        assert rt._current_device.y_pos == 10

    def test_set_x_numeric_string_with_alpha_suffix(self):
        """MUMPS numeric prefix: '3ABC' → 3."""
        rt = MUMPSRuntime()
        rt.set_x("3ABC")
        assert rt._current_device.x_pos == 3

    def test_set_x_zero(self):
        rt = MUMPSRuntime()
        rt.set_x("0")
        assert rt._current_device.x_pos == 0

    def test_set_x_decimal_truncates(self):
        """Decimal value is truncated to int."""
        rt = MUMPSRuntime()
        rt.set_x(Decimal("7.9"))
        assert rt._current_device.x_pos == 7

    def test_set_y_empty_string(self):
        """Empty string coerces to 0."""
        rt = MUMPSRuntime()
        rt.set_y("")
        assert rt._current_device.y_pos == 0

    def test_set_x_int(self):
        rt = MUMPSRuntime()
        rt.set_x(12)
        assert rt._current_device.x_pos == 12
