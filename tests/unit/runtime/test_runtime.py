"""Tests for MUMPSRuntime basic functionality.

Reference: Runtime API Contract (contracts/runtime-api.md)
"""

import pytest


@pytest.mark.runtime
class TestMUMPSRuntimeBasic:
    """Basic MUMPSRuntime functionality tests.

    Phase 10 validation: Verify core runtime API works correctly.
    """

    def test_write_and_get_output(self):
        """Runtime write() captures output and get_output() retrieves it."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt.write("Hello")
        rt.write(" ")
        rt.write("World")
        assert rt.get_output() == "Hello World"

    def test_clear_output(self):
        """Runtime clear() resets output buffer."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt.write("test")
        assert rt.get_output() == "test"
        rt.clear()
        assert rt.get_output() == ""

    def test_execute_simple_code(self):
        """Runtime execute() runs generated Python code."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        # Phase 13 (T076): Functions now require _rt as first parameter
        code = """
def TEST(_rt):
    global _test
    _rt.write("PASS")

_test = False
"""
        result = rt.execute(code)
        assert result.success is True
        assert result.output == "PASS"
        assert result.error is None

    def test_execute_captures_test_value(self):
        """Runtime execute() captures final $TEST value."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        # Phase 13 (T076): Functions now require _rt as first parameter
        code = """
def TEST(_rt):
    global _test
    _test = True

_test = False
"""
        result = rt.execute(code)
        assert result.success is True
        assert result.test_value is True

    def test_execute_handles_exceptions(self):
        """Runtime execute() captures exceptions and returns failure."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        # Phase 13 (T076): Functions now require _rt as first parameter
        code = """
def TEST(_rt):
    global _test
    raise ValueError("intentional error")

_test = False
"""
        result = rt.execute(code)
        assert result.success is False
        assert "intentional error" in result.error

    def test_execute_with_explicit_entry_point(self):
        """Runtime execute() can call specific entry point."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        # Phase 13 (T076): Functions now require _rt as first parameter
        code = """
def TEST(_rt):
    global _test
    _rt.write("FIRST")

def OTHER(_rt):
    global _test
    _rt.write("OTHER")

_test = False
"""
        result = rt.execute(code, entry_point="OTHER")
        assert result.success is True
        assert result.output == "OTHER"

    def test_execute_no_capture_output(self):
        """Runtime execute() with capture_output=False returns empty output."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        # Phase 13 (T076): Functions now require _rt as first parameter
        code = """
def TEST(_rt):
    global _test
    _rt.write("test")

