"""Tests for JOB command parsing (§8.2.10).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.10

Migrated from:
- tests/unit/test_io_commands.py::TestJobTimeoutAndProcessParameters
- tests/unit/test_multi_arg_commands.py::TestMultiJob
"""

import pytest

from m2py.parser import MUMPSParser
from m2py.asg import MJobStatement


@pytest.mark.parser
class TestJobCommandParsing:
    """Parser-level tests for JOB command (§8.2.10)."""

    def test_job_basic(self):
        """JOB ROUTINE parses correctly (§8.2.10)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J LABEL\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].call.name == "LABEL"

    def test_job_with_external_routine(self):
        """JOB ^ROUTINE parses correctly (§8.2.10)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J ^ROUTINE\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].call.routine == "ROUTINE"

    def test_job_with_timeout(self):
        """JOB ROUTINE::timeout parses correctly (§8.2.10).

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

    def test_job_with_arguments_and_timeout(self):
        """JOB START^ROUTINE(PORT)::5 parses correctly (§8.2.10).

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
        assert len(call.arguments) == 1
        assert job_target.timeout is not None
        assert job_target.timeout.value == 5

    def test_job_with_process_params_and_timeout(self):
        """JOB ROUTINE:(params):timeout parses correctly (§8.2.10).

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
        assert len(call.arguments) == 2
        assert len(job_target.processparameters) == 3
        assert job_target.timeout is not None
        assert job_target.timeout.value == 10

    def test_job_simple_label_with_timeout(self):
        """JOB LABEL::5 parses correctly (§8.2.10).

        Migrated from: test_io_commands.py::TestJobTimeoutAndProcessParameters::test_job_simple_label_with_timeout
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J LABEL::5\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        job_target = stmt.targets[0]
        assert job_target.call.name == "LABEL"
        assert job_target.timeout is not None
        assert job_target.timeout.value == 5

    def test_job_multi_target_with_per_target_params(self):
        """JOB with multiple targets having individual timeouts (§8.2.10).

        Per MUMPS 1995 spec 8.2.10, each jobargument can have its own
        processparameters and timeout: J LABEL1::5,LABEL2::10

        Migrated from: test_io_commands.py::TestJobTimeoutAndProcessParameters::test_job_multi_target_with_per_target_params
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


@pytest.mark.parser
class TestMultiJobParsing:
    """Tests for JOB command with multiple targets (§8.2.10).

    Migrated from: tests/unit/test_multi_arg_commands.py::TestMultiJob
    """

    def test_single_job(self):
        """Single JOB target works correctly (§8.2.10)."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J LABEL\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0].call.name == "LABEL"

    def test_multi_job(self):
        """JOB with multiple targets captures all targets (§8.2.10).

        Migrated from: test_multi_arg_commands.py::TestMultiJob::test_multi_job
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J LABEL1,LABEL2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 2

        assert stmt.targets[0].call.name == "LABEL1"
        assert stmt.targets[1].call.name == "LABEL2"

    def test_job_external_multiple(self):
        """JOB with multiple external routine targets (§8.2.10).

        Migrated from: test_multi_arg_commands.py::TestMultiJob::test_job_external_multiple
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J ^ROUTINE1,^ROUTINE2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MJobStatement)
        assert len(stmt.targets) == 2

        assert stmt.targets[0].call.routine == "ROUTINE1"
        assert stmt.targets[1].call.routine == "ROUTINE2"
