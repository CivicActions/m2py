"""Tests for state↔scope sync around EXTERNAL DO calls in TRAMPOLINE routines.

When a TRAMPOLINE routine (one using RoutineState with static fields) calls
an external subroutine via DO ^ROUTINE, the callee operates on _scope directly.
Before the call, state fields must be pushed into _scope so the callee sees
current values.  After the call returns, _scope must be pulled back into state
fields so the caller sees any modifications the callee made.

Previously, these per-field syncs were only emitted for TRAMPOLINE routines
with dynamic locals (state._locals dict).  Routines with static state_vars
(the common case) had NO sync around external DO calls, so:
  1. External routines couldn't see the caller's current variable values.
  2. The caller couldn't see changes made by the external routine.

The fix adds per-field emit_state_var_to_scope (before) and
emit_scope_var_to_state (after) for TRAMPOLINE + static state_vars.

Note: state_vars only includes variables that cross label boundaries (used in
more than one label). Variables local to a single label are accessed via _scope
directly and don't need sync.
"""

from __future__ import annotations

import pytest


@pytest.mark.codegen
class TestExternalDoStateSyncCodegen:
    """Verify generated Python contains per-field sync around external DO calls.

    For a variable to become a state_var (stored in RoutineState), it must be
    used across multiple labels.  The GOTO ensures TRAMPOLINE strategy.
    """

    def test_trampoline_external_do_emits_state_to_scope_before(self, generate_python):
        """TRAMPOLINE routine syncs state→scope BEFORE external DO call.

        A is set in TEST and read in END (crosses label boundary → state_var).
        Before D ^SETTER, state.A must be pushed to _scope['A'].
        """
        source = """\
TEST
 S A=1
 D ^SETTER
 G END
END
 W A
 Q
"""
        python_code = generate_python(source)

        # A should be a state_var (used in both TEST and END)
        assert "state.A" in python_code
        # Should have MArray wrapping for state→scope sync before the call
        assert "_scope['A']" in python_code
        assert "_m.value = _v._value if isinstance(_v, MArray) else _v" in python_code

    def test_trampoline_external_do_emits_scope_to_state_after(self, generate_python):
        """TRAMPOLINE routine syncs scope→state AFTER external DO call.

        After D ^SETTER returns, _scope['A'] must be synced back to state.A.
        """
        source = """\
TEST
 S A=0
 D ^SETTER
 G END
END
 W A
 Q
"""
        python_code = generate_python(source)

        lines = python_code.split("\n")
        # Find the run_with_goto_support call (the external DO)
        do_line_idx = None
        for i, line in enumerate(lines):
            if "run_with_goto_support" in line and "SETTER" in line:
                do_line_idx = i
                break

        assert do_line_idx is not None, "Expected external DO call for SETTER"

        # After the DO call, there should be scope→state sync for A
        after_do = "\n".join(lines[do_line_idx + 1 : do_line_idx + 10])
        assert "state.A" in after_do, (
            f"Expected scope→state sync for A after external DO.\n"
            f"Lines after DO:\n{after_do}"
        )

    def test_multiple_state_vars_all_synced(self, generate_python):
        """All state_vars are synced, not just one."""
        source = """\
TEST
 S A=1,B=2,C=3
 D ^OTHER
 G END
END
 W A," ",B," ",C
 Q
"""
        python_code = generate_python(source)

        # All three cross label boundary → all should appear in sync
        for var in ("A", "B", "C"):
            assert f"state.{var}" in python_code, (
                f"state.{var} not found in generated code"
            )
            assert f"_scope['{var}']" in python_code, f"_scope['{var}'] not found"

    def test_simple_functions_no_state_sync(self, generate_python):
        """SIMPLE_FUNCTIONS routines (no GOTOs) don't use state_var sync.

        Without GOTOs, the routine uses SIMPLE_FUNCTIONS strategy and
        accesses _scope directly — no RoutineState, no sync needed.
        """
        source = """\
TEST
 S X=1
 D ^OTHER
 W X
 Q
"""
        python_code = generate_python(source)

        # SIMPLE_FUNCTIONS uses _scope directly, not state.X
        assert "state.X" not in python_code


