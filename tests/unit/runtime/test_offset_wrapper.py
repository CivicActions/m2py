"""Unit tests for _create_offset_entry_wrapper factory function.

Tests the consolidated offset_wrapper factory that handles entry points
with line offsets within labels.

Phase 11 (US12): offset_wrapper Consolidation
"""

import types
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple
from unittest.mock import MagicMock, patch


from m2py.runtime import MArray, _create_offset_entry_wrapper, GotoExternal


# =============================================================================
# Test Fixtures - Mock Module and State Classes
# =============================================================================


@dataclass
class MockRoutineStateDynamic:
    """Mock state class with dynamic locals (uses _locals dict)."""

    _locals: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MockRoutineStateStatic:
    """Mock state class with static fields (dataclass fields)."""

    X: Optional[MArray] = None
    Y: Optional[MArray] = None
    Z: Optional[MArray] = None


def create_mock_module(
    routine_name: str = "TESTROUTINE",
    state_class: type = None,
    internal_func: callable = None,
    labels: Dict[str, callable] = None,
    line_map: Dict[int, Tuple[str, int]] = None,
) -> types.ModuleType:
    """Create a mock module for testing offset wrapper."""
    module = types.ModuleType(routine_name)
    module._routine_name = routine_name
    module._source_lines = ["line1", "line2", "line3"]
    module._label_lines = {"TEST": 0, "ENTRY": 1}

    if state_class:
        module.RoutineState = state_class

    if labels:
        module._labels = labels
    else:
        module._labels = {}

    if line_map:
        module._line_map = line_map
    else:
        module._line_map = {}

    return module


def create_mock_runtime():
    """Create a mock runtime object."""
    rt = MagicMock()
    rt._current_routine = None
    rt._current_source_lines = None
    rt._current_label_lines = None
    return rt


# =============================================================================
# Basic Factory Function Tests
# =============================================================================


class TestCreateOffsetEntryWrapperBasics:
    """Test basic factory function behavior."""

    def test_factory_returns_callable(self):
        """Factory should return a callable wrapper function."""
        module = create_mock_module(state_class=MockRoutineStateDynamic)

        def internal_func(_rt, state, _scope, _start_offset=0):
            return None, state

        wrapper = _create_offset_entry_wrapper(internal_func, 5, module)
        assert callable(wrapper)

    def test_wrapper_accepts_runtime_and_scope(self):
        """Wrapper should accept _rt and _scope parameters."""
        module = create_mock_module(state_class=MockRoutineStateDynamic)

        def internal_func(_rt, state, _scope, _start_offset=0):
            return None, state

        wrapper = _create_offset_entry_wrapper(internal_func, 5, module)
        rt = create_mock_runtime()

        # Should not raise
        result = wrapper(rt, _scope={})
        assert result is not None

    def test_wrapper_sets_runtime_context(self):
        """Wrapper should set _current_routine, _current_source_lines, _current_label_lines on runtime."""
        module = create_mock_module(
            routine_name="MYTEST", state_class=MockRoutineStateDynamic
        )

        def internal_func(_rt, state, _scope, _start_offset=0):
            return None, state

        wrapper = _create_offset_entry_wrapper(internal_func, 5, module)
        rt = create_mock_runtime()

        wrapper(rt, _scope={})

        assert rt._current_routine == "MYTEST"
        assert rt._current_source_lines == ["line1", "line2", "line3"]
        assert rt._current_label_lines == {"TEST": 0, "ENTRY": 1}


# =============================================================================
# Dynamic Locals Tests
# =============================================================================


