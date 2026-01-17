"""Tests for SET command code generation (§8.2.18).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.18
"""

import pytest


@pytest.mark.codegen
class TestSetCommandCodegen:
    """Codegen-level tests for SET command code generation (§8.2.18)."""

    def test_set_to_assignment(self, generate_python):
        """SET generates assignment statement (§8.2.18)."""
        code = generate_python("TEST\n S X=1\n Q\n")
        assert "X = " in code or "X=" in code

    def test_set_and_write_variable(self, execute_mumps):
        """SET assigns value, WRITE outputs it (§8.2.18).

        User Story 1 acceptance scenario 1:
        Given: TEST S X=1 W X Q
        When: generated and executed
        Then: output is "1"
        """
        result = execute_mumps("TEST\n S X=1\n W X\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_set_multiple_assignments(self, execute_mumps):
        """SET with comma-separated assignments works (§8.2.18).

        Spec 011 User Story 7 - Multiple SET Assignments
        Acceptance scenario 1:
        Given: TEST S X=1,Y=2,Z=3 W X,Y,Z Q
        When: generated and executed
        Then: output is "123"
        """
        result = execute_mumps("TEST\n S X=1,Y=2,Z=3\n W X,Y,Z\n Q\n")
        assert result.output == "123"
        assert result.success is True

    def test_set_multiple_string_assignments(self, execute_mumps):
        """SET with multiple string assignments works (§8.2.18).

        Spec 011 User Story 7 - Multiple SET Assignments
        Acceptance scenario 2:
        Given: TEST S A="X",B="Y" W A,B Q
        When: generated and executed
        Then: output is "XY"
        """
        result = execute_mumps('TEST\n S A="X",B="Y"\n W A,B\n Q\n')
        assert result.output == "XY"
        assert result.success is True

    def test_set_multiple_with_expressions(self, execute_mumps):
        """SET with expressions in later assignments uses prior values (§8.2.18).

        Multiple assignments execute left-to-right, so Y=X*3 uses X's new value.
        """
        result = execute_mumps("TEST\n S X=1+2,Y=X*3\n W X,Y\n Q\n")
        assert result.output == "39"
        assert result.success is True

    def test_set_multiple_subscripted(self, execute_mumps):
        """SET with multiple subscripted assignments (§8.2.18)."""
        result = execute_mumps("TEST\n S A(1)=10,A(2)=20\n W A(1),A(2)\n Q\n")
        assert result.output == "1020"
        assert result.success is True

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: SET multiple targets")
    def test_set_multiple_targets(self, generate_python):
        """SET (X,Y)=value generates multiple assignments (§8.2.18)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: SET global")
    def test_set_global(self, generate_python):
        """SET ^GLOBAL generates global assignment (§8.2.18)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: SET $PIECE basic")
    def test_set_piece(self, generate_python):
        """SET $PIECE generates piece replacement (§8.2.18)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: SET $EXTRACT basic")
    def test_set_extract(self, generate_python):
        """SET $EXTRACT generates substring replacement (§8.2.18)."""
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestLhsFunctionAssignmentCodegen:
    """Codegen tests for left-hand-side function assignment.

    SET $PIECE and SET $EXTRACT modify variables in-place with complex
    semantics: creation if undefined, delimiter padding, etc.

    Reference: §8.2.18
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LHS piece creates variable")
    def test_lhs_piece_creates_variable(self, generate_python):
        """SET $PIECE creates variable if undefined.

        S $P(X,"^",2)="B" when X undefined creates X="^B"
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LHS piece pads with delimiter")
    def test_lhs_piece_pads_with_delimiter(self, generate_python):
        """SET $PIECE pads with delimiters if needed.

        S X="A" S $P(X,"^",3)="C" creates X="A^^C"
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LHS piece replaces existing")
    def test_lhs_piece_replaces_existing(self, generate_python):
        """SET $PIECE replaces existing piece.

        S X="A^B^C" S $P(X,"^",2)="NEW" creates X="A^NEW^C"
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LHS extract creates variable")
    def test_lhs_extract_creates_variable(self, generate_python):
        """SET $EXTRACT creates variable if undefined.

        S $E(X,1,3)="ABC" when X undefined creates X="ABC"
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LHS extract replaces substring")
    def test_lhs_extract_replaces_substring(self, generate_python):
        """SET $EXTRACT replaces substring.

        S X="HELLO" S $E(X,1,2)="YO" creates X="YOLLO"
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: LHS extract beyond length")
    def test_lhs_extract_beyond_length(self, generate_python):
        """SET $EXTRACT beyond length pads with spaces.

        S X="AB" S $E(X,5,6)="XY" may create X="AB  XY"
        """
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestComputedOffsetCodegen:
    """Codegen tests for computed offsets in DO/GOTO.

    Offset expressions can include globals, functions, all operators.
    Requires line-indexed execution model.

    Reference: §8.2.3, §8.2.6
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: DO with literal offset")
    def test_do_with_literal_offset(self, generate_python):
        """DO LABEL+n with literal offset.

        D LABEL+5 dispatches to 5th line after LABEL.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: GOTO with literal offset")
    def test_goto_with_literal_offset(self, generate_python):
        """GOTO LABEL+n with literal offset.

        G LABEL+3 jumps to 3rd line after LABEL.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: offset with variable")
    def test_offset_with_variable(self, generate_python):
        """Offset containing variable evaluated at runtime.

        G LABEL+N computes target from N value.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: offset with global")
    def test_offset_with_global(self, generate_python):
        """Offset containing global variable.

        G STAR+^V1A reads ^V1A to compute offset.
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: offset with function")
    def test_offset_with_function(self, generate_python):
        """Offset containing intrinsic function call.

        G LABEL+$L(X) computes offset from $LENGTH(X).
        """
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: offset arithmetic")
    def test_offset_arithmetic(self, generate_python):
        """Offset with complex arithmetic expression.

        G LABEL+A*2-1 evaluates left-to-right.
        """
        pytest.fail("Stub - implement test")
