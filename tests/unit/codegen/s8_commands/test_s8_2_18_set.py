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

    def test_set_multiple_targets(self, execute_mumps):
        """SET (X,Y)=value assigns value to multiple targets (§8.2.18).

        YDB verified: S (X,Y)=5 W X,Y → "55"
        """
        result = execute_mumps("TEST\n S (X,Y)=5\n W X,Y\n Q\n")
        assert result.output == "55"
        assert result.success is True

    def test_set_global(self, execute_mumps):
        """SET ^GLOBAL generates global assignment (§8.2.18).

        YDB verified: S ^A=1 W ^A → "1"
        """
        result = execute_mumps("TEST\n S ^A=1\n W ^A\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_set_piece(self, execute_mumps):
        """SET $PIECE generates piece replacement (§8.2.18).

        YDB verified: S X="A^B^C" S $P(X,"^",2)="NEW" W X → "A^NEW^C"
        """
        result = execute_mumps('TEST\n S X="A^B^C" S $P(X,"^",2)="NEW"\n W X\n Q\n')
        assert result.output == "A^NEW^C"
        assert result.success is True

    def test_set_extract(self, execute_mumps):
        """SET $EXTRACT generates substring replacement (§8.2.18).

        YDB verified: S X="HELLO" S $E(X,1,2)="YO" W X → "YOLLO"
        """
        result = execute_mumps('TEST\n S X="HELLO" S $E(X,1,2)="YO"\n W X\n Q\n')
        assert result.output == "YOLLO"
        assert result.success is True


@pytest.mark.codegen
class TestLhsFunctionAssignmentCodegen:
    """Codegen tests for left-hand-side function assignment.

    SET $PIECE and SET $EXTRACT modify variables in-place with complex
    semantics: creation if undefined, delimiter padding, etc.

    Reference: §8.2.18
    """

    def test_lhs_piece_creates_variable(self, execute_mumps):
        """SET $PIECE creates variable if undefined.

        YDB verified: S $P(X,"^",2)="B" W X → "^B"
        """
        result = execute_mumps('TEST\n S $P(X,"^",2)="B"\n W X\n Q\n')
        assert result.output == "^B"
        assert result.success is True

    def test_lhs_piece_pads_with_delimiter(self, execute_mumps):
        """SET $PIECE pads with delimiters if needed.

        YDB verified: S X="A" S $P(X,"^",3)="C" W X → "A^^C"
        """
        result = execute_mumps('TEST\n S X="A" S $P(X,"^",3)="C"\n W X\n Q\n')
        assert result.output == "A^^C"
        assert result.success is True

    def test_lhs_piece_replaces_existing(self, execute_mumps):
        """SET $PIECE replaces existing piece.

        YDB verified: S X="A^B^C" S $P(X,"^",2)="NEW" W X → "A^NEW^C"
        """
        result = execute_mumps('TEST\n S X="A^B^C" S $P(X,"^",2)="NEW"\n W X\n Q\n')
        assert result.output == "A^NEW^C"
        assert result.success is True

    def test_lhs_extract_creates_variable(self, execute_mumps):
        """SET $EXTRACT creates variable if undefined.

        YDB verified: S $E(X,1,3)="ABC" W X → "ABC"
        """
        result = execute_mumps('TEST\n S $E(X,1,3)="ABC"\n W X\n Q\n')
        assert result.output == "ABC"
        assert result.success is True

    def test_lhs_extract_replaces_substring(self, execute_mumps):
        """SET $EXTRACT replaces substring.

        YDB verified: S X="HELLO" S $E(X,1,2)="YO" W X → "YOLLO"
        """
        result = execute_mumps('TEST\n S X="HELLO" S $E(X,1,2)="YO"\n W X\n Q\n')
        assert result.output == "YOLLO"
        assert result.success is True

    def test_lhs_extract_beyond_length(self, execute_mumps):
        """SET $EXTRACT beyond length pads with spaces.

        YDB verified: S X="AB" S $E(X,5,6)="XY" W X → "AB  XY"
        """
        result = execute_mumps('TEST\n S X="AB" S $E(X,5,6)="XY"\n W X\n Q\n')
        assert result.output == "AB  XY"
        assert result.success is True


@pytest.mark.codegen
class TestComputedOffsetCodegen:
    """Codegen tests for computed offsets in DO/GOTO.

    Offset expressions can include literals, variables, globals, functions,
    and arithmetic expressions. Requires line-indexed execution model.

    Reference: §8.2.3, §8.2.6, Spec 007
    """

    def test_do_with_literal_offset(self, generate_python, execute_mumps):
        """DO LABEL+n with literal offset dispatches to n-th line after LABEL.

        Per Spec 007: D LABEL+2 calls LABEL starting at statement index 2
        (0-indexed), skipping the first two statements.
        """
        code = """TEST D LABEL+2 Q
LABEL W "0" Q
 W "1" Q
 W "2" Q
"""
        python_code = generate_python(code)

        # Should have _line_map for offset dispatch
        assert "_line_map" in python_code
        # Should have _start_offset parameter in call
        assert "_start_offset" in python_code

        # Execute and verify - D LABEL+2 skips lines 2,3 and executes line 4
        result = execute_mumps(code)
        assert result.output == "2"
        assert result.success is True

    def test_goto_with_literal_offset(self, generate_python, execute_mumps):
        """GOTO LABEL+n with literal offset jumps to n-th line after LABEL.

        Per Spec 007: G LABEL+2 transfers to LABEL statement index 2.
        """
        code = """TEST G LABEL+2 Q
LABEL W "0" Q
 W "1" Q
 W "2" Q
"""
        python_code = generate_python(code)

        # Should have _line_map for offset dispatch
        assert "_line_map" in python_code

        # Execute and verify - G LABEL+2 jumps to line 4 (W "2")
        result = execute_mumps(code)
        assert result.output == "2"
        assert result.success is True

    def test_offset_with_variable(self, generate_python, execute_mumps):
        """Offset containing variable is evaluated at runtime.

        Per Spec 007: G LABEL+N computes target from N's value.
        """
        code = """TEST S N=1 G LABEL+N Q
LABEL W "0" Q
 W "1" Q
 W "2" Q
"""
        python_code = generate_python(code)

        # Should evaluate N at runtime using m_num()
        assert "m_num" in python_code or "int(" in python_code
        # Should have _line_map
        assert "_line_map" in python_code

        # Execute - N=1, so G LABEL+1 jumps to line 3 (W "1")
        result = execute_mumps(code)
        assert result.output == "1"
        assert result.success is True

    def test_offset_with_global(self, generate_python, execute_mumps):
        """Offset containing global variable reads global at runtime.

        Per Spec 007: G LABEL+^V reads ^V to compute offset.
        """
        code = """TEST S ^V=2 G LABEL+^V Q
LABEL W "0" Q
 W "1" Q
 W "2" Q
"""
        python_code = generate_python(code)

        # Should access global via _rt.globals
        assert "_rt.globals" in python_code or "globals" in python_code
        # Should have _line_map
        assert "_line_map" in python_code

        # Execute - ^V=2, so G LABEL+2 jumps to line 4 (W "2")
        result = execute_mumps(code)
        assert result.output == "2"
        assert result.success is True

    def test_offset_with_function(self, generate_python, execute_mumps):
        """Offset containing intrinsic function call evaluates function.

        Per Spec 007: G LABEL+$L(X) computes offset from $LENGTH(X).
        """
        code = """TEST S X="ab" G LABEL+$L(X) Q
LABEL W "0" Q
 W "1" Q
 W "2" Q
"""
        python_code = generate_python(code)

        # Should call len() for $LENGTH
        assert "len(" in python_code
        # Should have _line_map
        assert "_line_map" in python_code

        # Execute - $L("ab")=2, so G LABEL+2 jumps to line 4 (W "2")
        result = execute_mumps(code)
        assert result.output == "2"
        assert result.success is True

    def test_offset_arithmetic(self, generate_python, execute_mumps):
        """Offset with complex arithmetic expression evaluated left-to-right.

        Per Spec 007 and MUMPS §7.2: G LABEL+A*2-1 evaluates as ((A)*2)-1.
        """
        code = """TEST S A=1 G LABEL+A*2-1 Q
LABEL W "0" Q
 W "1" Q
 W "2" Q
"""
        python_code = generate_python(code)

        # Should have arithmetic operators
        assert "*" in python_code or "m_num" in python_code
        # Should have _line_map
        assert "_line_map" in python_code

        # Execute - A=1, so (1*2)-1=1, G LABEL+1 jumps to line 3 (W "1")
        result = execute_mumps(code)
        assert result.output == "1"
        assert result.success is True


@pytest.mark.codegen
class TestSetArgumentIndirectionCodegen:
    """Codegen tests for SET argument indirection (S @A where A="X=1").

    Spec 012 Phase 9: Support argument indirection in SET command.
    The indirection target contains a complete SET argument string.

    Reference: §7.1.1, §8.2.18
    """

    def test_set_argument_indirection_simple(self, execute_mumps):
        """S @A where A contains "X=1" sets X to 1.

        User Story 7 acceptance scenario 1:
        Given: S A="X=1" S @A
        When: generated and executed
        Then: X equals 1
        """
        result = execute_mumps('TEST\n S A="X=1" S @A\n W X\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_set_argument_indirection_multiple(self, execute_mumps):
        """S @A,@B executes both argument indirections.

        User Story 7 acceptance scenario 2:
        Given: S A="X=1",B="Y=2" S @A,@B
        When: generated and executed
        Then: X equals 1 and Y equals 2
        """
        result = execute_mumps('TEST\n S A="X=1",B="Y=2" S @A,@B\n W X,",",Y\n Q\n')
        assert result.output == "1,2"
        assert result.success is True

    def test_set_argument_indirection_multi_assign_string(self, execute_mumps):
        """S @A where A contains "X=1,Y=2" sets both X and Y.

        The indirection string can contain multiple comma-separated assignments.
        """
        result = execute_mumps('TEST\n S A="X=1,Y=2"\n S @A\n W X,",",Y\n Q\n')
        assert result.output == "1,2"
        assert result.success is True

    def test_set_argument_indirection_nested(self, execute_mumps):
        """S @A where A="@B" and B="X=5" sets X to 5.

        Nested argument indirection: the first level resolves to
        another indirection which is then executed.
        """
        result = execute_mumps('TEST\n S A="@B",B="X=5"\n S @A\n W X\n Q\n')
        assert result.output == "5"
        assert result.success is True

    def test_set_argument_indirection_mixed(self, execute_mumps):
        """Mixed regular and argument indirection in same SET.

        S Z=3,@A,Y=2 executes all in order.
        """
        result = execute_mumps('TEST\n S A="X=1"\n S Z=3,@A,Y=2\n W X,Y,Z\n Q\n')
        assert result.output == "123"
        assert result.success is True

    def test_set_argument_indirection_generates_execute_mumps(self, generate_python):
        """S @A generates _rt.execute_mumps("S " + ..., _scope) call."""
        code = generate_python('TEST\n S A="X=1" S @A\n Q\n')
        assert "execute_mumps" in code
        assert '"S "' in code