@pytest.mark.codegen
class TestExternalDoStateSyncExecution:
    """End-to-end tests verifying state↔scope sync with internal DO in TRAMPOLINE.

    Uses internal subroutine calls combined with GOTOs to exercise the
    TRAMPOLINE sync mechanism without needing external routine imports.
    """

    def test_subroutine_modifies_cross_label_var(self, execute_mumps):
        """Subroutine modifies a state_var, which is visible after GOTO.

        A is used in both TEST and END → state_var.  SUB modifies A.
        After GOTO END, the updated A value should be visible.
        """
        source = """\
TEST
 S A=0
 D SUB
 G DONE
DONE
 W A
 Q
SUB
 S A=42
 Q
"""
        result = execute_mumps(source)
        assert result.success is True
        assert result.output == "42"

    def test_multiple_vars_synced_across_labels(self, execute_mumps):
        """Multiple state_vars updated by subroutine visible after GOTO."""
        source = """\
TEST
 S A=1,B=2,C=3
 D SUB
 G DONE
DONE
 W A," ",B," ",C
 Q
SUB
 S A=10,B=20,C=30
 Q
"""
        result = execute_mumps(source)
        assert result.success is True
        assert result.output == "10 20 30"

    def test_caller_var_visible_to_callee_via_scope(self, execute_mumps):
        """State_var set by TRAMPOLINE caller is visible to subroutine.

        State→scope sync before the DO ensures callee reads current value.
        """
        source = """\
TEST
 S X=99
 D SUB
 G DONE
DONE
 Q
SUB
 W X
 Q
"""
        result = execute_mumps(source)
        assert result.success is True
        assert result.output == "99"

    def test_array_var_survives_do_in_trampoline(self, execute_mumps):
        """Array variable with subscripts preserved through DO in TRAMPOLINE.

        Both the root value and subscripts should survive the sync.
        """
        source = """\
TEST
 S IO="dev",IO(0)="term"
 D SUB
 G DONE
DONE
 W IO," ",IO(0)," ",$D(IO)
 Q
SUB
 Q
"""
        result = execute_mumps(source)
        assert result.success is True
        assert result.output == "dev term 11"

    def test_kill_propagation_across_goto(self, execute_mumps):
        """KILL X in one label makes $D(X)=0 in subsequent GOTO target.

        This tests the ._value kill propagation fix: when K X sets
        state.X = MArray() (_value=None), the state→scope sync must
        propagate None (not '') so $DATA returns 0 in the target label.
        """
        source = """\
TEST
 S X=42
 K X
 G DONE
DONE
 W $D(X)
 Q
"""
        result = execute_mumps(source)
        assert result.success is True
        assert result.output == "0"

    def test_kill_then_set_across_goto(self, execute_mumps):
        """SET after KILL: final value visible after GOTO."""
        source = """\
TEST
 S X=1
 K X
 S X=99
 G DONE
DONE
 W X," ",$D(X)
 Q
"""
        result = execute_mumps(source)
        assert result.success is True
        assert result.output == "99 1"

    def test_array_var_only_synced_across_goto(self, execute_mumps):
        """Variable only in array_vars (not state_vars) is synced across GOTO.

        This tests that array_vars are included in the sync loops: a variable
        with subscripts that crosses label boundaries must be synced even if
        it only appears in array_vars (not state_vars).
        """
        source = """\
TEST
 S DICO(1)=0
 D SUB
 G DONE
DONE
 W DICO(1)
 Q
SUB
 S DICO(1)=42
 Q
"""
        result = execute_mumps(source)
        assert result.success is True
        assert result.output == "42"
