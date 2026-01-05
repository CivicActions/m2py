"""Tests for Structured System Variable Names (SSVNs) parsing (§7.1.3).

Tests verify the textX grammar correctly captures SSVN syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.3
- §7.1.3.1 ^$CHARACTER - Character set profiles
- §7.1.3.2 ^$DEVICE - Device information
- §7.1.3.3 ^$EVENT - Event processing (MWAPI - out of scope)
- §7.1.3.5 ^$JOB - Process information
- §7.1.3.6 ^$ROUTINE - Routine information
- §7.1.3.7 ^$LOCK - Lock information
- §7.1.3.8 ^$GLOBAL - Global variable information
- §7.1.3.9 ^$SYSTEM - System information
- §7.1.3.10 ^$Z/^$Y - Implementation-defined
"""

import pytest

from m2py.asg import MRoutine, MStructuredSystemVariable
from m2py.parser import MUMPSParser


# In-scope SSVNs from contracts/test-naming.md SSVN_LIST
SSVN_IN_SCOPE = [
    "^$JOB",
    "^$ROUTINE",
    "^$GLOBAL",
    "^$LOCK",
    "^$DEVICE",
    "^$CHARACTER",
    "^$SYSTEM",
    "^$LIBRARY",
]

# Out-of-scope SSVNs - MWAPI (X11.6) requires windowing support not available in YottaDB
SSVN_OUT_OF_SCOPE = [
    "^$EVENT",  # MWAPI windowing events
    "^$WINDOW",  # MWAPI window definitions
    "^$DISPLAY",  # MWAPI display info
]


def _parse_ssvn_in_write(ssvn_expr: str) -> MStructuredSystemVariable:
    """Helper to parse SSVN expression via WRITE command."""
    parser = MUMPSParser()
    source = f"LABEL\tW {ssvn_expr}\n"
    routine = parser.parse(source)
    assert isinstance(routine, MRoutine)
    label = routine.labels[0]
    stmt = label.body.statements[0]
    assert len(stmt.arguments) >= 1
    return stmt.arguments[0]


@pytest.mark.parser
class TestSSVNsParsing:
    """Parser-level tests for SSVNs (§7.1.3).

    Structured System Variables provide access to system information.
    Uses MUMPSParser to verify grammar captures SSVN syntax via WRITE command.
    """

    def test_ssvn_job(self):
        """^$JOB SSVN parses correctly (§7.1.3.5).

        ^$JOB provides process information - character set, environments, events.
        """
        result = _parse_ssvn_in_write('^$JOB("test")')
        assert isinstance(result, MStructuredSystemVariable)
        assert result.name.upper() == "JOB"
        assert len(result.subscripts) == 1

    def test_ssvn_routine(self):
        """^$ROUTINE SSVN parses correctly (§7.1.3.6).

        ^$ROUTINE provides routine information - source, object code status.
        """
        result = _parse_ssvn_in_write('^$ROUTINE("MYRTN")')
        assert isinstance(result, MStructuredSystemVariable)
        assert result.name.upper() == "ROUTINE"
        assert len(result.subscripts) == 1

    def test_ssvn_global(self):
        """^$GLOBAL SSVN parses correctly (§7.1.3.8).

        ^$GLOBAL provides global variable information.
        """
        result = _parse_ssvn_in_write('^$GLOBAL("MYDATA")')
        assert isinstance(result, MStructuredSystemVariable)
        assert result.name.upper() == "GLOBAL"
        assert len(result.subscripts) == 1

    def test_ssvn_lock(self):
        """^$LOCK SSVN parses correctly (§7.1.3.7).

        ^$LOCK provides lock information - owner, count for lock resources.
        """
        result = _parse_ssvn_in_write('^$LOCK("^MYLOCK")')
        assert isinstance(result, MStructuredSystemVariable)
        assert result.name.upper() == "LOCK"
        assert len(result.subscripts) == 1

    def test_ssvn_device(self):
        """^$DEVICE SSVN parses correctly (§7.1.3.2).

        ^$DEVICE provides device information - state, properties, modes.
        """
        result = _parse_ssvn_in_write("^$DEVICE(0)")
        assert isinstance(result, MStructuredSystemVariable)
        assert result.name.upper() == "DEVICE"
        assert len(result.subscripts) == 1

    def test_ssvn_character(self):
        """^$CHARACTER SSVN parses correctly (§7.1.3.1).

        ^$CHARACTER provides character set profile information.
        """
        result = _parse_ssvn_in_write('^$CHARACTER("M")')
        assert isinstance(result, MStructuredSystemVariable)
        assert result.name.upper() == "CHARACTER"
        assert len(result.subscripts) == 1

    def test_ssvn_system(self):
        """^$SYSTEM SSVN parses correctly (§7.1.3.9).

        ^$SYSTEM provides system-wide defaults and configuration.
        """
        result = _parse_ssvn_in_write("^$SYSTEM")
        assert isinstance(result, MStructuredSystemVariable)
        assert result.name.upper() == "SYSTEM"
        # ^$SYSTEM can be used without subscripts
        assert len(result.subscripts) == 0

    def test_ssvn_z_implementation_defined(self):
        """Implementation-defined ^$Z... SSVN parses correctly (§7.1.3.10).

        ^$Z names are reserved for implementation-specific extensions.
        YottaDB uses ^$ZJOB, ^$ZROUTINE, etc.
        """
        result = _parse_ssvn_in_write('^$ZJOB("test")')
        assert isinstance(result, MStructuredSystemVariable)
        # Z-prefix SSVNs are implementation-defined
        assert result.name.upper().startswith("Z")
        assert len(result.subscripts) == 1

    def test_ssvn_y_implementation_defined(self):
        """Implementation-defined ^$Y... SSVN parses correctly (§7.1.3.10).

        ^$Y names are reserved for implementation-specific extensions.
        """
        result = _parse_ssvn_in_write("^$YTEST")
        assert isinstance(result, MStructuredSystemVariable)
        assert result.name.upper().startswith("Y")


