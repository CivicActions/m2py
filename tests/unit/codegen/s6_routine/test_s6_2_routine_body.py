"""Tests for Routine Body code generation (§6.2).

Reference: MUMPS 1995 ANSI Standard, Section 6.2
"""

import pytest


@pytest.mark.codegen
class TestRoutineBodyCodegen:
    """Codegen-level tests for routine body code generation (§6.2)."""

    def test_label_to_function(self, execute_mumps):
        """Labels generate callable Python functions (§6.2).

        YDB verified: D SUB Q SUB W "SUB" Q → "SUB"
        """
        result = execute_mumps('TEST\n D SUB\n Q\nSUB\n W "SUB"\n Q\n')
        assert result.output == "SUB"
        assert result.success is True

    def test_line_body(self, execute_mumps):
        """Line bodies execute statements in sequence (§6.2).

        YDB verified: S X=1,Y=2 W X,Y Q → "12"
        """
        result = execute_mumps("TEST\n S X=1,Y=2\n W X,Y\n Q\n")
        assert result.output == "12"
        assert result.success is True

    def test_block_structure(self, execute_mumps):
        """Block structure with subroutine calls works correctly (§6.2).

        YDB verified: D A Q A D B Q B W "B" Q → "B"
        """
        result = execute_mumps('TEST\n D A\n Q\nA\n D B\n Q\nB\n W "B"\n Q\n')
        assert result.output == "B"
        assert result.success is True

    def test_comment_preservation(self, generate_python):
        """Comments are preserved in output (§6.2).

        Spec 014 (T067): MUMPS inline comments (;...) are preserved
        as Python comments in the generated code.
        """
        code = generate_python("TEST\n S X=1 ; Initialize X\n W X ; Output\n Q\n")

        # Comments should appear as Python comments before their statements
        assert "# Initialize X" in code
        assert "# Output" in code
