"""Tests for XECUTE code compilation cache.

The XECUTE cache avoids re-parsing and re-generating Python for
identical MUMPS code strings.  This is critical for old-style
cross-references which execute the same M code for every data entry.
"""

import pytest

from m2py.runtime import MArray, MUMPSRuntime


def _set_scope_var(scope: dict, name: str, value: str) -> None:
    """Set a variable in _scope using the translated Python key."""
    from m2py.codegen.names import translate_name

    key = translate_name(name)
    arr = scope.setdefault(key, MArray())
    arr.value = value


def _get_scope_var(scope: dict, name: str) -> str:
    """Get a variable from _scope using the translated Python key."""
    from m2py.codegen.names import translate_name

    key = translate_name(name)
    val = scope.get(key)
    if val is None:
        return ""
    if isinstance(val, MArray):
        return str(val.value)
    return str(val)


@pytest.mark.runtime
class TestXecuteCache:
    """Validate XECUTE caching behaviour."""

    def test_cache_starts_empty(self):
        """A fresh runtime has an empty XECUTE cache."""
        rt = MUMPSRuntime()
        assert rt._xecute_cache == {}

    def test_execute_mumps_populates_cache(self):
        """First XECUTE of code populates the cache."""
        rt = MUMPSRuntime()
        scope: dict = {}
        rt.execute_mumps("S X=1", scope)
        assert len(rt._xecute_cache) == 1

    def test_cache_hit_returns_correct_result(self):
        """Repeated XECUTE of the same code uses the cache."""
        rt = MUMPSRuntime()
        scope: dict = {}
        rt.execute_mumps("S X=1", scope)
        cache_size_after_first = len(rt._xecute_cache)

        # Execute same code again - should hit cache
        scope2: dict = {}
        rt.execute_mumps("S X=1", scope2)
        assert len(rt._xecute_cache) == cache_size_after_first
        assert _get_scope_var(scope2, "X") == "1"

    def test_different_code_different_cache_entries(self):
        """Different XECUTE code strings create separate cache entries."""
        rt = MUMPSRuntime()
        scope: dict = {}
        rt.execute_mumps("S X=1", scope)
        rt.execute_mumps("S Y=2", scope)
        assert len(rt._xecute_cache) == 2
        assert _get_scope_var(scope, "X") == "1"
        assert _get_scope_var(scope, "Y") == "2"

    def test_cached_code_produces_correct_output(self):
        """Cache doesn't stale - repeated execution still works correctly."""
        rt = MUMPSRuntime()

        # Execute same code multiple times - all should work via cache
        for i in range(5):
            s: dict = {}
            _set_scope_var(s, "I", str(i))
            rt.execute_mumps("S X=I+10", s)
            assert _get_scope_var(s, "X") == str(i + 10)

        # Cache should have exactly 1 entry (same code)
        assert len(rt._xecute_cache) == 1

    def test_cache_stores_compiled_code_object(self):
        """Cache entries contain compiled code objects (not just source)."""
        rt = MUMPSRuntime()
        scope: dict = {}
        rt.execute_mumps("S X=42", scope)

        for key, entry in rt._xecute_cache.items():
            python_source, code_obj = entry
            assert isinstance(python_source, str)
            assert hasattr(code_obj, "co_code")  # compiled code object

    def test_empty_code_not_cached(self):
        """Empty/whitespace XECUTE code is not cached."""
        rt = MUMPSRuntime()
        scope: dict = {}
        rt.execute_mumps("", scope)
        rt.execute_mumps("   ", scope)
        assert len(rt._xecute_cache) == 0

    def test_write_output_from_cached_code(self):
        """Cached XECUTE code produces correct WRITE output."""
        rt = MUMPSRuntime()
        scope: dict = {}

        rt.execute_mumps('W "hello"', scope)
        first_output = rt.get_output()
        assert "hello" in first_output

        rt.clear()
        rt.execute_mumps('W "hello"', scope)
        second_output = rt.get_output()
        assert "hello" in second_output

    def test_global_set_from_cached_code(self):
        """Cached XECUTE code correctly writes to globals."""
        rt = MUMPSRuntime()
        scope: dict = {}

        code = 'S ^TMP("TEST",1)="A"'
        rt.execute_mumps(code, scope)
        rt.execute_mumps(code, scope)  # second call hits cache

        val = rt.globals.get("TMP", ("TEST", "1"))
        assert val == "A"


