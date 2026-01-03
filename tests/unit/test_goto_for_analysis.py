"""MIGRATED TO SPEC-ALIGNED LOCATIONS - Phase 8 (T173).

Original: test_goto_for_analysis.py (1262 lines, 8 classes, 47 tests)
Migration completed: Tests relocated to spec-aligned files.

Destinations:
- TestClassifyGotos (14 tests) → tests/unit/analysis/test_goto_classifier.py
- TestHasUnstructuredGoto (6 tests) → tests/unit/analysis/test_goto_classifier.py
- TestForLoopIsInfinite (4 tests) → tests/unit/analysis/test_for_analysis.py
- TestAnalyzeForLoops (4 tests) → tests/unit/analysis/test_for_analysis.py
- TestIntegrationWithParser (2 tests) → tests/unit/analysis/test_for_analysis.py
- TestForAnalysisNestedScopes (8 tests) → tests/unit/analysis/test_for_analysis.py
- TestLoopVarModificationEnhanced (9 tests) → tests/unit/analysis/test_for_analysis.py
- TestSignatureAwareByRefDetection (4 tests) → tests/unit/analysis/test_for_analysis.py

File retained as migration record per spec-002 protocol.
Do NOT delete - serves as documentation of migration destinations.
"""
