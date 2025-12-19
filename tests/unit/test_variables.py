"""Unit tests for variable analysis module."""

import pytest
from m2py.analysis.variables import (
    analyze_variables,
    get_def_use_chains,
    compute_transitive_inputs,
    ScopeVariables,
    VariableInfo,
    _extract_expression_variables,
    _extract_statement_variables,
)
from m2py.asg.elements import (
    MRoutine,
    MLabel,
    MScope,
    MCall,
)
from m2py.asg.statements import (
    MSetStatement,
    MWriteStatement,
    MNewStatement,
    MIfStatement,
    MForStatement,
    MQuitStatement,
    MDoStatement,
    MAssignment,
)
from m2py.asg.expressions import (
    MVariable,
    MLiteral,
    MBinaryOp,
    MExpr,
)


class TestScopeVariables:
    """Tests for ScopeVariables dataclass."""

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
    """Tests for VariableInfo dataclass."""

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
    """Tests for _extract_expression_variables function."""

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
        # X(Y) - both X and Y should be read
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


class TestExtractStatementVariables:
    """Tests for _extract_statement_variables function."""

    def test_extract_from_set_statement(self):
        """Test extracting variables from SET statement."""
        # S X=Y+Z
        target = MVariable(name="X", subscripts=[])
        left = MVariable(name="Y", subscripts=[])
        right = MVariable(name="Z", subscripts=[])
        value = MBinaryOp(operator="+", left=left, right=right)
        assignment = MAssignment(target=target, value=value)
        stmt = MSetStatement(assignments=[assignment])
        
        reads, writes, newed = _extract_statement_variables(stmt)
        assert writes == {"X"}
        assert reads == {"Y", "Z"}
        assert newed == set()

    def test_extract_from_write_statement(self):
        """Test extracting variables from WRITE statement."""
        var = MVariable(name="X", subscripts=[])
        stmt = MWriteStatement(arguments=[var])
        
        reads, writes, newed = _extract_statement_variables(stmt)
        assert reads == {"X"}
        assert writes == set()
        assert newed == set()

    def test_extract_from_new_statement(self):
        """Test extracting variables from NEW statement."""
        stmt = MNewStatement(variables=["A", "B", "C"])
        
        reads, writes, newed = _extract_statement_variables(stmt)
        assert reads == set()
        assert writes == set()
        assert newed == {"A", "B", "C"}

    def test_extract_from_if_statement(self):
        """Test extracting variables from IF statement condition."""
        cond = MVariable(name="X", subscripts=[])
        stmt = MIfStatement(condition=cond, then_scope=None)
        
        reads, writes, newed = _extract_statement_variables(stmt)
        assert reads == {"X"}
        assert writes == set()
        assert newed == set()

    def test_extract_from_for_statement(self):
        """Test extracting variables from FOR statement."""
        stmt = MForStatement(
            loop_var="I",
            parameters=[],
            body=None,
        )
        
        reads, writes, newed = _extract_statement_variables(stmt)
        # FOR writes the loop variable
        assert writes == {"I"}
        assert newed == set()

    def test_extract_from_quit_with_value(self):
        """Test extracting variables from QUIT with return value."""
        value = MVariable(name="RESULT", subscripts=[])
        stmt = MQuitStatement(return_value=value)
        
        reads, writes, newed = _extract_statement_variables(stmt)
        assert reads == {"RESULT"}
        assert writes == set()
        assert newed == set()


