"""Tests for FOR loop analysis functions.

Tests analyze_for_loops function that analyzes FOR loop properties:
- is_infinite (step=0 or argumentless)
- loop_var_modified_in_body
- has_internal_quit
- has_internal_goto
- exit_points

MUMPS 1995 Reference: §8.2.5 FOR command
"""

import pytest

from m2py.asg.elements import MRoutine, MLabel, MScope
from m2py.asg.statements import (
    MForStatement,
    MGotoStatement,
    MSetStatement,
    MQuitStatement,
    MAssignment,
)
from m2py.asg.expressions import MVariable, MLiteral
from m2py.asg.enums import ForLoopType
from m2py.analysis import analyze_for_loops
from m2py.parser.line_parser import detect_quit_after_for


@pytest.mark.analysis
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


@pytest.mark.analysis
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


@pytest.mark.analysis
class TestForAnalysisIntegration:
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
        from m2py.asg.enums import GotoType

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


@pytest.mark.analysis
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


@pytest.mark.analysis
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


@pytest.mark.analysis
class TestSignatureAwareByRefDetection:
    """Tests for signature-aware by-ref detection in FOR analysis (Phase 67d)."""

    def test_byref_to_callee_that_reads_only(self):
        """T6732: By-ref to callee that doesn't modify → loop_var_modified = False.

        LOOP   F I=1:1:10 D READER(.I)
               Q
        READER(A)
               W A   ; Only reads A, doesn't write
               Q

        With signatures, we know READER doesn't modify A, so I is not modified.
        """
        from m2py.parser import MUMPSParser
        from m2py.analysis.variables import compute_all_signatures

        parser = MUMPSParser()
        source = """LOOP F I=1:1:10 D READER(.I)
 Q
READER(A) ; Reads A but doesn't write it
 W A
 Q
"""
        routine = parser.parse(source)
        parser.resolve_references(routine)
        signatures = compute_all_signatures(routine)

        # With signatures, READER's byref_outputs should be empty (A not written)
        assert "A" not in signatures["READER"].byref_outputs

        # Now analyze with signatures
        analyze_for_loops(routine, signatures)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        # Signature-aware: callee doesn't modify A, so I not modified
        assert for_stmt.loop_var_modified_in_body is False

    def test_byref_to_callee_that_modifies(self):
        """T6733: By-ref to callee that modifies → loop_var_modified = True.

        LOOP   F I=1:1:10 D INCR(.I)
               Q
        INCR(A)
               S A=A+1
               Q

        With signatures, we know INCR modifies A, so I is modified.
        """
        from m2py.parser import MUMPSParser
        from m2py.analysis.variables import compute_all_signatures

        parser = MUMPSParser()
        source = """LOOP F I=1:1:10 D INCR(.I)
 Q
INCR(A)
 S A=A+1
 Q
"""
        routine = parser.parse(source)
        parser.resolve_references(routine)
        signatures = compute_all_signatures(routine)

        # With signatures, INCR's byref_outputs should include A
        assert "A" in signatures["INCR"].byref_outputs

        # Now analyze with signatures
        analyze_for_loops(routine, signatures)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        # Signature-aware: callee modifies A, so I is modified
        assert for_stmt.loop_var_modified_in_body is True

    def test_byref_to_external_routine_conservative(self):
        """T6734: By-ref to external routine → conservative True.

        LOOP   F I=1:1:10 D UNKNOWN^EXTERNAL(.I)
               Q

        External calls have no signature - fall back to conservative.
        """
        from m2py.parser import MUMPSParser
        from m2py.analysis.variables import compute_all_signatures

        parser = MUMPSParser()
        source = """LOOP F I=1:1:10 D UNKNOWN^EXTERNAL(.I)
 Q
"""
        routine = parser.parse(source)
        parser.resolve_references(routine)
        signatures = compute_all_signatures(routine)

        # Now analyze with signatures (but external call has none)
        analyze_for_loops(routine, signatures)

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        # Conservative: external call signature unknown, assume modified
        assert for_stmt.loop_var_modified_in_body is True

    def test_without_signatures_conservative(self):
        """Without signatures, by-ref is conservative (same as before Phase 67d)."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        source = """LOOP F I=1:1:10 D READER(.I)
 Q
READER(A)
 W A
 Q
