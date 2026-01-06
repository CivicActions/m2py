"""Tests for Indirection parsing (§7.3).

Tests verify the textX grammar correctly captures indirection syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.3
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes, get_expression_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for indirection tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestIndirectionParsing:
    """Parser-level tests for Indirection (§7.3).

    All commands use the same Indirection rule from expressions.tx,
    which handles:
    - Single indirection: @VAR
    - Nested indirection: @@VAR (parsed as @(@VAR))
    - Expression indirection: @(expr)
    - Subscripted indirection: @VAR(sub1,sub2)

    DO, GOTO, and LOCK use IndirectChain for additional features
    like @label^routine patterns.
    """

    # --- KILL indirection ---
    def test_kill_indirection(self, command_metamodel):
        """K @A - kill indirection."""
        model = command_metamodel.model_from_str("K @A", "KillCommand")
        assert len(model.args) == 1
        arg = model.args[0]
        assert arg.target is not None
        # target is an Indirection
        assert arg.target.__class__.__name__ == "Indirection"

    def test_kill_double_indirection(self, command_metamodel):
        """K @@A - nested indirection."""
        model = command_metamodel.model_from_str("K @@A", "KillCommand")
        assert len(model.args) == 1
        target = model.args[0].target
        assert target.__class__.__name__ == "Indirection"
        # Nested: expr is also Indirection (textX uses 'expr', not 'expression')
        assert target.expr.__class__.__name__ == "Indirection"

    def test_kill_multiple_indirection(self, command_metamodel):
        """K @A,@B - multiple indirection targets."""
        model = command_metamodel.model_from_str("K @A,@B", "KillCommand")
        assert len(model.args) == 2
        assert model.args[0].target.__class__.__name__ == "Indirection"
        assert model.args[1].target.__class__.__name__ == "Indirection"

    # --- SET indirection ---
    def test_set_target_indirection(self, command_metamodel):
        """S @A=1 - indirection as target."""
        model = command_metamodel.model_from_str("S @A=1", "SetCommand")
        assert len(model.assignments) == 1
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "Indirection"

    def test_set_value_indirection(self, command_metamodel):
        """S X=@A - indirection as value."""
        model = command_metamodel.model_from_str("S X=@A", "SetCommand")
        assert len(model.assignments) == 1
        # Value is an expression containing Indirection
        assert model.assignments[0].value is not None

    def test_set_both_indirection(self, command_metamodel):
        """S @B=@A - indirection on both sides."""
        model = command_metamodel.model_from_str("S @B=@A", "SetCommand")
        assert len(model.assignments) == 1
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "Indirection"

    def test_set_double_indirection(self, command_metamodel):
        """S @@A=1 - nested indirection as target."""
        model = command_metamodel.model_from_str("S @@A=1", "SetCommand")
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "Indirection"
        # textX uses 'expr' attribute
        assert target.expr.__class__.__name__ == "Indirection"

    def test_set_argument_indirection(self, command_metamodel):
        """S @A - argument-level indirection (var contains 'X=1')."""
        model = command_metamodel.model_from_str("S @A", "SetCommand")
        assert len(model.assignments) == 1
        # This uses SetIndirection
        arg = model.assignments[0]
        assert hasattr(arg, "indirect") and arg.indirect is not None

    # --- WRITE indirection (via Expr wrapper) ---
    def test_write_indirection(self, command_metamodel):
        """W @A - indirection as value (wrapped in Expr)."""
        model = command_metamodel.model_from_str("W @A", "WriteCommand")
        assert len(model.args) == 1
        arg = model.args[0].arg
        # WRITE uses Expr which wraps Indirection
        # Need to unwrap: arg.left.operand is the Indirection
        assert arg.__class__.__name__ == "Expr"
        assert arg.left.operand.__class__.__name__ == "Indirection"

    def test_write_double_indirection(self, command_metamodel):
        """W @@C - nested indirection."""
        model = command_metamodel.model_from_str("W @@C", "WriteCommand")
        arg = model.args[0].arg
        # Unwrap Expr to get Indirection
        inner = arg.left.operand
        assert inner.__class__.__name__ == "Indirection"
        assert inner.expr.__class__.__name__ == "Indirection"

    # --- READ indirection ---
    def test_read_indirection(self, command_metamodel):
        """R @A - indirection as target."""
        model = command_metamodel.model_from_str("R @A", "ReadCommand")
        assert len(model.args) == 1
        target = model.args[0].arg.target
        assert target.__class__.__name__ == "Indirection"

    def test_read_multiple_indirection(self, command_metamodel):
        """R @A,@B - multiple indirection targets."""
        model = command_metamodel.model_from_str("R @A,@B", "ReadCommand")
        assert len(model.args) == 2
        assert model.args[0].arg.target.__class__.__name__ == "Indirection"
        assert model.args[1].arg.target.__class__.__name__ == "Indirection"

    # --- HANG indirection (via Expr wrapper) ---
    def test_hang_indirection(self, command_metamodel):
        """H @A - indirection as duration (wrapped in Expr)."""
        model = command_metamodel.model_from_str("H @A", "HangCommand")
        # HangCommand args are Exprs which wraps the operand
        assert len(model.args) == 1
        assert model.args[0].__class__.__name__ == "Expr"
        assert model.args[0].left.operand.__class__.__name__ == "Indirection"

    # --- FOR indirection ---
    def test_for_indirection_var(self, command_metamodel):
        """F @A=1:1:10 - indirection as loop variable."""
        model = command_metamodel.model_from_str("F @A=1:1:10", "ForCommand")
        assert model.indirect is not None
        assert model.var is None
        assert model.indirect.__class__.__name__ == "Indirection"

    def test_for_double_indirection_var(self, command_metamodel):
        """F @@A=1:1:10 - double indirection as loop variable."""
        model = command_metamodel.model_from_str("F @@A=1:1:10", "ForCommand")
        assert model.indirect is not None
        # textX uses 'expr' attribute for nested
        assert model.indirect.expr.__class__.__name__ == "Indirection"

    def test_for_indirection_params(self, command_metamodel):
        """F I=@A:@B:@C - indirection in parameters."""
        model = command_metamodel.model_from_str("F I=@A:@B:@C", "ForCommand")
        assert model.var is not None
        assert len(model.params) == 1
        # Parameters are Expr wrappers - need to unwrap
        param = model.params[0]
        assert param.start.left.operand.__class__.__name__ == "Indirection"
        assert param.step.left.operand.__class__.__name__ == "Indirection"
        assert param.end.left.operand.__class__.__name__ == "Indirection"

    # --- DO indirection (uses IndirectChain) ---
    def test_do_indirection(self, command_metamodel):
        """D @A - simple DO indirection."""
        model = command_metamodel.model_from_str("D @A", "DoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None

    def test_do_double_indirection(self, command_metamodel):
        """D @@A - nested DO indirection via IndirectChain."""
        model = command_metamodel.model_from_str("D @@A", "DoCommand")
        target = model.targets[0]
        # DoIndirect has labelIndirect which is IndirectChain
        assert target.indirect.labelIndirect.nested is not None

    def test_do_name_indirection(self, command_metamodel):
        """D @X@(1) - name indirection: evaluate X to get label name, append subscript 1."""
        model = command_metamodel.model_from_str("D @X@(1)", "DoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None
        # IndirectChain should have name_subscripts
        label_indirect = target.indirect.labelIndirect
        assert label_indirect is not None
        assert hasattr(label_indirect, "name_subscripts")
        assert len(label_indirect.name_subscripts) == 1

    def test_do_chained_name_indirection(self, command_metamodel):
        """D @X@(A)@(B) - chained name indirection: append subscripts A then B."""
        model = command_metamodel.model_from_str("D @X@(A)@(B)", "DoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        label_indirect = target.indirect.labelIndirect
        assert label_indirect is not None
        assert len(label_indirect.name_subscripts) == 2

    # --- GOTO indirection (uses IndirectChain) ---
    def test_goto_indirection(self, command_metamodel):
        """G @A - simple GOTO indirection."""
        model = command_metamodel.model_from_str("G @A", "GotoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None

    def test_goto_double_indirection(self, command_metamodel):
        """G @@A - nested GOTO indirection via IndirectChain."""
        model = command_metamodel.model_from_str("G @@A", "GotoCommand")
        target = model.targets[0]
        # GotoIndirect has labelIndirect which is IndirectChain
        assert target.indirect.labelIndirect.nested is not None

    def test_goto_name_indirection(self, command_metamodel):
        """G @X@(A) - name indirection: evaluate X to get label name, append subscript A."""
        model = command_metamodel.model_from_str("G @X@(A)", "GotoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None
        # IndirectChain should have name_subscripts
        label_indirect = target.indirect.labelIndirect
        assert label_indirect is not None
        assert hasattr(label_indirect, "name_subscripts")
        assert len(label_indirect.name_subscripts) == 1

    def test_goto_chained_name_indirection(self, command_metamodel):
        """G @X@(1)@(2) - chained name indirection: append subscripts 1 then 2."""
        model = command_metamodel.model_from_str("G @X@(1)@(2)", "GotoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        label_indirect = target.indirect.labelIndirect
        assert label_indirect is not None
        assert len(label_indirect.name_subscripts) == 2

    # --- Triple indirection tests (Phase 102 Part E) ---
    def test_do_triple_indirection(self, command_metamodel):
        """D @@@A - triple DO indirection via nested IndirectChain."""
        model = command_metamodel.model_from_str("D @@@A", "DoCommand")
        target = model.targets[0]
        # IndirectChain nesting: outer.nested.nested
        outer = target.indirect.labelIndirect
        assert outer.nested is not None  # second @
        assert outer.nested.nested is not None  # third @

    def test_goto_triple_indirection(self, command_metamodel):
        """G @@@X - triple GOTO indirection."""
        model = command_metamodel.model_from_str("G @@@X", "GotoCommand")
        target = model.targets[0]
        outer = target.indirect.labelIndirect
        assert outer.nested is not None
        assert outer.nested.nested is not None

    def test_kill_triple_indirection(self, command_metamodel):
        """K @@@X - triple indirection in KILL."""
        model = command_metamodel.model_from_str("K @@@X", "KillCommand")
        target = model.args[0].target
        assert target.__class__.__name__ == "Indirection"
        assert target.expr.__class__.__name__ == "Indirection"
        assert target.expr.expr.__class__.__name__ == "Indirection"

    def test_set_triple_indirection_value(self, command_metamodel):
        """S X=@@@Y - triple indirection in SET value."""
        model = command_metamodel.model_from_str("S X=@@@Y", "SetCommand")
        value = model.assignments[0].value
        # Value is Expr wrapper containing nested indirections
        ind = value.left.operand
        assert ind.__class__.__name__ == "Indirection"
        assert ind.expr.__class__.__name__ == "Indirection"
        assert ind.expr.expr.__class__.__name__ == "Indirection"

    def test_subscript_indirection(self, command_metamodel):
        """Subscript indirection A(@B) parses correctly (§7.3).

        When @ appears in subscript position, the expression is evaluated
        and used as the subscript value.
        """
        model = command_metamodel.model_from_str("S A(@B)=1", "SetCommand")
        assert model is not None
        # Assignment uses 'targets' attribute (single target in this case)
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "LocalVariable"
        assert target.name == "A"
        # Subscript is an Indirection
        assert len(target.subscripts) == 1
        assert target.subscripts[0].__class__.__name__ == "Indirection"

    def test_pattern_indirection(self, command_metamodel):
        """Pattern indirection X?@PAT parses correctly (§7.3).

        The pattern for a match operation can be indirect.
        """
        model = command_metamodel.model_from_str("S X=Y?@PAT", "SetCommand")
        assert model is not None
        # The value is an Expr with pattern match
        value = model.assignments[0].value
        assert value is not None
        # Verify the pattern match has an indirect pattern
        assert hasattr(value, "tail") and len(value.tail) == 1
        tail = value.tail[0]
        assert tail.__class__.__name__ == "PatternMatchTail"
        # indirect_expr should be set (not pattern)
        assert tail.indirect_expr is not None


@pytest.fixture(scope="module")
def expr_metamodel():
    """Create expression metamodel for expression-level indirection parsing."""
    grammar_path = (
        Path(__file__).parent.parent.parent.parent.parent
        / "src"
        / "m2py"
        / "grammar"
        / "expressions.tx"
    )
    return metamodel_from_file(
        str(grammar_path), classes=get_expression_classes(), skipws=True
    )


@pytest.mark.parser
class TestExpressionIndirection:
    """Expression-level indirection tests (§7.3).


    Tests multi-level indirection parsing (@@, @@@) at the expression level.
    """

    def test_simple_indirection(self, expr_metamodel):
        """Parse simple @variable indirection."""
        model = expr_metamodel.model_from_str("@X", "Expr")
        assert model is not None

    def test_subscript_indirection(self, expr_metamodel):
        """Parse @variable(subscripts) indirection."""
        model = expr_metamodel.model_from_str("@X(1,2)", "Expr")
        assert model is not None

    def test_double_indirection(self, expr_metamodel):
        """Parse @@X double indirection (Phase 102 Part E)."""
        model = expr_metamodel.model_from_str("@@X", "Expr")
        assert model is not None
        # Outer indirection
        outer = model.left.operand
        assert outer.__class__.__name__ == "Indirection"
        # Inner indirection (expr contains another Indirection)
        inner = outer.expr
        assert inner.__class__.__name__ == "Indirection"
        # Innermost is the variable
        assert inner.expr.name == "X"

    def test_triple_indirection(self, expr_metamodel):
        """Parse @@@X triple indirection (Phase 102 Part E)."""
        model = expr_metamodel.model_from_str("@@@X", "Expr")
        assert model is not None
        outer = model.left.operand
        assert outer.__class__.__name__ == "Indirection"
        middle = outer.expr
        assert middle.__class__.__name__ == "Indirection"
        inner = middle.expr
        assert inner.__class__.__name__ == "Indirection"
        assert inner.expr.name == "X"

    def test_double_indirection_with_string(self, expr_metamodel):
        """Parse @@"literal" double indirection with string literal."""
        model = expr_metamodel.model_from_str('@@"^V1A"', "Expr")
        assert model is not None
        outer = model.left.operand
        inner = outer.expr
        assert inner.__class__.__name__ == "Indirection"
        # Innermost is a string literal
        assert inner.expr.__class__.__name__ == "StringLiteral"

    def test_double_indirection_with_subscripts(self, expr_metamodel):
        """Parse @@X(1,2) double indirection - subscripts apply to innermost variable.

        In MUMPS, @@X(1,2) means: evaluate X(1,2), then indirect twice.
        The subscripts attach to the innermost variable reference.
        """
        model = expr_metamodel.model_from_str("@@X(1,2)", "Expr")
        assert model is not None
        outer = model.left.operand
        inner = outer.expr
        # Subscripts are on the innermost variable X
        innermost = inner.expr
        assert innermost.__class__.__name__ == "LocalVariable"
        assert len(innermost.subscripts) == 2

    def test_triple_indirection_with_subscripts(self, expr_metamodel):
        """Parse @@@B("AB",2.4) triple indirection - subscripts apply to innermost variable.

        In MUMPS, @@@B("AB",2.4) means: evaluate B("AB",2.4), then indirect three times.
        """
        model = expr_metamodel.model_from_str('@@@B("AB",2.4)', "Expr")
        assert model is not None
        outer = model.left.operand
        middle = outer.expr
        inner = middle.expr
        innermost = inner.expr
        assert innermost.__class__.__name__ == "LocalVariable"
        assert innermost.name == "B"
        assert len(innermost.subscripts) == 2

    def test_name_indirection_with_subscripts(self, expr_metamodel):
        """Parse @B@(1) name indirection with subscripts (from task examples)."""
        model = expr_metamodel.model_from_str("@B@(1)", "Expr")
        assert model is not None
        ind = model.left.operand
        assert ind.__class__.__name__ == "Indirection"
        # name_subscripts captures the @(1) part
        assert ind.name_subscripts is not None
        assert len(ind.name_subscripts) == 1


@pytest.mark.parser
class TestIndirectionGrammar:
    """Test indirection parsing via MUMPSParser.

    Note: Simple indirection parsing is tested in TestIndirectionParsing and
    TestExpressionIndirection using direct grammar access. This class focuses
    on full parser pipeline integration tests for complex scenarios not
    covered elsewhere.
    """

    def test_name_indirection_chained(self):
        """@X@(1)@(2) chained name indirection should parse.

        Chained subscript indirection is more complex than single subscript
        and tests the parser's handling of multiple @() chains.
        """
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS @X@(1)@(2)=3\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        target = label.body.statements[0].assignments[0].target
        assert target.name_indirection_subscripts is not None
        assert len(target.name_indirection_subscripts) == 2

    def test_name_indirection_with_double_indirection(self):
        """@@X@(1) double indirection with name subscripts should parse.

        This complex pattern combines double indirection with subscripts.
        """
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS @@X@(1)=2\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_name_indirection_global(self):
        """@^VV@(1) global variable name indirection should parse.

        Tests indirection on global variables, which have a different
        grammar rule path.
        """
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS @^VV@(1,2)=3\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_name_indirection_complex_mugj_pattern(self):
        """Complex MUGJ pattern @@X@(1,2)@(5,6) should parse.

        This pattern from MUGJ tests combines all indirection features:
        double indirection, subscripted variable, chained subscripts.
        """
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tS @@X@(1,2)@(5,6)=1\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestDoIndirectionGrammar:
    """Test DO with various indirection forms via MUMPSParser."""

    def test_do_indirect_variable(self):
        """D @VAR should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tD @ROUTINE\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MDoStatement"

    def test_do_indirect_expression(self):
        """D @(expr) should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = "LABEL\tD @(X)\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MDoStatement"

    def test_do_indirect_complex_expression(self):
        """D @($P($T(X),";",2)) should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine

        parser = MUMPSParser()
        source = 'LABEL\tD @($P($T(X),";",2))\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MDoStatement"


