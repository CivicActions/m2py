"""Tests for MERGE command parsing (§8.2.13).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.13

Migrated from:
- tests/unit/test_io_commands.py::TestMergeCommand (ASG-level tests)
- tests/unit/test_multi_arg_commands.py::TestMultiMerge (multi-argument tests)
"""

import pytest


@pytest.mark.parser
class TestMergeCommandParsing:
    """Parser-level tests for MERGE command (§8.2.13)."""

    def test_merge_basic(self, command_metamodel):
        """M ^DEST=^SRC - basic merge parses correctly (§8.2.13)."""
        model = command_metamodel.model_from_str("M ^DEST=^SRC", "MergeCommand")
        assert len(model.merges) == 1

    def test_merge_naked_global(self, command_metamodel):
        """M ^(1)=^VV(2) - naked global in MERGE (§8.2.13)."""
        model = command_metamodel.model_from_str("M ^(1)=^VV(2)", "MergeCommand")
        assert len(model.merges) == 1

    def test_merge_indirection(self, command_metamodel):
        """MERGE @CMD - argument-level indirection in MERGE (§8.2.13)."""
        model = command_metamodel.model_from_str("MERGE @CMD", "MergeCommand")
        assert len(model.merges) == 1

    def test_merge_extended_global_pipe(self, command_metamodel):
        """M ^|"dst"|a=^|"src"|b - pipe-delimited extended globals in MERGE (§8.2.13)."""
        model = command_metamodel.model_from_str(
            'M ^|"dst"|a=^|"src"|b', "MergeCommand"
        )
        assert len(model.merges) == 1

    def test_merge_extended_global_bracket(self, command_metamodel):
        """M ^["dst"]a=^["src"]b - bracket-delimited extended globals in MERGE (§8.2.13)."""
        model = command_metamodel.model_from_str(
            'M ^["dst"]a=^["src"]b', "MergeCommand"
        )
        assert len(model.merges) == 1

    def test_merge_multiple_pairs(self, command_metamodel):
        """M X=Y,Z=W - multiple merge pairs parses correctly (§8.2.13).

        Migrated from: test_multi_arg_commands.py::TestMultiMerge::test_multi_merge
        """
        model = command_metamodel.model_from_str("M X=Y,Z=W", "MergeCommand")
        assert len(model.merges) == 2

    def test_merge_multiple_globals(self, command_metamodel):
        """M ^A=^B,^C=^D - multiple global pairs parses correctly (§8.2.13).

        Migrated from: test_multi_arg_commands.py::TestMultiMerge::test_multi_merge_globals
        """
        model = command_metamodel.model_from_str("M ^A=^B,^C=^D", "MergeCommand")
        assert len(model.merges) == 2
