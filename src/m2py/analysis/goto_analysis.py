"""GOTO classification and analysis functions.

High-level ASG analysis functions for GOTO statements:
- classify_gotos: Classify GOTO statements by target and context
- get_loop_exiting_gotos: Find GOTOs that exit loops
- get_gotos_by_type: Filter GOTOs by GotoType

These functions operate on ASG nodes (MRoutine, MGotoStatement, MForStatement)
and do not perform any text parsing.
"""

from typing import List, Optional

from ..asg.elements import MLabel, MRoutine, MScope
from ..asg.enums import GotoCodegenPattern, GotoType
from ..asg.statements import (
    MDoStatement,
    MForStatement,
    MGotoStatement,
    MIfStatement,
    MStatement,
)
from ..asg.type_helpers import get_body_scope, get_else_scope, get_then_scope


def _find_stmt_index_for_line(
    statements: List[MStatement], target_line: int
) -> Optional[int]:
    """Find the statement index for a given line number.

    Scans the statement list for the first statement at or after the target line.
    This handles cases where there may be gaps in line numbers.

    Args:
        statements: List of statements from a label body
        target_line: The line number to find

    Returns:
        Index of the statement at/after target_line, or None if not found
    """
    for i, stmt in enumerate(statements):
        if stmt.line_number is not None and stmt.line_number >= target_line:
            return i
    return None


def classify_gotos(routine: MRoutine) -> None:
    """Classify all GOTO statements in a routine.

    This function analyzes each MGotoStatement in the routine and:
    1. Sets the goto_type based on target and context
    2. Populates exits_loops with enclosing FOR loops exited
    3. Sets routine.needs_trampoline if any cross-label GOTO exists
    4. Sets routine.needs_loop_exit_exception if MULTI_LOOP_EXIT GOTOs exist

    Must be called AFTER resolve_references() so MCall.target is populated.

    Args:
        routine: The MRoutine to classify GOTOs in

    Side Effects:
        - Sets MGotoStatement.goto_type for each GOTO
        - Sets MGotoStatement.exits_loops for loop exits
        - Sets MRoutine.needs_trampoline if cross-label GOTOs exist
        - Sets MRoutine.needs_loop_exit_exception if MULTI_LOOP_EXIT GOTOs exist
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

    # Set needs_loop_exit_exception if any MULTI_LOOP_EXIT GOTO exists
    routine.needs_loop_exit_exception = _needs_loop_exit_exception(routine)

    # Set needs_trampoline if ANY cross-label GOTOs exist
    # This is the sole trigger for trampoline pattern with RoutineState
    routine.needs_trampoline = _detect_cross_label_gotos(routine)

    # Set has_offset_calls if any GOTO/DO has offset expression
    # This triggers TRAMPOLINE strategy even without cross-label GOTOs
    routine.has_offset_calls = _detect_offset_calls(routine)

    # Set has_external_gotos if any GOTO targets another routine
    # This requires dynamic locals for proper cross-routine variable visibility
    routine.has_external_gotos = _detect_external_gotos(routine)

    # Set fall-through flags on labels
    # Labels without explicit exit (QUIT/GOTO/HALT) fall through to the next label
    _detect_fallthrough(routine)


def _classify_gotos_in_scope(
    scope: MScope,
    current_label_idx: int,
    current_label: MLabel,
    label_positions: dict,
    routine: MRoutine,
    enclosing_fors: List[MForStatement],
    enclosing_if: Optional[MIfStatement] = None,
) -> None:
    """Classify GOTOs within a scope, tracking enclosing FORs and IF.

    Args:
        scope: The scope to scan for GOTOs
        current_label_idx: Index of current label in routine
        current_label: The MLabel containing this scope
        label_positions: Label name -> position mapping
        routine: The containing routine
        enclosing_fors: Stack of enclosing FOR loops (innermost last)
        enclosing_if: The MIfStatement containing this scope (for then_scope only)
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
                enclosing_if,
            )
        elif isinstance(stmt, MForStatement):
            # Recurse into FOR body with this FOR added to enclosing stack
            # No enclosing_if - GOTOs inside FOR are not restructurable to if/else
            if stmt.body:
                _classify_gotos_in_scope(
                    stmt.body,
                    current_label_idx,
                    current_label,
                    label_positions,
                    routine,
                    enclosing_fors + [stmt],
                    None,  # Clear enclosing_if inside FOR
                )
        elif isinstance(stmt, MIfStatement):
            # Recurse into IF then_scope with this IF as enclosing
            if stmt.then_scope is not None:
                _classify_gotos_in_scope(
                    stmt.then_scope,
                    current_label_idx,
                    current_label,
                    label_positions,
                    routine,
                    enclosing_fors,
                    stmt,  # Pass this IF as enclosing_if
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
                    None,  # Only direct MIfStatement sets enclosing_if
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
                    None,  # ELSE doesn't get restructurable GOTOs
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
                    None,  # Other bodies don't get restructurable GOTOs
                )