"""
        routine = parser.parse(source)
        # No signatures - conservative behavior
        analyze_for_loops(routine)  # No signatures passed

        label = routine.labels[0]
        for_stmt = None
        for stmt in label.body.statements:
            if isinstance(stmt, MForStatement):
                for_stmt = stmt
                break

        assert for_stmt is not None
        # Without signatures, falls back to conservative: by-ref = modified
        assert for_stmt.loop_var_modified_in_body is True


@pytest.mark.analysis
class TestValueParamsReferenceLoopVar:
    """Tests for value_params_reference_loop_var detection.

    Feature: 017-ydb-test-failures (V1FORB/V1FORC fixes)

    MUMPS FOR evaluates each VALUE parameter when it becomes current,
    NOT upfront like Python's for...in[...]. This means:

    1. Loop var reference: F I=1,I+1,3*I - I is evaluated with current value
    2. Other var reference: F I=A,B,B,C - variables evaluated when current

    If any VALUE parameter contains any variable reference, we must use
    sequential evaluation because the variable may change during the loop.
    """

    def test_detects_simple_loop_var_reference(self):
        """Detects when VALUE param is the loop variable itself."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # F I=1,I,3 - second param is just I
        routine = parser.parse("TEST F I=1,I,3 W I Q\n")
        analyze_for_loops(routine)  # Run analysis to set the flag

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert for_stmt.value_params_reference_loop_var is True

    def test_detects_expression_with_loop_var(self):
        """Detects when VALUE param expression contains loop variable."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # F I=1,I+1,3*I - second and third params reference I
        routine = parser.parse("TEST F I=1,I+1,3*I W I Q\n")
        analyze_for_loops(routine)  # Run analysis to set the flag

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert for_stmt.value_params_reference_loop_var is True

    def test_string_literals_no_var_reference(self):
        """VALUE params with string literals don't contain variables."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # F I="A","B","C" - string literals, no variable references
        routine = parser.parse('TEST F I="A","B","C" W I Q\n')
        analyze_for_loops(routine)  # Run analysis to set the flag

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert for_stmt.value_params_reference_loop_var is False

    def test_numeric_values_no_var_reference(self):
        """Numeric VALUE params don't contain variable references."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # F I=1,2,3 - numeric literals, no variable references
        routine = parser.parse("TEST F I=1,2,3 W I Q\n")
        analyze_for_loops(routine)  # Run analysis to set the flag

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert for_stmt.value_params_reference_loop_var is False

    def test_mixed_params_with_loop_var(self):
        """Mixed params where only some reference loop var."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # F I=1,I+1,5 - second param references I
        routine = parser.parse("TEST F I=1,I+1,5 W I Q\n")
        analyze_for_loops(routine)  # Run analysis to set the flag

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        assert for_stmt.value_params_reference_loop_var is True

    def test_other_variable_requires_sequential(self):
        """Any variable reference requires sequential evaluation."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # F I=1,X,Y - X and Y are variable refs (may change during loop)
        routine = parser.parse("TEST F I=1,X,Y W I Q\n")
        analyze_for_loops(routine)  # Run analysis to set the flag

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        # Any variable reference requires sequential evaluation
        assert for_stmt.value_params_reference_loop_var is True

    def test_range_params_not_checked(self):
        """RANGE parameters are not checked for variable references."""
        from m2py.parser import MUMPSParser

        parser = MUMPSParser()
        # F I=1:1:10 - RANGE param, not VALUE
        routine = parser.parse("TEST F I=1:1:10 W I Q\n")
        analyze_for_loops(routine)  # Run analysis to set the flag

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)
        # RANGE params aren't VALUE params, so this is False
        assert for_stmt.value_params_reference_loop_var is False


class TestDetectQuitAfterFor:
    """Test QUIT detection after FOR command."""

    def test_quit_after_for(self):
        """Detect QUIT after FOR on same line."""
        result = detect_quit_after_for("F I=1:1:10 W I Q")
        assert result is True

    def test_no_quit(self):
        """No QUIT returns False."""
        result = detect_quit_after_for("F I=1:1:10 W I")
        assert result is False

    def test_quit_without_for(self):
        """QUIT without FOR returns False."""
        result = detect_quit_after_for("S X=1 Q")
        assert result is False

    def test_quit_before_for(self):
        """QUIT before FOR doesn't count."""
        result = detect_quit_after_for("Q F I=1:1:10 W I")
        assert result is False

    def test_postconditioned_quit(self):
        """Postconditioned QUIT still detected."""
        result = detect_quit_after_for("F I=1:1:10 W I Q:I>5")
        assert result is True


@pytest.mark.analysis
class TestAnalyzeQuitContextForStatements:
    """Tests for analyze_quit_context_for_statements().

    This function analyzes QUIT context for a flat list of ASG statements
    (used by inline XECUTE code). Without this, QUIT inside FOR inside
    XECUTE would generate raise _XecuteExit() instead of break.

    Fixed suite: V3FOR (test 30305)
    """

    def test_quit_inside_for_marked_as_loop_quit(self):
        """QUIT inside a FOR loop should have exits_for set to the FOR statement."""
        from m2py.analysis.for_analysis import analyze_quit_context_for_statements

        # Build a FOR statement with a QUIT in its body
        for_body = MScope()
        quit_stmt = MQuitStatement(postcondition=None, return_value=None)
        for_body.statements = [quit_stmt]

        for_stmt = MForStatement(
            loop_var=None,
            body=for_body,
        )
        for_stmt.loop_type = ForLoopType.ARGUMENTLESS

        analyze_quit_context_for_statements([for_stmt])

        assert quit_stmt.exits_for is for_stmt

    def test_standalone_quit_not_loop_quit(self):
        """QUIT outside any FOR should NOT have exits_for set."""
        from m2py.analysis.for_analysis import analyze_quit_context_for_statements

        quit_stmt = MQuitStatement(postcondition=None, return_value=None)

        analyze_quit_context_for_statements([quit_stmt])

        # Should not be marked as exiting a FOR
        assert quit_stmt.exits_for is None

    def test_empty_statement_list(self):
        """Empty statement list should not crash."""
        from m2py.analysis.for_analysis import analyze_quit_context_for_statements

        analyze_quit_context_for_statements([])  # Should not crash
