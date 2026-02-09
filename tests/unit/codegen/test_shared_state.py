"""Tests for RoutineState generation (Spec 006 Phase 4).

Tests the generation of RoutineState dataclass for cross-label variable visibility.
"""

import pytest

from m2py.asg.elements import MRoutine
from m2py.codegen.shared_state import (
    generate_routine_state_class,
    generate_state_initialization,
)

# Inline imports string (generate_state_imports was removed as dead code)
_STATE_IMPORTS = (
    "from dataclasses import dataclass, field\n"
    "from typing import Any\n"
    "from m2py.runtime import MArray\n"
)


@pytest.mark.codegen
class TestGenerateRoutineStateClass:
    """Tests for generate_routine_state_class() function (T048, T050)."""

    def test_empty_routine_generates_minimal_class(self):
        """T050: Routine with no cross-label vars generates minimal dataclass."""
        routine = MRoutine(name="TEST")
        routine.routine_state_vars = set()
        routine.array_vars = set()

        code = generate_routine_state_class(routine)

        assert "@dataclass" in code
        assert "class RoutineState:" in code
        assert "pass" in code

    def test_simple_variable_generates_any_field(self):
        """T048: Simple variable generates Any typed field."""
        routine = MRoutine(name="TEST")
        routine.routine_state_vars = {"X"}
        routine.array_vars = set()

        code = generate_routine_state_class(routine)

        assert "@dataclass" in code
        assert "class RoutineState:" in code
        assert "X: Any = None" in code

    def test_multiple_simple_variables(self):
        """T048: Multiple simple variables generate sorted fields."""
        routine = MRoutine(name="TEST")
        routine.routine_state_vars = {"Z", "A", "M"}
        routine.array_vars = set()

        code = generate_routine_state_class(routine)

        # Variables should be sorted alphabetically
        assert "A: Any = None" in code
        assert "M: Any = None" in code
        assert "Z: Any = None" in code

        # Check order (A before M before Z)
        lines = code.split("\n")
        a_line = next(idx for idx, line in enumerate(lines) if "A: Any" in line)
        m_line = next(idx for idx, line in enumerate(lines) if "M: Any" in line)
        z_line = next(idx for idx, line in enumerate(lines) if "Z: Any" in line)
        assert a_line < m_line < z_line


@pytest.mark.codegen
class TestMArrayIntegration:
    """Tests for MArray fields in RoutineState (T054)."""

    def test_array_variable_generates_marray_field(self):
        """T054: Array variable generates MArray typed field."""
        routine = MRoutine(name="TEST")
        routine.routine_state_vars = set()
        routine.array_vars = {"A"}

        code = generate_routine_state_class(routine)

        assert "@dataclass" in code
        assert "A: MArray = field(default_factory=MArray)" in code

    def test_mixed_simple_and_array_variables(self):
        """T054: Routine with both simple and array vars generates both field types."""
        routine = MRoutine(name="TEST")
        routine.routine_state_vars = {"X", "Y"}
        routine.array_vars = {"A", "B"}

        code = generate_routine_state_class(routine)

        # Simple vars as Any
        assert "X: Any = None" in code
        assert "Y: Any = None" in code

        # Array vars as MArray
        assert "A: MArray = field(default_factory=MArray)" in code
        assert "B: MArray = field(default_factory=MArray)" in code

    def test_array_var_in_state_vars_uses_marray(self):
        """T054: Variable that's both in state_vars and array_vars uses MArray."""
        routine = MRoutine(name="TEST")
        routine.routine_state_vars = {"A"}  # Also in array_vars
        routine.array_vars = {"A"}

        code = generate_routine_state_class(routine)

        # Should be MArray, not Any
        assert "A: MArray = field(default_factory=MArray)" in code
        assert "A: Any" not in code


@pytest.mark.codegen
class TestGenerateStateInitialization:
    """Tests for generate_state_initialization() function (T049, T050)."""

    def test_generates_constructor_call(self):
        """T049: Generates RoutineState() constructor call."""
        routine = MRoutine(name="TEST")

        code = generate_state_initialization(routine)

        assert "state = RoutineState()" in code


@pytest.mark.codegen
class TestVariableNameTranslation:
    """Tests for variable name translation in RoutineState (T050)."""

    def test_percent_prefix_translated(self):
        """MUMPS %VAR translates to _pct_VAR in Python."""
        routine = MRoutine(name="TEST")
        routine.routine_state_vars = {"%X"}
        routine.array_vars = set()

        code = generate_routine_state_class(routine)

        # % prefix translated to _pct_
        assert "_pct_X: Any = None" in code
        assert "%X" not in code

    def test_regular_name_unchanged(self):
        """Regular variable names pass through unchanged."""
        routine = MRoutine(name="TEST")
        routine.routine_state_vars = {"MYVAR"}
        routine.array_vars = set()

        code = generate_routine_state_class(routine)

        assert "MYVAR: Any = None" in code


