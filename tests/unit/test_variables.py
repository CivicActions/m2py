"""Unit tests for variable analysis module."""

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

    def test_extract_from_select_arg(self):
        """Test extracting variables from MSelectArg (condition:value pair).

        MSelectArg represents a single condition:value pair in $SELECT,
        e.g., A=1:X in $SELECT(A=1:X,1:Y)
        """
        from m2py.asg.expressions import MSelectArg

        # Simple case: A=1:X -> reads A and X
        condition = MVariable(name="A", subscripts=[])
        value = MVariable(name="X", subscripts=[])
        select_arg = MSelectArg(condition=condition, value=value)
        reads = _extract_expression_variables(select_arg)
        assert reads == {"A", "X"}

    def test_extract_from_select_arg_with_complex_expressions(self):
        """Test extracting variables from MSelectArg with binary ops."""
        from m2py.asg.expressions import MSelectArg

        # A+B=1:X+Y -> reads A, B, X, Y
        cond_left = MVariable(name="A", subscripts=[])
        cond_right = MVariable(name="B", subscripts=[])
        condition = MBinaryOp(operator="+", left=cond_left, right=cond_right)

        val_left = MVariable(name="X", subscripts=[])
        val_right = MVariable(name="Y", subscripts=[])
        value = MBinaryOp(operator="+", left=val_left, right=val_right)

        select_arg = MSelectArg(condition=condition, value=value)
        reads = _extract_expression_variables(select_arg)
        assert reads == {"A", "B", "X", "Y"}

    def test_extract_from_select_arg_with_literals(self):
        """Test extracting variables from MSelectArg with literal condition."""
        from m2py.asg.expressions import MSelectArg

        # 1:Z (final fallback case in $SELECT) -> only reads Z
        condition = MLiteral(value=1)
        value = MVariable(name="Z", subscripts=[])
        select_arg = MSelectArg(condition=condition, value=value)
        reads = _extract_expression_variables(select_arg)
        assert reads == {"Z"}


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
        stmt = MIfStatement(conditions=[cond], condition=cond, then_scope=None)

        reads, writes, newed = _extract_statement_variables(stmt)
        assert reads == {"X"}
        assert writes == set()
        assert newed == set()

    def test_extract_from_if_statement_multi_condition(self):
        """Test extracting variables from multi-condition IF statement (I A,B)."""
        cond_a = MVariable(name="A", subscripts=[])
        cond_b = MVariable(name="B", subscripts=[])
        stmt = MIfStatement(conditions=[cond_a, cond_b], then_scope=None)

        reads, writes, newed = _extract_statement_variables(stmt)
        assert reads == {"A", "B"}
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


# =============================================================================
# Phase 58 Tests: Enhanced Variable Scoping
# =============================================================================


class TestFormalParameters:
    """Tests for formal parameter handling (Phase 58a)."""

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


class TestFunctionSignature:
    """Tests for FunctionSignature computation (Phase 58e)."""

    def test_signature_dataclass(self):
        """Test FunctionSignature has correct fields."""
        from m2py.analysis.variables import FunctionSignature
        from m2py.asg.enums import ScopeStrategy

        sig = FunctionSignature(
            label_name="CALC",
            formal_params=["X", "Y"],
            required_inputs={"Z"},
            has_value_quit=True,
        )

        assert sig.label_name == "CALC"
        assert sig.formal_params == ["X", "Y"]
        assert sig.required_inputs == {"Z"}
        assert sig.has_value_quit is True
        assert sig.scope_strategy == ScopeStrategy.SUBROUTINE  # default

    def test_compute_function_signature(self):
        """T624: Test signature computation for simple label."""
        from m2py.analysis.variables import compute_function_signature

        # Create CALC(X,Y) S Z=X+Y Q Z
        var_x = MVariable(name="X", subscripts=[])
        var_y = MVariable(name="Y", subscripts=[])
        var_z = MVariable(name="Z", subscripts=[])

        add_expr = MBinaryOp(left=var_x, operator="+", right=var_y)
        assignment = MAssignment(target=var_z, value=add_expr)
        set_stmt = MSetStatement(assignments=[assignment])
        quit_stmt = MQuitStatement(return_value=var_z)

        scope = MScope(statements=[set_stmt, quit_stmt])
        label = MLabel(name="CALC", formal_list=["X", "Y"], body=scope)

        # First analyze variables
        routine = MRoutine(name="TEST", labels=[label])
        label_vars = analyze_variables(routine)

        # Now compute signature
        sig = compute_function_signature(label, label_vars["CALC"])

        assert sig.label_name == "CALC"
        assert sig.formal_params == ["X", "Y"]
        assert sig.has_value_quit is True
        # Z is written but not in formal_params, so it's a side effect output
        assert "Z" in sig.side_effect_outputs

    def test_byref_outputs_formal_param_written(self):
        """T6702: Formal params that are written appear in byref_outputs.

        SWAP(X,Y)
            N T
            S T=X,X=Y,Y=T
            Q

        Both X and Y are written, so byref_outputs should be {"X", "Y"}.
        """
        from m2py.analysis.variables import compute_function_signature

        # Create SWAP(X,Y) N T S T=X,X=Y,Y=T Q
        var_x = MVariable(name="X", subscripts=[])
        var_y = MVariable(name="Y", subscripts=[])
        var_t = MVariable(name="T", subscripts=[])

        new_stmt = MNewStatement(variables=["T"])
        # S T=X
        assign1 = MAssignment(target=var_t, value=var_x)
        # S X=Y
        assign2 = MAssignment(target=var_x, value=var_y)
        # S Y=T
        assign3 = MAssignment(target=var_y, value=var_t)
        set_stmt = MSetStatement(assignments=[assign1, assign2, assign3])
        quit_stmt = MQuitStatement()

        scope = MScope(statements=[new_stmt, set_stmt, quit_stmt])
        label = MLabel(name="SWAP", formal_list=["X", "Y"], body=scope)

        routine = MRoutine(name="TEST", labels=[label])
        label_vars = analyze_variables(routine)
        sig = compute_function_signature(label, label_vars["SWAP"])

        assert sig.label_name == "SWAP"
        assert sig.formal_params == ["X", "Y"]
        assert sig.byref_outputs == {"X", "Y"}

    def test_byref_outputs_formal_param_read_only(self):
        """T6703: Formal params that are only read are NOT in byref_outputs.

        ADD(A,B)
            N R
            S R=A+B
            Q R

        A and B are only read, not written. byref_outputs should be empty.
        """
        from m2py.analysis.variables import compute_function_signature

        var_a = MVariable(name="A", subscripts=[])
        var_b = MVariable(name="B", subscripts=[])
        var_r = MVariable(name="R", subscripts=[])

        new_stmt = MNewStatement(variables=["R"])
        add_expr = MBinaryOp(left=var_a, operator="+", right=var_b)
        assign = MAssignment(target=var_r, value=add_expr)
        set_stmt = MSetStatement(assignments=[assign])
        quit_stmt = MQuitStatement(return_value=var_r)

        scope = MScope(statements=[new_stmt, set_stmt, quit_stmt])
        label = MLabel(name="ADD", formal_list=["A", "B"], body=scope)

        routine = MRoutine(name="TEST", labels=[label])
        label_vars = analyze_variables(routine)
        sig = compute_function_signature(label, label_vars["ADD"])

        assert sig.label_name == "ADD"
        assert sig.formal_params == ["A", "B"]
        assert sig.byref_outputs == set()  # No formal params are written
        assert sig.has_value_quit is True

    def test_byref_outputs_formal_param_conditionally_written(self):
        """T6704: Formal param conditionally written still appears in byref_outputs.

        MAYBE(X)
            I X<0 S X=0
            Q

        X is conditionally written. Conservative analysis marks it as byref output.
        """
        from m2py.analysis.variables import compute_function_signature
        from m2py.asg.enums import LiteralType

        var_x = MVariable(name="X", subscripts=[])
        lit_0 = MLiteral(value=0, literal_type=LiteralType.INTEGER)

        # I X<0 S X=0
        cond = MBinaryOp(left=var_x, operator="<", right=lit_0)
        assign = MAssignment(target=var_x, value=lit_0)
        set_stmt = MSetStatement(assignments=[assign])
        then_scope = MScope(statements=[set_stmt])
        if_stmt = MIfStatement(conditions=[cond], then_scope=then_scope)

        quit_stmt = MQuitStatement()

        scope = MScope(statements=[if_stmt, quit_stmt])
        label = MLabel(name="MAYBE", formal_list=["X"], body=scope)

        routine = MRoutine(name="TEST", labels=[label])
        label_vars = analyze_variables(routine)
        sig = compute_function_signature(label, label_vars["MAYBE"])

        assert sig.label_name == "MAYBE"
        assert sig.formal_params == ["X"]
        # Conservatively, X is in byref_outputs because it's written in some path
        assert sig.byref_outputs == {"X"}


