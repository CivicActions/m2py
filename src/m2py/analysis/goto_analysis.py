"""GOTO classification and analysis functions.

High-level ASG analysis functions for GOTO statements:
- classify_gotos: Classify GOTO statements by target and context
- get_loop_exiting_gotos: Find GOTOs that exit loops
- get_gotos_by_type: Filter GOTOs by GotoType

These functions operate on ASG nodes (MRoutine, MGotoStatement, MForStatement)
and do not perform any text parsing.
"""

from typing import List

from ..asg.elements import MLabel, MRoutine, MScope
from ..asg.enums import GotoType
from ..asg.statements import MForStatement, MGotoStatement
from ..asg.type_helpers import get_body_scope, get_else_scope, get_then_scope


def classify_gotos(routine: MRoutine) -> None:
    """Classify all GOTO statements in a routine.

    This function analyzes each MGotoStatement in the routine and:
    1. Sets the goto_type based on target and context
    2. Populates exits_loops with enclosing FOR loops exited
    3. Sets routine.has_unstructured_goto if any GOTO requires non-structured translation

    Must be called AFTER resolve_references() so MCall.target is populated.

    Args:
        routine: The MRoutine to classify GOTOs in

    Side Effects:
        - Sets MGotoStatement.goto_type for each GOTO
        - Sets MGotoStatement.exits_loops for loop exits
        - Sets MRoutine.has_unstructured_goto if complex control flow detected
    """
    # Build a position map for labels (for forward/backward detection)
    label_positions = {}
    for i, label in enumerate(routine.labels):
        label_positions[label.name] = i

    # Process each label's statements
    for label_idx, label in enumerate(routine.labels):
        _classify_gotos_in_scope(
            label.body, label_idx, label, label_positions, routine, enclosing_fors=[]
        )

    # Set has_unstructured_goto based on GOTO classifications
    # Unstructured patterns that can't easily translate to structured Python:
    # - BACKWARD_JUMP to different label (creates implicit loop across labels)
    # - UNRESOLVED (target unknown at compile time)
    # - Cross-label jumps not inside FOR loops (can't use break, need restructuring)
    routine.has_unstructured_goto = _has_unstructured_gotos(routine)


def _classify_gotos_in_scope(
    scope: MScope,
    current_label_idx: int,
    current_label: MLabel,
    label_positions: dict,
    routine: MRoutine,
    enclosing_fors: List[MForStatement],
) -> None:
    """Classify GOTOs within a scope, tracking enclosing FORs.

    Args:
        scope: The scope to scan for GOTOs
        current_label_idx: Index of current label in routine
        current_label: The MLabel containing this scope
        label_positions: Label name -> position mapping
        routine: The containing routine
        enclosing_fors: Stack of enclosing FOR loops (innermost last)
    """
    for stmt in scope.statements:
        if isinstance(stmt, MGotoStatement):
            _classify_single_goto(
                stmt,
                current_label_idx,
                current_label,
                label_positions,
                routine,
                enclosing_fors,
            )
        elif isinstance(stmt, MForStatement):
            # Recurse into FOR body with this FOR added to enclosing stack
            if stmt.body:
                _classify_gotos_in_scope(
                    stmt.body,
                    current_label_idx,
                    current_label,
                    label_positions,
                    routine,
                    enclosing_fors + [stmt],
                )
        # Recurse into other nested scopes using type-safe helpers
        else:
            then_scope = get_then_scope(stmt)
            if then_scope is not None:
                _classify_gotos_in_scope(
                    then_scope,
                    current_label_idx,
                    current_label,
                    label_positions,
                    routine,
                    enclosing_fors,
                )
            else_scope = get_else_scope(stmt)
            if else_scope is not None:
                _classify_gotos_in_scope(
                    else_scope,
                    current_label_idx,
                    current_label,
                    label_positions,
                    routine,
                    enclosing_fors,
                )
            body = get_body_scope(stmt)
            if body is not None:
                _classify_gotos_in_scope(
                    body,
                    current_label_idx,
                    current_label,
                    label_positions,
                    routine,
                    enclosing_fors,
                )


