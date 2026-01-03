"""Legacy test_parser.py - All tests migrated to spec-aligned locations.

This file previously contained MUMPSParser class tests. All tests have been
migrated to spec-aligned test files as part of Phase 8 reorganization.

Migration destinations:

TestMUMPSParserInit → tests/unit/meta/test_parser_api.py
TestMUMPSParserParse → tests/unit/meta/test_parser_api.py
TestMUMPSParserParseFile → tests/unit/meta/test_parser_api.py
TestMUMPSParserMUGJ → tests/unit/meta/test_parser_api.py
TestMUMPSParserGrammarIntegration → tests/unit/meta/test_parser_api.py
TestMUMPSParserClassifyPatterns → tests/unit/analysis/test_for_classifier.py
TestParserPerformance → tests/unit/meta/test_parser_performance.py
TestParserErrorHandling → tests/unit/meta/test_parser_errors.py
TestParseErrorCollection → tests/unit/meta/test_parser_errors.py
TestTransactionCommands → tests/unit/parser/s8_commands/test_s8_2_19_tcommit.py
                          tests/unit/parser/s8_commands/test_s8_2_20_trestart.py
                          tests/unit/parser/s8_commands/test_s8_2_21_trollback.py
                          tests/unit/parser/s8_commands/test_s8_2_22_tstart.py
TestASGSerialization → tests/unit/meta/test_asg_serialization.py
TestControlFlowBodyPopulation → tests/unit/asg/s8_commands/test_s8_2_05_for.py
                                tests/unit/asg/s8_commands/test_s8_2_09_if.py
                                tests/unit/asg/s8_commands/test_s8_2_03_do.py
TestPhase74Fixes → tests/unit/meta/test_regression_fixes.py

Do not add new tests to this file. Add tests to the appropriate spec-aligned
location based on the feature being tested.
"""
