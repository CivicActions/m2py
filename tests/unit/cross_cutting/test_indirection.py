"""Cross-cutting tests for indirection (Section 6.3.1, 7.3).

Indirection is a language feature that spans multiple commands and expressions.
This file tests the cross-cutting behavior of all indirection types.

From MUMPS 1995 ANSI Standard and spec reference 1995__a901027.md:

1. Name indirection: @VAR evaluates to a variable name
   SET @X=1 where X="Y" sets Y=1

2. Argument indirection: @VAR evaluates to a command argument
   WRITE @VAR where VAR contains format codes

3. Pattern indirection: X?@VAR where VAR contains a pattern
   IF X?@PAT where PAT="3N" checks if X matches 3 digits

4. Subscript indirection (1984): @VAR@(subs) for subscripted indirection
   @ARRAY@(1,2,3) where ARRAY="PRICES" refers to PRICES(1,2,3)

5. Generic indirection (future): Catch-all recovery for @ syntax

Reference: MUMPS 1995 ANSI Standard
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.parser.textx_classes import Indirection, LocalVariable
from m2py.asg.enums import IndirectionType


# =============================================================================
# Name Indirection Tests (Parser Level) - D1 Batch
# =============================================================================


@pytest.mark.parser
class TestNameIndirectionParser:
    """Parser tests for name indirection at expression level.

    Name indirection uses @ to dereference a variable that contains
    a variable name. E.g., if X="Y" then @X refers to variable Y.

    From MUMPS 1995 spec §7.3.1 (1995__a901027.md):
        "Set X='ABC'
         IF 123+@X=456"
    The @X evaluates to the value of variable ABC.

    Reference: §7.3.1
    """

    def test_name_indirection_in_set_target(self):
        """SET @VAR=1 parses name indirection as target (§7.3.1).

        Per 1995__a901027.md: "Set @X1='HELLO' will be executed as: Set Y='HELLO'"
        The target of SET can be an indirection that resolves to a variable name.
        """
        parser = MUMPSParser()
        result = parser.parse("TEST\n S @X=1")
        stmt = result.labels[0].body.statements[0]
        target = stmt.assignments[0].target

        # Target should be an Indirection node
        assert isinstance(target, Indirection)
        # The expression is the variable X
        assert isinstance(target.expression, LocalVariable)
        assert target.expression.name == "X"
        # Default type is NAME indirection
        assert target.indirection_type == IndirectionType.NAME

    def test_name_indirection_in_expression(self):
        """WRITE @VAR parses name indirection as expression (§7.3.1).

        Per 1995__a901027.md, name indirection is used in expressions:
        "Set X='ABC'
         IF 123+@X=456"
        """
        parser = MUMPSParser()
        result = parser.parse("TEST\n W @X")
        stmt = result.labels[0].body.statements[0]

        # WRITE arguments should contain an Indirection
        assert len(stmt.arguments) >= 1
        arg = stmt.arguments[0]
        assert isinstance(arg, Indirection)
        assert isinstance(arg.expression, LocalVariable)
        assert arg.expression.name == "X"

    def test_subscripted_name_indirection(self):
        """@VAR@(1,2) parses subscript indirection with subscripts (§7.3.1).

        Per 1984 ANSI addition (1995__a901027.md):
        "Set ARRAY='PRICES'
         Set PRICE=(100+SALESTAX/100)*@ARRAY@(1,2,3)"
        The @ARRAY@(1,2,3) resolves to PRICES(1,2,3).
        """
        parser = MUMPSParser()
        result = parser.parse("TEST\n S Y=@X@(1,2)")
        stmt = result.labels[0].body.statements[0]
        value = stmt.assignments[0].value

        # Should be an Indirection with name_indirection_subscripts
        assert isinstance(value, Indirection)
        assert isinstance(value.expression, LocalVariable)
        assert value.expression.name == "X"
        # name_indirection_subscripts holds the (1,2) subscripts
        assert value.name_indirection_subscripts is not None
        assert len(value.name_indirection_subscripts) == 1  # One subscript list
        assert len(value.name_indirection_subscripts[0]) == 2  # Two subscripts

    def test_chained_name_indirection(self):
        """@@VAR parses double (nested) indirection (§7.3.1).

        Per YDBTest/indirection/inref/indlcl.m:
        "set @@variable='PASSED'"
        Nested indirection is dereferenced twice at runtime.
        """
        parser = MUMPSParser()
        result = parser.parse("TEST\n S Y=@@X")
        stmt = result.labels[0].body.statements[0]
        value = stmt.assignments[0].value

        # Outer indirection
        assert isinstance(value, Indirection)
        assert value.indirection_type == IndirectionType.NAME
        # Inner indirection
        assert isinstance(value.expression, Indirection)
        assert value.expression.indirection_type == IndirectionType.NAME
        # Innermost is the variable X
        assert isinstance(value.expression.expression, LocalVariable)
        assert value.expression.expression.name == "X"


# =============================================================================
# Argument Indirection Tests (Parser Level) - D2 Batch
# =============================================================================


@pytest.mark.parser
class TestArgumentIndirectionParser:
    """Parser tests for argument indirection in commands.

    Argument indirection uses @VAR where VAR contains a complete
    argument for a command. E.g., DO @VAR where VAR="LABEL^ROUTINE".

    From MUMPS 1995 spec §8.1.3 (1995__a108004.md):
        "Argument indirection may be used recursively.
         A single instance of argument indirection may evaluate to one
         complete argument or to a sublist of complete arguments."

    Reference: §6.3.1, §7.3.2
    """

    def test_argument_indirection_in_do(self):
        """DO @VAR parses argument indirection (§7.3.2).

        Per 1995__a901027.md: "Do @(Z2)(1,2,3) will be executed as: Do TAG^Program(1,2,3)"
        DO with indirection creates MCall with indirection field set.
        """
        parser = MUMPSParser()
        result = parser.parse("TEST\n D @X")
        stmt = result.labels[0].body.statements[0]

        # DO has targets (MCall list)
        assert hasattr(stmt, "targets") and len(stmt.targets) == 1
        call = stmt.targets[0]
        # The call has indirection set
        assert call.indirection is not None
        assert isinstance(call.indirection, LocalVariable)
        assert call.indirection.name == "X"
        assert call.label_is_indirect is True

    def test_argument_indirection_in_goto(self):
        """GOTO @VAR parses argument indirection (§7.3.2).

        GOTO with indirection is similar to DO - the target is resolved at runtime.
        """
        parser = MUMPSParser()
        result = parser.parse("TEST\n G @X")
        stmt = result.labels[0].body.statements[0]

        # GOTO has targets (MCall or similar)
        assert hasattr(stmt, "targets") and len(stmt.targets) >= 1
        target = stmt.targets[0]
        # Should have indirection
        assert target.indirection is not None
        assert isinstance(target.indirection, LocalVariable)
        assert target.indirection.name == "X"

    def test_argument_indirection_in_set(self):
        """SET @VAR=1 or SET X=@VAR parses correctly (§7.3.2).

        Per examples__a108048.md, indirection on the left-hand side is name indirection,
        not argument indirection. SET X=@VAR is name indirection on the value.
        """
        parser = MUMPSParser()

        # SET X=@VAR - indirection on value
        result = parser.parse("TEST\n S X=@VAR")
        stmt = result.labels[0].body.statements[0]
        value = stmt.assignments[0].value

        assert isinstance(value, Indirection)
        assert isinstance(value.expression, LocalVariable)
        assert value.expression.name == "VAR"

    def test_argument_indirection_in_kill(self):
        """KILL @VAR parses argument indirection (§7.3.2).

        KILL with indirection allows the variable name to be determined at runtime.
        """
        parser = MUMPSParser()
        result = parser.parse("TEST\n K @X")
        stmt = result.labels[0].body.statements[0]

        # KILL targets should include an Indirection
        assert hasattr(stmt, "targets") and len(stmt.targets) >= 1
        target = stmt.targets[0]
        assert isinstance(target, Indirection)
        assert isinstance(target.expression, LocalVariable)
        assert target.expression.name == "X"

    def test_argument_indirection_in_write(self):
        """WRITE @VAR parses argument indirection (§7.3.2).

        Per 1995__a901027.md Argument indirection example:
        "Set SPACE='!!!',PAGE='#'
         Write @$Select(ENOUGH:SPACE,1:PAGE)"
        """
        parser = MUMPSParser()
        result = parser.parse("TEST\n W @VAR")
        stmt = result.labels[0].body.statements[0]

        assert len(stmt.arguments) >= 1
        arg = stmt.arguments[0]
        assert isinstance(arg, Indirection)
        assert isinstance(arg.expression, LocalVariable)
        assert arg.expression.name == "VAR"

    def test_argument_indirection_in_read(self):
        """READ @VAR parses argument indirection (§7.3.2).

        READ with indirection allows reading into a variable whose name
        is determined at runtime. READ arguments are wrapped in MReadTarget.
        """
        from m2py.asg.statements import MReadTarget

        parser = MUMPSParser()
        result = parser.parse("TEST\n R @X")
        stmt = result.labels[0].body.statements[0]

        # READ arguments are wrapped in MReadTarget
        assert hasattr(stmt, "arguments") and len(stmt.arguments) >= 1
        arg = stmt.arguments[0]
        assert isinstance(arg, MReadTarget)
        # The variable inside MReadTarget is the indirection
        assert isinstance(arg.variable, Indirection)
        assert isinstance(arg.variable.expression, LocalVariable)
        assert arg.variable.expression.name == "X"


# =============================================================================
# Pattern Indirection Tests (Parser Level) - D3 Batch
# =============================================================================


@pytest.mark.parser
class TestPatternIndirectionParser:
    """Parser tests for pattern indirection in pattern match.

    Pattern indirection uses X?@VAR where VAR contains a pattern.

    From MUMPS 1995 spec (1995__a901027.md):
        "Pattern indirection
         Set CODE='3U'_$Select(SPECIAL:'2N',1:'')_'5L'
         If X?@CODE"

    Reference: §7.2.5.5
    """

    def test_pattern_indirection_basic(self):
        """X?@PAT parses pattern indirection (§7.2.5.5).

        Per 1995__a901027.md:
        ">Set pattern='3N1\"-\"2N1\"-\"4N'
         >Write string?@pattern
         1"
        """
        from m2py.asg.expressions import MPatternMatch

        parser = MUMPSParser()
        result = parser.parse("TEST\n I X?@PAT Q")
        stmt = result.labels[0].body.statements[0]

        # The condition should be a pattern match with indirect pattern
        cond = stmt.condition
        assert isinstance(cond, MPatternMatch)
        # Subject is X
        assert isinstance(cond.subject, LocalVariable)
        assert cond.subject.name == "X"
        # Pattern is indirect
        assert cond.pattern_indirect is not None
        assert isinstance(cond.pattern_indirect, LocalVariable)
        assert cond.pattern_indirect.name == "PAT"
        # Pattern string should be empty when indirect
        assert cond.pattern == ""

    def test_pattern_indirection_with_subscript(self):
        """X?@PAT(1) parses pattern indirection with subscript (§7.2.5.5).

        Pattern indirection can use a subscripted variable to hold the pattern.
        """
        from m2py.asg.expressions import MPatternMatch

        parser = MUMPSParser()
        result = parser.parse("TEST\n I X?@PAT(1) Q")
        stmt = result.labels[0].body.statements[0]

        cond = stmt.condition
        assert isinstance(cond, MPatternMatch)
        assert cond.pattern_indirect is not None
        # The indirect pattern is PAT(1) - a subscripted variable
        assert cond.pattern_indirect.name == "PAT"
        assert len(cond.pattern_indirect.subscripts) == 1

    def test_pattern_indirection_in_if(self):
        """IF X?@PAT parses pattern indirection in condition (§7.2.5.5).

        Pattern indirection appears in IF conditions and other boolean contexts.
        """
        from m2py.asg.expressions import MPatternMatch

        parser = MUMPSParser()
        result = parser.parse("TEST\n I A?@B W 1")
        stmt = result.labels[0].body.statements[0]

        # Should have a condition
        assert stmt.condition is not None
        cond = stmt.condition
        assert isinstance(cond, MPatternMatch)
        assert cond.operator == "?"
        assert cond.pattern_indirect is not None
        assert cond.pattern_indirect.name == "B"


# =============================================================================
# Name Indirection Tests (ASG Level) - D4 Batch
# =============================================================================


@pytest.mark.asg
class TestNameIndirectionASG:
    """ASG tests for name indirection semantic analysis.

    ASG analysis must classify indirection type and track
    the indirected variable reference.

    Per MUMPS 1995 spec §7.3.1, name indirection @VAR dereferences
    the value of VAR as a variable name.

    Reference: §7.3.1
    """

    def test_name_indirection_classified(self):
        """Name indirection is classified as IndirectionType.NAME (§7.3.1).

        The ASG should record the indirection type for proper code generation.
        IndirectionType.NAME means the indirected value is a variable name.
        """
        parser = MUMPSParser()
        result = parser.parse("TEST\n S Y=@X")
        stmt = result.labels[0].body.statements[0]
        value = stmt.assignments[0].value

        assert isinstance(value, Indirection)
        assert value.indirection_type == IndirectionType.NAME

    def test_name_indirection_target_tracked(self):
        """Indirection target variable is tracked in ASG (§7.3.1).

        The expression field of MIndirection should contain the variable
        that holds the name to dereference.
        """
        parser = MUMPSParser()
        result = parser.parse("TEST\n S Y=@VARNAME")
        stmt = result.labels[0].body.statements[0]
        value = stmt.assignments[0].value

        assert isinstance(value, Indirection)
        assert value.expression is not None
        assert isinstance(value.expression, LocalVariable)
        assert value.expression.name == "VARNAME"

    def test_subscripted_indirection_subscripts_resolved(self):
        """Subscripts on indirection (@X@(a,b)) are resolved (§7.3.1).

        Per 1984 addition (1995__a901027.md), subscript indirection
        @VAR@(subs) appends subscripts to the resolved variable name.
        The name_indirection_subscripts field holds these additional subscripts.
        """
        from m2py.parser.textx_classes import NumericLiteral

        parser = MUMPSParser()
        result = parser.parse("TEST\n S Y=@X@(1,2)")
        stmt = result.labels[0].body.statements[0]
        value = stmt.assignments[0].value

        assert isinstance(value, Indirection)
        assert value.name_indirection_subscripts is not None
        # Should have one list of two subscripts
        assert len(value.name_indirection_subscripts) == 1
        subs = value.name_indirection_subscripts[0]
        assert len(subs) == 2
        # Subscripts should be numeric literals
        assert isinstance(subs[0], NumericLiteral)
        assert subs[0].value == 1
        assert isinstance(subs[1], NumericLiteral)
        assert subs[1].value == 2


# =============================================================================
# Argument Indirection Tests (ASG Level) - D4 Batch (continued)
# =============================================================================


@pytest.mark.asg
class TestArgumentIndirectionASG:
    """ASG tests for argument indirection semantic analysis.

    Argument indirection requires special handling since the
    actual command arguments are determined at runtime.

    Per MUMPS 1995 spec §8.1.3 (1995__a108004.md):
        "A single instance of argument indirection may evaluate to one
         complete argument or to a sublist of complete arguments."

    Reference: §6.3.1, §7.3.2
    """

    def test_argument_indirection_classified(self):
        """Argument indirection in WRITE is IndirectionType.NAME (§7.3.2).

        Note: In the current implementation, WRITE @VAR creates an Indirection
        node with type NAME (the value of VAR is a variable name). True
        argument indirection (where VAR contains a complete argument like
        "!,X") would be resolved at runtime.
        """
        parser = MUMPSParser()
        result = parser.parse("TEST\n W @VAR")
        stmt = result.labels[0].body.statements[0]

        assert len(stmt.arguments) >= 1
        arg = stmt.arguments[0]
        assert isinstance(arg, Indirection)
        # WRITE @VAR is name indirection - VAR contains a variable name
        assert arg.indirection_type == IndirectionType.NAME

    def test_do_indirection_requires_runtime(self):
        """DO @VAR has indirect call detected in ASG (§6.3.1).

        Since the target is determined at runtime, the call cannot be
        statically resolved. The MCall should have label_is_indirect=True
        and indirection set to the variable.

        After signature analysis via compute_all_signatures, the label's
        requires_runtime_scope and routine's requires_runtime_eval will be True.
        """
        from m2py.analysis.variables import compute_all_signatures

        parser = MUMPSParser()
        result = parser.parse("TEST\n D @X")

        # The specific call should have indirection detected
        stmt = result.labels[0].body.statements[0]
        call = stmt.targets[0]
        assert call.label_is_indirect is True
        assert call.indirection is not None
        assert call.indirection_levels == 1
        # Indirection expression should be the variable X
        assert isinstance(call.indirection, LocalVariable)
        assert call.indirection.name == "X"

        # After signature analysis, routine-level flag is set
        signatures = compute_all_signatures(result)
        assert signatures["TEST"].requires_runtime_scope is True
        assert result.requires_runtime_eval is True

    def test_xecute_indirection_detection(self):
        """XECUTE @VAR has indirection and requires runtime eval (§6.3.1).

        XECUTE always requires runtime evaluation. The statement itself
        has requires_runtime_eval=True. With indirection, even the code
        string is not known until runtime.
        """
        from m2py.asg.statements import MXecuteStatement

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


# =============================================================================
# Pattern Indirection Tests (ASG Level) - D4 Batch (continued)
# =============================================================================


@pytest.mark.asg
class TestPatternIndirectionASG:
    """ASG tests for pattern indirection semantic analysis.

    Pattern indirection means the pattern string is evaluated
    at runtime rather than compile time.

    Per 1995__a901027.md:
        "Pattern indirection
         Set CODE='3U'_$Select(SPECIAL:'2N',1:'')_'5L'
         If X?@CODE"

    Reference: §7.2.5.5
    """

    def test_pattern_indirection_classified(self):
        """Pattern indirection uses pattern_indirect field (§7.2.5.5).

        MPatternMatch with indirect pattern has pattern_indirect set
        to the variable containing the pattern string.
        """
        from m2py.asg.expressions import MPatternMatch

        parser = MUMPSParser()
        result = parser.parse("TEST\n I X?@PAT Q")
        stmt = result.labels[0].body.statements[0]

        cond = stmt.condition
        assert isinstance(cond, MPatternMatch)
        assert cond.pattern_indirect is not None
        assert isinstance(cond.pattern_indirect, LocalVariable)
        assert cond.pattern_indirect.name == "PAT"

    def test_pattern_indirection_prevents_static_compile(self):
        """Pattern indirection prevents static pattern compilation (§7.2.5.5).

        When a pattern is indirect, compiled_regex should be None since
        the actual pattern is not known until runtime.
        """
        from m2py.asg.expressions import MPatternMatch

        parser = MUMPSParser()
        result = parser.parse("TEST\n I X?@PAT Q")
        stmt = result.labels[0].body.statements[0]

        cond = stmt.condition
        assert isinstance(cond, MPatternMatch)
        # With indirect pattern, compiled_regex should be None
        assert cond.compiled_regex is None
        # The pattern string should be empty
        assert cond.pattern == ""


# =============================================================================
# Indirection Tests (Codegen Level) - D5 Batch
# =============================================================================


@pytest.mark.codegen
class TestIndirectionCodegen:
    """Codegen tests for indirection runtime behavior.

    Generated Python code must correctly handle all indirection
    types at runtime.

    Note: These tests are stubs pending codegen implementation.
    The generated Python runtime needs:
    1. A variable lookup function that takes a name string
    2. A pattern match function that compiles patterns at runtime
    3. Support for nested indirection chains

    Reference: §6.3.1, §7.3
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Codegen not yet implemented: name indirection execution")
    def test_name_indirection_resolves_at_runtime(self):
        """Name indirection resolves variable name at runtime (§7.3.1).

        Per 1995__a901027.md: "Set @X1='HELLO' will be executed as: Set Y='HELLO'"
        When X1="Y", setting @X1 should set variable Y.
        """
        pytest.fail("Stub - implement when codegen supports indirection")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Codegen not yet implemented: argument indirection execution"
    )
    def test_argument_indirection_resolves_at_runtime(self):
        """Argument indirection resolves argument at runtime (§7.3.2).

        Per 1995__a901027.md: "Write @$Select(ENOUGH:SPACE,1:PAGE)"
        The argument to WRITE is determined by evaluating the indirection.
        """
        pytest.fail("Stub - implement when codegen supports indirection")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Codegen not yet implemented: pattern indirection execution"
    )
    def test_pattern_indirection_resolves_at_runtime(self):
        """Pattern indirection resolves pattern at runtime (§7.2.5.5).

        Per 1995__a901027.md: "Write string?@pattern" where pattern="3N1...4N"
        The pattern string is retrieved and compiled at runtime.
        """
        pytest.fail("Stub - implement when codegen supports indirection")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Codegen not yet implemented: chained indirection execution"
    )
    def test_chained_indirection_resolves_correctly(self):
        """Chained indirection (@@VAR) resolves both levels (§7.3.1).

        Per YDBTest/indirection/inref/indlcl.m:
        "set @@variable='PASSED'"
        Multiple levels of indirection are dereferenced in sequence.
        """
        pytest.fail("Stub - implement when codegen supports indirection")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Codegen not yet implemented: subscripted indirection execution"
    )
    def test_subscripted_indirection_resolves_correctly(self):
        """Subscripted indirection @VAR@(1,2) works correctly (§7.3.1).

        Per 1984 addition (1995__a901027.md):
        "@ARRAY@(1,2,3) where ARRAY='PRICES' refers to PRICES(1,2,3)"
        The base is resolved first, then subscripts are appended.
        """
        pytest.fail("Stub - implement when codegen supports indirection")
