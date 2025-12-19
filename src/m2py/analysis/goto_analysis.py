"""GOTO classification and analysis functions.

High-level ASG analysis functions for GOTO statements:
- classify_gotos: Classify GOTO statements by target and context
- get_loop_exiting_gotos: Find GOTOs that exit loops
- get_gotos_by_type: Filter GOTOs by GotoType

These functions operate on ASG nodes (MRoutine, MGotoStatement, MForStatement)
and do not perform any text parsing.
"""

from typing import List
from ..asg.elements import MRoutine, MLabel, MScope
from ..asg.statements import MGotoStatement, MForStatement
from ..asg.enums import GotoType


def classify_gotos(routine: MRoutine) -> None:
    """Classify all GOTO statements in a routine.
    
    This function analyzes each MGotoStatement in the routine and:
    1. Sets the goto_type based on target and context
    2. Populates exits_loops with enclosing FOR loops exited
    
    Must be called AFTER resolve_references() so MCall.target is populated.
    
    Args:
        routine: The MRoutine to classify GOTOs in
        
    Side Effects:
        - Sets MGotoStatement.goto_type for each GOTO
        - Sets MGotoStatement.exits_loops for loop exits
    """
    # Build a position map for labels (for forward/backward detection)
    label_positions = {}
    for i, label in enumerate(routine.labels):
        label_positions[label.name] = i
    
    # Process each label's statements
    for label_idx, label in enumerate(routine.labels):
        _classify_gotos_in_scope(
            label.body,
            label_idx,
            label,
            label_positions,
            routine,
            enclosing_fors=[]
        )


def _classify_gotos_in_scope(
    scope: MScope,
    current_label_idx: int,
    current_label: MLabel,
    label_positions: dict,
    routine: MRoutine,
    enclosing_fors: List[MForStatement]
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
                enclosing_fors
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
                    enclosing_fors + [stmt]
                )
        # Recurse into other nested scopes
        elif hasattr(stmt, 'then_scope') and stmt.then_scope:
            _classify_gotos_in_scope(
                stmt.then_scope,
                current_label_idx,
                current_label,
                label_positions,
                routine,
                enclosing_fors
            )
        elif hasattr(stmt, 'else_scope') and stmt.else_scope:
            _classify_gotos_in_scope(
                stmt.else_scope,
                current_label_idx,
                current_label,
                label_positions,
                routine,
                enclosing_fors
            )
        elif hasattr(stmt, 'body') and stmt.body:
            _classify_gotos_in_scope(
                stmt.body,
                current_label_idx,
                current_label,
                label_positions,
                routine,
                enclosing_fors
            )


def _classify_single_goto(
    stmt: MGotoStatement,
    current_label_idx: int,
    current_label: MLabel,
    label_positions: dict,
    routine: MRoutine,
    enclosing_fors: List[MForStatement]
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
        # External call (^routine)
        if call.routine is not None:
            stmt.goto_type = GotoType.EXTERNAL
            continue
        
        # Unresolved reference
        if not call.is_resolved or call.target is None:
            stmt.goto_type = GotoType.UNRESOLVED
            continue
        
        target_label = call.target
        target_label_idx = label_positions.get(target_label.name, -1)
        
        # Same label = forward or backward within label
        if target_label.name == current_label.name:
            # Within same label - need line numbers to determine direction
            # For now, use a heuristic: if target line < source line = backward
            # If no line info, assume forward
            source_line = stmt.line_number or 0
            # For targets within same label, we'd need to track statement order
            # Simplify: treat as FORWARD for now
            stmt.goto_type = GotoType.FORWARD_JUMP
        else:
            # Different label = cross-label jump
            if target_label_idx < current_label_idx:
                # Jumping backward to earlier label
                stmt.goto_type = GotoType.BACKWARD_JUMP
            else:
                # Jumping forward to later label
                stmt.goto_type = GotoType.FORWARD_JUMP
        
        # If inside FOR loops, this is a loop exit
        if enclosing_fors:
            if len(enclosing_fors) == 1:
                stmt.goto_type = GotoType.LOOP_EXIT
                stmt.exits_loops = list(enclosing_fors)
            else:
                stmt.goto_type = GotoType.MULTI_LOOP_EXIT
                stmt.exits_loops = list(enclosing_fors)
        
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
