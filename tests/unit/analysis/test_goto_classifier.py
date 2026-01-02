"""Tests for GOTO classification analysis.

Migrated from: tests/unit/test_goto_for_analysis.py::TestClassifyGotos
Migrated from: tests/unit/test_goto_for_analysis.py::TestHasUnstructuredGoto

Tests for:
- classify_gotos() function
- GOTO type classification (FORWARD_JUMP, LOOP_EXIT, MULTI_LOOP_EXIT, etc.)
- has_internal_goto flag on FOR loops
- exits_loops and exit_points bidirectional references
- is_loop_continue detection
- has_unstructured_goto flag on routines
"""

from m2py.asg.elements import MRoutine, MLabel, MCall, MScope
from m2py.asg.statements import (
    MGotoStatement,
    MForStatement,
    MSetStatement,
    MAssignment,
)
from m2py.asg.expressions import MVariable, MLiteral
from m2py.asg.enums import GotoType, ForLoopType
from m2py.analysis import resolve_references, classify_gotos


class TestClassifyGotos:
    """Test classify_gotos function.

    Migrated from: tests/unit/test_goto_for_analysis.py::TestClassifyGotos
    """

    def _create_test_routine(self) -> MRoutine:
        """Create a test routine with labels."""
        routine = MRoutine(name="TEST")

        main_label = MLabel(name="MAIN")
        main_label.body = MScope()
        main_label.body.parent = main_label

        target_label = MLabel(name="TARGET")
        target_label.body = MScope()
        target_label.body.parent = target_label

        routine.add_label(main_label)
        routine.add_label(target_label)

        return routine

    def test_goto_same_label_is_forward_jump(self):
        """GOTO to same label should be FORWARD_JUMP (intra-label)."""
        routine = MRoutine(name="TEST")

        # Create a single label with GOTO to itself
        label = MLabel(name="MAIN")
        label.body = MScope()
        label.body.parent = label
        routine.add_label(label)

        # Add GOTO MAIN in MAIN (jumps to same label)
        goto_stmt = MGotoStatement()
        call = MCall(name="MAIN")
        goto_stmt.targets.append(call)
        label.body.add_statement(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # GOTO to same label is FORWARD_JUMP (within label scope)
        assert goto_stmt.goto_type == GotoType.FORWARD_JUMP

    def test_goto_cross_label_forward(self):
        """GOTO to later label should be FORWARD_JUMP with is_cross_label=True."""
        routine = self._create_test_routine()

        # Add GOTO TARGET to MAIN label
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        routine.labels[0].body.add_statement(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # GOTO to later label from earlier is FORWARD_JUMP with is_cross_label=True
        assert goto_stmt.goto_type == GotoType.FORWARD_JUMP
        assert goto_stmt.is_cross_label is True

    def test_goto_inside_for_is_loop_exit(self):
        """GOTO inside FOR loop should be classified as LOOP_EXIT."""
        routine = self._create_test_routine()

        # Create FOR loop with GOTO inside
        for_stmt = MForStatement()
        for_stmt.loop_var = "I"
        for_stmt.loop_type = ForLoopType.BOUNDED
        for_stmt.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        for_stmt.body.add_statement(goto_stmt)

        routine.labels[0].body.add_statement(for_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # GOTO inside FOR should be LOOP_EXIT
        assert goto_stmt.goto_type == GotoType.LOOP_EXIT
        assert len(goto_stmt.exits_loops) == 1
        assert goto_stmt.exits_loops[0] is for_stmt

    def test_has_internal_goto_set_on_for(self):
        """FOR loop should have has_internal_goto=True when containing GOTO."""
        routine = self._create_test_routine()

        # Create FOR loop with GOTO inside
        for_stmt = MForStatement()
        for_stmt.loop_var = "I"
        for_stmt.loop_type = ForLoopType.BOUNDED
        for_stmt.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        for_stmt.body.add_statement(goto_stmt)

        routine.labels[0].body.add_statement(for_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # FOR should have has_internal_goto=True
        assert for_stmt.has_internal_goto is True

    def test_exit_points_bidirectional(self):
        """FOR's exit_points should contain GOTOs that exit it."""
        routine = self._create_test_routine()

        # Create FOR loop with GOTO inside
        for_stmt = MForStatement()
        for_stmt.loop_var = "I"
        for_stmt.loop_type = ForLoopType.BOUNDED
        for_stmt.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        for_stmt.body.add_statement(goto_stmt)

        routine.labels[0].body.add_statement(for_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # Bidirectional: GOTO.exits_loops -> FOR, FOR.exit_points -> GOTO
        assert goto_stmt in for_stmt.exit_points
        assert for_stmt in goto_stmt.exits_loops

    def test_nested_for_multi_loop_exit(self):
        """GOTO inside nested FOR loops should be MULTI_LOOP_EXIT."""
        routine = self._create_test_routine()

        # Create nested FOR loops with GOTO in inner loop
        outer_for = MForStatement()
        outer_for.loop_var = "I"
        outer_for.loop_type = ForLoopType.BOUNDED
        outer_for.body = MScope()

        inner_for = MForStatement()
        inner_for.loop_var = "J"
        inner_for.loop_type = ForLoopType.BOUNDED
        inner_for.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        inner_for.body.add_statement(goto_stmt)

        outer_for.body.add_statement(inner_for)
        routine.labels[0].body.add_statement(outer_for)

        resolve_references(routine)
        classify_gotos(routine)

        # GOTO exits both loops
        assert goto_stmt.goto_type == GotoType.MULTI_LOOP_EXIT
        assert len(goto_stmt.exits_loops) == 2
        assert outer_for in goto_stmt.exits_loops
        assert inner_for in goto_stmt.exits_loops

    def test_external_goto(self):
        """GOTO to external routine should be EXTERNAL."""
        routine = self._create_test_routine()

        goto_stmt = MGotoStatement()
        call = MCall(name="LABEL", routine="OTHERROUTINE")
        goto_stmt.targets.append(call)
        routine.labels[0].body.add_statement(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        assert goto_stmt.goto_type == GotoType.EXTERNAL

    def test_same_routine_goto_not_external(self):
        """GOTO to same routine (label^SAMEROUTINE) should not be EXTERNAL."""
        routine = self._create_test_routine()

        # GOTO TARGET^TEST where routine name is TEST
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET", routine="TEST")  # Same routine
        goto_stmt.targets.append(call)
        routine.labels[0].body.add_statement(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # Should be classified as internal jump, not EXTERNAL
        # Since it jumps to a different label, it's FORWARD_JUMP with is_cross_label
        assert goto_stmt.goto_type != GotoType.EXTERNAL
        assert goto_stmt.goto_type == GotoType.FORWARD_JUMP
        assert goto_stmt.is_cross_label is True

    def test_is_loop_continue_when_goto_back_to_label_in_for(self):
        """GOTO back to same label from inside FOR should set is_loop_continue."""
        routine = MRoutine(name="TEST")

        # Create MAIN label with FOR loop containing GOTO MAIN
        main_label = MLabel(name="MAIN")
        main_label.body = MScope()
        main_label.body.parent = main_label
        routine.add_label(main_label)

        # Create FOR loop
        for_stmt = MForStatement()
        for_stmt.loop_var = "I"
        for_stmt.loop_type = ForLoopType.BOUNDED
        for_stmt.body = MScope()

        # GOTO MAIN inside the FOR - this is a "continue" pattern
        goto_stmt = MGotoStatement()
        call = MCall(name="MAIN")
        goto_stmt.targets.append(call)
        for_stmt.body.add_statement(goto_stmt)

        main_label.body.add_statement(for_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # Should be marked as loop continue
        assert goto_stmt.is_loop_continue is True
        assert goto_stmt.goto_type == GotoType.LOOP_EXIT  # Still exits the loop

    def test_is_loop_continue_false_for_cross_label_exit(self):
        """GOTO to different label from inside FOR should NOT set is_loop_continue."""
        routine = MRoutine(name="TEST")

        # Create MAIN and TARGET labels
        main_label = MLabel(name="MAIN")
        main_label.body = MScope()
        main_label.body.parent = main_label
        routine.add_label(main_label)

        target_label = MLabel(name="TARGET")
        target_label.body = MScope()
        target_label.body.parent = target_label
        routine.add_label(target_label)

        # Create FOR loop with GOTO TARGET
        for_stmt = MForStatement()
        for_stmt.loop_var = "I"
        for_stmt.loop_type = ForLoopType.BOUNDED
        for_stmt.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        for_stmt.body.add_statement(goto_stmt)

        main_label.body.add_statement(for_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # Should NOT be marked as loop continue (exits to different label)
        assert goto_stmt.is_loop_continue is False
        assert goto_stmt.goto_type == GotoType.LOOP_EXIT

    def test_is_loop_continue_false_when_not_in_for(self):
        """GOTO not inside FOR should have is_loop_continue=False."""
        routine = MRoutine(name="TEST")

        main_label = MLabel(name="MAIN")
        main_label.body = MScope()
        main_label.body.parent = main_label
        routine.add_label(main_label)

        # GOTO MAIN not inside a FOR loop
        goto_stmt = MGotoStatement()
        call = MCall(name="MAIN")
        goto_stmt.targets.append(call)
        main_label.body.add_statement(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # Should NOT be marked as loop continue (not in a FOR loop)
        assert goto_stmt.is_loop_continue is False


class TestHasUnstructuredGoto:
    """Test has_unstructured_goto flag on MRoutine.

    Migrated from: tests/unit/test_goto_for_analysis.py::TestHasUnstructuredGoto
    """

    def _create_test_routine(self) -> MRoutine:
        """Create a test routine with labels."""
        routine = MRoutine(name="TEST")

        main_label = MLabel(name="MAIN")
        main_label.body = MScope()
        main_label.body.parent = main_label

        target_label = MLabel(name="TARGET")
        target_label.body = MScope()
        target_label.body.parent = target_label

        routine.add_label(main_label)
        routine.add_label(target_label)

        return routine

    def test_no_gotos_is_structured(self):
        """Routine without GOTOs should have has_unstructured_goto=False."""
        routine = self._create_test_routine()

        # Add a simple SET statement, no GOTO
        set_stmt = MSetStatement()
        set_stmt.assignments = [
            MAssignment(target=MVariable(name="X"), value=MLiteral(value=1))
        ]
        routine.labels[0].body.add_statement(set_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        assert routine.has_unstructured_goto is False

    def test_loop_exit_goto_is_structured(self):
        """GOTO that just exits a FOR loop is structured (can use break)."""
        routine = self._create_test_routine()

        # Create FOR loop with GOTO TARGET inside
        for_stmt = MForStatement()
        for_stmt.loop_var = "I"
        for_stmt.loop_type = ForLoopType.BOUNDED
        for_stmt.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        for_stmt.body.add_statement(goto_stmt)

        routine.labels[0].body.add_statement(for_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # LOOP_EXIT can be translated to break, so it's structured
        assert goto_stmt.goto_type == GotoType.LOOP_EXIT
        assert routine.has_unstructured_goto is False

    def test_cross_label_forward_is_unstructured(self):
        """GOTO to different label (is_cross_label=True, not in FOR) is unstructured."""
        routine = self._create_test_routine()

        # Add GOTO TARGET to MAIN label (not in a FOR loop)
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        routine.labels[0].body.add_statement(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # Cross-label jump is FORWARD_JUMP with is_cross_label=True
        assert goto_stmt.goto_type == GotoType.FORWARD_JUMP
        assert goto_stmt.is_cross_label is True
        # Cross-label jump needs restructuring
        assert routine.has_unstructured_goto is True

    def test_backward_jump_is_unstructured(self):
        """GOTO to earlier label is unstructured (creates implicit loop)."""
        routine = MRoutine(name="TEST")

        # Create labels in order: TARGET, MAIN
        target_label = MLabel(name="TARGET")
        target_label.body = MScope()
        target_label.body.parent = target_label

        main_label = MLabel(name="MAIN")
        main_label.body = MScope()
        main_label.body.parent = main_label

        routine.add_label(target_label)
        routine.add_label(main_label)

        # Add GOTO TARGET in MAIN (jumps backward)
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        main_label.body.add_statement(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        assert goto_stmt.goto_type == GotoType.BACKWARD_JUMP
        assert routine.has_unstructured_goto is True

    def test_external_goto_is_structured(self):
        """GOTO to external routine is structured (becomes function call)."""
        routine = self._create_test_routine()

        goto_stmt = MGotoStatement()
        call = MCall(name="LABEL", routine="OTHERROUTINE")
        goto_stmt.targets.append(call)
        routine.labels[0].body.add_statement(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        assert goto_stmt.goto_type == GotoType.EXTERNAL
        assert routine.has_unstructured_goto is False

    def test_unresolved_goto_is_unstructured(self):
        """GOTO with unresolved target is unstructured (needs runtime dispatch)."""
        routine = self._create_test_routine()

        # Create GOTO to nonexistent label
        goto_stmt = MGotoStatement()
        call = MCall(name="NONEXISTENT")  # Doesn't exist
        goto_stmt.targets.append(call)
        routine.labels[0].body.add_statement(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        assert goto_stmt.goto_type == GotoType.UNRESOLVED
        assert routine.has_unstructured_goto is True
