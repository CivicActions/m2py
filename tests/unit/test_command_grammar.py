"""Tests for the command grammar (commands.tx).

Low-level tests that verify the textX command grammar directly.
Tests parse individual commands without semantic analysis.

For semantic analysis tests, see test_command_analysis.py.
"""

import pytest
from pathlib import Path
from textx import metamodel_from_file
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
from m2py.parser.textx_classes import get_all_classes


@pytest.fixture(scope="module")
def command_metamodel():
    """Load the command grammar metamodel with custom classes."""
    grammar_dir = Path(__file__).parent.parent.parent / "src" / "m2py" / "grammar"
    return metamodel_from_file(
        grammar_dir / "commands.tx", classes=get_all_classes(), skipws=False
    )


# TestSetCommand migrated to tests/unit/parser/s8_commands/test_s8_2_18_set.py

# TestWriteCommand migrated to tests/unit/parser/s8_commands/test_s8_2_25_write.py

# TestReadCommand migrated to tests/unit/parser/s8_commands/test_s8_2_17_read.py

# TestIfElseCommands migrated to tests/unit/parser/s8_commands/test_s8_2_09_if.py

# TestForCommand migrated to tests/unit/parser/s8_commands/test_s8_2_05_for.py

# TestGotoCommand migrated to tests/unit/parser/s8_commands/test_s8_2_06_goto.py

# TestDoCommand migrated to tests/unit/parser/s8_commands/test_s8_2_03_do.py

# TestQuitCommand migrated to tests/unit/parser/s8_commands/test_s8_2_16_quit.py


# TestArgumentPostconditions migrated to tests/unit/parser/s8_commands/test_s8_1_general_rules.py

# TestPostconditions migrated to tests/unit/parser/s8_commands/test_s8_1_general_rules.py

# TestQuitFollowedBySet migrated to tests/unit/parser/s8_commands/test_s8_2_16_quit.py

# TestQuitFollowedByTransaction migrated to tests/unit/parser/s8_commands/test_s8_2_16_quit.py

# TestNewKillCommands (NEW) migrated to tests/unit/parser/s8_commands/test_s8_2_14_new.py
# TestNewKillCommands (KILL) migrated to tests/unit/parser/s8_commands/test_s8_2_11_kill.py

# TestOtherCommands split and migrated to:
#   - HANG tests → tests/unit/parser/s8_commands/test_s8_2_08_hang.py
#   - HALT test → tests/unit/parser/s8_commands/test_s8_2_07_halt.py
#   - BREAK test → tests/unit/parser/s8_commands/test_s8_2_01_break.py
#   - LOCK tests → tests/unit/parser/s8_commands/test_s8_2_12_lock.py
#   - MERGE tests → tests/unit/parser/s8_commands/test_s8_2_13_merge.py
#   - XECUTE test → tests/unit/parser/s8_commands/test_s8_2_26_xecute.py
#   - VIEW tests → tests/unit/parser/s8_commands/test_s8_2_24_view.py
#   - SET extended global tests → tests/unit/parser/s8_commands/test_s8_2_18_set.py


# TestPostconditions migrated to tests/unit/parser/s8_commands/test_s8_1_general_rules.py


# TestIndirection migrated to tests/unit/parser/s7_expressions/test_s7_3_indirection.py


# =============================================================================
# Z-Commands (YottaDB/GT.M Extensions)
# =============================================================================

# TestZShowCommand migrated to tests/unit/parser/extensions/ydb/test_zshow.py
# TestZWriteCommand migrated to tests/unit/parser/extensions/ydb/test_zwrite.py
# TestZLoadCommand migrated to tests/unit/parser/extensions/ydb/test_zlink.py
# TestDoExternalCommand migrated to tests/unit/parser/s8_commands/test_s8_2_03_do.py
# TestByRefIndirection migrated to tests/unit/parser/s8_commands/test_s8_2_03_do.py
# TestZBreakCommand migrated to tests/unit/parser/extensions/ydb/test_zbreak.py
# TestZGotoCommand migrated to tests/unit/parser/extensions/ydb/test_zgoto.py
# TestZKillCommand migrated to tests/unit/parser/extensions/ydb/test_zkill.py
# TestZWithdrawCommand migrated to tests/unit/parser/extensions/ydb/test_zkill.py
# TestZHaltCommand migrated to tests/unit/parser/extensions/ydb/test_zhalt.py
# TestZAllocateCommand migrated to tests/unit/parser/extensions/ydb/test_zallocate.py
# TestZDeallocateCommand migrated to tests/unit/parser/extensions/ydb/test_zallocate.py
# TestZLinkCommand migrated to tests/unit/parser/extensions/ydb/test_zlink.py
# TestZPrintCommand migrated to tests/unit/parser/extensions/ydb/test_zprint.py
# TestZSystemCommand migrated to tests/unit/parser/extensions/ydb/test_zsystem.py
# TestZMessageCommand migrated to tests/unit/parser/extensions/ydb/test_zmessage.py
# TestZTriggerCommand migrated to tests/unit/parser/extensions/ydb/test_ztrigger.py
# TestZCompileCommand migrated to tests/unit/parser/extensions/ydb/test_zcompile.py
# TestZContinueCommand migrated to tests/unit/parser/extensions/ydb/test_zcontinue.py


# =============================================================================
# Part O Edge Cases and Misc Tests
# =============================================================================

# TestPartOEdgeCases migrated to tests/unit/meta/test_parser_edge_cases.py
# TestUnknownCommand migrated to tests/unit/meta/test_parser_edge_cases.py
# TestFunctionArgsEmpty migrated to tests/unit/meta/test_parser_edge_cases.py


# =============================================================================
# Phase 103 Grammar Tests - New features added for 100% clean parse rate
# =============================================================================
# TestZEditCommand migrated to tests/unit/parser/extensions/ydb/test_zedit.py
# TestZStepCommand migrated to tests/unit/parser/extensions/ydb/test_zstep.py
# TestZBreakLabelOffset migrated to tests/unit/parser/extensions/ydb/test_zbreak.py
# TestZWriteArgumentless migrated to tests/unit/parser/extensions/ydb/test_zwrite.py


# =============================================================================
# Remaining tests - to be migrated
# =============================================================================

# TestTextFunctionGrammar - $TEXT function grammar tests
# → Target: tests/unit/parser/s7_expressions/test_s7_1_5_intrinsic_functions.py

# TestExternalFunction - $& external function call syntax (skipped tests)
# → Target: tests/unit/parser/s7_expressions/test_s7_1_6_extrinsic_functions.py

# TestReadTargets - READ target extensions
# → Target: tests/unit/parser/s8_commands/test_s8_2_17_read.py
