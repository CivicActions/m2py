"""Tests for cross-label GOTO code generation (Spec 006 Phase 5).

Tests forward cross-label GOTO with trampoline pattern:
- Variable visibility across labels
- Multiple label chains
- IF/ELSE branch handling
"""

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


@pytest.fixture
def runtime():
    """Provide a fresh runtime instance for each test."""
    return MUMPSRuntime()


def execute_mumps(source: str, runtime: MUMPSRuntime) -> str:
    """Generate and execute MUMPS code, return output."""
    code = generate_python(source)
    result = runtime.execute(code)
    if not result.success:
        raise RuntimeError(f"Execution failed: {result.error}")
    return result.output


@pytest.mark.codegen
class TestForwardCrossLabelGoto:
    """Tests for forward cross-label GOTO (T059-T062)."""

    def test_forward_cross_label_variable_visibility(self, runtime):
        """T059: Variables set in source label visible in target label.

        MUMPS: TEST S X=1 G NEXT Q / NEXT W X Q
        Expected: "1"
        """
        source = """TEST S X=1 G NEXT Q
NEXT W X Q"""
        output = execute_mumps(source, runtime)
        assert output == "1"

    def test_forward_cross_label_skipped_code(self, runtime):
        """T060: Code after GOTO on same line is not executed.

        MUMPS: TEST G END W "skip" Q / END W "end" Q
        Expected: "end"
        """
        source = """TEST G END W "skip" Q
END W "end" Q"""
        output = execute_mumps(source, runtime)
        assert output == "end"

    def test_forward_cross_label_multiple_variables(self, runtime):
        """T061: Multiple variables visible in target label.

        MUMPS: TEST S A=10,B=20 G SUM Q / SUM W A+B Q
        Expected: "30"
        """
        source = """TEST S A=10,B=20 G SUM Q
SUM W A+B Q"""
        output = execute_mumps(source, runtime)
        assert output == "30"

    def test_forward_cross_label_chain(self, runtime):
        """T062: Multiple GOTOs form a chain across labels.

        MUMPS: TEST G A Q / A G B Q / B W "done" Q
        Expected: "done"
        """
        source = """TEST G A Q
A G B Q
B W "done" Q"""
        output = execute_mumps(source, runtime)
        assert output == "done"


@pytest.mark.codegen
class TestCrossLabelFromIfElse:
    """Tests for cross-label GOTO from IF/ELSE branches (T055a, T062a-b)."""

    def test_cross_label_from_if_true_branch(self, runtime):
        """T062a: Cross-label GOTO from IF true branch skips rest of line.

        MUMPS: TEST I 1 G PASS W "mid" Q / PASS W "P" Q
        Expected: "P" (W "mid" Q is skipped due to GOTO)
        """
        source = """TEST I 1 G PASS W "mid" Q
PASS W "P" Q"""
        output = execute_mumps(source, runtime)
        assert output == "P"

    def test_cross_label_from_else_branch(self, runtime):
        """T062b: Cross-label GOTO from ELSE branch (on separate line).

        Note: In MUMPS, ELSE on same line as IF is skipped when IF is false.
        ELSE must be on separate line to execute when $TEST is false.

        MUMPS: TEST I 0 G PASS / E G FAIL / Q / PASS W "P" Q / FAIL W "F" Q
        Expected: "F"
        """
        source = """TEST I 0 G PASS
 E  G FAIL
 Q
PASS W "P" Q
FAIL W "F" Q"""
        output = execute_mumps(source, runtime)
        assert output == "F"

    def test_cross_label_from_if_false_fallthrough(self, runtime):
        """When IF is false, rest of line is skipped including ELSE.

        MUMPS: TEST I 0 G PASS E G FAIL Q / PASS W "P" Q / FAIL W "F" Q
        Expected: "P" (entire line after I 0 is skipped, falls through to PASS)
        """
        source = """TEST I 0 G PASS E  G FAIL Q
PASS W "P" Q
FAIL W "F" Q"""
        output = execute_mumps(source, runtime)
        assert output == "P"


