"""Cross-cutting tests for naked global references (§7.1.2.4).

Naked references are a language feature that affects all global variable
access. A naked reference uses ^(subscripts) where the global name is
omitted and taken from the most recent global reference.

Key behaviors (FR-046):
- Naked indicator is set by any full global reference
- Naked reference ^(sub) uses prior global's name
- Naked indicator is sequence-dependent (order matters)
- Invalid if no prior global reference exists

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
    MIntrinsicFunction,
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

    def test_naked_reference_multiple_subscripts(self):
        """^(1,2,3) parses as naked reference with subscripts (§7.1.2.4)."""
        stmt = analyze_first_command("S ^(1,2,3)=100")

        assert isinstance(stmt, MSetStatement)
        target = stmt.assignments[0].target
        assert isinstance(target, MNakedGlobal)
        assert len(target.subscripts) == 3
        # Check all subscripts are literals
        for i, sub in enumerate(target.subscripts, start=1):
            assert isinstance(sub, MLiteral)
            assert sub.value == i

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

    def test_naked_vs_full_global_distinction(self):
        """Parser distinguishes ^(1) from ^DATA(1) (§7.1.2.4)."""
        # Parse naked reference
        stmt_naked = analyze_first_command("S ^(1)=100")
        target_naked = stmt_naked.assignments[0].target
        assert isinstance(target_naked, MNakedGlobal)

        # Parse full global reference
        stmt_full = analyze_first_command("S ^DATA(1)=100")
        target_full = stmt_full.assignments[0].target
        assert isinstance(target_full, MGlobal)
        assert target_full.name == "DATA"

        # Verify they are different types
        assert type(target_naked) is not type(target_full)


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

    def test_sequence_dependency_detected(self):
        """ASG captures sequence of global and naked references (FR-046).

        SET ^DATA(1)=X,^(2)=Y should produce one MGlobal followed by MNakedGlobal.
        The sequence matters for runtime resolution.
        """
        stmt = analyze_first_command("S ^DATA(1)=X,^(2)=Y")

        assert isinstance(stmt, MSetStatement)
        assert len(stmt.assignments) == 2

        # First assignment establishes naked indicator
        target1 = stmt.assignments[0].target
        assert isinstance(target1, MGlobal)
        assert target1.name == "DATA"

        # Second assignment uses naked reference
        target2 = stmt.assignments[1].target
        assert isinstance(target2, MNakedGlobal)
        # At runtime, ^(2) would resolve to ^DATA(2)


# =============================================================================
# Naked Reference State Transition Tests (Codegen Level)
# =============================================================================


@pytest.mark.codegen
class TestNakedStateTransitions:
    """Codegen tests for naked indicator state transitions.

    These tests verify ASG structure for multi-statement naked reference
    patterns that would require codegen tracking at runtime.
    Reference: §7.1.2.4, FR-046
    """

    def test_set_establishes_naked_indicator(self):
        """SET ^DATA(1)=X establishes naked indicator to ^DATA (§7.1.2.4).

        SET ^DATA(1)=X followed by SET ^(2)=Y should produce:
        - First: MGlobal with name="DATA"
        - Second: MNakedGlobal (will use DATA at runtime)
        """
        stmts = analyze_all_commands("S ^DATA(1)=X S ^(2)=Y")

        assert len(stmts) == 2
        # First SET establishes the indicator
        target1 = stmts[0].assignments[0].target
        assert isinstance(target1, MGlobal)
        assert target1.name == "DATA"

        # Second SET uses naked reference
        target2 = stmts[1].assignments[0].target
        assert isinstance(target2, MNakedGlobal)

    def test_read_establishes_naked_indicator(self):
        """SET X=^DATA(1) establishes naked indicator to ^DATA (§7.1.2.4).

        Reading a global also sets the naked indicator.
        SET X=^DATA(1) followed by SET Y=^(2) should work.
        """
        stmts = analyze_all_commands("S X=^DATA(1) S Y=^(2)")

        assert len(stmts) == 2
        # First SET reads ^DATA(1), establishing indicator
        value1 = stmts[0].assignments[0].value
        assert isinstance(value1, MGlobal)
        assert value1.name == "DATA"

        # Second SET uses naked reference as value
        value2 = stmts[1].assignments[0].value
        assert isinstance(value2, MNakedGlobal)

    def test_naked_reference_subscript_chaining(self):
        """Naked reference replaces last subscript, chains others (§7.1.2.4).

        SET ^DATA(1,2)=X establishes indicator as ^DATA(1
        SET ^(3)=Y should access ^DATA(1,3) at runtime
        """
        stmts = analyze_all_commands("S ^DATA(1,2)=X S ^(3)=Y")

        assert len(stmts) == 2
        # First: ^DATA(1,2) - indicator becomes ^DATA(1
        target1 = stmts[0].assignments[0].target
        assert isinstance(target1, MGlobal)
        assert target1.name == "DATA"
        assert len(target1.subscripts) == 2

        # Second: ^(3) - at runtime resolves to ^DATA(1,3)
        target2 = stmts[1].assignments[0].target
        assert isinstance(target2, MNakedGlobal)
        assert len(target2.subscripts) == 1

    def test_naked_reference_multiple_subscripts(self):
        """Naked with multiple subscripts extends from indicator (§7.1.2.4).

        SET ^DATA(1)=X establishes indicator as ^DATA
        SET ^(2,3)=Y should access ^DATA(2,3) at runtime
        """
        stmts = analyze_all_commands("S ^DATA(1)=X S ^(2,3)=Y")

        assert len(stmts) == 2
        # First: ^DATA(1) - indicator becomes ^DATA
        target1 = stmts[0].assignments[0].target
        assert isinstance(target1, MGlobal)
        assert len(target1.subscripts) == 1

        # Second: ^(2,3) has two subscripts
        target2 = stmts[1].assignments[0].target
        assert isinstance(target2, MNakedGlobal)
        assert len(target2.subscripts) == 2

    def test_naked_reference_updates_indicator(self):
        """Naked reference itself updates the indicator (§7.1.2.4).

        After ^DATA(1)=X, indicator is ^DATA
        After ^(2)=Y, indicator is ^DATA( (stripped last sub)
        After ^(3)=Z, should access ^DATA(3)
        """
        stmts = analyze_all_commands("S ^DATA(1)=X S ^(2)=Y S ^(3)=Z")

        assert len(stmts) == 3
        # All three have the expected types
        assert isinstance(stmts[0].assignments[0].target, MGlobal)
        assert isinstance(stmts[1].assignments[0].target, MNakedGlobal)
        assert isinstance(stmts[2].assignments[0].target, MNakedGlobal)

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

    def test_naked_indicator_scope(self):
        """Naked indicator scope within routine execution (§7.1.2.4).

        The naked indicator persists across statements within same execution.
        This test verifies ASG captures the sequence for codegen analysis.
        """
        # Multiple statements in sequence - naked indicator carries through
        stmts = analyze_all_commands("S ^DATA(1)=1 S X=^(2) S ^(3)=X")

        assert len(stmts) == 3
        # First: full global sets indicator
        assert isinstance(stmts[0].assignments[0].target, MGlobal)
        # Second: naked reference as value
        assert isinstance(stmts[1].assignments[0].value, MNakedGlobal)
        # Third: naked reference as target
        assert isinstance(stmts[2].assignments[0].target, MNakedGlobal)


# =============================================================================
# Naked Reference Edge Cases (Codegen Level)
# =============================================================================


@pytest.mark.codegen
class TestNakedReferenceEdgeCases:
    """Codegen tests for naked reference edge cases.

    Naked references can appear in various contexts beyond simple SET.
    Reference: §7.1.2.4, FR-046
    """

    def test_data_function_with_naked(self):
        """$DATA(^(1)) uses naked reference as argument (§7.1.2.4).

        $DATA on a naked reference should parse correctly.
        """
        stmt = analyze_first_command("S X=$D(^(1))")
        assert isinstance(stmt, MSetStatement)
        func = stmt.assignments[0].value
        assert isinstance(func, MIntrinsicFunction)
        assert func.name.upper() in ("D", "DATA")
        # First argument should be naked global
        assert len(func.arguments) >= 1
        assert isinstance(func.arguments[0], MNakedGlobal)

    def test_order_function_with_naked(self):
        """$ORDER(^(sub)) uses naked reference as argument (§7.1.2.4).

        $ORDER navigates globals and can use naked references.
        """
        stmt = analyze_first_command('S X=$O(^(""))')
        assert isinstance(stmt, MSetStatement)
        func = stmt.assignments[0].value
        assert isinstance(func, MIntrinsicFunction)
        assert func.name.upper() in ("O", "ORDER")
        # First argument should be naked global
        assert isinstance(func.arguments[0], MNakedGlobal)

    def test_kill_with_naked(self):
        """KILL ^(sub) uses naked reference (§7.1.2.4).

        KILL can target naked references.
        """
        stmt = analyze_first_command("K ^(1)")

        assert isinstance(stmt, MKillStatement)
        assert len(stmt.targets) == 1
        target = stmt.targets[0]
        assert isinstance(target, MNakedGlobal)
        assert len(target.subscripts) == 1

    def test_merge_with_naked(self):
        """MERGE ^(dest)=^SRC uses naked for destination (§7.1.2.4).

        MERGE copies tree structures and can use naked references.
        The destination is captured as MNakedGlobal in ASG.
        """
        from m2py.asg.statements import MMergeStatement

        stmt = analyze_first_command("M ^(1)=^SRC")

        assert isinstance(stmt, MMergeStatement)
        assert len(stmt.merges) == 1
        dest = stmt.merges[0].destination
        assert isinstance(dest, MNakedGlobal)
        assert len(dest.subscripts) == 1
        # Source should be a full global
        source = stmt.merges[0].source
        assert isinstance(source, MGlobal)
        assert source.name == "SRC"

    def test_lock_with_naked(self):
        """LOCK ^(sub) uses naked reference (§7.1.2.4).

        LOCK controls access to resources including naked references.
        Lock targets are returned as dicts with 'lockop' and 'target' keys.
        """
        from m2py.asg.statements import MLockStatement

        stmt = analyze_first_command("L ^(1)")

        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1
        # Lock targets are dicts with 'lockop' and 'target' keys
        target_dict = stmt.targets[0]
        assert isinstance(target_dict, dict)
        assert "target" in target_dict
        assert isinstance(target_dict["target"], MNakedGlobal)
        assert len(target_dict["target"].subscripts) == 1
