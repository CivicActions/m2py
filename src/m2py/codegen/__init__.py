"""Code generation module for MUMPS-to-Python transpilation.

Provides the public API for generating executable Python code from MUMPS source.
"""

from __future__ import annotations

import ast
from typing import TYPE_CHECKING

from m2py.parser import MUMPSParser
from m2py.codegen.routine import RoutineGenerator
from m2py.codegen.enums import GotoStrategy
from m2py.codegen.exceptions import CodegenError, UnsupportedFeatureError

if TYPE_CHECKING:
    from m2py.asg.elements import MRoutine


def _select_goto_strategy(routine: "MRoutine") -> GotoStrategy:
    """Select code generation strategy based on routine analysis.

    Spec 006 (T043-T044): Automatic strategy selection based on ASG flags.
    No user configuration needed - strategy is determined by analysis results.

    Args:
        routine: Analyzed MRoutine with needs_trampoline flag set

    Returns:
        GotoStrategy indicating which pattern to use

    Strategy Selection:
        - `needs_trampoline=True` → TRAMPOLINE with RoutineState
        - Offset calls present → TRAMPOLINE (for _start_offset parameter support)
        - Otherwise → SIMPLE_FUNCTIONS (current Spec 005 behavior)

    Note:
        UNRESOLVED and EXTERNAL GOTOs are checked at statement level during
        code generation, not at strategy selection. They raise UnsupportedFeatureError.
    """
    if routine.needs_trampoline:
        return GotoStrategy.TRAMPOLINE
    # Spec 007: Use TRAMPOLINE when offset calls exist for _start_offset support
    # Note: has_offset_calls is populated by classify_gotos() analysis pass
    if routine.has_offset_calls:
        return GotoStrategy.TRAMPOLINE
    return GotoStrategy.SIMPLE_FUNCTIONS


def _get_reachable_labels(routine: "MRoutine") -> set[str]:
    """Get labels reachable from the routine entry point.

    Computes the set of labels that can be reached via DO calls or GOTOs
    starting from the first label (entry point). Labels that are only
    callable externally (from other routines) are excluded.

    This is used to filter GOTO checking - unresolved GOTOs in unreachable
    labels shouldn't prevent compilation of the main routine.

    Args:
        routine: Analyzed MRoutine

    Returns:
        Set of label names reachable from entry
    """
    from m2py.asg.statements import MDoStatement, MGotoStatement

    if not routine.labels:
        return set()

    reachable: set[str] = set()
    worklist: list[str] = [routine.labels[0].name]  # Start from entry label
    label_map = {lbl.name: lbl for lbl in routine.labels}

    while worklist:
        label_name = worklist.pop()
        if label_name in reachable:
            continue
        reachable.add(label_name)

        label = label_map.get(label_name)
        if label is None or label.body is None:
            continue

        # Find all internal calls and gotos from this label
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MDoStatement):
                for call in stmt.targets:
                    # Only follow calls to labels in this routine (no routine specified)
                    if call.routine is None and call.name and call.name in label_map:
                        worklist.append(call.name)
            elif isinstance(stmt, MGotoStatement):
                for call in stmt.targets:
                    # Only follow gotos to labels in this routine
                    if call.routine is None and call.name and call.name in label_map:
                        worklist.append(call.name)

        # Also follow fall-through to next label
        if label.needs_fallthrough and label.next_label:
            worklist.append(label.next_label.name)

    return reachable


def _check_unsupported_gotos(routine: "MRoutine") -> None:
    """Check for unsupported GOTO patterns and raise if found.

    Spec 006 (T045a, T045b): Emit UnsupportedFeatureError for GOTO patterns
    that are deferred to later specs.

    Only checks labels that are reachable from the routine entry point.
    Labels that contain unresolved GOTOs but are only callable externally
    are allowed - they simply won't be generated.

    Args:
        routine: Analyzed MRoutine

    Raises:
        UnsupportedFeatureError: If UNRESOLVED GOTOs are found in reachable labels
    """
    from m2py.asg.enums import GotoType
    from m2py.asg.statements import MGotoStatement

    # Only check labels reachable from entry point
    reachable = _get_reachable_labels(routine)

    for label in routine.labels:
        if label.name not in reachable:
            continue  # Skip unreachable labels
        if label.body is None:
            continue
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                if stmt.goto_type == GotoType.UNRESOLVED:
                    raise UnsupportedFeatureError(
                        "UNRESOLVED GOTO not supported - See Spec 012"
                    )
                # Spec 008 Phase 6: EXTERNAL GOTOs now supported


def generate_python(
    source: str,
    *,
    routine_name: str | None = None,
    validate: bool = True,
) -> str:
    """Generate Python code from MUMPS source.

    Args:
        source: MUMPS source code (single routine)
        routine_name: Optional name for the routine (extracted from source if not provided)
        validate: If True, validate generated code with ast.parse()

    Returns:
        Python source code as a string

    Raises:
        ParseError: If MUMPS source cannot be parsed
        CodegenError: If code generation fails
        SyntaxError: If validate=True and generated code is invalid Python

    Example:
        >>> code = generate_python("TEST S X=1 W X Q")
        >>> print(code)
        from m2py.codegen.helpers import m_str, m_num, m_truth, m_compare
        ...
    """
    # Parse MUMPS source
    parser = MUMPSParser()
    routine = parser.parse(source, filename=routine_name)

    # Set routine name if provided
    if routine_name:
        routine.name = routine_name
    elif routine.labels:
        # Fall back to first label name (e.g. "TEST" from "TEST W 1 Q")
        routine.name = routine.labels[0].name

    # Run analysis passes required for code generation
    # Order matters: references first, then GOTO, FOR, quit context, variables
    parser.resolve_references(routine)
    parser.classify_gotos(routine)
    parser.analyze_for_loops(routine)
    parser.analyze_quit_context(routine)
    parser.analyze_variables(routine, compute_transitive=True)
    parser.compute_signatures(routine)

    # Spec 006 (T045a, T045b): Check for unsupported GOTO patterns
    _check_unsupported_gotos(routine)

    # Spec 006 (T043-T044): Select generation strategy based on analysis
    strategy = _select_goto_strategy(routine)

    # Generate Python code
    generator = RoutineGenerator(routine, strategy=strategy)
    python_code = generator.generate()

    # Validate if requested
    if validate:
        try:
            ast.parse(python_code)
        except SyntaxError as e:
            raise SyntaxError(
                f"Generated Python code is invalid: {e}\n\nGenerated code:\n{python_code}"
            ) from e

    return python_code


__all__ = [
    "generate_python",
    "CodegenError",
    "UnsupportedFeatureError",
]
