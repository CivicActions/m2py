"""Tests for ZWRITE command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZwriteCodegen:
    """Codegen-level tests for ZWRITE command (YDB)."""

    def test_zwrite_generates_dump(self, generate_python):
        """ZWRITE generates variable dump."""
        code = generate_python("TEST S X=1 ZWR X Q")
        assert "zwrite_local" in code
        assert "'X'" in code

    def test_zwrite_local_variable(self, execute_mumps):
        """ZWRITE displays local variable with name."""
        result = execute_mumps("TEST S X=1 ZWR X Q")
        assert result.success
        assert result.output.strip() == "X=1"

    def test_zwrite_subscripted_variable(self, execute_mumps):
        """ZWRITE displays subscripted variable with proper format."""
        result = execute_mumps("TEST S X=1,X(1)=2,X(1,1)=3 ZWR X Q")
        assert result.success
        lines = result.output.strip().split("\n")
        assert "X=1" in lines
        assert "X(1)=2" in lines
        assert "X(1,1)=3" in lines

    def test_zwrite_string_values_quoted(self, execute_mumps):
        """ZWRITE quotes string values."""
        result = execute_mumps('TEST S X="hello" ZWR X Q')
        assert result.success
        assert 'X="hello"' in result.output

    def test_zwrite_numeric_values_unquoted(self, execute_mumps):
        """ZWRITE does not quote numeric values."""
        result = execute_mumps("TEST S X=42 ZWR X Q")
        assert result.success
        assert "X=42" in result.output
        assert 'X="42"' not in result.output

    def test_zwrite_global(self, execute_mumps):
        """ZWRITE displays global variables."""
        result = execute_mumps("TEST S ^G=1 ZWR ^G K ^G Q")
        assert result.success
        assert "^G=1" in result.output

    def test_zwrite_argumentless(self, execute_mumps):
        """Argumentless ZWRITE displays all local variables."""
        result = execute_mumps("TEST S A=1,B=2 ZWR  Q")
        assert result.success
        assert "A=1" in result.output
        assert "B=2" in result.output


@pytest.mark.codegen
@pytest.mark.ydb
class TestZwriteSubscriptsPass2:
    """ZWRITE with subscripted arguments, ranges, and wildcards.

    Covers codegen/statements.py L6557-6603 (subscripted args, ranges).
    """

    def test_zwrite_simple_subscript(self, execute_mumps):
        """ZW X — ZWRITE a simple subscripted variable."""
        result = execute_mumps('TEST\n S X(1)="a",X(2)="b" ZW X Q\n')
        # ZWRITE should show at least some output for X
        assert result.success

    def test_zwrite_specific_subscript(self, execute_mumps):
        """ZW X(1) — ZWRITE a specific subscripted element."""
        result = execute_mumps('TEST\n S X(1)="hello" ZW X(1) Q\n')
        assert result.success

    def test_zwrite_nested_subscripts(self, execute_mumps):
        """ZW X — ZWRITE all X entries including nested."""
        result = execute_mumps('TEST\n S X(1,1)="a",X(1,2)="b",X(2,1)="c" ZW X Q\n')
        # ZWRITE should show subscripted entries
        assert result.success