@pytest.mark.codegen
class TestTrampolineCodeStructure:
    """Tests for trampoline pattern code generation structure."""

    def test_trampoline_generates_label_dict(self):
        """Trampoline pattern generates _labels dictionary."""
        source = """TEST G NEXT Q
NEXT W "done" Q"""
        code = generate_python(source)

        assert "_labels = {" in code
        assert '"TEST": _TEST' in code
        assert '"NEXT": _NEXT' in code

    def test_trampoline_generates_entry_point(self):
        """Trampoline pattern generates entry point function."""
        source = """TEST G NEXT Q
NEXT W "done" Q"""
        code = generate_python(source)

        # Entry point should be named after first label
        assert "def TEST():" in code
        assert "while label is not None:" in code
        assert "func = _labels[label]" in code

    def test_trampoline_generates_state_class(self):
        """Trampoline pattern generates RoutineState class."""
        source = """TEST S X=1 G NEXT Q
NEXT W X Q"""
        code = generate_python(source)

        assert "@dataclass" in code
        assert "class RoutineState:" in code
        assert "X: Any = None" in code

    def test_trampoline_label_functions_prefixed(self):
        """Label functions are prefixed with _ in trampoline pattern."""
        source = """TEST G NEXT Q
NEXT W "done" Q"""
        code = generate_python(source)

        assert "def _TEST(state)" in code
        assert "def _NEXT(state)" in code

    def test_trampoline_state_variable_access(self):
        """Variables are accessed via state object in trampoline pattern."""
        source = """TEST S X=1 G NEXT Q
NEXT W X Q"""
        code = generate_python(source)

        assert "state.X = 1" in code
        assert "state.X)" in code  # Used in write

    def test_trampoline_exits_on_quit(self, execute_mumps):
        """T088: Trampoline exits correctly when label returns None.

        MUMPS: TEST G A Q / A W "done" Q
        Expected: "done" (trampoline exits after A returns None)
        """
        source = """TEST G A Q
A W "done" Q"""
        result = execute_mumps(source)
        assert result.output == "done"
        assert result.success is True

    def test_trampoline_no_recursion_error_1000_iterations(self, execute_mumps):
        """T089: Trampoline handles 1000+ cyclic iterations without RecursionError.

        Pattern: TEST -> LOOP -> LOOP -> ... (1000 times)
        Uses trampoline dispatch, not Python recursion.
        """
        source = """TEST S N=0 G LOOP Q
LOOP S N=N+1 I N<1000 G LOOP
 W N Q"""
        result = execute_mumps(source)
        assert result.output == "1000"
        assert result.success is True

    def test_trampoline_no_recursion_error_10000_iterations(self, execute_mumps):
        """T089 extended: Trampoline handles 10000+ cyclic iterations.

        This would cause RecursionError with naive function calls.
        Python default recursion limit is ~1000.
        """
        source = """TEST S N=0 G LOOP Q
LOOP S N=N+1 I N<10000 G LOOP
 W N Q"""
        result = execute_mumps(source)
        assert result.output == "10000"
        assert result.success is True


@pytest.mark.codegen
class TestSimpleFunctionsNotAffected:
    """Tests that SIMPLE_FUNCTIONS pattern still works."""

    def test_simple_routine_no_trampoline(self):
        """Routine without cross-label GOTO uses simple functions."""
        source = 'TEST W "hello" Q'
        code = generate_python(source)

        # No trampoline machinery
        assert "RoutineState" not in code
        assert "_labels" not in code
        assert "def TEST():" in code
        assert "def _TEST(" not in code

    def test_intra_label_goto_no_trampoline(self):
        """Intra-label forward GOTO doesn't trigger trampoline."""
        source = """TEST I 1 G TEST+3
 W "skip"
 W "done" Q"""
        code = generate_python(source)

        # Should be simple function pattern with if/else restructuring
        assert "def TEST():" in code
        # No trampoline
        assert "_labels" not in code


