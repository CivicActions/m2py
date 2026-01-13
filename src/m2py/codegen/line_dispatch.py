"""Line dispatch utilities for computed offset support (Spec 007).

This module provides:
- Line map generation: builds `_line_map` from source lines to (label, offset) tuples
- Offset detection: checks if a routine contains offset calls
- Next executable finding: handles non-executable line targets

The line map enables GOTO/DO with computed offsets (e.g., `G LABEL+N`) by
mapping source line numbers to label entry points with offset positions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Optional, Tuple

if TYPE_CHECKING:
    from m2py.asg.elements import MRoutine
    from m2py.codegen.emitter import CodeEmitter


def has_offset_calls(routine: "MRoutine") -> bool:
    """Check if routine contains any offset calls (GOTO/DO with offsets).

    Traverses all labels and their statements to find any MCall with
    a non-None offset field.

    Args:
        routine: The MRoutine to check

    Returns:
        True if any offset call is found, False otherwise
    """
    from m2py.asg.statements import MGotoStatement, MDoStatement

    for label in routine.labels:
        if label.body:
            for stmt in label.body.walk_statements():
                # Check GOTO statements
                if isinstance(stmt, MGotoStatement):
                    for target in stmt.targets:
                        if target.offset is not None:
                            return True
                # Check DO statements
                elif isinstance(stmt, MDoStatement):
                    for target in stmt.targets:
                        if target.offset is not None:
                            return True
    return False


def generate_line_map(routine: "MRoutine") -> Dict[int, Tuple[str, int]]:
    """Build source line → (label_name, offset_within_label) mapping.

    Creates a dictionary mapping each executable source line number to
    a tuple of (label_name, offset). The offset is calculated as the
    difference between the statement's line number and the label's line
    number: offset = stmt.line_number - label.line_number.

    This means:
    - offset 0 = label line itself (may contain inline commands)
    - offset 1 = first line after the label line
    - offset 2 = second line after the label line

    Only includes lines that have executable content (excludes comments
    and blank lines).

    Args:
        routine: The MRoutine to generate line map for

    Returns:
        Dict mapping line_number → (label_name, offset_within_label)

    Example:
        For source:
            STAR W "0"     ; Line 1 (label line)
             W "1"         ; Line 2
             W "2"         ; Line 3
             Q             ; Line 4

        Returns:
            {1: ("STAR", 0), 2: ("STAR", 1), 3: ("STAR", 2), 4: ("STAR", 3)}
    """
    line_map: Dict[int, Tuple[str, int]] = {}

    for label in routine.labels:
        label_name = label.name
        label_line = label.line_number

        if label_line is None:
            continue

        # Label line itself is offset 0
        line_map[label_line] = (label_name, 0)

        # Add statements with their offsets (based on line difference)
        if label.body and label.body.statements:
            for stmt in label.body.statements:
                stmt_line = stmt.line_number
                if stmt_line is not None:
                    # Offset is the distance from label line
                    offset = stmt_line - label_line
                    line_map[stmt_line] = (label_name, offset)

    return line_map


def generate_line_map_code(
    line_map: Dict[int, Tuple[str, int]], emitter: "CodeEmitter"
) -> None:
    """Emit _line_map dictionary definition to code emitter.

    Generates Python code that defines the `_line_map` dictionary constant
    at the routine level.

    Args:
        line_map: The line map dictionary to emit
        emitter: CodeEmitter to write code to
    """
    if not line_map:
        emitter.line("_line_map: dict[int, tuple[str, int]] = {}")
        return

    emitter.line("_line_map: dict[int, tuple[str, int]] = {")
    with emitter.indented():
        for line_num in sorted(line_map.keys()):
            label_name, offset = line_map[line_num]
            emitter.line(f'{line_num}: ("{label_name}", {offset}),')
    emitter.line("}")


def find_next_executable(
    target_line: int, line_map: Dict[int, Tuple[str, int]]
) -> Optional[int]:
    """Find the next executable line at or after target_line.

    When an offset calculation lands on a non-executable line (comment
    or blank), MUMPS semantics say to continue to the next executable
    line.

    Args:
        target_line: The line number to start searching from
        line_map: The line map to search in

    Returns:
        The next executable line number, or None if no executable
        line exists at or after target_line
    """
    if target_line in line_map:
        return target_line

    # Find the next line number greater than target_line
    for line_num in sorted(line_map.keys()):
        if line_num > target_line:
            return line_num

    return None
