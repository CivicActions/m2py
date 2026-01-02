"""Tests for reference resolution.

Migrated from: tests/unit/test_resolver.py

Tests the resolver's ability to:
- Scan for MCall objects in GOTO/DO statements
- Resolve label references by name
- Populate back-references (callers, goto_sources)
- Collect global references
- Set call_type during resolution
"""

from m2py.asg.elements import MRoutine, MLabel, MCall, MScope
from m2py.asg.statements import MGotoStatement, MDoStatement
from m2py.analysis import resolve_references, get_unresolved_calls, get_external_calls


class TestResolveReferences:
    """Test resolve_references function.

    Migrated from: tests/unit/test_resolver.py::TestResolveReferences
    """

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
        """GOTO to local label should be resolved."""
        routine = self._create_test_routine()

        # Add GOTO TARGET to MAIN label
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        routine.labels[0].body.add_statement(goto_stmt)

        # Resolve
        resolve_references(routine)

        # Verify resolution
        assert call.is_resolved
        assert call.target is not None
        assert call.target.name == "TARGET"

    def test_resolve_sets_back_reference(self):
        """Resolved GOTO should add back-reference to label."""
        routine = self._create_test_routine()

        # Add GOTO TARGET to MAIN label
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        routine.labels[0].body.add_statement(goto_stmt)

        # Resolve
        resolve_references(routine)

        # Check back-reference
        target_label = routine.get_label("TARGET")
        assert len(target_label.goto_sources) == 1
        assert target_label.goto_sources[0] is call

    def test_resolve_do_adds_to_callers(self):
        """Resolved DO should add to label.callers."""
        routine = self._create_test_routine()

        # Add DO SUBROUTINE to MAIN label
        do_stmt = MDoStatement()
        call = MCall(name="SUBROUTINE")
        do_stmt.targets.append(call)
        routine.labels[0].body.add_statement(do_stmt)

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
        routine.labels[0].body.add_statement(goto_stmt)

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
        routine.labels[0].body.add_statement(goto_stmt)

        # Resolve
        resolve_references(routine)

        # External calls are not resolved locally
        assert not call.is_resolved

    def test_multiple_gotos_to_same_label(self):
        """Multiple GOTOs to same label should all be in back-references."""
        routine = self._create_test_routine()

        # Add two GOTOs to TARGET from MAIN
        goto1 = MGotoStatement()
        call1 = MCall(name="TARGET")
        goto1.targets.append(call1)
        routine.labels[0].body.add_statement(goto1)

        goto2 = MGotoStatement()
        call2 = MCall(name="TARGET")
        goto2.targets.append(call2)
        routine.labels[0].body.add_statement(goto2)

        # Resolve
        resolve_references(routine)

        # Both should be in back-references
        target_label = routine.get_label("TARGET")
        assert len(target_label.goto_sources) == 2


class TestGetUnresolvedCalls:
    """Test get_unresolved_calls function.

    Migrated from: tests/unit/test_resolver.py::TestGetUnresolvedCalls
    """

    def test_returns_unresolved_calls(self):
        """Should return list of unresolved MCall objects."""
        routine = MRoutine(name="TEST")
        label = MLabel(name="MAIN")
        label.body = MScope()
        routine.add_label(label)

        # Add GOTO to missing label
        goto_stmt = MGotoStatement()
        call = MCall(name="MISSING")
        goto_stmt.targets.append(call)
        label.body.add_statement(goto_stmt)

        resolve_references(routine)

        unresolved = get_unresolved_calls(routine)
        assert len(unresolved) == 1
        assert unresolved[0].name == "MISSING"

    def test_returns_empty_when_all_resolved(self):
        """Should return empty list when all calls resolved."""
        routine = MRoutine(name="TEST")

        main = MLabel(name="MAIN")
        main.body = MScope()
        routine.add_label(main)

        target = MLabel(name="TARGET")
        target.body = MScope()
        routine.add_label(target)

        # Add GOTO to existing label
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        main.body.add_statement(goto_stmt)

        resolve_references(routine)

        unresolved = get_unresolved_calls(routine)
        assert len(unresolved) == 0


class TestGetExternalCalls:
    """Test get_external_calls function.

    Migrated from: tests/unit/test_resolver.py::TestGetExternalCalls
    """

    def test_returns_external_calls(self):
        """Should return list of external MCall objects."""
        routine = MRoutine(name="TEST")
        label = MLabel(name="MAIN")
        label.body = MScope()
        routine.add_label(label)

        # Add GOTO to external routine
        goto_stmt = MGotoStatement()
        call = MCall(name="LABEL", routine="OTHER")
        goto_stmt.targets.append(call)
        label.body.add_statement(goto_stmt)

        resolve_references(routine)

        external = get_external_calls(routine)
        assert len(external) == 1
        assert external[0].routine == "OTHER"


