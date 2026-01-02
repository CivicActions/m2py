"""Shared fixtures for analysis tests.

Provides fixtures for testing internal analysis algorithms (not spec-aligned).
These tests verify the correctness of classifiers, resolvers, and other
internal analysis functions.
"""

import pytest


@pytest.fixture
def classify_for():
    """Fixture for classifying FOR loop types.

    Usage:
        def test_for_bounded(classify_for):
            loop_type = classify_for(for_node)
            assert loop_type == ForLoopType.BOUNDED
    """
    from m2py.analysis.for_classifier import classify_for_loop

    return classify_for_loop


@pytest.fixture
def classify_goto():
    """Fixture for classifying GOTO types.

    Usage:
        def test_goto_label(classify_goto):
            goto_type = classify_goto(goto_node)
            assert goto_type == GotoType.LABEL
    """
    from m2py.analysis.goto_classifier import classify_goto

    return classify_goto


@pytest.fixture
def extract_variables():
    """Fixture for extracting variables from expressions/statements.

    Usage:
        def test_variable_extraction(extract_variables):
            vars = extract_variables(statement)
            assert "X" in vars
    """
    from m2py.analysis.variables import (
        extract_expression_variables,
        extract_statement_variables,
    )

    return {
        "expression": extract_expression_variables,
        "statement": extract_statement_variables,
    }


@pytest.fixture
def analyze_variables():
    """Fixture for full variable analysis on a routine.

    Usage:
        def test_variable_analysis(analyze_variables, analyze_routine):
            routine = analyze_routine(source)
            result = analyze_variables(routine)
            assert "X" in result.input_variables
    """
    from m2py.analysis.variables import analyze_variables as _analyze

    return _analyze


@pytest.fixture
def resolve_references():
    """Fixture for resolving label/call references.

    Usage:
        def test_resolve(resolve_references, analyze_routine):
            routine = analyze_routine(source)
            resolve_references(routine)
            # References are now resolved
    """
    from m2py.analysis import resolve_references as _resolve

    return _resolve
