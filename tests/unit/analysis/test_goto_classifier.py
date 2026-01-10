"""Tests for GOTO classification patterns.

Tests the classify_gotos, resolve_references, and get_loop_exiting_gotos
functions that analyze GOTO control flow.

MUMPS 1995 Reference: §8.2.6 GOTO command
"""

import pytest

from m2py.analysis import (
    resolve_references,
    classify_gotos,
    get_loop_exiting_gotos,
    get_gotos_by_type,
)
from m2py.asg.elements import MRoutine, MLabel, MScope, MCall
from m2py.asg.statements import (
    MGotoStatement,
    MForStatement,
    MSetStatement,
    MAssignment,
)
from m2py.asg.expressions import MVariable, MLiteral
from m2py.asg.enums import GotoType, ForLoopType


class TestExtractGotoFromLine:
    """Test GOTO command extraction via get_goto_info helper."""

    def test_extract_goto_abbreviated(self):
        """G abbreviation should be recognized."""
        from tests.helpers.extraction_helpers import get_goto_info

        result = get_goto_info("\tG LABEL")
        assert result is not None
        name, routine, offset = result
        assert name == "LABEL"
        assert routine is None

    def test_extract_goto_full(self):
        """GOTO full keyword should be recognized."""
        from tests.helpers.extraction_helpers import get_goto_info

        result = get_goto_info("\tGOTO LABEL")
        assert result is not None
        name, routine, offset = result
        assert name == "LABEL"

    def test_extract_no_goto(self):
        """Line without GOTO should return None."""
        from tests.helpers.extraction_helpers import get_goto_info

        result = get_goto_info("\tS X=1 W X")
        assert result is None


class TestClassifyGotos:
    """Test classify_gotos function (T080-T085)."""

    def _create_routine_with_goto(
        self,
        target_label_name: str,
        source_label_name: str = "MAIN",
        routine_name: str = None,
        enclosing_for: bool = False,
    ):
        """Create a routine with a GOTO for testing."""
        routine = MRoutine(name="TEST")

        # Source label with GOTO
        source_label = MLabel(name=source_label_name)
        source_label.body = MScope()

        # Create GOTO statement
        goto_stmt = MGotoStatement()
        call = MCall(name=target_label_name, routine=routine_name)
        goto_stmt.targets.append(call)

        if enclosing_for:
            # Put GOTO inside a FOR loop
            for_stmt = MForStatement()
            for_stmt.body = MScope()
            for_stmt.body.add_statement(goto_stmt)
            source_label.body.add_statement(for_stmt)
        else:
            source_label.body.add_statement(goto_stmt)

        routine.add_label(source_label)

        # Target label
        target_label = MLabel(name="TARGET")
        target_label.body = MScope()
        routine.add_label(target_label)

        return routine

    def test_classify_external_goto(self):
        """GOTO ^ROUTINE should be classified as EXTERNAL (T085)."""
        routine = self._create_routine_with_goto("LABEL", routine_name="OTHER")
        resolve_references(routine)
        classify_gotos(routine)

        # Find the GOTO statement
        goto_stmt = list(routine.labels[0].body.walk_statements())[0]
        assert goto_stmt.goto_type == GotoType.EXTERNAL

    def test_classify_forward_jump(self):
        """GOTO to later label should be FORWARD_JUMP with is_cross_label=True (T080)."""
        routine = self._create_routine_with_goto("TARGET")
        resolve_references(routine)
        classify_gotos(routine)

        goto_stmt = list(routine.labels[0].body.walk_statements())[0]
        # TARGET is a different label, so FORWARD_JUMP with is_cross_label
        assert goto_stmt.goto_type == GotoType.FORWARD_JUMP
        assert goto_stmt.is_cross_label is True

    def test_classify_backward_jump(self):
        """GOTO to earlier label should be BACKWARD_JUMP (T081)."""
        routine = MRoutine(name="TEST")

        # First label
        first = MLabel(name="FIRST")
        first.body = MScope()
        routine.add_label(first)

        # Second label with GOTO FIRST (backward)
        second = MLabel(name="SECOND")
        second.body = MScope()
        goto_stmt = MGotoStatement()
        call = MCall(name="FIRST")
        goto_stmt.targets.append(call)
        second.body.add_statement(goto_stmt)
        routine.add_label(second)

        resolve_references(routine)
        classify_gotos(routine)

        # Should be backward jump
        assert goto_stmt.goto_type == GotoType.BACKWARD_JUMP

    def test_classify_loop_exit(self):
        """GOTO inside single FOR should be LOOP_EXIT (T082)."""
        routine = self._create_routine_with_goto("TARGET", enclosing_for=True)
        resolve_references(routine)
        classify_gotos(routine)

        # Find the GOTO inside the FOR
        for_stmt = routine.labels[0].body.statements[0]
        goto_stmt = for_stmt.body.statements[0]

        assert goto_stmt.goto_type == GotoType.LOOP_EXIT
        assert len(goto_stmt.exits_loops) == 1

    def test_classify_multi_loop_exit(self):
        """GOTO inside nested FORs should be MULTI_LOOP_EXIT (T083)."""
        routine = MRoutine(name="TEST")

        # Source label with nested FOR
        source = MLabel(name="MAIN")
        source.body = MScope()

        # Outer FOR
        outer_for = MForStatement()
        outer_for.body = MScope()

        # Inner FOR with GOTO
        inner_for = MForStatement()
        inner_for.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        inner_for.body.add_statement(goto_stmt)
        outer_for.body.add_statement(inner_for)

        source.body.add_statement(outer_for)
        routine.add_label(source)

        # Target label
        target = MLabel(name="TARGET")
        target.body = MScope()
        routine.add_label(target)

        resolve_references(routine)
        classify_gotos(routine)

        assert goto_stmt.goto_type == GotoType.MULTI_LOOP_EXIT
        assert len(goto_stmt.exits_loops) == 2

    def test_classify_unresolved(self):
        """GOTO to missing label should be UNRESOLVED (T080)."""
        routine = MRoutine(name="TEST")
        label = MLabel(name="MAIN")
        label.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="MISSING")
        goto_stmt.targets.append(call)
        label.body.add_statement(goto_stmt)

        routine.add_label(label)

        resolve_references(routine)
        classify_gotos(routine)

        assert goto_stmt.goto_type == GotoType.UNRESOLVED


