"""Cross-cutting tests for indirection (§6.3.1, §7.3).

Indirection is a language feature that spans multiple commands and expressions.
This file tests the cross-cutting behavior of all three indirection types:
- Name indirection: @VAR evaluates to a variable name
- Argument indirection: @VAR evaluates to a command argument
- Pattern indirection: X?@VAR where VAR contains a pattern

Reference: MUMPS 1995 ANSI Standard, Section 6.3.1, 7.3
See also: FR-005 (cross-cutting features need dedicated tests)
"""

import pytest


# =============================================================================
# Name Indirection Tests (Parser Level)
# =============================================================================


@pytest.mark.parser
class TestNameIndirectionParser:
    """Parser tests for name indirection at expression level.

    Name indirection uses @ to dereference a variable that contains
    a variable name. E.g., if X="Y" then @X refers to variable Y.
    Reference: §7.3.1
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: name indirection basic form")
    def test_name_indirection_in_set_target(self):
        """SET @VAR=1 parses name indirection as target (§7.3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: name indirection in expression")
    def test_name_indirection_in_expression(self):
        """WRITE @VAR parses name indirection as expression (§7.3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subscripted name indirection")
    def test_subscripted_name_indirection(self):
        """@VAR(1,2) parses indirection with subscripts (§7.3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: chained name indirection")
    def test_chained_name_indirection(self):
        """@@VAR parses double indirection (§7.3.1)."""
        pytest.fail("Stub - implement test")


# =============================================================================
# Argument Indirection Tests (Parser Level)
# =============================================================================


@pytest.mark.parser
class TestArgumentIndirectionParser:
    """Parser tests for argument indirection in commands.

    Argument indirection uses @VAR where VAR contains a complete
    argument for a command. E.g., DO @VAR where VAR="LABEL^ROUTINE".
    Reference: §6.3.1, §7.3.2
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: argument indirection in DO")
    def test_argument_indirection_in_do(self):
        """DO @VAR parses argument indirection (§7.3.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: argument indirection in GOTO")
    def test_argument_indirection_in_goto(self):
        """GOTO @VAR parses argument indirection (§7.3.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: argument indirection in SET")
    def test_argument_indirection_in_set(self):
        """SET @VAR=1 or SET X=@VAR parses correctly (§7.3.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: argument indirection in KILL")
    def test_argument_indirection_in_kill(self):
        """KILL @VAR parses argument indirection (§7.3.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: argument indirection in WRITE")
    def test_argument_indirection_in_write(self):
        """WRITE @VAR parses argument indirection (§7.3.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: argument indirection in READ")
    def test_argument_indirection_in_read(self):
        """READ @VAR parses argument indirection (§7.3.2)."""
        pytest.fail("Stub - implement test")


# =============================================================================
# Pattern Indirection Tests (Parser Level)
# =============================================================================


@pytest.mark.parser
class TestPatternIndirectionParser:
    """Parser tests for pattern indirection in pattern match.

    Pattern indirection uses X?@VAR where VAR contains a pattern.
    Reference: §7.2.5.5
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pattern indirection basic")
    def test_pattern_indirection_basic(self):
        """X?@PAT parses pattern indirection (§7.2.5.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pattern indirection with subscript")
    def test_pattern_indirection_with_subscript(self):
        """X?@PAT(1) parses pattern indirection with subscript (§7.2.5.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pattern indirection in expression")
    def test_pattern_indirection_in_if(self):
        """IF X?@PAT parses pattern indirection in condition (§7.2.5.5)."""
        pytest.fail("Stub - implement test")


# =============================================================================
# Name Indirection Tests (ASG Level)
# =============================================================================


@pytest.mark.asg
class TestNameIndirectionASG:
    """ASG tests for name indirection semantic analysis.

    ASG analysis must classify indirection type and track
    the indirected variable reference.
    Reference: §7.3.1
    """

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: name indirection type classification"
    )
    def test_name_indirection_classified(self):
        """Name indirection is classified as IndirectionType.NAME (§7.3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: indirection target tracking")
    def test_name_indirection_target_tracked(self):
        """Indirection target variable is tracked in ASG (§7.3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subscript resolution")
    def test_subscripted_indirection_subscripts_resolved(self):
        """Subscripts on indirection are resolved (§7.3.1)."""
        pytest.fail("Stub - implement test")


# =============================================================================
# Argument Indirection Tests (ASG Level)
# =============================================================================


@pytest.mark.asg
class TestArgumentIndirectionASG:
    """ASG tests for argument indirection semantic analysis.

    Argument indirection requires special handling since the
    actual command arguments are determined at runtime.
    Reference: §6.3.1, §7.3.2
    """

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: argument indirection classification"
    )
    def test_argument_indirection_classified(self):
        """Argument indirection is classified as IndirectionType.ARGUMENT (§7.3.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO indirection requires runtime")
    def test_do_indirection_requires_runtime(self):
        """DO @VAR is marked as requiring runtime evaluation (§6.3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: XECUTE indirection detection")
    def test_xecute_indirection_detection(self):
        """XECUTE @VAR has indirection flag set (§6.3.1)."""
        pytest.fail("Stub - implement test")


# =============================================================================
# Pattern Indirection Tests (ASG Level)
# =============================================================================


@pytest.mark.asg
class TestPatternIndirectionASG:
    """ASG tests for pattern indirection semantic analysis.

    Pattern indirection means the pattern string is evaluated
    at runtime rather than compile time.
    Reference: §7.2.5.5
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pattern indirection classification")
    def test_pattern_indirection_classified(self):
        """Pattern indirection is classified as IndirectionType.PATTERN (§7.2.5.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: pattern indirection prevents compile"
    )
    def test_pattern_indirection_prevents_static_compile(self):
        """Pattern indirection prevents static pattern compilation (§7.2.5.5)."""
        pytest.fail("Stub - implement test")


# =============================================================================
# Indirection Tests (Codegen Level)
# =============================================================================


@pytest.mark.codegen
class TestIndirectionCodegen:
    """Codegen tests for indirection runtime behavior.

    Generated Python code must correctly handle all indirection
    types at runtime.
    Reference: §6.3.1, §7.3
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: name indirection execution")
    def test_name_indirection_resolves_at_runtime(self):
        """Name indirection resolves variable name at runtime (§7.3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: argument indirection execution")
    def test_argument_indirection_resolves_at_runtime(self):
        """Argument indirection resolves argument at runtime (§7.3.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: pattern indirection execution")
    def test_pattern_indirection_resolves_at_runtime(self):
        """Pattern indirection resolves pattern at runtime (§7.2.5.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: chained indirection execution")
    def test_chained_indirection_resolves_correctly(self):
        """Chained indirection (@@VAR) resolves both levels (§7.3.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subscripted indirection execution")
    def test_subscripted_indirection_resolves_correctly(self):
        """Subscripted indirection @VAR(1,2) works correctly (§7.3.1)."""
        pytest.fail("Stub - implement test")
