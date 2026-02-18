"""Unit tests for label reachability analysis in codegen.

Tests for _get_reachable_labels which determines which labels are reachable
from the routine entry point. This is used to skip UNRESOLVED GOTO checking
in labels that are only callable externally (dead code from entry perspective).
"""

import pytest
from m2py.codegen import generate_python, _get_reachable_labels
from m2py.parser import MUMPSParser
from m2py.asg import MRoutine


def _parse_and_analyze(source: str) -> MRoutine:
    """Parse and analyze MUMPS source, returning the routine object."""
    parser = MUMPSParser()
    routine = parser.parse(source)

    # Find first non-empty label name for routine name
    if routine.labels:
        for label in routine.labels:
            if label.name:
                routine.name = label.name
                break

    # Run analysis passes (same as generate_python)
    parser.resolve_references(routine)
    parser.classify_gotos(routine)
    parser.analyze_for_loops(routine)
    parser.analyze_quit_context(routine)
    parser.analyze_variables(routine, compute_transitive=True)
    parser.compute_signatures(routine)

    return routine


@pytest.mark.codegen
class TestGetReachableLabels:
    """Tests for _get_reachable_labels function."""

    def test_single_label_routine(self):
        """Single label routine has just that label reachable."""
        source = """TEST
 W "Hello"
 Q
"""
        routine = _parse_and_analyze(source)
        reachable = _get_reachable_labels(routine)
        assert reachable == {"TEST"}

    def test_do_call_makes_label_reachable(self):
        """Labels called via DO are reachable."""
        source = """TEST
 D SUB
 Q
SUB
 W "sub"
 Q
"""
        routine = _parse_and_analyze(source)
        reachable = _get_reachable_labels(routine)
        assert "TEST" in reachable
        assert "SUB" in reachable

    def test_goto_makes_label_reachable(self):
        """Labels targeted by GOTO are reachable."""
        source = """TEST
 G END
 W "not reached"
END
 Q
"""
        routine = _parse_and_analyze(source)
        reachable = _get_reachable_labels(routine)
        assert "TEST" in reachable
        assert "END" in reachable

    def test_unreachable_label(self):
        """Labels not called or jumped to are not reachable."""
        source = """TEST
 W "test"
 Q
UNUSED
 W "never called"
 Q
"""
        routine = _parse_and_analyze(source)
        reachable = _get_reachable_labels(routine)
        assert "TEST" in reachable
        assert "UNUSED" not in reachable

    def test_external_call_does_not_make_local_label_reachable(self):
        """D SUB^OTHER doesn't add SUB to local reachable set."""
        source = """TEST
 D SUB^OTHER
 Q
SUB
 W "local sub"
 Q
"""
        routine = _parse_and_analyze(source)
        reachable = _get_reachable_labels(routine)
        assert "TEST" in reachable
        # SUB is not reachable because D SUB^OTHER calls external routine
        assert "SUB" not in reachable

    def test_fallthrough_makes_next_label_reachable(self):
        """Labels that fall through to next label make it reachable."""
        source = """TEST
 W "test"
NEXT
 W "next"
 Q
"""
        routine = _parse_and_analyze(source)
        reachable = _get_reachable_labels(routine)
        assert "TEST" in reachable
        assert "NEXT" in reachable

    def test_transitive_reachability(self):
        """Reachability is transitive through call chains."""
        source = """TEST
 D A
 Q
A
 D B
 Q
B
 D C
 Q
C
 Q
UNREACHABLE
 Q
"""
        routine = _parse_and_analyze(source)
        reachable = _get_reachable_labels(routine)
        assert "TEST" in reachable
        assert "A" in reachable
        assert "B" in reachable
        assert "C" in reachable
        assert "UNREACHABLE" not in reachable


