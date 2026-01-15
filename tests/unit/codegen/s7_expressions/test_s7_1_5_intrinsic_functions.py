"""Tests for Intrinsic Functions code generation (§7.1.5).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.5
"""

import pytest


@pytest.mark.codegen
class TestIntrinsicFunctionsCodegen:
    """Codegen-level tests for intrinsic functions code generation (§7.1.5)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $ASCII codegen")
    def test_function_ascii(self, generate_python):
        """$ASCII generates ord() equivalent (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $CHAR codegen")
    def test_function_char(self, generate_python):
        """$CHAR generates chr() equivalent (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $DATA codegen")
    def test_function_data(self, generate_python):
        """$DATA generates data check (§7.1.5)."""
        pytest.fail("Stub - implement test")

    def test_function_extract(self, execute_mumps):
        """$EXTRACT generates string slice (§7.1.5).

        Spec 010 Phase 5 (T031-T034): $EXTRACT extracts substrings by position.
        Uses 1-based indexing with inclusive range.
        """
        # Test 1: Default - first character
        result = execute_mumps('TEST W $E("HELLO") Q')
        assert result.output == "H"

        # Test 2: Single position
        result = execute_mumps('TEST W $E("HELLO",2) Q')
        assert result.output == "E"

        # Test 3: Range extraction
        result = execute_mumps('TEST W $E("HELLO",2,4) Q')
        assert result.output == "ELL"

        # Test 4: Out of range returns empty
        result = execute_mumps('TEST W $E("HELLO",6) Q')
        assert result.output == ""

        # Test 5: Position 0 returns empty
        result = execute_mumps('TEST W $E("HELLO",0) Q')
        assert result.output == ""

        # Test 6: Reverse range (start > end) returns empty
        result = execute_mumps('TEST W $E("HELLO",4,2) Q')
        assert result.output == ""

        # Test 7: Full form abbreviation
        result = execute_mumps('TEST W $EXTRACT("ABC",1,2) Q')
        assert result.output == "AB"

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $FIND codegen")
    def test_function_find(self, generate_python):
        """$FIND generates string find (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $GET codegen")
    def test_function_get(self, generate_python):
        """$GET generates dict.get() equivalent (§7.1.5)."""
        pytest.fail("Stub - implement test")

    def test_function_length(self, execute_mumps):
        """$LENGTH generates len() equivalent (§7.1.5).

        Spec 010 Phase 5 (T024-T026): $LENGTH has two forms:
        1. $L(string) - character count
        2. $L(string, delimiter) - piece count
        """
        # Test 1: Character count
        result = execute_mumps('TEST W $L("HELLO") Q')
        assert result.output == "5"

        # Test 2: Empty string length
        result = execute_mumps('TEST W $L("") Q')
        assert result.output == "0"

        # Test 3: Piece count
        result = execute_mumps('TEST W $L("A^B^C","^") Q')
        assert result.output == "3"

        # Test 4: Empty string has 1 piece
        result = execute_mumps('TEST W $L("","^") Q')
        assert result.output == "1"

        # Test 5: Leading/trailing delimiters count as pieces
        result = execute_mumps('TEST W $L("^A^B^","^") Q')
        assert result.output == "4"

        # Test 6: Full form abbreviation
        result = execute_mumps('TEST W $LENGTH("ABC") Q')
        assert result.output == "3"

    def test_function_order(self, execute_mumps):
        """$ORDER generates next key retrieval (§7.1.5).

        Tests:
        - Forward iteration from empty string
        - Forward iteration from existing key
        - Reverse iteration
        - Global variable support
        - MUMPS collation order (negatives < 0 < positives < strings)
        """
        # Test 1: Forward iteration from empty string - gets first key
        result = execute_mumps(
            'TEST\n S A(1)=1,A(2)=2,A(3)=3\n S X=$O(A(""))\n W X\n Q'
        )
        assert result.output == "1"

        # Test 2: Forward iteration from existing key
        result = execute_mumps("TEST\n S A(1)=1,A(2)=2,A(3)=3\n S X=$O(A(1))\n W X\n Q")
        assert result.output == "2"

        # Test 3: Reverse iteration - gets last key
        result = execute_mumps(
            'TEST\n S A(1)=1,A(2)=2,A(3)=3\n S X=$O(A(""),-1)\n W X\n Q'
        )
        assert result.output == "3"

        # Test 4: Collation order - negatives before positives
        result = execute_mumps(
            'TEST\n S A(-1)=1,A(0)=2,A(1)=3\n S X=$O(A(""))\n W X\n Q'
        )
        assert result.output == "-1"

        # Test 5: Collation order - strings after numbers
        result = execute_mumps('TEST\n S A(1)=1,A("Z")=2\n S X=$O(A(1))\n W X\n Q')
        assert result.output == "Z"

    def test_function_piece(self, execute_mumps):
        """$PIECE generates string split (§7.1.5).

        Spec 010 Phase 5 (T027-T030): $PIECE extracts delimited pieces.
        Uses 1-based indexing.
        """
        # Test 1: Single piece extraction
        result = execute_mumps('TEST W $P("A^B^C","^",2) Q')
        assert result.output == "B"

        # Test 2: Range extraction
        result = execute_mumps('TEST W $P("A^B^C","^",2,3) Q')
        assert result.output == "B^C"

        # Test 3: Out of range returns empty
        result = execute_mumps('TEST W $P("A^B^C","^",4) Q')
        assert result.output == ""

        # Test 4: First piece
        result = execute_mumps('TEST W $P("A^B^C","^",1) Q')
        assert result.output == "A"

        # Test 5: Multi-character delimiter
        result = execute_mumps('TEST W $P("A::B::C","::",2) Q')
        assert result.output == "B"

        # Test 6: Full form abbreviation
        result = execute_mumps('TEST W $PIECE("X-Y-Z","-",2) Q')
        assert result.output == "Y"

    def test_function_query(self, execute_mumps):
        """$QUERY generates tree traversal (§7.1.5).

        Tests:
        - Start from empty string to get first valued node
        - Continue traversal to next valued node
        - Multi-level subscript traversal (depth-first order)
        - End of traversal returns empty string
        """
        # Test 1: Start traversal - gets first valued node
        result = execute_mumps(
            'TEST\n S A(1,1)=1,A(1,2)=2,A(2,1)=3\n S X=$Q(A(""))\n W X\n Q'
        )
        assert result.output == "A(1,1)"

        # Test 2: Continue traversal to sibling
        result = execute_mumps(
            "TEST\n S A(1,1)=1,A(1,2)=2,A(2,1)=3\n S X=$Q(A(1,1))\n W X\n Q"
        )
        assert result.output == "A(1,2)"

        # Test 3: Cross branch boundary
        result = execute_mumps(
            "TEST\n S A(1,1)=1,A(1,2)=2,A(2,1)=3\n S X=$Q(A(1,2))\n W X\n Q"
        )
        assert result.output == "A(2,1)"

        # Test 4: End of traversal returns empty string
        result = execute_mumps("TEST\n S A(1)=1,A(2)=2\n S X=$Q(A(2))\n W X\n Q")
        assert result.output == ""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $RANDOM codegen")
    def test_function_random(self, generate_python):
        """$RANDOM generates random.randint (§7.1.5)."""
        pytest.fail("Stub - implement test")

    def test_function_select(self, execute_mumps):
        """$SELECT generates conditional expression (§7.1.5).

        Spec 010 Phase 3: $SELECT evaluates conditions left-to-right
        and returns the value for the first true condition.
        """
        # Test 1: Basic $SELECT with first condition true
        result = execute_mumps('TEST S X=$S(1=1:"YES",1:"NO") W X Q')
        assert result.output == "YES"

        # Test 2: $SELECT with multiple conditions - second matches
        result = execute_mumps('TEST S X=2 S Y=$S(X=1:"ONE",X=2:"TWO",1:"OTHER") W Y Q')
        assert result.output == "TWO"

        # Test 3: $SELECT with all false except final catch-all
        result = execute_mumps('TEST S Y=$S(0:"A",0:"B",1:"C") W Y Q')
        assert result.output == "C"

        # Test 4: $SELECT with comparison operators
        result = execute_mumps('TEST S A=5,B=3 S Y=$S(A>B:"FIRST",B>A:"SECOND") W Y Q')
        assert result.output == "FIRST"

        # Test 5: $SELECT using abbreviation $S
        result = execute_mumps('TEST S Y=$S(1:"ONLY") W Y Q')
        assert result.output == "ONLY"

    def test_function_select_abbreviation(self, generate_python):
        """$SELECT abbreviation $S generates same code (§7.1.5)."""
        # Both $SELECT and $S should generate the same pattern
        code_full = generate_python('TEST S X=$SELECT(1:"YES") Q')
        code_abbrev = generate_python('TEST S X=$S(1:"YES") Q')

        # Both should contain m_truth for condition check
        assert "m_truth" in code_full
        assert "m_truth" in code_abbrev

    def test_function_select_selectfalse_error(self, generate_python):
        """$SELECT raises SELECTFALSE when no condition is true (§7.1.5).

        Spec 010 Phase 3 T019: $SELECT with no true conditions must raise
        MRuntimeError with SELECTFALSE code.
        """
        from m2py.runtime import MUMPSRuntime

        # Generate code for $SELECT with all false conditions
        code = generate_python('TEST S X=$S(0:"A",0:"B") W X Q')

        # Execute - runtime captures exception as result error
        runtime = MUMPSRuntime()
        result = runtime.execute(code)

        # Check execution failed with SELECTFALSE error
        assert result.success is False
        assert "SELECTFALSE" in result.error

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TEXT codegen")
    def test_function_text(self, generate_python):
        """$TEXT generates source retrieval (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $TRANSLATE codegen")
    def test_function_translate(self, generate_python):
        """$TRANSLATE generates str.translate (§7.1.5)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.pre1995
    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $NEXT codegen (deprecated but supported)"
    )
    def test_function_next(self, generate_python):
        """$NEXT function generates $ORDER equivalent (§7.1.5, pre-1995)."""
        pytest.fail("Stub - implement test")
