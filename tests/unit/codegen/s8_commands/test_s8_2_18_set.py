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

    def test_lhs_piece_omitted_piece_from_defaults_to_one(self, execute_mumps):
        """SET $PIECE with omitted piece_from defaults to piece 1 (§8.2.18).

        S $P(X,"^")="NEW" sets piece 1 to "NEW".
        YDB verified: S X="A^B^C" S $P(X,"^")="NEW" W X → "NEW^B^C"
        """
        result = execute_mumps('TEST\n S X="A^B^C" S $P(X,"^")="NEW"\n W X\n Q\n')
        assert result.output == "NEW^B^C"
        assert result.success is True

    def test_lhs_piece_omitted_on_undefined_creates_piece_one(self, execute_mumps):
        """SET $PIECE on undefined variable with omitted piece creates piece 1 (§8.2.18).

        YDB verified: S $P(Y,"^")="FIRST" W Y → "FIRST"
        """
        result = execute_mumps('TEST\n S $P(Y,"^")="FIRST"\n W Y\n Q\n')
        assert result.output == "FIRST"
        assert result.success is True

    def test_lhs_piece_omitted_with_global(self, execute_mumps):
        """SET $PIECE on global with omitted piece_from defaults to 1 (§8.2.18).

        YDB verified: S ^G="X^Y^Z" S $P(^G,"^")="A" W ^G → "A^Y^Z"
        """
        result = execute_mumps('TEST\n S ^G="X^Y^Z" S $P(^G,"^")="A"\n W ^G\n Q\n')
        assert result.output == "A^Y^Z"
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


# =============================================================================
# LHS $EXTRACT Tests (consolidated from test_spec_009_lhs_extract.py)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.spec009
class TestLHSExtractBasic:
    """Tests for basic LHS $EXTRACT assignment."""

    def test_basic_character_replacement(self, execute_mumps):
        """Scenario 1: Replace first two characters of string.

        S X="HELLO" S $E(X,1,2)="YO" W X → "YOLLO"
        """
        result = execute_mumps('TEST S X="HELLO" S $E(X,1,2)="YO" W X Q')
        assert result.output == "YOLLO"

    def test_undefined_variable_creates_it(self, execute_mumps):
        """Scenario 2: LHS $EXTRACT on undefined variable creates it.

        S $E(Z,1,3)="ABC" W Z → "ABC"
        """
        result = execute_mumps('TEST S $E(Z,1,3)="ABC" W Z Q')
        assert result.output == "ABC"

    def test_space_padding(self, execute_mumps):
        """Scenario 3: Pad existing variable with spaces to reach position.

        S W="AB" S $E(W,5,6)="XY" W W → "AB  XY"
        """
        result = execute_mumps('TEST S W="AB" S $E(W,5,6)="XY" W W Q')
        assert result.output == "AB  XY"

    def test_single_position(self, execute_mumps):
        """Scenario 4: Single position replacement (no to_pos specified).

        S X="ABCDE" S $E(X,2)="X" W X → "AXCDE"
        """
        result = execute_mumps('TEST S X="ABCDE" S $E(X,2)="X" W X Q')
        assert result.output == "AXCDE"

    def test_replacement_longer_than_range(self, execute_mumps):
        """Scenario 5: Replacement string is longer than original range.

        S X="ABC" S $E(X,1,5)="HELLO" W X → "HELLO"
        """
        result = execute_mumps('TEST S X="ABC" S $E(X,1,5)="HELLO" W X Q')
        assert result.output == "HELLO"