@pytest.mark.codegen
class TestRoutineStateIntegration:
    """Integration tests for RoutineState generation (T050, T054)."""

    def test_generated_class_is_valid_python(self):
        """Generated RoutineState class is syntactically valid Python."""
        routine = MRoutine(name="TEST")
        routine.routine_state_vars = {"X", "Y"}
        routine.array_vars = {"A"}

        imports = _STATE_IMPORTS
        class_code = generate_routine_state_class(routine)

        # Combine imports and class definition
        full_code = imports + "\n" + class_code

        # Should parse without syntax error
        import ast

        ast.parse(full_code)

    def test_generated_class_can_instantiate(self):
        """Generated RoutineState class can be instantiated."""
        routine = MRoutine(name="TEST")
        routine.routine_state_vars = {"X"}
        routine.array_vars = {"A"}

        imports = _STATE_IMPORTS
        class_code = generate_routine_state_class(routine)
        init_code = generate_state_initialization(routine)

        # Combine all parts
        full_code = imports + "\n" + class_code + "\n" + init_code

        # Execute and verify
        namespace = {}
        exec(full_code, namespace)

        state = namespace["state"]
        assert state.X is None
        assert hasattr(state, "A")

    def test_marray_field_has_correct_behavior(self):
        """MArray field in generated class has MUMPS array semantics."""
        from m2py.runtime import MArray

        routine = MRoutine(name="TEST")
        routine.routine_state_vars = set()
        routine.array_vars = {"ARR"}

        imports = _STATE_IMPORTS
        class_code = generate_routine_state_class(routine)
        init_code = generate_state_initialization(routine)

        # Combine all parts
        full_code = imports + "\n" + class_code + "\n" + init_code

        # Execute
        namespace = {"MArray": MArray}
        exec(full_code, namespace)

        state = namespace["state"]

        # MArray should have MUMPS semantics
        state.ARR[1] = 10
        state.ARR[1, 2] = 20

        assert state.ARR.get(1) == 10
        assert state.ARR.get(1, 2) == 20
        assert state.ARR.defined(1) == 11  # Has value AND children


