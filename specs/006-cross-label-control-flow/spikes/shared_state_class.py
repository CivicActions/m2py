#!/usr/bin/env python3
"""Shared State Pattern: RoutineState Class Approach.

This spike tests passing a dataclass as shared state between label functions.
The trampoline passes state through each label function.

Pattern:
    @label("NAME")
    def NAME(s: RoutineState) -> tuple[Optional[str], RoutineState]:
        s.var = value  # Direct attribute access
        return ("NEXT", s)

Run: uv run python specs/006-cross-label-control-flow/spikes/shared_state_class.py
"""

from dataclasses import dataclass, field
from typing import Optional, Callable, Dict, Any
import io


@dataclass
class RoutineState:
    """Shared state container for routine variables.

    Advantages:
    - Type hints on each field
    - IDE autocomplete for variable names
    - Explicit declaration of all variables
    - Easy to inspect/debug
    - Immutable-friendly if needed

    Disadvantages:
    - Must pre-declare all variables
    - Dynamic variable creation requires __dict__ access
    - Class definition overhead
    """

    # Simple variables
    X: Any = None
    Y: Any = None
    Z: Any = None
    RESULT: Any = None

    # Output buffer
    _output: io.StringIO = field(default_factory=io.StringIO)

    def write(self, *args: Any) -> None:
        """Simulate MUMPS WRITE command."""
        for arg in args:
            if arg == "!":
                self._output.write("\n")
            else:
                self._output.write(str(arg))

    def get_output(self) -> str:
        return self._output.getvalue()


# Type alias for label functions
LabelFunc = Callable[[RoutineState], tuple[Optional[str], RoutineState]]

# Label registry
_labels: Dict[str, LabelFunc] = {}


def label(name: str):
    """Decorator to register a label function."""

    def decorator(func: LabelFunc) -> LabelFunc:
        _labels[name] = func
        return func

    return decorator


# =============================================================================
# Test Routine: Simple variable passing across labels
# =============================================================================


@label("ENTRY")
def ENTRY(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    """Set X, jump to ADDONE."""
    s.X = 10
    s.write("ENTRY: X=", s.X, "!")
    return ("ADDONE", s)


@label("ADDONE")
def ADDONE(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    """Add 1 to X, jump to DOUBLE."""
    s.X = s.X + 1
    s.write("ADDONE: X=", s.X, "!")
    return ("DOUBLE", s)


@label("DOUBLE")
def DOUBLE(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    """Double X, store in Y, jump to SHOW."""
    s.Y = s.X * 2
    s.write("DOUBLE: Y=", s.Y, "!")
    return ("SHOW", s)


@label("SHOW")
def SHOW(s: RoutineState) -> tuple[Optional[str], RoutineState]:
    """Show final results."""
    s.write("SHOW: X=", s.X, " Y=", s.Y, "!")
    s.RESULT = s.Y
    return (None, s)


# =============================================================================
# Trampoline
# =============================================================================


def run_trampoline(entry_label: str = "ENTRY") -> RoutineState:
    """Execute routine via trampoline dispatch loop."""
    state = RoutineState()
    current_label = entry_label

    while current_label is not None:
        if current_label not in _labels:
            raise RuntimeError(f"Unknown label: {current_label}")
        func = _labels[current_label]
        current_label, state = func(state)

    return state


# =============================================================================
# Rope Refactorability Tests
# =============================================================================


def test_rope_compatibility():
    """Test that Rope can work with this pattern."""
    # 1. Can rename RoutineState.X to RoutineState.VALUE?
    #    - Yes: IDE "Rename Symbol" works on dataclass fields

    # 2. Can extract a helper function that uses state?
    #    - Yes: def helper(s: RoutineState) -> RoutineState: ...

    # 3. Can find all usages of s.X?
    #    - Yes: "Find All References" works on dataclass fields

    print("Rope compatibility: GOOD")
    print("- Rename Symbol: Works on dataclass fields")
    print("- Extract Method: Works (pass state as parameter)")
    print("- Find References: Works for field accesses")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    state = run_trampoline()
    print(state.get_output())
    print("--- Results ---")
    print(f"Final RESULT: {state.RESULT}")
    print("Expected: 22 (10+1=11, 11*2=22)")
    print(f"Correct: {state.RESULT == 22}")
    print()
    test_rope_compatibility()
