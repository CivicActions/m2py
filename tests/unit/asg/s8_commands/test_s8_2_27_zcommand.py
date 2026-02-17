"""Tests for Z-commands ASG analysis (YDB Extensions).

Reference: YDB-specific extensions to MUMPS
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.asg.statements import (
    MZAllocateStatement,
    MZBreakStatement,
    MZDeallocateStatement,
    MZGotoStatement,
    MZHaltStatement,
    MZLinkStatement,
    MZLoadStatement,
    MZPrintStatement,
    MZShowStatement,
    MZTCommitStatement,
    MZTStartStatement,
    MZWriteStatement,
)


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
@pytest.mark.ydb
class TestZCommandsAnalysis:
    """ASG-level tests for YDB Z-commands analysis."""

    def test_zwrite_analysis(self):
        """ZWRITE command is correctly analyzed (YDB extension).

        Verifies that ZWRITE produces MZWriteStatement.
        """
        # Simple ZWRITE
        stmt = analyze_first_command("ZWR X")
        assert isinstance(stmt, MZWriteStatement)
        # Has args attribute
        assert hasattr(stmt, "args")

        # ZWRITE with pattern
        stmt2 = analyze_first_command("ZWR ^GLOBAL")
        assert isinstance(stmt2, MZWriteStatement)

        # Argumentless ZWRITE
        stmt3 = analyze_first_command("ZWR")
        assert isinstance(stmt3, MZWriteStatement)

    def test_zhalt_analysis(self):
        """ZHALT command is correctly analyzed (YDB extension).

        Verifies that ZHALT produces MZHaltStatement with exit code.
        """
        # ZHALT with exit code
        stmt = analyze_first_command("ZHALT 1")
        assert isinstance(stmt, MZHaltStatement)
        assert hasattr(stmt, "exitcode")
        assert stmt.exitcode is not None

        # ZHALT with zero
        stmt2 = analyze_first_command("ZHALT 0")
        assert isinstance(stmt2, MZHaltStatement)

        # Argumentless ZHALT
        stmt3 = analyze_first_command("ZHALT")
        assert isinstance(stmt3, MZHaltStatement)

    def test_zlink_analysis(self):
        """ZLINK/ZLOAD commands are correctly analyzed (YDB extension).

        Verifies that ZLINK and ZLOAD produce distinct ASG statement types:
        - ZL/ZLOAD → MZLoadStatement (load compiled routine object)
        - ZLI/ZLINK → MZLinkStatement (compile and link routine)
        """
        # ZL is ZLOAD abbreviation -> MZLoadStatement
        stmt = analyze_first_command('ZL "routine"')
        assert isinstance(stmt, MZLoadStatement)

        # ZLINK is distinct command -> MZLinkStatement
        stmt2 = analyze_first_command("ZLINK MYRTN")
        assert isinstance(stmt2, MZLinkStatement)

    def test_zshow_analysis(self):
        """ZSHOW command is correctly analyzed (YDB extension).

        Verifies that ZSHOW produces MZShowStatement.
        """
        # ZSHOW with info code
        stmt = analyze_first_command('ZSH "V"')
        assert isinstance(stmt, MZShowStatement)
        assert hasattr(stmt, "args")

        # ZSHOW with variable target
        stmt2 = analyze_first_command('ZSH "V":X')
        assert isinstance(stmt2, MZShowStatement)

    def test_zt_transaction_analysis(self):
        """ZTSTART/ZTCOMMIT commands are correctly analyzed (YDB extension).

        Verifies that journaled transaction commands produce correct ASG.
        """
        # ZTSTART
        stmt = analyze_first_command("ZTS")
        assert isinstance(stmt, MZTStartStatement)

        # ZTSTART full keyword
        stmt2 = analyze_first_command("ZTSTART")
        assert isinstance(stmt2, MZTStartStatement)

        # ZTCOMMIT
        stmt3 = analyze_first_command("ZTC")
        assert isinstance(stmt3, MZTCommitStatement)

        # ZTCOMMIT full keyword
        stmt4 = analyze_first_command("ZTCOMMIT")
        assert isinstance(stmt4, MZTCommitStatement)

    def test_zbreak_analysis(self):
        """ZBREAK command produces MZBreakStatement with args."""
        stmt = analyze_first_command('ZB TEST:"W 1":3')
        assert isinstance(stmt, MZBreakStatement)
        assert len(stmt.args) >= 1
        arg = stmt.args[0]
        assert arg.location is not None
        assert arg.action is not None
        assert arg.count is not None

    def test_zbreak_simple_label(self):
        """ZBREAK with bare label."""
        stmt = analyze_first_command("ZB LABEL")
        assert isinstance(stmt, MZBreakStatement)
        assert len(stmt.args) >= 1
        assert stmt.args[0].location is not None

    def test_zprint_analysis(self):
        """ZPRINT command produces MZPrintStatement with label/offset/routine."""
        stmt = analyze_first_command("ZP TEST")
        assert isinstance(stmt, MZPrintStatement)
        assert len(stmt.args) >= 1
        assert stmt.args[0].start_label == "TEST"

    def test_zprint_with_routine(self):
        """ZPRINT label^routine."""
        stmt = analyze_first_command("ZP TEST^MYRTN")
        assert isinstance(stmt, MZPrintStatement)
        arg = stmt.args[0]
        assert arg.start_label == "TEST"
        assert arg.routine == "MYRTN"

    def test_zprint_with_offset(self):
        """ZPRINT label+offset."""
        stmt = analyze_first_command("ZP TEST+3")
        assert isinstance(stmt, MZPrintStatement)
        arg = stmt.args[0]
        assert arg.start_label == "TEST"
        assert arg.start_offset is not None

    def test_zgoto_with_level_and_target(self):
        """ZGOTO level:target produces MZGotoStatement with level and target."""
        stmt = analyze_first_command("ZGOTO 1:DONE")
        assert isinstance(stmt, MZGotoStatement)
        assert len(stmt.args) >= 1
        arg = stmt.args[0]
        assert arg.level is not None
        assert arg.target is not None

    def test_zgoto_level_only(self):
        """ZGOTO 0 — unwind to level 0."""
        stmt = analyze_first_command("ZGOTO 0")
        assert isinstance(stmt, MZGotoStatement)
        assert len(stmt.args) >= 1
        assert stmt.args[0].level is not None

    def test_zallocate_analysis(self):
        """ZALLOCATE produces MZAllocateStatement with lock targets."""
        stmt = analyze_first_command("ZA ^A,^B")
        assert isinstance(stmt, MZAllocateStatement)
        assert len(stmt.targets) >= 2
        # ZALLOCATE always forces lockop="+"
        for t in stmt.targets:
            assert t.lockop == "+"

    def test_zallocate_with_timeout(self):
        """ZA ^X:5 — ZALLOCATE with timeout."""
        stmt = analyze_first_command("ZA ^X:5")
        assert isinstance(stmt, MZAllocateStatement)
        assert len(stmt.targets) >= 1

    def test_zdeallocate_analysis(self):
        """ZDEALLOCATE produces MZDeallocateStatement with lock targets."""
        stmt = analyze_first_command("ZD ^A,^B")
        assert isinstance(stmt, MZDeallocateStatement)
        assert len(stmt.targets) >= 2
        # ZDEALLOCATE always forces lockop="-"
        for t in stmt.targets:
            assert t.lockop == "-"
