"""Unit tests for GOTO and FOR loop analysis.

Tests the analysis functions that populate:
- MGotoStatement.goto_type, exits_loops
- MForStatement.has_internal_goto, exit_points, is_infinite, loop_var_modified_in_body
"""

import pytest
from m2py.asg.elements import MRoutine, MLabel, MCall, MScope
from m2py.asg.statements import (
    MGotoStatement,
    MForStatement,
    MSetStatement,
    MAssignment,
)
from m2py.asg.expressions import MVariable, MLiteral
from m2py.asg.enums import GotoType, ForLoopType
from m2py.analysis import resolve_references, classify_gotos, analyze_for_loops


class TestClassifyGotos:
    """Test classify_gotos function."""

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

    def test_goto_cross_label_forward(self):
        """GOTO to later label should be FORWARD_JUMP."""
        routine = self._create_test_routine()

        # Add GOTO TARGET to MAIN label
        goto_stmt = MGotoStatement()
        call = MCall(name="TARGET")
        goto_stmt.targets.append(call)
        routine.labels[0].body.add_statement(goto_stmt)

        resolve_references(routine)
        classify_gotos(routine)

        # GOTO to later label from earlier should be FORWARD_JUMP
        # Actually, cross-label without FOR = FORWARD_JUMP
        assert goto_stmt.goto_type == GotoType.FORWARD_JUMP

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
        assert goto_stmt.goto_type != GotoType.EXTERNAL
        assert goto_stmt.goto_type == GotoType.FORWARD_JUMP


class TestForLoopIsInfinite:
    """Test is_infinite detection for FOR loops."""

    def test_argumentless_for_is_infinite(self):
        """Argumentless FOR should be is_infinite=True."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # Argumentless FOR
        routine = parser.parse("TEST ; test\n F  Q:A=1\n")

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert for_stmt.loop_type == ForLoopType.ARGUMENTLESS
        assert for_stmt.is_infinite is True

    def test_step_zero_for_is_infinite(self):
        """FOR with step=0 should be is_infinite=True."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # FOR I=1:0:10 - step of 0 means infinite
        routine = parser.parse("TEST ; test\n F I=1:0:10 Q:A=1\n")

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert for_stmt.is_infinite is True

    def test_normal_bounded_not_infinite(self):
        """Normal bounded FOR should not be infinite."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse("TEST ; test\n F I=1:1:10 S X=1\n")

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert for_stmt.is_infinite is False

    def test_open_ended_not_infinite(self):
        """Open-ended FOR (no end value) should not be is_infinite."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        routine = parser.parse("TEST ; test\n F I=1:1 Q:I>10\n")

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        # Open-ended is not infinite per se (has a step)
        assert for_stmt.is_infinite is False


