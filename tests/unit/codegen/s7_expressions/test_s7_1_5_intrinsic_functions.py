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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $EXTRACT codegen")
    def test_function_extract(self, generate_python):
        """$EXTRACT generates string slice (§7.1.5)."""
        pytest.fail("Stub - implement test")

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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $LENGTH codegen")
    def test_function_length(self, generate_python):
        """$LENGTH generates len() equivalent (§7.1.5)."""
        pytest.fail("Stub - implement test")

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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $PIECE codegen")
    def test_function_piece(self, generate_python):
        """$PIECE generates string split (§7.1.5)."""
        pytest.fail("Stub - implement test")

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

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $SELECT codegen")
    def test_function_select(self, generate_python):
        """$SELECT generates conditional expression (§7.1.5)."""
        pytest.fail("Stub - implement test")

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
