"""Unit tests for I/O command parsing and ASG generation."""

from m2py.parser import MUMPSParser
from m2py.asg import MOpenStatement, MCloseStatement, MUseStatement, MJobStatement


def test_open_command_simple():
    """Test OPEN command with simple device."""
    parser = MUMPSParser()
    routine = parser.parse("TEST\n O X\n")

    assert len(routine.labels) == 1
    label = routine.labels[0]
    assert len(label.body.statements) == 1

    stmt = label.body.statements[0]
    assert isinstance(stmt, MOpenStatement)
    assert len(stmt.devices) == 1
    assert stmt.devices[0].device_expr is not None


def test_close_command_simple():
    """Test CLOSE command with simple device."""
    parser = MUMPSParser()
    routine = parser.parse("TEST\n C X\n")

    assert len(routine.labels) == 1
    label = routine.labels[0]
    assert len(label.body.statements) == 1

    stmt = label.body.statements[0]
    assert isinstance(stmt, MCloseStatement)
    assert len(stmt.devices) == 1
    assert stmt.devices[0].device_expr is not None


def test_use_command_simple():
    """Test USE command with simple device."""
    parser = MUMPSParser()
    routine = parser.parse("TEST\n U X\n")

    assert len(routine.labels) == 1
    label = routine.labels[0]
    assert len(label.body.statements) == 1

    stmt = label.body.statements[0]
    assert isinstance(stmt, MUseStatement)
    assert len(stmt.devices) == 1
    assert stmt.devices[0].device_expr is not None


def test_job_command_simple():
    """Test JOB command with simple label."""
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


def test_job_command_external():
    """Test JOB command with external routine."""
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


def test_io_commands_with_postconditions():
    """Test I/O commands with postconditions."""
    parser = MUMPSParser()
    routine = parser.parse("TEST\n O:X>0 DEV\n C:Y=1 DEV\n U:Z DEV\n")

    assert len(routine.labels) == 1
    label = routine.labels[0]
    assert len(label.body.statements) == 3

    # All should have postconditions
    for stmt in label.body.statements:
        assert stmt.postcondition is not None


def test_open_command_with_timeout():
    """Test OPEN command with timeout (single colon syntax)."""
    parser = MUMPSParser()
    routine = parser.parse("TEST\n O X:5\n")

    label = routine.labels[0]
    stmt = label.body.statements[0]

    assert isinstance(stmt, MOpenStatement)
    assert len(stmt.devices) == 1
    assert stmt.devices[0].device_expr is not None
    assert stmt.devices[0].device_expr.name == "X"
    assert stmt.devices[0].timeout is not None
    assert stmt.devices[0].timeout.value == 5
    assert stmt.devices[0].parameters == []


def test_open_command_with_double_colon_timeout():
    """Test OPEN command with double colon timeout (::timeout syntax)."""
    parser = MUMPSParser()
    routine = parser.parse("TEST\n O X::10\n")

    label = routine.labels[0]
    stmt = label.body.statements[0]

    assert isinstance(stmt, MOpenStatement)
    assert len(stmt.devices) == 1
    assert stmt.devices[0].device_expr is not None
    assert stmt.devices[0].device_expr.name == "X"
    assert stmt.devices[0].timeout is not None
    assert stmt.devices[0].timeout.value == 10
    assert stmt.devices[0].parameters == []


def test_open_command_with_params():
    """Test OPEN command with parameters."""
    parser = MUMPSParser()
    routine = parser.parse('TEST\n O X:("ABC")\n')

    label = routine.labels[0]
    stmt = label.body.statements[0]

    assert isinstance(stmt, MOpenStatement)
    assert len(stmt.devices) == 1
    assert stmt.devices[0].device_expr is not None
    assert stmt.devices[0].device_expr.name == "X"
    assert stmt.devices[0].timeout is None
    assert len(stmt.devices[0].parameters) == 1


def test_open_command_with_params_and_timeout():
    """Test OPEN command with parameters and timeout."""
    parser = MUMPSParser()
    routine = parser.parse('TEST\n O X:("A":0:2048):5\n')

    label = routine.labels[0]
    stmt = label.body.statements[0]

    assert isinstance(stmt, MOpenStatement)
    assert len(stmt.devices) == 1
    assert stmt.devices[0].device_expr is not None
    assert stmt.devices[0].device_expr.name == "X"
    assert stmt.devices[0].timeout is not None
    assert stmt.devices[0].timeout.value == 5
    assert len(stmt.devices[0].parameters) == 3