@pytest.mark.codegen
class TestBackwardCrossLabelGoto:
    """Phase 6: Backward cross-label GOTO patterns (T063-T069)."""

    def test_backward_cross_label_goto(self, execute_mumps):
        """T066: Backward GOTO creates implicit loop via trampoline.

        Pattern: TEST -> LOOP -> INC -> LOOP creates cycle
        """
        source = """TEST S X=0 G LOOP
INC S X=X+1 W X
LOOP I X<3 G INC
 Q"""
        result = execute_mumps(source)
        assert result.output == "123"
        assert result.success is True

    def test_backward_cross_label_variable_preserved(self, execute_mumps):
        """T068: Variables preserved across backward iterations."""
        source = """TEST S X=0,SUM=0 G LOOP
LOOP S X=X+1,SUM=SUM+X I X<10 G LOOP
 W SUM Q"""
        result = execute_mumps(source)
        assert result.output == "55"  # Sum of 1+2+...+10
        assert result.success is True

    def test_nested_label_cycle(self, execute_mumps):
        """T069: Nested labels with backward A->B->C->A pattern."""
        source = """TEST S N=0 G A
A S N=N+1 W "A"
 G B
B W "B"
 G C
C W "C"
 I N<3 G A
 Q"""
        result = execute_mumps(source)
        assert result.output == "ABCABCABC"
        assert result.success is True


@pytest.mark.codegen
class TestSelfLoopPattern:
    """Phase 6: Self-loop patterns (T069a/T069b)."""

    def test_self_loop_generates_while_pattern(self, generate_python):
        """T069b: Self-loop generates while True pattern, not trampoline."""
        # Single label that GOTOs itself
        source = """TEST S X=0
 S X=X+1 W X I X<3 G TEST
 Q"""
        code = generate_python(source)

        # Should generate while True: pattern
        assert "while True:" in code
        # Self-loop GOTO becomes continue
        assert "continue" in code
        # QUIT becomes break
        assert "break" in code

    def test_self_loop_with_cross_label_entry(self, execute_mumps):
        """T069a: Self-loop with cross-label entry works correctly.

        Pattern: TEST -> LOOP (with self-loop in LOOP)
        """
        source = """TEST S X=0 G LOOP
LOOP S X=X+1 W X I X<3 G LOOP
 Q"""
        result = execute_mumps(source)
        assert result.output == "123"
        assert result.success is True

    def test_self_loop_preserves_variables(self, execute_mumps):
        """Self-loop preserves variable state across iterations.

        Note: The self-loop must NOT initialize variables inside the loop,
        or they'll reset each iteration. We use a cross-label entry pattern.
        """
        # TEST initializes, then jumps to LOOP which has the self-loop
        source = """TEST S X=0,SUM=0 G LOOP
LOOP S X=X+1,SUM=SUM+X I X<5 G LOOP
 W SUM Q"""
        result = execute_mumps(source)
        assert result.output == "15"  # Sum of 1+2+3+4+5
        assert result.success is True


