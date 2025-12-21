"""Unit tests for I/O command parsing and ASG generation."""

import pytest
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
