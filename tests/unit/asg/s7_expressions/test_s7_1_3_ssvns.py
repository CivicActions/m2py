"""Tests for SSVNs ASG analysis (§7.1.3).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.3

SSVNs (Structured System Variables) provide access to system information.
They use ^$ prefix followed by a name and optional subscripts.

Per spec §7.1.3:
- ^$CHARACTER - Character set information
- ^$DEVICE - Device information
- ^$EVENT - Event information (out of scope)
- ^$GLOBAL - Global variable information
- ^$JOB - Process information
- ^$LIBRARY - Library information (out of scope)
- ^$LOCK - Lock table information
- ^$ROUTINE - Routine information
- ^$SYSTEM - System information
- ^$Z... - Implementation-defined
"""

import pytest

from m2py.asg import MStructuredSystemVariable, MLiteral, MVariable


@pytest.mark.asg
class TestSsvnsAnalysis:
    """ASG-level tests for structured system variables analysis (§7.1.3).

    These tests verify that SSVNs are correctly represented in the ASG
    with proper name and subscript information for Python code generation.
    """

    def test_ssvn_global(self, analyze_routine):
        """^$GLOBAL SSVN is correctly analyzed (§7.1.3.3).

        Example from spec: ^$Global(G) returns info about global G.
        Used for: FOR Set G=$Order(^$Global(G)) - iterate global directory
        """
        routine = analyze_routine('TEST\n W ^$GLOBAL("MYDATA")')
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]

        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "GLOBAL"
        assert len(arg.subscripts) == 1
        # Subscript should be a literal string "MYDATA"
        assert isinstance(arg.subscripts[0], MLiteral)
        assert arg.subscripts[0].value == "MYDATA"

    def test_ssvn_job(self, analyze_routine):
        """^$JOB SSVN is correctly analyzed (§7.1.3.4).

        Example from spec: ^$Job(J,"CHARACTER") returns charset for job J.
        Used for: iterating active jobs, getting job properties
        """
        routine = analyze_routine('TEST\n W ^$JOB(123,"CHARACTER")')
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]

        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "JOB"
        assert len(arg.subscripts) == 2
        # First subscript: job number
        assert isinstance(arg.subscripts[0], MLiteral)
        assert arg.subscripts[0].value == 123
        # Second subscript: property name
        assert isinstance(arg.subscripts[1], MLiteral)
        assert arg.subscripts[1].value == "CHARACTER"

    def test_ssvn_lock(self, analyze_routine):
        """^$LOCK SSVN is correctly analyzed (§7.1.3.5).

        Example from spec: ^$Lock(L) provides LOCK table information.
        Used for: iterating locks, checking lock ownership
        """
        routine = analyze_routine('TEST\n W ^$LOCK("^DATA")')
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]

        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "LOCK"
        assert len(arg.subscripts) == 1
        assert isinstance(arg.subscripts[0], MLiteral)
        assert arg.subscripts[0].value == "^DATA"

    def test_ssvn_routine(self, analyze_routine):
        """^$ROUTINE SSVN is correctly analyzed (§7.1.3.6).

        Example from spec: ^$Routine("TEST") returns routine info.
        Used for: checking routine existence, getting routine properties
        """
        routine = analyze_routine('TEST\n W ^$ROUTINE("MYRTN")')
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]

        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "ROUTINE"
        assert len(arg.subscripts) == 1
        assert isinstance(arg.subscripts[0], MLiteral)
        assert arg.subscripts[0].value == "MYRTN"

    def test_ssvn_system(self, analyze_routine):
        """^$SYSTEM SSVN is correctly analyzed (§7.1.3.7).

        Example from spec: ^$System provides system-wide information.
        Used for: getting system properties without subscript
        """
        routine = analyze_routine("TEST\n W ^$SYSTEM")
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]

        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "SYSTEM"
        # ^$SYSTEM can be used without subscripts
        assert len(arg.subscripts) == 0

    def test_ssvn_device(self, analyze_routine):
        """^$DEVICE SSVN is correctly analyzed (§7.1.3.2).

        Example from spec: ^$Device(devicexpr) provides device info.
        Used for: checking device properties, availability
        """
        routine = analyze_routine("TEST\n W ^$DEVICE")
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]

        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "DEVICE"
        assert len(arg.subscripts) == 0

    def test_ssvn_character(self, analyze_routine):
        """^$CHARACTER SSVN is correctly analyzed (§7.1.3.1).

        Example from spec: ^$Character(charsetexpr) provides charset info.
        Used for: character set queries, conversion algorithms
        """
        routine = analyze_routine('TEST\n W ^$CHARACTER("UTF8","A","LOWER")')
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]

        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "CHARACTER"
        assert len(arg.subscripts) == 3
        assert arg.subscripts[0].value == "UTF8"
        assert arg.subscripts[1].value == "A"
        assert arg.subscripts[2].value == "LOWER"

    def test_ssvn_job_variable_subscript(self, analyze_routine):
        """^$JOB with variable subscript is correctly analyzed (§7.1.3.4).

        Real-world pattern: FOR Set J=$Order(^$Job(J)) iterates jobs.
        Subscript can be a variable reference.
        """
        routine = analyze_routine("TEST\n W ^$JOB(J)")
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]

        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "JOB"
        assert len(arg.subscripts) == 1
        # Subscript should be a variable reference
        assert isinstance(arg.subscripts[0], MVariable)
        assert arg.subscripts[0].name == "J"

    def test_ssvn_library(self, analyze_routine):
        """^$LIBRARY SSVN is correctly analyzed (§7.1.3.6).

        ^$Library provides information about the availability of
        libraries and library elements in a system.
        """
        routine = analyze_routine('TEST\n W ^$LIBRARY("MATH")')
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]

        assert isinstance(arg, MStructuredSystemVariable)
        assert arg.name.upper() == "LIBRARY"
        assert len(arg.subscripts) == 1
        assert isinstance(arg.subscripts[0], MLiteral)
        assert arg.subscripts[0].value == "MATH"

    def test_ssvn_library_abbreviated(self, analyze_routine):
        """^$LI abbreviation for LIBRARY is correctly analyzed (§7.1.3.6)."""
        routine = analyze_routine('TEST\n W ^$LI("STRING")')
        label = routine.labels[0]
        stmt = label.body.statements[0]
        arg = stmt.arguments[0]

        assert isinstance(arg, MStructuredSystemVariable)
        # Abbreviated form - name captures what was parsed
        assert arg.name.upper() == "LI"
        assert len(arg.subscripts) == 1

    # ^$EVENT SSVN is out of scope - requires MWAPI windowing support.
    # ^$EVENT is valid MUMPS 1995 syntax (§7.1.3.3) but its semantics require
    # the MWAPI windowing runtime (X11.6) which YottaDB does not implement.
    # VistA uses this in ZISG*.m files for GUI interfaces.
    # See docs/limitations.md - LIM-003: MWAPI.
