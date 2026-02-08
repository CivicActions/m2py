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

    def test_unresolved_goto_in_reachable_label_blocked(self):
        """Unresolved GOTO in reachable code should raise error."""
        source = """TEST
 D PROBLEM
 Q
PROBLEM
 G NONEXISTENT
 Q
"""
        # This SHOULD raise UnsupportedFeatureError
        from m2py.codegen import UnsupportedFeatureError

        with pytest.raises(UnsupportedFeatureError, match="UNRESOLVED GOTO"):
            generate_python(source)

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
