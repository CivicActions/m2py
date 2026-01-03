"""Legacy test_classifier.py - All tests migrated to spec-aligned locations.

This file previously contained FOR loop and GOTO classification tests.
All tests have been migrated to spec-aligned test files as part of Phase 8
reorganization.

Migration destinations:

TestClassifyForLoop → tests/unit/analysis/test_for_classifier.py
TestExtractForFromLine → tests/unit/analysis/test_for_classifier.py
TestParseForStatement → tests/unit/asg/s8_commands/test_s8_2_05_for.py
TestQuitDetection → tests/unit/asg/s8_commands/test_s8_2_16_quit.py
TestParseSetStatement → tests/unit/asg/s8_commands/test_s8_2_18_set.py
TestParseWriteStatement → tests/unit/asg/s8_commands/test_s8_2_25_write.py
TestParseQuitStatement → tests/unit/asg/s8_commands/test_s8_2_16_quit.py
TestParseIfStatement → tests/unit/asg/s8_commands/test_s8_2_09_if.py
TestParseGotoStatement → tests/unit/asg/s8_commands/test_s8_2_06_goto.py
TestExtractGotoFromLine → tests/unit/analysis/test_goto_classifier.py
TestClassifyGotos → tests/unit/analysis/test_goto_classifier.py
TestGetLoopExitingGotos → tests/unit/analysis/test_goto_classifier.py
TestParseNewStatement → tests/unit/asg/s8_commands/test_s8_2_14_new.py
TestParseDoStatement → tests/unit/asg/s8_commands/test_s8_2_03_do.py
TestExtractDoFromLine → tests/unit/meta/test_line_parser.py
TestDetectUnreachableCode → tests/unit/asg/s6_routine/test_s6_3_execution.py

Do not add new tests to this file. Add tests to the appropriate spec-aligned
location based on the feature being tested.
"""
