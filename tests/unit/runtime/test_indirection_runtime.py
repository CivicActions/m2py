"""Unit tests for Spec 012 Phase 2: Indirection & XECUTE Runtime Methods.

Tests for:
- T007: MUMPSRuntime.get_var()
- T008: MUMPSRuntime.set_var()
- T010: MUMPSRuntime.parse_call_target()
- T011: MUMPSRuntime.execute_mumps()
- T012: _is_valid_varname() helper
- T040: MUMPSRuntime.set_indirected() (unified API)

These are foundational runtime methods that all indirection/XECUTE features depend on.
"""

import pytest

from m2py.runtime import (
    MUMPSRuntime,
    IndirectionError,
    CallTarget,
    MArray,
    _is_valid_varname,
)


# =============================================================================
# T012: _is_valid_varname() Tests
# =============================================================================


class TestIsValidVarname:
    """Tests for _is_valid_varname() helper function."""

    def test_single_letter_valid(self):
        """Single letter is valid MUMPS variable name."""
        assert _is_valid_varname("X") is True
        assert _is_valid_varname("A") is True
        assert _is_valid_varname("z") is True

    def test_letter_with_numbers_valid(self):
        """Letters followed by numbers are valid."""
        assert _is_valid_varname("VAR1") is True
        assert _is_valid_varname("A123") is True
        assert _is_valid_varname("TEST99") is True

    def test_percent_prefix_valid(self):
        """Names starting with % are valid (system variables)."""
        assert _is_valid_varname("%ZTMP") is True
        assert _is_valid_varname("%A") is True
        assert _is_valid_varname("%123") is True  # % followed by nums is valid

    def test_global_prefix_valid(self):
        """Global variable names (^prefix) are valid."""
        assert _is_valid_varname("^GLO") is True
        assert _is_valid_varname("^A1") is True
        assert _is_valid_varname("^ROUTINE") is True

    def test_global_percent_prefix_valid(self):
        """Global system variables (^%prefix) are valid."""
        assert _is_valid_varname("^%ZTMP") is True

    def test_empty_string_invalid(self):
        """Empty string is not a valid variable name."""
        assert _is_valid_varname("") is False

    def test_digit_start_invalid(self):
        """Names starting with digits are invalid."""
        assert _is_valid_varname("123BAD") is False
        assert _is_valid_varname("1VAR") is False
        assert _is_valid_varname("0") is False

    def test_underscore_start_invalid(self):
        """Names starting with underscore are invalid (not MUMPS standard)."""
        assert _is_valid_varname("_PRIV") is False
        assert _is_valid_varname("_") is False

    def test_subscripts_invalid(self):
        """Subscripted names should fail (need parsing first)."""
        assert _is_valid_varname("VAR(1)") is False
        assert _is_valid_varname("ARR(1,2)") is False

    def test_special_chars_invalid(self):
        """Special characters (except % and ^) are invalid."""
        assert _is_valid_varname("VAR$") is False
        assert _is_valid_varname("VAR@") is False
        assert _is_valid_varname("VAR-1") is False


# =============================================================================
# T007: get_var() Tests
# =============================================================================


