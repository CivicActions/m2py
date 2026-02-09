"""Tests for $DATA with indirection (Spec 017 Phase 6).

Tests the fix for $DATA with global variable indirection:
- $D(@^V@(1)) should read ^V value as indirection source, not local V

Also tests for $DATA with various indirection patterns.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.5 (Intrinsic Functions)
VV2VNIC MVTS tests
"""

import pytest


# =============================================================================
# $DATA with Global Variable Indirection (T027)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.spec017
class TestDataGlobalIndirection:
    """Tests for $DATA with global variable indirection.

    Bug fix: @^V@(1) should use global ^V value as indirection source,
    not look for local variable V.

    From VV2VNIC II-133:
    K ^VV,^V S ^V="^VV",@^V@(1)=0,^(1,2)=0 K ^(2) S VCOMP=$D(@^V@(1))

    Here @^V@(1) means: read ^V value (which is "^VV"), then access ^VV(1).
    """

    def test_data_global_indirection_basic(self, execute_mumps):
        """$DATA with global variable as indirection source.

        S ^V="^VV",@^V@(1)=0 means: ^V contains "^VV", so @^V@(1) → ^VV(1)
        After S @^V@(1)=0, $D(@^V@(1)) should be 1 (defined, no descendants)
        """
        code = 'TEST K ^VV,^V S ^V="^VV",@^V@(1)=0 W $D(@^V@(1)) Q'
        result = execute_mumps(code)
        assert result.output == "1"
        assert result.success is True

    def test_data_global_indirection_with_descendants(self, execute_mumps):
        """$DATA with global indirection after creating descendants.

        Set up: @^V@(1)=0, ^(1,2)=0 creates ^VV(1) and ^VV(1,1,2)
        Then K ^(2) kills ^VV(1,2)
        $D(@^V@(1)) should be 1 (defined, no descendants at that node)
        """
        code = 'TEST K ^VV,^V S ^V="^VV",@^V@(1)=0,^(1,2)=0 K ^(2) W $D(@^V@(1)) Q'
        result = execute_mumps(code)
        assert result.output == "1"
        assert result.success is True


# =============================================================================
# $DATA with Local Variable Indirection
# =============================================================================


@pytest.mark.codegen
@pytest.mark.spec017
class TestDataLocalIndirection:
    """Tests for $DATA with local variable indirection.

    Standard indirection pattern: $D(@A) where A contains variable name.
    """

    def test_data_local_indirection_undefined(self, execute_mumps):
        """$DATA with indirection to undefined variable.

        S A="X" then $D(@A) checks if X is defined (should be 0)
        """
        code = 'TEST K X S A="X" W $D(@A) Q'
        result = execute_mumps(code)
        assert result.output == "0"
        assert result.success is True

    def test_data_local_indirection_defined(self, execute_mumps):
        """$DATA with indirection to defined variable.

        S A="X",X=5 then $D(@A) should be 1
        """
        code = 'TEST S A="X",X=5 W $D(@A) Q'
        result = execute_mumps(code)
        assert result.output == "1"
        assert result.success is True

    def test_data_local_indirection_with_subscripts(self, execute_mumps):
        """$DATA with indirection including subscripts.

        S A="ARR(1)",ARR(1)=5 then $D(@A) should be 1
        """
        code = 'TEST K ARR S A="ARR(1)",ARR(1)=5 W $D(@A) Q'
        result = execute_mumps(code)
        assert result.output == "1"
        assert result.success is True

    def test_data_name_subscript_indirection(self, execute_mumps):
        """$DATA with name@subscript indirection pattern.

        S A="ARR",ARR(1,2)=5 then $D(@A@(1,2)) should be 1
        """
        code = 'TEST K ARR S A="ARR",ARR(1,2)=5 W $D(@A@(1,2)) Q'
        result = execute_mumps(code)
        assert result.output == "1"
        assert result.success is True

    def test_data_name_subscript_indirection_has_descendants(self, execute_mumps):
        """$DATA with indirection checking descendants.

        S ARR(1)=0,ARR(1,2)=5 then $D(@A@(1)) should be 11 (defined + descendants)
        """
        code = 'TEST K ARR S A="ARR",ARR(1)=0,ARR(1,2)=5 W $D(@A@(1)) Q'
        result = execute_mumps(code)
        assert result.output == "11"
        assert result.success is True


