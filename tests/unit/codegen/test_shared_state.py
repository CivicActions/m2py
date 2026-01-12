"""Tests for RoutineState generation (Spec 006 Phase 4).

Tests the generation of RoutineState dataclass for cross-label variable visibility.
"""

import pytest

from m2py.asg.elements import MRoutine
from m2py.codegen.shared_state import (
    generate_routine_state_class,
    generate_state_imports,
    generate_state_initialization,
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
class TestGenerateStateImports:
    """Tests for generate_state_imports() function (T050)."""

    def test_includes_dataclass_imports(self):
        """Import statement includes dataclass and field."""
        code = generate_state_imports()

        assert "from dataclasses import dataclass, field" in code

    def test_includes_any_import(self):
        """Import statement includes Any type."""
        code = generate_state_imports()

        assert "from typing import Any" in code

    def test_includes_marray_import(self):
        """Import statement includes MArray from runtime."""
        code = generate_state_imports()

        assert "from m2py.runtime import MArray" in code


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

        imports = generate_state_imports()
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

        imports = generate_state_imports()
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

        imports = generate_state_imports()
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
