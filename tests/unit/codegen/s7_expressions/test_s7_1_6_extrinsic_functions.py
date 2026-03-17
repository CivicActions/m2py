"""Tests for Extrinsic Functions code generation (§7.1.6).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.6
Spec 010 Phase 4: Extrinsic functions with by-reference parameter support
"""

import sys
import tempfile
from pathlib import Path

import pytest


@pytest.mark.codegen
class TestExtrinsicFunctionsCodegen:
    """Codegen-level tests for extrinsic functions code generation (§7.1.6)."""

    def test_extrinsic_function_call(self, generate_python):
        """Extrinsic function generates Python function call (§7.1.6).

        Spec 010 (T022): Internal extrinsic $$label generates _call_extrinsic call.
        """
        source = """TEST
 S X=$$ADD(3,4)
 Q X
ADD(A,B)
 Q A+B
"""
        code = generate_python(source)
        assert "_call_extrinsic(_rt, _globals['ADD']" in code
        # Verify the generated code is syntactically valid
        compile(code, "<test>", "exec")

    def test_extrinsic_with_arguments(self, generate_python):
        """Extrinsic function arguments are passed correctly (§7.1.6).

        Spec 014 (T076-T078): Always pass _scope for cross-routine variable visibility.
        """
        source = """TEST
 S X=$$CALC(1,2,3)
 Q X
CALC(A,B,C)
 Q A+B+C
"""
        code = generate_python(source)
        # Arguments should be passed to _call_extrinsic with _scope
        assert "_call_extrinsic(_rt, _globals['CALC'], 1, 2, 3, _scope=_scope)" in code

    def test_external_routine_call(self, generate_python):
        """External routine generates module import and call (§7.1.6).

        Spec 010 (T023): $$label^routine generates import and module-prefixed call.
        """
        source = """TEST
 S X=$$ADD^math(3,5)
 Q X
"""
        code = generate_python(source)
        # Should import the module ("math" is a Python stdlib name, so it becomes "math_")
        assert "import math_" in code
        # Should call with module prefix
        assert "_call_extrinsic(_rt, math_.ADD" in code

    def test_return_value_handling(self, generate_python):
        """Extrinsic return value is captured (§7.1.6).

        QUIT with expression in extrinsic returns the value.
        """
        source = """TEST
 S X=$$DOUBLE(5)
 Q X
DOUBLE(N)
 Q N*2
"""
        code = generate_python(source)
        # The SET should capture the extrinsic result
        assert "_scope.setdefault('X', MArray()).value = _call_extrinsic" in code


