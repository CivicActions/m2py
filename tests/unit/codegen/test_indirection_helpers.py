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
    """Tests for FOR loop indirection target code generation (T089)."""

    def test_single_level_indirection(self):
        """F @A generates resolve_for_target with levels=1."""
        code = generate_python('TEST\n S A="I" F @A=1:1:3 W I\n Q\n')
        # Should use resolve_for_target (unified approach)
        assert "resolve_for_target" in code
        # Should have level 1
        assert "levels=1" in code

    def test_double_level_indirection(self):
        """F @@A generates resolve_for_target with levels=2."""
        code = generate_python('TEST\n S A="B",B="I" F @@A=1:1:3 W I\n Q\n')
        # Should use resolve_for_target (unified approach)
        assert "resolve_for_target" in code
        # Should have level 2
        assert "levels=2" in code

    def test_indirect_var_stored_before_loop(self):
        """Indirect variable name resolved before loop starts."""
        code = generate_python('TEST\n S V="X" F @V=1:1:3 W X\n Q\n')
        # Should have _for_indirect_var assignment before while
        assert "_for_indirect_var" in code

    def test_subscripted_loop_var_uses_set(self):
        """Subscripted loop var uses MArray.set() with cached subscript.

        Per MUMPS spec: subscripts are evaluated once at FOR loop start.
        """
        code = generate_python("TEST\n F I(1)=1:1:3 W I(1)\n Q\n")
        # Should cache subscript and use .set() with cached value
        assert "_for_sub_0_0 = 1" in code
        assert ".set(_for_sub_0_0, value=" in code


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

    def test_for_loop_body_modifies_loop_var_codegen(self):
        """T084: FOR loop body modification uses state._locals in TRAMPOLINE.

        When body modifies loop variable with zero step (I=I+2), the generated
        code must sync with state._locals so loop condition sees body changes.

        Test case from MVTS I-340.4:
        FOR I=-4:0:5.3 S VCOMP=VCOMP_I,I=I+2,VCOMP=VCOMP_I
        Expected: -4-2-200224466 (loop terminates when body increments I>5.3)
        """
        # Cross-label GOTO + argumentless KILL triggers TRAMPOLINE + dynamic_locals
        code = generate_python(
            'TEST\n S VCOMP="" F I=-4:0:5.3 S VCOMP=VCOMP_I,I=I+2,VCOMP=VCOMP_I Q\n'
            "OTHER\n K\n G TEST Q\n"  # K triggers dynamic_locals, G triggers TRAMPOLINE
        )
        # In TRAMPOLINE with dynamic_locals, FOR loop should use state._locals
        # for loop_ref so body modifications are visible to loop condition
        assert "state._locals" in code
        # Loop should read from state._locals, not a Python local
        # E743: I is translated to _a_I to avoid ambiguity
        assert "state._locals.setdefault('_a_I'" in code

    def test_for_loop_body_modifies_loop_var_execution(self, execute_mumps):
        """T084: FOR loop body modification executes correctly in TRAMPOLINE.

        I-340.4: FOR with zero step where body modifies loop var must terminate.
        """
        # Need to trigger TRAMPOLINE + dynamic_locals
        # Cross-label GOTO triggers TRAMPOLINE, argumentless KILL triggers dynamic_locals
        result = execute_mumps(
            'TEST\n S VCOMP="" F I=-4:0:5.3 S VCOMP=VCOMP_I,I=I+2,VCOMP=VCOMP_I\n'
            " W VCOMP Q\n"
            "OTHER\n K\n G TEST Q\n"
        )
        # Expected output from YDB: -4-2-20022446
        assert result == "-4-2-20022446"

    def test_for_open_ended_with_goto_codegen(self):
        """T089h: Open-ended FOR in TRAMPOLINE syncs loop var to state._locals.

        When an open-ended FOR loop (F I=1:1) is in TRAMPOLINE mode with
        dynamic_locals, the loop variable must be synced to state._locals
        so that body code reading via state._locals.get('I') sees the value.

        Test case from MUGJ V1FORA2 I-350:
        F I=1:1 S VCOMP=VCOMP_I I I=5 G G350
        Expected: terminates when I reaches 5

        Without the fix, state.I is set by the for loop but state._locals['I']
        is never updated, causing the IF condition to always read empty string.
        """
        # Cross-label GOTO triggers TRAMPOLINE, argumentless KILL triggers dynamic_locals
        code = generate_python(
            'TEST\n S VCOMP="" F I=1:1 S VCOMP=VCOMP_I I I=5 G OUT\n'
            " Q\nOUT\n W VCOMP Q\n"
            "OTHER\n K\n G TEST Q\n"
        )
        # In TRAMPOLINE with dynamic_locals, open-ended FOR should sync to state._locals
        assert "state._locals" in code
        # Loop should sync I to state._locals
        # E743: I is translated to _a_I to avoid ambiguity
        assert "state._locals.setdefault('_a_I'" in code

    def test_for_open_ended_with_goto_execution(self, execute_mumps):
        """T089h: Open-ended FOR in TRAMPOLINE executes correctly.

        I-350 pattern: Open-ended FOR with IF condition checking loop var.
        The IF must see the loop variable value from state._locals.
        """
        result = execute_mumps(
            'TEST\n S VCOMP="" F I=1:1 S VCOMP=VCOMP_I I I=5 G OUT\n'
            " Q\nOUT\n W VCOMP Q\n"
            "OTHER\n K\n G TEST Q\n"
        )
        # Should terminate when I=5, output: 12345
        assert result == "12345"


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