@pytest.mark.codegen
class TestUnresolvedGotoInDeadCode:
    """Test that unresolved GOTOs in unreachable labels don't block transpilation."""

    def test_unresolved_goto_in_unreachable_label_allowed(self):
        """Unresolved GOTO in dead code should not prevent transpilation."""
        # This simulates V1NST1 pattern where GOTO section has unresolved targets
        source = """TEST
 W "test"
 Q
DEADCODE
 ; This label has GOTO to non-existent label
 G NONEXISTENT
 Q
"""
        # This should NOT raise UnsupportedFeatureError
        result = generate_python(source)
        assert "def TEST(" in result
        # DEADCODE label should still be generated (for external callers)
        assert "def DEADCODE(" in result

    def test_unresolved_goto_in_reachable_label_produces_runtime_error(self):
        """Unresolved GOTO in reachable code should compile but raise at runtime."""
        source = """TEST
 D PROBLEM
 Q
PROBLEM
 G NONEXISTENT
 Q
"""
        # Should now transpile successfully (no compile-time rejection)
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = generate_python(source)

        # Generated code should contain LabelNotFoundError at the GOTO site
        assert 'raise LabelNotFoundError("NONEXISTENT"' in result
        # The routine should still compile as valid Python
        import ast

        ast.parse(result)

    def test_v1nst1_pattern_transpiles(self):
        """V1NST1-like routine with unreachable GOTO section should transpile."""
        source = """V1NST1
 W "test"
 D SUB
 Q
SUB
 W "sub"
 Q
 ; The following is only called externally
GOTO
 S V="test"
 G EXTERNAL_LABEL
 Q
"""
        # Should transpile without error - GOTO label is unreachable from entry
        result = generate_python(source)
        assert "def V1NST1(" in result
        assert "def SUB(" in result


