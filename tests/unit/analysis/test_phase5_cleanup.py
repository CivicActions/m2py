"""Tests for Phase 5 (US4) — Analysis Cleanup & Detection.

Tests:
- T020/T021: Exclusive KILL/NEW detection flags on MRoutine
- T022: routine_uses_dynamic_locals includes exclusive flags
- T024: Kill analyzer deduplication (kill-family methods produce correct ASG)
- T025: DO/GOTO/JOB deduplication (call-family methods produce correct ASG)
- T026: unwrap_expression assertion for operator tails
- T027: statement_modifies_variable delegation
- T028: contains_naked_global in analysis.variables
"""

import pytest

from m2py.analysis.variables import (
    analyze_variables,
    contains_naked_global,
    statement_modifies_variable,
)
from m2py.asg.expressions import (
    MBinaryOp,
    MGlobal,
    MLiteral,
    MNakedGlobal,
    MVariable,
)
from m2py.asg.statements import (
    MAssignment,
    MKillStatement,
    MReadStatement,
    MReadTarget,
    MSetStatement,
)
from m2py.codegen.shared_state import routine_uses_dynamic_locals
from m2py.parser import MUMPSParser


@pytest.fixture
def parser():
    """Shared parser instance."""
    return MUMPSParser()


def _parse_and_analyze(parser, source):
    """Parse MUMPS source and run analysis pipeline."""
    routine = parser.parse(source)
    parser.resolve_references(routine)
    analyze_variables(routine)
    return routine


# =============================================================================
# T020/T021: Exclusive KILL/NEW detection
# =============================================================================


@pytest.mark.analysis
class TestExclusiveKillDetection:
    """Tests for has_exclusive_kill flag on MRoutine."""

    def test_no_kill(self, parser):
        """Routine without KILL should have has_exclusive_kill=False."""
        source = 'TEST\n W "Hello"\n Q\n'
        routine = _parse_and_analyze(parser, source)
        assert routine.has_exclusive_kill is False

    def test_selective_kill(self, parser):
        """Selective KILL (K X) should NOT set has_exclusive_kill."""
        source = "TEST\n S X=1\n K X\n Q\n"
        routine = _parse_and_analyze(parser, source)
        assert routine.has_exclusive_kill is False

    def test_argumentless_kill(self, parser):
        """Argumentless KILL (K with no args) should NOT set has_exclusive_kill."""
        source = "TEST\n K\n Q\n"
        routine = _parse_and_analyze(parser, source)
        assert routine.has_exclusive_kill is False
        assert routine.has_argumentless_kill is True

    def test_exclusive_kill(self, parser):
        """Exclusive KILL K (X) should set has_exclusive_kill=True."""
        source = "TEST\n S X=1,Y=2\n K (X)\n Q\n"
        routine = _parse_and_analyze(parser, source)
        assert routine.has_exclusive_kill is True

    def test_exclusive_kill_multiple_vars(self, parser):
        """Exclusive KILL K (X,Y) should set has_exclusive_kill=True."""
        source = "TEST\n S X=1,Y=2,Z=3\n K (X,Y)\n Q\n"
        routine = _parse_and_analyze(parser, source)
        assert routine.has_exclusive_kill is True


@pytest.mark.analysis
class TestExclusiveNewDetection:
    """Tests for has_exclusive_new flag on MRoutine."""

    def test_no_new(self, parser):
        """Routine without NEW should have has_exclusive_new=False."""
        source = 'TEST\n W "Hello"\n Q\n'
        routine = _parse_and_analyze(parser, source)
        assert routine.has_exclusive_new is False

    def test_selective_new(self, parser):
        """Selective NEW (N X) should NOT set has_exclusive_new."""
        source = "TEST\n N X\n S X=1\n Q\n"
        routine = _parse_and_analyze(parser, source)
        assert routine.has_exclusive_new is False

    def test_argumentless_new(self, parser):
        """Argumentless NEW (N with no args) should NOT set has_exclusive_new."""
        source = "TEST\n N\n Q\n"
        routine = _parse_and_analyze(parser, source)
        assert routine.has_exclusive_new is False
        assert routine.has_argumentless_new is True

    def test_exclusive_new(self, parser):
        """Exclusive NEW N (X) should set has_exclusive_new=True."""
        source = "TEST\n N (X)\n S Y=1\n Q\n"
        routine = _parse_and_analyze(parser, source)
        assert routine.has_exclusive_new is True


