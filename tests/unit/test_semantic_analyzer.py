"""MIGRATED: Tests from this file have been reorganized.

This file was migrated as part of Phase 8 spec-aligned test organization.
Test count: 62 tests across 14 test classes.

Migration destinations:
- TestAnalyzeExpression → tests/unit/meta/test_semantic_analyzer_internals.py
- TestUnwrapExpression → tests/unit/meta/test_semantic_analyzer_internals.py
- TestPatternMatchASG → tests/unit/asg/s7_expressions/test_s7_2_5_pattern_match.py
- TestIntrinsicFunctionASG → tests/unit/asg/s7_expressions/test_s7_1_5_intrinsic_functions.py
- TestExtrinsicFunctionASG → tests/unit/asg/s7_expressions/test_s7_1_6_extrinsic_functions.py
- TestIndirectionASG → tests/unit/asg/s7_expressions/test_s7_3_indirection.py
- TestSpecialVariableASG → tests/unit/asg/s7_expressions/test_s7_1_7_special_variables.py
- TestFormatControlASG → tests/unit/asg/s8_commands/test_s8_2_25_write.py
- TestXecuteConstantDetection → tests/unit/asg/s8_commands/test_s8_2_26_xecute.py
- TestPatternMatchCompilation → tests/unit/asg/s7_expressions/test_s7_2_5_pattern_match.py
- TestIndirectionClassification → tests/unit/asg/s7_expressions/test_s7_3_indirection.py
- TestReadFixedLength → tests/unit/asg/s8_commands/test_s8_2_17_read.py
- TestMActualParameterAnalysis → tests/unit/asg/s8_commands/test_s8_2_03_do.py
- TestZGotoLabelRefAnalysis → tests/unit/asg/extensions/ydb/test_zgoto.py

Reference: specs/002-spec-unit-test-organization/tasks.md T171a-T171n
"""
