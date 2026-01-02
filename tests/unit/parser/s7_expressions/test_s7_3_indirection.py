"""Tests for Indirection parsing (§7.3).

Tests verify the textX grammar correctly captures indirection syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.3
Migrated from:
- tests/unit/test_command_grammar.py::TestIndirection
- tests/unit/test_expression_grammar.py::TestIndirection
- tests/unit/test_grammar.py::TestIndirectionGrammar
- tests/unit/test_grammar.py::TestDoIndirectionGrammar
- tests/unit/test_special_constructs.py::TestIndirection
"""

import pytest

from m2py.asg import MRoutine
from m2py.parser import MUMPSParser


@pytest.mark.parser
class TestIndirection:
    """Tests for indirection (@) parsing across all commands (§7.3).

    All commands use the same Indirection rule from expressions.tx,
    which handles:
    - Single indirection: @VAR
    - Nested indirection: @@VAR (parsed as @(@VAR))
    - Expression indirection: @(expr)
    - Subscripted indirection: @VAR(sub1,sub2)

    DO, GOTO, and LOCK use IndirectChain for additional features
    like @label^routine patterns.

    Migrated from test_command_grammar.py::TestIndirection.
    """

    # --- KILL indirection ---
    def test_kill_indirection(self, command_metamodel):
        """K @A - kill indirection (§7.3)."""
        model = command_metamodel.model_from_str("K @A", "KillCommand")
        assert len(model.args) == 1
        arg = model.args[0]
        assert arg.target is not None
        # target is an Indirection
        assert arg.target.__class__.__name__ == "Indirection"

    def test_kill_double_indirection(self, command_metamodel):
        """K @@A - nested indirection (§7.3)."""
        model = command_metamodel.model_from_str("K @@A", "KillCommand")
        assert len(model.args) == 1
        target = model.args[0].target
        assert target.__class__.__name__ == "Indirection"
        # Nested: expr is also Indirection (textX uses 'expr', not 'expression')
        assert target.expr.__class__.__name__ == "Indirection"

    def test_kill_multiple_indirection(self, command_metamodel):
        """K @A,@B - multiple indirection targets (§7.3)."""
        model = command_metamodel.model_from_str("K @A,@B", "KillCommand")
        assert len(model.args) == 2
        assert model.args[0].target.__class__.__name__ == "Indirection"
        assert model.args[1].target.__class__.__name__ == "Indirection"

    # --- SET indirection ---
    def test_set_target_indirection(self, command_metamodel):
        """S @A=1 - indirection as target (§7.3)."""
        model = command_metamodel.model_from_str("S @A=1", "SetCommand")
        assert len(model.assignments) == 1
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "Indirection"

    def test_set_value_indirection(self, command_metamodel):
        """S X=@A - indirection as value (§7.3)."""
        model = command_metamodel.model_from_str("S X=@A", "SetCommand")
        assert len(model.assignments) == 1
        # Value is an expression containing Indirection
        assert model.assignments[0].value is not None

    def test_set_both_indirection(self, command_metamodel):
        """S @B=@A - indirection on both sides (§7.3)."""
        model = command_metamodel.model_from_str("S @B=@A", "SetCommand")
        assert len(model.assignments) == 1
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "Indirection"

    def test_set_double_indirection(self, command_metamodel):
        """S @@A=1 - nested indirection as target (§7.3)."""
        model = command_metamodel.model_from_str("S @@A=1", "SetCommand")
        target = model.assignments[0].targets
        assert target.__class__.__name__ == "Indirection"
        # textX uses 'expr' attribute
        assert target.expr.__class__.__name__ == "Indirection"

    def test_set_argument_indirection(self, command_metamodel):
        """S @A - argument-level indirection (var contains 'X=1') (§7.3)."""
        model = command_metamodel.model_from_str("S @A", "SetCommand")
        assert len(model.assignments) == 1
        # This uses SetIndirection
        arg = model.assignments[0]
        assert hasattr(arg, "indirect") and arg.indirect is not None

    # --- WRITE indirection (via Expr wrapper) ---
    def test_write_indirection(self, command_metamodel):
        """W @A - indirection as value (wrapped in Expr) (§7.3)."""
        model = command_metamodel.model_from_str("W @A", "WriteCommand")
        assert len(model.args) == 1
        arg = model.args[0].arg
        # WRITE uses Expr which wraps Indirection
        # Need to unwrap: arg.left.operand is the Indirection
        assert arg.__class__.__name__ == "Expr"
        assert arg.left.operand.__class__.__name__ == "Indirection"

    def test_write_double_indirection(self, command_metamodel):
        """W @@C - nested indirection (§7.3)."""
        model = command_metamodel.model_from_str("W @@C", "WriteCommand")
        arg = model.args[0].arg
        # Unwrap Expr to get Indirection
        inner = arg.left.operand
        assert inner.__class__.__name__ == "Indirection"
        assert inner.expr.__class__.__name__ == "Indirection"

    # --- READ indirection ---
    def test_read_indirection(self, command_metamodel):
        """R @A - indirection as target (§7.3)."""
        model = command_metamodel.model_from_str("R @A", "ReadCommand")
        assert len(model.args) == 1
        target = model.args[0].arg.target
        assert target.__class__.__name__ == "Indirection"

    def test_read_multiple_indirection(self, command_metamodel):
        """R @A,@B - multiple indirection targets (§7.3)."""
        model = command_metamodel.model_from_str("R @A,@B", "ReadCommand")
        assert len(model.args) == 2
        assert model.args[0].arg.target.__class__.__name__ == "Indirection"
        assert model.args[1].arg.target.__class__.__name__ == "Indirection"

    # --- HANG indirection (via Expr wrapper) ---
    def test_hang_indirection(self, command_metamodel):
        """H @A - indirection as duration (wrapped in Expr) (§7.3)."""
        model = command_metamodel.model_from_str("H @A", "HangCommand")
        # HangCommand args are Exprs which wraps the operand
        assert len(model.args) == 1
        assert model.args[0].__class__.__name__ == "Expr"
        assert model.args[0].left.operand.__class__.__name__ == "Indirection"

    # --- FOR indirection ---
    def test_for_indirection_var(self, command_metamodel):
        """F @A=1:1:10 - indirection as loop variable (§7.3)."""
        model = command_metamodel.model_from_str("F @A=1:1:10", "ForCommand")
        assert model.indirect is not None
        assert model.var is None
        assert model.indirect.__class__.__name__ == "Indirection"

    def test_for_double_indirection_var(self, command_metamodel):
        """F @@A=1:1:10 - double indirection as loop variable (§7.3)."""
        model = command_metamodel.model_from_str("F @@A=1:1:10", "ForCommand")
        assert model.indirect is not None
        # textX uses 'expr' attribute for nested
        assert model.indirect.expr.__class__.__name__ == "Indirection"

    def test_for_indirection_params(self, command_metamodel):
        """F I=@A:@B:@C - indirection in parameters (§7.3)."""
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
        """D @A - simple DO indirection (§7.3)."""
        model = command_metamodel.model_from_str("D @A", "DoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None

    def test_do_double_indirection(self, command_metamodel):
        """D @@A - nested DO indirection via IndirectChain (§7.3)."""
        model = command_metamodel.model_from_str("D @@A", "DoCommand")
        target = model.targets[0]
        # DoIndirect has labelIndirect which is IndirectChain
        assert target.indirect.labelIndirect.nested is not None

    def test_do_name_indirection(self, command_metamodel):
        """D @X@(1) - name indirection: evaluate X to get label name, append subscript 1 (§7.3)."""
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
        """D @X@(A)@(B) - chained name indirection: append subscripts A then B (§7.3)."""
        model = command_metamodel.model_from_str("D @X@(A)@(B)", "DoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        label_indirect = target.indirect.labelIndirect
        assert label_indirect is not None
        assert len(label_indirect.name_subscripts) == 2

    # --- GOTO indirection (uses IndirectChain) ---
    def test_goto_indirection(self, command_metamodel):
        """G @A - simple GOTO indirection (§7.3)."""
        model = command_metamodel.model_from_str("G @A", "GotoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        assert target.indirect is not None

    def test_goto_double_indirection(self, command_metamodel):
        """G @@A - nested GOTO indirection via IndirectChain (§7.3)."""
        model = command_metamodel.model_from_str("G @@A", "GotoCommand")
        target = model.targets[0]
        # GotoIndirect has labelIndirect which is IndirectChain
        assert target.indirect.labelIndirect.nested is not None

    def test_goto_name_indirection(self, command_metamodel):
        """G @X@(A) - name indirection: evaluate X to get label name, append subscript A (§7.3)."""
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
        """G @X@(1)@(2) - chained name indirection: append subscripts 1 then 2 (§7.3)."""
        model = command_metamodel.model_from_str("G @X@(1)@(2)", "GotoCommand")
        assert len(model.targets) == 1
        target = model.targets[0]
        label_indirect = target.indirect.labelIndirect
        assert label_indirect is not None
        assert len(label_indirect.name_subscripts) == 2

    # --- Triple indirection tests ---
    def test_do_triple_indirection(self, command_metamodel):
        """D @@@A - triple DO indirection via nested IndirectChain (§7.3)."""
        model = command_metamodel.model_from_str("D @@@A", "DoCommand")
        target = model.targets[0]
        # IndirectChain nesting: outer.nested.nested
        outer = target.indirect.labelIndirect
        assert outer.nested is not None  # second @
        assert outer.nested.nested is not None  # third @

    def test_goto_triple_indirection(self, command_metamodel):
        """G @@@X - triple GOTO indirection (§7.3)."""
        model = command_metamodel.model_from_str("G @@@X", "GotoCommand")
        target = model.targets[0]
        outer = target.indirect.labelIndirect
        assert outer.nested is not None
        assert outer.nested.nested is not None

    def test_kill_triple_indirection(self, command_metamodel):
        """K @@@X - triple indirection in KILL (§7.3)."""
        model = command_metamodel.model_from_str("K @@@X", "KillCommand")
        target = model.args[0].target
        assert target.__class__.__name__ == "Indirection"
        assert target.expr.__class__.__name__ == "Indirection"
        assert target.expr.expr.__class__.__name__ == "Indirection"

    def test_set_triple_indirection_value(self, command_metamodel):
        """S X=@@@Y - triple indirection in SET value (§7.3)."""
        model = command_metamodel.model_from_str("S X=@@@Y", "SetCommand")
        value = model.assignments[0].value
        # Value is Expr wrapper containing nested indirections
        ind = value.left.operand
        assert ind.__class__.__name__ == "Indirection"
        assert ind.expr.__class__.__name__ == "Indirection"
        assert ind.expr.expr.__class__.__name__ == "Indirection"


@pytest.mark.parser
class TestByRefIndirection:
    """Tests for pass-by-reference with indirection (§7.3).

    Migrated from test_command_grammar.py::TestByRefIndirection.
    """

    def test_do_byref_indirection(self, command_metamodel):
        """DO routine(.@X) - pass-by-ref with indirection (§7.3)."""
        model = command_metamodel.model_from_str("DO routine(.@X)", "DoCommand")
        assert model is not None
        # Args should parse correctly
        target = model.targets[0]
        assert target.args is not None

    def test_do_mixed_byref_args(self, command_metamodel):
        """DO routine(.@IX,.Y,Z) - mixed args (§7.3)."""
        model = command_metamodel.model_from_str("DO routine(.@IX,.Y,Z)", "DoCommand")
        assert model is not None


@pytest.mark.parser
class TestExpressionIndirection:
    """Tests for indirection parsing in expressions (§7.3).

    These tests verify indirection as expression operands, including
    multi-level indirection (@@, @@@) which is parsed recursively.

    Migrated from test_expression_grammar.py::TestIndirection.
    """

    def test_simple_indirection(self, expr_metamodel):
        """Parse simple @variable indirection (§7.3)."""
        model = expr_metamodel.model_from_str("@X", "Expr")
        assert model is not None

    def test_subscript_indirection(self, expr_metamodel):
        """Parse @variable(subscripts) indirection (§7.3)."""
        model = expr_metamodel.model_from_str("@X(1,2)", "Expr")
        assert model is not None

    def test_double_indirection(self, expr_metamodel):
        """Parse @@X double indirection (§7.3).

        @@X is parsed as @(@X) where the outer @ has an Indirection as its expr.
        """
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
        """Parse @@@X triple indirection (§7.3)."""
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
        """Parse @@"literal" double indirection with string literal (§7.3)."""
        model = expr_metamodel.model_from_str('@@"^V1A"', "Expr")
        assert model is not None
        outer = model.left.operand
        inner = outer.expr
        assert inner.__class__.__name__ == "Indirection"
        # Innermost is a string literal
        assert inner.expr.__class__.__name__ == "StringLiteral"

    def test_double_indirection_with_subscripts(self, expr_metamodel):
        """Parse @@X(1,2) double indirection - subscripts apply to innermost variable (§7.3).

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
        """Parse @@@B("AB",2.4) triple indirection - subscripts apply to innermost variable (§7.3).

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
        """Parse @B@(1) name indirection with subscripts (§7.3)."""
        model = expr_metamodel.model_from_str("@B@(1)", "Expr")
        assert model is not None
        ind = model.left.operand
        assert ind.__class__.__name__ == "Indirection"
        # name_subscripts captures the @(1) part
        assert ind.name_subscripts is not None
        assert len(ind.name_subscripts) == 1


@pytest.mark.parser
class TestIndirectionGrammar:
    """Test indirection parsing full-routine acceptance (§7.3).

    Migrated from: tests/unit/test_grammar.py::TestIndirectionGrammar
    """

    def test_simple_indirection(self):
        """@variable indirection should parse (§7.3)."""
        parser = MUMPSParser()
        source = "LABEL\tS @VAR=1\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_subscripted_indirection(self):
        """@variable(subscripts) should parse (§7.3)."""
        parser = MUMPSParser()
        source = "LABEL\tS @VAR@(1,2)=3\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_name_indirection(self):
        """@\"varname\" string indirection should parse (§7.3)."""
        parser = MUMPSParser()
        source = 'LABEL\tS @"X"=1\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_do_indirection(self):
        """D @ROUTINE indirection should parse (§7.3)."""
        parser = MUMPSParser()
        source = "LABEL\tD @ROUTINE\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_goto_indirection(self):
        """G @LABEL indirection should parse (§7.3)."""
        parser = MUMPSParser()
        source = "LABEL\tG @TARGET\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_name_indirection_single_subscript(self):
        """@X@(1) name indirection with single subscript should parse (§7.3)."""
        parser = MUMPSParser()
        source = "LABEL\tS @X@(1)=2\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert stmt.__class__.__name__ == "MSetStatement"
        # Verify target is an indirection with name_indirection_subscripts
        target = stmt.assignments[0].target
        # Could be 'Indirection' (textX class) or 'MIndirection' (ASG class)
        assert "Indirection" in target.__class__.__name__
        assert target.name_indirection_subscripts is not None
        assert len(target.name_indirection_subscripts) == 1

    def test_name_indirection_multiple_subscripts(self):
        """@X@(1,2,3) name indirection with multiple subscripts should parse (§7.3)."""
        parser = MUMPSParser()
        source = "LABEL\tS @X@(1,2,3)=4\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        target = label.body.statements[0].assignments[0].target
        assert target.name_indirection_subscripts is not None
        assert len(target.name_indirection_subscripts) == 1
        assert len(target.name_indirection_subscripts[0]) == 3

    def test_name_indirection_chained(self):
        """@X@(1)@(2) chained name indirection should parse (§7.3)."""
        parser = MUMPSParser()
        source = "LABEL\tS @X@(1)@(2)=3\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        target = label.body.statements[0].assignments[0].target
        assert target.name_indirection_subscripts is not None
        assert len(target.name_indirection_subscripts) == 2

    def test_name_indirection_with_double_indirection(self):
        """@@X@(1) double indirection with name subscripts should parse (§7.3)."""
        parser = MUMPSParser()
        source = "LABEL\tS @@X@(1)=2\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_name_indirection_global(self):
        """@^VV@(1) global variable name indirection should parse (§7.3)."""
        parser = MUMPSParser()
        source = "LABEL\tS @^VV@(1,2)=3\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)

    def test_name_indirection_complex_mugj_pattern(self):
        """Complex MUGJ pattern @@X@(1,2)@(5,6) should parse (§7.3)."""
        parser = MUMPSParser()
        source = "LABEL\tS @@X@(1,2)@(5,6)=1\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)


@pytest.mark.parser
class TestDoIndirectionGrammar:
    """Test DO with various indirection forms (§7.3).

    Migrated from: tests/unit/test_grammar.py::TestDoIndirectionGrammar
    """

    def test_do_indirect_variable(self):
        """D @VAR should parse (§7.3)."""
        parser = MUMPSParser()
        source = "LABEL\tD @ROUTINE\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MDoStatement"

    def test_do_indirect_expression(self):
        """D @(expr) should parse (§7.3)."""
        parser = MUMPSParser()
        source = "LABEL\tD @(X)\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MDoStatement"

    def test_do_indirect_complex_expression(self):
        """D @($P($T(X),\";\",2)) should parse (§7.3)."""
        parser = MUMPSParser()
        source = 'LABEL\tD @($P($T(X),";",2))\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        assert label.body.statements[0].__class__.__name__ == "MDoStatement"


@pytest.mark.parser
class TestIndirectionExpressionParsing:
    """Tests for indirection (@) constructs in expressions (§7.3).

    Migrated from: tests/unit/test_special_constructs.py::TestIndirection
    """

    def test_simple_indirection(self, parse_expression):
        """@X - simple variable indirection (§7.3).

        Migrated from: tests/unit/test_special_constructs.py::TestIndirection
        """
        model = parse_expression("@X")
        assert model is not None

    def test_subscripted_indirection(self, parse_expression):
        """@X(1,2) - indirection with subscripts (§7.3).

        Migrated from: tests/unit/test_special_constructs.py::TestIndirection
        """
        model = parse_expression("@X(1,2)")
        assert model is not None

    def test_global_indirection(self, parse_expression):
        """@^X - indirection of global (§7.3).

        Migrated from: tests/unit/test_special_constructs.py::TestIndirection
        """
        model = parse_expression("@^X")
        assert model is not None

    def test_string_indirection(self, parse_expression):
        """@\"VAR\" - indirection of string (§7.3).

        Migrated from: tests/unit/test_special_constructs.py::TestIndirection
        """
        model = parse_expression('@"VAR"')
        assert model is not None

    def test_paren_indirection(self, parse_expression):
        """@(expr) - indirection of parenthesized expression (§7.3).

        Migrated from: tests/unit/test_special_constructs.py::TestIndirection
        """
        model = parse_expression("@(A_B)")
        assert model is not None