@pytest.mark.codegen
class TestVariableVisibility:
    """Phase 7: Variable visibility across labels (T070-T076c)."""

    def test_variable_modification_in_target(self, execute_mumps):
        """T076: Variable set in source can be modified in target.

        MUMPS: TEST S X=1 G ADD Q / ADD S X=X+10 W X Q
        Expected: "11"
        """
        source = """TEST S X=1 G ADD Q
ADD S X=X+10 W X Q"""
        result = execute_mumps(source)
        assert result.output == "11"
        assert result.success is True

    def test_subscripted_locals_visibility(self, execute_mumps):
        """T075: Subscripted local variables visible across labels.

        MUMPS: TEST S A(1)=10,A(2)=20 G SUM Q / SUM W A(1)+A(2) Q
        Expected: "30"
        """
        source = """TEST S A(1)=10,A(2)=20 G SUM Q
SUM W A(1)+A(2) Q"""
        result = execute_mumps(source)
        assert result.output == "30"
        assert result.success is True

    @pytest.mark.xfail(reason="NEW command not yet supported in codegen")
    def test_newed_variable_isolation(self, execute_mumps):
        """T076a: NEWed variables are isolated to their label scope.

        In MUMPS, NEW creates a local scope for the variable.
        MUMPS: TEST N X S X=1 G NEXT Q / NEXT W X Q
        Expected: "" (X is local to TEST, not visible in NEXT)

        Note: This test expects YDB behavior where X is undefined in NEXT.
        """
        source = """TEST N X S X=1 G NEXT Q
NEXT W X Q"""
        result = execute_mumps(source)
        # YDB throws error on undefined variable access
        assert result.success is True

    @pytest.mark.xfail(reason="DO with args has issues in cross-label context")
    def test_formal_param_isolation(self, execute_mumps):
        """T076b: Formal parameters are isolated to subroutine scope.

        MUMPS: TEST D SUB(5) Q / SUB(X) G SHOW Q / SHOW W X Q
        Expected: "5" (X from SUB's formal param visible via cross-label GOTO)

        Note: Per MUMPS semantics, X in SUB(X) is local to SUB.
        When GOTO SHOW happens, X from SUB's scope should be visible.
        """
        source = """TEST D SUB(5) Q
SUB(X) G SHOW Q
SHOW W X Q"""
        result = execute_mumps(source)
        assert result.output == "5"
        assert result.success is True

    def test_undefined_variable_reads_as_empty_string(self, execute_mumps):
        """T076c: Skipped initialization leaves variable undefined.

        When IF condition is false, initialization is skipped.
        MUMPS: TEST I 0 S X=99 G DONE Q / DONE W X Q

        Note: YDB throws LVUNDEF error for undefined variables.
        m2py treats undefined as empty string (consistent with MArray.value).
        This allows code to continue without runtime errors.
        """
        source = """TEST I 0 S X=99 G DONE Q
DONE W X Q"""
        result = execute_mumps(source)
        # m2py outputs empty string for undefined variables (MUMPS semantics)
        assert result.output == ""
        assert result.success is True


@pytest.mark.codegen
class TestCrossLabelLoopExit:
    """Phase 8: Cross-label GOTO from inside FOR loops (T077-T083)."""

    def test_single_for_exit_to_label(self, execute_mumps):
        """T080: Single FOR loop exit via cross-label GOTO.

        MUMPS: TEST F I=1:1:10 W I I I=3 G DONE Q / DONE W "done" Q
        Expected: "123done" (write 1,2,3 then exit to DONE)
        """
        source = """TEST F I=1:1:10 W I I I=3 G DONE Q
DONE W "done" Q"""
        result = execute_mumps(source)
        assert result.output == "123done"
        assert result.success is True

    def test_nested_for_exit_to_label(self, execute_mumps):
        """T081: Nested FOR loop exit via cross-label GOTO.

        MUMPS: TEST F I=1:1:3 F J=1:1:2 W I,J I I=2,J=1 G OUT Q / OUT W "!" Q
        Expected: "111221!" (writes I,J pairs until I=2,J=1 then exits both loops)
        """
        source = """TEST F I=1:1:3 F J=1:1:2 W I,J I I=2,J=1 G OUT Q
OUT W "!" Q"""
        result = execute_mumps(source)
        assert result.output == "111221!"
        assert result.success is True

    def test_triple_nested_for_exit(self, execute_mumps):
        """T082: Triple nested FOR loop exit via cross-label GOTO.

        MUMPS: TEST F I=1:1:2 F J=1:1:2 F K=1:1:2 W I,J,K I I=1,J=2,K=1 G OUT Q / OUT W "!" Q
        Expected: "111112121!" (writes until I=1,J=2,K=1 then exits all three loops)
        """
        source = """TEST F I=1:1:2 F J=1:1:2 F K=1:1:2 W I,J,K I I=1,J=2,K=1 G OUT Q
OUT W "!" Q"""
        result = execute_mumps(source)
        assert result.output == "111112121!"
        assert result.success is True

    def test_loop_variable_visible_in_target(self, execute_mumps):
        """T083: Loop variable is visible in target label after exit.

        MUMPS: TEST F I=1:1:10 I I=5 G DONE Q / DONE W "I=",I Q
        Expected: "I=5" (I is accessible in DONE label via RoutineState)
        """
        source = """TEST F I=1:1:10 I I=5 G DONE Q
DONE W "I=",I Q"""
        result = execute_mumps(source)
        assert result.output == "I=5"
        assert result.success is True


