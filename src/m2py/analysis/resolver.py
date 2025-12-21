"""Reference resolution for GOTO and DO targets.

Resolves MCall references to their target MLabel objects:
1. Scans statements for MCall objects (in GOTO, DO statements)
2. Looks up labels by name within the routine
3. Populates MCall.target with resolved MLabel
4. Populates MLabel.callers and MLabel.goto_sources back-references

External calls (label^routine) are marked as external but not resolved
since they reference other routines not currently loaded.
"""

from typing import List, Optional
from ..asg.elements import MRoutine, MLabel, MCall, MScope
from ..asg.statements import MGotoStatement, MDoStatement
from ..asg.enums import CallType


def resolve_references(routine: MRoutine) -> None:
    """Resolve all MCall references in a routine to their targets.
    
    This is the main entry point for reference resolution. It:
    1. Builds a label lookup table for the routine
    2. Scans all statements for MCall objects
    3. Resolves each MCall to its target MLabel
    4. Populates back-references (callers, goto_sources)
    
    Args:
        routine: The MRoutine to resolve references in
        
    Side Effects:
        - Sets MCall.target to the resolved MLabel (or None)
        - Sets MCall.is_resolved to True if resolution succeeded
        - Appends to MLabel.callers for DO calls
        - Appends to MLabel.goto_sources for GOTO jumps
    """
    # Build label lookup table
    label_map = _build_label_map(routine)
    
    # Scan all labels for statements with MCall objects
    for label in routine.labels:
        _resolve_scope_references(label.body, label_map, routine)


def _build_label_map(routine: MRoutine) -> dict[str, MLabel]:
    """Build a name->label mapping for quick lookup.
    
    Args:
        routine: The MRoutine containing labels
        
    Returns:
        Dictionary mapping label names to MLabel objects
    """
    label_map = {}
    for label in routine.labels:
        label_map[label.name] = label
    return label_map


def _resolve_scope_references(
    scope: MScope,
    label_map: dict[str, MLabel],
    routine: MRoutine
) -> None:
    """Resolve MCall references in a scope and its nested scopes.
    
    Args:
        scope: The MScope to scan for references
        label_map: Name->label mapping for resolution
        routine: The containing routine
    """
    for stmt in scope.walk_statements():
        if isinstance(stmt, MGotoStatement):
            _resolve_goto_targets(stmt, label_map, routine)
        elif isinstance(stmt, MDoStatement):
            _resolve_do_targets(stmt, label_map, routine)


def _resolve_goto_targets(
    stmt: MGotoStatement,
    label_map: dict[str, MLabel],
    routine: MRoutine
) -> None:
    """Resolve GOTO target references.
    
    Args:
        stmt: The MGotoStatement with targets to resolve
        label_map: Name->label mapping for resolution
        routine: The containing routine
    """
    for call in stmt.targets:
        _resolve_call(call, label_map, routine, is_goto=True)


def _resolve_do_targets(
    stmt: MDoStatement,
    label_map: dict[str, MLabel],
    routine: MRoutine
) -> None:
    """Resolve DO target references.
    
    Args:
        stmt: The MDoStatement with targets to resolve
        label_map: Name->label mapping for resolution
        routine: The containing routine
    """
    for call in stmt.targets:
        _resolve_call(call, label_map, routine, is_goto=False)


def _resolve_call(
    call: MCall,
    label_map: dict[str, MLabel],
    routine: MRoutine,
    is_goto: bool = False
) -> None:
    """Resolve a single MCall to its target label.
    
    For local calls (no routine specified), looks up in label_map.
    For external calls (^routine), marks as external but does not resolve.
    
    Args:
        call: The MCall to resolve
        label_map: Name->label mapping for resolution
        routine: The containing routine
        is_goto: True if this is a GOTO target, False for DO
        
    Side Effects:
        - Sets call.target to the resolved MLabel (or None)
        - Sets call.is_resolved to True if found
        - Appends call to target label's callers or goto_sources
    """
    # Indirected calls cannot be resolved statically
    if call.indirection is not None:
        call.call_type = CallType.INDIRECT_CALL
        call.is_resolved = False
        return

    # External calls cannot be resolved without loading other routines
    if call.routine is not None:
        # External call - mark as not locally resolvable
        call.call_type = CallType.ROUTINE_CALL
        call.is_resolved = False
        return
    
    # Look up local label
    target_name = call.name
    if target_name in label_map:
        call.target = label_map[target_name]
        call.is_resolved = True
        call.call_type = CallType.OFFSET_CALL if call.offset is not None else CallType.LABEL_CALL
        
        # Add back-reference
        if is_goto:
            call.target.goto_sources.append(call)
        else:
            call.target.callers.append(call)
    else:
        # Label not found - could be forward reference not yet parsed
        # or a reference to an undefined label
        call.call_type = CallType.UNRESOLVED
        call.is_resolved = False


def get_unresolved_calls(routine: MRoutine) -> List[MCall]:
    """Get all MCall objects that could not be resolved.
    
    Useful for identifying missing labels or external references.
    
    Args:
        routine: The MRoutine to check
        
    Returns:
        List of MCall objects with is_resolved=False
    """
    unresolved = []
    
    for label in routine.labels:
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                for call in stmt.targets:
                    if not call.is_resolved:
                        unresolved.append(call)
            elif isinstance(stmt, MDoStatement):
                for call in stmt.targets:
                    if not call.is_resolved:
                        unresolved.append(call)
    
    return unresolved


def get_external_calls(routine: MRoutine) -> List[MCall]:
    """Get all MCall objects that reference external routines.
    
    Args:
        routine: The MRoutine to check
        
    Returns:
        List of MCall objects with routine != None
    """
    external = []
    
    for label in routine.labels:
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                for call in stmt.targets:
                    if call.routine is not None:
                        external.append(call)
            elif isinstance(stmt, MDoStatement):
                for call in stmt.targets:
                    if call.routine is not None:
                        external.append(call)
    
    return external
