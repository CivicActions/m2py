"""Tests for reference resolution functions.

Tests the resolver's ability to:
- Scan for MCall objects in GOTO/DO statements
- Resolve label references by name
- Populate back-references (callers, goto_sources)
- Collect global references

MUMPS 1995 Reference: §8.2.3 DO, §8.2.6 GOTO
"""

import pytest

from m2py.asg.elements import MRoutine, MLabel, MCall, MScope
from m2py.asg.statements import MGotoStatement, MDoStatement
from m2py.analysis import resolve_references


@pytest.mark.analysis
class TestResolveReferences:
    """Test resolve_references function (T074-T076)."""

    def _create_test_routine(self) -> MRoutine:
        """Create a test routine with labels and statements."""
        routine = MRoutine(name="TEST")

        # Create labels
        main_label = MLabel(name="MAIN")
        main_label.body = MScope()
        main_label.body.parent = main_label

        target_label = MLabel(name="TARGET")
        target_label.body = MScope()
        target_label.body.parent = target_label

        subroutine_label = MLabel(name="SUBROUTINE")
        subroutine_label.body = MScope()
        subroutine_label.body.parent = subroutine_label

        routine.add_label(main_label)
        routine.add_label(target_label)
        routine.add_label(subroutine_label)

        return routine

    def test_resolve_goto_to_local_label(self):
        """GOTO to local label should be resolved (T075)."""
        routine = self._create_test_routine()

        # Add GOTO TARGET to MAIN label
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        routine.labels[0].body.statements.append(goto_stmt)

        # Resolve
        resolve_references(routine)

        # Verify resolution
        assert call.is_resolved
        assert call.target is not None
        assert call.target.name == "TARGET"

    def test_resolve_sets_back_reference(self):
        """Resolved GOTO should add back-reference to label (T077)."""
        routine = self._create_test_routine()

        # Add GOTO TARGET to MAIN label
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        routine.labels[0].body.statements.append(goto_stmt)

        # Resolve
        resolve_references(routine)

        # Check back-reference
        target_label = routine.get_label("TARGET")
        assert len(target_label.goto_sources) == 1
        assert target_label.goto_sources[0] is call

    def test_resolve_do_adds_to_callers(self):
        """Resolved DO should add to label.callers (T077)."""
        routine = self._create_test_routine()

        # Add DO SUBROUTINE to MAIN label
        do_stmt = MDoStatement()
        call = MCall(name="SUBROUTINE")
        do_stmt.targets.append(call)
        routine.labels[0].body.statements.append(do_stmt)

        # Resolve
        resolve_references(routine)

        # Check back-reference
        sub_label = routine.get_label("SUBROUTINE")
        assert len(sub_label.callers) == 1
        assert sub_label.callers[0] is call

    def test_unresolved_label(self):
        """GOTO to missing label should be marked unresolved."""
        routine = self._create_test_routine()

        # Add GOTO NONEXISTENT to MAIN label
        goto_stmt = MGotoStatement()
        call = MCall(name="NONEXISTENT")
        goto_stmt.targets.append(call)
        routine.labels[0].body.statements.append(goto_stmt)

        # Resolve
        resolve_references(routine)

        # Verify not resolved
        assert not call.is_resolved
        assert call.target is None

    def test_external_call_not_resolved(self):
        """External call (^routine) should not be resolved locally."""
        routine = self._create_test_routine()

        # Add GOTO LABEL^OTHER to MAIN label
        goto_stmt = MGotoStatement()
        call = MCall(name="LABEL", routine="OTHER")
        goto_stmt.targets.append(call)
        routine.labels[0].body.statements.append(goto_stmt)

        # Resolve
        resolve_references(routine)

        # External calls are not resolved locally
        assert not call.is_resolved

    def test_self_routine_call_is_resolved(self):
        """Call to label^SAME_ROUTINE should be resolved as local.

        This is a regression test for MVTS V1OV2 which uses patterns like:
        G 691^V1OV2  ; inside routine V1OV2

        The routine name on the call matches the current routine, so it
        should be treated as a local call and resolved.
        """
        routine = self._create_test_routine()  # name="TEST"

        # Add GOTO TARGET^TEST to MAIN label (same routine name)
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET", routine="TEST")
        goto_stmt.targets.append(call)
        routine.labels[0].body.statements.append(goto_stmt)

        # Resolve
        resolve_references(routine)

        # Self-routine calls should be resolved locally
        assert call.is_resolved
        assert call.target is not None
        assert call.target.name == "TARGET"

    def test_multiple_gotos_to_same_label(self):
        """Multiple GOTOs to same label should all be in back-references."""
        routine = self._create_test_routine()

        # Add two GOTOs to TARGET from MAIN
        goto1 = MGotoStatement()
        call1 = MCall(name="TARGET")
        goto1.targets.append(call1)
        routine.labels[0].body.statements.append(goto1)

        goto2 = MGotoStatement()
        call2 = MCall(name="TARGET")
        goto2.targets.append(call2)
        routine.labels[0].body.statements.append(goto2)

        # Resolve
        resolve_references(routine)

        # Both should be in back-references
        target_label = routine.get_label("TARGET")
        assert len(target_label.goto_sources) == 2


@pytest.mark.analysis
class TestCallTypePopulation:
    """Regression tests for call_type population during reference resolution.

    Tests that MCall.call_type is correctly set during resolve_references().
    Merged from test_resolver_call_types.py.
    """

    def test_local_do_call_is_resolved_with_label_call_type(self, mugj_inref_dir):
        """Local DO call should have CallType.LABEL_CALL after resolution."""
        from m2py.parser.parser import MUMPSParser
        from m2py.asg.enums import CallType

        parser = MUMPSParser()
        routine = parser.parse_file(mugj_inref_dir / "V1BOA1.m")
        parser.resolve_references(routine)

        label = routine.get_label("22")
        first_do = next(
            stmt
            for stmt in label.body.walk_statements()
            if stmt.__class__.__name__ == "MDoStatement"
        )
        call = first_do.targets[0]

        assert call.is_resolved is True
        assert call.target is not None
        assert call.target.name == "EXAMINER"
        assert call.call_type == CallType.LABEL_CALL

    def test_external_do_call_marks_routine_call_type(self, mugj_inref_dir):
        """External DO call (^ROUTINE) should have CallType.ROUTINE_CALL."""
        from m2py.parser.parser import MUMPSParser
        from m2py.asg.enums import CallType

        parser = MUMPSParser()
        routine = parser.parse_file(mugj_inref_dir / "V1BOA1.m")
        parser.resolve_references(routine)

        end_label = routine.get_label("END")
        ext_do = next(
            stmt
            for stmt in end_label.body.walk_statements()
            if stmt.__class__.__name__ == "MDoStatement"
        )
        call = ext_do.targets[0]

        assert call.routine == "VREPORT"
        assert call.is_resolved is False
        assert call.call_type == CallType.ROUTINE_CALL


# =============================================================================
# Variables LIVE Paths
# =============================================================================
