"""Line dispatch utilities for computed offset support (Spec 007).

This module provides:
- Line map generation: builds `_line_map` from source lines to (label, offset) tuples
- Offset detection: checks if a routine contains offset calls

The line map enables GOTO/DO with computed offsets (e.g., `G LABEL+N`) by
mapping source line numbers to label entry points with offset positions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Tuple

from m2py.codegen.names import translate_name

if TYPE_CHECKING:
    from m2py.asg.elements import MRoutine
    from m2py.codegen.emitter import CodeEmitter


# NOTE: Offset call detection is now done in analysis layer via classify_gotos().
# The routine.has_offset_calls ASG field should be used instead of traversing here.
# See m2py.analysis.goto_analysis._detect_offset_calls() for the implementation.


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

        Note:
            Label names are translated to valid Python identifiers using translate_name().
            For example, numeric label "2" becomes "_n_2" so getattr() works correctly
            when accessing the label function on the imported module.
    """
    line_map: Dict[int, Tuple[str, int]] = {}

    for label in routine.labels:
        # Translate MUMPS label name to valid Python identifier
        # e.g., "2" -> "_n_2", "%FOO" -> "_pct_FOO"
        python_label_name = translate_name(label.name)
        label_line = label.line_number

        # Label line itself is offset 0
        if label_line is None:
            continue
        line_map[label_line] = (python_label_name, 0)

        # Add statements with their offsets (based on line difference)
        if label.body and label.body.statements:
            for stmt in label.body.statements:
                stmt_line = stmt.line_number
                if stmt_line is not None:
                    # Offset is the distance from label line
                    offset = stmt_line - label_line
                    line_map[stmt_line] = (python_label_name, offset)

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
    emitter.line("_line_map: dict[int, tuple[str, int]] = {")
    with emitter.indented():
        for line_num in sorted(line_map.keys()):
            label_name, offset = line_map[line_num]
            emitter.line(f'{line_num}: ("{label_name}", {offset}),')
    emitter.line("}")