class TestGetVar:
    """Tests for MUMPSRuntime.get_var() method."""

    @pytest.fixture
    def rt(self):
        """Create fresh runtime instance for each test."""
        return MUMPSRuntime()

    def test_get_simple_variable(self, rt):
        """Get a simple local variable."""
        scope = {"X": 5, "NAME": "John"}
        assert rt.get_var("X", scope) == 5
        assert rt.get_var("NAME", scope) == "John"

    def test_get_undefined_returns_empty_string(self, rt):
        """Undefined variables return empty string."""
        scope = {}
        assert rt.get_var("UNDEF", scope) == ""
        assert rt.get_var("NOTSET", scope) == ""

    def test_get_subscripted_variable(self, rt):
        """Get subscripted array variables."""
        arr = MArray()
        arr[1, 2].value = 10
        arr[1, 3].value = 30
        scope = {"ARR": arr}

        assert rt.get_var("ARR(1,2)", scope) == 10
        assert rt.get_var("ARR(1,3)", scope) == 30

    def test_get_undefined_subscript_returns_empty(self, rt):
        """Undefined subscripts return empty string."""
        arr = MArray()
        arr[1].value = 10
        scope = {"ARR": arr}

        assert rt.get_var("ARR(2)", scope) == ""
        assert rt.get_var("ARR(1,2)", scope) == ""

    def test_get_global_variable(self, rt):
        """Get global variables (^prefix)."""
        # Set via GlobalStorageBackend interface
        rt._globals.set("GLO", (), "100")
        scope = {}

        assert rt.get_var("^GLO", scope) == "100"

    def test_get_global_with_subscript(self, rt):
        """Get global variables with subscripts."""
        # Set via GlobalStorageBackend interface
        rt._globals.set("GLO", ("1",), "200")
        scope = {}

        assert rt.get_var("^GLO(1)", scope) == "200"

    def test_get_undefined_global(self, rt):
        """Undefined global returns empty string."""
        scope = {}
        assert rt.get_var("^NOTSET", scope) == ""

    def test_get_invalid_name_raises(self, rt):
        """Invalid variable name raises IndirectionError."""
        scope = {}
        with pytest.raises(IndirectionError) as exc_info:
            rt.get_var("123BAD", scope)
        assert "invalid variable name" in exc_info.value.reason

    def test_get_empty_name_raises(self, rt):
        """Empty variable name raises IndirectionError."""
        scope = {}
        with pytest.raises(IndirectionError) as exc_info:
            rt.get_var("", scope)
        assert "empty variable name" in exc_info.value.reason


# =============================================================================
# T008: set_var() Tests
# =============================================================================


class TestSetVar:
    """Tests for MUMPSRuntime.set_var() method."""

    @pytest.fixture
    def rt(self):
        """Create fresh runtime instance for each test."""
        return MUMPSRuntime()

    def test_set_simple_variable(self, rt):
        """Set a simple local variable."""
        scope = {}
        rt.set_var("X", 5, scope)
        # Variables are stored as MArray for consistency with codegen
        assert isinstance(scope["X"], MArray)
        assert scope["X"].value == 5

    def test_set_overwrites_existing(self, rt):
        """Setting overwrites existing value."""
        # Start with an MArray-wrapped value
        scope = {"X": MArray()}
        scope["X"].value = 10
        rt.set_var("X", 20, scope)
        assert scope["X"].value == 20

    def test_set_subscripted_creates_marray(self, rt):
        """Setting subscripted var creates MArray automatically."""
        scope = {}
        rt.set_var("ARR(1,2)", 10, scope)

        assert isinstance(scope["ARR"], MArray)
        assert scope["ARR"].get(1, 2) == 10

    def test_set_multiple_subscripts(self, rt):
        """Set multiple subscripts on same array."""
        scope = {}
        rt.set_var("ARR(1)", 10, scope)
        rt.set_var("ARR(2)", 20, scope)
        rt.set_var("ARR(1,1)", 11, scope)

        assert scope["ARR"].get(1) == 10
        assert scope["ARR"].get(2) == 20
        assert scope["ARR"].get(1, 1) == 11

    def test_set_global_variable(self, rt):
        """Set global variable (^prefix)."""
        scope = {}
        rt.set_var("^GLO", 100, scope)

        # Access via GlobalStorageBackend interface
        assert rt._globals.get("GLO", ()) == "100"

    def test_set_global_with_subscript(self, rt):
        """Set global with subscripts."""
        scope = {}
        rt.set_var("^GLO(1,2)", 200, scope)

        # Access via GlobalStorageBackend interface
        assert rt._globals.get("GLO", ("1", "2")) == "200"

    def test_set_invalid_name_raises(self, rt):
        """Invalid variable name raises IndirectionError."""
        scope = {}
        with pytest.raises(IndirectionError) as exc_info:
            rt.set_var("123BAD", 1, scope)
        assert "invalid variable name" in exc_info.value.reason

    def test_set_empty_name_raises(self, rt):
        """Empty variable name raises IndirectionError."""
        scope = {}
        with pytest.raises(IndirectionError) as exc_info:
            rt.set_var("", 1, scope)
        assert "empty variable name" in exc_info.value.reason


