"""Tests for DO command ASG analysis (§8.2.3).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.3
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MDoStatement, MSetStatement, MWriteStatement


@pytest.mark.asg
class TestDoCommandAnalysis:
    """ASG-level tests for DO command analysis (§8.2.3)."""

    def test_do_target_resolution(self):
        """DO command target is resolved to MLabel (§8.2.3)."""
        stmt = analyze_first_command("D LABEL")

        assert isinstance(stmt, MDoStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].name == "LABEL"

    def test_do_with_arguments(self):
        """DO command arguments are correctly analyzed (§8.2.3)."""
        stmt = analyze_first_command("D FUNC(1,2)")

        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]
        assert target.name == "FUNC"
        assert len(target.arguments) == 2

    def test_do_block_structure(self):
        """DO argumentless block structure is captured (§8.2.3)."""
        parser = MUMPSParser()
        source = """TEST\tD
 . S X=1
 . W X
 S Y=2
"""
        routine = parser.parse(source)

        # Should have 2 statements: DO block and SET
        assert len(routine.labels[0].body.statements) == 2

        do_stmt = routine.labels[0].body.statements[0]
        assert isinstance(do_stmt, MDoStatement)
        assert len(do_stmt.targets) == 0  # Argumentless DO
        assert len(do_stmt.body.statements) == 2
        assert isinstance(do_stmt.body.statements[0], MSetStatement)
        assert isinstance(do_stmt.body.statements[1], MWriteStatement)

        # SET Y=2 should be outside DO block
        assert isinstance(routine.labels[0].body.statements[1], MSetStatement)

    def test_mcall_creation(self):
        """MCall nodes are created with target links (§8.2.3)."""
        from m2py.asg.elements import MCall

        # Simple DO creates MCall target
        stmt = analyze_first_command("D LABEL")
        assert isinstance(stmt, MDoStatement)
        assert len(stmt.targets) == 1
        assert isinstance(stmt.targets[0], MCall)
        assert stmt.targets[0].name == "LABEL"

        # DO with routine creates MCall with routine reference
        stmt = analyze_first_command("D LABEL^ROUTINE")
        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]
        assert isinstance(target, MCall)
        assert target.name == "LABEL"
        assert target.routine == "ROUTINE"

        # DO with arguments creates MCall with arguments
        stmt = analyze_first_command("D FUNC(1,2,3)")
        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]
        assert isinstance(target, MCall)
        assert target.name == "FUNC"
        assert len(target.arguments) == 3

    def test_external_routine_reference(self):
        """External routine references are tracked (§8.2.3)."""
        parser = MUMPSParser()
        source = """TEST	;TEST
	D ^VREPORT
	Q
"""
        routine = parser.parse(source, "test.m")

        # Find the DO statement
        do_stmt = routine.labels[0].body.statements[0]
        assert isinstance(do_stmt, MDoStatement)

        # Check the target
        assert len(do_stmt.targets) == 1
        target = do_stmt.targets[0]
        assert target.name == "", f"Expected name='', got name={repr(target.name)}"
        assert target.name is not None, "name should be '' not None"
        assert target.routine == "VREPORT"


@pytest.mark.asg
class TestDoBlockBodyPopulation:
    """Tests for DO block body statement collection (§8.2.3)."""

    def test_do_block_nested(self):
        """Nested DO blocks are properly structured."""
        parser = MUMPSParser()
        source = """TEST\tD
 . S X=1
 . D
 . . S Y=2
 . . S Z=3
 . S A=4
 S B=5
"""
        routine = parser.parse(source)

        # Should have 2 statements: outer DO block and SET B=5
        assert len(routine.labels[0].body.statements) == 2

        outer_do = routine.labels[0].body.statements[0]
        assert isinstance(outer_do, MDoStatement)
        # Outer DO has: S X=1, nested DO, S A=4
        assert len(outer_do.body.statements) == 3

        inner_do = outer_do.body.statements[1]
        assert isinstance(inner_do, MDoStatement)
        # Inner DO has: S Y=2, S Z=3
        assert len(inner_do.body.statements) == 2


@pytest.mark.asg
class TestMActualParameterAnalysis:
    """Test T93.2: MActualParameter parent references are correctly set."""

    def test_extrinsic_function_args_have_correct_parents(self):
        """Extrinsic function arguments should have proper parent chain."""
        from m2py import MUMPSParser
        from m2py.asg.expressions import MActualParameter, MVariable, MExtrinsicFunction

        source = """TEST
 S X=$$FUNC^ROUT(A,B)
