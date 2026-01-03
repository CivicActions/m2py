"""Tests for Structured System Variable Names (SSVNs) parsing (§7.1.3).

Tests verify the textX grammar correctly captures SSVN syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.3
"""

import pytest


# In-scope SSVNs from contracts/test-naming.md SSVN_LIST
SSVN_IN_SCOPE = [
    "^$JOB",
    "^$ROUTINE",
    "^$GLOBAL",
    "^$LOCK",
    "^$DEVICE",
    "^$CHARACTER",
    "^$SYSTEM",
]

# Out-of-scope SSVNs per FR-055
SSVN_OUT_OF_SCOPE = [
    "^$LIBRARY",
    "^$EVENT",
]


@pytest.mark.parser
class TestSSVNsParsing:
    """Parser-level tests for SSVNs (§7.1.3).

    Structured System Variables provide access to system information.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$JOB SSVN parsing")
    def test_ssvn_job(self, parse_expression):
        """^$JOB SSVN parses correctly (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$ROUTINE SSVN parsing")
    def test_ssvn_routine(self, parse_expression):
        """^$ROUTINE SSVN parses correctly (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$GLOBAL SSVN parsing")
    def test_ssvn_global(self, parse_expression):
        """^$GLOBAL SSVN parses correctly (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$LOCK SSVN parsing")
    def test_ssvn_lock(self, parse_expression):
        """^$LOCK SSVN parses correctly (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$DEVICE SSVN parsing")
    def test_ssvn_device(self, parse_expression):
        """^$DEVICE SSVN parses correctly (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$CHARACTER SSVN parsing")
    def test_ssvn_character(self, parse_expression):
        """^$CHARACTER SSVN parses correctly (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$SYSTEM SSVN parsing")
    def test_ssvn_system(self, parse_expression):
        """^$SYSTEM SSVN parses correctly (§7.1.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ^$Z... SSVN parsing")
    def test_ssvn_z_implementation_defined(self, parse_expression):
        """Implementation-defined ^$Z... SSVN parses correctly (§7.1.3)."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestSSVNsOutOfScope:
    """Out-of-scope SSVNs (§7.1.3)."""

    @pytest.mark.skip(reason="Out of scope: ^$LIBRARY SSVN per FR-055")
    def test_ssvn_library_out_of_scope(self):
        """^$LIBRARY is out of scope."""
        pass

    @pytest.mark.skip(reason="Out of scope: ^$EVENT SSVN per FR-055")
    def test_ssvn_event_out_of_scope(self):
        """^$EVENT is out of scope."""
        pass


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
