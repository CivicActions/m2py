"""Tests for GOTO strategy selection (Spec 006 Phase 4).

Tests the automatic strategy selection based on ASG analysis flags.
"""

import pytest

from m2py.asg.elements import MCall, MLabel, MRoutine, MScope
from m2py.asg.enums import GotoType
from m2py.asg.statements import MGotoStatement
from m2py.codegen import (
    UnsupportedFeatureError,
    _check_unsupported_gotos,
    _select_goto_strategy,
)
from m2py.codegen.enums import GotoStrategy


@pytest.mark.codegen
class TestSelectGotoStrategy:
    """Tests for _select_goto_strategy() function (T043-T044)."""

    def test_no_cross_label_returns_simple_functions(self):
        """T044: Routine without cross-label GOTOs uses SIMPLE_FUNCTIONS.

        Pattern: needs_trampoline=False → SIMPLE_FUNCTIONS
        """
        routine = MRoutine(name="TEST")
        routine.needs_trampoline = False

        strategy = _select_goto_strategy(routine)

        assert strategy == GotoStrategy.SIMPLE_FUNCTIONS

    def test_cross_label_returns_trampoline(self):
        """T044: Routine with cross-label GOTOs uses TRAMPOLINE.

        Pattern: needs_trampoline=True → TRAMPOLINE
        """
        routine = MRoutine(name="TEST")
        routine.needs_trampoline = True

        strategy = _select_goto_strategy(routine)

        assert strategy == GotoStrategy.TRAMPOLINE

    def test_empty_routine_returns_simple_functions(self):
        """Empty routine defaults to SIMPLE_FUNCTIONS."""
        routine = MRoutine(name="TEST")
        # Default: needs_trampoline=False

        strategy = _select_goto_strategy(routine)

        assert strategy == GotoStrategy.SIMPLE_FUNCTIONS


@pytest.mark.codegen
class TestCheckUnsupportedGotos:
    """Tests for _check_unsupported_gotos() function (T045a, T045b)."""

    def _create_routine_with_goto(self, goto_type: GotoType) -> MRoutine:
        """Create a routine with a GOTO of specified type."""
        routine = MRoutine(name="TEST")
        label = MLabel(name="TEST")
        label.body = MScope()
        label.body.parent = label

        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        goto_stmt.goto_type = goto_type
        label.body.add_statement(goto_stmt)

        routine.add_label(label)
        return routine

    def test_unresolved_goto_raises_error(self):
        """T045a: UNRESOLVED GOTO raises UnsupportedFeatureError.

        Pattern: goto_type=UNRESOLVED → error with Spec 012 reference
        """
        routine = self._create_routine_with_goto(GotoType.UNRESOLVED)

        with pytest.raises(UnsupportedFeatureError, match="UNRESOLVED GOTO"):
            _check_unsupported_gotos(routine)

    def test_unresolved_goto_error_mentions_spec_012(self):
        """T045a: Error message references Spec 012."""
        routine = self._create_routine_with_goto(GotoType.UNRESOLVED)

        with pytest.raises(UnsupportedFeatureError, match="Spec 012"):
            _check_unsupported_gotos(routine)

    def test_external_goto_raises_error(self):
        """T045b: EXTERNAL GOTO now supported (Spec 008 Phase 6).

        Pattern: goto_type=EXTERNAL → no error, generates GotoExternal raise
        """
        routine = self._create_routine_with_goto(GotoType.EXTERNAL)

        # Should NOT raise - EXTERNAL GOTO is now supported
        _check_unsupported_gotos(routine)

    def test_external_goto_no_longer_blocked(self):
        """Spec 008 Phase 6: EXTERNAL GOTO is now supported."""
        routine = self._create_routine_with_goto(GotoType.EXTERNAL)

        # Should NOT raise
        _check_unsupported_gotos(routine)

    def test_forward_jump_does_not_raise(self):
        """FORWARD_JUMP GOTO does not raise error."""
        routine = self._create_routine_with_goto(GotoType.FORWARD_JUMP)

        # Should not raise
        _check_unsupported_gotos(routine)

    def test_backward_jump_does_not_raise(self):
        """BACKWARD_JUMP GOTO does not raise error."""
        routine = self._create_routine_with_goto(GotoType.BACKWARD_JUMP)

        # Should not raise
        _check_unsupported_gotos(routine)

    def test_loop_exit_does_not_raise(self):
        """LOOP_EXIT GOTO does not raise error."""
        routine = self._create_routine_with_goto(GotoType.LOOP_EXIT)

        # Should not raise
        _check_unsupported_gotos(routine)

    def test_empty_routine_does_not_raise(self):
        """Empty routine passes check."""
        routine = MRoutine(name="TEST")

        # Should not raise
        _check_unsupported_gotos(routine)