class TestDynamicLocalsHandling:
    """Test handling of state classes with dynamic _locals dict."""

    def test_dynamic_scope_initialization_with_marray(self):
        """Should copy MArray values from scope to state._locals."""
        module = create_mock_module(state_class=MockRoutineStateDynamic)
        captured_state = {}

        def internal_func(_rt, state, _scope, _start_offset=0):
            captured_state["locals"] = dict(state._locals)
            return None, state

        wrapper = _create_offset_entry_wrapper(internal_func, 5, module)
        rt = create_mock_runtime()

        x_array = MArray()
        x_array.value = 42
        wrapper(rt, _scope={"X": x_array})

        assert "X" in captured_state["locals"]
        assert captured_state["locals"]["X"] is x_array

    def test_dynamic_scope_initialization_with_raw_value(self):
        """Should wrap raw values in MArray when copying to state._locals."""
        module = create_mock_module(state_class=MockRoutineStateDynamic)
        captured_state = {}

        def internal_func(_rt, state, _scope, _start_offset=0):
            captured_state["locals"] = dict(state._locals)
            return None, state

        wrapper = _create_offset_entry_wrapper(internal_func, 5, module)
        rt = create_mock_runtime()

        wrapper(rt, _scope={"X": 42})

        assert "X" in captured_state["locals"]
        assert isinstance(captured_state["locals"]["X"], MArray)
        assert captured_state["locals"]["X"].value == 42

    def test_dynamic_state_sync_back_to_scope(self):
        """Should sync state._locals back to scope on exit."""
        module = create_mock_module(state_class=MockRoutineStateDynamic)

        def internal_func(_rt, state, _scope, _start_offset=0):
            # Modify state
            y_array = MArray()
            y_array.value = 100
            state._locals["Y"] = y_array
            return None, state

        wrapper = _create_offset_entry_wrapper(internal_func, 5, module)
        rt = create_mock_runtime()
        scope = {}

        wrapper(rt, _scope=scope)

        assert "Y" in scope
        assert scope["Y"].value == 100


# =============================================================================
# Static Fields Tests
# =============================================================================


class TestStaticFieldsHandling:
    """Test handling of state classes with static dataclass fields."""

    def test_static_scope_initialization_with_marray(self):
        """Should copy MArray values from scope to state fields."""
        module = create_mock_module(state_class=MockRoutineStateStatic)
        captured_state = {}

        def internal_func(_rt, state, _scope, _start_offset=0):
            captured_state["X"] = state.X
            return None, state

        wrapper = _create_offset_entry_wrapper(
            internal_func, 5, module, use_dataclass_sync=True
        )
        rt = create_mock_runtime()

        x_array = MArray()
        x_array.value = 42
        wrapper(rt, _scope={"X": x_array})

        assert captured_state["X"] is x_array

    def test_static_state_sync_with_dataclass_fields(self):
        """Should sync state fields back to scope using __dataclass_fields__."""
        module = create_mock_module(state_class=MockRoutineStateStatic)

        def internal_func(_rt, state, _scope, _start_offset=0):
            y_array = MArray()
            y_array.value = 200
            state.Y = y_array
            return None, state

        wrapper = _create_offset_entry_wrapper(
            internal_func, 5, module, use_dataclass_sync=True
        )
        rt = create_mock_runtime()
        scope = {}

        wrapper(rt, _scope=scope)

        assert "Y" in scope
        assert scope["Y"].value == 200

    def test_static_state_sync_with_dir(self):
        """Should sync state fields back to scope using dir() when use_dataclass_sync=False."""
        module = create_mock_module(state_class=MockRoutineStateStatic)

        def internal_func(_rt, state, _scope, _start_offset=0):
            z_array = MArray()
            z_array.value = 300
            state.Z = z_array
            return None, state

        wrapper = _create_offset_entry_wrapper(
            internal_func, 5, module, use_dataclass_sync=False
        )
        rt = create_mock_runtime()
        scope = {}

        wrapper(rt, _scope=scope)

        assert "Z" in scope
        assert scope["Z"].value == 300


# =============================================================================
# Trampoline Tests
# =============================================================================


class TestTrampolineLoop:
    """Test the internal trampoline loop for GOTO handling."""

    def test_trampoline_follows_target(self):
        """Should follow target returned by internal function."""
        call_sequence = []

        def internal_func(_rt, state, _scope, _start_offset=0):
            call_sequence.append("internal")
            return "NEXT", state

        def next_func(_rt, state, _scope):
            call_sequence.append("next")
            return None, state

        module = create_mock_module(state_class=MockRoutineStateDynamic)
        module._labels = {"NEXT": next_func}

        wrapper = _create_offset_entry_wrapper(internal_func, 5, module)
        rt = create_mock_runtime()

        wrapper(rt, _scope={})

        assert call_sequence == ["internal", "next"]

    def test_trampoline_handles_line_map_target(self):
        """Should handle integer targets via _line_map."""
        call_sequence = []

        def internal_func(_rt, state, _scope, _start_offset=0):
            call_sequence.append(f"internal@{_start_offset}")
            return 10, state  # Return line number

        def line10_func(_rt, state, _scope, _start_offset=0):
            call_sequence.append(f"line10@{_start_offset}")
            return None, state

        module = create_mock_module(state_class=MockRoutineStateDynamic)
        module._line_map = {10: ("LINE10", 2)}
        module._LINE10 = line10_func

        wrapper = _create_offset_entry_wrapper(internal_func, 5, module)
        rt = create_mock_runtime()

        wrapper(rt, _scope={})

        assert call_sequence == ["internal@5", "line10@2"]


