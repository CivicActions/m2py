"""Code generation module for MUMPS-to-Python transpilation.

Provides the public API for generating executable Python code from MUMPS source.
"""

from __future__ import annotations

import ast

from m2py.parser import MUMPSParser
from m2py.codegen.routine import RoutineGenerator


class CodegenError(Exception):
    """Base exception for code generation errors."""

    pass


class UnsupportedFeatureError(CodegenError):
    """Raised when attempting to generate code for unsupported feature."""

    pass


class NameTranslationError(CodegenError):
    """Raised when name translation fails."""

    pass


def generate_python(
    source: str,
    *,
    routine_name: str | None = None,
    validate: bool = True,
) -> str:
    """Generate Python code from MUMPS source.

    Args:
        source: MUMPS source code (single routine)
        routine_name: Optional name for the routine (extracted from source if not provided)
        validate: If True, validate generated code with ast.parse()

    Returns:
        Python source code as a string

    Raises:
        ParseError: If MUMPS source cannot be parsed
        CodegenError: If code generation fails
        SyntaxError: If validate=True and generated code is invalid Python

    Example:
        >>> code = generate_python("TEST S X=1 W X Q")
        >>> print(code)
        from m2py.codegen.helpers import m_num, m_truth, m_compare
        ...
    """
    # Parse MUMPS source
    parser = MUMPSParser()
    routine = parser.parse(source, filename=routine_name)

    # Set routine name if provided
    if routine_name:
        routine.name = routine_name

    # Run analysis passes required for code generation
    # Order matters: references first, then GOTO, FOR, quit context, variables
    parser.resolve_references(routine)
    parser.classify_gotos(routine)
    parser.analyze_for_loops(routine)
    parser.analyze_quit_context(routine)
    parser.analyze_variables(routine, compute_transitive=True)
    parser.compute_signatures(routine)

    # Generate Python code
    generator = RoutineGenerator(routine)
    python_code = generator.generate()

    # Validate if requested
    if validate:
        try:
            ast.parse(python_code)
        except SyntaxError as e:
            raise SyntaxError(
                f"Generated Python code is invalid: {e}\n\nGenerated code:\n{python_code}"
            ) from e

    return python_code


__all__ = [
    "generate_python",
    "CodegenError",
    "UnsupportedFeatureError",
    "NameTranslationError",
]