@pytest.mark.codegen
class TestDynamicLocalsGeneration:
    """Tests for Spec 017: Dynamic locals for argumentless KILL/NEW support."""

    def test_routine_uses_dynamic_locals_false_by_default(self):
        """Routine without argumentless KILL/NEW uses static fields."""
        from m2py.codegen.shared_state import routine_uses_dynamic_locals

        routine = MRoutine(name="TEST")
        routine.has_argumentless_kill = False
        routine.has_argumentless_new = False

        assert routine_uses_dynamic_locals(routine) is False

    def test_routine_uses_dynamic_locals_with_argumentless_kill(self):
        """Routine with argumentless KILL needs dynamic locals."""
        from m2py.codegen.shared_state import routine_uses_dynamic_locals

        routine = MRoutine(name="TEST")
        routine.has_argumentless_kill = True
        routine.has_argumentless_new = False

        assert routine_uses_dynamic_locals(routine) is True

    def test_routine_uses_dynamic_locals_with_argumentless_new(self):
        """Routine with argumentless NEW needs dynamic locals."""
        from m2py.codegen.shared_state import routine_uses_dynamic_locals

        routine = MRoutine(name="TEST")
        routine.has_argumentless_kill = False
        routine.has_argumentless_new = True

        assert routine_uses_dynamic_locals(routine) is True

    def test_routine_uses_dynamic_locals_with_both(self):
        """Routine with both argumentless KILL and NEW needs dynamic locals."""
        from m2py.codegen.shared_state import routine_uses_dynamic_locals

        routine = MRoutine(name="TEST")
        routine.has_argumentless_kill = True
        routine.has_argumentless_new = True

        assert routine_uses_dynamic_locals(routine) is True

    def test_dynamic_state_class_has_locals_dict(self):
        """Dynamic RoutineState has _locals dict field."""
        routine = MRoutine(name="TEST")
        routine.has_argumentless_kill = True
        routine.has_argumentless_new = False
        routine.routine_state_vars = {"X"}  # Should be ignored
        routine.array_vars = set()

        code = generate_routine_state_class(routine)

        assert "@dataclass" in code
        assert "class RoutineState:" in code
        assert "_locals: dict = field(default_factory=dict)" in code

    def test_dynamic_state_class_has_new_stack(self):
        """Dynamic RoutineState has _new_stack list field for NEW."""
        routine = MRoutine(name="TEST")
        routine.has_argumentless_kill = False
        routine.has_argumentless_new = True
        routine.routine_state_vars = set()
        routine.array_vars = set()

        code = generate_routine_state_class(routine)

        assert "_new_stack: list = field(default_factory=list)" in code

    def test_dynamic_state_class_ignores_static_vars(self):
        """Dynamic RoutineState does not include static var fields."""
        routine = MRoutine(name="TEST")
        routine.has_argumentless_kill = True
        routine.has_argumentless_new = False
        routine.routine_state_vars = {"X", "Y", "Z"}
        routine.array_vars = {"A", "B"}

        code = generate_routine_state_class(routine)

        # Should NOT have static fields
        assert "X: Any" not in code
        assert "Y: Any" not in code
        assert "A: MArray" not in code
        # Should have dynamic fields only
        assert "_locals: dict" in code
        assert "_new_stack: list" in code

    def test_dynamic_state_class_is_valid_python(self):
        """Dynamic RoutineState class is syntactically valid Python."""
        routine = MRoutine(name="TEST")
        routine.has_argumentless_kill = True
        routine.has_argumentless_new = True
        routine.routine_state_vars = {"X"}
        routine.array_vars = {"A"}

        imports = _STATE_IMPORTS
        class_code = generate_routine_state_class(routine)

        # Combine imports and class definition
        full_code = imports + "\n" + class_code

        # Should parse without syntax error
        import ast

        ast.parse(full_code)

    def test_dynamic_state_class_can_instantiate(self):
        """Dynamic RoutineState class can be instantiated and used."""
        routine = MRoutine(name="TEST")
        routine.has_argumentless_kill = True
        routine.has_argumentless_new = True
        routine.routine_state_vars = set()
        routine.array_vars = set()

        imports = _STATE_IMPORTS
        class_code = generate_routine_state_class(routine)
        init_code = generate_state_initialization(routine)

        # Combine all parts
        full_code = imports + "\n" + class_code + "\n" + init_code

        # Execute and verify
        namespace = {}
        exec(full_code, namespace)

        state = namespace["state"]
        assert hasattr(state, "_locals")
        assert hasattr(state, "_new_stack")
        assert state._locals == {}
        assert state._new_stack == []

    def test_dynamic_locals_can_store_and_retrieve(self):
        """Dynamic _locals dict can store and retrieve variables."""
        routine = MRoutine(name="TEST")
        routine.has_argumentless_kill = True
        routine.has_argumentless_new = False
        routine.routine_state_vars = set()
        routine.array_vars = set()

        imports = _STATE_IMPORTS
        class_code = generate_routine_state_class(routine)
        init_code = generate_state_initialization(routine)

        # Combine and execute
        full_code = imports + "\n" + class_code + "\n" + init_code
        namespace = {}
        exec(full_code, namespace)

        state = namespace["state"]

        # Simulate SET X=1, SET Y=2
        state._locals["X"] = "1"
        state._locals["Y"] = "2"

        assert state._locals.get("X", "") == "1"
        assert state._locals.get("Y", "") == "2"
        assert state._locals.get("Z", "") == ""  # Undefined

    def test_dynamic_locals_clear_simulates_kill(self):
        """_locals.clear() simulates argumentless KILL."""
        routine = MRoutine(name="TEST")
        routine.has_argumentless_kill = True
        routine.has_argumentless_new = False
        routine.routine_state_vars = set()
        routine.array_vars = set()

        imports = _STATE_IMPORTS
        class_code = generate_routine_state_class(routine)
        init_code = generate_state_initialization(routine)

        # Combine and execute
        full_code = imports + "\n" + class_code + "\n" + init_code
        namespace = {}
        exec(full_code, namespace)

        state = namespace["state"]

        # Set up some variables
        state._locals["X"] = "1"
        state._locals["Y"] = "2"
        state._locals["Z"] = "3"

        # Simulate argumentless KILL
        state._locals.clear()

        # All variables should be gone
        assert state._locals.get("X", "") == ""
        assert state._locals.get("Y", "") == ""
        assert state._locals.get("Z", "") == ""
        assert len(state._locals) == 0

    def test_new_stack_push_pop_simulates_new(self):
        """_new_stack push/pop simulates argumentless NEW."""
        routine = MRoutine(name="TEST")
        routine.has_argumentless_kill = False
        routine.has_argumentless_new = True
        routine.routine_state_vars = set()
        routine.array_vars = set()

        imports = _STATE_IMPORTS
        class_code = generate_routine_state_class(routine)
        init_code = generate_state_initialization(routine)

        # Combine and execute
        full_code = imports + "\n" + class_code + "\n" + init_code
        namespace = {}
        exec(full_code, namespace)

        state = namespace["state"]

        # Set initial values
        state._locals["X"] = "original"
        state._locals["Y"] = "also_original"

        # Simulate argumentless NEW: push and clear
        state._new_stack.append(dict(state._locals))
        state._locals.clear()

        # Variables should be cleared
        assert state._locals.get("X", "") == ""
        assert state._locals.get("Y", "") == ""

        # Set new values in NEW scope
        state._locals["X"] = "new_value"
        state._locals["Z"] = "only_in_new_scope"

        # Simulate QUIT: pop and restore
        if state._new_stack:
            state._locals.clear()
            state._locals.update(state._new_stack.pop())

        # Original values should be restored
        assert state._locals.get("X", "") == "original"
        assert state._locals.get("Y", "") == "also_original"
        # Z should not exist (wasn't in original scope)
        assert state._locals.get("Z", "") == ""

    def test_nested_new_scopes(self):
        """Multiple nested argumentless NEW operations work correctly."""
        routine = MRoutine(name="TEST")
        routine.has_argumentless_kill = False
        routine.has_argumentless_new = True
        routine.routine_state_vars = set()
        routine.array_vars = set()

        imports = _STATE_IMPORTS
        class_code = generate_routine_state_class(routine)
        init_code = generate_state_initialization(routine)

        # Combine and execute
        full_code = imports + "\n" + class_code + "\n" + init_code
        namespace = {}
        exec(full_code, namespace)

        state = namespace["state"]

        # Set initial value
        state._locals["X"] = "level0"

        # First NEW (level 1)
        state._new_stack.append(dict(state._locals))
        state._locals.clear()
        state._locals["X"] = "level1"

        # Second NEW (level 2)
        state._new_stack.append(dict(state._locals))
        state._locals.clear()
        state._locals["X"] = "level2"

        assert state._locals.get("X", "") == "level2"
        assert len(state._new_stack) == 2

        # First QUIT (back to level 1)
        state._locals.clear()
        state._locals.update(state._new_stack.pop())
        assert state._locals.get("X", "") == "level1"
        assert len(state._new_stack) == 1

        # Second QUIT (back to level 0)
        state._locals.clear()
        state._locals.update(state._new_stack.pop())
        assert state._locals.get("X", "") == "level0"
        assert len(state._new_stack) == 0


