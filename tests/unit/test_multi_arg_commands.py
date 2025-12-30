"""Unit tests for multi-argument command handling (Phase 78).

Tests verify that commands supporting multiple arguments correctly capture
all arguments, not just the first. These tests validate fixes for:
- MERGE: Multiple merge pairs (M X=Y,Z=W)
- OPEN: Multiple devices (O DEV1,DEV2)
- CLOSE: Multiple devices (C DEV1,DEV2)
- USE: Multiple devices (U DEV1,DEV2)
- JOB: Multiple targets (J LABEL1,LABEL2)

Per MUMPS 1995 specification, all these commands use "L argument" syntax
where L = comma-separated list.
"""

from m2py.parser import MUMPSParser
from m2py.asg import (
    MMergeStatement,
    MOpenStatement,
    MCloseStatement,
    MUseStatement,
    MJobStatement,
    MGlobal,
)


class TestMultiMerge:
    """Tests for MERGE command with multiple merge pairs."""

    def test_single_merge(self):
        """Single MERGE pair works correctly."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n M X=Y\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MMergeStatement)
        assert len(stmt.merges) == 1
        assert stmt.merges[0].destination.name == "X"
        assert stmt.merges[0].source.name == "Y"

    def test_multi_merge(self):
        """MERGE with multiple pairs captures all pairs.

        This is the key fix - previously only the last pair was kept.
        """
        parser = MUMPSParser()
        routine = parser.parse("TEST\n M X=Y,Z=W\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MMergeStatement)
        assert len(stmt.merges) == 2

        # First pair: X=Y
        assert stmt.merges[0].destination.name == "X"
        assert stmt.merges[0].source.name == "Y"

        # Second pair: Z=W
        assert stmt.merges[1].destination.name == "Z"
        assert stmt.merges[1].source.name == "W"

    def test_multi_merge_globals(self):
        """MERGE with multiple global pairs."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n M ^A=^B,^C=^D\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MMergeStatement)
        assert len(stmt.merges) == 2

        assert isinstance(stmt.merges[0].destination, MGlobal)
        assert stmt.merges[0].destination.name == "A"
        assert isinstance(stmt.merges[1].destination, MGlobal)
        assert stmt.merges[1].destination.name == "C"

    def test_vista_ztmon_pattern(self):
        """Test VistA ZTMON.m pattern with two merge pairs.

        This pattern appears in 210+ VistA files.
        """
        parser = MUMPSParser()
        # Simplified version of ZTMON pattern
        routine = parser.parse(
            'TEST\n M ZTC("S")=^ZTS("STATUS"),ZTC("L")=^ZTS("LOADA")\n'
        )

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MMergeStatement)
        assert len(stmt.merges) == 2

        # First merge: ZTC("S")=^ZTS("STATUS")
        assert stmt.merges[0].destination.name == "ZTC"
        assert stmt.merges[0].source.name == "ZTS"

        # Second merge: ZTC("L")=^ZTS("LOADA")
        assert stmt.merges[1].destination.name == "ZTC"
        assert stmt.merges[1].source.name == "ZTS"


class TestMultiOpen:
    """Tests for OPEN command with multiple devices."""

    def test_single_open(self):
        """Single OPEN device works correctly."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O X\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "X"

    def test_multi_open(self):
        """OPEN with multiple devices captures all devices."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n O DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"

    def test_open_with_params_multiple(self):
        """OPEN with parameters on multiple devices."""
        parser = MUMPSParser()
        routine = parser.parse('TEST\n O DEV1:("A"):5,DEV2:("B")\n')

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MOpenStatement)
        assert len(stmt.devices) == 2

        # First device has params and timeout
        assert stmt.devices[0].device_expr.name == "DEV1"
        assert len(stmt.devices[0].parameters) == 1
        assert stmt.devices[0].timeout is not None

        # Second device has params only
        assert stmt.devices[1].device_expr.name == "DEV2"
        assert len(stmt.devices[1].parameters) == 1


class TestMultiClose:
    """Tests for CLOSE command with multiple devices."""

    def test_single_close(self):
        """Single CLOSE device works correctly."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n C X\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "X"

    def test_multi_close(self):
        """CLOSE with multiple devices captures all devices."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n C DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"


class TestMultiUse:
    """Tests for USE command with multiple devices."""

    def test_single_use(self):
        """Single USE device works correctly."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n U X\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1
        assert stmt.devices[0].device_expr.name == "X"

    def test_multi_use(self):
        """USE with multiple devices captures all devices."""
        parser = MUMPSParser()
        routine = parser.parse("TEST\n U DEV1,DEV2\n")

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 2

        assert stmt.devices[0].device_expr.name == "DEV1"
        assert stmt.devices[1].device_expr.name == "DEV2"


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


class TestIndirectionSubscriptAnalysis:
    """Tests for MIndirection subscript analysis."""

    def test_indirection_expression_subscripts_analyzed(self):
        """Variables in @A(B,C) have subscripts on the expression, not indirection.

        The grammar @A(B,C) is parsed as @(A(B,C)) - indirection of subscripted A.
        The subscripts are on the inner expression, and they should be analyzed.
        """
        from m2py.asg import MIndirection

        parser = MUMPSParser()
        routine = parser.parse("TEST\n S @A(B,C)=1\n")

        stmt = routine.labels[0].body.statements[0]
        target = stmt.assignments[0].target

        # The target should be an indirection
        assert isinstance(target, MIndirection)

        # The expression is A(B,C) - a subscripted variable
        inner = target.expression
        assert inner.name == "A"
        assert len(inner.subscripts) == 2

        # Subscripts should be analyzed expressions
        assert inner.subscripts[0].name == "B"
        assert inner.subscripts[1].name == "C"

    def test_indirection_requires_runtime(self):
        """MIndirection has requires_runtime_eval=True."""
        from m2py.asg import MIndirection

        parser = MUMPSParser()
        routine = parser.parse("TEST\n S X=@A\n")

        stmt = routine.labels[0].body.statements[0]
        value = stmt.assignments[0].value

        assert isinstance(value, MIndirection)
        assert value.requires_runtime_eval is True


class TestCloseUseWithParams:
    """Tests for CLOSE and USE with device parameters."""

    def test_close_with_params(self):
        """CLOSE device:(params) parses parameters."""
        parser = MUMPSParser()
        routine = parser.parse('TEST\n C DEV:("PARAM")\n')

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MCloseStatement)
        assert len(stmt.devices) == 1
        assert len(stmt.devices[0].parameters) == 1

    def test_use_with_params(self):
        """USE device:(params) parses parameters."""
        parser = MUMPSParser()
        routine = parser.parse('TEST\n U DEV:("PARAM")\n')

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MUseStatement)
        assert len(stmt.devices) == 1
        assert len(stmt.devices[0].parameters) == 1
