"""FOR loop analysis functions.

High-level ASG analysis functions for FOR statements:
- analyze_for_loops: Analyze all FOR loops in a routine
- detect_loop_var_modification: Check if loop variable is modified in body
- detect_internal_quit: Check if QUIT is present in FOR body

These functions operate on ASG nodes (MRoutine, MForStatement)
and do not perform any text parsing.
"""

from typing import Union

from ..asg.elements import MRoutine, MScope
from ..asg.enums import PassingMode
from ..asg.expressions import MActualParameter, MVariable
from ..asg.statements import (
    MDoStatement,
    MForStatement,
    MKillStatement,
    MQuitStatement,
    MReadStatement,
    MSetStatement,
)
from ..asg.type_helpers import get_body_scope, get_else_scope, get_then_scope


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
                    # Extract loop variable name for modification checks
                    if isinstance(stmt.loop_var, str):
                        loop_var_name = stmt.loop_var
                        loop_var_for_check: Union[str, MVariable] = stmt.loop_var
                    elif isinstance(stmt.loop_var, MVariable):
                        loop_var_name = stmt.loop_var.name
                        loop_var_for_check = stmt.loop_var
                    else:
                        # MExpr case (e.g., indirection) - assume modified for safety
                        stmt.loop_var_modified_in_body = True
                        loop_var_name = None
                        loop_var_for_check = None  # type: ignore[assignment]

                    if loop_var_name and loop_var_for_check is not None:
                        # Check for SET, READ, KILL modifications
                        modified_in_body = _check_var_modified_in_scope(
                            loop_var_for_check, stmt.body
                        )
                        # Check for pass-by-reference in DO calls (conservative)
                        passed_byref = _check_var_passed_byref_in_scope(
                            loop_var_name, stmt.body
                        )
                        stmt.loop_var_modified_in_body = (
                            modified_in_body or passed_byref
                        )
                stmt.has_internal_quit = _check_quit_in_scope(stmt.body)
                # Recurse into nested structures within FOR body
                _analyze_fors_in_scope(stmt.body)
        # Recurse into other nested scopes using type-safe helpers
        then_scope = get_then_scope(stmt)
        if then_scope is not None:
            _analyze_fors_in_scope(then_scope)
        else:
            else_scope = get_else_scope(stmt)
            if else_scope is not None:
                _analyze_fors_in_scope(else_scope)
            else:
                body = get_body_scope(stmt)
                if body is not None and not isinstance(stmt, MForStatement):
                    _analyze_fors_in_scope(body)


def _check_var_modified_in_scope(
    loop_var: Union[str, MVariable], scope: MScope
) -> bool:
    """Check if a loop variable is modified in a scope.

    Detects modification via:
    - SET command: S I=value
    - READ command: R I (reads into variable)
    - KILL command: K I (removes variable, effectively modifying it)

    Args:
        loop_var: The loop variable (string name or MVariable)
        scope: The scope to check

    Returns:
        True if the variable is SET, READ, or KILLED within the scope
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
        # Check SET statements
        if isinstance(stmt, MSetStatement):
            for assignment in stmt.assignments:
                target = assignment.target
                if isinstance(target, MVariable):
                    if target.name == var_name:
                        return True
                elif isinstance(target, str):
                    if target == var_name:
                        return True

        # Check READ statements - reading INTO a variable modifies it
        elif isinstance(stmt, MReadStatement):
            from ..asg.statements import MReadTarget

            for arg in stmt.arguments:
                if isinstance(arg, MReadTarget):
                    target_var = arg.variable
                    if isinstance(target_var, MVariable):
                        if target_var.name == var_name:
                            return True

        # Check KILL statements - killing a variable modifies it
        elif isinstance(stmt, MKillStatement):
            # K (no targets, is_kill_all) - kills ALL local variables
            if stmt.is_kill_all:
                return True
            # Selective kill: check if loop var is in targets
            for target in stmt.targets:
                if isinstance(target, MVariable):
                    if target.name == var_name:
                        return True
                elif isinstance(target, str):
                    if target == var_name:
                        return True

        # Recurse into nested scopes using type-safe helpers
        then_scope = get_then_scope(stmt)
        if then_scope is not None:
            if _check_var_modified_in_scope(loop_var, then_scope):
                return True
        else_scope = get_else_scope(stmt)
        if else_scope is not None:
            if _check_var_modified_in_scope(loop_var, else_scope):
                return True
        body = get_body_scope(stmt)
        if body is not None:
            # Note: For nested FOR loops, we still check - the outer loop var
            # might be modified in an inner loop's body
            if _check_var_modified_in_scope(loop_var, body):
                return True

    return False


def _check_var_passed_byref_in_scope(var_name: str, scope: MScope) -> bool:
    """Check if a variable is passed by reference in a DO call within a scope.

    This is a conservative check - if the loop variable is passed by reference
    to any subroutine, we assume it may be modified (even though the callee
    may not actually modify it).

    Args:
        var_name: The variable name to check
        scope: The scope to check

    Returns:
        True if the variable is passed by reference in any DO call
    """
    for stmt in scope.statements:
        # Check DO statements for by-ref parameters
        if isinstance(stmt, MDoStatement):
            for call in stmt.targets:
                for arg in call.arguments:
                    if isinstance(arg, MActualParameter):
                        if arg.passing_mode == PassingMode.BY_REFERENCE:
                            if arg.variable_name == var_name:
                                return True

        # Recurse into nested scopes
        then_scope = get_then_scope(stmt)
        if then_scope is not None:
            if _check_var_passed_byref_in_scope(var_name, then_scope):
                return True
        else_scope = get_else_scope(stmt)
        if else_scope is not None:
            if _check_var_passed_byref_in_scope(var_name, else_scope):
                return True
        body = get_body_scope(stmt)
        if body is not None:
            if _check_var_passed_byref_in_scope(var_name, body):
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
        then_scope = get_then_scope(stmt)
        if then_scope is not None:
            if _check_quit_in_scope(then_scope):
                return True
        else_scope = get_else_scope(stmt)
        if else_scope is not None:
            if _check_quit_in_scope(else_scope):
                return True

        # Do NOT recurse into nested FOR bodies - their QUIT exits THEM, not us
        # Also don't recurse into DO blocks - separate scope

    return False