"""
        parser = MUMPSParser()
        routine = parser.parse(source)

        # Find the SET statement with extrinsic function
        stmt = routine.labels[0].body.statements[0]
        func = stmt.assignments[0].value

        assert isinstance(func, MExtrinsicFunction)
        assert len(func.arguments) == 2

        for i, arg in enumerate(func.arguments):
            assert isinstance(arg, MActualParameter)
            # Parent of MActualParameter should be the function
            assert arg.parent is func, f"Arg {i} parent should be the function"
            # Expression should be analyzed and have arg as parent
            assert isinstance(arg.expression, MVariable)
            assert arg.expression.parent is arg, (
                f"Arg {i} expression parent should be the arg"
            )

    def test_extrinsic_function_byref_args_have_correct_parents(self):
        """By-reference arguments should also have proper parent chain."""
        from m2py import MUMPSParser
        from m2py.asg.expressions import MActualParameter, MVariable, MExtrinsicFunction
        from m2py.asg.enums import PassingMode

        source = """TEST
 S X=$$FUNC(.Y)
"""
        parser = MUMPSParser()
        routine = parser.parse(source)

        stmt = routine.labels[0].body.statements[0]
        func = stmt.assignments[0].value

        assert isinstance(func, MExtrinsicFunction)
        assert len(func.arguments) == 1

        arg = func.arguments[0]
        assert isinstance(arg, MActualParameter)
        assert arg.passing_mode == PassingMode.BY_REFERENCE
        assert arg.parent is func
        assert isinstance(arg.expression, MVariable)
        assert arg.expression.parent is arg

    def test_do_with_expression_postcondition(self):
        """DO LABEL:X>0 parses expression postcondition (§8.1.4).

        Argument postconditions can be complex expressions.
        Only Do, Goto, and Xecute support argument postconditions.
        """
        from m2py.asg.expressions import MBinaryOp

        stmt = analyze_first_command("D PROC:N>0")

        assert isinstance(stmt, MDoStatement)
        assert len(stmt.targets) == 1
        target = stmt.targets[0]

        assert target.postcondition is not None
        assert isinstance(target.postcondition, MBinaryOp)
        assert target.postcondition.operator == ">"


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestExternalRoutineCalls:
    """Test that external routine calls (^ROUTINE syntax) are correctly represented (T373)."""

    def test_goto_external_routine_has_empty_name(self):
        """Test G ^ROUTINE sets name='' not name=None."""
        parser = MUMPSParser()
        source = """TEST	;TEST
	G ^VREPORT
	Q
"""
        routine = parser.parse(source, "test.m")

        # Find the GOTO statement
        goto_stmt = routine.labels[0].body.statements[0]
        assert goto_stmt.__class__.__name__ == "MGotoStatement"

        # Check the target
        assert len(goto_stmt.targets) == 1
        target = goto_stmt.targets[0]
        assert target.name == "", f"Expected name='', got name={repr(target.name)}"
        assert target.name is not None, "name should be '' not None"
        assert target.routine == "VREPORT"

    def test_do_label_with_routine_has_label_name(self):
        """Test D LABEL^ROUTINE sets name='LABEL'."""
        parser = MUMPSParser()
        source = """TEST	;TEST
	D START^VREPORT
	Q
"""
        routine = parser.parse(source, "test.m")

        do_stmt = routine.labels[0].body.statements[0]
        target = do_stmt.targets[0]
        assert target.name == "START"
        assert target.routine == "VREPORT"

    def test_do_local_label_has_name_no_routine(self):
        """Test D LABEL sets name='LABEL', routine=None."""
        parser = MUMPSParser()
        source = """TEST	;TEST
	D HELPER
	Q
HELPER	W "Test"
	Q
"""
        routine = parser.parse(source, "test.m")

        do_stmt = routine.labels[0].body.statements[0]
        target = do_stmt.targets[0]
        assert target.name == "HELPER"
        assert target.routine is None
