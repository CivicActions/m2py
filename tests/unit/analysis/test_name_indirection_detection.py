"""Tests for name indirection detection in variable analysis.

Tests the _routine_has_name_indirection_on_locals and
_expr_has_name_indirection_on_local functions that detect when
a routine uses name indirection that references local variables.

Reference: When indirection like @X reads another local variable,
the runtime needs dynamic variable access (state._locals dict) rather
than static Python variables in TRAMPOLINE mode.

Note: The current implementation `_routine_has_name_indirection_on_locals`
specifically checks for:
1. DO statements with indirect offsets (D LABEL+@N)
2. DO statements with nested indirection in the label (D @(@X))

Simple indirect DO like "D @L" is handled differently in codegen and
doesn't trigger has_name_indirection_on_locals.
"""

from m2py.parser import MUMPSParser
from m2py.analysis.variables import (
    _routine_has_name_indirection_on_locals,
    _expr_has_name_indirection_on_local,
    analyze_variables,
)


def parse(source: str):
    """Helper to parse MUMPS source code."""
    parser = MUMPSParser()
    return parser.parse(source)


# =============================================================================
# _routine_has_name_indirection_on_locals Tests
# =============================================================================


class TestRoutineHasNameIndirectionOnLocals:
    """Tests for routine-level name indirection detection."""

    def test_no_indirection(self):
        """Routine without indirection returns False."""
        routine = parse("TEST\n W 1 Q\n")
        assert _routine_has_name_indirection_on_locals(routine) is False

    def test_do_with_simple_label(self):
        """D LABEL without indirection returns False."""
        routine = parse("TEST\n D SUB Q\nSUB W 1 Q\n")
        assert _routine_has_name_indirection_on_locals(routine) is False

    def test_simple_indirect_do_not_detected(self):
        """Simple D @L is NOT detected by this function.

        Simple indirect DO like D @L where L is local is handled
        by resolve_nested_indirection at runtime, not by this detector.
        This function specifically looks for complex cases like offset
        indirection.
        """
        routine = parse('TEST\n S L="SUB" D @L Q\nSUB W 1 Q\n')
        # This returns False because it's a simple indirect DO
        # The function only detects offset indirection and nested indirection
        result = _routine_has_name_indirection_on_locals(routine)
        assert result is False

    def test_do_with_offset_indirection(self):
        """D LABEL+@N where N is local returns True."""
        routine = parse("TEST\n S N=2 D SUB+@N Q\nSUB\n W 1 Q\n")
        result = _routine_has_name_indirection_on_locals(routine)
        assert result is True

    def test_empty_routine(self):
        """Empty routine returns False."""
        routine = parse("TEST\n Q\n")
        assert _routine_has_name_indirection_on_locals(routine) is False


# =============================================================================
# _expr_has_name_indirection_on_local Tests
# =============================================================================


class TestExprHasNameIndirectionOnLocal:
    """Tests for expression-level name indirection detection."""

    def test_none_input(self):
        """None input returns False."""
        assert _expr_has_name_indirection_on_local(None) is False

    def test_non_indirection_expr(self):
        """Non-indirection expression returns False."""
        from m2py.asg.expressions import MLiteral

        expr = MLiteral(value="test", literal_type=None)
        assert _expr_has_name_indirection_on_local(expr) is False

    def test_circular_reference_protection(self):
        """Circular references don't cause infinite recursion."""
        # Create an expression that references itself
        from m2py.asg.expressions import MBinaryOp

        expr = MBinaryOp(left=None, operator="+", right=None)
        expr.left = expr  # Circular reference
        # Should not hang - visited set should prevent infinite recursion
        result = _expr_has_name_indirection_on_local(expr)
        assert result is False  # No indirection found


# =============================================================================
# Integration: analyze_variables sets flag
# =============================================================================


class TestAnalyzeVariablesSetsFlag:
    """Integration tests verifying analyze_variables sets the flag."""

    def test_flag_set_for_offset_indirection(self):
        """analyze_variables sets flag for offset indirection."""
        routine = parse("TEST\n S N=2 D SUB+@N Q\nSUB\n W 1 Q\n")
        analyze_variables(routine)
        assert routine.has_name_indirection_on_locals is True

    def test_flag_false_when_no_indirection(self):
        """Flag is False when no indirection present."""
        routine = parse("TEST\n W 1 Q\n")
        analyze_variables(routine)
        assert routine.has_name_indirection_on_locals is False

    def test_flag_false_for_value_indirection_only(self):
        """Value indirection like W @X doesn't set the flag.

        The flag is specifically for NAME indirection that affects
        DO/GOTO targets, not general value indirection.
        """
        routine = parse('TEST\n S X="Hello" W @X Q\n')
        analyze_variables(routine)
        # WRITE @X is value indirection, not name indirection for DO/GOTO
        assert routine.has_name_indirection_on_locals is False

    def test_flag_false_for_simple_indirect_do(self):
        """Simple D @X doesn't set the flag.

        Simple indirect DO is handled differently in codegen and doesn't
        require the dynamic_locals mode that this flag triggers.
        """
        routine = parse('TEST\n S X="FOO" D @X Q\nFOO W 1 Q\n')
        analyze_variables(routine)
        assert routine.has_name_indirection_on_locals is False