def _classify_single_goto(
    stmt: MGotoStatement,
    current_label_idx: int,
    current_label: MLabel,
    label_positions: dict,
    routine: MRoutine,
    enclosing_fors: List[MForStatement],
) -> None:
    """Classify a single GOTO statement.

    Sets stmt.goto_type and stmt.exits_loops based on:
    - Target resolution status
    - Target location relative to source
    - Enclosing control structures

    Args:
        stmt: The MGotoStatement to classify
        current_label_idx: Index of current label
        current_label: The containing MLabel
        label_positions: Label name -> position mapping
        routine: The containing routine
        enclosing_fors: Stack of enclosing FOR loops
    """
    # Check each target (usually just one, but GOTO can have multiple)
    for call in stmt.targets:
        # External call (^routine) - but check if it's same routine first
        if call.routine is not None:
            # Check if this is the same routine (G label^SAMEROUTINE pattern)
            if call.routine.upper() != routine.name.upper():
                stmt.goto_type = GotoType.EXTERNAL
                continue
            # Same routine explicit reference - treat as resolved if label exists
            if call.name in label_positions:
                # Continue to classify as regular GOTO within routine
                pass
            else:
                stmt.goto_type = GotoType.UNRESOLVED
                continue

        # Unresolved reference (no routine and not resolved)
        if call.routine is None and (not call.is_resolved or call.target is None):
            stmt.goto_type = GotoType.UNRESOLVED
            continue

        # Get target label - either from resolved target or by name lookup
        if call.target:
            target_label = call.target
        else:
            # Same-routine explicit call - look up label by name
            target_label = routine.get_label(call.name)
            if not target_label:
                stmt.goto_type = GotoType.UNRESOLVED
                continue

        target_label_idx = label_positions.get(target_label.name, -1)

        # Determine base goto type based on target location
        if target_label.name == current_label.name:
            # Intra-label jump: GOTO targets the same label it's contained in.
            # Direction depends on offset:
            # - G LABEL (no offset): jumps to start of label = backward
            # - G LABEL+n: jumps to label+n lines, direction depends on n vs current position
            stmt.is_cross_label = False

            # Check for offset to determine direction
            target_offset = call.offset
            if target_offset is None:
                # No offset: G LABEL = backward to label start
                # This pattern creates an implicit loop: code executes, then jumps
                # back to the label start. Example:
                #   TEST S X=X+1 W X I X<10 G TEST Q
                stmt.goto_type = GotoType.BACKWARD_JUMP
            else:
                # Has offset: G LABEL+n
                # Try to determine direction if offset is a literal AND we have line info
                from m2py.asg.expressions import MLiteral

                if (
                    isinstance(target_offset, MLiteral)
                    and target_offset.value is not None
                    and stmt.line_number is not None
                    and target_label.line_number is not None
                ):
                    # Static offset with line info - compare positions
                    goto_line_offset = stmt.line_number - target_label.line_number
                    target_line_offset = int(target_offset.value)

                    if target_line_offset > goto_line_offset:
                        # Target is ahead of GOTO position = forward
                        stmt.goto_type = GotoType.FORWARD_JUMP
                    else:
                        # Target is at or before GOTO position = backward
                        stmt.goto_type = GotoType.BACKWARD_JUMP
                else:
                    # Cannot determine direction statically (dynamic offset or missing line info)
                    # Default to FORWARD_JUMP since:
                    # 1. G LABEL+n is typically used to skip ahead (forward)
                    # 2. Codegen will handle conservatively if it can't restructure
                    stmt.goto_type = GotoType.FORWARD_JUMP
        else:
            # Different label = cross-label jump
            # Set is_cross_label flag to indicate label boundary crossing
            stmt.is_cross_label = True
            if target_label_idx < current_label_idx:
                # Jumping backward to earlier label
                stmt.goto_type = GotoType.BACKWARD_JUMP
            else:
                # Jumping forward to later label
                stmt.goto_type = GotoType.FORWARD_JUMP

        # If inside FOR loops, this is a loop exit (overrides FORWARD_JUMP/BACKWARD_JUMP type)
        # Note: is_cross_label remains set if target is different label
        if enclosing_fors:
            if len(enclosing_fors) == 1:
                stmt.goto_type = GotoType.LOOP_EXIT
                stmt.exits_loops = list(enclosing_fors)
            else:
                stmt.goto_type = GotoType.MULTI_LOOP_EXIT
                stmt.exits_loops = list(enclosing_fors)

            # Set has_internal_goto on all enclosing FORs
            for for_stmt in enclosing_fors:
                for_stmt.has_internal_goto = True
                # Add this GOTO to the FOR's exit_points (bidirectional link)
                if stmt not in for_stmt.exit_points:
                    for_stmt.exit_points.append(stmt)

            # Check for "continue" pattern: GOTO jumps back to the label containing
            # the innermost FOR loop. This is equivalent to Python's "continue".
            # The GOTO target must be the same label we're currently in.
            if target_label.name == current_label.name:
                stmt.is_loop_continue = True

        # If jumping to different label while inside FOR, it's a cross-label exit
        if enclosing_fors and target_label.name != current_label.name:
            if len(enclosing_fors) > 1:
                stmt.goto_type = GotoType.MULTI_LOOP_EXIT
            else:
                stmt.goto_type = GotoType.LOOP_EXIT
            stmt.exits_loops = list(enclosing_fors)


