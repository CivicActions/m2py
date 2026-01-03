"""Tests for MERGE command parsing (§8.2.13).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.13
"""

from pathlib import Path

import pytest
from textx import metamodel_from_file

from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar for MERGE command tests."""
    grammar_dir = (
        Path(__file__).parent.parent.parent.parent.parent / "src" / "m2py" / "grammar"
    )
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


@pytest.mark.parser
class TestMergeCommandParsing:
    """Parser-level tests for MERGE command (§8.2.13)."""

    def test_merge_basic(self, command_metamodel):
        """M ^DEST=^SRC parses correctly (§8.2.13)."""
        model = command_metamodel.model_from_str("M ^DEST=^SRC", "MergeCommand")
        assert len(model.merges) == 1

    def test_merge_naked_global(self, command_metamodel):
        """M ^(1)=^VV(2) - naked global in MERGE."""
        model = command_metamodel.model_from_str("M ^(1)=^VV(2)", "MergeCommand")
        assert len(model.merges) == 1

    def test_merge_indirection(self, command_metamodel):
        """MERGE @CMD - argument-level indirection in MERGE."""
        model = command_metamodel.model_from_str("MERGE @CMD", "MergeCommand")
        assert len(model.merges) == 1

    def test_merge_extended_global_pipe(self, command_metamodel):
        """M ^|"dst"|a=^|"src"|b - pipe-delimited extended globals in MERGE."""
        model = command_metamodel.model_from_str(
            'M ^|"dst"|a=^|"src"|b', "MergeCommand"
        )
        assert len(model.merges) == 1

    def test_merge_extended_global_bracket(self, command_metamodel):
        """M ^["dst"]a=^["src"]b - bracket-delimited extended globals in MERGE."""
        model = command_metamodel.model_from_str(
            'M ^["dst"]a=^["src"]b', "MergeCommand"
        )
        assert len(model.merges) == 1

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE global to local")
    def test_merge_global_to_local(self, parse_line):
        """MERGE local=^GLOBAL parses correctly (§8.2.13)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE local to global")
    def test_merge_local_to_global(self, parse_line):
        """MERGE ^GLOBAL=local parses correctly (§8.2.13)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE with subscripts")
    def test_merge_with_subscripts(self, parse_line):
        """MERGE arr(1)=src(2) subscripted merge parses correctly (§8.2.13)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE multiple")
    def test_merge_multiple(self, parse_line):
        """MERGE a=b,c=d multiple merges parses correctly (§8.2.13)."""
        pytest.fail("Stub - implement test")
