"""Tests for Z-commands ASG analysis (YDB Extensions).

Reference: YDB-specific extensions to MUMPS

Migrated from: tests/unit/test_command_analysis.py::TestOtherStatementAnalysis (partial)
"""

import pytest
from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import MZAllocateStatement, MZDeallocateStatement


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
@pytest.mark.ydb
class TestZCommandsAnalysis:
    """ASG-level tests for YDB Z-commands analysis.

    Migrated from: tests/unit/test_command_analysis.py::TestOtherStatementAnalysis (partial)
    """

    def test_zallocate(self):
        """za X produces MZAllocateStatement with incremental lock (YDB extension).

        Migrated from: test_command_analysis.py::TestOtherStatementAnalysis::test_zallocate
        """
        stmt = analyze_first_command("za X")

        assert isinstance(stmt, MZAllocateStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0]["lockop"] == "+"

    def test_zdeallocate(self):
        """zd X produces MZDeallocateStatement with decremental unlock (YDB extension).

        Migrated from: test_command_analysis.py::TestOtherStatementAnalysis::test_zdeallocate
        """
        stmt = analyze_first_command("zd X")

        assert isinstance(stmt, MZDeallocateStatement)
        assert len(stmt.targets) == 1
        assert stmt.targets[0]["lockop"] == "-"

    def test_zdeallocate_with_postcondition(self):
        """Zdeallocate:'(i#2) X produces MZDeallocateStatement with postcondition (YDB extension).

        Migrated from: test_command_analysis.py::TestOtherStatementAnalysis::test_zdeallocate_with_postcondition
        """
        stmt = analyze_first_command("Zdeallocate:'(i#2) X")

        assert isinstance(stmt, MZDeallocateStatement)
        assert stmt.postcondition is not None
        assert len(stmt.targets) == 1

    # ---- Stub tests for unimplemented features ----

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZWRITE analysis")
    def test_zwrite_analysis(self, analyze_routine):
        """ZWRITE command is correctly analyzed (YDB extension)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZHALT analysis")
    def test_zhalt_analysis(self, analyze_routine):
        """ZHALT command is correctly analyzed (YDB extension)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZLINK analysis")
    def test_zlink_analysis(self, analyze_routine):
        """ZLINK command is correctly analyzed (YDB extension)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZSHOW analysis")
    def test_zshow_analysis(self, analyze_routine):
        """ZSHOW command is correctly analyzed (YDB extension)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: ZTSTART/ZTCOMMIT analysis")
    def test_zt_transaction_analysis(self, analyze_routine):
        """ZTSTART/ZTCOMMIT commands are correctly analyzed (YDB extension)."""
        pytest.fail("Stub - implement test")
