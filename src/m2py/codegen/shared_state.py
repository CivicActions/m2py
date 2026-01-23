"""Shared state infrastructure for cross-label GOTO code generation.

Spec 006 Phase 4: Provides functions to generate RoutineState dataclass
for trampoline pattern. RoutineState carries variables across label boundaries.

Pattern (static fields):
    @dataclass
    class RoutineState:
        X: Any = None           # Simple variable
        A: MArray = field(default_factory=MArray)  # Array variable

Pattern (dynamic locals - Spec 017):
    @dataclass
    class RoutineState:
        _locals: dict = field(default_factory=dict)  # All local variables
        _new_stack: list = field(default_factory=list)  # Stack for NEW saves
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Set

if TYPE_CHECKING:
    from m2py.asg.elements import MRoutine


def routine_uses_dynamic_locals(routine: "MRoutine") -> bool:
    """Check if routine needs dynamic locals dict instead of static fields.

    Spec 017: Routines with argumentless KILL or argumentless NEW need
    dynamic variable storage because we cannot enumerate all variables
    statically. These routines use state._locals dict for all variable
    access instead of state.VAR individual fields.

    Args:
        routine: MRoutine to check

    Returns:
        True if routine needs _locals dict, False for static fields
    """
    return routine.has_argumentless_kill or routine.has_argumentless_new


def generate_routine_state_class(routine: "MRoutine") -> str:
    """Generate RoutineState dataclass definition for a routine.

    Spec 006 (T048): Builds RoutineState dataclass from analysis results.
    Uses routine.routine_state_vars for simple variables and
    routine.array_vars for MArray fields.

    Spec 017: When routine has argumentless KILL or NEW, generates dict-based
    RoutineState with _locals and _new_stack fields instead of static fields.

    Args:
        routine: Analyzed MRoutine with routine_state_vars and array_vars populated

    Returns:
        Python source code for the RoutineState dataclass

    Example output (static):
        @dataclass
        class RoutineState:
            X: Any = None
            Y: Any = None
            A: MArray = field(default_factory=MArray)

    Example output (dynamic - Spec 017):
        @dataclass
        class RoutineState:
            _locals: dict = field(default_factory=dict)
            _new_stack: list = field(default_factory=list)
    """
    # Spec 017: Check if routine needs dynamic locals
    if routine_uses_dynamic_locals(routine):
        return _generate_dynamic_state_class()

    # Standard static field generation
    lines = []

    # Get variable sets from analysis
    state_vars: Set[str] = routine.routine_state_vars or set()
    array_vars: Set[str] = routine.array_vars or set()

    # Identify simple vars (in state_vars but not arrays)
    simple_vars = state_vars - array_vars

    # Array vars that need state fields (intersection with state_vars OR just array_vars)
    # We include all array_vars since they may be accessed across labels
    array_state_vars = array_vars

    # If no variables need state, return minimal dataclass
    if not simple_vars and not array_state_vars:
        return """@dataclass
class RoutineState:
    \"\"\"Shared state for cross-label variable visibility.\"\"\"
    pass
"""

    lines.append("@dataclass")
    lines.append("class RoutineState:")
    lines.append('    """Shared state for cross-label variable visibility."""')

    # Add simple variable fields (Any type, default None)
    for var in sorted(simple_vars):
        # Translate variable name to valid Python identifier
        py_name = _translate_var_name(var)
        lines.append(f"    {py_name}: Any = None")

    # Add array variable fields (MArray type, default_factory=MArray)
    for var in sorted(array_state_vars):
        py_name = _translate_var_name(var)
        lines.append(f"    {py_name}: MArray = field(default_factory=MArray)")

    return "\n".join(lines) + "\n"


def _generate_dynamic_state_class() -> str:
    """Generate RoutineState with dynamic _locals dict for argumentless KILL/NEW.

    Spec 017: When a routine uses argumentless KILL or NEW, we cannot use
    static fields because we need to clear/save ALL variables dynamically.

    Returns:
        Python source code for dynamic RoutineState dataclass
    """
    return '''@dataclass
class RoutineState:
    """Shared state with dynamic locals for argumentless KILL/NEW support.

    _locals: Dictionary holding all local variable values. Variable names
             are keys, values are the variable values. Supports argumentless
             KILL (clear all) and dynamic variable access.

    _new_stack: Stack of saved _locals snapshots for argumentless NEW.
                Each NEW pushes a copy, QUIT pops and restores.
    """
    _locals: dict = field(default_factory=dict)
    _new_stack: list = field(default_factory=list)
'''


def generate_state_initialization(routine: "MRoutine") -> str:
    """Generate initial state creation for routine entry.

    Spec 006 (T049): Creates initial RoutineState instance at routine entry.

    Args:
        routine: Analyzed MRoutine

    Returns:
        Python source code for state initialization

    Example output:
        state = RoutineState()
    """
    return "state = RoutineState()\n"


def generate_state_imports() -> str:
    """Generate required imports for RoutineState.

    Returns:
        Python import statements needed for RoutineState definition
    """
    return """from dataclasses import dataclass, field
from typing import Any
from m2py.runtime import MArray
"""


def _translate_var_name(name: str) -> str:
    """Translate MUMPS variable name to valid Python identifier.

    Args:
        name: MUMPS variable name

    Returns:
        Valid Python identifier

    Note:
        MUMPS allows % prefix, which is not valid in Python.
        We translate % to _pct_.
    """
    if name.startswith("%"):
        return "_pct_" + name[1:]
    return name


__all__ = [
    "generate_routine_state_class",
    "generate_state_initialization",
    "generate_state_imports",
    "routine_uses_dynamic_locals",
]