@pytest.mark.codegen
class TestDynamicLocalsPaths:
    """Tests for code with argumentless KILL triggering dynamic_locals."""

    def test_set_with_argumentless_kill(self, execute_mumps):
        """SET in routine with argumentless KILL uses dynamic_locals."""
        result = execute_mumps("TEST\n\tK\n\tS X=1\n\tW X\n\tQ\n")
        assert result.output == "1"

    def test_kill_selective_in_dynamic_routine(self, execute_mumps):
        """Selective KILL in routine with argumentless KILL."""
        result = execute_mumps("TEST\n\tK\n\tS X=1,Y=2\n\tK X\n\tW $D(X),$D(Y)\n\tQ\n")
        assert "0" in result.output  # X killed
        assert "1" in result.output  # Y alive


@pytest.mark.codegen
class TestNewInDynamicRoutine:
    """Tests for NEW in routines with argumentless KILL/NEW."""

    def test_argumentless_new(self, execute_mumps):
        """Argumentless NEW in routine with argumentless KILL."""
        result = execute_mumps("TEST\n\tK\n\tS X=1\n\tN\n\tW $D(X)\n\tQ\n")
        assert result.output == "0"


# =============================================================================
# Indirect FOR loop variants
# =============================================================================


@pytest.mark.codegen
class TestIntrinsicsDynamicLocals:
    """Tests for intrinsic functions in routines with dynamic_locals."""

    def test_data_in_dynamic_routine(self, execute_mumps):
        """$D(X) in routine with argumentless KILL."""
        result = execute_mumps("TEST\n\tK\n\tS X=1\n\tW $D(X)\n\tQ\n")
        assert result.output == "1"

    def test_order_in_dynamic_routine(self, execute_mumps):
        """$O(X("")) in routine with argumentless KILL."""
        result = execute_mumps('TEST\n\tK\n\tS X(1)=1,X(3)=3\n\tW $O(X(""))\n\tQ\n')
        assert result.output == "1"


# =============================================================================
# SET argument indirection
# =============================================================================
