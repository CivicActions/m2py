"""Shared fixtures for parser-level tests.

Provides fixtures for parsing MUMPS source code at the textX grammar level.
"""

import pytest


@pytest.fixture
def parse_mumps():
    """Fixture providing a function to parse MUMPS source code.

    Returns a function that takes MUMPS source code and returns the parsed AST.
    This is the primary fixture for parser-level tests.

    Usage:
        def test_set_command_parsing(parse_mumps):
            result = parse_mumps("S X=1")
            assert result is not None
    """
    from m2py.parser import MUMPSParser

    parser = MUMPSParser()

    def _parse(source: str, *, rule: str = "routine"):
        """Parse MUMPS source code.

        Args:
            source: MUMPS source code to parse
            rule: Grammar rule to use (default: 'routine')

        Returns:
            Parsed AST node
        """
        return parser.parse(source)

    return _parse


@pytest.fixture
def parse_line():
    """Fixture for parsing a single MUMPS line.

    Usage:
        def test_single_line(parse_line):
            result = parse_line(" S X=1")
            assert result is not None
    """
    from m2py.parser import MUMPSParser

    parser = MUMPSParser()

    def _parse_line(line: str):
        """Parse a single MUMPS line (wraps in minimal routine structure)."""
        # Wrap line in a minimal routine to satisfy grammar
        routine_source = f"TEST\n{line}\n Q"
        return parser.parse(routine_source)

    return _parse_line


@pytest.fixture
def parse_expression():
    """Fixture for parsing a MUMPS expression.

    Usage:
        def test_expression(parse_expression):
            result = parse_expression("1+2*3")
            assert result is not None
    """
    from m2py.parser.line_parser import parse_expression as _parse_expr

    return _parse_expr


@pytest.fixture
def mumps_parser():
    """Fixture providing the MUMPSParser instance directly.

    Use this when you need direct access to parser methods.
    """
    from m2py.parser import MUMPSParser

    return MUMPSParser()
