"""Test helpers for parsing MUMPS commands and expressions.

These utilities provide direct access to textX parsing for unit tests
that need to examine parsed models before semantic analysis.

For production code, use:
- m2py.parser.line_parser.parse_commands_from_line() for parsing full line content
- m2py.analysis.analyze_command() for converting parsed commands to ASG nodes
"""

from typing import Optional, Any
from functools import lru_cache

from textx import metamodel_from_file
from textx.exceptions import TextXSyntaxError
from pathlib import Path

from m2py.parser.textx_classes import get_expression_classes


def _get_grammar_dir() -> Path:
    """Get the path to the grammar directory."""
    return Path(__file__).parent.parent.parent / "src" / "m2py" / "grammar"


@lru_cache(maxsize=1)
def _get_command_metamodel():
    """Get cached command metamodel for parsing single commands."""
    grammar_dir = _get_grammar_dir()
    return metamodel_from_file(
        str(grammar_dir / "commands.tx"),
        classes=get_expression_classes(),
        skipws=False,
    )


@lru_cache(maxsize=1)
def _get_expression_metamodel():
    """Get cached expression metamodel for parsing expressions."""
    grammar_dir = _get_grammar_dir()
    return metamodel_from_file(
        str(grammar_dir / "expressions.tx"),
        classes=get_expression_classes(),
        skipws=False,
    )


def parse_command(command_text: str) -> Optional[Any]:
    """Parse a MUMPS command string into a textX model.

    This is a test utility for parsing single commands. For production
    use, prefer parse_commands_from_line() which handles full line content.

    Args:
        command_text: The command string (e.g., "S X=1" or "W X")

    Returns:
        The parsed textX model or None if parsing fails
    """
    mm = _get_command_metamodel()
    try:
        return mm.model_from_str(command_text, "Command")
    except TextXSyntaxError:
        return None


def parse_expression(expr_text: str) -> Optional[Any]:
    """Parse a MUMPS expression string into a textX model.

    This is a test utility for parsing expressions independently.
    Production code typically gets expressions as part of commands.

    Args:
        expr_text: The expression string (e.g., "X+Y*Z")

    Returns:
        The parsed textX model or None if parsing fails
    """
    mm = _get_expression_metamodel()
    try:
        return mm.model_from_str(expr_text, "Expr")
    except TextXSyntaxError:
        return None