@pytest.mark.codegen
class TestRoutineStateSharedVariables:
    """Phase 10: RoutineState class maintains variable visibility (T090-T097)."""

    def test_routinestate_dataclass_generated(self):
        """T090/T094: RoutineState dataclass generated when needs_trampoline=True."""
        source = """TEST S X=1 G NEXT Q
NEXT W X Q"""
        code = generate_python(source)

        assert "@dataclass" in code
        assert "class RoutineState:" in code
        assert '"""Shared state for cross-label variable visibility."""' in code

    def test_routinestate_simple_variable_types(self):
        """T091/T095: Simple variables have Any type with None default."""
        source = """TEST S X=1,Y=2,Z=3 G NEXT Q
NEXT W X+Y+Z Q"""
        code = generate_python(source)

        # Simple variables should be typed as Any with None default
        assert "X: Any = None" in code
        assert "Y: Any = None" in code
        assert "Z: Any = None" in code

    def test_routinestate_array_variable_types(self):
        """T092/T095: Array variables have MArray type with factory default."""
        source = """TEST S A(1)=10,B(1,2)=20 G NEXT Q
NEXT W A(1)+B(1,2) Q"""
        code = generate_python(source)

        # Array variables should use MArray with field factory
        assert "A: MArray = field(default_factory=MArray)" in code
        assert "B: MArray = field(default_factory=MArray)" in code
        # Should import MArray
        assert "from m2py.runtime import MArray" in code

    def test_label_functions_return_tuple(self):
        """T093: Label functions accept state and return (next_label, state) tuple."""
        source = """TEST S X=1 G NEXT Q
NEXT W X Q"""
        code = generate_python(source)

        # Label functions should have correct signature
        assert "def _TEST(state) -> Tuple[Optional[str], RoutineState]:" in code
        assert "def _NEXT(state) -> Tuple[Optional[str], RoutineState]:" in code
        # Should return tuple with None for QUIT
        assert "return (None, state)" in code
        # Should return tuple with label name for GOTO
        assert 'return ("NEXT", state)' in code

    def test_state_passed_through_trampoline(self):
        """T096: State object passed through trampoline dispatch loop."""
        source = """TEST S X=1 G NEXT Q
NEXT W X Q"""
        code = generate_python(source)

        # Trampoline should initialize state and pass through
        assert "state = RoutineState()" in code
        assert "label, state = func(state)" in code

    def test_routinestate_enables_ide_autocomplete(self):
        """T097: RoutineState uses @dataclass with typed fields for IDE support."""
        source = """TEST S X=1,A(1)=2 G NEXT Q
NEXT W X+A(1) Q"""
        code = generate_python(source)

        # Verify dataclass decorator and proper typing imports
        assert "from dataclasses import dataclass, field" in code
        assert "from typing import Any, Optional, Tuple" in code
        assert "@dataclass" in code
        # Fields should be properly typed (not just dict keys)
        assert "X: Any" in code
        assert "A: MArray" in code
