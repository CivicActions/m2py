"""Dead code detection and unreachable code analysis.

This module provides analysis functions for detecting dead code and
unreachable statements in MUMPS source code.
"""

from typing import List, Tuple

from m2py.parser.line_parser import parse_commands_from_line


def detect_unreachable_code(lines: List[str]) -> List[Tuple[int, str]]:
    """Detect unreachable code after unconditional GOTO or QUIT using textX.

    Scans a list of MUMPS lines and identifies lines that cannot be
    reached because they follow an unconditional GOTO or QUIT command.

    Args:
        lines: List of MUMPS source lines

    Returns:
        List of (line_number, reason) tuples for unreachable lines
        Line numbers are 1-indexed
    """
    unreachable = []
    after_unconditional_exit = False
    unconditional_exit_line = 0

    for i, line in enumerate(lines, start=1):
        line_stripped = line.strip()

        # Skip empty lines and comment lines
        if not line_stripped or line_stripped.startswith(";"):
            continue

        # Check if this is a label line (starts with non-space)
        # Labels reset reachability since they can be GOTO targets
        if line and line[0] not in " \t":
            after_unconditional_exit = False
            continue

        # If we're after an unconditional exit, this code is unreachable
        if after_unconditional_exit:
            unreachable.append(
                (
                    i,
                    f"unreachable after unconditional exit on line {unconditional_exit_line}",
                )
            )
            continue

        # Parse commands from the line
        cmds = parse_commands_from_line(line_stripped)
        if not cmds:
            continue

        # Check the last command on the line
        last_cmd = cmds[-1]
        cmd_name = last_cmd.__class__.__name__

        # Check for unconditional GOTO
        if cmd_name == "GotoCommand":
            # Unconditional if no postcondition
            if not hasattr(last_cmd, "postcond") or not last_cmd.postcond:
                # Also check if targets have postconditions
                has_postcond = False
                if hasattr(last_cmd, "targets"):
                    for target in last_cmd.targets:
                        if hasattr(target, "postcond") and target.postcond:
                            has_postcond = True
                            break
                if not has_postcond:
                    after_unconditional_exit = True
                    unconditional_exit_line = i
                    continue

        # Check for unconditional QUIT
        if cmd_name == "QuitCommand":
            # Unconditional if no postcondition
            if not hasattr(last_cmd, "postcond") or not last_cmd.postcond:
                after_unconditional_exit = True
                unconditional_exit_line = i
                continue

    return unreachable
