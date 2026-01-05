"""Tests for TRESTART command ASG analysis (§8.2.20).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.20
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MRoutine
from m2py.asg.statements import MTRestartStatement


@pytest.mark.asg
class TestTrestartCommandAnalysis:
    """ASG-level tests for TRESTART command analysis (§8.2.20).

    TRESTART performs a transaction restart if $TLevel > 0.
    If $TLevel is 0, it generates an error (ecode="M44").
    """

    def test_trestart_command_node(self):
        """TRESTART command creates correct ASG node (§8.2.20).

        TRESTART parses to MTRestartStatement ASG node.
        It takes no arguments - just restarts the current transaction.
        """
        parser = MUMPSParser()
        source = """TEST
\tTRESTART
"""
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRestartStatement)
        # TRESTART has no arguments - just postcondition support
        assert stmt.postcondition is None

    def test_trestart_control_flow(self):
        """TRESTART control flow impact is analyzed (§8.2.20).

        TRESTART causes transaction restart - control returns to TSTART.
        It can have a postcondition to make it conditional.
        """
        parser = MUMPSParser()
        # TRESTART with postcondition - only restart if condition true
        source = """RETRY
\tTRESTART:ERR
"""
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTRestartStatement)
        # Postcondition controls whether TRESTART executes
        assert stmt.postcondition is not None
