"""Tests for Error Processing parsing (§6.3.2).

Tests verify the textX grammar correctly captures error processing constructs.

Reference: MUMPS 1995 ANSI Standard, Section 6.3.2
"""

import pytest

from m2py.asg import MNewStatement, MSetStatement
from m2py.parser.textx_classes import SpecialVariable


@pytest.mark.parser
class TestErrorProcessingParsing:
    """Parser-level tests for Error Processing (§6.3.2).

    Error processing involves $ETRAP, $ECODE, and related mechanisms.
    """

    def test_etrap_setting(self, parse_line):
        """SET $ETRAP=value parses correctly (§6.3.2)."""
        result = parse_line(' S $ETRAP="D ERR"')
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MSetStatement)
        target = stmt.assignments[0].target
        assert isinstance(target, SpecialVariable)
        assert target.name == "ETRAP"

    def test_ecode_reference(self, parse_line):
        """$ECODE special variable reference parses correctly (§6.3.2).

        $ECODE can be set to clear error conditions.
        """
        result = parse_line(' S $ECODE=""')
        assert result is not None
        stmt = result.labels[0].body.statements[0]
        assert isinstance(stmt, MSetStatement)
        target = stmt.assignments[0].target
        assert isinstance(target, SpecialVariable)
        assert target.name == "ECODE"

    def test_error_handling_structure(self, parse_mumps):
        """Error handling routine structure parses correctly (§6.3.2).

        A typical error handling structure includes $ETRAP setup and
        an error handler label.
        """
        code = (
            'ERROR\n N $ETRAP\n S $ETRAP="D ERRH"\n S X=1\n Q\nERRH\n S $ECODE=""\n Q'
        )
        result = parse_mumps(code)
        assert result is not None
        # Two labels: ERROR and ERRH
        assert len(result.labels) == 2
        assert result.labels[0].name == "ERROR"
        assert result.labels[1].name == "ERRH"
        # ERROR label has NEW, SET, SET, QUIT
        error_stmts = result.labels[0].body.statements
        assert len(error_stmts) == 4
        assert isinstance(error_stmts[0], MNewStatement)
        assert isinstance(error_stmts[1], MSetStatement)
        # ERRH label sets $ECODE and quits
        errh_stmts = result.labels[1].body.statements
        assert len(errh_stmts) == 2
        assert isinstance(errh_stmts[0], MSetStatement)
