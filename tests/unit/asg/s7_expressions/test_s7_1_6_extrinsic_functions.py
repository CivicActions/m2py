"""Tests for Extrinsic Functions ASG analysis (§7.1.6).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.6
"""

import pytest

from m2py.asg import MActualParameter, PassingMode
from m2py.asg.statements import MSetStatement, MQuitStatement


@pytest.mark.asg
class TestExtrinsicFunctionsAnalysis:
    """ASG-level tests for extrinsic functions analysis (§7.1.6)."""

    def test_extrinsic_function_resolution(self, analyze_routine):
        """Extrinsic function calls are resolved to targets (§7.1.6).

        Tests that $$label^routine syntax correctly captures the target
        label name and routine reference in the ASG.
        """
        routine = analyze_routine("TEST\n S X=$$CALC^UTILS\n Q")

        # Navigate to the SET command's value
        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MSetStatement)
        value = stmt.assignments[0].value

        # Verify target resolution
        assert type(value).__name__ == "ExtrinsicFunction"
        assert value.target is not None
        assert value.target.name == "CALC"
        assert value.target.routine == "UTILS"

    def test_extrinsic_function_arguments(self, analyze_routine):
        """Extrinsic function arguments are correctly analyzed (§7.1.6).

        Tests that arguments with by-value and by-reference passing modes
        are correctly captured in MActualParameter nodes.
        """
        routine = analyze_routine("TEST\n S X=$$CALC(.A,B,.C)\n Q")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MSetStatement)
        value = stmt.assignments[0].value

        assert type(value).__name__ == "ExtrinsicFunction"
        assert len(value.arguments) == 3

        # .A is by-reference
        assert isinstance(value.arguments[0], MActualParameter)
        assert value.arguments[0].passing_mode == PassingMode.BY_REFERENCE
        assert value.arguments[0].variable_name == "A"

        # B is by-value
        assert isinstance(value.arguments[1], MActualParameter)
        assert value.arguments[1].passing_mode == PassingMode.BY_VALUE

        # .C is by-reference
        assert isinstance(value.arguments[2], MActualParameter)
        assert value.arguments[2].passing_mode == PassingMode.BY_REFERENCE
        assert value.arguments[2].variable_name == "C"

    def test_extrinsic_function_return(self, analyze_routine):
        """Extrinsic function return value is tracked (§7.1.6).

        When a routine defines a label that returns a value via QUIT expr,
        callers using $$label receive that value. This test verifies
        we can parse both the call and the return.
        """
        # Test a routine with a QUIT that returns a value
        routine = analyze_routine("TEST(X)\n Q X*2")

        # Find the QUIT statement
        label = routine.labels[0]
        assert label.name == "TEST"

        # Check formal parameter (formal_list is list of strings)
        assert len(label.formal_list) == 1
        assert label.formal_list[0] == "X"

        # Find QUIT with return value
        quit_stmt = label.body.statements[0]
        assert isinstance(quit_stmt, MQuitStatement)
        assert quit_stmt.return_value is not None

    def test_extrinsic_special_variable(self, analyze_routine):
        """Extrinsic special variables ($$) are correctly analyzed (§7.1.6).

        Per §7.1.4.9, $$x (exvar without parentheses) is syntactically
        identical to $$x() - an extrinsic function call with no arguments.
        """
        routine = analyze_routine("TEST\n S X=$$MYFUNC\n Q")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MSetStatement)
        value = stmt.assignments[0].value

        # $$MYFUNC creates an ExtrinsicFunction node
        assert type(value).__name__ == "ExtrinsicFunction"
        assert value.target.name == "MYFUNC"
        # No explicit arguments - empty list
        assert value.arguments == []

    def test_external_routine_reference(self, analyze_routine):
        """External routine references are tracked (§7.1.6).

        Tests that $$label^ROUTINE correctly captures the external
        routine reference for cross-routine extrinsic function calls.
        """
        routine = analyze_routine("TEST\n S A=$$ADD^MATH(1,2),B=$$SUB^MATH(5,3)\n Q")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MSetStatement)
        # Multiple assignments in single SET
        assert len(stmt.assignments) == 2

        # First assignment: $$ADD^MATH(1,2)
        value1 = stmt.assignments[0].value
        assert type(value1).__name__ == "ExtrinsicFunction"
        assert value1.target.name == "ADD"
        assert value1.target.routine == "MATH"
        assert len(value1.arguments) == 2

        # Second assignment: $$SUB^MATH(5,3)
        value2 = stmt.assignments[1].value
        assert type(value2).__name__ == "ExtrinsicFunction"
        assert value2.target.name == "SUB"
        assert value2.target.routine == "MATH"
        assert len(value2.arguments) == 2


@pytest.mark.asg
class TestExtrinsicFunctionASG:
    """Test MExtrinsicFunction ASG node structure."""

    def test_extrinsic_simple(self):
        """$$FUNC creates MExtrinsicFunction with target."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MExtrinsicFunction

        expr = parse_expression("$$MYFUNC")
        result = analyze_expression(expr)

        assert isinstance(result, MExtrinsicFunction)
        assert result.target is not None
        assert result.target.name == "MYFUNC"

    def test_extrinsic_with_routine(self):
        """$$FUNC^ROUTINE has routine reference in target."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MExtrinsicFunction

        expr = parse_expression("$$CALC^UTILS")
        result = analyze_expression(expr)

        assert isinstance(result, MExtrinsicFunction)
        assert result.target is not None
        assert result.target.name == "CALC"
        assert result.target.routine == "UTILS"

    def test_extrinsic_with_args(self):
        """$$FUNC(a,b) has arguments list."""
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MExtrinsicFunction

        expr = parse_expression("$$ADD(1,2)")
        result = analyze_expression(expr)

        assert isinstance(result, MExtrinsicFunction)
        assert len(result.arguments) == 2

    def test_extrinsic_with_byref_args(self):
        """$$FUNC(.X,Y,.Z) preserves by-reference passing mode.

        MUMPS spec 8.1.7: .actualname = call-by-reference format.
        """
        from tests.helpers.parsing import parse_expression
        from m2py.analysis.semantic_analyzer import analyze_expression
        from m2py.asg import MExtrinsicFunction, MActualParameter, PassingMode

        expr = parse_expression("$$CALC(.A,B,.C)")
        result = analyze_expression(expr)

        assert isinstance(result, MExtrinsicFunction)
        assert len(result.arguments) == 3

        # First arg: .A is by-reference
        assert isinstance(result.arguments[0], MActualParameter)
        assert result.arguments[0].passing_mode == PassingMode.BY_REFERENCE
        assert result.arguments[0].variable_name == "A"

        # Second arg: B is by-value
        assert isinstance(result.arguments[1], MActualParameter)
        assert result.arguments[1].passing_mode == PassingMode.BY_VALUE

        # Third arg: .C is by-reference
        assert isinstance(result.arguments[2], MActualParameter)
        assert result.arguments[2].passing_mode == PassingMode.BY_REFERENCE
        assert result.arguments[2].variable_name == "C"
