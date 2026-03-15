"""Tests for DO command ASG analysis (§8.2.3).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.3
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import (
    MDoStatement,
    MForStatement,
    MSetStatement,
    MWriteStatement,
)


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

    def test_do_with_empty_parens(self):
        """DO label^routine() - empty parens indicate parameter passing semantics."""
        stmt = analyze_first_command("D LABEL^routine()")
        assert isinstance(stmt, MDoStatement)
        assert len(stmt.targets) == 1
        target = stmt.targets[0]
        # Verify MCall structure for empty parens
        from m2py.asg.elements import MCall

        assert isinstance(target, MCall)
        assert target.name == "LABEL"
        assert target.routine == "routine"
        assert target.arguments == []

    def test_do_with_empty_parens_no_routine(self):
        """DO label() - empty parens with just label."""
        stmt = analyze_first_command("D LABEL()")
        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]
        from m2py.asg.elements import MCall

        assert isinstance(target, MCall)
        assert target.name == "LABEL"
        assert target.arguments == []

    def test_do_with_empty_args(self):
        """DO command with empty arguments (§8.2.3)."""
        # DO select^routine(,begin)
        stmt = analyze_first_command("DO select^routine(,begin)")
        target = stmt.targets[0]
        # In ASG arguments list, empty position should be None or empty string or similar?
        # TextX might put empty string or None.
        # Assuming list length is preserved.
        assert len(target.arguments) == 2

        # DO routine(,,,val)
        stmt2 = analyze_first_command("DO routine(,,,val)")
        target2 = stmt2.targets[0]
        assert len(target2.arguments) == 4


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

    def test_do_for_do_shares_dot_block(self):
        """D  F ...  D — trailing D inside FOR shares the leading D's dot-block.

        In MUMPS, ``D  F I=1:1:3 D`` means:
          1. Leading D starts the dot-block
          2. F loops, and the trailing D inside the FOR *also* executes
             the same dot-block
        Both argumentless DOs on the same line must share the same body.
        """
        parser = MUMPSParser()
        source = """TEST\tD  F I=1:1:3 D
 . W I,!
"""
        routine = parser.parse(source)
        stmts = routine.labels[0].body.statements

        # First statement is the leading argumentless DO
        leading_do = stmts[0]
        assert isinstance(leading_do, MDoStatement)
        assert not leading_do.targets  # argumentless
        assert leading_do.is_inline_block
        assert len(leading_do.body.statements) == 1
        assert isinstance(leading_do.body.statements[0], MWriteStatement)

        # Second statement is the FOR loop (same-line post-DO)
        for_stmt = stmts[1]
        assert isinstance(for_stmt, MForStatement)
        # FOR body should contain the trailing argumentless DO
        assert len(for_stmt.body.statements) == 1
        inner_do = for_stmt.body.statements[0]
        assert isinstance(inner_do, MDoStatement)
        assert not inner_do.targets  # argumentless
        assert inner_do.is_inline_block
        # Inner DO must have the same body content as leading DO
        assert len(inner_do.body.statements) == 1
        assert isinstance(inner_do.body.statements[0], MWriteStatement)

    def test_do_for_do_multi_line_block(self):
        """D  F ...  D with multi-line dot-block."""
        parser = MUMPSParser()
        source = """TEST\tD  F I=1:1:3 D
 . S X=I*2
 . W X,!
"""
        routine = parser.parse(source)
        stmts = routine.labels[0].body.statements

        leading_do = stmts[0]
        assert isinstance(leading_do, MDoStatement)
        assert len(leading_do.body.statements) == 2

        for_stmt = stmts[1]
        assert isinstance(for_stmt, MForStatement)
        inner_do = for_stmt.body.statements[0]
        assert isinstance(inner_do, MDoStatement)
        # Both DOs share the same 2-statement block
        assert len(inner_do.body.statements) == 2
        assert isinstance(inner_do.body.statements[0], MSetStatement)
        assert isinstance(inner_do.body.statements[1], MWriteStatement)

    def test_do_for_do_quit_shares_block(self):
        """D  F ...  D  Q:cond — trailing D shares block, Q is separate."""
        parser = MUMPSParser()
        source = """MGTF\tD  F  D  Q:%ZISHY
 . W "line",!
"""
        routine = parser.parse(source)
        stmts = routine.labels[0].body.statements

        leading_do = stmts[0]
        assert isinstance(leading_do, MDoStatement)
        assert leading_do.is_inline_block
        assert len(leading_do.body.statements) == 1

        for_stmt = stmts[1]
        assert isinstance(for_stmt, MForStatement)
        # FOR body: D (argumentless) and Q:%ZISHY
        assert len(for_stmt.body.statements) == 2
        inner_do = for_stmt.body.statements[0]
        assert isinstance(inner_do, MDoStatement)
        assert inner_do.is_inline_block
        assert len(inner_do.body.statements) == 1

    def test_do_without_for_do_no_sharing(self):
        """Plain D (no trailing D) — no sharing needed."""
        parser = MUMPSParser()
        source = """TEST\tD
 . S X=1
 S Y=2