@pytest.mark.codegen
class TestUnresolvedGotoFallback:
    """Phase 11: UNRESOLVED GOTO fallback — compile-time rejection → runtime error."""

    def test_simple_unresolved_goto_compiles(self):
        """A routine with GOTO to a non-existent label should compile."""
        source = """TEST
 S X=1
 I X G EXIT
 W "done"
 Q
"""
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = generate_python(source)

        assert 'raise LabelNotFoundError("EXIT"' in result
        import ast

        ast.parse(result)

    def test_unresolved_goto_warning_emitted(self):
        """Transpiling a routine with UNRESOLVED GOTO should emit a warning."""
        source = """TEST
 D REACHABLE
 Q
REACHABLE
 G MISSING
 Q
"""
        import warnings

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            generate_python(source)

        # Expect at least one warning about UNRESOLVED GOTO
        goto_warnings = [x for x in w if "UNRESOLVED GOTO" in str(x.message)]
        assert len(goto_warnings) >= 1
        assert "MISSING" in str(goto_warnings[0].message)
        assert "LabelNotFoundError" in str(goto_warnings[0].message)

    def test_unresolved_goto_with_postcondition_compiles(self):
        """G EXIT:cond with missing EXIT compiles but raises at runtime."""
        source = """TEST
 S X=1
 G MISSING:X=1
 W "fell through"
 Q
"""
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = generate_python(source)

        # The GOTO to MISSING should produce a LabelNotFoundError
        assert "LabelNotFoundError" in result
        import ast

        ast.parse(result)

    def test_multi_target_goto_with_unresolved_target(self):
        """G EXISTING:cond,MISSING:cond2 where MISSING doesn't exist."""
        source = """TEST
 N X S X=0
 G DONE:X=0,MISSING:X=1
 Q
DONE
 W "done"
 Q
"""
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = generate_python(source)

        # Should compile (MISSING path may never be taken)
        import ast

        ast.parse(result)
        # The MISSING target should produce LabelNotFoundError
        assert "LabelNotFoundError" in result

    def test_xecute_goto_to_existing_label_works(self):
        """X 'G B' where B is a label in the routine should work (not raise)."""
        source = """TEST
 S VCOMP=""
 X "G B","S VCOMP=VCOMP_7"
 W VCOMP
 Q
A S VCOMP=VCOMP_4 Q
B S VCOMP=VCOMP_6 Q
"""
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = generate_python(source)

        # Should NOT contain LabelNotFoundError for B
        # B is a valid label in the routine — reachable via XECUTE
        assert 'LabelNotFoundError("B"' not in result
        import ast

        ast.parse(result)

    def test_unresolved_goto_in_unreachable_still_allowed(self):
        """GOTO to missing label in unreachable code should still transpile."""
        source = """TEST
 W "test"
 Q
DEAD
 G NOWHERE
 Q
"""
        # Unreachable labels with unresolved GOTOs should work as before
        result = generate_python(source)
        assert "def TEST(" in result

    def test_a1bfjobr_pattern(self):
        """A1BFJOBR pattern: G EXIT guarded by IF, EXIT not in routine.

        This is the most common VistA pattern — the routine typically
        calls EXIT from another routine externally but references it
        locally behind conditions.
        """
        source = """A1BFJOBR
 ;;V1.0
EN
 S U="^"
 I 0 G EXIT
 W "done"
 Q
"""
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = generate_python(source)

        assert 'raise LabelNotFoundError("EXIT"' in result
        import ast

        ast.parse(result)

    def test_multiple_unresolved_gotos_in_same_routine(self):
        """Routine with multiple UNRESOLVED GOTOs all compile."""
        source = """TEST
 D SUB1
 D SUB2
 Q
SUB1
 I 0 G MISSING1
 Q
SUB2
 I 0 G MISSING2
 Q
"""
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = generate_python(source)

        assert 'LabelNotFoundError("MISSING1"' in result
        assert 'LabelNotFoundError("MISSING2"' in result
        import ast

        ast.parse(result)

    def test_runtime_error_raised_when_unresolved_goto_reached(self):
        """When the GOTO to a missing label is actually reached, LabelNotFoundError fires."""
        import warnings

        source = """TEST
 G MISSING
 Q
"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            code = generate_python(source)

        # Execute the generated code — it should raise LabelNotFoundError
        from m2py.runtime import MUMPSRuntime, LabelNotFoundError, run_with_goto_support

        ns = {}
        exec(code, ns)
        rt = MUMPSRuntime()
        rt._capture_output = True
        rt._current_routine = "TEST"
        rt._current_source_lines = ns.get("_source_lines", [])
        rt._current_label_lines = ns.get("_label_lines", {})

        with pytest.raises(LabelNotFoundError, match="MISSING"):
            run_with_goto_support(ns["TEST"], rt, {})

    def test_unreached_unresolved_goto_does_not_error(self):
        """When the GOTO to a missing label is NOT reached, no error occurs."""
        import warnings

        source = """TEST
 W "OK"
 Q
DEAD
 G MISSING
 Q
"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            code = generate_python(source)

        # Execute — should succeed (DEAD label is never reached)
        from m2py.runtime import MUMPSRuntime, run_with_goto_support

        ns = {}
        exec(code, ns)
        rt = MUMPSRuntime()
        rt._capture_output = True
        rt._current_routine = "TEST"
        rt._current_source_lines = ns.get("_source_lines", [])
        rt._current_label_lines = ns.get("_label_lines", {})

        # Should not raise
        run_with_goto_support(ns["TEST"], rt, {})
        assert rt.get_output() == "OK"

    def test_guarded_unresolved_goto_not_reached(self):
        """G MISSING:0 — postcondition is false, GOTO not taken, no error."""
        import warnings

        source = """TEST
 S X=0
 I X G MISSING
 W "OK"
 Q
"""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            code = generate_python(source)

        from m2py.runtime import MUMPSRuntime, run_with_goto_support

        ns = {}
        exec(code, ns)
        rt = MUMPSRuntime()
        rt._capture_output = True
        rt._current_routine = "TEST"
        rt._current_source_lines = ns.get("_source_lines", [])
        rt._current_label_lines = ns.get("_label_lines", {})

        # The IF X is 0 (false), so GOTO MISSING is never taken
        run_with_goto_support(ns["TEST"], rt, {})
        assert rt.get_output() == "OK"
