"""Tests for GOTO classification patterns.

Tests the classify_gotos and resolve_references functions
that analyze GOTO control flow.

MUMPS 1995 Reference: §8.2.6 GOTO command
"""

import pytest

from m2py.analysis import (
    resolve_references,
    classify_gotos,
)
from m2py.asg.elements import MRoutine, MLabel, MScope, MCall
from m2py.asg.statements import (
    MGotoStatement,
    MForStatement,
)
from m2py.asg.expressions import MLiteral
from m2py.asg.enums import GotoType, ForLoopType
from m2py.parser import MUMPSParser


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
            for_stmt.body.statements.append(goto_stmt)
            source_label.body.statements.append(for_stmt)
        else:
            source_label.body.statements.append(goto_stmt)

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
        second.body.statements.append(goto_stmt)
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
        inner_for.body.statements.append(goto_stmt)
        outer_for.body.statements.append(inner_for)

        source.body.statements.append(outer_for)
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
        label.body.statements.append(goto_stmt)

        routine.add_label(label)

        resolve_references(routine)
        classify_gotos(routine)

        assert goto_stmt.goto_type == GotoType.UNRESOLVED

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
        label.body.statements.append(goto_stmt)
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
        label.body.statements.append(goto_stmt)

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
        routine.labels[0].body.statements.append(goto_stmt)

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
        for_stmt.body.statements.append(goto_stmt)

        routine.labels[0].body.statements.append(for_stmt)

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
        for_stmt.body.statements.append(goto_stmt)

        routine.labels[0].body.statements.append(for_stmt)

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
        for_stmt.body.statements.append(goto_stmt)

        routine.labels[0].body.statements.append(for_stmt)

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
        inner_for.body.statements.append(goto_stmt)

        outer_for.body.statements.append(inner_for)
        routine.labels[0].body.statements.append(outer_for)

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
        routine.labels[0].body.statements.append(goto_stmt)

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
        routine.labels[0].body.statements.append(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # Should be classified as internal jump, not EXTERNAL
        # Since it jumps to a different label, it's FORWARD_JUMP with is_cross_label
        assert goto_stmt.goto_type != GotoType.EXTERNAL
        assert goto_stmt.goto_type == GotoType.FORWARD_JUMP
        assert goto_stmt.is_cross_label is True

    def test_goto_to_same_label_in_for_is_loop_exit_not_continue(self):
        """GOTO to same label from inside FOR exits loop, does not continue.

        Per MUMPS spec (MDC 3.6.5): "Execution of GOTO effects the immediate
        termination of all FORs in the line containing the GOTO."

        A GOTO to the same label exits the FOR loop and creates a function
        call/recursion, NOT a continue pattern. This is verified against YDB.
        """
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

        # GOTO MAIN inside the FOR - this exits the loop, then calls MAIN
        goto_stmt = MGotoStatement()
        call = MCall(name="MAIN")
        goto_stmt.targets.append(call)
        for_stmt.body.statements.append(goto_stmt)

        main_label.body.statements.append(for_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # GOTO inside FOR loop exits the loop
        assert goto_stmt.goto_type == GotoType.LOOP_EXIT
        assert goto_stmt.exits_loops == [for_stmt]
        # Note: There is no is_loop_continue flag - GOTO cannot create continue semantics

    def test_goto_to_different_label_exits_loop(self):
        """GOTO to different label from inside FOR exits loop."""
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
        for_stmt.body.statements.append(goto_stmt)

        main_label.body.statements.append(for_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # Exits loop to different label
        assert goto_stmt.goto_type == GotoType.LOOP_EXIT
        assert goto_stmt.is_cross_label is True

    def test_goto_outside_for_not_loop_exit(self):
        """GOTO not inside FOR is not marked as loop exit."""
        routine = MRoutine(name="TEST")

        main_label = MLabel(name="MAIN")
        main_label.body = MScope()
        main_label.body.parent = main_label
        routine.add_label(main_label)

        # GOTO MAIN not inside a FOR loop
        goto_stmt = MGotoStatement()
        call = MCall(name="MAIN")
        goto_stmt.targets.append(call)
        main_label.body.statements.append(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # Not in FOR loop, so not a loop exit - classified as backward jump
        assert goto_stmt.goto_type == GotoType.BACKWARD_JUMP
        assert goto_stmt.exits_loops == []


class TestNeedsTrampoline:
    """Test needs_trampoline flag for Spec 006 cross-label GOTOs (T037)."""

    def _create_test_routine(self):
        """Create a basic two-label routine for testing."""
        routine = MRoutine(name="TEST")

        # MAIN label
        main_label = MLabel(name="MAIN")
        main_label.body = MScope()
        main_label.body.parent = main_label
        routine.add_label(main_label)

        # TARGET label
        target_label = MLabel(name="TARGET")
        target_label.body = MScope()
        target_label.body.parent = target_label
        routine.add_label(target_label)

        return routine

    def test_intra_label_forward_no_trampoline(self):
        """Intra-label forward GOTO does NOT require trampoline (T037 case 1).

        Pattern: GOTO within same label uses if/else restructuring,
        not trampoline pattern.
        """
        routine = MRoutine(name="TEST")

        # Single label with intra-label forward GOTO
        label = MLabel(name="MAIN", line_number=1)
        label.body = MScope()
        label.body.parent = label

        # Create a GOTO that targets same label with offset (intra-label forward)
        # G MAIN+5 from within MAIN

        goto_stmt = MGotoStatement(line_number=2)
        call = MCall(name="MAIN")
        call.offset = MLiteral(value=10)  # Forward to line 10
        goto_stmt.targets.append(call)
        label.body.statements.append(goto_stmt)

        routine.add_label(label)

        resolve_references(routine)
        classify_gotos(routine)

        # Should be intra-label (is_cross_label=False)
        assert goto_stmt.is_cross_label is False
        # No trampoline needed for intra-label GOTO
        assert routine.needs_trampoline is False

    def test_forward_cross_label_needs_trampoline(self):
        """Forward cross-label GOTO requires trampoline (T037 case 2).

        Pattern: G TARGET from MAIN where TARGET is a different label.
        """
        routine = self._create_test_routine()

        # Add forward cross-label GOTO in MAIN
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        routine.labels[0].body.statements.append(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # Forward jump to different label
        assert goto_stmt.goto_type == GotoType.FORWARD_JUMP
        assert goto_stmt.is_cross_label is True
        # Cross-label requires trampoline
        assert routine.needs_trampoline is True

    def test_backward_cross_label_needs_trampoline(self):
        """Backward cross-label GOTO requires trampoline (T037 case 3).

        Pattern: G MAIN from TARGET where TARGET comes after MAIN.
        """
        routine = self._create_test_routine()

        # Add backward cross-label GOTO in TARGET
        goto_stmt = MGotoStatement()
        call = MCall(name="MAIN")
        goto_stmt.targets.append(call)
        routine.labels[1].body.statements.append(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # Backward jump to earlier label
        assert goto_stmt.goto_type == GotoType.BACKWARD_JUMP
        assert goto_stmt.is_cross_label is True
        # Cross-label requires trampoline
        assert routine.needs_trampoline is True

    def test_cycle_needs_trampoline(self):
        """Cyclic GOTO pattern A→B→A requires trampoline (T037 case 4).

        Pattern: MAIN→TARGET and TARGET→MAIN creates a cycle.
        """
        routine = self._create_test_routine()

        # Add GOTO TARGET in MAIN
        goto_main_to_target = MGotoStatement()
        call1 = MCall(name="TARGET")
        goto_main_to_target.targets.append(call1)
        routine.labels[0].body.statements.append(goto_main_to_target)

        # Add GOTO MAIN in TARGET (creates cycle)
        goto_target_to_main = MGotoStatement()
        call2 = MCall(name="MAIN")
        goto_target_to_main.targets.append(call2)
        routine.labels[1].body.statements.append(goto_target_to_main)

        resolve_references(routine)
        classify_gotos(routine)

        # Both are cross-label
        assert goto_main_to_target.is_cross_label is True
        assert goto_target_to_main.is_cross_label is True
        # Cycle requires trampoline
        assert routine.needs_trampoline is True

    def test_intra_label_backward_no_trampoline(self):
        """Intra-label backward GOTO does NOT require trampoline.

        Pattern: G MAIN from within MAIN (no offset) creates while loop,
        not trampoline.
        """
        routine = MRoutine(name="TEST")

        label = MLabel(name="MAIN")
        label.body = MScope()
        label.body.parent = label

        # GOTO same label (backward intra-label)
        goto_stmt = MGotoStatement()
        call = MCall(name="MAIN")
        goto_stmt.targets.append(call)
        label.body.statements.append(goto_stmt)

        routine.add_label(label)

        resolve_references(routine)
        classify_gotos(routine)

        # Intra-label backward (creates implicit while loop)
        assert goto_stmt.is_cross_label is False
        assert goto_stmt.goto_type == GotoType.BACKWARD_JUMP
        # No trampoline for intra-label (use while True pattern)
        assert routine.needs_trampoline is False

    def test_loop_exit_cross_label_needs_trampoline(self):
        """Cross-label GOTO from inside FOR loop needs trampoline.

        Pattern: FOR I=1:1:10 G TARGET (where TARGET is different label)
        """
        routine = self._create_test_routine()

        # Add FOR loop with cross-label GOTO in MAIN
        for_stmt = MForStatement()
        for_stmt.body = MScope()
        for_stmt.body.parent = for_stmt

        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        for_stmt.body.statements.append(goto_stmt)

        routine.labels[0].body.statements.append(for_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # Loop exit AND cross-label
        assert goto_stmt.goto_type == GotoType.LOOP_EXIT
        assert goto_stmt.is_cross_label is True
        # Cross-label requires trampoline even with loop exit
        assert routine.needs_trampoline is True

    def test_no_goto_no_trampoline(self):
        """Routine without GOTO doesn't need trampoline."""
        routine = MRoutine(name="TEST")

        label = MLabel(name="MAIN")
        label.body = MScope()
        label.body.parent = label
        routine.add_label(label)

        resolve_references(routine)
        classify_gotos(routine)

        assert routine.needs_trampoline is False


class TestHasOffsetCalls:
    """Test has_offset_calls flag for Spec 007 offset dispatch."""

    def test_no_offset_no_flag(self):
        """Routine without offset calls has has_offset_calls=False."""
        routine = MRoutine(name="TEST")

        label = MLabel(name="MAIN")
        label.body = MScope()
        label.body.parent = label

        # GOTO without offset
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        label.body.statements.append(goto_stmt)

        routine.add_label(label)

        target_label = MLabel(name="TARGET")
        target_label.body = MScope()
        routine.add_label(target_label)

        resolve_references(routine)
        classify_gotos(routine)

        assert routine.has_offset_calls is False

    def test_goto_with_offset_sets_flag(self):
        """GOTO with offset sets has_offset_calls=True."""
        from m2py.asg.enums import LiteralType

        routine = MRoutine(name="TEST")

        label = MLabel(name="MAIN")
        label.body = MScope()
        label.body.parent = label

        # GOTO with offset expression
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        call.offset = MLiteral(value=2, literal_type=LiteralType.INTEGER)
        goto_stmt.targets.append(call)
        label.body.statements.append(goto_stmt)

        routine.add_label(label)

        target_label = MLabel(name="TARGET")
        target_label.body = MScope()
        routine.add_label(target_label)

        resolve_references(routine)
        classify_gotos(routine)

        assert routine.has_offset_calls is True

    def test_do_with_offset_sets_flag(self):
        """DO with offset sets has_offset_calls=True."""
        from m2py.asg.enums import LiteralType
        from m2py.asg.statements import MDoStatement

        routine = MRoutine(name="TEST")

        label = MLabel(name="MAIN")
        label.body = MScope()
        label.body.parent = label

        # DO with offset expression
        do_stmt = MDoStatement()
        call = MCall(name="SUB")
        call.offset = MLiteral(value=1, literal_type=LiteralType.INTEGER)
        do_stmt.targets.append(call)
        label.body.statements.append(do_stmt)

        routine.add_label(label)

        sub_label = MLabel(name="SUB")
        sub_label.body = MScope()
        routine.add_label(sub_label)

        resolve_references(routine)
        classify_gotos(routine)

        assert routine.has_offset_calls is True


class TestGotoAnalysisIntraLabelOffset:
    """Tests for intra-label GOTO with offset (L243-259, L311-313)."""

    def test_goto_with_static_offset_forward(self):
        """G TEST+3 from within TEST — forward offset (L243-259)."""
        parser = MUMPSParser()
        source = "TEST\n\tS X=1\n\tG TEST+3\n\tS Y=2\n\tS Z=3\n\tW Z\n\tQ\n"
        routine = parser.parse(source)
        resolve_references(routine)
        classify_gotos(routine)

    def test_goto_external_routine(self):
        """G LABEL^OTHER — external GOTO."""
        from m2py.asg.statements import MGotoStatement

        parser = MUMPSParser()
        source = "TEST\n\tG LABEL^OTHER\n\tQ\n"
        routine = parser.parse(source)
        resolve_references(routine)
        classify_gotos(routine)
        from m2py.analysis.goto_analysis import GotoType

        # Find GOTOs and check classification directly
        gotos = [
            stmt
            for label in routine.labels
            for stmt in label.body.walk_statements()
            if isinstance(stmt, MGotoStatement) and stmt.goto_type == GotoType.EXTERNAL
        ]
        assert len(gotos) > 0


class TestGotoAnalysisXecuteExternal:
    """Tests for XECUTE external GOTO detection (L631)."""

    def test_xecute_with_goto_external(self):
        """X 'G ^OTHER' — XECUTE containing external GOTO pattern."""
        parser = MUMPSParser()
        source = 'TEST\n\tX "G ^OTHER"\n\tQ\n'
        routine = parser.parse(source)
        resolve_references(routine)
        classify_gotos(routine)


class TestGotoAnalysisDoWithOffset:
    """Tests for DO with offset detection (L596)."""

    def test_do_with_offset(self):
        """D SUB+2 — DO with offset sets has_offset_calls."""
        parser = MUMPSParser()
        source = "TEST\n\tD SUB+2\n\tQ\nSUB\n\tS X=1\n\tS Y=2\n\tW Y\n\tQ\n"
        routine = parser.parse(source)
        resolve_references(routine)
        classify_gotos(routine)


# =============================================================================
# Pattern Compiler LIVE Error Paths
# =============================================================================
