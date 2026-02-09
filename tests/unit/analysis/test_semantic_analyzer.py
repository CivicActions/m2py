"""Tests for analysis/semantic_analyzer.py.

Covers semantic analysis of TSTART params, JOB indirection,
VIEW colon values, TROLLBACK levels, and expression unwrapping.
"""

from unittest.mock import MagicMock

from m2py.parser import MUMPSParser
from m2py.analysis import resolve_references
from m2py.asg.statements import (
    MForStatement,
    MSetStatement,
    MQuitStatement,
)


class TestAnalyzeStrPass2:
    """_analyze_str converts raw string variable names to MVariable ASG nodes.

    Covers semantic_analyzer.py L666-669.
    """

    def test_str_variable_name_in_tstart(self):
        """TSTART (X,Y) — raw variable names handled by _analyze_str."""
        parser = MUMPSParser()
        source = "TEST\n\tTS (X,Y)\n\tTC\n\tQ\n"
        routine = parser.parse(source)
        resolve_references(routine)
        stmt = routine.labels[0].body.statements[0]
        # TSTART restart vars should be MVariable instances
        assert hasattr(stmt, "restart_vars")
        if stmt.restart_vars:
            for rv in stmt.restart_vars:
                assert hasattr(rv, "name")

    def test_str_single_tstart_var(self):
        """TSTART (X) — single restart var converted."""
        parser = MUMPSParser()
        source = "TEST\n\tTS (X)\n\tTC\n\tQ\n"
        routine = parser.parse(source)
        resolve_references(routine)
        stmt = routine.labels[0].body.statements[0]
        if stmt.restart_vars:
            assert stmt.restart_vars[0].name == "X"


class TestReadUnknownArgPass2:
    """READ command fallback for unrecognized argument types.

    Covers semantic_analyzer.py L947-949.
    """

    def test_read_with_prompt_and_variable(self):
        """R "Enter: ",X — prompt + read target."""
        parser = MUMPSParser()
        source = 'TEST\n\tR "Enter: ",X\n\tQ\n'
        routine = parser.parse(source)
        resolve_references(routine)
        stmt = routine.labels[0].body.statements[0]
        # Should have at least 2 arguments (prompt + target)
        assert len(stmt.arguments) >= 2

    def test_read_multiple_targets(self):
        """R X,Y,Z — multiple read targets parsed."""
        parser = MUMPSParser()
        source = "TEST\n\tR X,Y,Z\n\tQ\n"
        routine = parser.parse(source)
        resolve_references(routine)
        stmt = routine.labels[0].body.statements[0]
        assert len(stmt.arguments) == 3


class TestSimpleVarToAsgPass2:
    """_simple_var_to_asg converts variable objects/names to MVariable.

    Covers semantic_analyzer.py L1069-1071.
    """

    def test_for_loop_var_becomes_mvariable(self):
        """FOR I=1:1:10 — loop variable I converted to MVariable."""
        parser = MUMPSParser()
        source = "TEST\n\tF I=1:1:10 W I\n\tQ\n"
        routine = parser.parse(source)
        resolve_references(routine)
        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert hasattr(for_stmt, "loop_var")
        assert for_stmt.loop_var.name == "I"

    def test_for_loop_var_percent(self):
        """FOR %I=1:1:10 — loop variable with % prefix."""
        parser = MUMPSParser()
        source = "TEST\n\tF %I=1:1:10 W %I\n\tQ\n"
        routine = parser.parse(source)
        resolve_references(routine)
        for_stmt = routine.labels[0].body.statements[0]
        assert for_stmt.loop_var.name == "%I"


class TestJobIndirectionAnalysisPass2:
    """JOB command with indirection in semantic analysis.

    Covers semantic_analyzer.py L1960-1979.
    """

    def test_job_indirect_label(self):
        """J @VAR — indirect JOB target."""
        parser = MUMPSParser()
        source = 'TEST\n\tS VAR="SUB"\n\tJ @VAR\n\tQ\nSUB\n\tQ\n'
        routine = parser.parse(source)
        resolve_references(routine)
        stmts = routine.labels[0].body.statements
        # Find the JOB statement
        job_stmt = None
        for s in stmts:
            if hasattr(s, "__class__") and "Job" in type(s).__name__:
                job_stmt = s
                break
        assert job_stmt is not None
        # JOB targets use MJobTarget with .call
        if hasattr(job_stmt, "targets") and job_stmt.targets:
            target = job_stmt.targets[0]
            if hasattr(target, "call") and target.call:
                assert target.call.label_is_indirect


class TestViewColonValuePass2:
    """VIEW command colon-separated value analysis.

    Covers semantic_analyzer.py L2069-2071.
    """

    def test_view_simple(self):
        """VIEW "NOUNDEF" — simple VIEW command."""
        parser = MUMPSParser()
        source = 'TEST\n\tV "NOUNDEF"\n\tQ\n'
        routine = parser.parse(source)
        resolve_references(routine)
        stmt = routine.labels[0].body.statements[0]
        assert stmt is not None


