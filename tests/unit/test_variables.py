"""MIGRATED TO SPEC-ALIGNED LOCATIONS - Phase 8 (T175).

Original: test_variables.py (2005 lines, 22 classes, ~200 tests)
Migration completed: Tests relocated to spec-aligned files.

Destinations:
- TestScopeVariables → tests/unit/analysis/test_variable_analysis.py
- TestVariableInfo → tests/unit/analysis/test_variable_analysis.py
- TestExtractExpressionVariables → tests/unit/analysis/test_variable_analysis.py
- TestExtractStatementVariables → tests/unit/analysis/test_variable_analysis.py
- TestAnalyzeVariables → tests/unit/analysis/test_variable_analysis.py
- TestGetDefUseChains → tests/unit/analysis/test_variable_analysis.py
- TestComputeTransitiveInputs → tests/unit/analysis/test_variable_analysis.py
- TestFormalParameters → tests/unit/analysis/test_variable_analysis.py
- TestFunctionSignature → tests/unit/analysis/test_variable_analysis.py
- TestScopeStrategy → tests/unit/analysis/test_variable_analysis.py
- TestQuitAnalysis → tests/unit/analysis/test_variable_analysis.py
- TestParameterBinding → tests/unit/analysis/test_variable_analysis.py
- TestEdgeCases → tests/unit/analysis/test_variable_analysis.py
- TestPassingModeAnalysis → tests/unit/analysis/test_variable_analysis.py
- TestParameterBindingAdvanced → tests/unit/analysis/test_variable_analysis.py
- TestSignatureComputation → tests/unit/analysis/test_variable_analysis.py
- TestTransitivePropagation → tests/unit/analysis/test_variable_analysis.py
- TestFormalParamsShadowing → tests/unit/analysis/test_variable_analysis.py
- TestRoutineAnalysisCache → tests/unit/analysis/test_variable_analysis.py
- TestPerformance (@pytest.mark.slow) → tests/unit/analysis/test_variable_analysis.py
- TestRoutineAnalysisCacheIncremental → tests/unit/analysis/test_variable_analysis.py
- TestRoutineRequiresRuntimeEval → tests/unit/analysis/test_variable_analysis.py

File retained as migration record per spec-002 protocol.
Do NOT delete - serves as documentation of migration destinations.
"""
