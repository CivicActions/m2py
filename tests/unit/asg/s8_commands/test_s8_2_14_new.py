"""Tests for NEW command ASG analysis (§8.2.14).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.14

Migrated from: tests/unit/test_command_analysis.py::TestNewStatementAnalysis (partial)
"""

import pytest

from m2py.parser.line_parser import parse_commands_from_line
from m2py.analysis.semantic_analyzer import analyze_command
from m2py.analysis.variables import (
    analyze_variables,
    classify_scope_strategy,
    compute_all_signatures,
    FunctionSignature,
    ScopeVariables,
)
from m2py.asg.elements import (
    MRoutine,
    MLabel,
    MScope,
)
from m2py.asg.enums import ScopeStrategy
from m2py.asg.expressions import (
    MVariable,
    MBinaryOp,
)
from m2py.asg.statements import (
    MNewStatement,
    MSetStatement,
    MAssignment,
)
from m2py.parser import MUMPSParser


def analyze_first_command(line: str):
    """Helper to parse a line and analyze the first command."""
    cmds = parse_commands_from_line(line)
    assert len(cmds) >= 1, f"No commands parsed from: {line}"
    return analyze_command(cmds[0])


@pytest.mark.asg
class TestNewCommandAnalysis:
    """ASG-level tests for NEW command analysis (§8.2.14).

    Migrated from: tests/unit/test_command_analysis.py::TestNewStatementAnalysis
    """

    def test_simple_new(self):
        """N X produces MNewStatement (§8.2.14).

        Migrated from: test_command_analysis.py::TestNewStatementAnalysis::test_simple_new
        """
        stmt = analyze_first_command("N X")

        assert isinstance(stmt, MNewStatement)
        assert "X" in stmt.variables

    def test_multiple_new(self):
        """N X,Y,Z produces multiple variables (§8.2.14).

        Migrated from: test_command_analysis.py::TestNewStatementAnalysis::test_multiple_new
        """
        stmt = analyze_first_command("N X,Y,Z")

        assert isinstance(stmt, MNewStatement)
        assert len(stmt.variables) == 3


@pytest.mark.asg
class TestScopeVariables:
    """Tests for ScopeVariables dataclass (§8.2.14 NEW command).

    Migrated from tests/unit/test_variables.py::TestScopeVariables
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


@pytest.mark.asg
class TestFormalParameters:
    """Tests for formal parameter handling (§8.2.14 NEW command).

    Migrated from tests/unit/test_variables.py::TestFormalParameters
    """

    def test_formal_params_not_in_inputs(self):
        """T594: Formal params should not appear in input_variables."""
        # Create a label with formal parameters that are read
        # SET Z=X+Y  where X, Y are formal params
        var_x = MVariable(name="X", subscripts=[])
        var_y = MVariable(name="Y", subscripts=[])
        var_z = MVariable(name="Z", subscripts=[])

        add_expr = MBinaryOp(left=var_x, operator="+", right=var_y)
        assignment = MAssignment(target=var_z, value=add_expr)
        set_stmt = MSetStatement(assignments=[assignment])
        scope = MScope(statements=[set_stmt])

        # Label has formal_list ["X", "Y"]
        label = MLabel(name="CALC", formal_list=["X", "Y"], body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        result = analyze_variables(routine)

        # X and Y are formal params - they should NOT be in input_variables
        assert "X" not in result["CALC"].input_variables
        assert "Y" not in result["CALC"].input_variables
        # But X and Y should be tracked as reads
        assert "X" in result["CALC"].reads
        assert "Y" in result["CALC"].reads
        # Z is written
        assert "Z" in result["CALC"].output_variables

    def test_formal_params_in_formal_params_set(self):
        """Formal params should be in formal_params set."""
        scope = MScope(statements=[])
        label = MLabel(name="CALC", formal_list=["A", "B", "C"], body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        result = analyze_variables(routine)

        assert result["CALC"].formal_params == {"A", "B", "C"}


@pytest.mark.asg
class TestScopeStrategy:
    """Tests for scope strategy classification (§8.2.14 NEW command).

    Migrated from tests/unit/test_variables.py::TestScopeStrategy
    """

    def test_pure_function_classification(self):
        """T651: Pure function - has return, no side effects."""
        sig = FunctionSignature(
            label_name="PURE",
            formal_params=["X"],
            has_value_quit=True,
            has_void_quit=False,
            side_effect_outputs=set(),
            byref_outputs=set(),
            requires_runtime_scope=False,
        )

        strategy = classify_scope_strategy(sig)
        assert strategy == ScopeStrategy.PURE_FUNCTION

    def test_subroutine_classification(self):
        """T652: Subroutine - no return value, may have side effects."""
        sig = FunctionSignature(
            label_name="SUB",
            formal_params=[],
            has_value_quit=False,
            has_void_quit=True,
            side_effect_outputs={"X", "Y"},
            requires_runtime_scope=False,
        )

        strategy = classify_scope_strategy(sig)
        assert strategy == ScopeStrategy.SUBROUTINE

    def test_requires_runtime_classification(self):
        """T653: Runtime required - has indirection/XECUTE."""
        sig = FunctionSignature(
            label_name="DYN",
            requires_runtime_scope=True,
        )

        strategy = classify_scope_strategy(sig)
        assert strategy == ScopeStrategy.REQUIRES_RUNTIME

    def test_function_with_outputs_classification(self):
        """Function with return AND by-ref outputs."""
        sig = FunctionSignature(
            label_name="FUNC",
            has_value_quit=True,
            byref_outputs={"X"},
            requires_runtime_scope=False,
        )

        strategy = classify_scope_strategy(sig)
        assert strategy == ScopeStrategy.FUNCTION_WITH_OUTPUTS

    def test_pure_function_computed_from_source(self):
        """T6741: Pure function classification from parsed source.

        ADD(A,B)
            N R
            S R=A+B
            Q R

        A and B are only read, not written. R is NEWed and returned.
        Should classify as PURE_FUNCTION.
        """
        parser = MUMPSParser()
        source = """ADD(A,B)
 N R
 S R=A+B
 Q R
"""
        routine = parser.parse(source)
        parser.resolve_references(routine)
        signatures = compute_all_signatures(routine)

        sig = signatures["ADD"]
        assert sig.formal_params == ["A", "B"]
        assert sig.byref_outputs == set()  # A, B only read, not written
        assert sig.has_value_quit is True
        assert sig.scope_strategy == ScopeStrategy.PURE_FUNCTION

    def test_function_with_outputs_computed_from_source(self):
        """T6742: Function with outputs classification from parsed source.

        CALC(A,B)
            S A=A+B
            Q A

        A is written (potential by-ref output) and returned.
        Should classify as FUNCTION_WITH_OUTPUTS.
        """
        parser = MUMPSParser()
        source = """CALC(A,B)
 S A=A+B
 Q A
"""
        routine = parser.parse(source)
        parser.resolve_references(routine)
        signatures = compute_all_signatures(routine)

        sig = signatures["CALC"]
        assert sig.formal_params == ["A", "B"]
        assert sig.byref_outputs == {"A"}  # A is written
        assert sig.has_value_quit is True
        assert sig.scope_strategy == ScopeStrategy.FUNCTION_WITH_OUTPUTS
