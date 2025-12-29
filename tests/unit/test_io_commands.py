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
    assert stmt.device_expr is not None


def test_close_command_simple():
    """Test CLOSE command with simple device."""
    parser = MUMPSParser()
    routine = parser.parse("TEST\n C X\n")

    assert len(routine.labels) == 1
    label = routine.labels[0]
    assert len(label.body.statements) == 1

    stmt = label.body.statements[0]
    assert isinstance(stmt, MCloseStatement)
    assert stmt.device_expr is not None


def test_use_command_simple():
    """Test USE command with simple device."""
    parser = MUMPSParser()
    routine = parser.parse("TEST\n U X\n")

    assert len(routine.labels) == 1
    label = routine.labels[0]
    assert len(label.body.statements) == 1

    stmt = label.body.statements[0]
    assert isinstance(stmt, MUseStatement)
    assert stmt.device_expr is not None


def test_job_command_simple():
    """Test JOB command with simple label."""
    parser = MUMPSParser()
    routine = parser.parse("TEST\n J LABEL\n")

    assert len(routine.labels) == 1
    label = routine.labels[0]
    assert len(label.body.statements) == 1

    stmt = label.body.statements[0]
    assert isinstance(stmt, MJobStatement)
    assert stmt.call is not None
    assert stmt.call.name == "LABEL"


def test_job_command_external():
    """Test JOB command with external routine."""
    parser = MUMPSParser()
    routine = parser.parse("TEST\n J ^ROUTINE\n")

    assert len(routine.labels) == 1
    label = routine.labels[0]
    assert len(label.body.statements) == 1

    stmt = label.body.statements[0]
    assert isinstance(stmt, MJobStatement)
    assert stmt.call is not None
    assert stmt.call.routine == "ROUTINE"


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
    assert stmt.device_expr is not None
    assert stmt.device_expr.name == "X"
    assert stmt.timeout is not None
    assert stmt.timeout.value == 5
    assert stmt.parameters == []


def test_open_command_with_double_colon_timeout():
    """Test OPEN command with double colon timeout (::timeout syntax)."""
    parser = MUMPSParser()
    routine = parser.parse("TEST\n O X::10\n")

    label = routine.labels[0]
    stmt = label.body.statements[0]

    assert isinstance(stmt, MOpenStatement)
    assert stmt.device_expr is not None
    assert stmt.device_expr.name == "X"
    assert stmt.timeout is not None
    assert stmt.timeout.value == 10
    assert stmt.parameters == []


def test_open_command_with_params():
    """Test OPEN command with parameters."""
    parser = MUMPSParser()
    routine = parser.parse('TEST\n O X:("ABC")\n')

    label = routine.labels[0]
    stmt = label.body.statements[0]

    assert isinstance(stmt, MOpenStatement)
    assert stmt.device_expr is not None
    assert stmt.device_expr.name == "X"
    assert stmt.timeout is None
    assert len(stmt.parameters) == 1


def test_open_command_with_params_and_timeout():
    """Test OPEN command with parameters and timeout."""
    parser = MUMPSParser()
    routine = parser.parse('TEST\n O X:("A":0:2048):5\n')

    label = routine.labels[0]
    stmt = label.body.statements[0]

    assert isinstance(stmt, MOpenStatement)
    assert stmt.device_expr is not None
    assert stmt.device_expr.name == "X"
    assert stmt.timeout is not None
    assert stmt.timeout.value == 5
    assert len(stmt.parameters) == 3


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
        assert stmt.destination is not None
        assert stmt.source is not None

    def test_merge_command_with_postcondition(self):
        """MERGE:condition dest=source handles postcondition."""
        from m2py.asg import MMergeStatement

        parser = MUMPSParser()
        routine = parser.parse("TEST\n M:X>0 ^DEST=^SRC\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MMergeStatement)
        assert stmt.postcondition is not None
        assert stmt.destination is not None
        assert stmt.source is not None

    def test_merge_with_local_variables(self):
        """MERGE can merge local variable trees."""
        from m2py.asg import MMergeStatement

        parser = MUMPSParser()
        routine = parser.parse("TEST\n M LOCAL1=LOCAL2\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MMergeStatement)
        assert stmt.destination is not None
        assert stmt.source is not None


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
        call = stmt.targets[0]
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
        call = stmt.targets[0]
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

    def test_job_backward_compat_calls_property(self):
        """MJobStatement.calls property provides backward compatibility.

        The .calls property is a deprecated alias for .targets to maintain
        backward compatibility with existing code.
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n J LABEL\n")

        label = routine.labels[0]
        stmt = label.body.statements[0]

        assert isinstance(stmt, MJobStatement)
        # Both .calls and .targets should return the same list
        assert stmt.calls is stmt.targets
        assert len(stmt.calls) == 1
        assert stmt.calls[0].name == "LABEL"