class TestAnalyzeVariables:
    """Tests for analyze_variables function."""

    def test_analyze_empty_routine(self):
        """Test analyzing routine with no labels."""
        routine = MRoutine(name="EMPTY", labels=[])
        result = analyze_variables(routine)
        assert result == {}

    def test_analyze_simple_label(self):
        """Test analyzing label with simple SET."""
        # Label with: S X=1
        target = MVariable(name="X", subscripts=[])
        value = MLiteral(value=1)
        assignment = MAssignment(target=target, value=value)
        stmt = MSetStatement(assignments=[assignment])
        scope = MScope(statements=[stmt])
        label = MLabel(name="TEST", body=scope)
        routine = MRoutine(name="TEST", labels=[label])
        
        result = analyze_variables(routine)
        assert "TEST" in result
        scope_vars = result["TEST"]
        assert "X" in scope_vars.writes
        assert scope_vars.reads == set()

    def test_analyze_read_write_pattern(self):
        """Test analyzing label with read then write."""
        # S Y=X, S X=1
        # First: Y = X (reads X, writes Y)
        target1 = MVariable(name="Y", subscripts=[])
        value1 = MVariable(name="X", subscripts=[])
        assign1 = MAssignment(target=target1, value=value1)
        stmt1 = MSetStatement(assignments=[assign1])
        
        # Second: X = 1 (writes X)
        target2 = MVariable(name="X", subscripts=[])
        value2 = MLiteral(value=1)
        assign2 = MAssignment(target=target2, value=value2)
        stmt2 = MSetStatement(assignments=[assign2])
        
        scope = MScope(statements=[stmt1, stmt2])
        label = MLabel(name="TEST", body=scope)
        routine = MRoutine(name="TEST", labels=[label])
        
        result = analyze_variables(routine)
        scope_vars = result["TEST"]
        assert scope_vars.reads == {"X"}  # X read before written
        assert scope_vars.writes == {"X", "Y"}
        assert "X" in scope_vars.input_variables  # X is an input

    def test_analyze_with_new(self):
        """Test analyzing label with NEW statement."""
        # N X S X=1
        new_stmt = MNewStatement(variables=["X"])
        target = MVariable(name="X", subscripts=[])
        value = MLiteral(value=1)
        assignment = MAssignment(target=target, value=value)
        set_stmt = MSetStatement(assignments=[assignment])
        
        scope = MScope(statements=[new_stmt, set_stmt])
        label = MLabel(name="TEST", body=scope)
        routine = MRoutine(name="TEST", labels=[label])
        
        result = analyze_variables(routine)
        scope_vars = result["TEST"]
        assert scope_vars.newed == {"X"}
        assert scope_vars.writes == {"X"}
        # X should NOT be an input since it's NEWed before use
        assert "X" not in scope_vars.input_variables


class TestGetDefUseChains:
    """Tests for get_def_use_chains function."""

    def test_def_use_simple(self):
        """Test simple def-use chain."""
        # S X=1 W X
        target = MVariable(name="X", subscripts=[])
        value = MLiteral(value=1)
        assignment = MAssignment(target=target, value=value)
        set_stmt = MSetStatement(assignments=[assignment])
        set_stmt.line_number = 1
        
        write_var = MVariable(name="X", subscripts=[])
        write_stmt = MWriteStatement(arguments=[write_var])
        write_stmt.line_number = 2
        
        scope = MScope(statements=[set_stmt, write_stmt])
        label = MLabel(name="TEST", body=scope)
        
        chains = get_def_use_chains(label)
        assert "X" in chains

    def test_def_use_multiple_defs(self):
        """Test variable with multiple definitions."""
        # S X=1 S X=2
        target1 = MVariable(name="X", subscripts=[])
        value1 = MLiteral(value=1)
        assign1 = MAssignment(target=target1, value=value1)
        stmt1 = MSetStatement(assignments=[assign1])
        stmt1.line_number = 1
        
        target2 = MVariable(name="X", subscripts=[])
        value2 = MLiteral(value=2)
        assign2 = MAssignment(target=target2, value=value2)
        stmt2 = MSetStatement(assignments=[assign2])
        stmt2.line_number = 2
        
        scope = MScope(statements=[stmt1, stmt2])
        label = MLabel(name="TEST", body=scope)
        
        chains = get_def_use_chains(label)
        assert "X" in chains


class TestComputeTransitiveInputs:
    """Tests for compute_transitive_inputs function."""

    def test_no_calls(self):
        """Test routine with no internal calls."""
        label_vars = {
            "A": ScopeVariables(
                reads={"X"},
                writes={"Y"},
                input_variables={"X"},
                output_variables={"Y"},
            ),
        }
        label = MLabel(name="A", body=MScope())
        routine = MRoutine(name="TEST", labels=[label])
        
        result = compute_transitive_inputs(routine, label_vars)
        # Returns Dict[str, Set[str]] of transitive input variables
        assert result["A"] == {"X"}

    def test_simple_call_chain(self):
        """Test simple A->B call chain."""
        # A calls B, B reads X
        label_vars = {
            "A": ScopeVariables(
                reads=set(),
                writes={"Y"},
                input_variables=set(),
                output_variables={"Y"},
            ),
            "B": ScopeVariables(
                reads={"X"},
                writes=set(),
                input_variables={"X"},
                output_variables=set(),
            ),
        }
        
        # Create routine with call from A to B
        call_b = MCall(name="B", routine=None, arguments=[])
        do_stmt = MDoStatement(targets=[call_b])
        scope_a = MScope(statements=[do_stmt])
        label_a = MLabel(name="A", body=scope_a)
        label_b = MLabel(name="B", body=MScope())
        routine = MRoutine(name="TEST", labels=[label_a, label_b])
        
        result = compute_transitive_inputs(routine, label_vars)
        # A should now have X as transitive input from B
        assert "X" in result["A"]