@pytest.mark.parser
class TestSSVNsOutOfScope:
    """Out-of-scope SSVNs - MWAPI (X11.6) requires windowing support.

    YottaDB does not implement MWAPI. See docs/limitations.md for details.
    ^$EVENT (§7.1.3.3) is valid syntax but requires MWAPI runtime.
    See docs/limitations.md - LIM-003: MWAPI.
    """

    pass  # ^$EVENT syntax parses, but runtime requires MWAPI (out of scope)


@pytest.mark.parser
class TestStructuredSystemVariableGrammar:
    """Test Structured System Variables (SSVs) parsing via MUMPSParser.

    Per MUMPS 1995 spec 7.1.4.12, SSVNs use ^$ prefix:
    ^$CHARACTER, ^$DEVICE, ^$EVENT, ^$GLOBAL, ^$JOB, ^$LOCK, ^$ROUTINE, ^$SYSTEM
    """

    def test_ssv_device(self):
        """^$DEVICE should parse as SSV."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine, MStructuredSystemVariable

        parser = MUMPSParser()
        source = "LABEL\tW ^$DEVICE\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert len(stmt.arguments) == 1
        arg = stmt.arguments[0]
        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "DEVICE"

    def test_ssv_job_with_subscript(self):
        """^$JOB(pid) should parse as SSV with subscript."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine, MStructuredSystemVariable

        parser = MUMPSParser()
        source = "LABEL\tW ^$JOB(PID)\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert len(stmt.arguments) == 1
        arg = stmt.arguments[0]
        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "JOB"
        assert len(arg.subscripts) == 1

    def test_ssv_global_with_name(self):
        """^$GLOBAL("MYDATA") should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine, MStructuredSystemVariable

        parser = MUMPSParser()
        source = 'LABEL\tW ^$GLOBAL("MYDATA")\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        assert len(stmt.arguments) == 1
        arg = stmt.arguments[0]
        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "GLOBAL"

    def test_ssv_routine_with_name(self):
        """^$ROUTINE("TEST") should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine, MStructuredSystemVariable

        parser = MUMPSParser()
        source = 'LABEL\tW ^$ROUTINE("TEST")\n'
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]
        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "ROUTINE"

    def test_ssv_system(self):
        """^$SYSTEM should parse."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine, MStructuredSystemVariable

        parser = MUMPSParser()
        source = "LABEL\tW ^$SYSTEM\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]
        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "SYSTEM"

    def test_ssv_abbreviated_d(self):
        """^$D should parse as abbreviated DEVICE."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine, MStructuredSystemVariable

        parser = MUMPSParser()
        source = "LABEL\tW ^$D\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]
        assert isinstance(arg, MStructuredSystemVariable)
        # Single letter D is the abbreviation
        assert arg.name.upper() == "D"

    def test_ssv_abbreviated_j_with_subscript(self):
        """^$J(1) should parse as abbreviated JOB."""
        from m2py.parser import MUMPSParser
        from m2py.asg import MRoutine, MStructuredSystemVariable

        parser = MUMPSParser()
        source = "LABEL\tW ^$J(1)\n"
        routine = parser.parse(source)

        assert isinstance(routine, MRoutine)
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]
        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "J"
