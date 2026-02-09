"""Shared fixtures for ASG-level tests.

Provides fixtures for semantic analysis at the ASG (Abstract Semantic Graph) level.
"""

import pytest


@pytest.fixture
def analyze_routine():
    """Fixture providing a function to parse and analyze a MUMPS routine.

    Returns the analyzed MRoutine ASG node with all semantic analysis complete.

    Usage:
        def test_set_variable_binding(analyze_routine):
            routine = analyze_routine("TEST\\n S X=1\\n Q")
            # Examine ASG nodes...
    """
    from m2py.parser import MUMPSParser

    parser = MUMPSParser()

    def _analyze(source: str):
        """Parse and analyze MUMPS source, returning the MRoutine ASG."""
        return parser.parse(source)

    return _analyze


@pytest.fixture
def analyze_expression():
    """Fixture for analyzing individual MUMPS expressions.

    Usage:
        def test_binary_operation_analysis(analyze_expression):
            result = analyze_expression("1+2*3")
            assert result.operator == "+"
    """
    from m2py.analysis.semantic_analyzer import (
        analyze_expression as _analyze_expr,
    )

    return _analyze_expr


@pytest.fixture
def analyze_statement():
    """Fixture for analyzing a single MUMPS statement.

    Wraps the statement in a minimal routine and extracts the analyzed statement.

    Usage:
        def test_set_statement_analysis(analyze_statement):
            stmt = analyze_statement("S X=1")
            assert stmt.assignments[0].target.name == "X"
    """
    from m2py.parser import MUMPSParser

    parser = MUMPSParser()

    def _analyze_statement(stmt_text: str):
        """Parse a statement and return the first non-label statement."""
        # Wrap in minimal routine
        source = f"TEST\n {stmt_text}\n Q"
        routine = parser.parse(source)
        # Return first statement from second line (after label)
        if routine.body and len(routine.body) > 1:
            line = routine.body[1]
            if hasattr(line, "commands") and line.commands:
                return line.commands[0]
        return None

    return _analyze_statement


@pytest.fixture
def resolve_refs():
    """Fixture for resolving references within a routine.

    Usage:
        def test_call_resolution(resolve_refs, analyze_routine):
            routine = analyze_routine("TEST\\n D SUB\\nSUB\\n Q")
            resolve_refs(routine)
            # Now calls have resolved targets
    """
    from m2py.analysis import resolve_references

    return resolve_references