@pytest.mark.runtime
class TestXecuteCacheLRUEviction:
    """Validate LRU eviction when _xecute_cache exceeds _xecute_cache_max.

    Commit 14026e58: each XECUTE cache entry retains ~29 KB; unbounded
    caching caused OOM on large routines like DMUDIC00.  LRU eviction
    discards the oldest 25% when the cache reaches _xecute_cache_max.
    """

    def test_cache_max_default(self):
        """Default _xecute_cache_max is 1024."""
        rt = MUMPSRuntime()
        assert rt._xecute_cache_max == 1024

    def test_eviction_triggers_at_max(self):
        """Cache evicts oldest 25% when it reaches max size."""
        rt = MUMPSRuntime()
        rt._xecute_cache_max = 8  # Small limit for testing
        scope: dict = {}

        # Fill cache to exactly max
        for i in range(8):
            rt.execute_mumps(f"S X={i}", scope)
        assert len(rt._xecute_cache) == 8

        # One more entry triggers eviction of oldest 25% (2) then adds 1
        rt.execute_mumps("S X=99", scope)
        assert len(rt._xecute_cache) <= 8
        # Oldest entries evicted, newest is present
        cache_keys = list(rt._xecute_cache.keys())
        # The last inserted code should be in cache
        assert any("99" in k for k in cache_keys)

    def test_eviction_removes_oldest_entries(self):
        """Eviction removes the oldest (first-inserted) entries."""
        rt = MUMPSRuntime()
        rt._xecute_cache_max = 4
        scope: dict = {}

        # Insert 4 unique entries
        for i in range(4):
            rt.execute_mumps(f"S Z={i * 100}", scope)
        first_keys = list(rt._xecute_cache.keys())

        # Insert one more — triggers eviction of oldest 25% (1 entry)
        rt.execute_mumps("S Z=999", scope)
        remaining_keys = list(rt._xecute_cache.keys())
        # First key should have been evicted
        assert first_keys[0] not in remaining_keys
        # Last keys and new key should remain
        assert any("999" in k for k in remaining_keys)

    def test_cache_still_works_after_eviction(self):
        """Cache hits still function correctly after eviction."""
        rt = MUMPSRuntime()
        rt._xecute_cache_max = 4
        scope: dict = {}

        # Fill and trigger eviction
        for i in range(5):
            rt.execute_mumps(f"S A={i}", scope)

        # Re-execute one of the remaining cached entries
        scope2: dict = {}
        rt.execute_mumps("S A=4", scope2)
        assert _get_scope_var(scope2, "A") == "4"

    def test_eviction_preserves_cache_correctness(self):
        """All cache entries produce correct results after eviction cycles."""
        rt = MUMPSRuntime()
        rt._xecute_cache_max = 4

        # Run 12 unique codes — several eviction cycles
        for i in range(12):
            scope_i: dict = {}
            rt.execute_mumps(f"S V={i + 10}", scope_i)
            assert _get_scope_var(scope_i, "V") == str(i + 10)

        # Cache should not have grown beyond max
        assert len(rt._xecute_cache) <= rt._xecute_cache_max


@pytest.mark.runtime
class TestNamespaceCycleBreaking:
    """Verify execute_mumps namespace.clear() prevents reference cycles.

    Commit 14026e58: exec() sets XECUTE.__globals__ = namespace and
    namespace["XECUTE"] = XECUTE, creating a cycle.  namespace.clear()
    in the finally block breaks this immediately.
    """

    def test_execute_mumps_produces_correct_result(self):
        """Basic execute_mumps still works with namespace.clear()."""
        rt = MUMPSRuntime()
        scope: dict = {}
        rt.execute_mumps("S X=42", scope)
        assert _get_scope_var(scope, "X") == "42"

    def test_multiple_executes_independent(self):
        """Sequential execute_mumps calls don't share namespace state."""
        rt = MUMPSRuntime()
        scope: dict = {}
        rt.execute_mumps("S A=1", scope)
        rt.execute_mumps("S B=2", scope)
        assert _get_scope_var(scope, "A") == "1"
        assert _get_scope_var(scope, "B") == "2"

    def test_write_output_after_namespace_clear(self):
        """WRITE output survives namespace.clear() (output is on runtime)."""
        rt = MUMPSRuntime()
        scope: dict = {}
        rt.execute_mumps('W "hello"', scope)
        rt.execute_mumps('W "world"', scope)
        output = rt.get_output()
        assert "hello" in output
        assert "world" in output

    def test_exception_still_propagates(self):
        """Errors in XECUTE still propagate despite namespace.clear()."""
        rt = MUMPSRuntime()
        scope: dict = {}
        with pytest.raises(SyntaxError, match="XECUTE parse error"):
            rt.execute_mumps("(((", scope)
