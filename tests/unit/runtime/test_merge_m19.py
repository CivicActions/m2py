"""Unit tests for MERGE M19 error detection.

Tests that m2py correctly detects and raises M19 errors when MERGE source
and destination have an ancestor/descendant relationship, per the MUMPS
1995 standard (Section 8.2.13).
"""

from __future__ import annotations

import pytest

from m2py.runtime.helpers import _m19_check
from m2py.runtime.exceptions import MRuntimeError


# =============================================================================
# Unit tests for _m19_check helper
# =============================================================================


class TestM19CheckHelper:
    """Tests for the _m19_check(src_subs, dest_subs) helper."""

    def test_dest_is_descendant_of_source(self):
        """M19 fires when dest subscripts extend source subscripts."""
        with pytest.raises(MRuntimeError, match="M19"):
            _m19_check(("1",), ("1", "2"))

    def test_source_is_descendant_of_dest(self):
        """M19 fires when source subscripts extend dest subscripts."""
        with pytest.raises(MRuntimeError, match="M19"):
            _m19_check(("1", "2"), ("1",))

    def test_root_vs_subscripted(self):
        """M19 fires: root is ancestor of any subscripted node."""
        with pytest.raises(MRuntimeError, match="M19"):
            _m19_check((), ("1",))

    def test_subscripted_vs_root(self):
        """M19 fires: subscripted is descendant of root."""
        with pytest.raises(MRuntimeError, match="M19"):
            _m19_check(("1",), ())

    def test_deep_ancestor(self):
        """M19 fires with deeply nested ancestor/descendant."""
        with pytest.raises(MRuntimeError, match="M19"):
            _m19_check(("a", "b"), ("a", "b", "c", "d"))

    def test_self_merge_no_error(self):
        """Self-merge (same subscripts) is NOT an M19 error."""
        _m19_check(("1",), ("1",))  # Should not raise

    def test_self_merge_root_no_error(self):
        """Self-merge at root level is NOT an M19 error."""
        _m19_check((), ())  # Should not raise

    def test_different_subscripts_no_error(self):
        """Non-overlapping sibling subscripts are fine."""
        _m19_check(("1",), ("2",))  # Should not raise

    def test_different_deep_branches_no_error(self):
        """Non-overlapping branches at same depth are fine."""
        _m19_check(("1", "a"), ("1", "b"))  # Should not raise

    def test_completely_different_paths_no_error(self):
        """Completely different subscript paths are fine."""
        _m19_check(("x", "y"), ("a", "b"))  # Should not raise

    def test_partial_prefix_different_value_no_error(self):
        """Partial prefix match but diverging at some level is fine."""
        _m19_check(("1", "2", "3"), ("1", "2", "4"))  # Should not raise

    def test_error_has_m19_code(self):
        """The MRuntimeError has code='M19'."""
        with pytest.raises(MRuntimeError) as exc_info:
            _m19_check(("1",), ("1", "2"))
        assert exc_info.value.code == "M19"


# =============================================================================
# Integration tests: MERGE M19 through transpile + execute pipeline
# =============================================================================


def _run(code: str) -> str:
    """Transpile and execute MUMPS code, return output."""
    from m2py.codegen import generate_python
    from m2py.runtime import MUMPSRuntime

    py = generate_python(code)
    rt = MUMPSRuntime()
    result = rt.execute(py)
    assert result.success, f"Execution failed: {result.error}"
    return result.output.rstrip()


