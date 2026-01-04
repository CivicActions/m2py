"""Tests for ZGOTO command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.asg
@pytest.mark.ydb
class TestZgotoAsg:
    """ASG-level tests for ZGOTO command (YDB)."""

    def test_zgoto_asg_node(self):
        """ZGOTO creates proper ASG node with level and target."""
        from m2py import MUMPSParser
        from m2py.asg.statements import MZGotoStatement
        from m2py.asg.elements import MCall

        source = """TEST
 ZGOTO 1:label^routine
"""
        parser = MUMPSParser()
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZGotoStatement)
        assert len(stmt.args) == 1
        arg = stmt.args[0]
        assert arg.level is not None
        assert arg.level.value == 1
        assert isinstance(arg.target, MCall)

    def test_zgoto_type_classification(self):
        """ZGOTO level 0 is classified as unwinding (return to base)."""
        from m2py import MUMPSParser
        from m2py.asg.statements import MZGotoStatement

        source = """TEST
 ZGOTO 0
"""
        parser = MUMPSParser()
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZGotoStatement)
        assert len(stmt.args) == 1
        arg = stmt.args[0]
        # Level 0 means unwind to base - this is the "unwinding" type
        assert arg.level is not None
        assert arg.level.value == 0
        # No target means just unwind
        assert arg.target is None

    def test_zgoto_entryref_resolution(self):
        """ZGOTO entryref is resolved to target with label and routine."""
        from m2py import MUMPSParser
        from m2py.asg.statements import MZGotoStatement
        from m2py.asg.elements import MCall

        source = """TEST
 ZGOTO 2:ERROR^HANDLER
"""
        parser = MUMPSParser()
        routine = parser.parse(source)
        stmt = routine.labels[0].body.statements[0]

        assert isinstance(stmt, MZGotoStatement)
        arg = stmt.args[0]
        assert isinstance(arg.target, MCall)
        assert arg.target.name == "ERROR"
        assert arg.target.routine == "HANDLER"


@pytest.mark.asg
@pytest.mark.ydb
class TestZGotoLabelRefAnalysis:
    """Test LabelRef analysis for ZGOTO command."""

    def test_zgoto_with_labelref_target(self):
        """ZGOTO 1:label^routine should produce MZGotoStatement with target."""
        from m2py import MUMPSParser
        from m2py.asg.statements import MZGotoStatement
        from m2py.asg.elements import MCall

        source = """TEST
 ZGOTO 1:label^routine
"""
        parser = MUMPSParser()
        routine = parser.parse(source)

        # Find the ZGOTO statement
        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MZGotoStatement)
        assert len(stmt.args) == 1

        arg = stmt.args[0]
        assert arg.target is not None
        assert isinstance(arg.target, MCall)
        assert arg.target.name == "label"
        assert arg.target.routine == "routine"

    def test_zgoto_with_indirect_routine(self):
        """ZGOTO 1:label^@routinevar should handle indirect routine."""
        from m2py import MUMPSParser
        from m2py.asg.statements import MZGotoStatement
        from m2py.asg.elements import MCall

        source = """TEST
 ZGOTO 1:label^@routinevar
"""
        parser = MUMPSParser()
        routine = parser.parse(source)

        stmt = routine.labels[0].body.statements[0]
        assert isinstance(stmt, MZGotoStatement)
        assert len(stmt.args) == 1

        arg = stmt.args[0]
        assert arg.target is not None
        assert isinstance(arg.target, MCall)
        assert arg.target.routine_is_indirect