class TestAnalyzeForLoops:
    """Test analyze_for_loops function."""

    def test_loop_var_not_modified(self):
        """FOR loop that doesn't modify loop var should be detected."""
        routine = MRoutine(name="TEST")
        label = MLabel(name="MAIN")
        label.body = MScope()
        label.body.parent = label
        routine.add_label(label)

        # Create FOR loop that doesn't modify I
        for_stmt = MForStatement()
        for_stmt.loop_var = "I"
        for_stmt.loop_type = ForLoopType.BOUNDED
        for_stmt.body = MScope()

        # SET X=1 (not I)
        set_stmt = MSetStatement()
        x_var = MVariable()
        x_var.name = "X"
        value = MLiteral()
        value.value = 1
        set_stmt.assignments = [MAssignment(target=x_var, value=value)]
        for_stmt.body.add_statement(set_stmt)

        label.body.add_statement(for_stmt)

        analyze_for_loops(routine)

        assert for_stmt.loop_var_modified_in_body is False

    def test_loop_var_modified(self):
        """FOR loop that modifies loop var should be detected."""
        routine = MRoutine(name="TEST")
        label = MLabel(name="MAIN")
        label.body = MScope()
        label.body.parent = label
        routine.add_label(label)

        # Create FOR loop that modifies I
        for_stmt = MForStatement()
        for_stmt.loop_var = "I"
        for_stmt.loop_type = ForLoopType.BOUNDED
        for_stmt.body = MScope()

        # SET I=I+1 (modifies loop var)
        set_stmt = MSetStatement()
        i_var = MVariable()
        i_var.name = "I"
        value = MLiteral()
        value.value = 1
        set_stmt.assignments = [MAssignment(target=i_var, value=value)]
        for_stmt.body.add_statement(set_stmt)

        label.body.add_statement(for_stmt)

        analyze_for_loops(routine)

        assert for_stmt.loop_var_modified_in_body is True

    def test_has_internal_quit_detected(self):
        """FOR loop with QUIT in body should set has_internal_quit=True."""
        from m2py.asg.statements import MQuitStatement

        routine = MRoutine(name="TEST")
        label = MLabel(name="MAIN")
        label.body = MScope()
        label.body.parent = label
        routine.add_label(label)

        # Create FOR loop with QUIT
        for_stmt = MForStatement()
        for_stmt.loop_var = "I"
        for_stmt.loop_type = ForLoopType.BOUNDED
        for_stmt.body = MScope()

        quit_stmt = MQuitStatement()
        for_stmt.body.add_statement(quit_stmt)

        label.body.add_statement(for_stmt)

        analyze_for_loops(routine)

        assert for_stmt.has_internal_quit is True

    def test_has_internal_quit_not_set_for_nested_for(self):
        """QUIT in nested FOR should not set outer FOR's has_internal_quit."""
        from m2py.asg.statements import MQuitStatement

        routine = MRoutine(name="TEST")
        label = MLabel(name="MAIN")
        label.body = MScope()
        label.body.parent = label
        routine.add_label(label)

        # Create outer FOR with inner FOR that has QUIT
        outer_for = MForStatement()
        outer_for.loop_var = "I"
        outer_for.loop_type = ForLoopType.BOUNDED
        outer_for.body = MScope()

        inner_for = MForStatement()
        inner_for.loop_var = "J"
        inner_for.loop_type = ForLoopType.BOUNDED
        inner_for.body = MScope()

        quit_stmt = MQuitStatement()
        inner_for.body.add_statement(quit_stmt)

        outer_for.body.add_statement(inner_for)
        label.body.add_statement(outer_for)

        analyze_for_loops(routine)

        # Inner FOR has QUIT
        assert inner_for.has_internal_quit is True
        # Outer FOR does NOT have QUIT (the QUIT is in inner FOR)
        assert outer_for.has_internal_quit is False


