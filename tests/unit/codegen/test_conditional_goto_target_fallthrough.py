"""Tests for conditional GOTO target fallthrough (self-loop break fix).

When a GOTO command has no statement-level postcondition but ALL of its
targets have target-level postconditions (e.g., ``G LABEL:condition``),
the GOTO is effectively conditional. If none of the target conditions
are met, execution must fall through to the next line/label.

This was a bug: ``G N:A=""`` was treated as an unconditional exit because
only the statement-level postcondition was checked, causing:
1. Subsequent statements to be incorrectly marked as unreachable.
2. ``has_explicit_exit`` to return True, preventing ``break`` in self-loop
   ``while True:`` blocks, making fall-through to the next label unreachable.
"""

import pytest

from m2py.codegen import generate_python
from m2py.parser.parser import MUMPSParser
from m2py.runtime import MUMPSRuntime


@pytest.fixture
def runtime():
    """Provide a fresh runtime instance for each test."""
    return MUMPSRuntime()


def execute_mumps(source: str, runtime: MUMPSRuntime) -> str:
    """Generate and execute MUMPS code, return output."""
    code = generate_python(source)
    result = runtime.execute(code)
    if not result.success:
        raise RuntimeError(f"Execution failed: {result.error}")
    return result.output


def parse_and_classify(source: str):
    """Parse MUMPS source and run analysis passes."""
    parser = MUMPSParser()
    routine = parser.parse(source, filename="TEST")
    parser.resolve_references(routine)
    parser.classify_gotos(routine)
    return routine


# =========================================================================
# Analysis-level tests: unreachable marking and has_explicit_exit
# =========================================================================


@pytest.mark.codegen
class TestConditionalGotoTargetUnreachable:
    """Unreachable analysis for GOTO with all-conditional targets."""

    def test_goto_all_targets_conditional_not_unreachable(self):
        """Statements after G LABEL:cond should NOT be marked unreachable.

        ``G END:X=""`` — if X is not empty, execution continues to next line.
        """
        source = """TEST S X=1 G END:X="" W X Q
END Q"""
        routine = parse_and_classify(source)
        label = routine.labels[0]  # TEST
        # Statements: SET, GOTO, WRITE, QUIT
        stmts = label.body.statements
        goto_idx = next(
            i for i, s in enumerate(stmts) if type(s).__name__ == "MGotoStatement"
        )
        # Statement after the conditional GOTO should NOT be unreachable
        assert not stmts[goto_idx + 1].is_unreachable, (
            'Statement after G END:X="" should be reachable'
        )

    def test_goto_unconditional_target_is_unreachable(self):
        """Statements after G LABEL (no condition) SHOULD be unreachable."""
        source = """TEST S X=1 G END W X Q
END Q"""
        routine = parse_and_classify(source)
        label = routine.labels[0]
        stmts = label.body.statements
        goto_idx = next(
            i for i, s in enumerate(stmts) if type(s).__name__ == "MGotoStatement"
        )
        assert stmts[goto_idx + 1].is_unreachable, (
            "Statement after unconditional G END should be unreachable"
        )

    def test_goto_mixed_targets_one_unconditional(self):
        """G A:cond,B (one unconditional target) — unreachable after."""
        source = """TEST S X=1 G A:X="",B W "hi" Q
A Q
B Q"""
        routine = parse_and_classify(source)
        label = routine.labels[0]
        stmts = label.body.statements
        goto_idx = next(
            i for i, s in enumerate(stmts) if type(s).__name__ == "MGotoStatement"
        )
        assert stmts[goto_idx + 1].is_unreachable, (
            "G A:cond,B has one unconditional target — unreachable after"
        )

    def test_goto_multiple_all_conditional_not_unreachable(self):
        """G A:cond1,B:cond2 (all conditional) — reachable after."""
        source = """TEST S X=1 G A:X="",B:X=2 W "hi" Q
A Q
B Q"""
        routine = parse_and_classify(source)
        label = routine.labels[0]
        stmts = label.body.statements
        goto_idx = next(
            i for i, s in enumerate(stmts) if type(s).__name__ == "MGotoStatement"
        )
        assert not stmts[goto_idx + 1].is_unreachable, (
            "G A:cond1,B:cond2 all conditional — reachable after"
        )


@pytest.mark.codegen
class TestConditionalGotoTargetExplicitExit:
    """has_explicit_exit for labels ending with conditional GOTO targets."""

    def test_label_ending_conditional_goto_no_explicit_exit(self):
        """Label ending with G NEXT:cond should NOT have explicit exit.

        When the conditional GOTO is the last statement, the label can
        fall through if the condition is false.
        """
        source = """TEST S X=1 G NEXT:X=""
NEXT W "done" Q"""
        routine = parse_and_classify(source)
        label = routine.labels[0]  # TEST
        assert not label.has_explicit_exit

    def test_label_with_quit_after_conditional_goto_has_explicit_exit(self):
        """Label ending with Q after conditional GOTO — still explicit exit."""
        source = """TEST S X=1 G NEXT:X="" W X Q
NEXT Q"""
        routine = parse_and_classify(source)
        label = routine.labels[0]
        # Last statement is unconditional QUIT
        assert label.has_explicit_exit

    def test_label_ending_unconditional_goto_has_explicit_exit(self):
        """Label ending with G NEXT (no cond) SHOULD have explicit exit."""
        source = """TEST G END
END Q"""
        routine = parse_and_classify(source)
        label = routine.labels[0]
        assert label.has_explicit_exit

    def test_label_ending_stmt_postconditioned_goto_no_explicit_exit(self):
        """G:cond NEXT — statement-level postcondition, no explicit exit."""
        source = """TEST S X=1 G:X NEXT
NEXT W "done" Q"""
        routine = parse_and_classify(source)
        label = routine.labels[0]
        assert not label.has_explicit_exit

    def test_label_ending_multi_target_all_conditional(self):
        """G A:c1,B:c2 as last stmt — not explicit exit."""
        source = """TEST S X=1 G A:X=1,B:X=2
A Q
B Q"""
        routine = parse_and_classify(source)
        label = routine.labels[0]
        assert not label.has_explicit_exit

    def test_label_ending_multi_target_one_unconditional(self):
        """G A:c1,B as last stmt — has explicit exit (B is unconditional)."""
        source = """TEST S X=1 G A:X=1,B
A Q
B Q"""
        routine = parse_and_classify(source)
        label = routine.labels[0]
        assert label.has_explicit_exit


