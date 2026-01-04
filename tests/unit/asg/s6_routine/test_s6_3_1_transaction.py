"""Tests for Transaction Processing ASG analysis (§6.3.1).

Reference: MUMPS 1995 ANSI Standard, Section 6.3.1

§6.3.1 defines the transaction processing model:
- TSTART initiates a transaction (may be restartable or serializable)
- TCOMMIT attempts to commit when $TLEVEL becomes zero
- TROLLBACK rescinds modifications and sets $TLEVEL to zero
- TRESTART causes transaction to restart (if restartable)

The ASG must capture:
- Transaction boundary markers (MTStartStatement, MTCommitStatement, etc.)
- Restart variable lists (vars saved for TRESTART)
- Transaction parameters (SERIAL, TRANSACTIONID)
- Nested transaction structure ($TLEVEL > 1)
"""

import pytest

from m2py.asg.statements import (
    MTCommitStatement,
    MTRestartStatement,
    MTRollbackStatement,
    MTStartStatement,
)


@pytest.mark.asg
class TestTransactionProcessingAnalysis:
    """ASG-level tests for transaction processing analysis (§6.3.1)."""

    def test_transaction_boundary_detection(self, analyze_routine):
        """TSTART/TCOMMIT boundaries are correctly identified (§6.3.1).

        Per §6.3.1: A TRANSACTION begins with TSTART and ends with TCOMMIT
        or TROLLBACK. The ASG must capture these boundary markers.
        """
        routine = analyze_routine("""\
TEST
 TSTART
 S ^A=1
 TCOMMIT
""")
        label = routine.get_label("TEST")
        statements = label.body.statements

        # Verify transaction boundary statements are captured
        assert len(statements) == 3

        # First statement is TSTART (transaction start boundary)
        tstart = statements[0]
        assert isinstance(tstart, MTStartStatement)

        # Last statement is TCOMMIT (transaction end boundary)
        tcommit = statements[2]
        assert isinstance(tcommit, MTCommitStatement)

    def test_tlevel_tracking(self, analyze_routine):
        """Nested transactions increment $TLEVEL (§6.3.1).

        Per §6.3.1: TSTART adds one to $TLEVEL. The ASG captures
        each TSTART/TCOMMIT allowing $TLEVEL to be computed.

        Nested example:
        - TSTART -> $TLEVEL=1
        - TSTART -> $TLEVEL=2
        - TCOMMIT -> $TLEVEL=1
        - TCOMMIT -> $TLEVEL=0 (commit occurs)
        """
        routine = analyze_routine("""\
TEST
 TSTART
 TSTART
 S ^A=1
 TCOMMIT
 TCOMMIT
""")
        label = routine.get_label("TEST")
        statements = label.body.statements

        # Should have: TSTART, TSTART, SET, TCOMMIT, TCOMMIT
        assert len(statements) == 5

        # Count transaction statements
        tstart_count = sum(1 for s in statements if isinstance(s, MTStartStatement))
        tcommit_count = sum(1 for s in statements if isinstance(s, MTCommitStatement))

        assert tstart_count == 2, "Nested TSTART should create 2 MTStartStatement nodes"
        assert tcommit_count == 2, (
            "Nested TCOMMIT should create 2 MTCommitStatement nodes"
        )

    def test_transaction_variable_isolation(self, analyze_routine):
        """Restart variables are captured for transaction isolation (§6.3.1).

        Per §6.3.1 and §8.2.22: TSTART (VAR1,VAR2) specifies variables
        whose values are saved for potential TRESTART. TSTART * saves all
        current local variables.

        The ASG captures restart_vars and restart_all flag.
        """
        # Test explicit variable list
        routine = analyze_routine("""\
TEST
 TSTART (X,Y,Z)
 S X=1,Y=2,Z=3
 TCOMMIT
""")
        label = routine.get_label("TEST")
        tstart = label.body.statements[0]

        assert isinstance(tstart, MTStartStatement)
        assert tstart.restart_all is False
        assert len(tstart.restart_vars) == 3

        # Verify variable names
        var_names = [v.name for v in tstart.restart_vars]
        assert "X" in var_names
        assert "Y" in var_names
        assert "Z" in var_names

    def test_tstart_all_vars_restartable(self, analyze_routine):
        """TSTART * makes all variables restartable (§6.3.1).

        Per §8.2.22: When restartargument is asterisk (*), it specifies
        all current names and marks the CONTEXT-STRUCTURE as exclusive.
        """
        routine = analyze_routine("""\
TEST
 TSTART *
 S X=1
 TCOMMIT
""")
        label = routine.get_label("TEST")
        tstart = label.body.statements[0]

        assert isinstance(tstart, MTStartStatement)
        assert tstart.restart_all is True
        assert len(tstart.restart_vars) == 0  # No explicit vars when * is used

    def test_tstart_parameters(self, analyze_routine):
        """TSTART parameters (SERIAL, TRANSACTIONID) are captured (§6.3.1).

        Per §8.2.22: TSTART accepts parameters like:
        - SERIAL (S) - serializable transaction
        - TRANSACTIONID=expr - transaction identifier
        """
        routine = analyze_routine("""\
TEST
 TSTART ():SERIAL:TRANSACTIONID="TXN001"
 S ^A=1
 TCOMMIT
""")
        label = routine.get_label("TEST")
        tstart = label.body.statements[0]

        assert isinstance(tstart, MTStartStatement)
        assert tstart.parameters is not None
        assert len(tstart.parameters) == 2

        # Check parameter names
        param_names = [p.name for p in tstart.parameters]
        assert "SERIAL" in param_names
        assert "TRANSACTIONID" in param_names

        # Check TRANSACTIONID has value
        tid_param = next(p for p in tstart.parameters if p.name == "TRANSACTIONID")
        assert tid_param.value is not None
        assert tid_param.value.value == "TXN001"

    def test_trollback_statement(self, analyze_routine):
        """TROLLBACK creates MTRollbackStatement (§6.3.1).

        Per §6.3.1: TROLLBACK rescinds all global variable modifications
        within the transaction and sets $TLEVEL to zero.
        """
        routine = analyze_routine("""\
TEST
 TSTART
 S ^A=1
 TROLLBACK
""")
        label = routine.get_label("TEST")
        statements = label.body.statements

        assert len(statements) == 3
        trollback = statements[2]
        assert isinstance(trollback, MTRollbackStatement)

    def test_trestart_statement(self, analyze_routine):
        """TRESTART creates MTRestartStatement (§6.3.1).

        Per §6.3.1: TRESTART explicitly causes the transaction to restart
        (if restartable). Execution resumes with the initial TSTART.
        """
        routine = analyze_routine("""\
TEST
 TSTART (X)
 S X=1
 TRESTART
""")
        label = routine.get_label("TEST")
        statements = label.body.statements

        assert len(statements) == 3
        trestart = statements[2]
        assert isinstance(trestart, MTRestartStatement)
