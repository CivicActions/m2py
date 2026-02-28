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