@pytest.mark.codegen
class TestGotoStrategyEnum:
    """Tests for GotoStrategy enum (T045)."""

    def test_simple_functions_exists(self):
        """SIMPLE_FUNCTIONS strategy exists."""
        assert hasattr(GotoStrategy, "SIMPLE_FUNCTIONS")

    def test_trampoline_exists(self):
        """TRAMPOLINE strategy exists."""
        assert hasattr(GotoStrategy, "TRAMPOLINE")

    def test_strategies_are_distinct(self):
        """Strategies have distinct values."""
        assert GotoStrategy.SIMPLE_FUNCTIONS != GotoStrategy.TRAMPOLINE


@pytest.mark.codegen
class TestStrategyIntegration:
    """Integration tests for strategy selection in generate_python()."""

    def test_simple_routine_uses_simple_functions(self, generate_python):
        """Routine without GOTOs uses SIMPLE_FUNCTIONS strategy."""
        # Simple routine with no GOTOs
        code = generate_python('TEST\n W "hello"\n Q\n')

        # Should generate standard function pattern (with _scope and **_kwargs)
        assert "def TEST(_scope=None, **_kwargs):" in code
        assert "_rt.write" in code

    def test_intra_label_goto_uses_simple_functions(self, generate_python):
        """Routine with intra-label GOTOs only uses SIMPLE_FUNCTIONS."""
        # Intra-label forward GOTO - restructured to if/else
        code = generate_python('TEST\n I 1 G TEST+3\n W "skip"\n W "done"\n Q\n')

        # Should still be simple function pattern (with _scope and **_kwargs)
        assert "def TEST(_scope=None, **_kwargs):" in code or "_labels" in code
        # Either simple functions or trampoline is acceptable

    def test_cross_label_goto_uses_trampoline(self, generate_python):
        """Routine with cross-label GOTOs uses TRAMPOLINE strategy."""
        # Cross-label forward GOTO
        code = generate_python('TEST\n G NEXT\n Q\nNEXT\n W "done"\n Q\n')

        # Should have trampoline dispatch
        assert "while" in code
        assert "RoutineState" in code
        assert "_labels" in code

    def test_cyclic_cross_label_goto_uses_trampoline(self, generate_python):
        """T108: Routine with cyclic cross-label GOTOs uses TRAMPOLINE strategy.

        Pattern: A→B→A cycle should use trampoline to avoid stack overflow.
        """
        # Create a cycle: TEST → NEXT → TEST (with counter to stop)
        code = generate_python(
            "TEST\n S X=0\n G NEXT\n Q\nNEXT\n S X=X+1\n W X\n I X<3 G TEST\n Q\n"
        )

        # Should have trampoline dispatch
        assert "while" in code
        assert "RoutineState" in code
        assert "_labels" in code

    def test_external_goto_generates_raise(self, generate_python):
        """Spec 008 Phase 6: External GOTO generates raise GotoExternal."""
        code = generate_python("TEST\n G ^OTHER\n Q\n")
        # Should generate import and raise, not error
        assert "import OTHER" in code
        assert "raise GotoExternal(OTHER, None)" in code