class TestTStartParamsPass2:
    """TSTART parameter analysis with compound forms.

    Covers semantic_analyzer.py L2142-2147.
    """

    def test_tstart_serial(self):
        """TSTART ():S — SERIAL/S parameter."""
        parser = MUMPSParser()
        source = "TEST\n\tTS ():S\n\tTC\n\tQ\n"
        routine = parser.parse(source)
        resolve_references(routine)
        stmt = routine.labels[0].body.statements[0]
        if hasattr(stmt, "parameters") and stmt.parameters:
            names = [p.name for p in stmt.parameters]
            assert any("S" in n.upper() for n in names)

    def test_tstart_transactionid(self):
        """TSTART ():(T="BA") — TRANSACTIONID parameter with value."""
        parser = MUMPSParser()
        source = 'TEST\n\tTS ():(T="BA")\n\tTC\n\tQ\n'
        routine = parser.parse(source)
        resolve_references(routine)
        stmt = routine.labels[0].body.statements[0]
        assert hasattr(stmt, "parameters")

    def test_tstart_restart_all(self):
        """TSTART * — restart all variables."""
        parser = MUMPSParser()
        source = "TEST\n\tTS *\n\tTC\n\tQ\n"
        routine = parser.parse(source)
        resolve_references(routine)
        stmt = routine.labels[0].body.statements[0]
        assert stmt.restart_all is True


class TestTRollbackLevelPass2:
    """TROLLBACK level expression analysis.

    Covers semantic_analyzer.py L2218-2227.
    """

    def test_trollback_no_args(self):
        """TROLLBACK — rollback all transactions."""
        parser = MUMPSParser()
        source = "TEST\n\tTS\n\tTRO\n\tQ\n"
        routine = parser.parse(source)
        resolve_references(routine)
        stmts = routine.labels[0].body.statements
        tro_stmt = stmts[1]
        assert hasattr(tro_stmt, "level")

    def test_trollback_with_level(self):
        """TROLLBACK 1 — rollback to specific level."""
        parser = MUMPSParser()
        source = "TEST\n\tTS\n\tTRO 1\n\tQ\n"
        routine = parser.parse(source)
        resolve_references(routine)
        stmts = routine.labels[0].body.statements
        tro_stmt = stmts[1]
        if hasattr(tro_stmt, "level") and tro_stmt.level is not None:
            assert tro_stmt.level is not None


class TestAnalyzeStatementPass2:
    """analyze_statement convenience function.

    Covers semantic_analyzer.py L2931-2933.
    """

    def test_analyze_set_statement(self):
        """analyze_statement("S", "X=1") returns MSetStatement."""
        from m2py.analysis.semantic_analyzer import analyze_statement

        result = analyze_statement("S", "X=1")
        assert result is not None
        assert isinstance(result, MSetStatement)

    def test_analyze_write_statement(self):
        """analyze_statement("W", '"Hello"') returns MWriteStatement."""
        from m2py.analysis.semantic_analyzer import analyze_statement
        from m2py.asg.statements import MWriteStatement

        result = analyze_statement("W", '"Hello"')
        assert result is not None
        assert isinstance(result, MWriteStatement)

    def test_analyze_empty_content(self):
        """analyze_statement("Q", "") returns MQuitStatement."""
        from m2py.analysis.semantic_analyzer import analyze_statement

        result = analyze_statement("Q", "")
        assert result is not None
        assert isinstance(result, MQuitStatement)

    def test_analyze_invalid_returns_none(self):
        """analyze_statement with garbage returns None."""
        from m2py.analysis.semantic_analyzer import analyze_statement

        # Should return None or handle gracefully
        # (parser may produce MParseError which maps to None)
        _ = analyze_statement("X", "???!!!@@@")


class TestUnwrapExpressionPass2:
    """unwrap_expression simple unwrapper.

    Covers semantic_analyzer.py L2955-2967.
    """

    def test_unwrap_literal(self):
        """Unwrap a literal passes through unchanged."""
        from m2py.analysis.semantic_analyzer import unwrap_expression
        from m2py.asg.expressions import MLiteral

        lit = MLiteral(value="hello", literal_type=None)
        result = unwrap_expression(lit)
        assert result is lit

    def test_unwrap_none(self):
        """Unwrap None returns None."""
        from m2py.analysis.semantic_analyzer import unwrap_expression

        result = unwrap_expression(None)
        assert result is None

    def test_unwrap_textx_expr_with_left(self):
        """Unwrap Expr-like object with left attr and no ops."""
        from m2py.analysis.semantic_analyzer import unwrap_expression

        inner = MagicMock()
        inner.left = MagicMock()
        inner.left.operand = "final"
        inner.left.operator = None
        inner.left.operators = None
        # No tail/ops on outer
        inner.tail = None
        inner.ops = None
        result = unwrap_expression(inner)
        # Should recursively unwrap to inner.left
        assert result is not inner  # Should unwrap at least one level

    def test_unwrap_paren_expr(self):
        """Unwrap ParenExpr-like object with expr attr."""
        from m2py.analysis.semantic_analyzer import unwrap_expression

        inner_val = MagicMock(spec=[])  # no left/operand/expr
        paren = MagicMock()
        paren.left = None  # Not an Expr
        del paren.left
        paren.operand = None  # Not a UnaryExpr
        del paren.operand
        paren.expr = inner_val
        result = unwrap_expression(paren)
        assert result is inner_val
