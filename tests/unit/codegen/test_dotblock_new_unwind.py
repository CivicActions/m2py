"""Tests for dot-block NEW unwind in TRAMPOLINE mode.

In TRAMPOLINE mode, NEW'd variables inside dot blocks must be unwound
when the dot block exits. The generated code must:

1. Record the NEW stack depth (mark) before the dot block starts
2. Unwind all entries pushed above that mark when the block exits

Without this, variables NEW'd inside a dot block (e.g., N DD inside
a . . block) are never restored when the block exits, leaving them
undefined for subsequent iterations of an enclosing FOR loop.

The specific bug this fixes: DICN0.m's N5 label does:
  N DD S DD=0 D
  . N DIFILEI,...
  . F  S DD=$O(^DD(+DO(2),.01,1,DD)) Q:'DD  D
  . . ...
  . . S %=DD N DD,D
  . . X ^DD(...)
The N DD,D inside the .. block removes DD from state._locals.
Without unwind-to-mark, DD stays undefined after the block exits,
causing KeyError on the next FOR iteration.
"""

import sys
import types

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


@pytest.fixture(autouse=True)
def _cleanup_modules():
    """Remove test modules from sys.modules after each test."""
    before = set(sys.modules)
    yield
    for name in set(sys.modules) - before:
        del sys.modules[name]


@pytest.fixture
def runtime():
    """Fresh runtime for each test."""
    return MUMPSRuntime()


def _load(source: str, name: str) -> types.ModuleType:
    """Transpile MUMPS source and load as a Python module."""
    code = generate_python(source, routine_name=name)
    mod = types.ModuleType(name)
    mod.__dict__["__name__"] = name
    exec(compile(code, f"<{name}>", "exec"), mod.__dict__)  # noqa: S102
    sys.modules[name] = mod
    return mod


@pytest.mark.codegen
class TestDotBlockNewUnwindBasic:
    """NEW inside dot blocks is unwound on block exit in TRAMPOLINE mode."""

    def test_new_in_dot_block_restored_after_exit(self, runtime):
        """Variable NEW'd in dot block is restored when block exits.

        MUMPS: S X="outer" D  W X
               . N X S X="inner"
        Expected: W X outputs "outer" (NEW unwound on dot block exit)
        """
        # Force TRAMPOLINE by adding a GOTO
        source = 'TEST S X="outer" D  W X Q\n . N X S X="inner"\n G SKIP\nSKIP Q\n'
        mod = _load(source, "NDUB1")
        scope: dict = {}
        mod.TEST(runtime, _scope=scope)
        assert runtime.get_output() == "outer"

    def test_new_in_nested_dot_restored(self, runtime):
        """NEW in nested dot block only affects that level.

        MUMPS: S X="outer",Y="outer" D
               . S X="mid" D
               . . N X,Y S X="inner",Y="inner"
               . W X,Y
        Expected: X="mid", Y="outer" (inner NEW unwound, outer . still has mid)
        """
        source = (
            'TEST S X="outer",Y="outer" D  Q\n'
            ' . S X="mid" D\n'
            ' . . N X,Y S X="inner",Y="inner"\n'
            " . W X,Y\n"
            " G SKIP\nSKIP Q\n"
        )
        mod = _load(source, "NDUB2")
        scope: dict = {}
        mod.TEST(runtime, _scope=scope)
        assert runtime.get_output() == "midouter"

    def test_new_in_for_dot_block_each_iteration(self, runtime):
        """NEW inside FOR/dot block restores on each iteration.

        MUMPS: S X="outer" F I=1:1:3 D
               . N X S X=I W X,","
               W X
        Expected: 1,2,3,outer
        """
        source = (
            'TEST S X="outer" F I=1:1:3 D\n'
            ' . N X S X=I W X,","\n'
            " W X Q\n"
            " G SKIP\nSKIP Q\n"
        )
        mod = _load(source, "NDUB3")
        scope: dict = {}
        mod.TEST(runtime, _scope=scope)
        assert runtime.get_output() == "1,2,3,outer"