# =============================================================================
# GotoExternal Handling Tests
# =============================================================================


class TestGotoExternalHandling:
    """Test handling of GotoExternal exceptions."""

    def test_goto_external_syncs_state_before_transfer(self):
        """Should sync state to scope before handling external GOTO."""
        module = create_mock_module(state_class=MockRoutineStateDynamic)
        target_module = create_mock_module(
            routine_name="TARGET", state_class=MockRoutineStateDynamic
        )
        target_module.TARGET = lambda _rt, _scope=None: None

        def internal_func(_rt, state, _scope, _start_offset=0):
            # Set a variable before GOTO
            x_array = MArray()
            x_array.value = 999
            state._locals["X"] = x_array
            raise GotoExternal(target_module, "TARGET", None, _rt)

        wrapper = _create_offset_entry_wrapper(internal_func, 5, module)
        rt = create_mock_runtime()
        scope = {}

        with patch("m2py.runtime.run_with_goto_support"):
            with patch("m2py.runtime.resolve_goto_target"):
                wrapper(rt, _scope=scope)

        # State should be synced to scope
        assert "X" in scope
        assert scope["X"].value == 999

    def test_goto_external_in_trampoline_syncs_and_stops(self):
        """Should sync state and stop trampoline on GotoExternal."""
        call_sequence = []
        module = create_mock_module(state_class=MockRoutineStateDynamic)
        target_module = create_mock_module(
            routine_name="TARGET", state_class=MockRoutineStateDynamic
        )
        target_module.TARGET = lambda _rt, _scope=None: None

        def internal_func(_rt, state, _scope, _start_offset=0):
            call_sequence.append("internal")
            return "NEXT", state

        def next_func(_rt, state, _scope):
            call_sequence.append("next")
            raise GotoExternal(target_module, "TARGET", None, _rt)

        module._labels = {"NEXT": next_func}

        wrapper = _create_offset_entry_wrapper(internal_func, 5, module)
        rt = create_mock_runtime()

        with patch("m2py.runtime.run_with_goto_support"):
            with patch("m2py.runtime.resolve_goto_target"):
                wrapper(rt, _scope={})

        assert call_sequence == ["internal", "next"]


# =============================================================================
# Edge Cases
# =============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_scope(self):
        """Should handle empty scope dict."""
        module = create_mock_module(state_class=MockRoutineStateDynamic)

        def internal_func(_rt, state, _scope, _start_offset=0):
            return None, state

        wrapper = _create_offset_entry_wrapper(internal_func, 5, module)
        rt = create_mock_runtime()

        # Should not raise
        result = wrapper(rt, _scope={})
        assert result is not None

    def test_none_scope_defaults_to_empty_dict(self):
        """Should use empty dict when _scope is None."""
        module = create_mock_module(state_class=MockRoutineStateDynamic)

        def internal_func(_rt, state, _scope, _start_offset=0):
            return None, state

        wrapper = _create_offset_entry_wrapper(internal_func, 5, module)
        rt = create_mock_runtime()

        # Should not raise
        result = wrapper(rt, _scope=None)
        assert result is not None

    def test_no_state_class_calls_entry_directly(self):
        """Should call entry function directly if no RoutineState class."""
        module = create_mock_module()  # No state_class
        entry_called = []

        def entry_func(_rt, _scope=None):
            entry_called.append(True)
            return "entry_result"

        module.TESTROUTINE = entry_func

        def internal_func(_rt, state, _scope, _start_offset=0):
            return None, state

        wrapper = _create_offset_entry_wrapper(internal_func, 5, module)
        rt = create_mock_runtime()

        result = wrapper(rt, _scope={})

        assert entry_called == [True]
        assert result == "entry_result"

    def test_offset_passed_to_internal_function(self):
        """Should pass _start_offset parameter to internal function."""
        module = create_mock_module(state_class=MockRoutineStateDynamic)
        received_offset = []

        def internal_func(_rt, state, _scope, _start_offset=0):
            received_offset.append(_start_offset)
            return None, state

        wrapper = _create_offset_entry_wrapper(internal_func, 7, module)
        rt = create_mock_runtime()

        wrapper(rt, _scope={})

        assert received_offset == [7]