# =========================================================================
# Execution-level tests: self-loop with conditional GOTO fall-through
# =========================================================================


@pytest.mark.codegen
class TestSelfLoopConditionalFallthrough:
    """Self-loop labels that fall through when GOTO condition isn't met."""

    def test_self_loop_conditional_falls_through(self, runtime):
        """Self-loop with G SAME:cond should fall through to next label.

        LOOP iterates X from 1 to 3 via $O, then falls through to DONE.
        """
        source = """\
TEST
 K ^TMP
 S ^TMP(1)="a",^TMP(2)="b",^TMP(3)="c"
 S X="" D LOOP
 Q
LOOP S X=$O(^TMP(X)) G LOOP:X'=""
DONE W X,"END" Q"""
        output = execute_mumps(source, runtime)
        assert output == "END"

    def test_self_loop_conditional_iterates_and_falls_through(self, runtime):
        """Self-loop GOTO iterates then falls through; next label writes output."""
        source = """\
TEST
 S X=0
 G LOOP
 Q
LOOP S X=X+1 G LOOP:X<3
AFTER W X Q"""
        output = execute_mumps(source, runtime)
        assert output == "3"

    def test_self_loop_two_conditional_gotos(self, runtime):
        """Label with two conditional self-GOTOs, both false → fall-through."""
        source = """\
TEST S A=0,B=0 G LOOP Q
LOOP S A=A+1,B=B+1
 G LOOP:A<2
 G LOOP:B<2
DONE W A,",",B Q"""
        output = execute_mumps(source, runtime)
        # A and B both start at 0, increment together
        # First iter: A=1,B=1 → A<2 true → continue
        # Second iter: A=2,B=2 → A<2 false, B<2 false → fall through
        assert output == "2,2"

    def test_self_loop_goto_other_label_conditional(self, runtime):
        """G OTHER:cond in a self-loop label — falls through if cond false.

        This is the DITR pattern: G N:A="" where N is a different label.
        When A is not empty, execution continues in the current label body.
        """
        source = """\
TEST S X=5 G WORK Q
WORK
 G EXIT:X=0
 S X=X-1
 G WORK:X>2
NEXT W X Q
EXIT W "exit" Q"""
        output = execute_mumps(source, runtime)
        # X=5 → G EXIT:0=0 false → X=4 → G WORK:4>2 true
        # X=4 → G EXIT:0=0 false → X=3 → G WORK:3>2 true
        # X=3 → G EXIT:0=0 false → X=2 → G WORK:2>2 false → fall through to NEXT
        assert output == "2"

    def test_self_loop_unconditional_goto_does_not_fall_through(self, runtime):
        """G SAME (unconditional) in a self-loop — should loop forever.

        Add a quit condition inside to prevent infinite loop.
        """
        source = """\
TEST S X=0 G LOOP Q
LOOP S X=X+1 Q:X>2  W X," " G LOOP
AFTER W "never" Q"""
        output = execute_mumps(source, runtime)
        assert output == "1 2 "
        assert "never" not in output


@pytest.mark.codegen
class TestConditionalGotoTargetFallthroughToPiece:
    """Regression test for DITR-like pattern: fall-through writes to record."""

    def test_fallthrough_sets_piece(self, runtime):
        """Self-loop with conditional GOTO falls through to $PIECE SET.

        Mimics DITR: NS iterates, falls through to P which does S $P(...)
        """
        source = """\
TEST
 S ^TMP($J,1)="AAA"
 S X=1
 D NS
 W ^TMP($J,1)
 Q
NS
 G P:X
 Q
P
 S $P(^TMP($J,1),"^",2)="BBB"
 Q"""
        output = execute_mumps(source, runtime)
        assert output == "AAA^BBB"

    def test_self_loop_iterates_then_sets_piece(self, runtime):
        """Multi-iteration self-loop falls through to piece-setting label.

        Pattern: NS loops via conditional GOTO, writes field values via P.
        """
        source = """\
TEST
 S ^TMP($J,1)="HDR"
 S CNT=0,B=2
 D NS
 W ^TMP($J,1)
 Q
NS
 S CNT=CNT+1
 G NS:CNT<3
P
 S $P(^TMP($J,1),"^",B)="VAL" Q"""
        output = execute_mumps(source, runtime)
        # Loops: CNT=1→G NS:1<3 true, CNT=2→G NS:2<3 true, CNT=3→G NS:3<3 false → P
        assert output == "HDR^VAL"