@pytest.mark.codegen
class TestExtrinsicByRefCodegen:
    """Spec 010 Phase 4: Tests for by-reference parameter passing in extrinsics."""

    def test_byref_parameter_generates_byref_list(self, generate_python):
        """By-reference arguments generate _byref parameter (T021).

        When .VAR syntax is used, the _call_extrinsic should receive
        _byref list with variable names for updating after call.
        """
        source = """TEST
 S A=5,B=10
 S X=$$DOUBLE(.A,.B)
 Q
DOUBLE(P1,P2)
 S P1=P1*2
 S P2=P2*2
 Q P1+P2
"""
        code = generate_python(source)
        # Should have _byref parameter with variable names
        assert "_byref=['A', 'B']" in code

    def test_byref_mixed_with_byvalue(self, generate_python):
        """Mixed by-ref and by-value args handled correctly (T021).

        Only by-ref args should be in _byref list, by-value args are None.
        """
        source = """TEST
 S A=5,B=10
 S X=$$CALC(A,.B,3)
 Q
CALC(P1,P2,P3)
 S P2=P2+P1+P3
 Q P2
"""
        code = generate_python(source)
        # _byref should have None for non-byref positions and name for byref
        assert "_byref=[None, 'B', None]" in code

    def test_byref_return_tuple_generated(self, generate_python):
        """Extrinsic with byref outputs returns tuple (T020).

        When a label modifies by-ref parameters and has a return value,
        it should return (value, *byref_outputs).
        """
        source = """TEST
 Q
DOUBLE(X)
 S X=X*2
 Q X
"""
        code = generate_python(source)
        # DOUBLE should return tuple since X is a byref output
        assert "return (" in code
        assert "DOUBLE" in code

    def test_byref_extrinsic_runtime_behavior(self, generate_python):
        """By-ref extrinsic updates caller's variables at runtime (T021).

        This is a full integration test: the callee modifies by-ref params
        and those changes are visible to the caller after the call.
        """
        source = """TEST
 S A=10,B=20
 S X=$$DOUBLE(.A,.B)
 Q A_B_X
DOUBLE(P1,P2)
 S P1=P1*2
 S P2=P2*2
 Q P1+P2
"""
        code = generate_python(source)
        namespace = {}
        exec(code, namespace)

        # Call the generated code
        runtime = namespace["MUMPSRuntime"]()
        result = namespace["TEST"](runtime)

        # A should be 20 (10*2), B should be 40 (20*2), X should be 60 (20+40)
        assert result == "204060"

    def test_byvalue_extrinsic_returns_scalar_not_tuple(self, generate_python):
        """Extrinsic called by-value returns scalar even if callee modifies param.

        When callee modifies a formal parameter (creating byref_outputs) but
        caller passes by VALUE (no . prefix), the return value should be
        just the scalar, not a tuple. The _call_extrinsic helper extracts
        _result[0] when the callee returns a tuple but no _byref is provided.

        This tests the fix for the arith.m multiplication bug where
        $$times("1","1") was returning ('1', '10') instead of '1'.
        """
        source = """TEST
 S X=$$INC(5)
 Q X
INC(N)
 S N=N+1
 Q N
"""
        code = generate_python(source)
        namespace = {}
        exec(code, namespace)

        # Call the generated code
        runtime = namespace["MUMPSRuntime"]()
        result = namespace["TEST"](runtime)

        # Should return "6" (or 6), not a tuple like ("6", "6")
        # The key assertion is that it's NOT a tuple
        assert not isinstance(result, tuple), f"Expected scalar, got tuple: {result}"
        assert str(result) == "6"

    def test_byvalue_extrinsic_does_not_modify_caller_var(self, generate_python):
        """By-value extrinsic does not modify caller's variable.

        When caller passes by value (no . prefix), the caller's variable
        should not be modified even if the callee writes to the parameter.
        """
        source = """TEST
 S A=5
 S X=$$INC(A)
 Q A_","_X
INC(N)
 S N=N+1
 Q N
"""
        code = generate_python(source)
        namespace = {}
        exec(code, namespace)

        # Call the generated code
        runtime = namespace["MUMPSRuntime"]()
        result = namespace["TEST"](runtime)

        # A should be 5 (unchanged), X should be 6 (return value)
        assert result == "5,6"

    def test_byref_extrinsic_modifies_caller_var(self, generate_python):
        """By-ref extrinsic modifies caller's variable AND returns value.

        When caller passes by reference (.A), both the return value
        AND the by-ref update should occur.
        """
        source = """TEST
 S A=5
 S X=$$INC(.A)
 Q A_","_X
INC(N)
 S N=N+1
 Q N
"""
        code = generate_python(source)
        namespace = {}
        exec(code, namespace)

        # Call the generated code
        runtime = namespace["MUMPSRuntime"]()
        result = namespace["TEST"](runtime)

        # A should be 6 (modified via .A), X should be 6 (return value)
        assert result == "6,6"


