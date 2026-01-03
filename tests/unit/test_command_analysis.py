"""MIGRATED TO SPEC-ALIGNED LOCATIONS - Phase 8 (T172).

Original: test_command_analysis.py (602 lines, 12 classes, ~50 tests)
Migration completed: Tests relocated to spec-aligned files.

Destinations:
- TestSetStatementAnalysis (16 tests) → tests/unit/asg/s8_commands/test_s8_2_18_set.py
- TestWriteStatementAnalysis (3 tests) → tests/unit/asg/s8_commands/test_s8_2_25_write.py
- TestQuitStatementAnalysis (3 tests) → tests/unit/asg/s8_commands/test_s8_2_16_quit.py
- TestIfStatementAnalysis (2 tests) → tests/unit/asg/s8_commands/test_s8_2_09_if.py
- TestForStatementAnalysis (4 tests) → tests/unit/asg/s8_commands/test_s8_2_05_for.py
- TestGotoStatementAnalysis (3 tests) → tests/unit/asg/s8_commands/test_s8_2_06_goto.py
- TestDoStatementAnalysis (2 tests) → tests/unit/asg/s8_commands/test_s8_2_03_do.py
- TestNewStatementAnalysis (2 tests) → tests/unit/asg/s8_commands/test_s8_2_14_new.py
- TestKillStatementAnalysis (4 tests) → tests/unit/asg/s8_commands/test_s8_2_11_kill.py
- TestOtherStatementAnalysis (8 tests) → split by command:
  - HANG → tests/unit/asg/s8_commands/test_s8_2_08_hang.py
  - HALT → tests/unit/asg/s8_commands/test_s8_2_07_halt.py
  - BREAK → tests/unit/asg/s8_commands/test_s8_2_01_break.py
  - ZALLOCATE/ZDEALLOCATE → tests/unit/asg/extensions/ydb/test_zallocate.py
- TestMultipleCommandsAnalysis (1 test) → tests/unit/meta/test_command_analysis_integration.py
- TestExpressionAnalysis (5 tests) → tests/unit/asg/s7_expressions/test_s7_2_operators.py

File retained as migration record per spec-002 protocol.
Do NOT delete - serves as documentation of migration destinations.
"""
