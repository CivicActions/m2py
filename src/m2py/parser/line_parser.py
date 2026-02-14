"""textX-based MUMPS line parsing infrastructure.

This module provides low-level parsing using textX grammars to convert MUMPS
line content into textX model objects. These models can then be analyzed by
``analyze_command()`` in ``semantic_analyzer.py`` to produce full ASG nodes.

**Parsing Functions** (primary API):
- `parse_line_content()` - Parse line text → textX LineContent model
- `parse_commands_from_line()` - Parse line text → list of command models

**Internal**:
- `_get_line_metamodel()` - Cached textX metamodel for line.tx

For ASG construction from parsed commands, use the SemanticAnalyzer which
converts textX models into full-fidelity ASG nodes with proper typing and
parent relationships.

Test utilities for parsing single commands/expressions are in tests/helpers/parsing.py.
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, List
from functools import lru_cache

if TYPE_CHECKING:
    from m2py.asg.elements import MParseError

from textx import metamodel_from_file
from textx.exceptions import TextXSyntaxError


@lru_cache(maxsize=1)
def _get_line_metamodel():
    """Get the cached line content grammar metamodel with custom classes."""
    from .textx_classes import get_all_classes

    grammar_dir = Path(__file__).parent.parent / "grammar"
    return metamodel_from_file(
        grammar_dir / "line.tx", classes=get_all_classes(), skipws=False
    )


def parse_line_content(
    line_content: str, line_number: int = 0
) -> "Any | MParseError | None":
    """Parse a MUMPS line content string into a textX model.

    This parses the content after a label or continuation prefix,
    which consists of commands separated by spaces and optionally
    ending with a comment.

    Args:
        line_content: The line content (e.g., "S X=1 W X  ;comment")
        line_number: Optional line number for error reporting (0 if unknown)

    Returns:
        - The parsed textX LineContent model on success
        - MParseError on parse failure (with error details)
        - None for empty/whitespace-only lines (not an error)

    Error Handling:
        Returns MParseError on parse failure for error-tolerant parsing. textX
        enforces full input consumption by default, raising TextXSyntaxError if
        any input remains unparsed. This function catches that error and returns
        an MParseError, allowing partial parsing of files while preserving error
        information for later reporting.

        MUMPSUnknownCommandError is also caught and converted to MParseError for
        unknown commands that don't match any recognized MUMPS command pattern.

        None is returned only for empty/whitespace lines which are not errors.
    """
    from m2py.asg.elements import MParseError
    from m2py.parser.exceptions import MUMPSUnknownCommandError

    # Empty or whitespace-only lines are not errors
    if not line_content or not line_content.strip():
        return None

    mm = _get_line_metamodel()
    try:
        return mm.model_from_str(line_content)
    except TextXSyntaxError as e:
        # Extract position info from textX exception
        col = getattr(e, "col", 0) or 0
        msg = str(e)
        # Clean up the message (remove file path prefix if present)
        if ": " in msg:
            msg = msg.split(": ", 1)[-1]
        return MParseError(
            line_number=line_number,
            column=col,
            message=msg,
            line_content=line_content,
        )
    except MUMPSUnknownCommandError as e:
        # Unknown command - convert to MParseError for error-tolerant parsing
        return MParseError(
            line_number=line_number,
            column=e.column or 0,
            message=str(e),
            line_content=line_content,
        )


def parse_commands_from_line(
    line_content: str, line_number: int = 0
) -> "List[Any] | MParseError":
    """Parse a line content string and return list of command models.

    Args:
        line_content: The line content string
        line_number: Optional line number for error reporting (0 if unknown)

    Returns:
        List of textX command models on success, or MParseError on failure.
        Empty list for empty/whitespace lines (not an error).
    """
    from m2py.asg.elements import MParseError

    result = parse_line_content(line_content, line_number)

    # Propagate parse errors
    if isinstance(result, MParseError):
        return result

    # Empty line or parse returned None (whitespace only)
    if result is None:
        return []

    # Extract commands from parsed model
    if hasattr(result, "commands") and result.commands:
        return [lc.cmd for lc in result.commands]
    return []


def extract_comment(source_line: str) -> str:
    """Extract comment text from a MUMPS source line.

    Finds the first semicolon not inside a string literal and returns
    the text after it (stripped of leading/trailing whitespace).

    MUMPS comments start with an unquoted semicolon (;). Semicolons
    inside quoted strings ("hello;world") are NOT comment delimiters.

    Args:
        source_line: Original MUMPS source line

    Returns:
        Comment text without the leading semicolon, or empty string if no comment
    """
    in_string = False
    for i, char in enumerate(source_line):
        if char == '"':
            in_string = not in_string
        elif char == ";" and not in_string:
            # Found unquoted semicolon - rest is comment
            return source_line[i + 1 :].strip()
    return ""