class TestIntegrationWithParser:
    """Integration tests using actual MUMPS parsing."""

    def test_full_analysis_pipeline(self):
        """Test full analysis: parse -> resolve -> classify_gotos -> analyze_for_loops."""
        from m2py.parser import MUMPSParser

        source = """TEST ; Test routine
 F I=1:0:10 G TARGET
TARGET ; target label
 Q
"""
        parser = MUMPSParser()
        routine = parser.parse(source)
        parser.resolve_references(routine)
        parser.classify_gotos(routine)
        parser.analyze_for_loops(routine)

        # Get the FOR statement
        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)

        # Check is_infinite (step=0)
        assert for_stmt.is_infinite is True

        # Check has_internal_goto
        assert for_stmt.has_internal_goto is True

        # Check exit_points
        assert len(for_stmt.exit_points) == 1

        # Get the GOTO
        goto_stmt = for_stmt.body.statements[0]
        assert isinstance(goto_stmt, MGotoStatement)

        # Check goto_type
        assert goto_stmt.goto_type == GotoType.LOOP_EXIT

        # Check exits_loops
        assert for_stmt in goto_stmt.exits_loops

    def test_v1fora1_analysis(self):
        """Test analysis on actual V1FORA1.m MUGJ test file."""
        from m2py.parser import MUMPSParser
        from pathlib import Path

        path = Path("tests/functional/mugj/inref/V1FORA1.m")
        if not path.exists():
            pytest.skip("V1FORA1.m not found")

        parser = MUMPSParser()
        routine = parser.parse_file(path)
        parser.resolve_references(routine)
        parser.classify_gotos(routine)
        parser.analyze_for_loops(routine)

        # Check that step-0 loops are detected
        step_zero_fors = []
        infinite_fors = []

        for label in routine.labels:
            for stmt in label.body.statements:
                if isinstance(stmt, MForStatement):
                    for param in stmt.parameters:
                        if param.step:
                            step_val = getattr(param.step, "value", None)
                            if step_val == 0:
                                step_zero_fors.append((label.name, stmt))
                    if stmt.is_infinite:
                        infinite_fors.append((label.name, stmt))

        # V1FORA1 has step-0 loops at labels 340, G3401, G3402, G3403, 344
        assert len(step_zero_fors) >= 5, (
            f"Expected >=5 step-0 FORs, got {len(step_zero_fors)}"
        )
        assert len(infinite_fors) >= 5, (
            f"Expected >=5 infinite FORs, got {len(infinite_fors)}"
        )

        # Check that GOTOs inside FORs are detected
        fors_with_gotos = [
            (label.name, stmt)
            for label in routine.labels
            for stmt in label.body.statements
            if isinstance(stmt, MForStatement) and stmt.has_internal_goto
        ]

        # Labels 340, G3401, G3402 have GOTOs inside FOR
        assert len(fors_with_gotos) >= 3, (
            f"Expected >=3 FORs with GOTOs, got {len(fors_with_gotos)}"
        )


# =============================================================================
# FOR Analysis Nested Scope Recursion Tests
# =============================================================================


class TestForAnalysisNestedScopes:
    """Test nested scope recursion in for_analysis.py.

    Tests _check_var_modified_in_scope() and _check_quit_in_scope()
    recursion into nested scopes (then_scope, else_scope, body).
    """

    def test_for_with_if_modifying_loop_var_in_then(self):
        """FOR with IF that modifies loop var in then_scope.

        Tests _check_var_modified_in_scope() recursion into then_scope.
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        source = """TEST
 F I=1:1:10 I I>5 S I=10 Q
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        assert for_stmt.loop_var_modified_in_body is True

    def test_for_with_quit_in_if_then_scope(self):
        """FOR with QUIT inside IF then_scope should detect internal QUIT.

        Tests _check_quit_in_scope() recursion into then_scope.
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        source = """TEST
 F I=1:1:100 I I>50 Q
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        assert for_stmt.has_internal_quit is True

    def test_for_with_nested_for_quit_not_detected(self):
        """QUIT in nested FOR should NOT count as internal QUIT of outer FOR.

        Tests that _check_quit_in_scope() doesn't recurse into nested FOR bodies.
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        source = """TEST
 F I=1:1:10 D
 . F J=1:1:5 Q:J>3
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        outer_for = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                outer_for = stmt
                break

        assert outer_for is not None
        assert outer_for.has_internal_quit is False

    def test_for_with_else_modifying_var(self):
        """Test loop var modification detected in ELSE branch.

        Tests else_scope recursion path.
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        source = """TEST
 F I=1:1:10 I I>5 W I E  S I=I+10
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        assert for_stmt.loop_var_modified_in_body is True

    def test_for_with_do_body_modifying_var(self):
        """Test loop var modification detected in argumentless DO body.

        Tests body recursion path for statements with body attribute.
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        source = """TEST
 F I=1:1:10 D
 . S I=I+1
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        assert for_stmt.loop_var_modified_in_body is True

    def test_for_with_quit_in_do_body_not_detected(self):
        """QUIT in DO body should NOT be detected (separate scope).

        Per MUMPS semantics, a QUIT in a DO block exits that DO, not the FOR.
        """
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        source = """TEST
 F I=1:1:10 D
 . Q:I>5
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        assert for_stmt.has_internal_quit is False

    def test_for_with_direct_quit_in_body(self):
        """FOR with direct QUIT (not in nested structure) should be detected."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        source = """TEST
 F I=1:1:10 Q:I>5 W I
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        assert for_stmt.has_internal_quit is True


