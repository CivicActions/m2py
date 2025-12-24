"""Tests for external routine call representation (T373)."""

from m2py.parser import MUMPSParser


class TestExternalRoutineCalls:
    """Test that external routine calls (^ROUTINE syntax) are correctly represented."""

    def test_do_external_routine_has_empty_name(self):
        """Test D ^ROUTINE sets name='' not name=None."""
        parser = MUMPSParser()
        source = """TEST	;TEST
	D ^VREPORT
	Q
"""
        routine = parser.parse(source, "test.m")

        # Find the DO statement
        do_stmt = routine.labels[0].body.statements[0]
        assert do_stmt.__class__.__name__ == "MDoStatement"

        # Check the target
        assert len(do_stmt.targets) == 1
        target = do_stmt.targets[0]
        assert target.name == "", f"Expected name='', got name={repr(target.name)}"
        assert target.name is not None, "name should be '' not None"
        assert target.routine == "VREPORT"

    def test_goto_external_routine_has_empty_name(self):
        """Test G ^ROUTINE sets name='' not name=None."""
        parser = MUMPSParser()
        source = """TEST	;TEST
	G ^VREPORT
	Q
"""
        routine = parser.parse(source, "test.m")

        # Find the GOTO statement
        goto_stmt = routine.labels[0].body.statements[0]
        assert goto_stmt.__class__.__name__ == "MGotoStatement"

        # Check the target
        assert len(goto_stmt.targets) == 1
        target = goto_stmt.targets[0]
        assert target.name == "", f"Expected name='', got name={repr(target.name)}"
        assert target.name is not None, "name should be '' not None"
        assert target.routine == "VREPORT"

    def test_do_label_with_routine_has_label_name(self):
        """Test D LABEL^ROUTINE sets name='LABEL'."""
        parser = MUMPSParser()
        source = """TEST	;TEST
	D START^VREPORT
	Q
"""
        routine = parser.parse(source, "test.m")

        do_stmt = routine.labels[0].body.statements[0]
        target = do_stmt.targets[0]
        assert target.name == "START"
        assert target.routine == "VREPORT"

    def test_do_local_label_has_name_no_routine(self):
        """Test D LABEL sets name='LABEL', routine=None."""
        parser = MUMPSParser()
        source = """TEST	;TEST
	D HELPER
	Q
HELPER	W "Test"
	Q
"""
        routine = parser.parse(source, "test.m")

        do_stmt = routine.labels[0].body.statements[0]
        target = do_stmt.targets[0]
        assert target.name == "HELPER"
        assert target.routine is None
