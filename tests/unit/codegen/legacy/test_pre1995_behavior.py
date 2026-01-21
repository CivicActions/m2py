"""
Pre-1995 MUMPS Behavior Tests - Code Generation Level.

Tests code generation for deprecated and legacy MUMPS constructs
from the 1977, 1984, and 1990 ANSI standards.

MUMPS Spec Reference:
- $NEXT function: Deprecated in 1995 §7.1.5, replaced by $ORDER
- For complete evolution table, see: specs/002-spec-unit-test-organization/research.md
"""

import pytest

from m2py.parser import MUMPSParser


@pytest.mark.codegen
@pytest.mark.pre1995
class TestNextFunctionBehavior:
    """
    §7.1.5 $NEXT Function code generation (deprecated in 1995).

    Tests verify that $NEXT generates correct Python code that produces
    the same runtime behavior as $ORDER (they are functionally equivalent).
    $NEXT returns -1 when no more subscripts exist, while $ORDER returns "".
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    def test_next_function_codegen(self, parser, generate_python):
        """Verify $NEXT generates code using m_order with -1 wrapper."""
        code_next = "TEST S X=$NEXT(^A(K)) Q"
        code_order = "TEST S X=$ORDER(^A(K)) Q"

        py_next = generate_python(code_next)
        py_order = generate_python(code_order)

        # $NEXT wraps m_order_global in lambda that converts "" to -1
        assert "m_order_global" in py_next
        assert "lambda" in py_next and "-1" in py_next
        # $ORDER uses m_order_global directly
        assert "m_order_global" in py_order

    def test_next_function_runtime_behavior(self, execute_mumps):
        """Verify $NEXT produces correct runtime behavior.

        $NEXT traverses sparse array and returns -1 at end.
        """
        # Test first subscript
        result = execute_mumps('TEST S ^A(1)="a",^A(3)="c",^A(5)="e" W $N(^A("")) Q')
        assert result.output.strip() == "1"

        # Test middle subscript
        result = execute_mumps('TEST S ^A(1)="a",^A(3)="c",^A(5)="e" W $N(^A(1)) Q')
        assert result.output.strip() == "3"

        # Test end returns -1
        result = execute_mumps('TEST S ^A(1)="a",^A(3)="c",^A(5)="e" W $N(^A(5)) Q')
        assert result.output.strip() == "-1"

    def test_next_abbreviated_form(self, execute_mumps):
        """Verify $N abbreviation works correctly."""
        # $N is the abbreviated form of $NEXT
        result = execute_mumps('TEST S X(1)="a",X(3)="c" W $N(X("")) Q')
        assert result.output.strip() == "1"

        result = execute_mumps('TEST S X(1)="a",X(3)="c" W $N(X(3)) Q')
        assert result.output.strip() == "-1"


@pytest.mark.codegen
@pytest.mark.pre1995
class TestPre1984CodeGeneration:
    """
    Test code generation for pre-1984 MUMPS patterns.

    Before 1984, code relied on:
    - Global variable scope (no NEW command)
    - $NEXT for array traversal
    - No formal parameters
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    def test_legacy_variable_scope_codegen(self, execute_mumps):
        """Verify codegen handles code without NEW correctly.

        Pre-1984 MUMPS used global variable scope. Variables are visible
        across subroutine calls without explicit NEW/KILL.
        """
        # Pre-1984 code used manual variable cleanup
        # TMP should be accessible in both routines (global scope)
        result = execute_mumps("""TEST
 S X=1
 D SUB
 K TMP
 W X
 Q
SUB
 S TMP=X*2
 S X=TMP
 Q""")
        assert result.output.strip() == "2"


@pytest.mark.codegen
@pytest.mark.pre1995
class TestPre1990CodeGeneration:
    """
    Test code generation for pre-1990 MUMPS patterns.

    Before 1990, code relied on:
    - FOR loops for array copying (no MERGE)
    - String manipulation without $TRANSLATE/$REVERSE
    """

    @pytest.fixture
    def parser(self):
        """Provide parser instance."""
        return MUMPSParser()

    def test_legacy_array_copy_codegen(self, execute_mumps):
        """Verify codegen handles manual array copy pattern.

        Pre-1990 MUMPS used FOR loops with $ORDER to copy arrays
        since MERGE command wasn't available.
        """
        # Test that array copy pattern works
        result = execute_mumps("""TEST
 S ^SRC(1)="a",^SRC(3)="c"
 S K="" F  S K=$O(^SRC(K)) Q:K=""  S ^DST(K)=^SRC(K)
 W ^DST(1),^DST(3)
 Q""")
        assert result.output.strip() == "ac"