_test = False
"""
        result = rt.execute(code, capture_output=False)
        assert result.success is True
        assert result.output == ""


@pytest.mark.runtime
class TestExecutionResult:
    """ExecutionResult dataclass tests."""

    def test_execution_result_fields(self):
        """ExecutionResult has correct fields."""
        from m2py.runtime import ExecutionResult

        result = ExecutionResult(
            output="hello",
            success=True,
            error=None,
            test_value=False,
        )
        assert result.output == "hello"
        assert result.success is True
        assert result.error is None
        assert result.test_value is False


@pytest.mark.runtime
class TestMArrayBasic:
    """Basic MArray functionality tests (T053).

    Spec 006: MUMPS arrays are sparse, hierarchical structures where
    each node can have BOTH a value AND children.
    """

    def test_root_value(self):
        """MArray stores value at root node.

        MUMPS: S A=1
        """
        from m2py.runtime import MArray

        arr = MArray()
        arr.value = 1
        assert arr.value == 1

    def test_undefined_returns_empty_string(self):
        """Undefined node returns empty string (MUMPS semantics)."""
        from m2py.runtime import MArray

        arr = MArray()
        assert arr.value == ""
        assert arr.get(1) == ""
        assert arr.get(1, 2) == ""

    def test_single_subscript_set_get(self):
        """MArray supports single subscript access.

        MUMPS: S A(1)=10
        """
        from m2py.runtime import MArray

        arr = MArray()
        arr[1] = 10
        assert arr.get(1) == 10

    def test_nested_subscript_set_get(self):
        """MArray supports nested subscript access.

        MUMPS: S A(1,2)=20
        """
        from m2py.runtime import MArray

        arr = MArray()
        arr[1, 2] = 20
        assert arr.get(1, 2) == 20

    def test_value_and_children_coexist(self):
        """Node can have both value AND children.

        MUMPS: S A=1, S A(1)=2
        Both A and A(1) have values simultaneously.
        """
        from m2py.runtime import MArray

        arr = MArray()
        arr.value = 1
        arr[1] = 2
        arr[1, 2] = 3

        assert arr.value == 1
        assert arr.get(1) == 2
        assert arr.get(1, 2) == 3


@pytest.mark.runtime
class TestMArrayDefined:
    """Tests for MArray.defined() - $DATA semantics (T053)."""

    def test_defined_empty(self):
        """Empty node returns 0."""
        from m2py.runtime import MArray

        arr = MArray()
        assert arr.defined() == 0

    def test_defined_value_only(self):
        """Node with value but no children returns 1."""
        from m2py.runtime import MArray

        arr = MArray()
        arr.value = 42
        assert arr.defined() == 1

    def test_defined_children_only(self):
        """Node with children but no value returns 10."""
        from m2py.runtime import MArray

        arr = MArray()
        arr[1] = 10  # Creates child, but root has no value
        assert arr.defined() == 10

    def test_defined_value_and_children(self):
        """Node with both value and children returns 11."""
        from m2py.runtime import MArray

        arr = MArray()
        arr.value = 1
        arr[1] = 2
        assert arr.defined() == 11

    def test_defined_with_subscripts(self):
        """defined() works with subscript path."""
        from m2py.runtime import MArray

        arr = MArray()
        arr[1, 2] = 3

        # Path that exists
        assert arr.defined(1) == 10  # Has children (2), no value
        assert arr.defined(1, 2) == 1  # Has value, no children

        # Path that doesn't exist
        assert arr.defined(99) == 0


@pytest.mark.runtime
class TestMArrayKill:
    """Tests for MArray.kill() - KILL command semantics (T053)."""

    def test_kill_entire_array(self):
        """kill() with no args clears entire array."""
        from m2py.runtime import MArray

        arr = MArray()
        arr.value = 1
        arr[1] = 2
        arr[1, 2] = 3

        arr.kill()

        assert arr.defined() == 0
        assert arr.get(1) == ""

    def test_kill_subscript(self):
        """kill(subscript) removes that node and descendants."""
        from m2py.runtime import MArray

        arr = MArray()
        arr[1] = 10
        arr[1, 2] = 20
        arr[2] = 30

        arr.kill(1)

        assert arr.get(1) == ""
        assert arr.get(1, 2) == ""
        assert arr.get(2) == 30  # Unaffected

    def test_kill_nonexistent(self):
        """kill() on nonexistent path does nothing."""
        from m2py.runtime import MArray

        arr = MArray()
        arr[1] = 10

        # Should not raise
        arr.kill(99)
        arr.kill(1, 99)

        assert arr.get(1) == 10


@pytest.mark.runtime
class TestMArrayOrder:
    """Tests for MArray.order() - $ORDER semantics (T053)."""

    def test_order_first_subscript(self):
        """order() with empty start returns first subscript."""
        from m2py.runtime import MArray

        arr = MArray()
        arr[1] = 10
        arr[2] = 20
        arr[3] = 30

        assert arr.order() == 1

    def test_order_next_subscript(self):
        """order(start=x) returns next subscript after x."""
        from m2py.runtime import MArray

        arr = MArray()
        arr[1] = 10
        arr[2] = 20
        arr[3] = 30

        assert arr.order(start=1) == 2
        assert arr.order(start=2) == 3

    def test_order_last_returns_empty(self):
        """order() past last subscript returns empty string."""
        from m2py.runtime import MArray

        arr = MArray()
        arr[1] = 10
        arr[2] = 20

        assert arr.order(start=2) == ""

    def test_order_empty_array(self):
        """order() on empty array returns empty string."""
        from m2py.runtime import MArray

        arr = MArray()
        assert arr.order() == ""

    def test_order_numbers_before_strings(self):
        """MUMPS collation: numbers sort before strings."""
        from m2py.runtime import MArray

        arr = MArray()
        arr["B"] = 1
        arr[1] = 2
        arr["A"] = 3
        arr[2] = 4

        # Numbers first (1, 2), then strings (A, B)
        assert arr.order() == 1
        assert arr.order(start=1) == 2
        assert arr.order(start=2) == "A"
        assert arr.order(start="A") == "B"
        assert arr.order(start="B") == ""

    def test_order_at_subscript_level(self):
        """order() works at nested subscript level."""
        from m2py.runtime import MArray

        arr = MArray()
        arr[1, "A"] = 1
        arr[1, "B"] = 2
        arr[1, "C"] = 3

        assert arr.order(1) == "A"
        assert arr.order(1, start="A") == "B"
        assert arr.order(1, start="B") == "C"

    def test_order_start_not_found_returns_next_greater(self):
        """order() with start not in array returns next greater key."""
        from m2py.runtime import MArray

        arr = MArray()
        arr[1] = 10
        arr[3] = 30
        arr[5] = 50

        # Start=2 not found, should return 3 (next greater)
        assert arr.order(start=2) == 3
        # Start=4 not found, should return 5
        assert arr.order(start=4) == 5
        # Start=6 not found, no greater keys, return ""
        assert arr.order(start=6) == ""

    def test_order_nested_path_not_found(self):
        """order() with invalid nested path returns empty string."""
        from m2py.runtime import MArray

        arr = MArray()
        arr[1, "A"] = 1

        # Path (2) doesn't exist
        assert arr.order(2) == ""


@pytest.mark.runtime
class TestMArrayMethods:
    """Tests for additional MArray methods (T053)."""

    def test_set_method(self):
        """set() method provides keyword-based value setting."""
        from m2py.runtime import MArray

        arr = MArray()
        arr.set(value=10)
        arr.set(1, value=20)
        arr.set(1, 2, value=30)

        assert arr.value == 10
        assert arr.get(1) == 20
        assert arr.get(1, 2) == 30

    def test_set_requires_value_keyword(self):
        """set() raises if value= not provided."""
        from m2py.runtime import MArray

        arr = MArray()
        with pytest.raises(ValueError, match="value="):
            arr.set(1)

    def test_getitem_creates_nodes(self):
        """arr[x] creates intermediate nodes if needed."""
        from m2py.runtime import MArray

        arr = MArray()
        node = arr[1, 2, 3]

        # Node should exist (was created)
        assert isinstance(node, MArray)
        # But have no value
        assert node.value == ""

    def test_repr(self):
        """__repr__ provides useful debug output."""
        from m2py.runtime import MArray

        arr = MArray()
        assert "MArray" in repr(arr)

        arr.value = 42
        assert "value=42" in repr(arr)

        arr[1] = 10
        assert "children" in repr(arr)


@pytest.mark.runtime
class TestRunWithGotoSupport:
    """Tests for run_with_goto_support() runtime helper.

    Spec 008 Phase 6: This function handles GotoExternal exceptions
    to implement external GOTO control transfer.
    """

    def test_normal_execution_returns_result(self):
        """When entry_func doesn't raise GotoExternal, returns normally."""
        from m2py.runtime import MUMPSRuntime, run_with_goto_support

        def simple_func(_rt, _scope=None):
            return "completed"

        _rt = MUMPSRuntime()
        result = run_with_goto_support(simple_func, _rt)
        assert result == "completed"

    def test_passes_scope_to_entry_func(self):
        """_scope is passed to entry function."""
        from m2py.runtime import MUMPSRuntime, run_with_goto_support

        received_scope = None

        def capture_scope(_rt, _scope=None):
            nonlocal received_scope
            received_scope = _scope
            return "done"

        _rt = MUMPSRuntime()
        my_scope = {"X": 42}
        run_with_goto_support(capture_scope, _rt, _scope=my_scope)
        assert received_scope is my_scope
        assert received_scope["X"] == 42

    def test_creates_empty_scope_if_none(self):
        """Creates empty _scope dict if None provided."""
        from m2py.runtime import MUMPSRuntime, run_with_goto_support

        received_scope = None

        def capture_scope(_rt, _scope=None):
            nonlocal received_scope
            received_scope = _scope
            return "done"

        _rt = MUMPSRuntime()
        run_with_goto_support(capture_scope, _rt, _scope=None)
        assert received_scope == {}

    def test_catches_goto_external_and_transfers(self):
        """GotoExternal is caught and control transfers to target."""
        import types

        from m2py.runtime import GotoExternal, MUMPSRuntime, run_with_goto_support

        # Create a mock module with entry function
        target_module = types.ModuleType("target_mod")
        target_module._routine_name = "target_mod"
        target_module._label_lines = {"target_mod": 0}

        call_count = 0

        def target_entry(_rt, _scope=None):
            nonlocal call_count
            call_count += 1
            return "transferred"

        target_module.target_mod = target_entry

        # Entry function that raises GotoExternal
        def source_func(_rt, _scope=None):
            raise GotoExternal(target_module, None, _rt=_rt)

        _rt = MUMPSRuntime()
        result = run_with_goto_support(source_func, _rt)
        assert result == "transferred"
        assert call_count == 1

    def test_transfers_to_specific_label(self):
        """GotoExternal with label transfers to that label's function."""
        import types

        from m2py.runtime import GotoExternal, MUMPSRuntime, run_with_goto_support

        target_module = types.ModuleType("target_mod")
        target_module._routine_name = "target_mod"
        target_module._label_lines = {"target_mod": 0, "HELPER": 5}

        def helper_func(_rt, _scope=None):
            return "at HELPER"

        target_module.HELPER = helper_func

        def source_func(_rt, _scope=None):
            raise GotoExternal(target_module, "HELPER", _rt=_rt)

        _rt = MUMPSRuntime()
        result = run_with_goto_support(source_func, _rt)
        assert result == "at HELPER"

    def test_raises_label_not_found_for_missing_label(self):
        """GotoExternal to non-existent label raises LabelNotFoundError."""
        import types

        from m2py.runtime import (
            GotoExternal,
            LabelNotFoundError,
            MUMPSRuntime,
            run_with_goto_support,
        )

        target_module = types.ModuleType("target_mod")
        target_module._routine_name = "target_mod"
        target_module._label_lines = {"target_mod": 0}

        def target_entry(_rt, _scope=None):
            return "entry"

        target_module.target_mod = target_entry

        def source_func(_rt, _scope=None):
            raise GotoExternal(target_module, "NONEXISTENT", _rt=_rt)

        _rt = MUMPSRuntime()
        with pytest.raises(LabelNotFoundError) as exc_info:
            run_with_goto_support(source_func, _rt)

        assert exc_info.value.label == "NONEXISTENT"
        assert exc_info.value.routine == "target_mod"
