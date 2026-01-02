"""Tests for JOB command ASG analysis (§8.2.10).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.10

Migrated from:
- tests/unit/test_io_commands.py::TestJobIndirection
- tests/unit/test_io_commands.py::TestJobTimeoutAndProcessParameters
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MJobStatement, MDoStatement
from m2py.asg.expressions import MVariable, MBinaryOp


@pytest.mark.asg
class TestJobCommandAnalysis:
    """ASG-level tests for JOB command analysis (§8.2.10)."""

    def test_job_command_simple(self):
        """JOB command creates correct ASG node (§8.2.10)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J LABEL\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].call.name == "LABEL"

    def test_job_command_external(self):
        """JOB command with external routine (§8.2.10)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J ^ROUTINE\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].call.routine == "ROUTINE"


@pytest.mark.asg
class TestJobIndirectionAnalysis:
    """Tests for JOB command indirection handling (§8.2.10).

    Migrated from: tests/unit/test_io_commands.py::TestJobIndirection
    Phase 80 bug fix.
    """

    def test_job_with_simple_indirection(self):
        """JOB @VAR sets label_is_indirect=True and captures indirection (§8.2.10).

        Per MUMPS spec, J @VAR should start a job whose label is determined
        at runtime from the value of VAR.

        Migrated from: test_io_commands.py::TestJobIndirection::test_job_with_simple_indirection
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J @VAR\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        call = stmt.targets[0].call
        assert call.label_is_indirect is True
        assert call.indirection is not None
        assert isinstance(call.indirection, MVariable)
        assert call.indirection.name == "VAR"

    def test_job_with_routine_indirection(self):
        """JOB @VAR^ROUTINE handles label indirection with explicit routine (§8.2.10).

        Migrated from: test_io_commands.py::TestJobIndirection::test_job_with_routine_indirection
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J @VAR^MYROUTINE\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        call = stmt.targets[0].call
        assert call.label_is_indirect is True
        assert call.indirection is not None
        assert isinstance(call.indirection, MVariable)
        assert call.indirection.name == "VAR"
        assert call.routine == "MYROUTINE"

    def test_job_targets_consistency_with_do(self):
        """MJobStatement.targets and MDoStatement.targets have consistent naming (§8.2.10).

        Phase 81 renamed MJobStatement.calls to .targets for consistency with
        MDoStatement and MGotoStatement.

        Migrated from: test_io_commands.py::TestJobIndirection::test_job_targets_consistency_with_do
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J LABEL\n D OTHER\n")

        label = routine.labels[0]
        job_stmt = label.body.statements[0]
        do_stmt = label.body.statements[1]

        assert isinstance(job_stmt, MJobStatement)
        assert isinstance(do_stmt, MDoStatement)

        # Both should have .targets attribute
        assert hasattr(job_stmt, "targets")
        assert hasattr(do_stmt, "targets")
        assert len(job_stmt.targets) == 1
        assert len(do_stmt.targets) == 1


@pytest.mark.asg
class TestJobTimeoutAndProcessParametersAnalysis:
    """Tests for JOB command timeout and processparameters ASG (§8.2.10).

    Migrated from: tests/unit/test_io_commands.py::TestJobTimeoutAndProcessParameters

    Phase 90: Added support for full JOB syntax per MUMPS 1995 MDC 8.2.10:
    J label^routine(actuallist):(processparameters):timeout

    VistA Examples:
    - J ^XMRONT::5                     - routine with timeout only
    - J START^XWBVLL(PORT)::5          - routine with args and timeout
    - J CHILDONT^%ZISTCPS(NIO,RTN):(:16::):10  - full syntax
    """

    def test_job_with_timeout_only(self):
        """JOB with timeout only (::timeout syntax) (§8.2.10).

        Migrated from: test_io_commands.py::TestJobTimeoutAndProcessParameters::test_job_with_timeout_only
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J ^XMRONT::5\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        job_target = stmt.targets[0]
        assert job_target.call.routine == "XMRONT"
        assert job_target.timeout is not None
        assert job_target.timeout.value == 5
        assert job_target.processparameters == []

    def test_job_with_routine_args_and_timeout(self):
        """JOB with actuallist and timeout: J START^ROUTINE(PORT)::5 (§8.2.10).

        Migrated from: test_io_commands.py::TestJobTimeoutAndProcessParameters::test_job_with_routine_args_and_timeout
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J START^XWBVLL(PORT)::5\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        job_target = stmt.targets[0]
        call = job_target.call
        assert call.name == "START"
        assert call.routine == "XWBVLL"
        # Should have arguments (actuallist) - wrapped in MActualParameter
        assert len(call.arguments) == 1
        # Access the actual expression via .expression
        assert call.arguments[0].expression.name == "PORT"
        assert job_target.timeout is not None
        assert job_target.timeout.value == 5
        assert job_target.processparameters == []

    def test_job_with_processparams_only(self):
        """JOB with processparameters but no timeout (§8.2.10).

        Migrated from: test_io_commands.py::TestJobTimeoutAndProcessParameters::test_job_with_processparams_only
        """
        parser = MUMPSParser()
        routine = parser.parse('TEST\n J LABEL:(IN="/dev/null":OUT="/dev/null")\n')

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        job_target = stmt.targets[0]
        assert job_target.call.name == "LABEL"
        # Should have processparameters - these are expressions like IN="/dev/null"
        assert len(job_target.processparameters) == 2
        # Processparams are key=value expressions (MBinaryOp with = operator)
        assert isinstance(job_target.processparameters[0], MBinaryOp)
        assert job_target.processparameters[0].operator == "="
        # No timeout
        assert job_target.timeout is None

    def test_job_with_processparams_and_timeout(self):
        """JOB with both processparameters and timeout (§8.2.10).

        Migrated from: test_io_commands.py::TestJobTimeoutAndProcessParameters::test_job_with_processparams_and_timeout
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J CHILDONT^ZISTCPS(NIO,RTN):(16:32:64):10\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        job_target = stmt.targets[0]
        call = job_target.call
        assert call.name == "CHILDONT"
        assert call.routine == "ZISTCPS"
        # Should have arguments (actuallist)
        assert len(call.arguments) == 2
        # Should have processparameters on the target
        assert len(job_target.processparameters) == 3
        # Timeout should be populated on the target
        assert job_target.timeout is not None
        assert job_target.timeout.value == 10
