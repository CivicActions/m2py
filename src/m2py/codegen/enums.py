"""Code generation enumerations.

Defines enums used during Python code generation:
- GotoStrategy: High-level strategy for cross-label GOTO handling
"""

from enum import Enum, auto


class GotoStrategy(Enum):
    """High-level strategy for cross-label GOTO code generation.

    Determines the overall code generation pattern for a routine based on
    its GOTO patterns. Strategy is selected automatically based on ASG
    analysis flags (no user configuration needed).

    Spec 006 Decision: Trampoline pattern handles ALL cross-label GOTOs
    including cyclic patterns. State machine strategy was evaluated but
    deferred - trampoline handles all patterns discovered in VistA analysis.

    Values:
        SIMPLE_FUNCTIONS: Labels as simple Python functions (no cross-label GOTOs).
            - Current Spec 005 behavior
            - Labels generate `def LABEL(): ...`
            - Intra-label GOTOs use if/else restructuring

        TRAMPOLINE: Labels as functions with RoutineState, dispatched via trampoline.
            - Required when `needs_trampoline=True` (any cross-label GOTO)
            - Labels generate `def LABEL(state: RoutineState): ...`
            - Labels return `(next_label, state)` tuple
            - Trampoline `while` loop dispatches to next label
            - Prevents stack overflow for cyclic patterns (A→B→A)
            - RoutineState carries variables across label boundaries
    """

    SIMPLE_FUNCTIONS = auto()
    TRAMPOLINE = auto()
