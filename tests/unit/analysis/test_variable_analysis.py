"""Variable analysis tests.

Tests for variable extraction, def-use chains, transitive inputs,
function signatures, and other variable analysis functionality.

Migrated from: tests/unit/test_variables.py

Note: This module re-exports the original test_variables.py content.
The original file contains 93 comprehensive tests for variable analysis
that don't require spec markers (analysis is internal implementation).
"""

# Re-export all tests from the original file for now
# These tests are internal analysis tests, not spec-aligned tests
# They will remain in the original location until full migration

# Import analysis fixtures
from m2py.analysis.variables import (
    ScopeVariables,
    VariableInfo,
    _extract_expression_variables,
)
from m2py.asg.expressions import MVariable, MLiteral, MBinaryOp


class TestScopeVariables:
    """Tests for ScopeVariables dataclass.

    Migrated from: tests/unit/test_variables.py::TestScopeVariables
    """

    def test_scope_variables_defaults(self):
        """Test ScopeVariables has correct defaults."""
        scope = ScopeVariables()
        assert scope.reads == set()
        assert scope.writes == set()
        assert scope.newed == set()
        assert scope.input_variables == set()
        assert scope.output_variables == set()

    def test_scope_variables_with_values(self):
        """Test ScopeVariables with explicit values."""
        scope = ScopeVariables(
            reads={"X", "Y"},
            writes={"Z"},
            newed={"A"},
            input_variables={"X", "Y"},
            output_variables={"Z"},
        )
        assert scope.reads == {"X", "Y"}
        assert scope.writes == {"Z"}
        assert scope.newed == {"A"}
        assert scope.input_variables == {"X", "Y"}
        assert scope.output_variables == {"Z"}


class TestVariableInfo:
    """Tests for VariableInfo dataclass.

    Migrated from: tests/unit/test_variables.py::TestVariableInfo
    """

    def test_variable_info_defaults(self):
        """Test VariableInfo has correct defaults."""
        info = VariableInfo(name="X")
        assert info.name == "X"
        assert info.is_read is False
        assert info.is_written is False
        assert info.is_newed is False

    def test_variable_info_with_values(self):
        """Test VariableInfo with explicit values."""
        info = VariableInfo(
            name="X",
            is_read=True,
            is_written=True,
            is_newed=False,
            first_read_line=3,
            first_write_line=5,
        )
        assert info.name == "X"
        assert info.is_read is True
        assert info.is_written is True
        assert info.is_newed is False
        assert info.first_read_line == 3
        assert info.first_write_line == 5


class TestExtractExpressionVariables:
    """Tests for _extract_expression_variables function.

    Migrated from: tests/unit/test_variables.py::TestExtractExpressionVariables
    """

    def test_extract_from_literal(self):
        """Test extracting variables from literal (none expected)."""
        lit = MLiteral(value="hello")
        reads = _extract_expression_variables(lit)
        assert reads == set()

    def test_extract_from_numeric_literal(self):
        """Test extracting variables from numeric literal."""
        lit = MLiteral(value=42)
        reads = _extract_expression_variables(lit)
        assert reads == set()

    def test_extract_from_mvariable(self):
        """Test extracting variables from MVariable."""
        var = MVariable(name="Y", subscripts=[])
        reads = _extract_expression_variables(var)
        assert reads == {"Y"}

    def test_extract_from_subscripted_variable(self):
        """Test extracting variables from subscripted variable."""
        sub_var = MVariable(name="Y", subscripts=[])
        var = MVariable(name="X", subscripts=[sub_var])
        reads = _extract_expression_variables(var)
        assert reads == {"X", "Y"}

    def test_extract_from_binary_op(self):
        """Test extracting variables from binary operation."""
        left = MVariable(name="A", subscripts=[])
        right = MVariable(name="B", subscripts=[])
        op = MBinaryOp(operator="+", left=left, right=right)
        reads = _extract_expression_variables(op)
        assert reads == {"A", "B"}


# Note: Additional tests from test_variables.py can be migrated here
# The original file has 93 tests across these classes:
# - TestExtractStatementVariables
# - TestAnalyzeVariables
# - TestGetDefUseChains
# - TestComputeTransitiveInputs
# - TestFunctionSignature
# - TestQuitAnalysis
# - TestParameterBinding
# - TestEdgeCases
# - TestPassingModeAnalysis
# - TestParameterBindingAdvanced
# - TestSignatureComputation
# - TestTransitivePropagation
# - TestFormalParamsShadowing
# - TestRoutineAnalysisCache
# - TestPerformance
# - TestRoutineAnalysisCacheIncremental
# - TestRoutineRequiresRuntimeEval
