"""Tests for JOB command ASG analysis (§8.2.10).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.10
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MJobStatement, MDoStatement


@pytest.mark.asg
class TestJobCommandAnalysis:
    """ASG-level tests for JOB command analysis (§8.2.10)."""

    def test_job_command_node(self):
        """JOB command creates correct ASG node (§8.2.10)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J LABEL\n")

        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0] is not None
        assert stmt.targets[0].call.name == "LABEL"

    def test_job_target_resolution(self):
        """JOB target is resolved (§8.2.10)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J ^ROUTINE\n")

        assert len(routine.labels) == 1
        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0] is not None
        assert stmt.targets[0].call.routine == "ROUTINE"

    def test_job_process_parameters(self):
        """JOB process parameters are analyzed (§8.2.10)."""
        from m2py.asg.expressions import MBinaryOp

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


@pytest.mark.asg
class TestJobIndirection:
    """Tests for JOB command indirection handling (Phase 80 bug fix)."""

    def test_job_with_simple_indirection(self):
        """JOB @VAR sets label_is_indirect=True and captures indirection.

        Per MUMPS spec, J @VAR should start a job whose label is determined
        at runtime from the value of VAR.
        """
        from m2py.asg.expressions import MVariable

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
        """JOB @VAR^ROUTINE handles label indirection with explicit routine."""
        from m2py.asg.expressions import MVariable

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
        """MJobStatement.targets and MDoStatement.targets have consistent naming.

        Phase 81 renamed MJobStatement.calls to .targets for consistency with
        MDoStatement and MGotoStatement.
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
class TestJobTimeoutAndProcessParameters:
    """Tests for JOB command timeout and processparameters syntax.

    Phase 90: Added support for full JOB syntax per MUMPS 1995 MDC 8.2.10:
    J label^routine(actuallist):(processparameters):timeout

    VistA Examples:
    - J ^XMRONT::5                     - routine with timeout only
    - J START^XWBVLL(PORT)::5          - routine with args and timeout
    - J CHILDONT^%ZISTCPS(NIO,RTN):(:16::):10  - full syntax
    """

    def test_job_with_timeout_only(self):
        """JOB with timeout only (::timeout syntax)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J ^XMRONT::5\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        job_target = stmt.targets[0]
        assert job_target.call.routine == "XMRONT"
        # Timeout should be populated on the target
        assert job_target.timeout is not None
        assert job_target.timeout.value == 5
        # No processparameters
        assert job_target.processparameters == []

    def test_job_with_routine_args_and_timeout(self):
        """JOB with actuallist and timeout: J START^ROUTINE(PORT)::5"""
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
        # Timeout should be populated on the target
        assert job_target.timeout is not None
        assert job_target.timeout.value == 5
        # No processparameters
        assert job_target.processparameters == []

    def test_job_with_processparams_and_timeout(self):
        """JOB with both processparameters and timeout."""
        parser = MUMPSParser()
        # Simpler pattern that our grammar supports (no empty slots)
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

    def test_job_simple_label_with_timeout(self):
        """JOB with simple label and timeout: J LABEL::5"""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J LABEL::5\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        job_target = stmt.targets[0]
        assert job_target.call.name == "LABEL"
        # Timeout should be populated on the target
        assert job_target.timeout is not None
        assert job_target.timeout.value == 5

    def test_job_multi_target_with_per_target_params(self):
        """JOB with multiple targets having individual timeouts.

        Per MUMPS 1995 spec 8.2.10, each jobargument can have its own
        processparameters and timeout:
        J LABEL1::5,LABEL2::10

        This tests the MJobTarget wrapper which stores per-target
        processparameters and timeout (Phase 92 fix).
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J LABEL1::5,LABEL2::10\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 2

        # First target: LABEL1 with timeout=5
        job_target1 = stmt.targets[0]
        assert job_target1.call.name == "LABEL1"
        assert job_target1.timeout is not None
        assert job_target1.timeout.value == 5
        assert job_target1.processparameters == []

        # Second target: LABEL2 with timeout=10
        job_target2 = stmt.targets[1]
        assert job_target2.call.name == "LABEL2"
        assert job_target2.timeout is not None
        assert job_target2.timeout.value == 10
        assert job_target2.processparameters == []


@pytest.mark.asg
class TestMultiJob:
    """Tests for JOB command with multiple targets."""

    def test_single_job(self):
        """Single JOB target works correctly."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J LABEL\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].call.name == "LABEL"

    def test_multi_job(self):
        """JOB with multiple targets captures all targets."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J LABEL1,LABEL2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 2

        assert stmt.targets[0].call.name == "LABEL1"
        assert stmt.targets[1].call.name == "LABEL2"

    def test_job_external_multiple(self):
        """JOB with multiple external routine targets."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J ^ROUTINE1,^ROUTINE2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 2

        assert stmt.targets[0].call.routine == "ROUTINE1"
        assert stmt.targets[1].call.routine == "ROUTINE2"