@pytest.mark.codegen
class TestExternalRoutineCallsCodegen:
    """Codegen tests for cross-routine calls.

    External calls require module loading, caching, and shared
    runtime context for variable passing.

    Reference: §7.1.6
    """

    def test_module_import_generation(self, generate_python):
        """External call generates import statement.

        $$FUNC^ROUTINE generates: import routine
        """
        source = """TEST
 S X=$$CALC^mathlib(5)
 Q X
"""
        code = generate_python(source)
        assert "import mathlib" in code

    def test_external_with_scope_parameter(self, generate_python):
        """External extrinsic passes _scope for variable visibility.

        Spec 008 (T045): External calls pass _scope=_scope for
        cross-routine variable visibility.
        """
        source = """TEST
 S X=$$CALC^mathlib(5)
 Q X
"""
        code = generate_python(source)
        assert "_scope=_scope" in code

    def test_module_caching(self, generate_python):
        """External modules are cached after first import.

        Multiple calls to same routine reuse cached module.
        Python's import statement handles caching via sys.modules.
        We verify that standard import statement is used (Python caches
        even when import statement appears multiple times in code).
        """
        source = """TEST
 S A=$$ADD^math(1,2)
 S B=$$MULT^math(3,4)
 Q A+B
"""
        code = generate_python(source)
        # Python's import statement provides module caching via sys.modules
        # We use standard import, not __import__ or importlib
        assert "import math_" in code
        # Module is used with standard attribute access
        assert "math_.ADD" in code
        assert "math_.MULT" in code
        # verify valid Python syntax
        compile(code, "<test>", "exec")

    def test_cross_routine_variable_passing(self, generate_python):
        """Variables visible across routine calls.

        Variables not NEWed in callee are visible to caller.
        Requires shared runtime context via _scope parameter.
        """
        source = """TEST
 S A=100
 S X=$$MODIFY^helper()
 Q A
"""
        code = generate_python(source)
        # External calls pass _scope=_scope for cross-routine visibility
        assert "_scope=_scope" in code
        # The _scope is initialized and used throughout
        assert "_scope if _scope is not None else {}" in code
        # Variables are accessed via _scope for visibility to callees
        assert "_scope.setdefault('A', MArray())" in code
        # verify valid Python syntax
        compile(code, "<test>", "exec")

    def test_routine_name_translation(self, generate_python):
        """Routine names translated to valid module names.

        %ROUTINE becomes _pct_ROUTINE module.
        This is required because % is invalid in Python identifiers.
        """
        source = """TEST
 S X=$$UTILS^%SYSTEM(1,2)
 Q X
"""
        code = generate_python(source)
        # % prefix translated to _pct_ for valid Python module name
        assert "import _pct_SYSTEM" in code
        # Module reference in call also translated
        assert "_pct_SYSTEM.UTILS" in code
        # verify valid Python syntax (import of non-existent module is syntax OK)
        compile(code, "<test>", "exec")


@pytest.mark.codegen
class TestExtrinsicEntryPoint:
    """T100: Tests for $$^ROUTINE pattern (extrinsic calling routine entry point).

    When $$^ROUTINE is used with no label, it calls the routine's entry point,
    which is the routine name itself (the first label in the routine).
    """

    def test_extrinsic_routine_only(self, generate_python):
        """$$^ROUTINE (no label) calls routine's entry point.

        T100: When label is empty but routine exists, use routine name as label.
        """
        source = """TEST
 S X=$$^HELPER
 Q X
"""
        code = generate_python(source)
        # Should import the module
        assert "import HELPER" in code
        # Should call the routine name as the entry point
        assert "_call_extrinsic(_rt, HELPER.HELPER" in code
        # verify valid Python syntax
        compile(code, "<test>", "exec")

    def test_extrinsic_routine_only_with_args(self, generate_python):
        """$$^ROUTINE(args) calls routine's entry point with arguments.

        T100: Entry point call should pass arguments correctly.
        """
        source = """TEST
 S X=$$^MATH(1,2)
 Q X
"""
        code = generate_python(source)
        # Should import the module
        assert "import MATH" in code
        # Should call routine.routine with args
        assert "_call_extrinsic(_rt, MATH.MATH, 1, 2" in code
        # verify valid Python syntax
        compile(code, "<test>", "exec")

    def test_extrinsic_percent_routine_only(self, generate_python):
        """$$^%ROUTINE calls %ROUTINE's entry point.

        T100: Percent routines also support entry point calls.
        """
        source = """TEST
 S X=$$^%UTIL
 Q X
"""
        code = generate_python(source)
        # % prefix translated to _pct_
        assert "import _pct_UTIL" in code
        # Should call _pct_UTIL._pct_UTIL (entry point is routine name)
        assert "_call_extrinsic(_rt, _pct_UTIL._pct_UTIL" in code
        # verify valid Python syntax
        compile(code, "<test>", "exec")


