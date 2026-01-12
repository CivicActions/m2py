#!/usr/bin/env python3
"""Shared State Pattern: Outer-Scope Variables Approach.

This spike tests using variables in outer scope (module/function level)
with `nonlocal` declarations in nested label functions.

Pattern:
    X = None
    Y = None

    def LABEL():
        nonlocal X, Y
        X = value

Run: uv run python specs/006-cross-label-control-flow/spikes/shared_state_outer.py
"""

from typing import Optional, Callable, Dict
import io


def run_routine() -> tuple[str, int]:
    """Execute routine with outer-scope variables.

    Advantages:
    - Natural Python variable syntax
    - No class boilerplate
    - Variables behave like local function variables
    - Matches MUMPS semantics (all locals visible)

    Disadvantages:
    - Must declare `nonlocal` for every variable in every label
    - Easy to forget `nonlocal` → creates new local instead
    - No type hints on variables (unless using annotations)
    - All variables must be declared at top of containing function
    - Harder to pass state to helper functions
    """

    # Shared variables in outer scope
    X: int = 0
    Y: int = 0
    RESULT: int = 0

    # Output buffer
    _output = io.StringIO()

    def write(*args):
        for arg in args:
            if arg == "!":
                _output.write("\n")
            else:
                _output.write(str(arg))

    # Label registry (local to this routine)
    _labels: Dict[str, Callable[[], Optional[str]]] = {}

    def label(name: str):
        def decorator(func: Callable[[], Optional[str]]) -> Callable[[], Optional[str]]:
            _labels[name] = func
            return func

        return decorator

    # =========================================================================
    # Label Functions
    # =========================================================================

    @label("ENTRY")
    def ENTRY() -> Optional[str]:
        nonlocal X  # MUST declare nonlocal!
        X = 10
        write("ENTRY: X=", X, "!")
        return "ADDONE"

    @label("ADDONE")
    def ADDONE() -> Optional[str]:
        nonlocal X  # MUST declare nonlocal!
        X = X + 1
        write("ADDONE: X=", X, "!")
        return "DOUBLE"

    @label("DOUBLE")
    def DOUBLE() -> Optional[str]:
        nonlocal Y  # MUST declare nonlocal!
        Y = X * 2  # X read-only here, no nonlocal needed for reads
        write("DOUBLE: Y=", Y, "!")
        return "SHOW"

    @label("SHOW")
    def SHOW() -> Optional[str]:
        nonlocal RESULT  # MUST declare nonlocal!
        write("SHOW: X=", X, " Y=", Y, "!")
        RESULT = Y
        return None

    # =========================================================================
    # Trampoline
    # =========================================================================

    current_label: Optional[str] = "ENTRY"
    while current_label is not None:
        if current_label not in _labels:
            raise RuntimeError(f"Unknown label: {current_label}")
        func = _labels[current_label]
        current_label = func()

    return _output.getvalue(), RESULT


# =============================================================================
# Rope Refactorability Tests
# =============================================================================


def test_rope_compatibility():
    """Test that Rope can work with this pattern."""
    # 1. Can rename variable X?
    #    - PARTIAL: Must update all `nonlocal X` declarations too

    # 2. Can extract a helper function?
    #    - DIFFICULT: Helper would need its own nonlocal or take params

    # 3. Can find all usages of X?
    #    - YES: But includes both reads and nonlocal declarations

    print("Rope compatibility: MODERATE")
    print("- Rename Symbol: Works but must update all nonlocal declarations")
    print("- Extract Method: Difficult (nonlocal scope issues)")
    print("- Find References: Works but noisy (includes nonlocal lines)")


# =============================================================================
# Demonstration of nonlocal pitfall
# =============================================================================


def demonstrate_nonlocal_bug():
    """Show what happens if you forget nonlocal."""
    X = 10

    def broken_label():
        # BUG: Forgot `nonlocal X`
        X = 20  # This creates a NEW local variable, doesn't modify outer X!
        return X

    def fixed_label():
        nonlocal X
        X = 20  # This modifies the outer X
        return X

    print("\n--- nonlocal Pitfall Demo ---")
    print(f"Before: X = {X}")
    result = broken_label()
    print(f"After broken_label(): X = {X}, returned {result}")  # X still 10!
    result = fixed_label()
    print(f"After fixed_label(): X = {X}, returned {result}")  # X now 20


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    output, result = run_routine()
    print(output)
    print("--- Results ---")
    print(f"Final RESULT: {result}")
    print("Expected: 22 (10+1=11, 11*2=22)")
    print(f"Correct: {result == 22}")
    print()
    test_rope_compatibility()
    demonstrate_nonlocal_bug()