def _classify_single_goto(
    stmt: MGotoStatement,
    current_label_idx: int,
    current_label: MLabel,
    label_positions: dict,
    routine: MRoutine,
    enclosing_fors: List[MForStatement],
    enclosing_if: Optional[MIfStatement] = None,
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
        enclosing_if: The MIfStatement containing this GOTO (for restructurable back-ref)
    """
    # Check each target (usually just one, but GOTO can have multiple)
    for call in stmt.targets:
        # Check for indirection first
        # Indirect GOTOs are resolved at runtime, not statically
        if call.label_is_indirect or call.routine_is_indirect:
            stmt.goto_type = GotoType.INDIRECT
            continue

        # External call (^routine) - but check if it's same routine first
        if call.routine is not None:
            # Check if this is the same routine (G label^SAMEROUTINE pattern)
            if call.routine.upper() != routine.name.upper():
                stmt.goto_type = GotoType.EXTERNAL
                continue
            # Same routine explicit reference - treat as resolved if label exists
            # G ^ROUTINENAME (empty label) means "restart from entry label"
            effective_name = call.name if call.name else routine.name
            if effective_name in label_positions:
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
            # G ^ROUTINENAME (empty label) defaults to routine entry label
            effective_name = call.name if call.name else routine.name
            target_label = routine.get_label(effective_name)
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
                # Mark label as having self-loop for while True: generation
                current_label.has_self_loop = True
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
                        # Compute target statement index for restructuring
                        # target_stmt_index = offset (since LABEL+n refers to line n)
                        # But we need to map line to statement index in the label body
                        # For simple cases where each line is one statement:
                        # target_line = label.line_number + offset
                        # We need to find which statement is at that line
                        target_line = target_label.line_number + target_line_offset
                        stmt.target_stmt_index = _find_stmt_index_for_line(
                            current_label.body.statements, target_line
                        )
                    else:
                        # Target is at or before GOTO position = backward
                        stmt.goto_type = GotoType.BACKWARD_JUMP
                        # Mark label as having self-loop for while True: generation
                        current_label.has_self_loop = True
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
                # Same-label LOOP_EXIT needs special handling
                # When GOTO targets the same label from inside a FOR loop, we need to
                # break the FOR loop AND continue the outer while True self-loop
                if not stmt.is_cross_label and target_label.name == current_label.name:
                    enclosing_fors[0].has_same_label_exit = True
            else:
                stmt.goto_type = GotoType.MULTI_LOOP_EXIT
                stmt.exits_loops = list(enclosing_fors)

            # Set has_internal_goto on all enclosing FORs
            for for_stmt in enclosing_fors:
                for_stmt.has_internal_goto = True
                # Add this GOTO to the FOR's exit_points (bidirectional link)
                # Use identity check (any()) to avoid deep __eq__ recursion
                # on ASG nodes with heavily nested expressions.
                if not any(stmt is ep for ep in for_stmt.exit_points):
                    for_stmt.exit_points.append(stmt)

            # Pre-compute FOR fields for codegen
            # Set has_cross_label_exit if this GOTO crosses label boundary
            if stmt.is_cross_label:
                # For LOOP_EXIT, the single enclosing FOR needs the flag
                # For MULTI_LOOP_EXIT, all enclosing FORs need the flag
                for for_stmt in enclosing_fors:
                    for_stmt.has_cross_label_exit = True

                # Get target label name for exit_target (raw MUMPS name - codegen translates)
                target_name = stmt.targets[0].name if stmt.targets else None

                # Set exit_target for cross-label exits
                if stmt.goto_type == GotoType.MULTI_LOOP_EXIT:
                    outermost_for = enclosing_fors[0]
                    # Set exit_target on outermost FOR (for calling after except)
                    if target_name:
                        outermost_for.exit_target = target_name
                elif stmt.goto_type == GotoType.LOOP_EXIT:
                    # For single loop exit, set exit_target on that FOR
                    if target_name:
                        enclosing_fors[0].exit_target = target_name

            # MULTI_LOOP_EXIT always needs exception wrapper, regardless of cross_label
            # For cross-label: after catching, call target label
            # For same-label: after catching, continue (restart the while True self-loop)
            if stmt.goto_type == GotoType.MULTI_LOOP_EXIT:
                outermost_for = enclosing_fors[0]
                outermost_for.needs_exception_wrapper = True
                # Mark same-label exit for codegen to generate 'continue' instead of call
                if not stmt.is_cross_label:
                    outermost_for.has_same_label_exit = True

            # Note: There is no "continue" pattern in MUMPS via GOTO.
            # Per MUMPS spec (MDC 3.6.5): "Execution of GOTO effects the immediate
            # termination of all FORs in the line containing the GOTO."
            # A GOTO to the same label creates a function call/recursion, not continue.

        # If jumping to different label while inside FOR, it's a cross-label exit
        if enclosing_fors and target_label.name != current_label.name:
            if len(enclosing_fors) > 1:
                stmt.goto_type = GotoType.MULTI_LOOP_EXIT
            else:
                stmt.goto_type = GotoType.LOOP_EXIT
            stmt.exits_loops = list(enclosing_fors)

    # Compute is_restructurable and codegen_pattern after all classification
    _compute_codegen_fields(stmt, enclosing_if)


def _compute_codegen_fields(
    stmt: MGotoStatement, enclosing_if: Optional[MIfStatement] = None
) -> None:
    """Compute is_restructurable and codegen_pattern for a GOTO statement.

    This must be called after goto_type, is_cross_label, and exits_loops are set.

    Args:
        stmt: The MGotoStatement to update
        enclosing_if: The MIfStatement containing this GOTO (for restructurable back-ref)
    """
    # is_restructurable: intra-label forward jump
    stmt.is_restructurable = (
        stmt.goto_type == GotoType.FORWARD_JUMP and not stmt.is_cross_label
    )

    # Set back-reference on enclosing IF if this GOTO is restructurable
    if stmt.is_restructurable and enclosing_if is not None:
        enclosing_if.restructurable_goto = stmt

    # Determine codegen_pattern based on analysis results
    if stmt.exits_loops:
        if len(stmt.exits_loops) == 1:
            stmt.codegen_pattern = GotoCodegenPattern.BREAK
        else:
            stmt.codegen_pattern = GotoCodegenPattern.MULTI_BREAK
    elif stmt.goto_type in (GotoType.EXTERNAL, GotoType.UNRESOLVED):
        stmt.codegen_pattern = GotoCodegenPattern.UNSUPPORTED
    elif stmt.goto_type == GotoType.BACKWARD_JUMP:
        # Backward jumps are unsupported
        stmt.codegen_pattern = GotoCodegenPattern.UNSUPPORTED
    elif stmt.goto_type == GotoType.FORWARD_JUMP and not stmt.is_cross_label:
        # Intra-label forward jump - can be restructured
        stmt.codegen_pattern = GotoCodegenPattern.FORWARD
    else:
        # Cross-label forward jump or other cases - function call
        stmt.codegen_pattern = GotoCodegenPattern.FUNCTION_CALL


def _needs_loop_exit_exception(routine: MRoutine) -> bool:
    """Check if the routine needs the _LoopExit exception class.

    The _LoopExit exception is needed when there are MULTI_LOOP_EXIT GOTOs
    that need to exit multiple nested FOR loops.

    Args:
        routine: The routine to check

    Returns:
        True if _LoopExit exception class should be generated
    """
    for label in routine.labels:
        if label.body is None:
            continue
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                if stmt.goto_type == GotoType.MULTI_LOOP_EXIT:
                    return True
    return False


def _detect_cross_label_gotos(routine: MRoutine) -> bool:
    """Check if the routine has ANY cross-label GOTO statements.

    Detects cross-label GOTOs that require trampoline pattern.
    This includes BOTH forward and backward cross-label jumps. The trampoline
    pattern is required for ALL cross-label GOTOs to:
    1. Avoid stack growth with repeated cross-label calls
    2. Handle cyclic patterns (A→B→A) without RecursionError
    3. Maintain variable visibility across label boundaries via RoutineState

    Note: This is distinct from `has_unstructured_goto` which is set on MRoutine
    for analysis purposes (used by tests). `needs_trampoline` is the sole trigger
    for trampoline pattern selection in code generation.

    Args:
        routine: The routine to check

    Returns:
        True if any cross-label GOTO exists (forward or backward)
    """
    for label in routine.labels:
        if label.body is None:
            continue
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                # Cross-label GOTOs require trampoline pattern
                if stmt.is_cross_label:
                    return True
    return False


def _detect_offset_calls(routine: MRoutine) -> bool:
    """Check if the routine contains any offset calls (GOTO/DO with offsets).

    Detects GOTO/DO with offset expressions (e.g., G LABEL+N, D SUB+2).
    When offset calls exist, the TRAMPOLINE strategy is required for line-based
    dispatch via _line_map and _start_offset parameter support.

    This function walks all statements looking for MCall targets with non-None
    offset fields.

    Args:
        routine: The routine to check

    Returns:
        True if any GOTO/DO has an offset expression
    """
    for label in routine.labels:
        if label.body is None:
            continue
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


def _detect_external_gotos(routine: MRoutine) -> bool:
    """Check if the routine contains any external GOTOs (to other routines).

    External GOTOs require all local variables to be synced to _scope so that
    the target routine can access them. MUMPS has a single symbol table, so
    variables set before a GOTO must be visible in the target routine.

    This checks for MCall targets with non-None routine field (indicates external).
    Also checks XECUTE constant values for external GOTO patterns.

    Args:
        routine: The routine to check

    Returns:
        True if any GOTO targets an external routine
    """
    from m2py.asg.statements import MXecuteStatement

    for label in routine.labels:
        if label.body is None:
            continue
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                for target in stmt.targets:
                    if target.routine is not None:
                        return True
            # Check XECUTE constant values for external GOTO patterns
            # Look for "G ^" or "G LABEL^" patterns in the constant strings
            elif isinstance(stmt, MXecuteStatement) and stmt.constant_values:
                for const_val in stmt.constant_values:
                    # Check for G(OTO) ^ROUTINE or G(OTO) LABEL^ROUTINE patterns
                    # Using simple string check - look for " G ^" or " G LABEL^"
                    import re

                    if re.search(
                        r"\bG(?:OTO)?\s+[A-Za-z0-9_%]*\^", const_val, re.IGNORECASE
                    ):
                        return True
    return False


def _detect_fallthrough(routine: MRoutine) -> None:
    """Detect labels that need fall-through to the next label.

    MUMPS labels fall through to the next label if they don't end with
    an explicit exit (QUIT, GOTO, or HALT).

    This function sets:
    - MLabel.needs_fallthrough: True if label should fall through
    - MLabel.next_label: Reference to the next label in sequence

    Args:
        routine: The MRoutine to analyze

    Side Effects:
        - Sets MLabel.needs_fallthrough for each label
        - Sets MLabel.next_label for each label (except the last)
    """
    labels = routine.labels
    num_labels = len(labels)

    for i, label in enumerate(labels):
        # Set reference to next label (None for last label)
        if i + 1 < num_labels:
            label.next_label = labels[i + 1]
        else:
            label.next_label = None

        # Check if this label needs fall-through
        # A label needs fall-through if:
        # 1. It's not the last label (nothing to fall through to)
        # 2. It doesn't have an explicit exit (QUIT, GOTO, HALT)
        if i + 1 < num_labels and not label.has_explicit_exit:
            label.needs_fallthrough = True
        else:
            label.needs_fallthrough = False
