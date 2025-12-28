"""Reference resolution for GOTO and DO targets.

Resolves MCall references to their target MLabel objects:
1. Scans statements for MCall objects (in GOTO, DO statements)
2. Looks up labels by name within the routine
3. Populates MCall.target with resolved MLabel
4. Populates MLabel.callers and MLabel.goto_sources back-references
5. Collects all global variable references into MRoutine.global_refs

External calls (label^routine) are marked as external but not resolved
since they reference other routines not currently loaded.
"""

from typing import List, Set
from ..asg.elements import MRoutine, MLabel, MCall, MScope
from ..asg.statements import MGotoStatement, MDoStatement
from ..asg.enums import CallType
from ..asg.expressions import MGlobal, MNakedGlobal


def resolve_references(routine: MRoutine) -> None:
    """Resolve all MCall references in a routine to their targets.

    This is the main entry point for reference resolution. It:
    1. Builds a label lookup table for the routine
    2. Scans all statements for MCall objects
    3. Resolves each MCall to its target MLabel
    4. Populates back-references (callers, goto_sources)
    5. Collects all global variable references into routine.global_refs

    Args:
        routine: The MRoutine to resolve references in

    Side Effects:
        - Sets MCall.target to the resolved MLabel (or None)
        - Sets MCall.is_resolved to True if resolution succeeded
        - Appends to MLabel.callers for DO calls
        - Appends to MLabel.goto_sources for GOTO jumps
        - Populates routine.global_refs with names of all referenced globals
    """
    # Build label lookup table
    label_map = _build_label_map(routine)

    # Scan all labels for statements with MCall objects
    for label in routine.labels:
        _resolve_scope_references(label.body, label_map, routine)

    # Collect all global variable references
    routine.global_refs = list(_collect_global_refs(routine))


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
    scope: MScope, label_map: dict[str, MLabel], routine: MRoutine
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
    stmt: MGotoStatement, label_map: dict[str, MLabel], routine: MRoutine
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
    stmt: MDoStatement, label_map: dict[str, MLabel], routine: MRoutine
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
    call: MCall, label_map: dict[str, MLabel], routine: MRoutine, is_goto: bool = False
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
        call.call_type = (
            CallType.OFFSET_CALL if call.offset is not None else CallType.LABEL_CALL
        )

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


def _collect_global_refs(routine: MRoutine) -> Set[str]:
    """Collect all global variable names referenced in the routine.

    Walks all expressions in the routine looking for MGlobal nodes
    and collects their names. MNakedGlobal nodes are tracked separately
    since they don't have explicit names (they use the last global context).

    Args:
        routine: The MRoutine to scan

    Returns:
        Set of global variable names (without ^ prefix)
    """
    global_names: Set[str] = set()
    visited: Set[int] = set()

    for label in routine.labels:
        for stmt in label.body.walk_statements():
            _collect_globals_from_node(stmt, global_names, visited)

    return global_names


def _collect_globals_from_node(node, global_names: Set[str], visited: Set[int]) -> None:
    """Recursively collect global names from an ASG node.

    Walks through all fields of a node looking for MGlobal instances.
    Uses visited set to avoid infinite recursion from circular references.

    Args:
        node: Any ASG node to scan
        global_names: Set to add found global names to
        visited: Set of already-visited node ids to prevent cycles
    """
    if node is None:
        return

    # Skip already-visited nodes to prevent cycles
    node_id = id(node)
    if node_id in visited:
        return
    visited.add(node_id)

    # Check if this node is a global
    if isinstance(node, MGlobal):
        if node.name:
            global_names.add(node.name)
        return

    # MNakedGlobal doesn't have an explicit name - tracked separately
    if isinstance(node, MNakedGlobal):
        return

    # Recursively check all attributes that might contain expressions
    if hasattr(node, "__dataclass_fields__"):
        for field_name in node.__dataclass_fields__:
            if field_name.startswith("_") or field_name == "parent":
                continue
            value = getattr(node, field_name, None)
            if value is None:
                continue
            if isinstance(value, list):
                for item in value:
                    _collect_globals_from_node(item, global_names, visited)
            elif hasattr(value, "__dataclass_fields__"):
                _collect_globals_from_node(value, global_names, visited)