# =============================================================================
# T010: parse_call_target() Tests
# =============================================================================


class TestParseCallTarget:
    """Tests for MUMPSRuntime.parse_call_target() method."""

    @pytest.fixture
    def rt(self):
        """Create fresh runtime instance for each test."""
        return MUMPSRuntime()

    def test_simple_label(self, rt):
        """Parse simple label: LABEL."""
        target = rt.parse_call_target("LABEL")
        assert target == CallTarget(label="LABEL", routine=None, offset=None)

    def test_external_routine_only(self, rt):
        """Parse external routine: ^ROUTINE."""
        target = rt.parse_call_target("^ROUTINE")
        assert target == CallTarget(label=None, routine="ROUTINE", offset=None)

    def test_label_in_routine(self, rt):
        """Parse label in routine: LABEL^ROUTINE."""
        target = rt.parse_call_target("LABEL^ROUTINE")
        assert target == CallTarget(label="LABEL", routine="ROUTINE", offset=None)

    def test_label_with_offset(self, rt):
        """Parse label with offset: LABEL+5."""
        target = rt.parse_call_target("LABEL+5")
        assert target == CallTarget(label="LABEL", routine=None, offset=5)

    def test_label_offset_routine(self, rt):
        """Parse full format: LABEL+5^ROUTINE."""
        target = rt.parse_call_target("LABEL+5^ROUTINE")
        assert target == CallTarget(label="LABEL", routine="ROUTINE", offset=5)

    def test_offset_without_label(self, rt):
        """Parse offset without label: +3^ROUTINE."""
        target = rt.parse_call_target("+3^ROUTINE")
        assert target == CallTarget(label=None, routine="ROUTINE", offset=3)

    def test_empty_target_raises(self, rt):
        """Empty target string raises error."""
        with pytest.raises(IndirectionError) as exc_info:
            rt.parse_call_target("")
        assert "empty call target" in exc_info.value.reason

    def test_invalid_offset_raises(self, rt):
        """Non-integer offset raises error."""
        with pytest.raises(IndirectionError) as exc_info:
            rt.parse_call_target("LABEL+ABC")
        assert "invalid offset" in exc_info.value.reason


# =============================================================================
# T011: execute_mumps() Tests (basic structure)
# =============================================================================


class TestExecuteMumps:
    """Tests for MUMPSRuntime.execute_mumps() method.

    Note: Full XECUTE integration tests are in Phase 4-5.
    These tests verify basic structure and error handling.
    """

    @pytest.fixture
    def rt(self):
        """Create fresh runtime instance for each test."""
        return MUMPSRuntime()

    def test_execute_empty_code_returns_none(self, rt):
        """Empty code returns None."""
        scope = {}
        result = rt.execute_mumps("", scope)
        assert result is None

    def test_execute_whitespace_only_returns_none(self, rt):
        """Whitespace-only code returns None."""
        scope = {}
        result = rt.execute_mumps("   ", scope)
        assert result is None

    # Note: Full XECUTE tests require codegen integration which is Phase 4
    # Placeholder tests here verify the method exists and basic signature


# =============================================================================
# T075j: get_var() with naked reference strings
# =============================================================================


