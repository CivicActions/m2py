"""Shared fixtures for codegen-level tests.

Provides fixtures for testing Python code generation and execution.
"""

from pathlib import Path

import pytest


@pytest.fixture
def generate_python():
    """Fixture providing a function to generate Python from MUMPS source.

    Usage:
        def test_set_codegen(generate_python):
            python_code = generate_python("TEST\\n S X=1\\n Q")
            assert "X = " in python_code
    """
    from m2py.codegen import generate_python as _generate

    def _gen(source: str, *, routine_name: str | None = None) -> str:
        """Generate Python code from MUMPS source."""
        return _generate(source, routine_name=routine_name)

    return _gen


@pytest.fixture
def execute_mumps():
    """Fixture for parsing, generating, and executing MUMPS code.

    Returns a function that takes MUMPS source and returns execution result.

    Usage:
        def test_set_executes(execute_mumps):
            result = execute_mumps("TEST\\n S X=1\\n W X\\n Q")
            assert result.output == "1"
    """
    from m2py.codegen import generate_python
    from m2py.runtime import MUMPSRuntime

    def _execute(source: str, *, capture_output: bool = True):
        """Execute MUMPS source and return result."""
        python_code = generate_python(source)
        runtime = MUMPSRuntime()
        return runtime.execute(python_code, capture_output=capture_output)

    return _execute


@pytest.fixture
def compare_output_to_functional_suite():
    """Fixture for comparing codegen output against functional test suite baselines.

    This satisfies FR-029: codegen tests must reference YDBTest functional suites.

    Usage:
        def test_v1fora_output(compare_output_to_functional_suite, execute_mumps):
            result = execute_mumps(mumps_source)
            compare_output_to_functional_suite("V1FORA", result.output)
    """
    # Base path for functional test suites
    functional_base = Path(__file__).parent.parent.parent / "functional"

    # Output reference directories
    outref_dirs = {
        "mugj": functional_base / "mugj" / "outref",
    }

    def _compare(routine_name: str, actual_output: str, *, suite: str = "mugj") -> bool:
        """Compare actual output against expected baseline.

        Args:
            routine_name: Name of the routine (e.g., "V1FORA")
            actual_output: The actual output from code execution
            suite: Which test suite to check against (default: "mugj")

        Returns:
            True if output matches baseline, raises AssertionError otherwise
        """
        outref_dir = outref_dirs.get(suite)
        if not outref_dir:
            raise ValueError(f"Unknown test suite: {suite}")

        # Try common extensions
        for ext in [".txt", ".mjo", ""]:
            baseline_path = outref_dir / f"{routine_name}{ext}"
            if baseline_path.exists():
                expected = baseline_path.read_text(encoding="utf-8", errors="replace")
                assert actual_output.strip() == expected.strip(), (
                    f"Output mismatch for {routine_name}:\nExpected:\n{expected}\n\nActual:\n{actual_output}"
                )
                return True

        raise FileNotFoundError(f"No baseline found for {routine_name} in {outref_dir}")

    return _compare


@pytest.fixture
def validate_python_syntax():
    """Fixture to validate generated Python code is syntactically correct.

    Usage:
        def test_generated_syntax(generate_python, validate_python_syntax):
            code = generate_python(mumps_source)
            validate_python_syntax(code)  # Raises SyntaxError if invalid
    """
    import ast

    def _validate(python_code: str) -> bool:
        """Validate Python code syntax.

        Raises SyntaxError if code is invalid.
        Returns True if valid.
        """
        ast.parse(python_code)
        return True

    return _validate


@pytest.fixture
def execute_expr(execute_mumps):
    """Fixture for executing a single MUMPS expression/command.

    Auto-wraps the code in a routine label, reducing boilerplate for simple tests.
    Ideal for testing expressions, operators, and single commands.

    Usage:
        def test_addition(execute_expr):
            assert execute_expr('W 1+2') == "3"

        @pytest.mark.parametrize("expr,expected", [
            ("1+2", "3"),
            ('"A"_"B"', "AB"),
        ])
        def test_expressions(execute_expr, expr, expected):
            assert execute_expr(f'W {expr}') == expected
    """

    def _execute_expr(code: str) -> str:
        """Execute a single MUMPS command and return output.

        Args:
            code: A single MUMPS command (e.g., 'W 1+2' or 'S X=1 W X')

        Returns:
            The output string (stripped of trailing whitespace)
        """
        # Wrap in minimal routine: label + code + quit
        source = f"_EXPR\n {code}\n Q\n"
        result = execute_mumps(source)
        return result.output.rstrip()

    return _execute_expr


@pytest.fixture
def eval_mumps(execute_mumps):
    """Fixture for evaluating a MUMPS expression and returning its value.

    Unlike execute_expr which captures WRITE output, this evaluates an expression
    and returns the result as a Python value. Useful for testing expression
    evaluation without needing WRITE.

    Usage:
        def test_arithmetic(eval_mumps):
            assert eval_mumps('1+2') == "3"
            assert eval_mumps('$L("ABC")') == "3"

        def test_string_concat(eval_mumps):
            assert eval_mumps('"Hello"_" "_"World"') == "Hello World"
    """

    def _eval_mumps(expr: str) -> str:
        """Evaluate a MUMPS expression and return its value.

        Args:
            expr: A MUMPS expression (e.g., '1+2', '$L("ABC")', '"A"_"B"')

        Returns:
            The expression result as a string (MUMPS canonical form)
        """
        # Use % as temp variable, write it, return via QUIT
        source = f"EVAL\n S %=({expr})\n W %\n Q\n"
        result = execute_mumps(source)
        return result.output.rstrip()

    return _eval_mumps
