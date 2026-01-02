"""Tests for TSTART command parsing (§8.2.24).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.24
Migrated from:
- tests/unit/test_grammar.py::TestTStartEmptyRestartGrammar
- tests/unit/test_parser.py::TestTransactionCommands (TSTART tests)
"""

import pytest

from m2py.asg import MRoutine
from m2py.parser import MUMPSParser
from m2py.asg.statements import MTStartStatement, MTCommitStatement


@pytest.mark.parser
class TestTStartEmptyRestartGrammar:
    """Test TSTART with empty restart argument and parameters (§8.2.24).

    Per MUMPS 1995 spec 8.2.22, TSTART () means "restart all local
    variables" - equivalent to TSTART *.

    Parameters like SERIAL, TRANSACTIONID control transaction behavior.

    Migrated from: tests/unit/test_grammar.py::TestTStartEmptyRestartGrammar
    """

    def test_tstart_empty_parens(self):
        """TSTART () should parse - restart all locals (§8.2.24)."""
        parser = MUMPSParser()
        source = "LABEL\tTS ()\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        assert len(label.body.statements) == 1
        stmt = label.body.statements[0]
        assert stmt.__class__.__name__ == "MTStartStatement"

    def test_tstart_empty_parens_with_serial(self):
        """TSTART ():S should parse - restart all, serial mode (§8.2.24)."""
        parser = MUMPSParser()
        source = "LABEL\tTS ():serial\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert stmt.__class__.__name__ == "MTStartStatement"
        assert len(stmt.parameters) == 1
        assert stmt.parameters[0].name == "serial"
        assert stmt.parameters[0].value is None

    def test_tstart_abbreviated_serial(self):
        """TSTART ():S should parse with abbreviated serial (§8.2.24)."""
        parser = MUMPSParser()
        source = "LABEL\tTS ():S\n"
        routine = parser.parse(source)

        stmt = routine.labels[0].body.statements[0]
        assert len(stmt.parameters) == 1
        assert stmt.parameters[0].name == "S"

    def test_tstart_transactionid(self):
        """TSTART ():T=\"BA\" should parse with transaction ID (§8.2.24)."""
        parser = MUMPSParser()
        source = 'LABEL\tTS ():transactionid="BA"\n'
        routine = parser.parse(source)

        stmt = routine.labels[0].body.statements[0]
        assert len(stmt.parameters) == 1
        assert stmt.parameters[0].name == "transactionid"
        assert stmt.parameters[0].value is not None
        assert stmt.parameters[0].value.value == "BA"

    def test_tstart_multiple_params(self):
        """TSTART ():serial:T=\"X\" should parse multiple params (§8.2.24)."""
        parser = MUMPSParser()
        source = 'LABEL\tTS ():serial:T="X"\n'
        routine = parser.parse(source)

        stmt = routine.labels[0].body.statements[0]
        assert len(stmt.parameters) == 2
        assert stmt.parameters[0].name == "serial"
        assert stmt.parameters[1].name == "T"
        assert stmt.parameters[1].value.value == "X"

    def test_tstart_star_still_works(self):
        """TSTART * should still parse - restart all (explicit) (§8.2.24)."""
        parser = MUMPSParser()
        source = "LABEL\tTS *\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        stmt = routine.labels[0].body.statements[0]
        assert stmt.restart_all is True

    def test_tstart_varlist_still_works(self):
        """TSTART (A,B,C) should still parse - named vars (§8.2.24)."""
        parser = MUMPSParser()
        source = "LABEL\tTS (A,B,C)\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        stmt = routine.labels[0].body.statements[0]
        assert len(stmt.restart_vars) == 3


@pytest.mark.parser
class TestTStartBasicParsing:
    """Test TSTART basic parsing (§8.2.24).

    Migrated from: tests/unit/test_parser.py::TestTransactionCommands
    """

    def test_tstart_basic(self):
        """T94.14: Basic TSTART command should parse to MTStartStatement (§8.2.24)."""
        parser = MUMPSParser()
        source = "TEST\tTS\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        assert len(label.body.statements) == 1
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTStartStatement)
        assert stmt.restart_all is False
        assert stmt.restart_vars == []
        assert stmt.parameters == []

    def test_tstart_full_keyword(self):
        """T94.14: TSTART with full keyword should parse (§8.2.24)."""
        parser = MUMPSParser()
        source = "TEST\tTSTART\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTStartStatement)

    def test_tstart_with_restart_vars(self):
        """T94.14: TSTART with restart variables should parse (§8.2.24)."""
        parser = MUMPSParser()
        source = "TEST\tTS (X,Y,Z)\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTStartStatement)
        # Should have 3 restart variables
        assert len(stmt.restart_vars) == 3
        assert stmt.restart_all is False

    def test_tstart_with_restart_all(self):
        """T94.14: TSTART * should set restart_all flag (§8.2.24)."""
        parser = MUMPSParser()
        # Per MUMPS spec, * is outside parens: TS *
        source = "TEST\tTS *\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTStartStatement)
        assert stmt.restart_all is True

    def test_tstart_with_postcondition(self):
        """T94.14: TSTART with postcondition should parse (§8.2.24)."""
        parser = MUMPSParser()
        source = "TEST\tTS:X=1\n"
        routine = parser.parse(source)

        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert isinstance(stmt, MTStartStatement)
        assert stmt.postcondition is not None


@pytest.mark.parser
class TestTransactionSequence:
    """Test full transaction sequences (§8.2.24).

    Migrated from: tests/unit/test_parser.py::TestTransactionCommands
    """

    def test_transaction_sequence(self):
        """T94.14: Full transaction sequence should parse correctly (§8.2.24)."""
        parser = MUMPSParser()
        source = """TEST
\tTS (X)
\tS X=1
\tTC
"""
        routine = parser.parse(source)

        label = routine.labels[0]
        assert len(label.body.statements) == 3

        # First statement: TSTART
        stmt0 = label.body.statements[0]
        assert isinstance(stmt0, MTStartStatement)
        assert len(stmt0.restart_vars) == 1

        # Third statement: TCOMMIT
        stmt2 = label.body.statements[2]
        assert isinstance(stmt2, MTCommitStatement)
