"""Compile MUMPS code strings through the full parse→analyze→structure pipeline.

This module provides ``compile_mumps_line``, the single entry-point for
turning a raw MUMPS code string into a list of fully-analysed ASG
statements.  It is used by XECUTE code-generation so that ``codegen/``
never imports parser or analysis internals directly.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Union

if TYPE_CHECKING:
    from m2py.asg.statements import MStatement

from m2py.asg.elements import MParseError


def compile_mumps_line(
    code_str: str,
    context: Optional[object] = None,
) -> Union[list["MStatement"], MParseError]:
    """Run full parse → analyze → structure pipeline for a MUMPS code string.

    Used by XECUTE and any other inline compilation needs.

    Steps:
        1. Parse the MUMPS source text into textX command models.
        2. Analyse each command into an ASG ``MStatement`` node.
        3. Structure flat statement lists into proper control-flow nesting
           (FOR / IF / ELSE body grouping).
        4. Analyse QUIT context so QUITs inside FOR loops generate ``break``
           rather than ``raise _XecuteExit()``.

    Args:
        code_str: MUMPS source code string (single line, no label prefix).
        context: Unused. Accepted for API forward-compatibility.

    Returns:
        A list of analysed ``MStatement`` ASG nodes on success.
        An ``MParseError`` sentinel on parse failure.
        An empty list when *code_str* is empty or whitespace-only.
    """
    from m2py.analysis.for_analysis import analyze_quit_context_for_statements
    from m2py.analysis.semantic_analyzer import analyze_command
    from m2py.parser.line_parser import parse_commands_from_line
    from m2py.parser.parser import _structure_commands_with_bodies

    # Step 1: Parse
    commands = parse_commands_from_line(code_str)
    if isinstance(commands, MParseError):
        return commands

    if not commands:
        return []

    # Step 2: Analyse each textX command → ASG statement
    asg_statements: list[MStatement] = []
    for textx_cmd in commands:
        asg_stmt = analyze_command(textx_cmd, None)
        if asg_stmt is not None:
            asg_statements.append(asg_stmt)

    # Step 3: Structure flat list into proper FOR/IF/ELSE nesting
    structured = _structure_commands_with_bodies(asg_statements)

    # Step 4: Analyse QUIT context (inline XECUTE code doesn't go
    # through routine-level analysis, so we do it here)
    analyze_quit_context_for_statements(structured)

    return structured
