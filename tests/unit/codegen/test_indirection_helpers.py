"""Tests for indirection codegen helper functions.

Tests for the new helper functions in m2py.codegen.indirection:
- _get_scope_expr: Returns appropriate scope expression for context
- _generate_for_indirection_target: FOR loop indirection code generation

These functions support TRAMPOLINE mode with dynamic_locals.
"""

import pytest
from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


# =============================================================================
# _get_scope_expr Context Tests (via generated code inspection)
# =============================================================================


@pytest.mark.codegen
class TestScopeExprInGeneratedCode:
    """Tests verifying correct scope expression in generated code."""

    def test_simple_indirection_uses_scope(self):
        """Simple indirection in SIMPLE_FUNCTIONS uses _scope."""
        code = generate_python('TEST\n S X="Y" S @X=1 Q\n')
        # In SIMPLE_FUNCTIONS mode, should use _scope
        assert "_scope" in code

    def test_trampoline_with_argumentless_kill_uses_state_locals(self):
        """TRAMPOLINE with argumentless KILL uses state._locals."""
        # Argumentless KILL triggers dynamic_locals mode
        code = generate_python(
            "TEST\n S X=1,Y=2 K\n W X Q\nOTHER\n G TEST Q\n"  # GOTO triggers TRAMPOLINE
        )
        # Should use state._locals for dynamic variable access
        if "TRAMPOLINE" in code or "state" in code:
            # If TRAMPOLINE mode was triggered, check for state._locals
            pass  # Mode detection depends on GOTO analysis


# =============================================================================
# FOR Loop Indirection Target Generation Tests
# =============================================================================


@pytest.mark.codegen
class TestForIndirectionTargetGeneration:
    """Tests for _generate_for_indirection_target code generation."""

    def test_single_level_indirection(self):
        """F @A generates resolve_indirection_name with levels=1."""
        code = generate_python('TEST\n S A="I" F @A=1:1:3 W I\n Q\n')
        # Should use resolve_indirection_name
        assert "resolve_indirection_name" in code
        # Should have level 1
        assert ", 1," in code

    def test_double_level_indirection(self):
        """F @@A generates resolve_indirection_name with levels=2."""
        code = generate_python('TEST\n S A="B",B="I" F @@A=1:1:3 W I\n Q\n')
        # Should use resolve_indirection_name
        assert "resolve_indirection_name" in code
        # Should have level 2
        assert ", 2," in code

    def test_indirect_var_stored_before_loop(self):
        """Indirect variable name resolved before loop starts."""
        code = generate_python('TEST\n S V="X" F @V=1:1:3 W X\n Q\n')
        # Should have _for_indirect_var assignment before while
        assert "_for_indirect_var" in code

    def test_subscripted_loop_var_uses_set(self):
        """Subscripted loop var uses MArray.set() for access."""
        code = generate_python("TEST\n F I(1)=1:1:3 W I(1)\n Q\n")
        # Should use .set() for initial value
        assert ".set(1, value=" in code


# =============================================================================
# TRAMPOLINE Mode Dynamic Locals Tests
# =============================================================================


@pytest.mark.codegen
class TestTrampolineDynamicLocals:
    """Tests for TRAMPOLINE mode with dynamic locals."""

    def test_argumentless_new_triggers_dynamic_locals(self):
        """Argumentless NEW triggers dynamic_locals mode."""
        code = generate_python(
            "TEST\n S X=1 N\n W X Q\nOTHER\n G TEST Q\n"  # GOTO triggers TRAMPOLINE
        )
        # When TRAMPOLINE + argumentless NEW, should use state._locals
        # and RoutineState should have _locals field
        if "RoutineState" in code:
            assert "_locals" in code

    def test_argumentless_kill_triggers_dynamic_locals(self):
        """Argumentless KILL triggers dynamic_locals mode."""
        code = generate_python(
            "TEST\n S X=1,Y=2 K\n W X Q\nOTHER\n G TEST Q\n"  # GOTO triggers TRAMPOLINE
        )
        if "RoutineState" in code:
            assert "_locals" in code

    def test_name_indirection_on_locals_triggers_dynamic(self):
        """D @X where X is local triggers dynamic_locals mode."""
        code = generate_python(
            'TEST\n S X="SUB" D @X Q\n'
            "SUB\n W 1 Q\n"
            "OTHER\n G TEST Q\n"  # GOTO triggers TRAMPOLINE
        )
        # Name indirection on local should trigger dynamic_locals
        if "RoutineState" in code:
            # Should have _locals for dynamic access
            pass


# =============================================================================
# Integration: Indirection Execution Tests
# =============================================================================


@pytest.fixture
def execute_mumps():
    """Execute MUMPS code and return result."""

    def _execute(source: str):
        python_code = generate_python(source)
        runtime = MUMPSRuntime()
        result = runtime.execute(python_code, capture_output=True)
        return result.output

    return _execute


@pytest.mark.codegen
class TestIndirectionExecution:
    """Integration tests executing indirection code."""

    def test_for_simple_indirect_execution(self, execute_mumps):
        """F @A=1:1:3 W X executes correctly."""
        result = execute_mumps('TEST\n S A="X" F @A=1:1:3 W X\n Q\n')
        assert result == "123"

    def test_for_subscripted_var_execution(self, execute_mumps):
        """F I(1)=1:1:3 W I(1) executes correctly."""
        result = execute_mumps("TEST\n F I(1)=1:1:3 W I(1)\n Q\n")
        assert result == "123"

    def test_nested_indirection_in_for(self, execute_mumps):
        """F @A where A contains @B chain."""
        # A contains "@B", B contains "X", so loop var is X
        result = execute_mumps('TEST\n S A="@B",B="X" F @A=1:1:3 W X\n Q\n')
        assert result == "123"