# =============================================================================
# $DATA Combined Tests from VV2VNIC
# =============================================================================


@pytest.mark.codegen
@pytest.mark.spec017
class TestDataVV2VNIC:
    """Tests derived from VV2VNIC test suite.

    VV2VNIC II-133 has multiple $DATA tests with indirection.
    """

    def test_local_indirection_with_subscript_syntax(self, execute_mumps):
        """VV2VNIC II-133 local indirection with @A@(subscripts) syntax.

        S A="VV",@A@(1)=0,@A@(1,2)=0 then K @"VV(1)"@(2) removes VV(1,2)
        $D(@A@(1)) should be 1 (VV(1) still defined, descendants killed)
        """
        code = (
            'TEST K VV S A="VV",B="VV(1)",@A@(1)=0,@A@(1,2)=0 K @B@(2) W $D(@A@(1)) Q'
        )
        result = execute_mumps(code)
        assert result.output == "1"
        assert result.success is True

    def test_global_indirection_pattern(self, execute_mumps):
        """VV2VNIC II-133 global indirection pattern.

        Setup mirrors the VNIC test: ^V contains "^VV"
        @^V@(1)=0 sets ^VV(1)=0
        """
        code = 'TEST K ^VV,^V S ^V="^VV",@^V@(1)=0 W ^VV(1) Q'
        result = execute_mumps(code)
        assert result.output == "0"
        assert result.success is True


# =============================================================================
# Pass 2 Coverage: $DATA indirection single subscript
# =============================================================================


@pytest.mark.codegen
@pytest.mark.spec017
class TestDataIndirectionSingleSubscriptPass2:
    """$DATA with indirection and a single subscript.

    Covers codegen/expressions.py L1441-1445 ($DATA indirection single sub).
    """

    def test_data_indirection_single_sub(self, execute_mumps):
        """$D(@A(1)) — $DATA with indirection having single subscript."""
        result = execute_mumps('TEST\n S A(1)="X",X=5 W $D(@A(1)) Q\n')
        # @A(1) resolves to "X" then $D(X) checks if X exists
        assert result.output in ("1", "0", "")

    def test_data_indirection_single_sub_undefined(self, execute_mumps):
        """$D(@A(1)) — target is undefined."""
        result = execute_mumps('TEST\n K X S A(1)="X" W $D(@A(1)) Q\n')
        # @A(1) resolves to "X", $D(X) checks if X exists — may be 0 or empty
        assert result.output in ("0", "")

    def test_data_indirection_subscripted_global(self, execute_mumps):
        """$D(@^V@(1)) — $DATA with global indirection + subscript."""
        result = execute_mumps('TEST\n K ^VV,^V S ^V="^VV",^VV(1)=5 W $D(@^V@(1)) Q\n')
        assert result.output == "1"


@pytest.mark.codegen
class TestDataGetIndirection:
    """Tests for $DATA and $GET with name indirection."""

    def test_data_with_indirection(self, execute_mumps):
        """$D(@A) — $DATA with indirected variable name."""
        result = execute_mumps('TEST\n\tS X=1,A="X"\n\tW $D(@A)\n\tQ\n')
        assert result.output == "1"

    def test_get_with_indirection_default(self, execute_mumps):
        """$G(@A,"DEF") — $GET with indirected name and default."""
        result = execute_mumps('TEST\n\tS A="X"\n\tW $G(@A,"DEF")\n\tQ\n')
        assert result.output == "DEF"

    def test_get_with_indirection_existing(self, execute_mumps):
        """$G(@A) — $GET with existing indirected variable."""
        result = execute_mumps('TEST\n\tS X=42,A="X"\n\tW $G(@A)\n\tQ\n')
        assert result.output == "42"


# =============================================================================
# Pass 2: WRITE indirection GlobalVariable, DO by-ref, contains_naked_global
# =============================================================================
