"""textX-based MUMPS line parsing infrastructure.

This module provides low-level parsing using textX grammars to convert MUMPS
line content into textX model objects. These models can then be analyzed by
the SemanticAnalyzer to produce full ASG nodes.

**Parsing Functions** (primary API):
- `parse_line_content()` - Parse line text → textX LineContent model
- `parse_commands_from_line()` - Parse line text → list of command models

**FOR Loop Utilities**:
- `extract_for_commands()` - Extract FOR commands from a line
- `classify_for_command()` - Classify FOR loop type (bounded, open-ended, etc.)
- `detect_quit_after_for()` - Check if QUIT follows FOR on the same line

**Internal**:
- `_get_command_metamodel()` - Cached textX metamodel for commands.tx
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

from ..asg.enums import ForLoopType, ForParamType


@lru_cache(maxsize=1)
def _get_command_metamodel():
    """Get the cached command grammar metamodel with custom classes."""
    from .textx_classes import get_all_classes

    grammar_dir = Path(__file__).parent.parent / "grammar"
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


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


def detect_quit_after_for(line_content: str) -> bool:
    """Detect if there's a QUIT command after any FOR command on this line.

    In MUMPS, FOR body extends to end of line. If QUIT appears after FOR
    on the same line, it's an exit point for the FOR loop.

    Args:
        line_content: The line content string

    Returns:
        True if QUIT found after FOR, False otherwise
    """
    from m2py.asg.elements import MParseError

    commands = parse_commands_from_line(line_content)
    if not commands or isinstance(commands, MParseError):
        return False

    found_for = False
    for cmd in commands:
        cls_name = cmd.__class__.__name__
        if cls_name == "ForCommand":
            found_for = True
        elif found_for and cls_name == "QuitCommand":
            return True

    return False


def extract_for_commands(line_content: str) -> List[Any]:
    """Extract all FOR commands from a line content string.

    Uses textX grammar to properly parse and identify FOR commands,
    avoiding false positives from string literals or other contexts.

    Args:
        line_content: The line content string

    Returns:
        List of ForCommand textX models found in the line
    """
    from m2py.asg.elements import MParseError

    cmds = parse_commands_from_line(line_content)
    if isinstance(cmds, MParseError):
        return []
    return [cmd for cmd in cmds if cmd.__class__.__name__ == "ForCommand"]


def classify_for_command(for_cmd) -> tuple:
    """Classify a textX ForCommand into loop type and variable.

    Args:
        for_cmd: A textX ForCommand model

    Returns:
        Tuple of (ForLoopType, loop_var) where loop_var is a string (simple var)
        or LocalVariable (subscripted var) or ""
    """
    # Argumentless FOR: no var or params
    if not for_cmd.var or not for_cmd.params:
        return ForLoopType.ARGUMENTLESS, ""

    # For simple variables, return the string name; for subscripted, return the object
    if for_cmd.var.subscripts:
        loop_var = for_cmd.var
    else:
        loop_var = for_cmd.var.name

    # Analyze parameters to determine loop type
    param_types = []
    for param in for_cmd.params:
        if param.step:
            if param.end:
                param_types.append(ForParamType.RANGE)
            else:
                param_types.append(ForParamType.OPEN_RANGE)
        else:
            param_types.append(ForParamType.VALUE)

    # Determine overall loop type
    if not param_types:
        return ForLoopType.ARGUMENTLESS, loop_var

    unique_types = set(param_types)

    if len(for_cmd.params) > 1 and len(unique_types) > 1:
        return ForLoopType.MIXED, loop_var

    if ForParamType.RANGE in unique_types:
        return ForLoopType.BOUNDED, loop_var
    elif ForParamType.OPEN_RANGE in unique_types:
        return ForLoopType.OPEN_ENDED, loop_var
    else:
        return ForLoopType.STRING_LIST, loop_var
