"""Cross-cutting tests for MUMPS language semantics.

This file tests fundamental language behaviors that span multiple
commands and expressions:
- $TEST special variable modification (FR-047)
- Left-to-right evaluation without precedence (FR-050)
- Exclusive NEW scoping behavior (FR-048)
- Transaction nesting with $TLEVEL (FR-051)

Reference: MUMPS 1995 ANSI Standard, various sections
See also: FR-046-051 (language semantic requirements)
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.expressions import MBinaryOp
from m2py.asg.statements import MNewStatement
from m2py.parser.textx_classes import NumericLiteral


# =============================================================================
# $TEST Special Variable Tests
# =============================================================================


@pytest.mark.parser
class TestTestVariableParser:
    """Parser tests for commands that affect $TEST.

    $TEST is modified by: IF with argument, and timeout commands
    (OPEN, READ, JOB, LOCK with timeouts).
    Reference: §7.1.4.10, §8.2.9, FR-047

    Note: Detailed IF/ELSE parser tests in tests/unit/parser/s8_commands/
    These tests verify cross-cutting $TEST behavior.
    """

    def test_argumentless_if_parsed(self):
        """Argumentless IF reads $TEST (§8.2.9)."""
        parser = MUMPSParser()
        source = "LABEL\tI\n"
        routine = parser.parse(source)

        if_stmt = routine.labels[0].body.statements[0]
        assert if_stmt.__class__.__name__ == "MIfStatement"
        # Argumentless IF has no condition - reads $TEST
        assert if_stmt.condition is None
        assert len(if_stmt.conditions) == 0

    def test_if_with_argument_parsed(self):
        """IF with argument sets $TEST (§8.2.9)."""
        parser = MUMPSParser()
        source = "LABEL\tI X=1\n"
        routine = parser.parse(source)

        if_stmt = routine.labels[0].body.statements[0]
        assert if_stmt.__class__.__name__ == "MIfStatement"
        # IF with argument has condition that sets $TEST
        assert if_stmt.condition is not None
        assert len(if_stmt.conditions) == 1


@pytest.mark.asg
class TestTestVariableASG:
    """ASG tests for $TEST tracking.

    ASG analysis must track which commands read and modify $TEST.
    Reference: §7.1.4.10, §8.2.4, §8.2.9, FR-047

    Note: Detailed IF/ELSE ASG tests in tests/unit/asg/s8_commands/
    These tests verify cross-cutting $TEST state transitions.
    """

    def test_if_modifies_test(self):
        """IF with argument modifies $TEST (§8.2.9, FR-047)."""
        from m2py.asg.statements import MIfStatement

        parser = MUMPSParser()
        source = "LABEL\tI X=1\n"
        routine = parser.parse(source)

        if_stmt = routine.labels[0].body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        # IF with condition sets $TEST to truth value
        assert if_stmt.condition is not None

    def test_argumentless_if_reads_test(self):
        """Argumentless IF reads $TEST (§8.2.9, FR-047)."""
        from m2py.asg.statements import MIfStatement

        parser = MUMPSParser()
        source = "LABEL\tI\n"
        routine = parser.parse(source)

        if_stmt = routine.labels[0].body.statements[0]
        assert isinstance(if_stmt, MIfStatement)
        # Argumentless IF reads $TEST (condition is None)
        assert if_stmt.condition is None

    def test_else_reads_test(self):
        """ELSE command reads $TEST (§8.2.4, FR-047)."""
        from m2py.asg.statements import MElseStatement

        parser = MUMPSParser()
        source = "LABEL\tE  S X=1\n"
        routine = parser.parse(source)

        else_stmt = routine.labels[0].body.statements[0]
        assert isinstance(else_stmt, MElseStatement)
        # ELSE reads $TEST - executes when $TEST=0
        assert else_stmt.body is not None


@pytest.mark.codegen
class TestTestVariableCodegen:
    """Codegen tests for $TEST behavior.

    Generated Python must correctly maintain $TEST state.
    Reference: §7.1.4.10, §8.2.4, §8.2.9, FR-047
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires code execution")
    def test_if_true_sets_test_true(self):
        """IF 1 sets $TEST=1 (§8.2.9).

        IF 1
        ; $TEST should be 1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires code execution")
    def test_if_false_sets_test_false(self):
        """IF 0 sets $TEST=0 (§8.2.9).

        IF 0
        ; $TEST should be 0
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires code execution")
    def test_argumentless_if_uses_test(self):
        """Argumentless IF executes based on $TEST (§8.2.9).

        IF 1
        IF  WRITE "YES"  ; Should execute
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Runtime behavior - requires code execution")
    def test_else_uses_test(self):
        """ELSE executes when $TEST=0 (§8.2.4).

        IF 0
        ELSE  WRITE "NO"  ; Should execute
        """
        pytest.fail("Stub - implement test")


# =============================================================================
# Left-to-Right Evaluation Tests
# =============================================================================


@pytest.mark.parser
class TestLeftToRightParser:
    """Parser tests for operator expressions.

    MUMPS has no operator precedence - strict left-to-right.
    Reference: §7.2
    """

    def test_mixed_operators_parsed(self):
        """2+3*4 parses as (2+3)*4 not 2+(3*4) (§7.2).

        MUMPS evaluates strictly left-to-right with no operator precedence.
        The parser must capture the expression structure correctly for ASG
        analysis to maintain left-to-right semantics.

        Reference: 1995__a107190 (§7.2 - Expression tail)
        """
        parser = MUMPSParser()
        source = "LABEL\tS X=2+3*4\n"
        routine = parser.parse(source)

        set_stmt = routine.labels[0].body.statements[0]
        assert set_stmt.__class__.__name__ == "MSetStatement"

        # The expression structure is captured for ASG analysis
        assignment = set_stmt.assignments[0]
        assert assignment.target.name == "X"
        # Value expression exists (structure verified in ASG tests)
        assert assignment.value is not None


@pytest.mark.asg
class TestLeftToRightASG:
    """ASG tests for expression structure.

    ASG must represent left-to-right grouping.
    Reference: §7.2, FR-050
    """

    def test_mixed_operators_asg_structure(self):
        """2+3*4 has correct left-to-right ASG structure (§7.2, FR-050).

        The ASG must represent expressions with left-to-right grouping.
        2+3*4 becomes ((2+3)*4), so:
        - Top-level operator is * (last operation in left-to-right order)
        - Left child is the + operation (2+3)
        - Right child is the literal 4

        Reference: 1995__a107190 (§7.2 - All operators same precedence)
        """
        cmds = parse_commands_from_line("S X=2+3*4")
        stmt = analyze_command(cmds[0])
        expr = stmt.assignments[0].value

        # Top-level should be multiplication (last operation)
        assert isinstance(expr, MBinaryOp)
        assert expr.operator == "*"

        # Left side should be the addition (2+3)
        assert isinstance(expr.left, MBinaryOp)
        assert expr.left.operator == "+"

        # Right side is the literal 4
        assert isinstance(expr.right, NumericLiteral)
        assert expr.right.value == 4

        # Verify the nested addition operands
        assert isinstance(expr.left.left, NumericLiteral)
        assert expr.left.left.value == 2
        assert isinstance(expr.left.right, NumericLiteral)
        assert expr.left.right.value == 3


@pytest.mark.codegen
class TestLeftToRightCodegen:
    """Codegen tests for expression evaluation.

    Generated Python must evaluate left-to-right without precedence.
    Reference: §7.2, FR-050
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: 2+3*4=20")
    def test_addition_then_multiplication(self):
        """2+3*4 evaluates to 20, not 14 (§7.2, FR-050).

        SET X=2+3*4  ; X should be 20 = (2+3)*4
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: 10-3-2=5")
    def test_subtraction_left_to_right(self):
        """10-3-2 evaluates to 5 (§7.2).

        SET X=10-3-2  ; X should be 5 = (10-3)-2
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: division left to right")
    def test_division_left_to_right(self):
        """24/4/2 evaluates to 3 (§7.2).

        SET X=24/4/2  ; X should be 3 = (24/4)/2
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: mixed with comparison")
    def test_mixed_arithmetic_comparison(self):
        """2+3>4 evaluates to 1 (true) (§7.2).

        SET X=2+3>4  ; (2+3)>4 = 5>4 = 1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: parentheses override")
    def test_parentheses_override_left_to_right(self):
        """2+(3*4) evaluates to 14 with parentheses (§7.2).

        SET X=2+(3*4)  ; X should be 14
        """
        pytest.fail("Stub - implement test")