class TestGetVarNakedReferences:
    """Tests for get_var handling naked reference strings like '^(3)'.

    Bug fix T075j: When get_var receives a name like "^(3)", it should
    interpret this as a naked reference using the current naked indicator,
    not as a literal variable name.
    """

    @pytest.fixture
    def rt(self):
        """Create fresh runtime instance for each test."""
        return MUMPSRuntime()

    def test_naked_reference_resolved(self, rt):
        """get_var('^(3)') resolves using current naked indicator."""
        # Set up: ^V(3) = 42
        rt.globals.set("V", ("3",), "42")
        # Set naked indicator to ("V", ())
        rt.globals._naked_indicator = ("V", ())

        scope = {}
        result = rt.get_var("^(3)", scope)
        assert result == "42"

    def test_naked_reference_with_multiple_subscripts(self, rt):
        """get_var('^(1,2)') appends subscripts to naked indicator."""
        # Set up: ^V(3,1,2) = "deep"
        rt.globals.set("V", ("3", "1", "2"), "deep")
        # Set naked indicator to ("V", ("3",))
        rt.globals._naked_indicator = ("V", ("3",))

        scope = {}
        result = rt.get_var("^(1,2)", scope)
        assert result == "deep"

    def test_naked_reference_undefined_returns_empty(self, rt):
        """get_var for undefined naked reference returns empty string."""
        # Set naked indicator to ("V", ())
        rt.globals._naked_indicator = ("V", ())

        scope = {}
        result = rt.get_var("^(99)", scope)
        assert result == ""

    def test_naked_reference_without_subscripts_raises(self, rt):
        """get_var('^') without subscripts raises error."""
        scope = {}
        with pytest.raises(IndirectionError) as exc_info:
            rt.get_var("^", scope)
        # The error message should indicate naked reference requires subscripts
        # or invalid variable name
        assert (
            "naked reference" in exc_info.value.reason.lower()
            or "invalid" in exc_info.value.reason.lower()
        )


# =============================================================================
# T075j: set_var() with naked reference strings
# =============================================================================


class TestSetVarNakedReferences:
    """Tests for set_var handling naked reference strings."""

    @pytest.fixture
    def rt(self):
        """Create fresh runtime instance for each test."""
        return MUMPSRuntime()

    def test_set_naked_reference(self, rt):
        """set_var('^(3)', value) sets via naked indicator."""
        # Set naked indicator to ("V", ())
        rt.globals._naked_indicator = ("V", ())

        scope = {}
        rt.set_var("^(3)", 42, scope)

        # Verify ^V(3) was set (values are stored as-is, not converted to string)
        assert rt.globals.get("V", ("3",)) == 42

    def test_set_naked_reference_deep(self, rt):
        """set_var with naked reference appending multiple subscripts."""
        # Set naked indicator to ("V", ("1",))
        rt.globals._naked_indicator = ("V", ("1",))

        scope = {}
        rt.set_var("^(2,3)", "deep", scope)

        # Verify ^V(1,2,3) was set
        assert rt.globals.get("V", ("1", "2", "3")) == "deep"


# =============================================================================
# T040: MUMPSRuntime.set_indirected() Tests (Variable System)
# =============================================================================


