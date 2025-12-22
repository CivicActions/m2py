"""Tests for unreachable code detection and has_explicit_exit property.

Tests for T531 (is_unreachable marking) and T532 (has_explicit_exit property).
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg.statements import (
    MSetStatement,
    MWriteStatement,
    MQuitStatement,
    MGotoStatement,
    MHaltStatement,
    MIfStatement,
    MForStatement,
    MDoStatement,
)


class TestUnreachableCodeDetection:
    """Test T531: Statements after unconditional exit are marked is_unreachable."""

    def test_statements_after_quit_are_unreachable(self):
        """Statements after unconditional QUIT should be marked unreachable."""
        parser = MUMPSParser()
        source = '''TEST
 S X=1
 Q
 S Y=2
 W "never"
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        stmts = routine.labels[0].body.statements
        assert len(stmts) == 4

        # Before QUIT - reachable
        assert stmts[0].is_unreachable is False  # S X=1
        assert stmts[1].is_unreachable is False  # Q

        # After QUIT - unreachable
        assert stmts[2].is_unreachable is True  # S Y=2
        assert stmts[3].is_unreachable is True  # W "never"

    def test_statements_after_goto_are_unreachable(self):
        """Statements after unconditional GOTO should be marked unreachable."""
        parser = MUMPSParser()
        source = '''TEST
 S X=1
 G OTHER
 S Y=2
OTHER Q
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        stmts = routine.labels[0].body.statements
        assert len(stmts) == 3

        assert stmts[0].is_unreachable is False  # S X=1
        assert stmts[1].is_unreachable is False  # G OTHER
        assert stmts[2].is_unreachable is True  # S Y=2

    def test_statements_after_halt_are_unreachable(self):
        """Statements after unconditional HALT should be marked unreachable."""
        parser = MUMPSParser()
        source = '''TEST
 S X=1
 HALT
 S Y=2
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        stmts = routine.labels[0].body.statements
        assert len(stmts) == 3

        assert stmts[0].is_unreachable is False  # S X=1
        assert stmts[1].is_unreachable is False  # H
        assert stmts[2].is_unreachable is True  # S Y=2

    def test_conditional_quit_does_not_make_following_unreachable(self):
        """Statements after conditional QUIT should NOT be marked unreachable."""
        parser = MUMPSParser()
        source = '''TEST
 S X=1
 Q:X=1
 S Y=2
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        stmts = routine.labels[0].body.statements
        assert len(stmts) == 3

        # All reachable because QUIT is conditional
        assert stmts[0].is_unreachable is False  # S X=1
        assert stmts[1].is_unreachable is False  # Q:X=1
        assert stmts[2].is_unreachable is False  # S Y=2

    def test_conditional_goto_does_not_make_following_unreachable(self):
        """Statements after conditional GOTO should NOT be marked unreachable."""
        parser = MUMPSParser()
        source = '''TEST
 S X=1
 G:X=1 OTHER
 S Y=2
OTHER Q
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        stmts = routine.labels[0].body.statements
        assert len(stmts) == 3

        # All reachable because GOTO is conditional
        assert stmts[0].is_unreachable is False
        assert stmts[1].is_unreachable is False
        assert stmts[2].is_unreachable is False

    def test_unreachable_in_if_then_scope(self):
        """Unreachable code detection works inside IF then_scope."""
        parser = MUMPSParser()
        source = '''TEST
 I X=1 D
 . S A=1
 . Q
 . S B=2
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        if_stmt = routine.labels[0].body.statements[0]
        assert isinstance(if_stmt, MIfStatement)

        do_stmt = if_stmt.then_scope.statements[0]
        assert isinstance(do_stmt, MDoStatement)

        body_stmts = do_stmt.body.statements
        assert len(body_stmts) == 3

        assert body_stmts[0].is_unreachable is False  # S A=1
        assert body_stmts[1].is_unreachable is False  # Q
        assert body_stmts[2].is_unreachable is True  # S B=2

    def test_unreachable_in_for_body(self):
        """Unreachable code detection works inside FOR body."""
        parser = MUMPSParser()
        source = '''TEST
 F I=1:1:10 D
 . S X=I
 . Q
 . S Y=I
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        for_stmt = routine.labels[0].body.statements[0]
        assert isinstance(for_stmt, MForStatement)

        do_stmt = for_stmt.body.statements[0]
        assert isinstance(do_stmt, MDoStatement)

        body_stmts = do_stmt.body.statements
        assert len(body_stmts) == 3

        assert body_stmts[0].is_unreachable is False  # S X=I
        assert body_stmts[1].is_unreachable is False  # Q
        assert body_stmts[2].is_unreachable is True  # S Y=I

    def test_unreachable_in_do_block_body(self):
        """Unreachable code detection works inside DO block body."""
        parser = MUMPSParser()
        source = '''TEST
 D
 . S X=1
 . Q
 . S Y=2
 S Z=3
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        do_stmt = routine.labels[0].body.statements[0]
        assert isinstance(do_stmt, MDoStatement)

        body_stmts = do_stmt.body.statements
        assert len(body_stmts) == 3

        assert body_stmts[0].is_unreachable is False  # S X=1
        assert body_stmts[1].is_unreachable is False  # Q
        assert body_stmts[2].is_unreachable is True  # S Y=2

        # Statement after DO block is still reachable
        assert routine.labels[0].body.statements[1].is_unreachable is False  # S Z=3

    def test_multiple_labels_independent_unreachable_tracking(self):
        """Each label tracks unreachable code independently."""
        parser = MUMPSParser()
        source = '''FIRST
 Q
 S X=1
SECOND
 S Y=2
 Q
 S Z=3
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        # FIRST label
        first_stmts = routine.labels[0].body.statements
        assert first_stmts[0].is_unreachable is False  # Q
        assert first_stmts[1].is_unreachable is True  # S X=1

        # SECOND label
        second_stmts = routine.labels[1].body.statements
        assert second_stmts[0].is_unreachable is False  # S Y=2
        assert second_stmts[1].is_unreachable is False  # Q
        assert second_stmts[2].is_unreachable is True  # S Z=3

    def test_no_statements_no_unreachable(self):
        """Empty label body has no unreachable code."""
        parser = MUMPSParser()
        source = '''TEST
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        assert len(routine.labels[0].body.statements) == 0


class TestHasExplicitExit:
    """Test T532: MLabel.has_explicit_exit property."""

    def test_label_ending_with_quit_has_explicit_exit(self):
        """Label ending with QUIT has has_explicit_exit=True."""
        parser = MUMPSParser()
        source = '''TEST
 S X=1
 Q
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        assert routine.labels[0].has_explicit_exit is True

    def test_label_ending_with_goto_has_explicit_exit(self):
        """Label ending with GOTO has has_explicit_exit=True."""
        parser = MUMPSParser()
        source = '''TEST
 S X=1
 G OTHER
OTHER Q
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        assert routine.labels[0].has_explicit_exit is True

    def test_label_ending_with_halt_has_explicit_exit(self):
        """Label ending with HALT has has_explicit_exit=True."""
        parser = MUMPSParser()
        source = '''TEST
 S X=1
 HALT
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        assert routine.labels[0].has_explicit_exit is True

    def test_label_ending_with_set_has_no_explicit_exit(self):
        """Label ending with SET has has_explicit_exit=False."""
        parser = MUMPSParser()
        source = '''TEST
 S X=1
 S Y=2
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        assert routine.labels[0].has_explicit_exit is False

    def test_label_ending_with_write_has_no_explicit_exit(self):
        """Label ending with WRITE has has_explicit_exit=False."""
        parser = MUMPSParser()
        source = '''TEST
 S X=1
 W "hello"
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        assert routine.labels[0].has_explicit_exit is False

    def test_label_with_conditional_quit_at_end_has_no_explicit_exit(self):
        """Label ending with conditional QUIT has has_explicit_exit=False."""
        parser = MUMPSParser()
        source = '''TEST
 S X=1
 Q:X=1
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        # Conditional QUIT is not guaranteed to exit
        assert routine.labels[0].has_explicit_exit is False

    def test_label_with_unreachable_code_after_quit(self):
        """Label with unreachable code after QUIT still has has_explicit_exit=True."""
        parser = MUMPSParser()
        source = '''TEST
 S X=1
 Q
 S Y=2
 W "never"
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        # The last non-unreachable statement is QUIT
        assert routine.labels[0].has_explicit_exit is True

    def test_empty_label_has_no_explicit_exit(self):
        """Empty label has has_explicit_exit=False."""
        parser = MUMPSParser()
        source = '''TEST
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        assert routine.labels[0].has_explicit_exit is False

    def test_label_only_comments_has_no_explicit_exit(self):
        """Label with only comments has has_explicit_exit=False."""
        parser = MUMPSParser()
        source = '''TEST ; just a label with inline comment
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        assert routine.labels[0].has_explicit_exit is False

    def test_multiple_labels_independent_exit_status(self):
        """Each label has its own has_explicit_exit status."""
        parser = MUMPSParser()
        source = '''FIRST
 S X=1
 Q
SECOND
 S Y=2
THIRD
 G FIRST
'''
        routine = parser.parse(source)
        parser.resolve_references(routine)

        assert routine.labels[0].has_explicit_exit is True  # FIRST ends with Q
        assert routine.labels[1].has_explicit_exit is False  # SECOND ends with S
        assert routine.labels[2].has_explicit_exit is True  # THIRD ends with G


class TestMUGJUnreachableCodeExamples:
    """Test unreachable code detection with real MUGJ test patterns."""

    def test_v1prgd_label2_unreachable_pattern(self):
        """V1PRGD label 2 has code after QUIT that should be unreachable."""
        parser = MUMPSParser()
        routine = parser.parse_file('tests/functional/mugj/inref/V1PRGD.m')
        parser.resolve_references(routine)

        # Find label "2"
        label_2 = None
        for label in routine.labels:
            if label.name == '2':
                label_2 = label
                break

        assert label_2 is not None
        assert label_2.has_explicit_exit is True

        # Find where QUIT occurs and verify statements after are unreachable
        found_quit = False
        for stmt in label_2.body.statements:
            if isinstance(stmt, MQuitStatement) and not stmt.postcondition:
                found_quit = True
                continue
            if found_quit:
                assert stmt.is_unreachable is True, f"{stmt.__class__.__name__} should be unreachable"

    def test_v1prgd2_implicit_quit_pattern(self):
        """V1PRGD2 main label ends without QUIT (implicit QUIT)."""
        parser = MUMPSParser()
        routine = parser.parse_file('tests/functional/mugj/inref/V1PRGD2.m')
        parser.resolve_references(routine)

        # Main label should not have explicit exit
        main_label = routine.labels[0]
        assert main_label.has_explicit_exit is False

    def test_vabc_implicit_quit_no_synthetic_statement(self):
        """VABC.m ends without QUIT - ASG should NOT add synthetic MQuitStatement.
        
        The ASG must accurately represent the source code. Labels without explicit
        QUIT use MLabel.has_explicit_exit=False to signal implicit return behavior.
        Python code generation handles this via Python's implicit return semantics.
        """
        parser = MUMPSParser()
        routine = parser.parse_file('tests/functional/mugj/inref/VABC.m')
        parser.resolve_references(routine)

        main_label = routine.labels[0]
        
        # ASG should contain only the SET statement (no synthetic QUIT)
        assert len(main_label.body.statements) == 1
        assert main_label.body.statements[0].__class__.__name__ == 'MSetStatement'
        
        # has_explicit_exit correctly identifies no explicit exit
        assert main_label.has_explicit_exit is False
        
    def test_va_explicit_quit_captured(self):
        """VA.m ends with explicit QUIT - ASG captures it correctly."""
        parser = MUMPSParser()
        routine = parser.parse_file('tests/functional/mugj/inref/VA.m')
        parser.resolve_references(routine)

        main_label = routine.labels[0]
        
        # ASG should contain SET and QUIT
        assert len(main_label.body.statements) == 2
        assert main_label.body.statements[0].__class__.__name__ == 'MSetStatement'
        assert main_label.body.statements[1].__class__.__name__ == 'MQuitStatement'
        
        # has_explicit_exit correctly identifies explicit exit
        assert main_label.has_explicit_exit is True
