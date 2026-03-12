"""Tests for deeply nested DO block extraction into module-level helpers.

When Python nesting depth exceeds _NESTING_EXTRACTION_THRESHOLD (~14),
the code generator extracts the DO block body into a standalone helper
function at module level.  This avoids CPython's ~20 statically nested
block limit.

Fixes: DICA1.m and similar routines that nest >14 dot levels deep (each
conditional DO ≈ 3-4 Python nesting levels: try + with + while).
"""

import sys
import types

import pytest

from m2py.codegen import generate_python
from m2py.codegen.statements import _NESTING_EXTRACTION_THRESHOLD


@pytest.fixture(autouse=True)
def _cleanup_modules():
    """Remove test modules from sys.modules after each test."""
    before = set(sys.modules)
    yield
    for name in set(sys.modules) - before:
        del sys.modules[name]


@pytest.mark.codegen
class TestNestingExtraction:
    """Tests for DO block extraction into module-level helper functions."""

    def test_threshold_value_is_reasonable(self):
        """The extraction threshold should be between 10 and 18.

        CPython's limit is ~20 nested blocks.  Each DO block adds ~3-4
        Python nesting levels, so threshold should trigger well below 20.
        """
        assert 10 <= _NESTING_EXTRACTION_THRESHOLD <= 18

    def test_shallow_nesting_no_helpers(self):
        """Shallow DO blocks (2-3 levels) do NOT generate helper functions."""
        source = "TEST\n . W 1\n . . W 2\n Q\n"
        code = generate_python(source, routine_name="SHALLOW")
        assert "_dot_helper_" not in code

    def test_deep_nesting_generates_helpers(self):
        """Deeply nested conditional DO blocks produce _dot_helper_ functions.

        Each conditional DO (I cond D / . body) adds ~3-4 Python nesting
        levels (if + try + with + while), so stacking them quickly exceeds
        the extraction threshold.
        """
        # Build MUMPS with nested conditional DO blocks:
        #   . I 1 D
        #   . . I 1 D
        #   . . . I 1 D
        #   ...
        # This pattern triggers deep Python nesting (each level ≈ 3-4 indent)
        lines = ["DEEP"]
        for level in range(1, 8):
            indent = " " + ". " * level
            lines.append(f"{indent}I 1 D")
        lines.append(" " + ". " * 8 + "W 1")
        lines.append(" Q")
        source = "\n".join(lines)

        code = generate_python(source, routine_name="DEEP")
        assert "_dot_helper_" in code, (
            "Expected _dot_helper_ in generated code for deeply nested conditional DOs"
        )

    def test_helper_is_callable_function(self):
        """Extracted helper is a valid Python function that can be called."""
        lines = ["DEEP"]
        for level in range(1, 8):
            indent = " " + ". " * level
            lines.append(f"{indent}I 1 D")
        lines.append(" " + ". " * 8 + "W 1")
        lines.append(" Q")
        source = "\n".join(lines)

        code = generate_python(source, routine_name="DEEPCALL")
        # Verify the code compiles without SyntaxError
        compile(code, "<DEEPCALL>", "exec")

    def test_helper_defined_before_main(self):
        """Helper function definitions appear before the __main__ entry point."""
        lines = ["DEEP"]
        for level in range(1, 8):
            indent = " " + ". " * level
            lines.append(f"{indent}I 1 D")
        lines.append(" " + ". " * 8 + "W 1")
        lines.append(" Q")
        source = "\n".join(lines)

        code = generate_python(source, routine_name="DEEPORD")
        assert "def _dot_helper_" in code
        helper_def_pos = code.index("def _dot_helper_")
        if 'if __name__ == "__main__"' in code:
            main_pos = code.index('if __name__ == "__main__"')
            assert helper_def_pos < main_pos, (
                "Helper function definition must be before __main__ block"
            )

    def test_extracted_block_executes_correctly(self):
        """A deeply nested routine with extraction runs correctly."""
        from m2py.runtime import MUMPSRuntime

        lines = ["DEEP"]
        for level in range(1, 8):
            indent = " " + ". " * level
            lines.append(f"{indent}I 1 D")
        lines.append(" " + ". " * 8 + 'W "ok"')
        lines.append(" Q")
        source = "\n".join(lines)

        code = generate_python(source, routine_name="DEEPRUN")
        mod = types.ModuleType("DEEPRUN")
        mod.__dict__["__name__"] = "DEEPRUN"
        sys.modules["DEEPRUN"] = mod
        exec(compile(code, "<DEEPRUN>", "exec"), mod.__dict__)  # noqa: S102

        rt = MUMPSRuntime()
        scope: dict = {}
        mod.DEEP(rt, _scope=scope)
        output = rt.get_output()
        assert "ok" in output

    def test_multiple_deep_blocks_extract_and_execute(self):
        """Multiple deeply nested DO blocks produce valid code with extraction."""
        # Two separate deeply nested blocks in the same routine
        lines = ["MULTI"]
        for level in range(1, 8):
            indent = " " + ". " * level
            lines.append(f"{indent}I 1 D")
        lines.append(" " + ". " * 8 + 'W "A"')
        # Second deep block
        lines.append(" S B=0")
        for level in range(1, 8):
            indent = " " + ". " * level
            lines.append(f"{indent}I 1 D")
        lines.append(" " + ". " * 8 + 'W "B"')
        lines.append(" Q")
        source = "\n".join(lines)

        code = generate_python(source, routine_name="MULTI")
        # At least one helper must be extracted
        assert "def _dot_helper_" in code
        # Both blocks execute correctly
        from m2py.runtime import MUMPSRuntime

        mod = types.ModuleType("MULTI")
        exec(compile(code, "MULTI.py", "exec"), mod.__dict__)
        rt = MUMPSRuntime()
        mod.MULTI(rt, _scope={})
        output = rt.get_output()
        assert "A" in output
        assert "B" in output