# =============================================================================
# Exclusive NEW Tests
# =============================================================================


@pytest.mark.parser
class TestExclusiveNewParser:
    """Parser tests for Exclusive NEW syntax.

    NEW (var1,var2,...) protects listed variables, makes all others NEW.
    Reference: §8.2.14
    """

    def test_exclusive_new_parsed(self):
        """NEW (X,Y) parses exclusive NEW form (§8.2.14).

        Exclusive NEW syntax uses parentheses around the variable list.
        This form keeps listed variables visible and creates new scope
        for all other variables.

        Reference: 1995__a108042.md, examples__a108042.md
        """
        parser = MUMPSParser()
        source = "LABEL\tN (X,Y)\n"
        routine = parser.parse(source)

        new_stmt = routine.labels[0].body.statements[0]
        assert new_stmt.__class__.__name__ == "MNewStatement"
        # Parser captures exclusive form
        assert new_stmt.exclusive is True

    def test_exclusive_new_multiple_vars_parsed(self):
        """NEW (A,B,C,D) parses with multiple variables (§8.2.14).

        Exclusive NEW can protect any number of variables.
        """
        cmds = parse_commands_from_line("N (A,B,C,D)")
        stmt = analyze_command(cmds[0])

        assert isinstance(stmt, MNewStatement)
        assert stmt.exclusive is True
        assert len(stmt.except_list) == 4
        assert set(stmt.except_list) == {"A", "B", "C", "D"}

    def test_exclusive_vs_regular_new_distinction(self):
        """Parser distinguishes NEW X from NEW (X) (§8.2.14).

        Regular NEW creates new scope for listed variables.
        Exclusive NEW creates new scope for all EXCEPT listed variables.
        """
        # Regular NEW
        cmds = parse_commands_from_line("N X,Y")
        regular = analyze_command(cmds[0])
        assert isinstance(regular, MNewStatement)
        assert regular.exclusive is False
        assert len(regular.variables) == 2

        # Exclusive NEW
        cmds = parse_commands_from_line("N (X,Y)")
        exclusive = analyze_command(cmds[0])
        assert isinstance(exclusive, MNewStatement)
        assert exclusive.exclusive is True
        assert len(exclusive.except_list) == 2


