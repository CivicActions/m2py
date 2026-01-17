"""Unit tests for Spec 012 Phase 2: Indirection & XECUTE Runtime Methods.

Tests for:
- T007: MUMPSRuntime.get_var()
- T008: MUMPSRuntime.set_var()
- T009: MUMPSRuntime.resolve_indirection()
- T010: MUMPSRuntime.parse_call_target()
- T011: MUMPSRuntime.execute_mumps()
- T012: _is_valid_varname() helper

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
# T065: get_indirection_source() Tests - Edge Case Error Handling
# =============================================================================


class TestGetIndirectionSource:
    """Tests for MUMPSRuntime.get_indirection_source() method.

    T065: This method provides better error messages when the source
    variable for indirection is undefined.
    """

    @pytest.fixture
    def rt(self):
        """Create fresh runtime instance for each test."""
        return MUMPSRuntime()

    def test_defined_variable_returns_value(self, rt):
        """Get indirection source for defined variable returns its value."""
        arr = MArray()
        arr.value = "TARGET"
        scope = {"X": arr}
        result = rt.get_indirection_source("X", scope)
        assert result == "TARGET"

    def test_undefined_variable_raises_error(self, rt):
        """Undefined source variable raises IndirectionError with clear message."""
        scope = {}
        with pytest.raises(IndirectionError) as exc_info:
            rt.get_indirection_source("UNDEF", scope)
        assert "Undefined local variable" in str(exc_info.value)
        assert "UNDEF" in str(exc_info.value)

    def test_undefined_variable_error_reason(self, rt):
        """IndirectionError has the error message as reason field."""
        scope = {}
        with pytest.raises(IndirectionError) as exc_info:
            rt.get_indirection_source("NOTSET", scope)
        # The reason field contains the full error message
        assert "Undefined local variable" in exc_info.value.reason
        assert "NOTSET" in exc_info.value.reason

    def test_empty_value_returns_empty_string(self, rt):
        """Variable with empty value returns empty string."""
        arr = MArray()
        arr.value = ""
        scope = {"X": arr}
        result = rt.get_indirection_source("X", scope)
        assert result == ""

    def test_numeric_value_converted_to_string(self, rt):
        """Numeric values are returned as strings for use in indirection."""
        arr = MArray()
        arr.value = 123
        scope = {"X": arr}
        result = rt.get_indirection_source("X", scope)
        # Value is converted to string for use as variable name
        assert result == "123"


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
# T009: resolve_indirection() Tests
# =============================================================================


class TestResolveIndirection:
    """Tests for MUMPSRuntime.resolve_indirection() method."""

    @pytest.fixture
    def rt(self):
        """Create fresh runtime instance for each test."""
        return MUMPSRuntime()

    def test_single_level_indirection(self, rt):
        """Single level @X: If X="VAR", returns value of VAR.

        In MUMPS, @X where X contains a variable name "VAR" evaluates
        to the value of VAR. This is one level of indirection.
        """
        # A="B" means @A should look up "B", which is 42
        scope = {"A": "B", "B": 42, "C": "hello"}

        assert rt.resolve_indirection("A", 1, scope) == 42
        # C="hello" means @C looks up "hello" - which doesn't exist
        with pytest.raises(IndirectionError):
            rt.resolve_indirection("C", 1, scope)

    def test_double_level_indirection(self, rt):
        """Double level @@X: If X="VAR" and VAR="OTHER", returns value of OTHER.

        In MUMPS, @@X where X contains "VAR" and VAR contains "OTHER"
        evaluates to the value of OTHER. Two levels of dereference.
        """
        # A="B", B="C", so @@A -> @B -> look up "C", which is "result"
        scope = {"A": "B", "B": "C", "C": "result"}

        assert rt.resolve_indirection("A", 2, scope) == "result"

    def test_triple_level_indirection(self, rt):
        """Triple level @@@X chains three dereferences.

        If X="A", A="B", B="C", and C=100, then @@@X:
        1. Gets value of X -> "A"
        2. Gets value of A -> "B"
        3. Gets value of B -> "C"
        4. Gets value of C -> 100
        """
        # X="A", A="B", B="C", C=100
        # @@@X -> A -> B -> C -> get value of C = 100
        scope = {"X": "A", "A": "B", "B": "C", "C": 100}

        assert rt.resolve_indirection("X", 3, scope) == 100

    def test_indirection_undefined_chain(self, rt):
        """Undefined variable in chain raises error."""
        scope = {"A": "UNDEF"}

        with pytest.raises(IndirectionError) as exc_info:
            rt.resolve_indirection("A", 2, scope)
        assert "undefined variable in indirection chain" in exc_info.value.reason

    def test_indirection_levels_less_than_one_raises(self, rt):
        """Levels < 1 raises error."""
        scope = {"A": "B"}

        with pytest.raises(IndirectionError) as exc_info:
            rt.resolve_indirection("A", 0, scope)
        assert "levels must be >= 1" in exc_info.value.reason


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
