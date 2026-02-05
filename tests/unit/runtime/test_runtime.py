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
        # T075b: Functions now receive _scope for cross-routine variable visibility
        code = """
def TEST(_rt, _scope=None, _start_offset=0):
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
        # T075b: Functions now receive _scope for cross-routine variable visibility
        code = """
def TEST(_rt, _scope=None, _start_offset=0):
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
        # T075b: Functions now receive _scope for cross-routine variable visibility
        code = """
def TEST(_rt, _scope=None, _start_offset=0):
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
        # T075b: Functions now receive _scope for cross-routine variable visibility
        code = """
def TEST(_rt, _scope=None, _start_offset=0):
    global _test
    _rt.write("FIRST")

def OTHER(_rt, _scope=None, _start_offset=0):
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
        # T075b: Functions now receive _scope for cross-routine variable visibility
        code = """
def TEST(_rt, _scope=None, _start_offset=0):
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
class TestMArrayMergeFrom:
    """Tests for MArray.merge_from() - MERGE command semantics."""

    def test_merge_from_copies_value(self):
        """merge_from() copies source value to destination."""
        from m2py.runtime import MArray

        source = MArray()
        source.value = 42

        dest = MArray()
        dest.merge_from(source)

        assert dest.value == 42

    def test_merge_from_copies_children(self):
        """merge_from() copies source children to destination."""
        from m2py.runtime import MArray

        source = MArray()
        source[1] = 10
        source[2] = 20

        dest = MArray()
        dest.merge_from(source)

        assert dest.get(1) == 10
        assert dest.get(2) == 20

    def test_merge_from_deep_copies_nested(self):
        """merge_from() deep copies nested children."""
        from m2py.runtime import MArray

        source = MArray()
        source[1, "A"] = "nested"
        source[1, "B"] = "also nested"

        dest = MArray()
        dest.merge_from(source)

        assert dest.get(1, "A") == "nested"
        assert dest.get(1, "B") == "also nested"

    def test_merge_from_preserves_existing_children(self):
        """merge_from() preserves existing destination children not in source."""
        from m2py.runtime import MArray

        source = MArray()
        source[1] = "new"

        dest = MArray()
        dest[2] = "existing"

        dest.merge_from(source)

        assert dest.get(1) == "new"
        assert dest.get(2) == "existing"

    def test_merge_from_overwrites_existing_value(self):
        """merge_from() overwrites destination value if source has value."""
        from m2py.runtime import MArray

        source = MArray()
        source.value = "source_value"

        dest = MArray()
        dest.value = "old_value"

        dest.merge_from(source)

        assert dest.value == "source_value"

    def test_merge_from_merges_overlapping_children(self):
        """merge_from() recursively merges overlapping children."""
        from m2py.runtime import MArray

        source = MArray()
        source[1, "A"] = "from_source"
        source[1, "B"] = "also_source"

        dest = MArray()
        dest[1, "A"] = "dest_existing"
        dest[1, "C"] = "dest_only"

        dest.merge_from(source)

        # Source values overwrite
        assert dest.get(1, "A") == "from_source"
        assert dest.get(1, "B") == "also_source"
        # Dest values preserved
        assert dest.get(1, "C") == "dest_only"

    def test_merge_from_no_source_value_preserves_dest_value(self):
        """merge_from() preserves dest value if source has no value."""
        from m2py.runtime import MArray

        source = MArray()
        source[1] = "child"  # source has children but no value

        dest = MArray()
        dest.value = "keep_this"

        dest.merge_from(source)

        # Value should be preserved since source._value is None
        assert dest.value == "keep_this"
        # Children should be merged
        assert dest.get(1) == "child"


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


@pytest.mark.runtime
class TestMUMPSRuntimeTextMethod:
    """Tests for MUMPSRuntime.get_text() method ($TEXT implementation)."""

    def test_text_plus_zero_returns_routine_name(self):
        """$TEXT(+0) returns the current routine name."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt._current_routine = "TESTRTN"
        # get_text(offset=0, label=None) should return routine name
        assert rt.get_text(0) == "TESTRTN"

    def test_text_plus_zero_external_module(self):
        """$TEXT(+0^ROUTINE) returns external module's routine name."""
        import types

        from m2py.runtime import MUMPSRuntime

        target_module = types.ModuleType("EXTERNAL")
        target_module._routine_name = "EXTERNAL"
        target_module._source_lines = []
        target_module._label_lines = {}

        rt = MUMPSRuntime()
        assert rt.get_text(0, module=target_module) == "EXTERNAL"

    def test_text_negative_offset_returns_empty(self):
        """$TEXT with negative offset returns empty string."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt._current_source_lines = ["TEST W 1 Q", "NEXT W 2 Q"]
        assert rt.get_text(-1) == ""

    def test_text_returns_source_line(self):
        """$TEXT(+n) returns nth source line."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt._current_source_lines = ["TEST W 1 Q", "NEXT W 2 Q", "END Q"]
        # +1 returns first line (1-based indexing)
        assert rt.get_text(1) == "TEST W 1 Q"
        assert rt.get_text(2) == "NEXT W 2 Q"
        assert rt.get_text(3) == "END Q"

    def test_text_out_of_bounds_returns_empty(self):
        """$TEXT with out-of-bounds offset returns empty string."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt._current_source_lines = ["TEST W 1 Q"]
        assert rt.get_text(2) == ""  # Beyond end
        assert rt.get_text(100) == ""

    def test_text_with_label_and_offset(self):
        """$TEXT(LABEL+n) returns line relative to label."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt._current_source_lines = ["TEST W 1 Q", "HELPER W 2 Q", " W 3 Q"]
        rt._current_label_lines = {"TEST": 0, "HELPER": 1}
        # HELPER+0 returns HELPER line
        assert rt.get_text(0, label="HELPER") == "HELPER W 2 Q"
        # HELPER+1 returns next line
        assert rt.get_text(1, label="HELPER") == " W 3 Q"

    def test_text_with_nonexistent_label_returns_empty(self):
        """$TEXT with non-existent label returns empty string."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt._current_source_lines = ["TEST W 1 Q"]
        rt._current_label_lines = {"TEST": 0}
        assert rt.get_text(0, label="NONEXISTENT") == ""

    def test_text_from_external_module_source(self):
        """$TEXT from external module returns that module's source lines."""
        import types

        from m2py.runtime import MUMPSRuntime

        target_module = types.ModuleType("EXTERNAL")
        target_module._routine_name = "EXTERNAL"
        target_module._source_lines = ["EXT W 'external' Q", "EXT2 W 'line2' Q"]
        target_module._label_lines = {"EXT": 0, "EXT2": 1}

        rt = MUMPSRuntime()
        assert rt.get_text(1, module=target_module) == "EXT W 'external' Q"
        assert rt.get_text(2, module=target_module) == "EXT2 W 'line2' Q"
        assert rt.get_text(0, label="EXT2", module=target_module) == "EXT2 W 'line2' Q"

    def test_text_converts_tabs_to_spaces(self):
        """$TEXT converts tabs to single space (YDB behavior).

        T075f: MUMPS/YDB converts tabs in source lines to single spaces
        when returning $TEXT values.
        """
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        # Source with tabs
        rt._current_source_lines = ["TEST\tW 'hello' Q", "NEXT\t\tW 'world' Q"]
        rt._current_label_lines = {"TEST": 0, "NEXT": 1}

        # Tabs should be converted to single spaces
        assert rt.get_text(1) == "TEST W 'hello' Q"
        assert rt.get_text(2) == "NEXT  W 'world' Q"  # Two tabs -> two spaces


