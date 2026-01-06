"""Cross-cutting tests for naked global references (§7.1.2.4).

Naked references are a language feature that affects all global variable
access. A naked reference uses ^(subscripts) where the global name is
omitted and taken from the most recent global reference.

Key behaviors (FR-046):
- Naked indicator is set by any full global reference
- Naked reference ^(sub) uses prior global's name
- Naked indicator is sequence-dependent (order matters)
- Invalid if no prior global reference exists

This file focuses on:
- Cross-cutting behavior across multiple commands
- Codegen/runtime behavior requiring execution

Reference: MUMPS 1995 ANSI Standard, Section 7.1.2.4
See also: FR-005 (cross-cutting features need dedicated tests)
         FR-046 (naked reference state tracking)
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.expressions import (
    MLiteral,
    MGlobal,
    MNakedGlobal,
)
from m2py.asg.statements import MSetStatement, MKillStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


def analyze_all_commands(line: str):
    """Helper to parse and analyze all commands from a line."""
    cmds = parse_commands_from_line(line)
    return [analyze_command(cmd) for cmd in cmds]


# =============================================================================
# Naked Reference Syntax Tests (Parser Level)
# These tests cover multi-subscript and expression subscript edge cases.
# =============================================================================


@pytest.mark.parser
class TestNakedReferenceParser:
    """Parser tests for naked reference syntax.

    Naked reference format: ^(subscripts)
    The global name portion is empty.
    Reference: §7.1.2.4
    """

    def test_naked_reference_basic(self):
        """^(1) parses as naked reference (§7.1.2.4)."""
        stmt = analyze_first_command("S ^(1)=100")

        assert isinstance(stmt, MSetStatement)
        target = stmt.assignments[0].target
        assert isinstance(target, MNakedGlobal)
        assert len(target.subscripts) == 1
        # First subscript should be literal 1
        assert isinstance(target.subscripts[0], MLiteral)
        assert target.subscripts[0].value == 1

    def test_naked_reference_expression_subscript(self):
        """^(X+1) parses as naked reference with expression (§7.1.2.4)."""
        stmt = analyze_first_command("S ^(X+1)=100")

        assert isinstance(stmt, MSetStatement)
        target = stmt.assignments[0].target
        assert isinstance(target, MNakedGlobal)
        assert len(target.subscripts) == 1
        # First subscript should be an expression (MBinaryOp or MExpr type)
        # The exact ASG type depends on analysis depth - verify it exists
        subscript = target.subscripts[0]
        # At minimum, verify we have a subscript with structure
        assert subscript is not None
        # If fully analyzed to ASG, would be MBinaryOp; otherwise textX Expr
        # For cross-cutting tests, we verify presence not deep analysis
        # Deep analysis belongs in s7_expressions tests


# =============================================================================
# Naked Indicator State Tests (Parser Level)
# =============================================================================


@pytest.mark.parser
class TestNakedIndicatorParser:
    """Parser tests for full global references that set naked indicator.

    Any full global reference (read or write) sets the naked indicator.
    Reference: §7.1.2.4
    """

    def test_set_global_parsed(self):
        """SET ^DATA(1)=X parses full global reference (§7.1.2.4)."""
        stmt = analyze_first_command("S ^DATA(1)=X")

        assert isinstance(stmt, MSetStatement)
        target = stmt.assignments[0].target
        assert isinstance(target, MGlobal)
        assert target.name == "DATA"
        assert len(target.subscripts) == 1

    def test_read_global_parsed(self):
        """SET X=^DATA(1) parses full global reference (§7.1.2.4)."""
        stmt = analyze_first_command("S X=^DATA(1)")

        assert isinstance(stmt, MSetStatement)
        value = stmt.assignments[0].value
        assert isinstance(value, MGlobal)
        assert value.name == "DATA"
        assert len(value.subscripts) == 1

    def test_kill_global_parsed(self):
        """KILL ^DATA(1) parses full global reference (§7.1.2.4)."""
        stmt = analyze_first_command("K ^DATA(1)")

        assert isinstance(stmt, MKillStatement)
        assert len(stmt.targets) == 1
        target = stmt.targets[0]
        assert isinstance(target, MGlobal)
        assert target.name == "DATA"
        assert len(target.subscripts) == 1


# =============================================================================
# Naked Reference Tests (ASG Level)
# =============================================================================


@pytest.mark.asg
class TestNakedReferenceASG:
    """ASG tests for naked reference analysis.

    ASG analysis must track which globals set the naked indicator
    and which use naked references.
    Reference: §7.1.2.4, FR-046
    """

    def test_naked_reference_classified(self):
        """Naked reference is classified as MNakedGlobal (§7.1.2.4)."""
        stmt = analyze_first_command("S ^(1)=100")

        target = stmt.assignments[0].target
        # MNakedGlobal is the ASG type for naked references
        assert isinstance(target, MNakedGlobal)
        # MNakedGlobal should not have a 'name' attribute (inherits from naked indicator)
        assert not hasattr(target, "name") or target.name is None

    def test_full_global_sets_naked_indicator(self):
        """Full global reference tracked with name for naked indicator (§7.1.2.4).

        A full global reference like ^DATA(1) establishes the naked indicator.
        The ASG should capture the global name and subscripts for this.
        """
        stmt = analyze_first_command("S ^DATA(1,2)=100")

        target = stmt.assignments[0].target
        assert isinstance(target, MGlobal)
        # Full global has a name that will set the naked indicator
        assert target.name == "DATA"
        # And subscripts that contribute to the indicator
        assert len(target.subscripts) == 2

    def test_naked_reference_subscripts_tracked(self):
        """Naked reference subscripts are tracked in ASG (§7.1.2.4)."""
        stmt = analyze_first_command('S ^("a","b")=100')

        target = stmt.assignments[0].target
        assert isinstance(target, MNakedGlobal)
        assert len(target.subscripts) == 2
        # Verify subscript values
        assert target.subscripts[0].value == "a"
        assert target.subscripts[1].value == "b"


# =============================================================================
# Naked Reference State Transition Tests (Codegen Level)
# =============================================================================


@pytest.mark.codegen
class TestNakedStateTransitions:
    """Codegen tests for naked indicator state transitions.

    These tests verify RUNTIME behavior of naked reference resolution.
    The naked indicator must be tracked at runtime to resolve ^(sub) references.
    Reference: §7.1.2.4, FR-046
    """

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: SET establishes indicator at runtime"
    )
    def test_set_establishes_naked_indicator(self):
        """SET ^DATA(1)=X establishes naked indicator to ^DATA (§7.1.2.4).

        SET ^DATA(1)=X
        SET ^(2)=Y  ; Should access ^DATA(2) at runtime
        """
        pytest.fail("Stub - requires codegen runtime execution")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: READ establishes indicator at runtime"
    )
    def test_read_establishes_naked_indicator(self):
        """SET X=^DATA(1) establishes naked indicator to ^DATA (§7.1.2.4).

        SET X=^DATA(1)
        SET Y=^(2)  ; Should access ^DATA(2) at runtime
        """
        pytest.fail("Stub - requires codegen runtime execution")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subscript chaining at runtime")
    def test_naked_reference_subscript_chaining(self):
        """Naked reference replaces last subscript, chains others (§7.1.2.4).

        SET ^DATA(1,2)=X  ; Indicator = ^DATA(1
        SET ^(3)=Y        ; Should access ^DATA(1,3) at runtime
        """
        pytest.fail("Stub - requires codegen runtime execution")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: multiple subscripts at runtime")
    def test_naked_reference_multiple_subscripts(self):
        """Naked with multiple subscripts extends from indicator (§7.1.2.4).

        SET ^DATA(1)=X   ; Indicator = ^DATA
        SET ^(2,3)=Y     ; Should access ^DATA(2,3) at runtime
        """
        pytest.fail("Stub - requires codegen runtime execution")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: naked updates indicator at runtime")
    def test_naked_reference_updates_indicator(self):
        """Naked reference itself updates the indicator (§7.1.2.4).

        SET ^DATA(1)=X   ; Indicator = ^DATA
        SET ^(2)=Y       ; Access ^DATA(2), indicator = ^DATA(
        SET ^(3)=Z       ; Should access ^DATA(3) at runtime
        """
        pytest.fail("Stub - requires codegen runtime execution")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: different global changes indicator")
    def test_different_global_changes_indicator(self):
        """Reference to different global changes indicator (§7.1.2.4).

        SET ^DATA(1)=X    ; Indicator = ^DATA
        SET ^OTHER(5)=Y   ; Indicator = ^OTHER
        SET ^(6)=Z        ; Should access ^OTHER(6), not ^DATA(6)

        This test verifies runtime behavior which requires codegen.
        """
        pytest.fail("Stub - requires codegen runtime execution")


# =============================================================================
# Naked Reference Error Conditions (Codegen Level)
# =============================================================================


@pytest.mark.codegen
class TestNakedReferenceErrors:
    """Codegen tests for naked reference error conditions.

    Naked reference without prior global reference is an error (M1).
    Reference: §7.1.2.4, FR-046
    """

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: M1 error detection requires codegen"
    )
    def test_naked_without_prior_global_error(self):
        """Naked reference without prior global raises M1 error (§7.1.2.4).

        At start of routine or after indicator cleared, using ^(1) is an error.
        This test requires runtime execution to verify error M1 is raised.
        """
        pytest.fail("Stub - requires codegen runtime execution for M1 error")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: naked indicator scope at runtime")
    def test_naked_indicator_scope(self):
        """Naked indicator scope within routine execution (§7.1.2.4).

        The naked indicator persists across statements within same execution.
        SET ^DATA(1)=1 S X=^(2) S ^(3)=X  ; All reference ^DATA at runtime
        """
        pytest.fail("Stub - requires codegen runtime execution")


# =============================================================================
# Naked Reference Edge Cases (Codegen Level)
# =============================================================================


@pytest.mark.codegen
class TestNakedReferenceEdgeCases:
    """Codegen tests for naked reference edge cases.

    These tests verify RUNTIME behavior of naked references in various contexts.
    ASG parsing tests for these are in the respective command test files.
    Reference: §7.1.2.4, FR-046
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $DATA with naked at runtime")
    def test_data_function_with_naked(self):
        """$DATA(^(1)) uses naked reference at runtime (§7.1.2.4).

        ASG parsing is tested in test_s7_1_5_intrinsic_functions.py.
        This tests runtime resolution of the naked reference.
        """
        pytest.fail("Stub - requires codegen runtime execution")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ORDER with naked at runtime")
    def test_order_function_with_naked(self):
        """$ORDER(^(sub)) uses naked reference at runtime (§7.1.2.4).

        ASG parsing is tested in test_s7_1_5_intrinsic_functions.py.
        This tests runtime resolution of the naked reference.
        """
        pytest.fail("Stub - requires codegen runtime execution")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: KILL with naked at runtime")
    def test_kill_with_naked(self):
        """KILL ^(sub) uses naked reference at runtime (§7.1.2.4).

        ASG parsing is tested in test_s8_2_11_kill.py.
        This tests runtime resolution of the naked reference.
        """
        pytest.fail("Stub - requires codegen runtime execution")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE with naked at runtime")
    def test_merge_with_naked(self):
        """MERGE ^(dest)=^SRC uses naked at runtime (§7.1.2.4).

        ASG parsing is tested in test_s8_2_13_merge.py.
        This tests runtime resolution of the naked reference.
        """
        pytest.fail("Stub - requires codegen runtime execution")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LOCK with naked at runtime")
    def test_lock_with_naked(self):
        """LOCK ^(sub) uses naked reference at runtime (§7.1.2.4).

        ASG parsing is tested in test_s8_2_12_lock.py.
        This tests runtime resolution of the naked reference.
        """
        pytest.fail("Stub - requires codegen runtime execution")