@pytest.mark.codegen
@pytest.mark.spec009
class TestLHSExtractEdgeCases:
    """Edge case tests for LHS $EXTRACT assignment."""

    def test_replacement_longer_than_original_range_middle(self, execute_mumps):
        """Replacement longer than range in middle of string expands it.

        S X="HELLO" S $E(X,2,3)="ABCD" W X → "HABCDLO"
        """
        result = execute_mumps('TEST S X="HELLO" S $E(X,2,3)="ABCD" W X Q')
        assert result.output == "HABCDLO"

    def test_replacement_shorter_than_range(self, execute_mumps):
        """Replacement shorter than range shrinks the string.

        S X="HELLO" S $E(X,2,4)="X" W X → "HXO"
        """
        result = execute_mumps('TEST S X="HELLO" S $E(X,2,4)="X" W X Q')
        assert result.output == "HXO"

    def test_same_length_replacement(self, execute_mumps):
        """Same length replacement keeps string length.

        S X="HELLO" S $E(X,2,3)="XX" W X → "HXXLO"
        """
        result = execute_mumps('TEST S X="HELLO" S $E(X,2,3)="XX" W X Q')
        assert result.output == "HXXLO"

    def test_empty_string_position_one(self, execute_mumps):
        """Set position 1 on empty string.

        S X="" S $E(X,1)="A" W X → "A"
        """
        result = execute_mumps('TEST S X="" S $E(X,1)="A" W X Q')
        assert result.output == "A"

    def test_replace_at_end(self, execute_mumps):
        """Replace characters at end of string.

        S X="HELLO" S $E(X,4,5)="XX" W X → "HELXX"
        """
        result = execute_mumps('TEST S X="HELLO" S $E(X,4,5)="XX" W X Q')
        assert result.output == "HELXX"

    def test_extend_string_beyond_end(self, execute_mumps):
        """Extend string by setting position beyond end.

        S X="ABC" S $E(X,5)="X" W X → "ABC X"
        """
        result = execute_mumps('TEST S X="ABC" S $E(X,5)="X" W X Q')
        assert result.output == "ABC X"

    def test_lhs_extract_position_zero_is_noop(self, execute_mumps):
        """LHS $EXTRACT with position 0 should be no-op (YDB verified).

        S X="abc" S $E(X,0)="X" W X → "abc" (unchanged)
        Unlike RHS $E(X,0) which returns "", LHS $E(X,0)=val is a no-op.
        """
        result = execute_mumps('TEST S X="abc" S $E(X,0)="X" W X Q')
        assert result.output == "abc"

    def test_lhs_extract_negative_start_treated_as_one(self, execute_mumps):
        """LHS $EXTRACT with negative start should map to position 1 (YDB verified).

        S X="abc" S $E(X,-1,2)="XX" W X → "XXc"
        YDB treats negative start as 1, so this replaces positions 1-2.
        """
        result = execute_mumps('TEST S X="abc" S $E(X,-1,2)="XX" W X Q')
        assert result.output == "XXc"


@pytest.mark.codegen
@pytest.mark.spec009
class TestLHSExtractGlobals:
    """Tests for LHS $EXTRACT on global variables (FR-009)."""

    def test_lhs_extract_on_global(self, execute_mumps):
        """LHS $EXTRACT works on global variables.

        S $E(^G,1,3)="ABC" W ^G → "ABC"
        """
        result = execute_mumps('TEST S $E(^G,1,3)="ABC" W ^G Q')
        assert result.output == "ABC"

    def test_lhs_extract_on_subscripted_global(self, execute_mumps):
        """LHS $EXTRACT on subscripted global variable."""
        result = execute_mumps('TEST S ^G(1)="HELLO" S $E(^G(1),2,3)="XX" W ^G(1) Q')
        assert result.output == "HXXLO"

    def test_lhs_extract_global_padding(self, execute_mumps):
        """LHS $EXTRACT on undefined global pads with spaces."""
        result = execute_mumps('TEST S $E(^H,3)="X" W ^H Q')
        assert result.output == "  X"


@pytest.mark.codegen
@pytest.mark.spec009
class TestLHSExtractStartGreaterThanEnd:
    """Tests for LHS $EXTRACT with start > end edge case."""

    def test_start_greater_than_end_no_modification(self, execute_mumps):
        """When start > end, no modification occurs per YDB behavior.

        S X="HELLO" S $E(X,4,2)="XX" W X → "HELLO" (unchanged)
        """
        result = execute_mumps('TEST S X="HELLO" S $E(X,4,2)="XX" W X Q')
        assert result.output == "HELLO"

    def test_start_greater_than_end_with_value(self, execute_mumps):
        """Start > end with existing value is a no-op.

        S X="ABCDE" S $E(X,3,1)="XXX" W X → "ABCDE" (unchanged)
        """
        result = execute_mumps('TEST S X="ABCDE" S $E(X,3,1)="XXX" W X Q')
        assert result.output == "ABCDE"


# =============================================================================
# LHS $PIECE Tests (consolidated from test_spec_009_lhs_piece.py)
# =============================================================================