@pytest.mark.parser
class TestIndirectionDirectGrammar:
    """Direct grammar-level indirection tests using expression metamodel."""

    @pytest.fixture(scope="class")
    def expression_metamodel(self):
        """Load the expression grammar metamodel."""
        from pathlib import Path
        from textx import metamodel_from_file

        grammar_dir = (
            Path(__file__).parent.parent.parent.parent.parent
            / "src"
            / "m2py"
            / "grammar"
        )
        return metamodel_from_file(str(grammar_dir / "expressions.tx"), skipws=False)

    def test_simple_indirection(self, expression_metamodel):
        """@X - simple variable indirection."""
        model = expression_metamodel.model_from_str("@X", "Expr")
        assert model is not None

    def test_subscripted_indirection(self, expression_metamodel):
        """@X(1,2) - indirection with subscripts."""
        model = expression_metamodel.model_from_str("@X(1,2)", "Expr")
        assert model is not None

    def test_global_indirection(self, expression_metamodel):
        """@^X - indirection of global."""
        model = expression_metamodel.model_from_str("@^X", "Expr")
        assert model is not None

    def test_string_indirection(self, expression_metamodel):
        """@"VAR" - indirection of string."""
        model = expression_metamodel.model_from_str('@"VAR"', "Expr")
        assert model is not None

    def test_paren_indirection(self, expression_metamodel):
        """@(expr) - indirection of parenthesized expression."""
        model = expression_metamodel.model_from_str("@(A_B)", "Expr")
        assert model is not None
