"""Tests for ZGOTO command ASG analysis (YDB extension).

Reference: YottaDB Z-Commands

Migrated from: tests/unit/test_semantic_analyzer.py::TestZGotoLabelRefAnalysis
"""

import pytest
from m2py import MUMPSParser
from m2py.asg.statements import MZGotoStatement
from m2py.asg.elements import MCall


@pytest.mark.asg
@pytest.mark.ydb
class TestZgotoAsg:
    """ASG-level tests for ZGOTO command (YDB).

    Migrated from: TestZGotoLabelRefAnalysis
    """

    def test_zgoto_with_labelref_target(self):
        """ZGOTO 1:label^routine should produce MZGotoStatement with target."""
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

    # ---- Stub tests for unimplemented features ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZGotoType classification")
    def test_zgoto_type_classification(self, analyze_statement):
        """ZGOTO is classified by type (unwinding, computed)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZGOTO entryref resolution")
    def test_zgoto_entryref_resolution(self, analyze_statement):
        """ZGOTO entryref is resolved to target."""
        pytest.fail("Stub - implement test")