@pytest.mark.codegen
@pytest.mark.spec009
class TestLHSPieceBasic:
    """Tests for basic LHS $PIECE assignment."""

    def test_basic_piece_replacement(self, execute_mumps):
        """Scenario 1: Replace second piece of delimited string.

        S X="A^B^C" S $P(X,"^",2)="NEW" W X → "A^NEW^C"
        """
        result = execute_mumps('TEST S X="A^B^C" S $P(X,"^",2)="NEW" W X Q')
        assert result.output == "A^NEW^C"

    def test_undefined_variable_with_padding(self, execute_mumps):
        """Scenario 2: LHS $PIECE on undefined variable pads with delimiters.

        S $P(Y,"^",3)="C" W Y → "^^C"
        """
        result = execute_mumps('TEST S $P(Y,"^",3)="C" W Y Q')
        assert result.output == "^^C"

    def test_existing_variable_needs_padding(self, execute_mumps):
        """Scenario 3: Pad existing variable to reach target piece.

        S X="A" S $P(X,"^",3)="C" W X → "A^^C"
        """
        result = execute_mumps('TEST S X="A" S $P(X,"^",3)="C" W X Q')
        assert result.output == "A^^C"

    def test_range_replacement(self, execute_mumps):
        """Scenario 4: Range replacement collapses multiple pieces.

        S X="A^B^C^D^E" S $P(X,"^",2,4)="X" W X → "A^X^E"
        """
        result = execute_mumps('TEST S X="A^B^C^D^E" S $P(X,"^",2,4)="X" W X Q')
        assert result.output == "A^X^E"


@pytest.mark.codegen
@pytest.mark.spec009
class TestLHSPieceEdgeCases:
    """Edge case tests for LHS $PIECE assignment."""

    def test_piece_one_replacement(self, execute_mumps):
        """Replace first piece of string."""
        result = execute_mumps('TEST S X="A^B^C" S $P(X,"^",1)="NEW" W X Q')
        assert result.output == "NEW^B^C"

    def test_empty_string_piece_one(self, execute_mumps):
        """Set piece 1 on empty string."""
        result = execute_mumps('TEST S X="" S $P(X,"^",1)="A" W X Q')
        assert result.output == "A"

    def test_range_beyond_existing_pieces(self, execute_mumps):
        """Range replacement where end is beyond existing pieces."""
        result = execute_mumps('TEST S X="A^B" S $P(X,"^",2,5)="X" W X Q')
        assert result.output == "A^X"

    def test_range_starting_beyond_existing(self, execute_mumps):
        """Range replacement starting beyond existing pieces adds padding."""
        result = execute_mumps('TEST S X="A^B" S $P(X,"^",4,5)="X" W X Q')
        assert result.output == "A^B^^X"

    def test_different_delimiter(self, execute_mumps):
        """Use a different delimiter character."""
        result = execute_mumps('TEST S X="A:B:C" S $P(X,":",2)="NEW" W X Q')
        assert result.output == "A:NEW:C"

    def test_multi_char_delimiter(self, execute_mumps):
        """Use multi-character delimiter."""
        result = execute_mumps('TEST S X="A||B||C" S $P(X,"||",2)="NEW" W X Q')
        assert result.output == "A||NEW||C"


@pytest.mark.codegen
@pytest.mark.spec009
class TestLHSPieceGlobals:
    """Tests for LHS $PIECE on global variables (FR-009)."""

    def test_lhs_piece_on_global(self, execute_mumps):
        """Scenario 5: LHS $PIECE works on global variables.

        S $P(^G,"^",2)="B" W ^G → "^B"
        """
        result = execute_mumps('TEST S $P(^G,"^",2)="B" W ^G Q')
        assert result.output == "^B"

    def test_lhs_piece_on_subscripted_global(self, execute_mumps):
        """LHS $PIECE on subscripted global variable."""
        result = execute_mumps('TEST S ^G(1)="A^B^C" S $P(^G(1),"^",2)="NEW" W ^G(1) Q')
        assert result.output == "A^NEW^C"

    def test_lhs_piece_global_padding(self, execute_mumps):
        """LHS $PIECE on undefined global pads with delimiters."""
        result = execute_mumps('TEST S $P(^H,"^",3)="C" W ^H Q')
        assert result.output == "^^C"


@pytest.mark.codegen
@pytest.mark.spec009
class TestLHSPieceInvalidInputs:
    """Tests for LHS $PIECE edge cases with invalid piece numbers."""

    def test_piece_zero_no_modification(self, execute_mumps):
        """Piece number 0 results in no modification per MUMPS spec.

        S X="A^B^C" S $P(X,"^",0)="NEW" W X → "A^B^C" (unchanged)
        """
        result = execute_mumps('TEST S X="A^B^C" S $P(X,"^",0)="NEW" W X Q')
        assert result.output == "A^B^C"

    def test_negative_piece_no_modification(self, execute_mumps):
        """Negative piece number results in no modification per MUMPS spec.

        S X="A^B^C" S $P(X,"^",-1)="NEW" W X → "A^B^C" (unchanged)
        """
        result = execute_mumps('TEST S X="A^B^C" S $P(X,"^",-1)="NEW" W X Q')
        assert result.output == "A^B^C"