def get_loop_exiting_gotos(routine: MRoutine) -> List[MGotoStatement]:
    """Get all GOTOs that exit FOR loops.

    Args:
        routine: The MRoutine to scan

    Returns:
        List of MGotoStatement objects that have exits_loops populated
    """
    result = []
    for label in routine.labels:
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                if stmt.exits_loops:
                    result.append(stmt)
    return result


def get_gotos_by_type(routine: MRoutine, goto_type: GotoType) -> List[MGotoStatement]:
    """Get all GOTOs of a specific type.

    Args:
        routine: The MRoutine to scan
        goto_type: The GotoType to filter by

    Returns:
        List of MGotoStatement objects with matching goto_type
    """
    result = []
    for label in routine.labels:
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                if stmt.goto_type == goto_type:
                    result.append(stmt)
    return result


def _has_unstructured_gotos(routine: MRoutine) -> bool:
    """Determine if routine has GOTOs that require unstructured translation.

    Returns True if any GOTO pattern cannot be easily mapped to structured
    Python constructs (if/else, break, function calls). These patterns
    typically require a state machine or exception-based control flow.

    Unstructured patterns:
    - BACKWARD_JUMP: Creates implicit loops (especially cross-label)
    - UNRESOLVED: Target unknown at compile time, needs runtime dispatch
    - FORWARD_JUMP with is_cross_label=True (not exiting a loop): Can't use
      simple if/else within a single function without restructuring

    Structured patterns (return False):
    - LOOP_EXIT / MULTI_LOOP_EXIT: Translates to break (or exception for multi)
    - FORWARD_JUMP within same label (is_cross_label=False): Translates to if/else
    - EXTERNAL: Translates to function call to another module

    Args:
        routine: The MRoutine to analyze

    Returns:
        True if unstructured control flow detected
    """
    for label in routine.labels:
        for stmt in label.body.walk_statements():
            if not isinstance(stmt, MGotoStatement):
                continue

            # UNRESOLVED always requires runtime dispatch
            if stmt.goto_type == GotoType.UNRESOLVED:
                return True

            # BACKWARD_JUMP typically creates loops that need state machine
            if stmt.goto_type == GotoType.BACKWARD_JUMP:
                return True

            # Cross-label forward jumps (not loop exits) require restructuring
            # These jump to a different label and can't use simple if/else
            if stmt.is_cross_label and not stmt.exits_loops:
                return True

    return False