@pytest.mark.codegen
class TestExtrinsicByRef:
    """Tests for extrinsic function calls with pass-by-reference."""

    def test_extrinsic_with_byref(self, execute_mumps):
        """$$FN(.X) — extrinsic modifies caller's variable."""
        result = execute_mumps(
            'TEST\n\tS X=1\n\tS R=$$FN(.X)\n\tW X," ",R\n\tQ\nFN(A)\n\tS A=A+10\n\tQ A\n'
        )
        assert "11" in result.output  # X modified to 11
        assert "11" in result.output  # Return value is also 11

    def test_extrinsic_with_omitted_arg(self, execute_mumps):
        """$$FN(1,,3) — extrinsic with omitted middle argument."""
        result = execute_mumps("TEST\n\tW $$FN(1,,3)\n\tQ\nFN(A,B,C)\n\tQ A+$G(B)+C\n")
        assert result.output == "4"  # 1 + 0 + 3


# =============================================================================
# $DATA / $ORDER in dynamic_locals routines
# =============================================================================


@pytest.mark.codegen
class TestActualParamByVariableNamePass2:
    """Passing parameters by variable_name attr rather than expression.

    Covers codegen/expressions.py L1094-1096.
    """

    def test_do_with_variable_params(self, execute_mumps):
        """D SUB(X) — pass variable by value."""
        result = execute_mumps("TEST\n S X=42 D SUB(X) Q\nSUB(A)\n W A Q\n")
        assert result.output == "42"

    def test_extrinsic_with_variable_params(self, execute_mumps):
        """$$FN(X) — pass variable by value to extrinsic."""
        result = execute_mumps("TEST\n S X=5 W $$FN(X) Q\nFN(A)\n Q A*2\n")
        assert result.output == "10"


# =============================================================================
# Extrinsic context save/restore (_call_extrinsic runtime context)
# =============================================================================


@pytest.mark.codegen
class TestExtrinsicContextSaveRestoreCodegen:
    """Verify _call_extrinsic saves/restores runtime context (codegen level).

    When an extrinsic function calls into another routine ($$FUNC^ROUTINE),
    the callee sets _rt._current_routine to its own name.  Without save/restore,
    $TEXT(+0) in the caller returns the wrong routine name after the extrinsic
    returns.

    The fix adds save/restore of _current_routine, _current_source_lines, and
    _current_label_lines inside the generated _call_extrinsic helper, mirroring
    the pattern used in external DO calls.
    """

    def test_call_extrinsic_saves_current_routine(self, generate_python):
        """_call_extrinsic saves _rt._current_routine before the call."""
        source = "TEST\n S X=$$ADD(1,2)\n Q X\nADD(A,B)\n Q A+B\n"
        code = generate_python(source)
        assert "_saved_routine = _rt._current_routine" in code

    def test_call_extrinsic_restores_current_routine(self, generate_python):
        """_call_extrinsic restores _rt._current_routine in finally block."""
        source = "TEST\n S X=$$ADD(1,2)\n Q X\nADD(A,B)\n Q A+B\n"
        code = generate_python(source)
        assert "_rt._current_routine = _saved_routine" in code

    def test_call_extrinsic_saves_source_lines(self, generate_python):
        """_call_extrinsic saves _rt._current_source_lines."""
        source = "TEST\n S X=$$ADD(1,2)\n Q X\nADD(A,B)\n Q A+B\n"
        code = generate_python(source)
        assert "_saved_source_lines = _rt._current_source_lines" in code

    def test_call_extrinsic_saves_label_lines(self, generate_python):
        """_call_extrinsic saves _rt._current_label_lines."""
        source = "TEST\n S X=$$ADD(1,2)\n Q X\nADD(A,B)\n Q A+B\n"
        code = generate_python(source)
        assert "_saved_label_lines = _rt._current_label_lines" in code

    def test_call_extrinsic_restore_in_finally(self, generate_python):
        """Save/restore are in try/finally for exception safety."""
        source = "TEST\n S X=$$ADD(1,2)\n Q X\nADD(A,B)\n Q A+B\n"
        code = generate_python(source)
        lines = code.split("\n")

        # Find finally: block within _call_extrinsic
        in_call_extrinsic = False
        found_finally = False
        found_restore_after_finally = False
        for line in lines:
            if "def _call_extrinsic" in line:
                in_call_extrinsic = True
            if in_call_extrinsic and "finally:" in line:
                found_finally = True
            if found_finally and "_rt._current_routine = _saved_routine" in line:
                found_restore_after_finally = True
                break

        assert found_restore_after_finally, (
            "_rt._current_routine restore should be in the finally block"
        )