@pytest.mark.codegen
class TestDotBlockNewUnwindEdgeCases:
    """Edge cases for dot-block NEW unwind."""

    def test_argumentless_new_in_dot_block(self, runtime):
        """Argumentless NEW inside dot block restores all vars on exit.

        MUMPS: S X=1,Y=2 D  W X,Y
               . N  S X=99,Y=99
        Expected: W X,Y outputs "12" (full snapshot restored)
        """
        source = "TEST S X=1,Y=2 D  W X,Y Q\n . N  S X=99,Y=99\n G SKIP\nSKIP Q\n"
        mod = _load(source, "NDUE1")
        scope: dict = {}
        mod.TEST(runtime, _scope=scope)
        assert runtime.get_output() == "12"

    def test_new_with_external_do_in_dot_block(self, runtime):
        """NEW + external DO inside dot block: NEW still unwound on exit.

        MUMPS: S X=1 D  W X
               . N X S X=2
        Expected: "1" — NEW unwound even though block does an external call
        """
        # Create a stub external routine
        _load("STUB Q\nSUB Q\n", "STUB")

        source = "TEST S X=1 D  W X Q\n . N X S X=2 D SUB^STUB\n G SKIP\nSKIP Q\n"
        mod = _load(source, "NDUE2")
        scope: dict = {}
        mod.TEST(runtime, _scope=scope)
        assert runtime.get_output() == "1"

    def test_multiple_news_in_same_dot_block(self, runtime):
        """Multiple NEWs in same dot block all unwound on exit.

        MUMPS: S A=1,B=2 D  W A,B
               . N A S A=10
               . N B S B=20
        Expected: "12" (both A and B restored)
        """
        source = (
            "TEST S A=1,B=2 D  W A,B Q\n . N A S A=10\n . N B S B=20\n G SKIP\nSKIP Q\n"
        )
        mod = _load(source, "NDUE3")
        scope: dict = {}
        mod.TEST(runtime, _scope=scope)
        assert runtime.get_output() == "12"

    def test_new_in_inner_dot_then_use_in_for(self, runtime):
        """NEW in inner dot block, var used by outer FOR loop.

        This is the DICN0 pattern: FOR sets DD, inner block does N DD.
        After inner block, DD must be restored for the next FOR iteration.

        MUMPS: S DD=0 D
               . F  S DD=DD+1 Q:DD>3  D
               . . N DD S DD=99
               W DD
        Expected: DD=4 after loop (3 iterations: DD goes 1→2→3→4 then Q)
        """
        source = (
            "TEST S DD=0 D\n"
            " . F  S DD=DD+1 Q:DD>3  D\n"
            " . . N DD S DD=99\n"
            " W DD Q\n"
            " G SKIP\nSKIP Q\n"
        )
        mod = _load(source, "NDUE4")
        scope: dict = {}
        mod.TEST(runtime, _scope=scope)
        assert runtime.get_output() == "4"


@pytest.mark.codegen
class TestDotBlockNewCodegen:
    """Codegen structure tests for dot-block NEW unwind."""

    def test_trampoline_nondynamic_dot_with_new_uses_scope_mgr(self):
        """Non-dynamic_locals TRAMPOLINE with NEW in dot block uses new_var()."""
        source = "TEST S X=1 D  W X Q\n . N X S X=2\n G SKIP\nSKIP Q\n"
        code = generate_python(source, routine_name="NDUC1")
        # Non-dynamic_locals: uses scope manager new_var() for save/restore
        assert ".new_var(" in code

    def test_trampoline_dynamic_dot_with_new_has_mark(self):
        """Dynamic_locals TRAMPOLINE with NEW in dot block generates ns_mark.

        Argumentless NEW in the routine forces dynamic_locals mode.
        """
        source = "TEST N  S X=1 D  W X Q\n . N X S X=2\n G SKIP\nSKIP Q\n"
        code = generate_python(source, routine_name="NDUC1D")
        assert "_ns_mark_" in code
        assert "unwind_new_stack_to_mark" in code

    def test_dot_without_new_no_mark(self):
        """Dot block without NEW does not generate ns_mark or new_var."""
        source = "TEST S X=1 D  W X Q\n . S X=2\n G SKIP\nSKIP Q\n"
        code = generate_python(source, routine_name="NDUC2")
        assert "_ns_mark_" not in code
        # The import line always includes the function, so check for actual call
        assert "unwind_new_stack_to_mark(state" not in code
        assert ".new_var(" not in code

    def test_nested_dots_have_separate_marks(self):
        """Nested dot blocks each get their own unique marks in dynamic mode."""
        # Argumentless NEW forces dynamic_locals
        source = "TEST N  D  Q\n . N A\n . D\n . . N B\n G SKIP\nSKIP Q\n"
        code = generate_python(source, routine_name="NDUC3")
        import re

        marks = re.findall(r"_ns_mark_\d+", code)
        unique_marks = set(marks)
        assert len(unique_marks) >= 2, f"Expected >= 2 unique marks, got {unique_marks}"