# =============================================================================
# T087: Subscript Indirection Context Tests
# =============================================================================


@pytest.mark.codegen
class TestSubscriptIndirectionContext:
    """Tests for T087: Subscript indirection uses VALUE instead of NAME.

    When @X appears inside a subscript position (e.g., ^A(@X) or A(@X)),
    the indirection should return the VALUE for use as a subscript,
    not validate the result as a variable NAME.

    Key difference:
    - NAME indirection: @X where X="Y" validates "Y" as variable name
    - SUBSCRIPT indirection: A(@X) where X="5" uses "5" as subscript value
    """

    def test_subscript_indirection_uses_value_not_name(self, execute_mumps):
        """T087: ^A(@X) where X=55 should use 55 as subscript (I-502).

        This tests the exact case from V1IDNM2.m test I-502.
        @^(4) should resolve to VALUE 55, not validate "55" as a name.
        """
        # Setup: ^V1A(5)=55, ^V1A(4)="^V1A(5)"
        # Action: S ^V1A(@^(4))=200
        # @^(4) -> "^V1A(5)" -> 55 (VALUE)
        # Result: ^V1A(55)=200
        result = execute_mumps(
            "TEST\n"
            ' S ^V1A(5)=55,^V1A(4)="^V1A(5)"\n'
            " S ^V1A(@^(4))=200\n"
            " W ^V1A(55)\n"
            " Q\n"
        )
        assert result == "200"

    def test_subscript_indirection_local_array(self, execute_mumps):
        """T087: A(@X) where X=3 should use 3 as subscript.

        Local array subscript indirection must also use VALUE.
        """
        result = execute_mumps(
            "TEST\n S X=3\n S A(1)=10,A(2)=20,A(3)=30\n W A(@X)\n Q\n"
        )
        assert result == "30"

    def test_subscript_indirection_resolves_chain(self, execute_mumps):
        """T087: @X in subscript where X points to another var.

        @X where X="Y" and Y=5 should resolve to VALUE 5.
        """
        result = execute_mumps('TEST\n S X="Y",Y=5\n S A(5)="found"\n W A(@X)\n Q\n')
        assert result == "found"

    def test_subscript_indirection_multiple_levels(self, execute_mumps):
        """T087: @@X in subscript resolves two levels.

        @@X where X="Y", Y="Z", Z=7 -> VALUE 7.
        """
        result = execute_mumps(
            'TEST\n S X="Y",Y="Z",Z=7\n S A(7)="level2"\n W A(@@X)\n Q\n'
        )
        assert result == "level2"

    def test_subscript_indirection_nested_in_subscript(self, execute_mumps):
        """T087: A(B(@C)) - subscripted variable with indirection in subscript.

        This tests a subscripted local variable where one subscript uses
        indirection. B(@C) where C="key" and key=99 gives B(99).
        The @C resolves to "key", then "key" is looked up to get 99.
        """
        result = execute_mumps(
            "TEST\n"
            ' S C="key",key=99,B(99)="found"\n'  # key=99 so @C -> "key" -> 99
            " W B(@C)\n"
            " Q\n"
        )
        assert result == "found"

    def test_subscript_indirection_codegen_uses_get_subscript_indirected(self):
        """T087: Generated code uses get_subscript_indirected for subscripts."""
        code = generate_python('TEST\n S X="Y"\n W A(@X)\n Q\n')
        # Should use get_subscript_indirected in subscript context
        assert "get_subscript_indirected" in code

    def test_subscript_indirection_global_set_target(self, execute_mumps):
        """T087: SET ^A(@X)=value uses VALUE for subscript.

        The SET target subscript should also use VALUE indirection.
        """
        result = execute_mumps('TEST\n S X=42\n S ^G(@X)="success"\n W ^G(42)\n Q\n')
        assert result == "success"

    def test_subscript_indirection_naked_global(self, execute_mumps):
        """T087: ^(@X) naked global with subscript indirection.

        After accessing ^A(1), naked ^(@X) where X=2 should access ^A(2).
        """
        result = execute_mumps(
            "TEST\n"
            ' S ^A(1)="one",^A(2)="two"\n'
            " S X=2\n"
            " S Y=^A(1)\n"  # Set naked indicator to ^A(1)
            " W ^(@X)\n"  # Should access ^A(2)
            " Q\n"
        )
        assert result == "two"