@pytest.mark.runtime
class TestZWriteFormatting:
    """Tests for ZWRITE value and subscript formatting.

    Spec 017 Phase 7: ZWRITE output formatting fixes.
    These tests verify correct MUMPS ZWRITE semantics:
    - Numeric subscripts are unquoted and expanded (1E+11 → 100000000000)
    - String subscripts are quoted (even if they look like numbers without E+/E-)
    - Numeric values are unquoted (even if stored as strings)
    - Non-numeric string values are quoted
    """

    def test_format_subscript_integer(self):
        """Integer subscripts are unquoted."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt._format_subscript("123") == "123"
        assert rt._format_subscript("-456") == "-456"
        assert rt._format_subscript("0") == "0"

    def test_format_subscript_decimal(self):
        """Decimal subscripts are unquoted."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt._format_subscript(".5") == ".5"
        assert rt._format_subscript("-.123") == "-.123"
        assert rt._format_subscript("3.14159") == "3.14159"

    def test_format_subscript_scientific_with_sign(self):
        """Scientific notation with E+/E- (from Decimal) is expanded."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        # These represent numeric subscripts (from str(Decimal(...)))
        assert rt._format_subscript("1E+11") == "100000000000"
        assert rt._format_subscript("1E-2") == ".01"
        assert rt._format_subscript("-1E+3") == "-1000"

    def test_format_subscript_scientific_without_sign(self):
        """Scientific notation without +/- is a string subscript (quoted)."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        # These represent string literals (user wrote "1E60" in quotes)
        assert rt._format_subscript("1E60") == '"1E60"'
        assert rt._format_subscript("1E11") == '"1E11"'

    def test_format_subscript_string(self):
        """Non-numeric strings are quoted."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt._format_subscript("hello") == '"hello"'
        assert rt._format_subscript("A") == '"A"'
        assert rt._format_subscript("test123") == '"test123"'

    def test_format_subscript_string_with_quotes(self):
        """Strings containing quotes are escaped."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt._format_subscript('say "hi"') == '"say ""hi"""'

    def test_quote_value_numeric(self):
        """Numeric-looking values are unquoted."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt._quote_value("123") == "123"
        assert rt._quote_value("-456") == "-456"
        assert rt._quote_value(".5") == ".5"

    def test_quote_value_scientific_with_sign(self):
        """Scientific notation values with E+/E- are expanded (not quoted)."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt._quote_value("1E+11") == "100000000000"
        assert rt._quote_value("1E-2") == ".01"

    def test_quote_value_non_numeric(self):
        """Non-numeric strings are quoted."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt._quote_value("hello") == '"hello"'
        assert rt._quote_value("A") == '"A"'

    def test_quote_value_empty(self):
        """Empty strings and None are quoted as empty string."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        assert rt._quote_value("") == '""'
        assert rt._quote_value(None) == '""'

    def test_zwrite_global_subscript_formatting(self):
        """ZWRITE globals formats subscripts correctly."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        # Set a global with numeric subscript that stores as "1E+11"
        rt.globals.set("f", ("1E+11",), "1E11")

        # ZWRITE should expand the subscript to full number
        rt.zwrite_global("f", ())
        output = rt.get_output()
        assert "^f(100000000000)=" in output

    def test_zwrite_global_string_subscript_preserved(self):
        """ZWRITE preserves string subscripts that look like numbers."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        # Set a global with string subscript "1E60" (no +/- in exponent)
        rt.globals.set("x", ("1E60", "1"), "23")

        rt.zwrite_global("x", ())
        output = rt.get_output()
        # String subscript should be quoted
        assert '^x("1E60",1)=23' in output

    def test_zwrite_local_collation_order_with_decimals(self):
        """ZWRITE outputs subscripts in MUMPS collation order (numerics sorted numerically).

        T091: This test verifies that ZWRITE sorts subscripts using MUMPS collation:
        - Numerics before strings
        - Numerics sorted numerically (0 < .0005 < .001 < 1)

        This reproduces the basic/locals test failure where subscripts like:
        A(0), A(.0005), A(.001), A(1)
        Were being sorted as strings (A(.0005), A(.001), A(0), A(1)) instead of
        numerically (A(0), A(.0005), A(.001), A(1)).
        """
        from m2py.runtime import MUMPSRuntime, MArray

        rt = MUMPSRuntime()
        # Create an MArray with decimal subscripts - add in non-sorted order
        A = MArray()
        A[".0005"].value = "A(.0005)"  # Would sort first as string
        A["0"].value = "A(0)"  # Should sort first numerically
        A[".001"].value = "A(.001)"
        A["1"].value = "A(1)"
        A["1.0005"].value = "A(1.0005)"
        A["2"].value = "A(2)"

        # Use the internal method to test - pass as local scope
        # zwrite_local expects Python-translated name and tuple of subscripts
        rt.zwrite_local("A", (), {"A": A})
        output = rt.get_output()

        # Verify output order is MUMPS collation (numerics sorted numerically)
        lines = [line for line in output.strip().split("\n") if line]
        assert len(lines) == 6, f"Expected 6 lines, got: {lines}"

        # Expected order: 0, .0005, .001, 1, 1.0005, 2
        assert 'A(0)="A(0)"' in lines[0], f"First should be A(0), got: {lines[0]}"
        assert 'A(.0005)="A(.0005)"' in lines[1], (
            f"Second should be A(.0005), got: {lines[1]}"
        )
        assert 'A(.001)="A(.001)"' in lines[2], (
            f"Third should be A(.001), got: {lines[2]}"
        )
        assert 'A(1)="A(1)"' in lines[3], f"Fourth should be A(1), got: {lines[3]}"
        assert 'A(1.0005)="A(1.0005)"' in lines[4], (
            f"Fifth should be A(1.0005), got: {lines[4]}"
        )
        assert 'A(2)="A(2)"' in lines[5], f"Sixth should be A(2), got: {lines[5]}"


@pytest.mark.runtime
class TestGetOrderMethod:
    """Tests for MUMPSRuntime.get_order() - $ORDER with indirection support.

    T075b: Added get_order() method to support $O(@X) indirection patterns.
    This method resolves variable names at runtime and performs $ORDER.
    """

    def test_get_order_local_array_first(self):
        """get_order("A(\"\")", _scope) returns first subscript."""
        from m2py.runtime import MUMPSRuntime, MArray

        rt = MUMPSRuntime()
        arr = MArray()
        arr[1] = "one"
        arr[2] = "two"
        arr[3] = "three"
        _scope = {"A": arr}

        result = rt.get_order('A("")', _scope, 1)
        assert result == "1"

    def test_get_order_local_array_next(self):
        """get_order("A(1)", _scope) returns next subscript after 1."""
        from m2py.runtime import MUMPSRuntime, MArray

        rt = MUMPSRuntime()
        arr = MArray()
        arr[1] = "one"
        arr[2] = "two"
        _scope = {"A": arr}

        result = rt.get_order("A(1)", _scope, 1)
        assert result == "2"

    def test_get_order_local_array_last(self):
        """get_order at last subscript returns empty string."""
        from m2py.runtime import MUMPSRuntime, MArray

        rt = MUMPSRuntime()
        arr = MArray()
        arr[1] = "one"
        _scope = {"A": arr}

        result = rt.get_order("A(1)", _scope, 1)
        assert result == ""

    def test_get_order_local_array_reverse(self):
        """get_order with direction -1 returns previous subscript."""
        from m2py.runtime import MUMPSRuntime, MArray

        rt = MUMPSRuntime()
        arr = MArray()
        arr[1] = "one"
        arr[2] = "two"
        arr[3] = "three"
        _scope = {"A": arr}

        result = rt.get_order("A(2)", _scope, -1)
        assert result == "1"

    def test_get_order_undefined_array(self):
        """get_order on undefined variable returns empty string."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        _scope = {}

        result = rt.get_order('UNDEF("")', _scope, 1)
        assert result == ""

    def test_get_order_non_array_returns_empty(self):
        """get_order on non-array variable returns empty string."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        _scope = {"X": "scalar"}

        result = rt.get_order('X("")', _scope, 1)
        assert result == ""

    def test_get_order_global_array(self):
        """get_order("^G(\"\")", _scope) works for globals."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt.globals.set("G", ("1",), "value1")
        rt.globals.set("G", ("2",), "value2")
        _scope = {}

        result = rt.get_order('^G("")', _scope, 1)
        assert result == "1"

    def test_get_order_global_next_subscript(self):
        """get_order on global returns next subscript."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt.globals.set("G", ("A",), "a")
        rt.globals.set("G", ("B",), "b")
        _scope = {}

        result = rt.get_order('^G("A")', _scope, 1)
        assert result == "B"

    def test_get_order_empty_name_returns_empty(self):
        """get_order with empty name returns empty string."""
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        _scope = {}

        result = rt.get_order("", _scope, 1)
        assert result == ""

    def test_get_order_numeric_collation(self):
        """get_order respects MUMPS numeric collation."""
        from m2py.runtime import MUMPSRuntime, MArray

        rt = MUMPSRuntime()
        arr = MArray()
        arr["1"] = "one"
        arr["10"] = "ten"
        arr["2"] = "two"
        _scope = {"A": arr}

        # Numeric collation: 1 < 2 < 10
        result = rt.get_order("A(1)", _scope, 1)
        assert result == "2"
        result = rt.get_order("A(2)", _scope, 1)
        assert result == "10"

    # -------------------------------------------------------------------------
    # V1IDNM3 Edge Cases: Nested indirection, naked refs, subscript evaluation
    # -------------------------------------------------------------------------

    def test_get_order_nested_indirection(self):
        """get_order resolves nested indirection (@name) before $ORDER.

        When name starts with @, resolve_nested_indirection is called first
        to get the actual variable name string, then $ORDER is performed.
        """
        from m2py.runtime import MUMPSRuntime, MArray

        rt = MUMPSRuntime()
        arr = MArray()
        arr[1] = "one"
        arr[2] = "two"
        arr[3] = "three"
        ref = MArray()
        ref.value = "A(1)"  # @REF resolves to "A(1)"
        _scope = {"A": arr, "REF": ref}

        # @REF should resolve to A(1), then $O returns next subscript
        result = rt.get_order("@REF", _scope, 1)
        assert result == "2"

    def test_get_order_nested_indirection_empty_resolution(self):
        """get_order returns empty when nested indirection resolves to empty."""
        from m2py.runtime import MUMPSRuntime, MArray

        rt = MUMPSRuntime()
        ref = MArray()
        ref.value = ""  # Empty target
        _scope = {"REF": ref}

        result = rt.get_order("@REF", _scope, 1)
        assert result == ""

    def test_get_order_naked_global_reference(self):
        """get_order handles naked global references ^(subs).

        When the global name is just "^", resolve_naked() is called to get
        the actual global name from the naked indicator.

        The naked indicator is set to the parent level of the last access,
        so ^(sub) appends 'sub' to that parent level.
        """
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        # Set up globals with nested subscripts
        rt.globals.set("G", ("X", "1"), "x1")
        rt.globals.set("G", ("X", "2"), "x2")
        rt.globals.set("G", ("X", "3"), "x3")
        _scope = {}

        # Access ^G(X,1) - sets naked indicator to G with parent subs ("X",)
        rt.get_var('^G("X",1)', _scope)
        # Now ^(1) appends "1" to parent ("X",) giving ^G("X","1")
        # $O(^G("X","1")) should return "2" (next subscript after 1)
        result = rt.get_order("^(1)", _scope, 1)
        assert result == "2"

    def test_get_order_naked_global_first(self):
        """get_order with naked reference from empty subscript.

        When naked indicator's parent is empty (top level access), ^("")
        starts $ORDER from the beginning of the global.
        """
        from m2py.runtime import MUMPSRuntime

        rt = MUMPSRuntime()
        rt.globals.set("G", ("1",), "one")
        rt.globals.set("G", ("2",), "two")
        _scope = {}

        # Access ^G(1) - sets naked indicator to G with parent subs ()
        rt.get_var("^G(1)", _scope)
        # ^("") appends "" to parent () giving ^G("") - first subscript
        result = rt.get_order('^("")', _scope, 1)
        assert result == "1"

    def test_get_order_subscript_evaluation_with_varref(self):
        """get_order evaluates VarRef subscripts to their actual values.

        When subscripts contain variable references, _evaluate_subscripts
        resolves them to actual values before performing $ORDER.
        """
        from m2py.runtime import MUMPSRuntime, MArray

        rt = MUMPSRuntime()
        arr = MArray()
        arr[10, 1] = "one"
        arr[10, 2] = "two"
        arr[10, 3] = "three"
        idx = MArray()
        idx.value = 10
        _scope = {"A": arr, "I": idx}

        # This tests that subscript "10" string form works
        # The VarRef resolution happens before get_order is called
        result = rt.get_order("A(10,1)", _scope, 1)
        assert result == "2"


@pytest.mark.runtime
class TestResolveGotoTarget:
    """Tests for resolve_goto_target() function.

    resolve_goto_target extracts the target function from a GotoExternal
    exception, handling:
    - G ^ROUTINE: Entry label (routine name)
    - G LABEL^ROUTINE: Specific label
    - G LABEL+N^ROUTINE: Label with offset (uses _line_map)
    """

    def test_resolve_goto_routine_only(self):
        """G ^ROUTINE resolves to routine entry function."""
        from m2py.runtime import GotoExternal, resolve_goto_target
        import types

        # Create mock module with entry function
        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._label_lines = {"TESTRTN": 0}
        module._line_map = {1: ("TESTRTN", 0)}

        def entry_func(_rt, _scope=None):
            pass

        module.TESTRTN = entry_func

        goto = GotoExternal(module=module, label=None, offset=None)
        result = resolve_goto_target(goto)

        assert result is entry_func

    def test_resolve_goto_label(self):
        """G LABEL^ROUTINE resolves to specific label function."""
        from m2py.runtime import GotoExternal, resolve_goto_target
        import types

        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._label_lines = {"TESTRTN": 0, "SUB": 5}
        module._line_map = {1: ("TESTRTN", 0), 6: ("SUB", 0)}

        def sub_func(_rt, _scope=None):
            pass

        module.SUB = sub_func

        goto = GotoExternal(module=module, label="SUB", offset=None)
        result = resolve_goto_target(goto)

        assert result is sub_func

    def test_resolve_goto_numeric_label(self):
        """G 0012^ROUTINE resolves numeric label using translate_name."""
        from m2py.runtime import GotoExternal, resolve_goto_target
        import types

        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._label_lines = {"TESTRTN": 0, "0012": 10}
        module._line_map = {1: ("TESTRTN", 0), 11: ("_n_0012", 0)}

        def numeric_func(_rt, _scope=None):
            pass

        # Python function name is translated from "0012" to "_n_0012"
        module._n_0012 = numeric_func

        goto = GotoExternal(module=module, label="0012", offset=None)
        result = resolve_goto_target(goto)

        assert result is numeric_func

    def test_resolve_goto_percent_label(self):
        """G %FOO^ROUTINE resolves percent-prefixed label."""
        from m2py.runtime import GotoExternal, resolve_goto_target
        import types

        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._label_lines = {"TESTRTN": 0, "%FOO": 5}
        module._line_map = {1: ("TESTRTN", 0), 6: ("_pct_FOO", 0)}

        def pct_func(_rt, _scope=None):
            pass

        # Python function name is translated from "%FOO" to "_pct_FOO"
        module._pct_FOO = pct_func

        goto = GotoExternal(module=module, label="%FOO", offset=None)
        result = resolve_goto_target(goto)

        assert result is pct_func

    def test_resolve_goto_label_not_found_raises(self):
        """G NOTEXIST^ROUTINE raises LabelNotFoundError."""
        from m2py.runtime import GotoExternal, resolve_goto_target, LabelNotFoundError
        import types

        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._label_lines = {"TESTRTN": 0}
        module._line_map = {1: ("TESTRTN", 0)}

        def entry_func(_rt, _scope=None):
            pass

        module.TESTRTN = entry_func

        goto = GotoExternal(module=module, label="NOTEXIST", offset=None)

        with pytest.raises(LabelNotFoundError):
            resolve_goto_target(goto)

    def test_resolve_goto_with_offset_zero(self):
        """G LABEL+0^ROUTINE resolves to label start (offset 0)."""
        from m2py.runtime import GotoExternal, resolve_goto_target
        import types

        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._label_lines = {"TESTRTN": 0, "SUB": 5}
        module._line_map = {1: ("TESTRTN", 0), 6: ("SUB", 0), 7: ("SUB", 1)}

        def sub_func(_rt, _scope=None):
            pass

        module.SUB = sub_func

        goto = GotoExternal(module=module, label="SUB", offset=0)
        result = resolve_goto_target(goto)

        assert result is sub_func

    def test_resolve_goto_with_positive_offset(self):
        """G LABEL+N^ROUTINE creates offset_wrapper for N>0."""
        from m2py.runtime import GotoExternal, resolve_goto_target
        import types

        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._source_lines = ["TESTRTN", " W 1", " W 2", " Q"]
        module._label_lines = {"TESTRTN": 0}
        # _line_map maps 1-based line numbers to (label, offset)
        module._line_map = {
            1: ("TESTRTN", 0),
            2: ("TESTRTN", 1),
            3: ("TESTRTN", 2),
            4: ("TESTRTN", 3),
        }

        def internal_func(_rt, state, _scope, _start_offset=0):
            return (None, state)

        module._TESTRTN = internal_func
        module.TESTRTN = lambda _rt, _scope=None: None

        # G TESTRTN+2^TESTRTN should create an offset_wrapper
        # label_lines["TESTRTN"] = 0 (0-indexed)
        # target_line = 0 + 2 + 1 = 3 (1-indexed)
        # _line_map[3] = ("TESTRTN", 2)
        goto = GotoExternal(module=module, label="TESTRTN", offset=2)
        result = resolve_goto_target(goto)

        # Result should be a wrapper function (not the original)
        assert result is not module.TESTRTN
        assert callable(result)
        # The wrapper has a docstring indicating it's an offset wrapper
        assert "offset" in result.__doc__.lower()


@pytest.mark.runtime
class TestCallExternalWithOffset:
    """Tests for call_external_with_offset() runtime helper.

    This helper handles calling external routines at a specific offset
    (D LABEL+N^ROUTINE). It properly initializes state from _scope,
    calls the internal function, runs the trampoline if needed, and
    syncs state changes back to _scope.
    """

    def test_basic_call_with_offset(self):
        """call_external_with_offset calls internal function with offset."""
        import types
        from dataclasses import dataclass, field

        from m2py.runtime import MArray, MUMPSRuntime, call_external_with_offset

        # Create a mock module with TRAMPOLINE-style internal function
        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._source_lines = ["TESTRTN", " W 1", " W 2", " Q"]
        module._label_lines = {"TESTRTN": 0}
        module._line_map = {1: ("TESTRTN", 0), 2: ("TESTRTN", 1)}
        module._labels = {}

        @dataclass
        class RoutineState:
            X: MArray = field(default_factory=MArray)

        module.RoutineState = RoutineState

        received_offset = None

        def internal_func(_rt, state, _scope, _start_offset=0):
            nonlocal received_offset
            received_offset = _start_offset
            return (None, state)

        module._TESTRTN = internal_func
        module._labels["TESTRTN"] = internal_func

        _rt = MUMPSRuntime()
        _scope = {}

        call_external_with_offset(module, "TESTRTN", 1, _rt, _scope)

        assert received_offset == 1

    def test_initializes_state_from_scope(self):
        """call_external_with_offset initializes state from _scope."""
        import types
        from dataclasses import dataclass, field

        from m2py.runtime import MArray, MUMPSRuntime, call_external_with_offset

        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._source_lines = ["TESTRTN"]
        module._label_lines = {"TESTRTN": 0}
        module._line_map = {1: ("TESTRTN", 0)}
        module._labels = {}

        @dataclass
        class RoutineState:
            X: MArray = field(default_factory=MArray)

        module.RoutineState = RoutineState

        received_state = None

        def internal_func(_rt, state, _scope, _start_offset=0):
            nonlocal received_state
            received_state = state
            return (None, state)

        module._TESTRTN = internal_func
        module._labels["TESTRTN"] = internal_func

        _rt = MUMPSRuntime()
        x_arr = MArray()
        x_arr.value = 42
        _scope = {"X": x_arr}

        call_external_with_offset(module, "TESTRTN", 0, _rt, _scope)

        # State should have been initialized from scope
        assert received_state is not None
        assert received_state.X.value == 42

    def test_syncs_state_changes_back_to_scope(self):
        """call_external_with_offset syncs state changes back to _scope."""
        import types
        from dataclasses import dataclass, field

        from m2py.runtime import MArray, MUMPSRuntime, call_external_with_offset

        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._source_lines = ["TESTRTN"]
        module._label_lines = {"TESTRTN": 0}
        module._line_map = {1: ("TESTRTN", 0)}
        module._labels = {}

        @dataclass
        class RoutineState:
            X: MArray = field(default_factory=MArray)
            Y: MArray = field(default_factory=MArray)

        module.RoutineState = RoutineState

        def internal_func(_rt, state, _scope, _start_offset=0):
            # Modify state during execution
            state.X.value = 100
            state.Y.value = "modified"
            return (None, state)

        module._TESTRTN = internal_func
        module._labels["TESTRTN"] = internal_func

        _rt = MUMPSRuntime()
        _scope = {}

        call_external_with_offset(module, "TESTRTN", 0, _rt, _scope)

        # Changes should be synced back to _scope
        assert "X" in _scope
        assert "Y" in _scope
        # Check the values - may be raw or wrapped in MArray
        x_val = _scope["X"].value if isinstance(_scope["X"], MArray) else _scope["X"]
        y_val = _scope["Y"].value if isinstance(_scope["Y"], MArray) else _scope["Y"]
        assert x_val == 100
        assert y_val == "modified"

    def test_follows_trampoline_transitions(self):
        """call_external_with_offset follows trampoline when function returns target."""
        import types
        from dataclasses import dataclass, field

        from m2py.runtime import MUMPSRuntime, call_external_with_offset

        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._source_lines = ["TESTRTN", "NEXT"]
        module._label_lines = {"TESTRTN": 0, "NEXT": 1}
        module._line_map = {1: ("TESTRTN", 0), 2: ("NEXT", 0)}

        @dataclass
        class RoutineState:
            _visited: list = field(default_factory=list)

        module.RoutineState = RoutineState

        call_sequence = []

        def testrtn_func(_rt, state, _scope, _start_offset=0):
            call_sequence.append("TESTRTN")
            return ("NEXT", state)  # Transition to NEXT

        def next_func(_rt, state, _scope, _start_offset=0):
            call_sequence.append("NEXT")
            return (None, state)  # End

        module._TESTRTN = testrtn_func
        module._NEXT = next_func
        module._labels = {"TESTRTN": testrtn_func, "NEXT": next_func}

        _rt = MUMPSRuntime()
        _scope = {}

        call_external_with_offset(module, "TESTRTN", 0, _rt, _scope)

        # Should have followed the trampoline transition
        assert call_sequence == ["TESTRTN", "NEXT"]

    def test_handles_dynamic_locals_state(self):
        """call_external_with_offset handles dynamic _locals dict in state."""
        import types

        from m2py.runtime import MArray, MUMPSRuntime, call_external_with_offset

        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._source_lines = ["TESTRTN"]
        module._label_lines = {"TESTRTN": 0}
        module._line_map = {1: ("TESTRTN", 0)}
        module._labels = {}

        # Dynamic state with _locals dict
        class DynamicRoutineState:
            def __init__(self):
                self._locals = {}

        module.RoutineState = DynamicRoutineState

        received_state = None

        def internal_func(_rt, state, _scope, _start_offset=0):
            nonlocal received_state
            received_state = state
            # Modify via _locals dict
            state._locals["NEWVAR"] = MArray()
            state._locals["NEWVAR"].value = "dynamic"
            return (None, state)

        module._TESTRTN = internal_func
        module._labels["TESTRTN"] = internal_func

        _rt = MUMPSRuntime()
        x_arr = MArray()
        x_arr.value = 42
        _scope = {"X": x_arr}

        call_external_with_offset(module, "TESTRTN", 0, _rt, _scope)

        # X should have been initialized from scope
        assert "X" in received_state._locals
        # NEWVAR should be synced back to scope
        assert "NEWVAR" in _scope

    def test_restores_runtime_context(self):
        """call_external_with_offset saves and restores runtime context."""
        import types
        from dataclasses import dataclass

        from m2py.runtime import MUMPSRuntime, call_external_with_offset

        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._source_lines = ["TESTRTN W 1 Q"]
        module._label_lines = {"TESTRTN": 0}
        module._line_map = {1: ("TESTRTN", 0)}
        module._labels = {}

        @dataclass
        class RoutineState:
            pass

        module.RoutineState = RoutineState

        def internal_func(_rt, state, _scope, _start_offset=0):
            return (None, state)

        module._TESTRTN = internal_func
        module._labels["TESTRTN"] = internal_func

        _rt = MUMPSRuntime()
        # Set initial runtime context
        _rt._current_routine = "ORIGINAL"
        _rt._current_source_lines = ["ORIGINAL source"]
        _rt._current_label_lines = {"ORIGINAL": 0}

        _scope = {}

        call_external_with_offset(module, "TESTRTN", 0, _rt, _scope)

        # Runtime context should be restored after call
        assert _rt._current_routine == "ORIGINAL"
        assert _rt._current_source_lines == ["ORIGINAL source"]
        assert _rt._current_label_lines == {"ORIGINAL": 0}

    def test_handles_none_scope(self):
        """call_external_with_offset handles None _scope by creating empty dict."""
        import types
        from dataclasses import dataclass

        from m2py.runtime import MUMPSRuntime, call_external_with_offset

        module = types.ModuleType("TESTRTN")
        module._routine_name = "TESTRTN"
        module._source_lines = ["TESTRTN"]
        module._label_lines = {"TESTRTN": 0}
        module._line_map = {1: ("TESTRTN", 0)}
        module._labels = {}

        @dataclass
        class RoutineState:
            pass

        module.RoutineState = RoutineState

        def internal_func(_rt, state, _scope, _start_offset=0):
            return (None, state)

        module._TESTRTN = internal_func
        module._labels["TESTRTN"] = internal_func

        _rt = MUMPSRuntime()

        # Should not raise with None scope
        call_external_with_offset(module, "TESTRTN", 0, _rt, None)


@pytest.mark.runtime
class TestFindToplevelColon:
    """Tests for _find_toplevel_colon helper function.

    This helper is used for XECUTE argument postcondition parsing.
    It finds the first colon that's not inside quotes or parentheses.
    """

    def test_simple_postcondition(self):
        """Simple VAR:condition pattern."""
        from m2py.runtime import _find_toplevel_colon

        assert _find_toplevel_colon("X:1") == 1
        assert _find_toplevel_colon("VAR:COND") == 3

    def test_no_colon(self):
        """No colon returns -1."""
        from m2py.runtime import _find_toplevel_colon

        assert _find_toplevel_colon("VARIABLE") == -1
        assert _find_toplevel_colon("") == -1

    def test_colon_in_quoted_string(self):
        """Colon inside quoted string is NOT a top-level colon."""
        from m2py.runtime import _find_toplevel_colon

        # String contains colon, but it's inside quotes
        assert _find_toplevel_colon('"A:B"') == -1
        assert _find_toplevel_colon('"code:with:colons"') == -1

    def test_colon_after_quoted_string(self):
        """Colon after quoted string IS a top-level colon."""
        from m2py.runtime import _find_toplevel_colon

        # Colon is after the quoted string
        result = _find_toplevel_colon('"STRING":COND')
        assert result == 8  # Position of : after closing quote

    def test_colon_in_parentheses(self):
        """Colon inside function call parentheses is NOT top-level."""
        from m2py.runtime import _find_toplevel_colon

        # $SELECT contains colons inside parens
        assert _find_toplevel_colon('$S(1>2:"a",1:"b")') == -1

    def test_colon_after_function_call(self):
        """Colon after function call IS top-level."""
        from m2py.runtime import _find_toplevel_colon

        # Function followed by postcondition
        # '$P(X,","):COND' - colon at position 9 (0-indexed)
        result = _find_toplevel_colon('$P(X,","):COND')
        assert result == 9  # Position of : after closing paren

    def test_nested_parentheses(self):
        """Handles nested parentheses correctly."""
        from m2py.runtime import _find_toplevel_colon

        # Nested parens with colon inside
        assert _find_toplevel_colon("F(G(H:I))") == -1

    def test_mixed_quotes_and_parens(self):
        """Handles mix of quotes and parentheses."""
        from m2py.runtime import _find_toplevel_colon

        # Quote inside parens with colon
        assert _find_toplevel_colon('F("a:b")') == -1
        # Paren inside quotes (not special)
        assert _find_toplevel_colon('"(":COND') == 3
