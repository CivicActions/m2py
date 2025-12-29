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
from typing import Optional, Any, List
from functools import lru_cache

from textx import metamodel_from_file
from textx.exceptions import TextXSyntaxError

from ..asg.enums import ForLoopType, ForParamType


@lru_cache(maxsize=1)
def _get_command_metamodel():
    """Get the cached command grammar metamodel with custom classes."""
    from .textx_classes import get_expression_classes

    grammar_dir = Path(__file__).parent.parent / "grammar"
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_expression_classes(), skipws=False
    )


@lru_cache(maxsize=1)
def _get_line_metamodel():
    """Get the cached line content grammar metamodel with custom classes."""
    from .textx_classes import get_expression_classes

    grammar_dir = Path(__file__).parent.parent / "grammar"
    return metamodel_from_file(
        grammar_dir / "line.tx", classes=get_expression_classes(), skipws=False
    )


def parse_line_content(line_content: str) -> Optional[Any]:
    """Parse a MUMPS line content string into a textX model.

    This parses the content after a label or continuation prefix,
    which consists of commands separated by spaces and optionally
    ending with a comment.

    Args:
        line_content: The line content (e.g., "S X=1 W X  ;comment")

    Returns:
        The parsed textX LineContent model or None if parsing fails.

    Error Handling:
        Returns None on parse failure for error-tolerant parsing. textX enforces
        full input consumption by default, raising TextXSyntaxError if any input
        remains unparsed. This function catches that error and returns None,
        allowing partial parsing of files that may contain some invalid lines.

        For stricter error handling, catch the result being None and handle
        accordingly, or use the underlying metamodel directly with try/except.
    """
    mm = _get_line_metamodel()
    try:
        return mm.model_from_str(line_content)
    except TextXSyntaxError:
        return None


def parse_commands_from_line(line_content: str) -> List[Any]:
    """Parse a line content string and return list of command models.

    Args:
        line_content: The line content string

    Returns:
        List of textX command models (empty if parsing fails)
    """
    model = parse_line_content(line_content)
    if model and model.commands:
        return [lc.cmd for lc in model.commands]
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
    commands = parse_commands_from_line(line_content)
    if not commands:
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
    cmds = parse_commands_from_line(line_content)
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