class TestScopeStrategy:
    """Tests for scope strategy classification (Phase 58i)."""

    def test_pure_function_classification(self):
        """T651: Pure function - has return, no side effects."""
        from m2py.analysis.variables import classify_scope_strategy, FunctionSignature
        from m2py.asg.enums import ScopeStrategy

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
        from m2py.analysis.variables import classify_scope_strategy, FunctionSignature
        from m2py.asg.enums import ScopeStrategy

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
        from m2py.analysis.variables import classify_scope_strategy, FunctionSignature
        from m2py.asg.enums import ScopeStrategy

        sig = FunctionSignature(
            label_name="DYN",
            requires_runtime_scope=True,
        )

        strategy = classify_scope_strategy(sig)
        assert strategy == ScopeStrategy.REQUIRES_RUNTIME

    def test_function_with_outputs_classification(self):
        """Function with return AND by-ref outputs."""
        from m2py.analysis.variables import classify_scope_strategy, FunctionSignature
        from m2py.asg.enums import ScopeStrategy

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
        from m2py.parser import MUMPSParser
        from m2py.analysis.variables import compute_all_signatures
        from m2py.asg.enums import ScopeStrategy

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
        from m2py.parser import MUMPSParser
        from m2py.analysis.variables import compute_all_signatures
        from m2py.asg.enums import ScopeStrategy

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


class TestQuitAnalysis:
    """Tests for QUIT value analysis (Phase 58f)."""

    def test_quit_with_value_detected(self):
        """T632: QUIT with value is detected."""
        from m2py.analysis.variables import analyze_quit_statements

        # Q X+Y
        var_x = MVariable(name="X", subscripts=[])
        var_y = MVariable(name="Y", subscripts=[])
        expr = MBinaryOp(left=var_x, operator="+", right=var_y)
        quit_stmt = MQuitStatement(return_value=expr)

        scope = MScope(statements=[quit_stmt])
        label = MLabel(name="TEST", body=scope)

        has_value, has_void, return_expr = analyze_quit_statements(label)

        assert has_value is True
        assert has_void is False
        assert return_expr is not None

    def test_quit_without_value_detected(self):
        """QUIT without value is detected."""
        from m2py.analysis.variables import analyze_quit_statements

        quit_stmt = MQuitStatement(return_value=None)
        scope = MScope(statements=[quit_stmt])
        label = MLabel(name="TEST", body=scope)

        has_value, has_void, return_expr = analyze_quit_statements(label)

        assert has_value is False
        assert has_void is True
        assert return_expr is None

    def test_mixed_quits_detected(self):
        """T633: Mixed QUIT with and without value."""
        from m2py.analysis.variables import analyze_quit_statements

        var_x = MVariable(name="X", subscripts=[])
        quit_with_value = MQuitStatement(return_value=var_x)
        quit_without = MQuitStatement(return_value=None)

        scope = MScope(statements=[quit_with_value, quit_without])
        label = MLabel(name="TEST", body=scope)

        has_value, has_void, return_expr = analyze_quit_statements(label)

        assert has_value is True
        assert has_void is True


class TestParameterBinding:
    """Tests for parameter binding (Phase 58c)."""

    def test_parameter_binding_dataclass(self):
        """Test ParameterBinding has correct fields."""
        from m2py.analysis.variables import ParameterBinding
        from m2py.asg.enums import PassingMode

        binding = ParameterBinding(
            formal_name="X",
            actual_expr=MLiteral(value=42),
            passing_mode=PassingMode.BY_VALUE,
        )

        assert binding.formal_name == "X"
        assert binding.passing_mode == PassingMode.BY_VALUE
        assert binding.caller_var_name is None

    def test_byref_binding(self):
        """Test call-by-reference binding tracks caller variable."""
        from m2py.analysis.variables import ParameterBinding
        from m2py.asg.enums import PassingMode

        var_a = MVariable(name="A", subscripts=[])
        binding = ParameterBinding(
            formal_name="X",
            actual_expr=var_a,
            passing_mode=PassingMode.BY_REFERENCE,
            caller_var_name="A",
        )

        assert binding.formal_name == "X"
        assert binding.passing_mode == PassingMode.BY_REFERENCE
        assert binding.caller_var_name == "A"