# =============================================================================
# MERGE Command Tests
# =============================================================================


class TestMergeCommand:
    """Tests for MERGE command ASG field population."""

    def test_merge_command_simple(self):
        """MERGE dest=source produces MMergeStatement with both fields."""
        from m2py.asg import MMergeStatement

        parser = MUMPSParser()
        routine = parser.parse("TEST\n M ^DEST=^SRC\n")

        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MMergeStatement)
        assert len(stmt.merges) == 1
        assert stmt.merges[0].destination is not None
        assert stmt.merges[0].source is not None

    def test_merge_command_with_postcondition(self):
        """MERGE:condition dest=source handles postcondition."""
        from m2py.asg import MMergeStatement

        parser = MUMPSParser()
        routine = parser.parse("TEST\n M:X>0 ^DEST=^SRC\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MMergeStatement)
        assert stmt.postcondition is not None
        assert len(stmt.merges) == 1
        assert stmt.merges[0].destination is not None
        assert stmt.merges[0].source is not None

    def test_merge_with_local_variables(self):
        """MERGE can merge local variable trees."""
        from m2py.asg import MMergeStatement

        parser = MUMPSParser()
        routine = parser.parse("TEST\n M LOCAL1=LOCAL2\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MMergeStatement)
        assert len(stmt.merges) == 1
        assert stmt.merges[0].destination is not None
        assert stmt.merges[0].source is not None


# =============================================================================
# VIEW Command Tests
# =============================================================================


class TestViewCommand:
    """Tests for VIEW command ASG field population."""

    def test_view_command_simple(self):
        """VIEW with arguments produces MViewStatement."""
        from m2py.asg import MViewStatement

        parser = MUMPSParser()
        routine = parser.parse('TEST\n V "UNDEF"\n')

        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MViewStatement)
        assert len(stmt.arguments) >= 1

    def test_view_command_with_expression(self):
        """VIEW with variable expression."""
        from m2py.asg import MViewStatement

        parser = MUMPSParser()
        routine = parser.parse("TEST\n V X\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MViewStatement)
        assert len(stmt.arguments) >= 1

    def test_view_command_with_postcondition(self):
        """VIEW:condition args handles postcondition."""
        from m2py.asg import MViewStatement

        parser = MUMPSParser()
        routine = parser.parse('TEST\n V:X>0 "DEBUG"\n')

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MViewStatement)
        assert stmt.postcondition is not None


# =============================================================================
# LOCK Command Tests
# =============================================================================


class TestLockCommand:
    """Tests for LOCK command ASG field population."""

    def test_lock_command_simple(self):
        """LOCK variable produces MLockStatement."""
        from m2py.asg import MLockStatement

        parser = MUMPSParser()
        routine = parser.parse("TEST\n L ^GLOBAL\n")

        label = routine.labels[0]
        assert len(label.body.statements) == 1

        stmt = label.body.statements[0]
        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1

    def test_lock_command_with_timeout(self):
        """LOCK variable:timeout handles timeout."""
        from m2py.asg import MLockStatement

        parser = MUMPSParser()
        routine = parser.parse("TEST\n L ^GLOBAL:5\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1

    def test_lock_increment(self):
        """LOCK +variable produces incremental lock."""
        from m2py.asg import MLockStatement

        parser = MUMPSParser()
        routine = parser.parse("TEST\n L +^GLOBAL\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1
        assert stmt.lock_type == "+"

    def test_lock_decrement(self):
        """LOCK -variable produces decremental lock."""
        from m2py.asg import MLockStatement

        parser = MUMPSParser()
        routine = parser.parse("TEST\n L -^GLOBAL\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert len(stmt.targets) >= 1
        assert stmt.lock_type == "-"

    def test_lock_release_all(self):
        """LOCK without arguments releases all locks."""
        from m2py.asg import MLockStatement

        parser = MUMPSParser()
        routine = parser.parse("TEST\n L\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MLockStatement)
        assert stmt.targets == []


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
        from m2py.asg import MDoStatement

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

    def test_job_with_processparams_only(self):
        """JOB with processparameters but no timeout."""
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