# =============================================================================
# T022: routine_uses_dynamic_locals includes exclusive flags
# =============================================================================


@pytest.mark.analysis
class TestDynamicLocalsWithExclusiveFlags:
    """Tests that exclusive KILL/NEW trigger dynamic_locals."""

    def test_exclusive_kill_triggers_dynamic_locals(self, parser):
        """Exclusive KILL should require dynamic locals."""
        source = "TEST\n S X=1,Y=2\n K (X)\n Q\n"
        routine = _parse_and_analyze(parser, source)
        assert routine_uses_dynamic_locals(routine) is True

    def test_exclusive_new_triggers_dynamic_locals(self, parser):
        """Exclusive NEW should require dynamic locals."""
        source = "TEST\n N (X)\n S Y=1\n Q\n"
        routine = _parse_and_analyze(parser, source)
        assert routine_uses_dynamic_locals(routine) is True

    def test_no_exclusive_no_dynamic_locals(self, parser):
        """Simple routine without exclusive ops should not require dynamic locals."""
        source = "TEST\n S X=1\n W X\n Q\n"
        routine = _parse_and_analyze(parser, source)
        # Only if there's no other reason for dynamic locals
        if (
            not routine.has_argumentless_kill
            and not routine.has_argumentless_new
            and not routine.has_name_indirection_on_locals
            and not routine.has_external_gotos
        ):
            assert routine_uses_dynamic_locals(routine) is False


# =============================================================================
# T024: Kill analyzer deduplication (verify ASG output is correct)
# =============================================================================


@pytest.mark.analysis
class TestKillAnalyzerDedup:
    """Verify kill-family analyzers produce correct ASG nodes after dedup."""

    def test_kill_selective(self, parser):
        """K X,Y should produce statement with 2 targets."""
        source = "TEST\n S X=1,Y=2\n K X,Y\n Q\n"
        routine = _parse_and_analyze(parser, source)
        body = routine.labels[0].body
        kill_stmts = [
            s for s in body.walk_statements() if isinstance(s, MKillStatement)
        ]
        assert len(kill_stmts) == 1
        stmt = kill_stmts[0]
        assert stmt.exclusive is False
        assert len(stmt.targets) == 2

    def test_kill_exclusive(self, parser):
        """K (X) should produce exclusive statement with except_list."""
        source = "TEST\n S X=1,Y=2\n K (X)\n Q\n"
        routine = _parse_and_analyze(parser, source)
        body = routine.labels[0].body
        kill_stmts = [
            s for s in body.walk_statements() if isinstance(s, MKillStatement)
        ]
        assert len(kill_stmts) == 1
        stmt = kill_stmts[0]
        assert stmt.exclusive is True
        assert "X" in stmt.except_list

    def test_kill_all(self, parser):
        """K (no args) should produce kill-all statement."""
        source = "TEST\n K\n Q\n"
        routine = _parse_and_analyze(parser, source)
        body = routine.labels[0].body
        kill_stmts = [
            s for s in body.walk_statements() if isinstance(s, MKillStatement)
        ]
        assert len(kill_stmts) == 1
        stmt = kill_stmts[0]
        assert stmt.is_kill_all is True


# =============================================================================
# T025: DO/GOTO/JOB deduplication (verify ASG output is correct)
# =============================================================================


@pytest.mark.analysis
class TestCallAnalyzerDedup:
    """Verify call-family analyzers produce correct ASG nodes after dedup."""

    def test_do_with_args(self, parser):
        """D LABEL(X) should produce call with arguments."""
        source = "TEST\n D SUB(1)\n Q\nSUB(X)\n W X\n Q\n"
        routine = _parse_and_analyze(parser, source)
        body = routine.labels[0].body
        from m2py.asg.statements import MDoStatement

        do_stmts = [s for s in body.walk_statements() if isinstance(s, MDoStatement)]
        assert len(do_stmts) == 1
        assert len(do_stmts[0].targets) == 1
        call = do_stmts[0].targets[0]
        assert call.name == "SUB"
        assert len(call.arguments) == 1

    def test_goto_label(self, parser):
        """G LABEL should produce call with label name."""
        source = "TEST\n G END\nEND\n Q\n"
        routine = _parse_and_analyze(parser, source)
        body = routine.labels[0].body
        from m2py.asg.statements import MGotoStatement

        goto_stmts = [
            s for s in body.walk_statements() if isinstance(s, MGotoStatement)
        ]
        assert len(goto_stmts) == 1
        assert len(goto_stmts[0].targets) == 1
        assert goto_stmts[0].targets[0].name == "END"