class TestLoopVarModificationEnhanced:
    """Test enhanced loop variable modification detection (Phase 66).

    Tests for READ, KILL, and pass-by-reference detection.
    """

    def test_loop_var_modified_by_read(self):
        """FOR loop with READ into loop var should be detected."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # READ I reads into the loop variable, modifying it
        source = """TEST
 F I=1:1 R I Q:I=0
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        assert for_stmt.loop_var_modified_in_body is True

    def test_loop_var_not_modified_by_read_other_var(self):
        """FOR loop with READ into different var should not set modified."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # READ X reads into X, not the loop variable I
        source = """TEST
 F I=1:1:10 R X W I
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        assert for_stmt.loop_var_modified_in_body is False

    def test_loop_var_modified_by_kill(self):
        """FOR loop with KILL of loop var should be detected."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # KILL D removes the loop variable, modifying it
        # This is the "K D Q" idiom for early loop exit
        source = """TEST
 F D="+" K D Q
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        assert for_stmt.loop_var_modified_in_body is True

    def test_loop_var_modified_by_kill_all(self):
        """FOR loop with argumentless KILL (kill all) should be detected."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # K with no arguments kills ALL local variables (note: K alone, W separate)
        source = """TEST ; test
 F I=1:1:10 K  W I
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        assert for_stmt.loop_var_modified_in_body is True

    def test_loop_var_not_modified_by_kill_other_var(self):
        """FOR loop with KILL of different var should not set modified."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # KILL X does not affect loop variable I
        source = """TEST
 F I=1:1:10 K X W I
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        assert for_stmt.loop_var_modified_in_body is False

    def test_loop_var_modified_by_byref_do(self):
        """FOR loop with loop var passed by-ref should be detected."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # D BLANK(.I) passes I by reference - callee CAN modify it
        source = """TEST
 F I=1:1:30 D BLANK(.I)
 Q
BLANK(X) ; X is passed by reference
 S X=X+1
 Q
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        # Loop var passed by-ref means it COULD be modified
        assert for_stmt.loop_var_modified_in_body is True

    def test_loop_var_not_modified_by_byval_do(self):
        """FOR loop with loop var passed by-value should not set modified."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # D WORK(I) passes I by value - callee cannot modify it
        source = """TEST
 F I=1:1:10 D WORK(I)
 Q
WORK(X)
 W X
 Q
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        assert for_stmt.loop_var_modified_in_body is False

    def test_loop_var_not_modified_by_byref_other_var(self):
        """FOR loop with different var passed by-ref should not set modified."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # D WORK(.X) passes X by reference, but loop var is I
        source = """TEST
 N X S X=0
 F I=1:1:10 D WORK(.X)
 Q
WORK(Y) ; Y is passed by reference
 S Y=Y+1
 Q
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        # Loop var I is NOT passed by-ref - only X is
        assert for_stmt.loop_var_modified_in_body is False

    def test_loop_var_byref_iterator_pattern(self):
        """Test iterator pattern: D ITER(.NEXT) Q:NEXT=0."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # Classic VistA iterator pattern: pass NEXT by-ref so callee can set exit condition
        source = """TEST
 F NEXT=1:1 D PTNEXT(.NEXT) Q:NEXT=0
 Q
PTNEXT(N) ; Set N to 0 to signal end
 S N=$O(^PAT(N))
 Q
"""
        routine = parser.parse(source)
        analyze_for_loops(routine)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        # NEXT is passed by-ref - it CAN be modified to signal loop exit
        assert for_stmt.loop_var_modified_in_body is True