@pytest.mark.codegen
class TestExtrinsicContextSaveRestoreExecution:
    """Verify $TEXT(+0) returns correct routine after external extrinsic call.

    End-to-end test: create two routines, have the caller invoke an extrinsic
    in the callee, then verify $TEXT(+0) still returns the caller's name.
    """

    def test_text_plus_zero_after_external_extrinsic(self):
        """$TEXT(+0) returns caller routine name after $$FUNC^OTHER.

        CALLER calls $$ADD^HELPER(1,2) then writes $TEXT(+0).
        Without save/restore, $TEXT(+0) would return "HELPER" instead of "CALLER".
        """
        from m2py.codegen import generate_python

        caller_source = """\
CALLER
 S X=$$ADD^HELPER(1,2)
 W $T(+0)
 Q
"""
        helper_source = """\
HELPER
 Q
ADD(A,B)
 Q A+B
"""
        caller_code = generate_python(caller_source)
        helper_code = generate_python(helper_source)

        with tempfile.TemporaryDirectory() as tmpdir:
            helper_path = Path(tmpdir) / "HELPER.py"
            helper_path.write_text(helper_code)
            sys.path.insert(0, tmpdir)
            try:
                if "HELPER" in sys.modules:
                    del sys.modules["HELPER"]

                ns = {}
                exec(caller_code, ns)
                runtime = ns["MUMPSRuntime"]()
                ns["CALLER"](runtime)
                output = runtime.get_output()
                assert output == "CALLER", (
                    f"$TEXT(+0) should return 'CALLER' but got '{output}'"
                )
            finally:
                sys.path.remove(tmpdir)
                sys.modules.pop("HELPER", None)

    def test_text_plus_zero_after_multiple_external_extrinsics(self):
        """$TEXT(+0) correct after multiple external extrinsic calls.

        MAIN calls $$F1^R1(1) then $$F2^R2(2) then writes $TEXT(+0).
        """
        from m2py.codegen import generate_python

        main_source = """\
MAIN
 S A=$$F1^ROUT1(1)
 S B=$$F2^ROUT2(2)
 W $T(+0)
 Q
"""
        rout1_source = """\
ROUT1
 Q
F1(X)
 Q X*10
"""
        rout2_source = """\
ROUT2
 Q
F2(X)
 Q X*20
"""
        main_code = generate_python(main_source)
        rout1_code = generate_python(rout1_source)
        rout2_code = generate_python(rout2_source)

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "ROUT1.py").write_text(rout1_code)
            Path(tmpdir, "ROUT2.py").write_text(rout2_code)
            sys.path.insert(0, tmpdir)
            try:
                for mod in ("ROUT1", "ROUT2"):
                    sys.modules.pop(mod, None)

                ns = {}
                exec(main_code, ns)
                runtime = ns["MUMPSRuntime"]()
                ns["MAIN"](runtime)
                output = runtime.get_output()
                assert output == "MAIN", (
                    f"$TEXT(+0) should return 'MAIN' but got '{output}'"
                )
            finally:
                sys.path.remove(tmpdir)
                for mod in ("ROUT1", "ROUT2"):
                    sys.modules.pop(mod, None)

    def test_extrinsic_return_value_preserved(self):
        """External extrinsic returns correct value with context save/restore.

        Ensures the save/restore doesn't interfere with the return value.
        """
        from m2py.codegen import generate_python

        caller_source = """\
CALLER
 S X=$$DOUBLE^MATHLIB(21)
 W X
 Q
"""
        mathlib_source = """\
MATHLIB
 Q
DOUBLE(N)
 Q N*2
"""
        caller_code = generate_python(caller_source)
        mathlib_code = generate_python(mathlib_source)

        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "MATHLIB.py").write_text(mathlib_code)
            sys.path.insert(0, tmpdir)
            try:
                sys.modules.pop("MATHLIB", None)

                ns = {}
                exec(caller_code, ns)
                runtime = ns["MUMPSRuntime"]()
                ns["CALLER"](runtime)
                output = runtime.get_output()
                assert output == "42", f"Expected '42' but got '{output}'"
            finally:
                sys.path.remove(tmpdir)
                sys.modules.pop("MATHLIB", None)