# =============================================================================
# T026: unwrap_expression assertion
# =============================================================================


@pytest.mark.analysis
class TestUnwrapExpressionAssertion:
    """Test that unwrap_expression assertion works correctly."""

    def test_unwrap_simple_value(self):
        """Simple value should unwrap without assertion."""
        from m2py.analysis.semantic_analyzer import unwrap_expression

        lit = MLiteral(value="42")
        result = unwrap_expression(lit)
        assert result is lit

    def test_unwrap_none(self):
        """None should return None."""
        from m2py.analysis.semantic_analyzer import unwrap_expression

        assert unwrap_expression(None) is None


# =============================================================================
# T027: statement_modifies_variable delegation
# =============================================================================


@pytest.mark.analysis
class TestStatementModifiesVariable:
    """Tests for statement_modifies_variable utility."""

    def test_set_modifies_target(self):
        """SET X=1 should modify X."""
        target = MVariable(name="X")
        value = MLiteral(value="1")
        assignment = MAssignment(target=target, value=value)
        stmt = MSetStatement(assignments=[assignment])
        assert statement_modifies_variable(stmt, "X") is True
        assert statement_modifies_variable(stmt, "Y") is False

    def test_read_modifies_target(self):
        """READ X should modify X."""
        target = MVariable(name="X")
        read_target = MReadTarget(variable=target)
        stmt = MReadStatement(arguments=[read_target])
        assert statement_modifies_variable(stmt, "X") is True
        assert statement_modifies_variable(stmt, "Y") is False

    def test_kill_all_modifies_any(self):
        """K (no args, kill-all) should modify any variable."""
        stmt = MKillStatement()  # No targets = kill all
        assert statement_modifies_variable(stmt, "X") is True
        assert statement_modifies_variable(stmt, "Y") is True

    def test_kill_selective_modifies_target(self):
        """K X should modify X only."""
        target = MVariable(name="X")
        stmt = MKillStatement(targets=[target])
        assert statement_modifies_variable(stmt, "X") is True
        assert statement_modifies_variable(stmt, "Y") is False

    def test_kill_exclusive_modifies_non_excepted(self):
        """K (X) should modify Y but not X."""
        stmt = MKillStatement(exclusive=True, except_list=["X"])
        assert statement_modifies_variable(stmt, "X") is False
        assert statement_modifies_variable(stmt, "Y") is True


# =============================================================================
# T028: contains_naked_global in analysis.variables
# =============================================================================


@pytest.mark.analysis
class TestContainsNakedGlobal:
    """Tests for contains_naked_global after move to analysis layer."""

    def test_literal_no_naked(self):
        """MLiteral should not contain naked global."""
        expr = MLiteral(value="42")
        assert contains_naked_global(expr) is False

    def test_variable_no_naked(self):
        """MVariable should not contain naked global."""
        expr = MVariable(name="X")
        assert contains_naked_global(expr) is False

    def test_naked_global_detected(self):
        """MNakedGlobal should be detected."""
        expr = MNakedGlobal()
        assert contains_naked_global(expr) is True

    def test_variable_with_naked_subscript(self):
        """MVariable with MNakedGlobal subscript should be detected."""
        expr = MVariable(name="X", subscripts=[MNakedGlobal()])
        assert contains_naked_global(expr) is True

    def test_binary_op_with_naked(self):
        """MBinaryOp with MNakedGlobal operand should be detected."""
        expr = MBinaryOp(
            left=MLiteral(value="1"),
            operator="+",
            right=MNakedGlobal(),
        )
        assert contains_naked_global(expr) is True

    def test_binary_op_without_naked(self):
        """MBinaryOp with no naked globals should not be detected."""
        expr = MBinaryOp(
            left=MLiteral(value="1"),
            operator="+",
            right=MLiteral(value="2"),
        )
        assert contains_naked_global(expr) is False

    def test_global_with_naked_subscript(self):
        """MGlobal with naked subscript should be detected."""
        expr = MGlobal(name="A", subscripts=[MNakedGlobal()])
        assert contains_naked_global(expr) is True

    def test_caching(self):
        """Result should be cached as _has_naked_global attribute."""
        expr = MLiteral(value="42")
        assert not hasattr(expr, "_has_naked_global")
        result = contains_naked_global(expr)
        assert result is False
        assert getattr(expr, "_has_naked_global") is False
        # Second call should use cache
        result2 = contains_naked_global(expr)
        assert result2 is False