class TestM19Integration:
    """Integration tests: M19 detection through the full transpiler pipeline."""

    def test_global_dest_is_descendant(self):
        """M ^A(1,2)=^A(1) raises M19 (global)."""
        out = _run(
            "TEST\n"
            " K ^A\n"
            ' S ^A(1)="v1",^A(1,2)="v12"\n'
            ' N $ET S $ET="W ""M19"",! S $EC="""""\n'
            " M ^A(1,2)=^A(1)\n"
            ' W "no-err",!\n'
            " K ^A Q"
        )
        assert out == "M19"

    def test_global_source_is_descendant(self):
        """M ^A=^A(1) raises M19 (global)."""
        out = _run(
            "TEST\n"
            " K ^A\n"
            ' S ^A(1)="v1",^A(1,2)="v12"\n'
            ' N $ET S $ET="W ""M19"",! S $EC="""""\n'
            " M ^A=^A(1)\n"
            ' W "no-err",!\n'
            " K ^A Q"
        )
        assert out == "M19"

    def test_local_dest_is_descendant(self):
        """M A(1,2)=A(1) raises M19 (local)."""
        out = _run(
            "TEST\n"
            " N A\n"
            ' S A(1)="v1",A(1,2)="v12"\n'
            ' N $ET S $ET="W ""M19"",! S $EC="""""\n'
            " M A(1,2)=A(1)\n"
            ' W "no-err",!\n'
            " Q"
        )
        assert out == "M19"

    def test_local_source_is_descendant(self):
        """M A=A(1) raises M19 (local)."""
        out = _run(
            "TEST\n"
            " N A\n"
            ' S A(1)="v1"\n'
            ' N $ET S $ET="W ""M19"",! S $EC="""""\n'
            " M A=A(1)\n"
            ' W "no-err",!\n'
            " Q"
        )
        assert out == "M19"

    def test_self_merge_global_ok(self):
        """M ^A=^A is not M19 (self-merge, no-op)."""
        out = _run(
            "TEST\n"
            " K ^A\n"
            ' S ^A="root",^A(1)="child"\n'
            " M ^A=^A\n"
            ' W "^A=",$G(^A)," ^A(1)=",$G(^A(1)),!\n'
            " K ^A Q"
        )
        assert out == "^A=root ^A(1)=child"

    def test_self_merge_local_ok(self):
        """M A=A is not M19 (self-merge, no-op)."""
        out = _run(
            "TEST\n"
            " N A\n"
            ' S A="root",A(1)="child"\n'
            " M A=A\n"
            ' W "A=",$G(A)," A(1)=",$G(A(1)),!\n'
            " Q"
        )
        assert out == "A=root A(1)=child"

    def test_same_variable_non_overlapping_ok(self):
        """M C(3)=C(1) with non-overlapping subscripts is fine."""
        out = _run(
            "TEST\n"
            " N C\n"
            ' S C(1)="v1",C(2)="v2"\n'
            " M C(3)=C(1)\n"
            ' W "C(3)=",$G(C(3)),!\n'
            " Q"
        )
        assert out == "C(3)=v1"

    def test_cross_local_global_no_m19(self):
        """M A(1,2)=^A(1) does NOT raise M19 (different variable spaces)."""
        out = _run(
            "TEST\n"
            " N A\n"
            ' S A(1)="local"\n'
            " K ^A\n"
            ' S ^A(1)="global"\n'
            " M A(1,2)=^A(1)\n"
            ' W "A(1,2)=",$G(A(1,2)),!\n'
            " K ^A Q"
        )
        assert out == "A(1,2)=global"

    def test_different_globals_no_m19(self):
        """M ^B=^A does NOT raise M19 (different globals)."""
        out = _run(
            "TEST\n"
            " K ^A,^B\n"
            ' S ^A(1)="v1",^A(1,2)="v12"\n'
            " M ^B=^A\n"
            ' W "^B(1)=",$G(^B(1))," ^B(1,2)=",$G(^B(1,2)),!\n'
            " K ^A,^B Q"
        )
        assert out == "^B(1)=v1 ^B(1,2)=v12"

    def test_basic_merge_still_works(self):
        """Verify basic MERGE functionality isn't broken by M19 checks."""
        out = _run(
            "TEST\n"
            " K ^A,^B\n"
            ' S ^A(1)="a1",^A(2)="a2",^A(2,"x")="a2x"\n'
            " M ^B=^A\n"
            ' W "^B(1)=",$G(^B(1))," ^B(2)=",$G(^B(2))," ^B(2,x)=",$G(^B(2,"x")),!\n'
            " K ^A,^B Q"
        )
        assert out == "^B(1)=a1 ^B(2)=a2 ^B(2,x)=a2x"