class TestEdgeCases:
    """Tests for edge cases (Phase 58j)."""

    def test_global_variable_excluded(self):
        """T660: Global ^VAR excluded from local variable analysis."""
        # The extraction returns global names with ^, but they should be excluded
        # from input_variables/output_variables (the high-level analysis)
        var_x = MVariable(name="X", subscripts=[])  # local
        global_var = MVariable(name="^G", subscripts=[])  # global

        # Check expression extraction
        result = _extract_expression_variables(var_x)
        assert "X" in result

        # Globals are excluded from expression extraction (the check is in there)
        result = _extract_expression_variables(global_var)
        assert "^G" not in result

    def test_subscripted_variable_tracks_both(self):
        """T662: Subscripted X(I) tracks both X and I."""
        # X(I) - subscripted variable
        subscript = MVariable(name="I", subscripts=[])
        var_x = MVariable(name="X", subscripts=[subscript])

        result = _extract_expression_variables(var_x)

        assert "X" in result
        assert "I" in result

    def test_new_creates_scope_boundary(self):
        """NEW command creates scope boundary."""
        from m2py.asg.statements import MNewStatement

        # NEW A (uses variables list, not targets)
        new_stmt = MNewStatement(variables=["A"])

        reads, writes, news = _extract_statement_variables(new_stmt)

        assert "A" in news
        assert "A" not in reads
        assert "A" not in writes

    def test_special_variables_excluded(self):
        """T661: Special variables ($HOROLOG etc) excluded from local analysis."""
        from m2py.asg.expressions import MSpecialVariable

        # $HOROLOG is a special variable
        special = MSpecialVariable(name="HOROLOG")
        result = _extract_expression_variables(special)
        assert result == set()

        # Variables starting with $ are excluded
        var_with_dollar = MVariable(name="$X", subscripts=[])
        result = _extract_expression_variables(var_with_dollar)
        assert "$X" not in result

    def test_exclusive_new_not_enumerable(self):
        """T654: NEW (X) exclusive - can't enumerate all variables statically."""
        from m2py.asg.statements import MNewStatement

        # NEW (X) means NEW all EXCEPT X
        # Statically we can only know the exceptions, not what gets newed.
        # The current implementation doesn't add to news for exclusive NEW
        # since we can't enumerate all variables that exist at runtime.
        exclusive_new = MNewStatement(variables=["X"], exclusive=True)

        reads, writes, news = _extract_statement_variables(exclusive_new)

        # For exclusive NEW, we can't enumerate what gets newed
        # In the current implementation, variables list (the exceptions) may
        # still be present, but the key insight is that X is NOT newed.
        # This is a limitation of static analysis.
        # The test validates we at least don't crash and reads/writes are empty.
        assert reads == set()
        assert writes == set()

    def test_argumentless_do_block_scope(self):
        """T655: Argumentless DO creates block scope for indented code."""
        # D  (argumentless DO) - body is separate scope
        # This test verifies we handle empty targets gracefully
        do_stmt = MDoStatement(targets=[])

        reads, writes, news = _extract_statement_variables(do_stmt)

        # No variables in argumentless DO
        assert reads == set()
        assert writes == set()
        assert news == set()

    def test_kill_affects_variables(self):
        """T656: KILL effects on variable visibility."""
        from m2py.asg.statements import MKillStatement

        # KILL X,Y - makes variables undefined
        kill_target_x = MVariable(name="X", subscripts=[])
        kill_target_y = MVariable(name="Y", subscripts=[])
        kill_stmt = MKillStatement(targets=[kill_target_x, kill_target_y])

        reads, writes, news = _extract_statement_variables(kill_stmt)

        # KILL writes (sets to undefined) the variables
        assert "X" in writes
        assert "Y" in writes
        assert reads == set()

    def test_nested_new_different_levels(self):
        """T657: Nested NEW at different scope levels."""
        # If we NEW A at outer scope, then NEW B in inner scope,
        # both A and B are local to their respective scopes
        new_outer = MNewStatement(variables=["A"])
        new_inner = MNewStatement(variables=["B"])

        reads1, writes1, news1 = _extract_statement_variables(new_outer)
        reads2, writes2, news2 = _extract_statement_variables(new_inner)

        assert "A" in news1
        assert "B" in news2
        assert "A" not in news2
        assert "B" not in news1

    def test_variable_used_before_and_after_new(self):
        """T658: Variable used before and after NEW.

        S Y=X N X S X=1 - In true MUMPS semantics, first X read comes from
        caller scope (input), then NEW creates local X, then S X=1 writes local.

        Current static analysis limitation: We track that X was read and X was
        newed, but the conservative approach excludes X from input_variables
        because we can't easily distinguish the timeline. This is a known
        limitation - the analysis errs on the side of caution.
        """
        var_y = MVariable(name="Y", subscripts=[])
        var_x1 = MVariable(name="X", subscripts=[])
        assign1 = MAssignment(target=var_y, value=var_x1)
        set1 = MSetStatement(assignments=[assign1])

        new_stmt = MNewStatement(variables=["X"])

        var_x2 = MVariable(name="X", subscripts=[])
        assign2 = MAssignment(target=var_x2, value=MLiteral(value=1))
        set2 = MSetStatement(assignments=[assign2])

        scope = MScope(statements=[set1, new_stmt, set2])
        label = MLabel(name="TEST", body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        result = analyze_variables(routine)

        # X is read (before NEW semantically, but we track reads regardless)
        assert "X" in result["TEST"].reads
        # X is also NEWed
        assert "X" in result["TEST"].newed
        # Y is written and not NEWed - it's an output
        assert "Y" in result["TEST"].output_variables
        # Note: Due to static analysis limitation, X may or may not be in
        # input_variables depending on order tracking. We verify reads/newed.
        # The conservative approach excludes NEWed vars from inputs.

    def test_same_variable_name_multiple_labels(self):
        """T659: Same variable name in multiple labels - no conflict."""
        # Two labels both use X - they're independent
        var_x1 = MVariable(name="X", subscripts=[])
        assign1 = MAssignment(target=var_x1, value=MLiteral(value=1))
        set1 = MSetStatement(assignments=[assign1])
        scope1 = MScope(statements=[set1])
        label1 = MLabel(name="LABEL1", body=scope1)

        var_x2 = MVariable(name="X", subscripts=[])
        var_y = MVariable(name="Y", subscripts=[])
        assign2 = MAssignment(target=var_y, value=var_x2)
        set2 = MSetStatement(assignments=[assign2])
        scope2 = MScope(statements=[set2])
        label2 = MLabel(name="LABEL2", body=scope2)

        routine = MRoutine(name="TEST", labels=[label1, label2])

        result = analyze_variables(routine)

        # Each label has its own analysis
        assert "X" in result["LABEL1"].writes
        assert "X" in result["LABEL2"].reads
        # LABEL1 doesn't read X, LABEL2 doesn't write X
        assert "X" not in result["LABEL1"].input_variables
        assert "X" in result["LABEL2"].input_variables


class TestPassingModeAnalysis:
    """Tests for call-by-reference analysis (Phase 58b)."""

    def test_byvalue_argument(self):
        """T602: BY_VALUE for expression arguments."""
        from m2py.asg.expressions import MActualParameter
        from m2py.asg.enums import PassingMode

        # D CALC(X+1) - X+1 is by value
        var_x = MVariable(name="X", subscripts=[])
        expr = MBinaryOp(left=var_x, operator="+", right=MLiteral(value=1))
        param = MActualParameter(
            passing_mode=PassingMode.BY_VALUE, expression=expr, variable_name=None
        )

        assert param.passing_mode == PassingMode.BY_VALUE
        assert not param.is_byref
        assert not param.is_omitted

    def test_byref_argument(self):
        """T601: BY_REFERENCE for .variable arguments."""
        from m2py.asg.expressions import MActualParameter
        from m2py.asg.enums import PassingMode

        # D CALC(.X) - .X is by reference
        var_x = MVariable(name="X", subscripts=[])
        param = MActualParameter(
            passing_mode=PassingMode.BY_REFERENCE, expression=var_x, variable_name="X"
        )

        assert param.passing_mode == PassingMode.BY_REFERENCE
        assert param.is_byref
        # variable_name holds the caller's variable name for BY_REFERENCE
        assert param.variable_name == "X"
        assert not param.is_omitted

    def test_omitted_argument(self):
        """T603: OMITTED for empty argument position."""
        from m2py.asg.expressions import MActualParameter
        from m2py.asg.enums import PassingMode

        # D CALC(,Y) - first arg is omitted
        param = MActualParameter(
            passing_mode=PassingMode.OMITTED, expression=None, variable_name=None
        )

        assert param.passing_mode == PassingMode.OMITTED
        assert param.is_omitted
        assert not param.is_byref


class TestParameterBindingAdvanced:
    """Advanced tests for parameter binding (Phase 58c-d)."""

    def test_bind_parameters_value(self):
        """T610: D CALC(A,B) calling CALC(X,Y) - bindings X←A, Y←B."""
        from m2py.analysis.variables import bind_parameters
        from m2py.asg.enums import PassingMode

        # Create the target label CALC(X,Y)
        target_label = MLabel(name="CALC", formal_list=["X", "Y"], body=MScope())

        # Create call with two arguments A, B
        var_a = MVariable(name="A", subscripts=[])
        var_b = MVariable(name="B", subscripts=[])
        call = MCall(name="CALC", routine=None, arguments=[var_a, var_b])

        bindings = bind_parameters(call, target_label)

        assert len(bindings) == 2
        assert bindings[0].formal_name == "X"
        assert bindings[0].passing_mode == PassingMode.BY_VALUE
        assert bindings[1].formal_name == "Y"
        assert bindings[1].passing_mode == PassingMode.BY_VALUE

    def test_bind_parameters_partial(self):
        """T611: D CALC(A) calling CALC(X,Y) - X←A, Y←omitted."""
        from m2py.analysis.variables import bind_parameters
        from m2py.asg.enums import PassingMode

        # Create the target label CALC(X,Y)
        target_label = MLabel(name="CALC", formal_list=["X", "Y"], body=MScope())

        # Create call with one argument A
        var_a = MVariable(name="A", subscripts=[])
        call = MCall(name="CALC", routine=None, arguments=[var_a])

        bindings = bind_parameters(call, target_label)

        assert len(bindings) == 2
        assert bindings[0].formal_name == "X"
        assert bindings[0].passing_mode == PassingMode.BY_VALUE
        assert bindings[1].formal_name == "Y"
        assert bindings[1].passing_mode == PassingMode.OMITTED

    def test_byref_creates_alias(self):
        """T617: .X passed to formal A - X aliased."""
        from m2py.analysis.variables import bind_parameters
        from m2py.asg.expressions import MActualParameter
        from m2py.asg.enums import PassingMode

        # Create target label SUB(A)
        target_label = MLabel(name="SUB", formal_list=["A"], body=MScope())

        # Create call with .X (by reference)
        var_x = MVariable(name="X", subscripts=[])
        byref_param = MActualParameter(
            passing_mode=PassingMode.BY_REFERENCE, expression=var_x, variable_name="X"
        )
        call = MCall(name="SUB", routine=None, arguments=[byref_param])

        bindings = bind_parameters(call, target_label)

        assert len(bindings) == 1
        assert bindings[0].formal_name == "A"
        assert bindings[0].passing_mode == PassingMode.BY_REFERENCE
        assert bindings[0].caller_var_name == "X"


class TestSignatureComputation:
    """Advanced tests for function signature computation (Phase 58e-f)."""

    def test_label_no_formal_reads_external(self):
        """T625: Label with no formal params reading external vars."""
        from m2py.analysis.variables import compute_function_signature

        # Label reads X without having it as formal param
        var_x = MVariable(name="X", subscripts=[])
        var_y = MVariable(name="Y", subscripts=[])
        assign = MAssignment(target=var_y, value=var_x)
        set_stmt = MSetStatement(assignments=[assign])
        scope = MScope(statements=[set_stmt])
        label = MLabel(name="NOFORMALS", body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        label_vars = analyze_variables(routine)
        sig = compute_function_signature(label, label_vars["NOFORMALS"])

        # X should be a required input since not in formal params
        assert "X" in sig.required_inputs
        assert sig.formal_params == []

    def test_label_with_indirection_requires_runtime(self):
        """T626: Label with indirection - requires runtime scope."""
        from m2py.analysis.variables import (
            compute_function_signature,
            check_requires_runtime_scope,
        )
        from m2py.asg.statements import MXecuteStatement

        # XECUTE defeats static analysis
        # MXecuteStatement uses code_expressions, not arguments
        xecute_stmt = MXecuteStatement(code_expressions=[MLiteral(value="S X=1")])
        scope = MScope(statements=[xecute_stmt])
        label = MLabel(name="DYN", body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        # Check the function directly
        assert check_requires_runtime_scope(label) is True

        label_vars = analyze_variables(routine)
        sig = compute_function_signature(label, label_vars["DYN"])

        assert sig.requires_runtime_scope is True

    def test_extrinsic_function_signature(self):
        """T634: $$FUNC() extrinsic requires return value."""
        from m2py.analysis.variables import compute_function_signature
        from m2py.asg.enums import ScopeStrategy

        # $$FUNC returns X+Y
        var_x = MVariable(name="X", subscripts=[])
        var_y = MVariable(name="Y", subscripts=[])
        result = MBinaryOp(left=var_x, operator="+", right=var_y)
        quit_stmt = MQuitStatement(return_value=result)
        scope = MScope(statements=[quit_stmt])
        label = MLabel(name="FUNC", formal_list=["X", "Y"], body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        label_vars = analyze_variables(routine)
        sig = compute_function_signature(label, label_vars["FUNC"])

        assert sig.has_value_quit is True
        assert sig.has_void_quit is False
        assert sig.return_value is not None
        # With formal params and return, pure function or function with outputs
        assert sig.scope_strategy in (
            ScopeStrategy.PURE_FUNCTION,
            ScopeStrategy.FUNCTION_WITH_OUTPUTS,
        )


class TestTransitivePropagation:
    """Tests for transitive input/output propagation (Phase 58g)."""

    def test_a_calls_b_calls_c(self):
        """T640: A calls B calls C - transitive input propagation."""
        from m2py.analysis.variables import compute_transitive_inputs

        # C reads VAR
        var_c = MVariable(name="VAR", subscripts=[])
        write_c = MWriteStatement(arguments=[var_c])
        scope_c = MScope(statements=[write_c])
        label_c = MLabel(name="C", body=scope_c)

        # B calls C
        call_c = MCall(name="C", routine=None, arguments=[])
        do_c = MDoStatement(targets=[call_c])
        scope_b = MScope(statements=[do_c])
        label_b = MLabel(name="B", body=scope_b)

        # A calls B
        call_b = MCall(name="B", routine=None, arguments=[])
        do_b = MDoStatement(targets=[call_b])
        scope_a = MScope(statements=[do_b])
        label_a = MLabel(name="A", body=scope_a)

        routine = MRoutine(name="TEST", labels=[label_a, label_b, label_c])
        label_vars = analyze_variables(routine)

        transitive = compute_transitive_inputs(routine, label_vars)

        # C needs VAR, B calls C so B needs VAR, A calls B so A needs VAR
        assert "VAR" in transitive["C"]
        assert "VAR" in transitive["B"]
        assert "VAR" in transitive["A"]

    def test_byref_propagates_output(self):
        """T641: A calls B with by-ref, B modifies - A's outputs include it."""
        from m2py.analysis.variables import (
            compute_transitive_outputs,
            compute_all_signatures,
        )
        from m2py.asg.expressions import MActualParameter
        from m2py.asg.enums import PassingMode

        # B(X) sets X=1
        formal_x = MVariable(name="X", subscripts=[])
        assign = MAssignment(target=formal_x, value=MLiteral(value=1))
        set_stmt = MSetStatement(assignments=[assign])
        scope_b = MScope(statements=[set_stmt])
        label_b = MLabel(name="B", formal_list=["X"], body=scope_b)

        # A calls B(.VAR) - VAR passed by reference
        byref_param = MActualParameter(
            passing_mode=PassingMode.BY_REFERENCE,
            expression=MVariable(name="VAR", subscripts=[]),
            variable_name="VAR",
        )
        call_b = MCall(name="B", routine=None, arguments=[byref_param])
        call_b.target = label_b  # Link call to target
        do_b = MDoStatement(targets=[call_b])
        scope_a = MScope(statements=[do_b])
        label_a = MLabel(name="A", body=scope_a)

        routine = MRoutine(name="TEST", labels=[label_a, label_b])
        routine._labels_by_name = {"A": label_a, "B": label_b}

        label_vars = analyze_variables(routine)
        signatures = compute_all_signatures(routine)

        transitive_outputs = compute_transitive_outputs(routine, label_vars, signatures)

        # B writes to formal X, which is aliased to A's VAR
        # So VAR should be in A's transitive outputs
        assert "VAR" in transitive_outputs["A"]

    def test_nested_byref_chain_propagates(self):
        """T6711: Nested call chain A → B → C with by-ref propagates outputs.

        OUTER calls MIDDLE(.X)
        MIDDLE(A) calls INNER(.A)
        INNER(B) sets B=B*2

        OUTER's transitive_outputs should include X via MIDDLE→INNER chain.

        Note: byref_outputs only captures direct writes within a label.
        MIDDLE doesn't write to A directly (only passes it by-ref to INNER),
        so A won't be in MIDDLE's byref_outputs. However, compute_transitive_outputs
        propagates the modification through the call chain.
        """
        from m2py.analysis.variables import (
            compute_transitive_outputs,
            compute_all_signatures,
        )
        from m2py.asg.expressions import MActualParameter
        from m2py.asg.enums import PassingMode, LiteralType

        # INNER(B) S B=B*2 Q
        formal_b = MVariable(name="B", subscripts=[])
        lit_2 = MLiteral(value=2, literal_type=LiteralType.INTEGER)
        multiply = MBinaryOp(left=formal_b, operator="*", right=lit_2)
        assign_b = MAssignment(target=formal_b, value=multiply)
        set_inner = MSetStatement(assignments=[assign_b])
        quit_inner = MQuitStatement()
        scope_inner = MScope(statements=[set_inner, quit_inner])
        label_inner = MLabel(name="INNER", formal_list=["B"], body=scope_inner)

        # MIDDLE(A) D INNER(.A) Q
        formal_a = MVariable(name="A", subscripts=[])
        byref_a = MActualParameter(
            passing_mode=PassingMode.BY_REFERENCE,
            expression=formal_a,
            variable_name="A",
        )
        call_inner = MCall(name="INNER", routine=None, arguments=[byref_a])
        call_inner.target = label_inner
        do_inner = MDoStatement(targets=[call_inner])
        quit_middle = MQuitStatement()
        scope_middle = MScope(statements=[do_inner, quit_middle])
        label_middle = MLabel(name="MIDDLE", formal_list=["A"], body=scope_middle)

        # OUTER D MIDDLE(.X) Q
        var_x = MVariable(name="X", subscripts=[])
        byref_x = MActualParameter(
            passing_mode=PassingMode.BY_REFERENCE,
            expression=var_x,
            variable_name="X",
        )
        call_middle = MCall(name="MIDDLE", routine=None, arguments=[byref_x])
        call_middle.target = label_middle
        do_middle = MDoStatement(targets=[call_middle])
        quit_outer = MQuitStatement()
        scope_outer = MScope(statements=[do_middle, quit_outer])
        label_outer = MLabel(name="OUTER", body=scope_outer)

        routine = MRoutine(name="TEST", labels=[label_outer, label_middle, label_inner])
        routine._labels_by_name = {
            "OUTER": label_outer,
            "MIDDLE": label_middle,
            "INNER": label_inner,
        }

        label_vars = analyze_variables(routine)
        signatures = compute_all_signatures(routine)

        # Verify byref_outputs are populated correctly for direct writes
        # INNER writes to B, so B is in byref_outputs
        assert "B" in signatures["INNER"].byref_outputs
        # MIDDLE does NOT write to A directly - it only passes A by-ref
        # So A is NOT in MIDDLE's byref_outputs (this is correct!)
        assert "A" not in signatures["MIDDLE"].byref_outputs

        transitive_outputs = compute_transitive_outputs(routine, label_vars, signatures)

        # INNER writes B, which is aliased to MIDDLE's A
        # So A should be in MIDDLE's transitive outputs
        assert "A" in transitive_outputs["MIDDLE"]
        # MIDDLE modifies A (transitively), which is aliased to OUTER's X
        # So X should be in OUTER's transitive outputs
        assert "X" in transitive_outputs["OUTER"]

    def test_byref_param_not_modified_not_in_outputs(self):
        """T6712: By-ref param NOT modified → NOT in transitive outputs.

        CALLER calls READER(.X)
        READER(A) W A Q  ; Only reads A, doesn't write

        CALLER's transitive_outputs should NOT include X.
        """
        from m2py.analysis.variables import (
            compute_transitive_outputs,
            compute_all_signatures,
        )
        from m2py.asg.expressions import MActualParameter
        from m2py.asg.enums import PassingMode

        # READER(A) W A Q - only reads A
        formal_a = MVariable(name="A", subscripts=[])
        write_stmt = MWriteStatement(arguments=[formal_a])
        quit_reader = MQuitStatement()
        scope_reader = MScope(statements=[write_stmt, quit_reader])
        label_reader = MLabel(name="READER", formal_list=["A"], body=scope_reader)

        # CALLER D READER(.X) Q
        var_x = MVariable(name="X", subscripts=[])
        byref_x = MActualParameter(
            passing_mode=PassingMode.BY_REFERENCE,
            expression=var_x,
            variable_name="X",
        )
        call_reader = MCall(name="READER", routine=None, arguments=[byref_x])
        call_reader.target = label_reader
        do_reader = MDoStatement(targets=[call_reader])
        quit_caller = MQuitStatement()
        scope_caller = MScope(statements=[do_reader, quit_caller])
        label_caller = MLabel(name="CALLER", body=scope_caller)

        routine = MRoutine(name="TEST", labels=[label_caller, label_reader])
        routine._labels_by_name = {"CALLER": label_caller, "READER": label_reader}

        label_vars = analyze_variables(routine)
        signatures = compute_all_signatures(routine)

        # Verify READER doesn't have A in byref_outputs (only reads, no writes)
        assert "A" not in signatures["READER"].byref_outputs
        assert "A" in label_vars["READER"].reads
        assert "A" not in label_vars["READER"].writes

        transitive_outputs = compute_transitive_outputs(routine, label_vars, signatures)

        # READER doesn't modify A, so X should NOT be in CALLER's outputs
        assert "X" not in transitive_outputs["CALLER"]


class TestFormalParamsShadowing:
    """Tests for formal parameter shadowing (Phase 58a)."""

    def test_read_caller_var_before_formal_shadows(self):
        """T595: Reading caller's variable before formal param shadows it.

        Per MUMPS semantics, formal params perform implicit NEW at entry.
        If a label reads a variable with same name as formal param before
        any writes, it reads the *local* NEW'd copy (undefined), not caller's.
        """
        # Label CALC(X) that immediately reads X
        # Since X is formal param, it's NEWed implicitly, so X starts undefined
        var_x = MVariable(name="X", subscripts=[])
        var_result = MVariable(name="RESULT", subscripts=[])
        # S RESULT=X (reads X which is formal, so local copy not caller's)
        assign = MAssignment(target=var_result, value=var_x)
        set_stmt = MSetStatement(assignments=[assign])
        scope = MScope(statements=[set_stmt])
        label = MLabel(name="CALC", formal_list=["X"], body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        result = analyze_variables(routine)

        # X is a formal param, so it should NOT be in input_variables
        # (it's provided via the call, not read from caller's scope)
        assert "X" not in result["CALC"].input_variables
        # X IS in reads (we do read it)
        assert "X" in result["CALC"].reads
        # X is treated as implicitly NEWed
        assert "X" in result["CALC"].formal_params


class TestRoutineAnalysisCache:
    """Tests for RoutineAnalysisCache (Phase 59 - T683)."""

    def test_cache_basic_usage(self):
        """Test basic cache usage pattern."""
        from m2py.analysis.variables import RoutineAnalysisCache

        # Create a routine with two labels
        var_x = MVariable(name="X", subscripts=[])
        set_stmt = MSetStatement(
            assignments=[MAssignment(target=var_x, value=MLiteral(value="1"))]
        )
        scope_a = MScope(statements=[set_stmt])
        label_a = MLabel(name="A", body=scope_a)

        scope_b = MScope(statements=[])
        label_b = MLabel(name="B", body=scope_b)

        routine = MRoutine(name="TEST", labels=[label_a, label_b])

        cache = RoutineAnalysisCache(routine)
        cache.ensure_analyzed(compute_transitive=False)

        # Check that results are accessible
        assert "A" in cache.label_vars
        assert "B" in cache.label_vars
        assert "X" in cache.label_vars["A"].writes

    def test_cache_invalidate_label(self):
        """Test invalidating a specific label."""
        from m2py.analysis.variables import RoutineAnalysisCache

        var_x = MVariable(name="X", subscripts=[])
        set_stmt = MSetStatement(
            assignments=[MAssignment(target=var_x, value=MLiteral(value="1"))]
        )
        scope = MScope(statements=[set_stmt])
        label = MLabel(name="A", body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        cache = RoutineAnalysisCache(routine)
        cache.ensure_analyzed(compute_transitive=False)

        # Invalidate and re-analyze
        cache.invalidate_label("A")
        assert not cache._fully_analyzed

        cache.ensure_analyzed(compute_transitive=False)
        assert cache._fully_analyzed


class TestPerformance:
    """Performance tests for variable analysis (Phase 59 - T684)."""

    def test_analysis_performance_500_lines(self, tmp_path):
        """T684: 500-line routine analyzes in <2 seconds per SC-005.

        This test generates a synthetic 500+ line MUMPS routine and
        verifies that full analysis completes within 2 seconds.
        """
        import time
        from m2py.parser.parser import MUMPSParser

        # Generate a 550-line MUMPS routine with realistic complexity
        lines = ["TEST ; Performance test routine"]

        # Generate 25 labels, each with ~22 lines (25 * 22 = 550)
        for i in range(25):
            lines.append(f"LABEL{i}(P{i})")
            # Mix of SET, NEW, WRITE, IF statements
            for j in range(6):
                lines.append(f" N VAR{j}")
            for j in range(6):
                lines.append(f" S VAR{j}=P{i}+{j}")
            for j in range(6):
                lines.append(f" W VAR{j},!")
            for j in range(3):
                lines.append(f" I VAR{j}>0 D")
                lines.append(f" . S RESULT=VAR{j}*2")
            lines.append(f" Q P{i}")

        # Add some cross-label calls
        lines.append("MAIN")
        for i in range(20):
            lines.append(f" D LABEL{i}({i})")
        lines.append(" Q")

        source = "\n".join(lines)
        assert len(lines) > 500, f"Generated {len(lines)} lines, need 500+"

        # Write to temp file
        test_file = tmp_path / "PERF.m"
        test_file.write_text(source)

        # Time parsing + full analysis
        parser = MUMPSParser()

        start = time.perf_counter()
        routine = parser.parse_file(test_file)
        parser.analyze_variables(routine, compute_transitive=True)
        parser.compute_signatures(routine)
        elapsed = time.perf_counter() - start

        # Verify analysis completed
        assert len(routine.labels) >= 20

        # SC-005 requirement: <2 seconds
        assert elapsed < 2.0, f"Analysis took {elapsed:.2f}s, exceeds 2s limit"

        # Informational: print timing
        print(f"\n  Performance: {len(lines)} lines analyzed in {elapsed * 1000:.1f}ms")


# =============================================================================
# RoutineAnalysisCache Incremental Analysis Tests
# =============================================================================


class TestRoutineAnalysisCacheIncremental:
    """Test RoutineAnalysisCache incremental analysis paths.

    These tests cover the incremental reanalysis paths in ensure_analyzed()
    that were added for performance optimization.
    """

    def test_cache_incremental_reanalysis(self):
        """Test incremental reanalysis when label is invalidated.

        This tests the incremental path in ensure_analyzed() where only
        stale labels are reanalyzed.
        """
        from m2py.analysis.variables import RoutineAnalysisCache

        # Create routine with multiple labels
        var_x = MVariable(name="X", subscripts=[])
        var_y = MVariable(name="Y", subscripts=[])

        set_x = MSetStatement(
            assignments=[MAssignment(target=var_x, value=MLiteral(value="1"))]
        )
        set_y = MSetStatement(
            assignments=[MAssignment(target=var_y, value=MLiteral(value="2"))]
        )

        scope_a = MScope(statements=[set_x])
        scope_b = MScope(statements=[set_y])
        scope_c = MScope(statements=[])

        label_a = MLabel(name="A", body=scope_a)
        label_b = MLabel(name="B", body=scope_b)
        label_c = MLabel(name="C", body=scope_c)

        routine = MRoutine(name="TEST", labels=[label_a, label_b, label_c])

        cache = RoutineAnalysisCache(routine)
        cache.ensure_analyzed(compute_transitive=True)

        assert cache._fully_analyzed
        initial_a_writes = cache.label_vars["A"].writes.copy()

        # Invalidate only one label
        cache.invalidate_label("A")
        assert not cache._fully_analyzed
        assert "A" not in cache._valid_labels
        assert "B" in cache._valid_labels
        assert "C" in cache._valid_labels

        # Re-analyze - should only recompute label A
        cache.ensure_analyzed(compute_transitive=True)
        assert cache._fully_analyzed
        assert cache.label_vars["A"].writes == initial_a_writes

    def test_cache_invalidate_all_triggers_full_reanalysis(self):
        """Test that invalidate_all clears everything."""
        from m2py.analysis.variables import RoutineAnalysisCache

        var_x = MVariable(name="X", subscripts=[])
        set_stmt = MSetStatement(
            assignments=[MAssignment(target=var_x, value=MLiteral(value="1"))]
        )
        scope = MScope(statements=[set_stmt])

        label_a = MLabel(name="A", body=scope)
        label_b = MLabel(name="B", body=MScope(statements=[]))

        routine = MRoutine(name="TEST", labels=[label_a, label_b])

        cache = RoutineAnalysisCache(routine)
        cache.ensure_analyzed(compute_transitive=False)

        assert len(cache._valid_labels) == 2

        cache.invalidate_all()
        assert len(cache._valid_labels) == 0
        assert not cache._fully_analyzed

        # Re-analyze
        cache.ensure_analyzed(compute_transitive=False)
        assert cache._fully_analyzed
        assert len(cache._valid_labels) == 2

    def test_cache_full_reanalysis_when_many_labels_stale(self):
        """Test that full reanalysis triggers when >50% labels are stale.

        This tests the optimization path in ensure_analyzed() that does
        full reanalysis instead of incremental when too many labels changed.
        """
        from m2py.analysis.variables import RoutineAnalysisCache

        # Create routine with 4 labels
        labels = []
        for name in ["A", "B", "C", "D"]:
            scope = MScope(statements=[])
            labels.append(MLabel(name=name, body=scope))

        routine = MRoutine(name="TEST", labels=labels)

        cache = RoutineAnalysisCache(routine)
        cache.ensure_analyzed(compute_transitive=False)

        # Invalidate 3 out of 4 labels (>50%)
        cache.invalidate_label("A")
        cache.invalidate_label("B")
        cache.invalidate_label("C")

        assert len(cache._valid_labels) == 1  # Only D is valid

        # Re-analyze - should trigger full reanalysis path
        cache.ensure_analyzed(compute_transitive=False)
        assert cache._fully_analyzed
        assert len(cache._valid_labels) == 4

    def test_cache_call_graph_building(self):
        """Test that call graph is built correctly for affected label tracking."""
        from m2py.analysis.variables import RoutineAnalysisCache

        # Create routine where A calls B
        call_b = MCall(name="B")
        do_stmt = MDoStatement(targets=[call_b])
        scope_a = MScope(statements=[do_stmt])

        scope_b = MScope(statements=[])

        label_a = MLabel(name="A", body=scope_a)
        label_b = MLabel(name="B", body=scope_b)

        routine = MRoutine(name="TEST", labels=[label_a, label_b])

        cache = RoutineAnalysisCache(routine)
        cache.ensure_analyzed(compute_transitive=True)

        # Verify call graph was built
        assert "A" in cache._call_graph
        assert "B" in cache._call_graph["A"]

        # Verify reverse call graph
        assert "B" in cache._reverse_call_graph
        assert "A" in cache._reverse_call_graph["B"]

    def test_cache_affected_labels_transitive(self):
        """Test that affected labels includes transitive callers."""
        from m2py.analysis.variables import RoutineAnalysisCache

        # Create call chain: A -> B -> C
        call_b = MCall(name="B")
        call_c = MCall(name="C")

        do_b = MDoStatement(targets=[call_b])
        do_c = MDoStatement(targets=[call_c])

        scope_a = MScope(statements=[do_b])
        scope_b = MScope(statements=[do_c])
        scope_c = MScope(statements=[])

        label_a = MLabel(name="A", body=scope_a)
        label_b = MLabel(name="B", body=scope_b)
        label_c = MLabel(name="C", body=scope_c)

        routine = MRoutine(name="TEST", labels=[label_a, label_b, label_c])

        cache = RoutineAnalysisCache(routine)
        cache.ensure_analyzed(compute_transitive=True)

        # Get affected labels if C changes
        affected = cache._get_affected_labels({"C"})

        # Should include C and all transitive callers (B, A)
        assert "C" in affected
        assert "B" in affected
        assert "A" in affected

    def test_cache_signatures_property(self):
        """Test the signatures property accessor."""
        from m2py.analysis.variables import RoutineAnalysisCache

        var_x = MVariable(name="X", subscripts=[])
        set_stmt = MSetStatement(
            assignments=[MAssignment(target=var_x, value=MLiteral(value="1"))]
        )
        scope = MScope(statements=[set_stmt])
        label = MLabel(name="A", body=scope)

        routine = MRoutine(name="TEST", labels=[label])

        cache = RoutineAnalysisCache(routine)

        # Accessing signatures should trigger analysis
        sigs = cache.signatures
        assert "A" in sigs
        assert cache._fully_analyzed


class TestRoutineRequiresRuntimeEval:
    """Tests for MRoutine.requires_runtime_eval rollup from label signatures."""

    def test_routine_without_indirection_does_not_require_runtime(self):
        """T6831a: Routine with no indirection has requires_runtime_eval=False."""
        from m2py.analysis.variables import compute_all_signatures

        # Simple SET X=1 - no indirection
        var_x = MVariable(name="X", subscripts=[])
        set_stmt = MSetStatement(
            assignments=[MAssignment(target=var_x, value=MLiteral(value="1"))]
        )
        scope = MScope(statements=[set_stmt])
        label = MLabel(name="MAIN", body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        compute_all_signatures(routine)

        assert routine.requires_runtime_eval is False

    def test_routine_with_xecute_requires_runtime(self):
        """T6831b: Routine with XECUTE has requires_runtime_eval=True."""
        from m2py.analysis.variables import compute_all_signatures
        from m2py.asg.statements import MXecuteStatement

        # Label with XECUTE defeats static analysis
        xecute_stmt = MXecuteStatement(code_expressions=[MLiteral(value="S X=1")])
        scope = MScope(statements=[xecute_stmt])
        label = MLabel(name="DYN", body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        compute_all_signatures(routine)

        assert routine.requires_runtime_eval is True

    def test_routine_with_one_runtime_label_requires_runtime(self):
        """T6831c: Routine requires runtime if ANY label requires it."""
        from m2py.analysis.variables import compute_all_signatures
        from m2py.asg.statements import MXecuteStatement

        # Label 1: Simple, no indirection
        var_x = MVariable(name="X", subscripts=[])
        set_stmt = MSetStatement(
            assignments=[MAssignment(target=var_x, value=MLiteral(value="1"))]
        )
        scope1 = MScope(statements=[set_stmt])
        label1 = MLabel(name="SIMPLE", body=scope1)

        # Label 2: Has XECUTE
        xecute_stmt = MXecuteStatement(code_expressions=[MLiteral(value="S Y=2")])
        scope2 = MScope(statements=[xecute_stmt])
        label2 = MLabel(name="DYNAMIC", body=scope2)

        routine = MRoutine(name="TEST", labels=[label1, label2])

        compute_all_signatures(routine)

        # Routine should require runtime because one label does
        assert routine.requires_runtime_eval is True
        # Verify individual labels
        assert label1.signature.requires_runtime_scope is False
        assert label2.signature.requires_runtime_scope is True

    def test_routine_with_indirect_do_requires_runtime(self):
        """T6831d: Routine with D @VAR has requires_runtime_eval=True."""
        from m2py.analysis.variables import compute_all_signatures

        # DO @VAR - indirected call
        call = MCall(name="", label_is_indirect=True, indirection=MVariable(name="CMD"))
        do_stmt = MDoStatement(targets=[call])
        scope = MScope(statements=[do_stmt])
        label = MLabel(name="INDIRECT", body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        compute_all_signatures(routine)

        assert routine.requires_runtime_eval is True