class TestGetLoopExitingGotos:
    """Test get_loop_exiting_gotos function (T086)."""

    def test_returns_gotos_with_exits_loops(self):
        """Should return GOTOs that exit FOR loops."""
        routine = MRoutine(name="TEST")

        # Label with FOR containing GOTO
        label = MLabel(name="MAIN")
        label.body = MScope()

        for_stmt = MForStatement()
        for_stmt.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        for_stmt.body.add_statement(goto_stmt)

        label.body.add_statement(for_stmt)
        routine.add_label(label)

        target = MLabel(name="TARGET")
        target.body = MScope()
        routine.add_label(target)

        resolve_references(routine)
        classify_gotos(routine)

        result = get_loop_exiting_gotos(routine)
        assert len(result) == 1
        assert result[0] is goto_stmt


class TestGetGotosByType:
    """Test get_gotos_by_type function for filtering GOTOs by their classification.

    MUMPS 1995 Reference: §8.2.6 GOTO command
    Coverage target: Lines 272-278 in goto_analysis.py
    """

    def test_get_multi_loop_exit_gotos(self):
        """Filter nested loop exits with get_gotos_by_type(MULTI_LOOP_EXIT).

        MUMPS: `FOR I=1:1:10 FOR J=1:1:10 GOTO EXIT` exits both loops.
        """
        routine = MRoutine(name="TEST")

        label = MLabel(name="MAIN")
        label.body = MScope()

        # Nested FOR loops with GOTO
        outer_for = MForStatement()
        outer_for.loop_var = "I"
        outer_for.loop_type = ForLoopType.BOUNDED
        outer_for.body = MScope()

        inner_for = MForStatement()
        inner_for.loop_var = "J"
        inner_for.loop_type = ForLoopType.BOUNDED
        inner_for.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="EXIT")
        goto_stmt.targets.append(call)
        inner_for.body.add_statement(goto_stmt)

        outer_for.body.add_statement(inner_for)
        label.body.add_statement(outer_for)
        routine.add_label(label)

        # Target label outside loops
        target = MLabel(name="EXIT")
        target.body = MScope()
        routine.add_label(target)

        resolve_references(routine)
        classify_gotos(routine)

        result = get_gotos_by_type(routine, GotoType.MULTI_LOOP_EXIT)
        assert len(result) == 1
        assert result[0] is goto_stmt
        assert result[0].goto_type == GotoType.MULTI_LOOP_EXIT

    def test_get_loop_exit_excludes_multi_loop(self):
        """get_gotos_by_type(LOOP_EXIT) excludes MULTI_LOOP_EXIT gotos.

        Single loop exit should be LOOP_EXIT, not MULTI_LOOP_EXIT.
        """
        routine = MRoutine(name="TEST")

        label = MLabel(name="MAIN")
        label.body = MScope()

        # Single FOR with GOTO
        for_stmt = MForStatement()
        for_stmt.loop_var = "I"
        for_stmt.loop_type = ForLoopType.BOUNDED
        for_stmt.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="EXIT")
        goto_stmt.targets.append(call)
        for_stmt.body.add_statement(goto_stmt)

        label.body.add_statement(for_stmt)
        routine.add_label(label)

        target = MLabel(name="EXIT")
        target.body = MScope()
        routine.add_label(target)

        resolve_references(routine)
        classify_gotos(routine)

        loop_exits = get_gotos_by_type(routine, GotoType.LOOP_EXIT)
        multi_exits = get_gotos_by_type(routine, GotoType.MULTI_LOOP_EXIT)
        assert len(loop_exits) == 1
        assert len(multi_exits) == 0
        assert loop_exits[0].goto_type == GotoType.LOOP_EXIT

    def test_get_forward_jump_gotos(self):
        """Filter forward jumps with get_gotos_by_type(FORWARD_JUMP).

        MUMPS: `GOTO LABEL2` from LABEL1 to later LABEL2 is a forward jump.
        """
        routine = MRoutine(name="TEST")

        label1 = MLabel(name="LABEL1")
        label1.body = MScope()

        goto_stmt = MGotoStatement()
        call = MCall(name="LABEL2")
        goto_stmt.targets.append(call)
        label1.body.add_statement(goto_stmt)
        routine.add_label(label1)

        label2 = MLabel(name="LABEL2")
        label2.body = MScope()
        routine.add_label(label2)

        resolve_references(routine)
        classify_gotos(routine)

        result = get_gotos_by_type(routine, GotoType.FORWARD_JUMP)
        assert len(result) == 1
        assert result[0] is goto_stmt

    def test_get_gotos_by_type_returns_empty_for_no_matches(self):
        """get_gotos_by_type returns empty list when no gotos match type."""
        routine = MRoutine(name="TEST")

        label = MLabel(name="MAIN")
        label.body = MScope()

        # GOTO to external routine
        goto_stmt = MGotoStatement()
        call = MCall(name="LABEL", routine="OTHERROUTINE")
        goto_stmt.targets.append(call)
        label.body.add_statement(goto_stmt)
        routine.add_label(label)

        resolve_references(routine)
        classify_gotos(routine)

        # No LOOP_EXIT gotos exist
        result = get_gotos_by_type(routine, GotoType.LOOP_EXIT)
        assert len(result) == 0

    def test_same_routine_explicit_missing_label_is_unresolved(self):
        """GOTO MISSING^SAMEROUTINE where MISSING doesn't exist should be UNRESOLVED.

        MUMPS: When a GOTO explicitly references the same routine with ^ROUTINENAME
        but the target label doesn't exist, it should be UNRESOLVED.
        Coverage target: Lines 166-167 in goto_analysis.py
        """
        routine = MRoutine(name="TEST")

        label = MLabel(name="MAIN")
        label.body = MScope()

        # GOTO MISSING^TEST where MISSING label doesn't exist
        goto_stmt = MGotoStatement()
        call = MCall(name="MISSING", routine="TEST")  # Same routine, missing label
        goto_stmt.targets.append(call)
        label.body.add_statement(goto_stmt)
        routine.add_label(label)

        resolve_references(routine)
        classify_gotos(routine)

        # Should be UNRESOLVED since MISSING label doesn't exist
        assert goto_stmt.goto_type == GotoType.UNRESOLVED


@pytest.mark.analysis
class TestClassifyGotosAdvanced:
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

    def test_goto_same_label_is_backward_jump(self):
        """GOTO to same label (without offset) should be BACKWARD_JUMP.

        G LABEL from within LABEL always jumps to the start of the label,
        which is backward from any position within the label's body.
        This pattern creates an implicit loop.
        """
        routine = MRoutine(name="TEST")

        # Create a single label with GOTO to itself
        label = MLabel(name="MAIN")
        label.body = MScope()
        label.body.parent = label
        routine.add_label(label)

        # Add GOTO MAIN in MAIN (jumps to same label = backward to start)
        goto_stmt = MGotoStatement()
        call = MCall(name="MAIN")
        goto_stmt.targets.append(call)
        label.body.add_statement(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # GOTO to same label without offset = backward to label start
        assert goto_stmt.goto_type == GotoType.BACKWARD_JUMP
        assert goto_stmt.is_cross_label is False

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


@pytest.mark.analysis
class TestHasUnstructuredGoto:
    """Test has_unstructured_goto flag on MRoutine."""

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