@pytest.mark.asg
class TestExclusiveNewASG:
    """ASG tests for Exclusive NEW analysis.

    ASG must identify exclusive NEW and track protected variables.
    Reference: §8.2.14, FR-048
    """

    def test_exclusive_new_classified(self):
        """Exclusive NEW has exclusive=True in ASG (§8.2.14, FR-048).

        The ASG must distinguish exclusive NEW from regular NEW so that
        codegen can implement inverse scoping behavior.
        """
        cmds = parse_commands_from_line("N (X,Y)")
        stmt = analyze_command(cmds[0])

        assert isinstance(stmt, MNewStatement)
        assert stmt.exclusive is True

        # Verify regular NEW is not exclusive
        cmds = parse_commands_from_line("N X,Y")
        stmt = analyze_command(cmds[0])
        assert stmt.exclusive is False

    def test_protected_variables_tracked(self):
        """Protected variable list tracked in ASG (§8.2.14, FR-048).

        The except_list contains variables that should NOT be NEWed,
        i.e., they remain visible from outer scope.
        """
        cmds = parse_commands_from_line("N (A,B,C)")
        stmt = analyze_command(cmds[0])

        assert isinstance(stmt, MNewStatement)
        assert hasattr(stmt, "except_list")
        assert len(stmt.except_list) == 3
        assert "A" in stmt.except_list
        assert "B" in stmt.except_list
        assert "C" in stmt.except_list

        # Regular NEW has empty except_list
        cmds = parse_commands_from_line("N X")
        stmt = analyze_command(cmds[0])
        assert stmt.except_list == []


