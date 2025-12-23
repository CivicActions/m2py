"""FOR loop analysis functions.

High-level ASG analysis functions for FOR statements:
- analyze_for_loops: Analyze all FOR loops in a routine
- detect_loop_var_modification: Check if loop variable is modified in body
- detect_internal_quit: Check if QUIT is present in FOR body

These functions operate on ASG nodes (MRoutine, MForStatement)
and do not perform any text parsing.
"""

from typing import List, Set, Optional, Union
from ..asg.elements import MRoutine, MLabel, MScope
from ..asg.statements import MForStatement, MSetStatement, MQuitStatement
from ..asg.expressions import MVariable


def analyze_for_loops(routine: MRoutine) -> None:
    """Analyze all FOR loops in a routine.
    
    This function scans each MForStatement and:
    1. Detects if loop variable is modified inside the body
    2. Sets loop_var_modified_in_body accordingly
    3. Detects if QUIT is present in the body
    4. Sets has_internal_quit accordingly
    
    Args:
        routine: The MRoutine to analyze
        
    Side Effects:
        - Sets MForStatement.loop_var_modified_in_body for each FOR
        - Sets MForStatement.has_internal_quit for each FOR
    """
    for label in routine.labels:
        _analyze_fors_in_scope(label.body)


def _analyze_fors_in_scope(scope: MScope) -> None:
    """Recursively analyze FOR loops in a scope.
    
    Args:
        scope: The scope to scan for FOR statements
    """
    for stmt in scope.statements:
        if isinstance(stmt, MForStatement):
            # Analyze this FOR's body for loop var modification and internal QUIT
            if stmt.body:
                if stmt.loop_var:
                    stmt.loop_var_modified_in_body = _check_var_modified_in_scope(
                        stmt.loop_var, stmt.body
                    )
                stmt.has_internal_quit = _check_quit_in_scope(stmt.body)
                # Recurse into nested structures within FOR body
                _analyze_fors_in_scope(stmt.body)
        # Recurse into other nested scopes
        elif hasattr(stmt, 'then_scope') and stmt.then_scope:
            _analyze_fors_in_scope(stmt.then_scope)
        elif hasattr(stmt, 'else_scope') and stmt.else_scope:
            _analyze_fors_in_scope(stmt.else_scope)
        elif hasattr(stmt, 'body') and stmt.body:
            _analyze_fors_in_scope(stmt.body)


def _check_var_modified_in_scope(
    loop_var: Union[str, MVariable],
    scope: MScope
) -> bool:
    """Check if a loop variable is modified in a scope.
    
    Args:
        loop_var: The loop variable (string name or MVariable)
        scope: The scope to check
        
    Returns:
        True if the variable is SET within the scope
    """
    # Extract the variable name for comparison
    if isinstance(loop_var, str):
        var_name = loop_var
    elif isinstance(loop_var, MVariable):
        var_name = loop_var.name
    else:
        # Complex case (indirection) - assume modified to be safe
        return True
    
    for stmt in scope.statements:
        if isinstance(stmt, MSetStatement):
            # Check each assignment target
            for assignment in stmt.assignments:
                target = assignment.target
                if isinstance(target, MVariable):
                    if target.name == var_name:
                        return True
                elif isinstance(target, str):
                    if target == var_name:
                        return True
        
        # Recurse into nested scopes
        if hasattr(stmt, 'then_scope') and stmt.then_scope:
            if _check_var_modified_in_scope(loop_var, stmt.then_scope):
                return True
        if hasattr(stmt, 'else_scope') and stmt.else_scope:
            if _check_var_modified_in_scope(loop_var, stmt.else_scope):
                return True
        if hasattr(stmt, 'body') and stmt.body:
            # Note: For nested FOR loops, we still check - the outer loop var
            # might be modified in an inner loop's body
            if _check_var_modified_in_scope(loop_var, stmt.body):
                return True
    
    return False


def _check_quit_in_scope(scope: MScope) -> bool:
    """Check if a QUIT statement is present in a scope (not just nested FORs).
    
    Only detects QUIT that would exit THIS scope, not QUITs in nested
    FOR loops (which would exit those inner loops instead).
    
    Args:
        scope: The scope to check
        
    Returns:
        True if QUIT is found in this scope
    """
    for stmt in scope.statements:
        if isinstance(stmt, MQuitStatement):
            return True
        
        # Check in IF/ELSE scopes - QUIT there would still exit the FOR
        if hasattr(stmt, 'then_scope') and stmt.then_scope:
            if _check_quit_in_scope(stmt.then_scope):
                return True
        if hasattr(stmt, 'else_scope') and stmt.else_scope:
            if _check_quit_in_scope(stmt.else_scope):
                return True
        
        # Do NOT recurse into nested FOR bodies - their QUIT exits THEM, not us
        # Also don't recurse into DO blocks - separate scope
    
    return False
