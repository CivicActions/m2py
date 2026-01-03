"""MIGRATED TO SPEC-ALIGNED LOCATIONS - Phase 8.

Original: test_line_parser.py (549 lines, 16 classes)
Migration completed: Tests relocated to spec-aligned files.

Destinations:
- TestParseLineContent → tests/unit/meta/test_line_parser.py
- TestParseCommandsFromLine → tests/unit/meta/test_line_parser.py
- TestGetLineComment → tests/unit/meta/test_line_parser.py
- TestParseCommand → tests/unit/meta/test_line_parser.py
- TestParseExpression → tests/unit/meta/test_line_parser.py
- TestParseSetCommand → tests/unit/asg/s8_commands/test_s8_2_18_set.py
- TestParseWriteCommand → tests/unit/asg/s8_commands/test_s8_2_25_write.py
- TestParseQuitCommand → tests/unit/asg/s8_commands/test_s8_2_16_quit.py
- TestParseIfCommand → tests/unit/asg/s8_commands/test_s8_2_09_if.py
- TestArgumentlessIfFollowedByCommand → tests/unit/asg/s8_commands/test_s8_2_09_if.py
- TestParseForCommand → tests/unit/asg/s8_commands/test_s8_2_05_for.py
- TestExtractForCommands → tests/unit/analysis/test_for_classifier.py
- TestClassifyForFromTextx → tests/unit/analysis/test_for_classifier.py
- TestParseForCommandToAsg → tests/unit/asg/s8_commands/test_s8_2_05_for.py
- TestDetectQuitAfterFor → tests/unit/analysis/test_for_analysis.py
- TestExtractFunctionErrorPaths → tests/unit/meta/test_line_parser.py

File retained as migration record per spec-002 protocol.
Do NOT delete - serves as documentation of migration destinations.
"""