"""
        routine = parser.parse(source)
        stmts = routine.labels[0].body.statements

        do_stmt = stmts[0]
        assert isinstance(do_stmt, MDoStatement)
        assert do_stmt.is_inline_block
        assert len(do_stmt.body.statements) == 1

        set_stmt = stmts[1]
        assert isinstance(set_stmt, MSetStatement)

    def test_do_for_no_inner_do(self):
        """D  F ... S X=1 — FOR body has no argumentless DO, no sharing."""
        parser = MUMPSParser()
        source = """TEST\tD  F I=1:1:3 S X=I
 . W "hello",!
"""
        routine = parser.parse(source)
        stmts = routine.labels[0].body.statements

        leading_do = stmts[0]
        assert isinstance(leading_do, MDoStatement)
        assert leading_do.is_inline_block
        assert len(leading_do.body.statements) == 1

        for_stmt = stmts[1]
        assert isinstance(for_stmt, MForStatement)
        # FOR body has SET only (no argumentless DO)
        assert len(for_stmt.body.statements) == 1
        assert isinstance(for_stmt.body.statements[0], MSetStatement)


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


@pytest.mark.asg
class TestDoRoutineIndirection:
    """Tests for DO with routine indirection (GAP-011c).

    Per MUMPS 1995 §8.1.6, entryrefs allow indirection of both
    label and routinename: D LABEL^@ROUTINEVAR, D @VAR^@ROUTINE
    """

    def test_do_routine_indirection(self):
        """DO LABEL^@ROUTINEVAR - routine name is indirect.

        The routine name comes from a variable at runtime.
        """
        stmt = analyze_first_command("D LABEL^@R")
        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]

        # Label is literal, routine is indirect
        assert target.name == "LABEL"
        assert target.routine_is_indirect is True
        assert target.routine_indirection is not None
        # routine_indirection is MIndirection containing the variable
        assert target.routine_indirection.expression.name == "R"

    def test_do_indirect_label_and_routine(self):
        """DO @LABELVAR^@ROUTINEVAR - both label and routine indirect.

        Full indirection: D @L^@R means evaluate L for label, R for routine.
        """
        stmt = analyze_first_command("D @L^@R")
        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]

        # Label is indirect - indirection wraps the variable
        assert target.label_is_indirect is True
        assert target.indirection is not None
        assert target.indirection.expression.name == "L"

        # Routine is indirect - indirection wraps the variable
        assert target.routine_is_indirect is True
        assert target.routine_indirection is not None
        assert target.routine_indirection.expression.name == "R"

    def test_do_indirect_with_offset_and_routine(self):
        """DO @VAR+offset^@ROUTINE - indirection with offset and routine.

        Complex form combining indirection, offset, and routine indirection.
        """
        stmt = analyze_first_command("D @A+5^@R")
        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]

        # Label indirection - wraps the variable
        assert target.label_is_indirect is True
        assert target.indirection.expression.name == "A"

        # Offset expression
        assert target.offset is not None
        assert target.offset.value == 5

        # Routine indirection - wraps the variable
        assert target.routine_is_indirect is True
        assert target.routine_indirection.expression.name == "R"


@pytest.mark.asg
class TestDoOffsetExpressions:
    """Tests for DO with offset expressions (GAP-011e).

    Per MUMPS 1995 §8.1.6, entryrefs allow integer offsets: LABEL+5^ROUTINE
    """

    def test_do_label_with_offset(self):
        """DO LABEL+5 - label with numeric offset.

        References the 5th line after LABEL.
        """
        stmt = analyze_first_command("D LABEL+5")
        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]

        assert target.name == "LABEL"
        assert target.offset is not None
        assert target.offset.value == 5

    def test_do_label_offset_routine(self):
        """DO LABEL+3^ROUTINE - label+offset in external routine.

        Full entryref with label, offset, and routine.
        """
        stmt = analyze_first_command("D LABEL+3^ROUTINE")
        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]

        assert target.name == "LABEL"
        assert target.offset is not None
        assert target.offset.value == 3
        assert target.routine == "ROUTINE"

    def test_do_label_variable_offset(self):
        """DO LABEL+N^ROUTINE - offset is a variable.

        Offset can be any expression, including variables.
        """
        stmt = analyze_first_command("D LABEL+N^ROUTINE")
        assert isinstance(stmt, MDoStatement)
        target = stmt.targets[0]

        assert target.name == "LABEL"
        assert target.offset is not None
        assert target.offset.name == "N"
        assert target.routine == "ROUTINE"
