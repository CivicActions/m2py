"""Tests for Indirection ASG analysis (§6.3.1).

Reference: MUMPS 1995 ANSI Standard, Section 6.3.1
"""

import pytest

from m2py.asg.enums import IndirectionType
from m2py.asg.expressions import MPatternMatch
from m2py.asg.statements import MSetStatement
from m2py.parser.textx_classes import Indirection, LocalVariable


@pytest.mark.asg
class TestIndirectionAnalysis:
    """ASG-level tests for indirection analysis (§6.3.1)."""

    def test_name_indirection_resolution(self, analyze_routine):
        """Name indirection (@var) is correctly represented in ASG (§6.3.1).

        Per 1995__a106010.md: "If the evaluation of a command or any of the
        arguments of a command encounters an indirect expression of the form
        @expritem which cannot be resolved using the syntax or metatalanguage
        defined for the command..."

        At ASG level, name indirection creates an Indirection node with
        indirection_type=NAME and the dereferenced variable in expression.
        """
        routine = analyze_routine("TEST\n S @VAR=1\n Q")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MSetStatement)

        target = stmt.assignments[0].target
        assert isinstance(target, Indirection)
        assert target.indirection_type == IndirectionType.NAME
        assert isinstance(target.expression, LocalVariable)
        assert target.expression.name == "VAR"

    def test_argument_indirection_in_set_value(self, analyze_routine):
        """Argument indirection in SET value context is correctly analyzed (§6.3.1).

        Per 1984 addition: @VAR@(subs) resolves VAR to a name, then appends
        subscripts. The expression-level analysis is in s7_expressions/test_s7_3.

        This test verifies the SET statement correctly carries the indirection.
        """
        routine = analyze_routine("TEST\n S Y=@X@(1,2)\n Q")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MSetStatement)

        value = stmt.assignments[0].value
        assert isinstance(value, Indirection)
        # Detailed expression checks are in s7_expressions/test_s7_3_indirection

    def test_pattern_indirection_in_if_context(self, analyze_routine):
        """Pattern indirection in IF condition context is correctly analyzed (§6.3.1).

        Pattern indirection uses @ in the pattern position of the pattern
        match operator (?). The expression-level analysis is in s7_expressions.

        This test verifies the IF statement correctly carries the pattern match.
        """
        routine = analyze_routine("TEST\n I X?@PAT W 1\n Q")

        stmt = routine.labels[0].body.statements[0]
        # First condition of IF statement should be a pattern match
        condition = stmt.conditions[0]

        assert isinstance(condition, MPatternMatch)
        # Detailed pattern_indirect checks are in s7_expressions/test_s7_2_5_pattern_match

    def test_indirection_static_analysis(self, analyze_routine):
        """Indirection impact on static analysis is tracked (§6.3.1).

        Indirection nodes have properties that indicate static analysis
        characteristics: can_resolve_statically, requires_runtime_eval.
        """
        routine = analyze_routine("TEST\n S @VAR=1\n Q")

        stmt = routine.labels[0].body.statements[0]
        target = stmt.assignments[0].target

        assert isinstance(target, Indirection)
        # Indirection requires runtime evaluation by default
        assert target.requires_runtime_eval is True
        # Cannot resolve statically without constant propagation
        assert target.can_resolve_statically is False

    def test_do_indirection_requires_runtime(self, analyze_routine):
        """DO @VAR has indirect call detected and marked for runtime (§6.3.1).

        Since the target is determined at runtime, the call cannot be
        statically resolved. The MCall should have label_is_indirect=True
        and indirection set to MIndirection wrapping the variable.

        After signature analysis via compute_all_signatures, the label's
        requires_runtime_scope and routine's requires_runtime_eval will be True.
        """
        from m2py.analysis.variables import compute_all_signatures
        from m2py.parser import MUMPSParser
        from m2py.asg.expressions import MIndirection

        parser = MUMPSParser()
        result = parser.parse("TEST\n D @X")

        # The specific call should have indirection detected
        stmt = result.labels[0].body.statements[0]
        call = stmt.targets[0]
        assert call.label_is_indirect is True
        assert call.indirection is not None
        assert call.indirection_levels == 1
        # Indirection expression is MIndirection wrapping the variable
        assert isinstance(call.indirection, MIndirection)
        assert isinstance(call.indirection.expression, LocalVariable)
        assert call.indirection.expression.name == "X"

        # After signature analysis, routine-level flag is set
        signatures = compute_all_signatures(result)
        assert signatures["TEST"].requires_runtime_scope is True
        assert result.requires_runtime_eval is True

    def test_xecute_indirection_detection(self, analyze_routine):
        """XECUTE @VAR has indirection and requires runtime eval (§6.3.1).

        XECUTE always requires runtime evaluation. The statement itself
        has requires_runtime_eval=True. With indirection, even the code
        string is not known until runtime.
        """
        from m2py.asg.statements import MXecuteStatement
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        result = parser.parse("TEST\n X @X")
        stmt = result.labels[0].body.statements[0]

        assert isinstance(stmt, MXecuteStatement)
        # XECUTE statement requires runtime evaluation
        assert stmt.requires_runtime_eval is True
        # The code_expressions should contain the indirection
        assert len(stmt.code_expressions) >= 1
        expr = stmt.code_expressions[0]
        assert isinstance(expr, Indirection)
        assert isinstance(expr.expression, LocalVariable)
        assert expr.expression.name == "X"