class TestSetIndirected:
    """Tests for MUMPSRuntime.set_indirected() unified SET method.

    Feature: 018-unified-variable-system
    Task: T040 - Create unified SET operation using IndirectionResolver

    Note: Values are stored in MArray objects for generated code compatibility.
    Tests verify the .value attribute of the MArray.
    """

    @pytest.fixture
    def rt(self):
        """Provide fresh MUMPSRuntime instance."""
        return MUMPSRuntime()

    def test_single_level_local(self, rt):
        """@X=5 where X="Y" sets Y="5" (string per MUMPS semantics)."""
        scope = {"X": "Y"}
        rt.set_indirected("X", 5, scope, levels=1)
        assert "Y" in scope
        # MUMPS stores values as strings, wrapped in MArray
        assert scope["Y"].value == "5"

    def test_two_level_local(self, rt):
        """@@X=5 where X="Y", Y="Z" sets Z="5" (string per MUMPS)."""
        scope = {"X": "Y", "Y": "Z"}
        rt.set_indirected("X", 5, scope, levels=2)
        assert "Z" in scope
        assert scope["Z"].value == "5"

    def test_three_level_local(self, rt):
        """@@@X=5 where X→Y→Z→W sets W="5" (string per MUMPS)."""
        scope = {"X": "Y", "Y": "Z", "Z": "W"}
        rt.set_indirected("X", 5, scope, levels=3)
        assert "W" in scope
        assert scope["W"].value == "5"

    def test_single_level_with_subscripts(self, rt):
        """@X@(1,2)=5 where X="A" sets A(1,2)="5" (string per MUMPS)."""
        scope = {"X": "A"}
        rt.set_indirected("X", 5, scope, levels=1, per_level_subscripts=[[1, 2]])
        assert "A" in scope
        assert scope["A"][1, 2].value == "5"

    def test_two_level_with_subscripts(self, rt):
        """@@X@(1)@(2)=5 where X="A", A(1)="B" sets B(2)="5" (string per MUMPS)."""
        scope = {"X": "A", "A": MArray()}
        scope["A"][1].value = "B"
        rt.set_indirected("X", 5, scope, levels=2, per_level_subscripts=[[1], [2]])
        assert "B" in scope
        assert scope["B"][2].value == "5"

    def test_invalid_name_raises_error(self, rt):
        """Invalid resolved name raises VarExpectedError."""
        from m2py.core.exceptions import VarExpectedError

        scope = {"X": "1+1"}  # Invalid variable name
        with pytest.raises(VarExpectedError):
            rt.set_indirected("X", 5, scope, levels=1)

    def test_empty_name_raises_error(self, rt):
        """Empty resolved name raises VarExpectedError."""
        from m2py.core.exceptions import VarExpectedError

        scope = {"X": ""}
        with pytest.raises(VarExpectedError):
            rt.set_indirected("X", 5, scope, levels=1)

    def test_global_target(self, rt):
        """@X=5 where X="^GLO" sets global as string per MUMPS."""
        scope = {"X": "^GLO"}
        rt.set_indirected("X", 5, scope, levels=1)
        # Value stored in globals as string per MUMPS semantics
        assert rt.globals.get("GLO", ()) == "5"

    def test_global_target_with_subscripts(self, rt):
        """@X@(1)=5 where X="^GLO" sets ^GLO(1)="5" (string per MUMPS)."""
        scope = {"X": "^GLO"}
        rt.set_indirected("X", 5, scope, levels=1, per_level_subscripts=[[1]])
        assert rt.globals.get("GLO", ("1",)) == "5"

    def test_percent_name(self, rt):
        """@X=5 where X="%Z" sets %Z="5" (string per MUMPS)."""
        scope = {"X": "%Z"}
        rt.set_indirected("X", 5, scope, levels=1)
        # %Z stored as _pct_Z in scope
        assert "_pct_Z" in scope
        assert scope["_pct_Z"].value == "5"

    def test_zero_value_stored_as_string(self, rt):
        """@X=0 must store "0" not 0 to preserve truthiness in WRITE.

        Bug fix: Integer 0 is falsy in Python, so (0 or '') evaluates to ''.
        But string "0" is truthy, so ("0" or '') evaluates to "0".
        This bug caused WRITE @Y to print empty instead of "0".
        Feature: 018-unified-variable-system
        """
        scope = {"X": "Y"}
        rt.set_indirected("X", 0, scope, levels=1)
        # Must be string "0", not int 0, wrapped in MArray
        assert scope["Y"].value == "0"
        assert type(scope["Y"].value) is str
        # This is the real test - ensures (value or '') works in WRITE
        assert (scope["Y"].value or "") == "0"

    def test_empty_string_preserved(self, rt):
        """@X="" stores empty string correctly."""
        scope = {"X": "Y"}
        rt.set_indirected("X", "", scope, levels=1)
        assert scope["Y"].value == ""
        assert type(scope["Y"].value) is str