@pytest.mark.codegen
class TestExclusiveNewCodegen:
    """Codegen tests for Exclusive NEW behavior.

    Generated Python must implement inverse scoping correctly.
    Reference: §8.2.14, FR-048
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: exclusive NEW protects listed")
    def test_exclusive_new_protects_listed_variables(self):
        """NEW (X) keeps X visible, hides others (§8.2.14, FR-048).

        SET A=1,X=2
        NEW (X)
        ; X should still be 2, A should be undefined
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: exclusive NEW hides unlisted")
    def test_exclusive_new_hides_unlisted_variables(self):
        """NEW (X) makes unlisted variables undefined (§8.2.14, FR-048).

        SET A=1,B=2,X=3
        NEW (X)
        ; A and B should be undefined
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: exclusive NEW restored on QUIT")
    def test_exclusive_new_restored_on_quit(self):
        """Exclusive NEW variables restored on QUIT (§8.2.14, FR-048)."""
        pytest.fail("Stub - implement test")


# =============================================================================
# Transaction Nesting Tests
# =============================================================================


@pytest.mark.parser
class TestTransactionNestingParser:
    """Parser tests for transaction command syntax.

    TSTART/TCOMMIT/TROLLBACK support nesting.
    Reference: §8.2.19, §8.2.21, §8.2.22
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TSTART parsed")
    def test_tstart_parsed(self):
        """TSTART parses transaction start (§8.2.22)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TCOMMIT parsed")
    def test_tcommit_parsed(self):
        """TCOMMIT parses transaction commit (§8.2.19)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TROLLBACK parsed")
    def test_trollback_parsed(self):
        """TROLLBACK parses transaction rollback (§8.2.21)."""
        pytest.fail("Stub - implement test")


@pytest.mark.asg
class TestTransactionNestingASG:
    """ASG tests for transaction analysis.

    ASG must track transaction nesting level ($TLEVEL).
    Reference: §8.2.19, §8.2.21, §8.2.22, FR-051
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TLEVEL tracking")
    def test_tlevel_tracking(self):
        """ASG tracks $TLEVEL for nested transactions (§7.1.7, FR-051)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: nested TSTART detection")
    def test_nested_tstart_detection(self):
        """ASG detects nested TSTART commands (FR-051)."""
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestTransactionNestingCodegen:
    """Codegen tests for transaction nesting behavior.

    Generated Python must correctly implement nested transactions
    with $TLEVEL tracking.
    Reference: §8.2.19, §8.2.21, §8.2.22, FR-051
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TLEVEL increments")
    def test_tlevel_increments_on_tstart(self):
        """TSTART increments $TLEVEL (§8.2.22, FR-051).

        ; $TLEVEL=0
        TSTART
        ; $TLEVEL should be 1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: nested $TLEVEL")
    def test_nested_tstart_increments_tlevel(self):
        """Nested TSTART increments $TLEVEL (§8.2.22, FR-051).

        TSTART    ; $TLEVEL=1
        TSTART    ; $TLEVEL should be 2
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TCOMMIT decrements")
    def test_tcommit_decrements_tlevel(self):
        """TCOMMIT decrements $TLEVEL (§8.2.19, FR-051).

        TSTART    ; $TLEVEL=1
        TSTART    ; $TLEVEL=2
        TCOMMIT   ; $TLEVEL should be 1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: TROLLBACK to level")
    def test_trollback_to_specific_level(self):
        """TROLLBACK:n rolls back to level n (§8.2.21, FR-051).

        TSTART    ; $TLEVEL=1
        TSTART    ; $TLEVEL=2
        TSTART    ; $TLEVEL=3
        TROLLBACK:1  ; Should rollback to $TLEVEL=1
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: full TROLLBACK")
    def test_trollback_full(self):
        """Argumentless TROLLBACK rolls back all levels (§8.2.21, FR-051).

        TSTART    ; $TLEVEL=1
        TSTART    ; $TLEVEL=2
        TROLLBACK ; $TLEVEL should be 0
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TRESTART tracking")
    def test_trestart_tracking(self):
        """$TRESTART counts restart attempts (§7.1.7, FR-051)."""
        pytest.fail("Stub - implement test")