class TestCallTypePopulation:
    """Regression tests for call_type population during reference resolution.

    Migrated from: tests/unit/test_resolver.py::TestCallTypePopulation

    Tests that MCall.call_type is correctly set during resolve_references().
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


class TestGlobalRefsCollection:
    """Tests for MRoutine.global_refs population.

    Migrated from: tests/unit/test_resolver.py::TestGlobalRefsCollection
    """

    def test_routine_with_no_globals(self):
        """Routine with no globals has empty global_refs."""
        from m2py.asg.statements import MSetStatement, MAssignment
        from m2py.asg.expressions import MVariable, MLiteral

        routine = MRoutine(name="TEST")

        # Simple SET X=1 - no globals
        var_x = MVariable(name="X", subscripts=[])
        set_stmt = MSetStatement(
            assignments=[MAssignment(target=var_x, value=MLiteral(value="1"))]
        )
        scope = MScope(statements=[set_stmt])
        label = MLabel(name="MAIN", body=scope)
        routine.add_label(label)

        resolve_references(routine)

        assert routine.global_refs == []

    def test_routine_with_single_global(self):
        """Routine with ^GLOBAL has it in global_refs."""
        from m2py.asg.statements import MSetStatement, MAssignment
        from m2py.asg.expressions import MGlobal, MLiteral

        routine = MRoutine(name="TEST")

        # SET ^GLOBAL=1
        global_var = MGlobal(name="GLOBAL", subscripts=[])
        set_stmt = MSetStatement(
            assignments=[MAssignment(target=global_var, value=MLiteral(value="1"))]
        )
        scope = MScope(statements=[set_stmt])
        label = MLabel(name="MAIN", body=scope)
        routine.add_label(label)

        resolve_references(routine)

        assert "GLOBAL" in routine.global_refs
        assert len(routine.global_refs) == 1

    def test_routine_with_multiple_globals(self):
        """Routine with ^A, ^B has both in global_refs."""
        from m2py.asg.statements import MSetStatement, MAssignment
        from m2py.asg.expressions import MGlobal, MLiteral

        routine = MRoutine(name="TEST")

        # SET ^A=1, ^B=2
        global_a = MGlobal(name="A", subscripts=[])
        global_b = MGlobal(name="B", subscripts=[])
        set_stmt = MSetStatement(
            assignments=[
                MAssignment(target=global_a, value=MLiteral(value="1")),
                MAssignment(target=global_b, value=MLiteral(value="2")),
            ]
        )
        scope = MScope(statements=[set_stmt])
        label = MLabel(name="MAIN", body=scope)
        routine.add_label(label)

        resolve_references(routine)

        assert "A" in routine.global_refs
        assert "B" in routine.global_refs
        assert len(routine.global_refs) == 2

    def test_global_refs_deduplication(self):
        """Global refs should not contain duplicates."""
        from m2py.asg.statements import MSetStatement, MWriteStatement, MAssignment
        from m2py.asg.expressions import MGlobal, MLiteral

        routine = MRoutine(name="TEST")

        # SET ^DATA=1 then W ^DATA - same global referenced twice
        global1 = MGlobal(name="DATA", subscripts=[])
        global2 = MGlobal(name="DATA", subscripts=[])
        set_stmt = MSetStatement(
            assignments=[MAssignment(target=global1, value=MLiteral(value="1"))]
        )
        write_stmt = MWriteStatement(arguments=[global2])
        scope = MScope(statements=[set_stmt, write_stmt])
        label = MLabel(name="MAIN", body=scope)
        routine.add_label(label)

        resolve_references(routine)

        # Should only appear once (using set internally)
        assert routine.global_refs.count("DATA") == 1

    def test_global_refs_in_nested_scopes(self):
        """Global refs in nested scopes (FOR, IF) should be collected."""
        from m2py.asg.statements import MSetStatement, MForStatement, MAssignment
        from m2py.asg.expressions import MGlobal, MLiteral

        routine = MRoutine(name="TEST")

        # FOR block with SET ^NESTED=1
        global_var = MGlobal(name="NESTED", subscripts=[])
        set_stmt = MSetStatement(
            assignments=[MAssignment(target=global_var, value=MLiteral(value="1"))]
        )
        for_body = MScope(statements=[set_stmt])
        for_stmt = MForStatement(loop_var="I", body=for_body)
        scope = MScope(statements=[for_stmt])
        label = MLabel(name="MAIN", body=scope)
        routine.add_label(label)

        resolve_references(routine)

        assert "NESTED" in routine.global_refs
