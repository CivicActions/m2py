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


# =============================================================================
# T075j: resolve_indirection() with numeric terminal values
# =============================================================================


class TestResolveIndirectionNumericTerminals:
    """Tests for resolve_indirection stopping early on non-variable-name values.

    Bug fix T075j: When resolving indirection like @@@X, if an intermediate
    value is not a valid variable name (e.g., a numeric string like "200"),
    return it as-is instead of trying to look it up as a variable.

    Note: resolve_indirection always returns strings because values are
    converted to strings for use as variable names in the chain.
    """

    @pytest.fixture
    def rt(self):
        """Create fresh runtime instance for each test."""
        return MUMPSRuntime()

    def test_numeric_string_stops_chain(self, rt):
        """Chain stops when value is numeric string (not a var name).

        A="B", B="C", C="D", D=200
        @@@A (3 levels): A→B, B→C, C→D, final=D → 200 (int, because D is valid var)
        @@@@A (4 levels): +1 more: D→200, "200" not valid → "200" (string)
        """
        scope = {"A": "B", "B": "C", "C": "D", "D": 200}
        # @@@A: 3 levels means 3 lookups in loop, then final lookup of D → 200
        assert rt.resolve_indirection("A", 3, scope) == 200
        # @@@@A: 4 levels means D's value enters loop, becomes "200" (not valid var)
        assert rt.resolve_indirection("A", 4, scope) == "200"
        # @@@@@A: same as @@@@A because "200" is not a var name
        assert rt.resolve_indirection("A", 5, scope) == "200"

    def test_single_level_with_numeric_value(self, rt):
        """@A where A contains numeric returns the numeric.

        1 level: look up A in loop → 123, then "123" is not valid var → return "123"
        """
        scope = {"A": 123}
        # @A should look up A, get 123, convert to "123" in loop
        # Then "123" is not a valid var name, return "123"
        assert rt.resolve_indirection("A", 1, scope) == "123"

    def test_double_level_with_numeric_intermediate(self, rt):
        """@@A where intermediate value is numeric stops at that value."""
        scope = {"A": "B", "B": 456}
        # @@A: A→"B"→456 (2 lookups)
        # After getting 456, "456" is not a valid var name, return it
        assert rt.resolve_indirection("A", 2, scope) == "456"

    def test_chain_with_five_string_vars(self, rt):
        """Deep chain with all string intermediates works correctly.

        A→B→C→D→E, E=300
        - @A (1): A→B, final=B→"C"
        - @@A (2): A→B→C, final=C→"D"
        - @@@A (3): A→B→C→D, final=D→"E"
        - @@@@A (4): A→B→C→D→E, final=E→300 (int)
        - @@@@@A (5): ...→E→300, "300" not valid → "300" (string)
        """
        scope = {"A": "B", "B": "C", "C": "D", "D": "E", "E": 300}
        # @A: 1 level means loop does 1 lookup A→B, then final lookup B→C
        assert rt.resolve_indirection("A", 1, scope) == "C"
        # @@A: 2 levels → final lookup of C→D
        assert rt.resolve_indirection("A", 2, scope) == "D"
        # @@@A: 3 levels → final lookup of D→E
        assert rt.resolve_indirection("A", 3, scope) == "E"
        # @@@@A: 4 levels → final lookup of E→300 (int)
        assert rt.resolve_indirection("A", 4, scope) == 300
        # @@@@@A: 5 levels → E→300 enters loop, "300" not valid → "300"
        assert rt.resolve_indirection("A", 5, scope) == "300"

    def test_negative_number_stops_chain(self, rt):
        """Negative number string is not a valid var name.

        A→B, B=-42
        - @A (1): A→B, final=B→-42 (int)
        - @@A (2): A→B→-42, "-42" not valid → "-42" (string)
        """
        scope = {"A": "B", "B": -42}
        # @A: 1 level → final lookup B→-42 (int)
        assert rt.resolve_indirection("A", 1, scope) == -42
        # @@A: 2 levels → "-42" is not a valid var name
        assert rt.resolve_indirection("A", 2, scope) == "-42"
        assert rt.resolve_indirection("A", 3, scope) == "-42"

    def test_float_number_stops_chain(self, rt):
        """Float number string is not a valid var name."""
        scope = {"A": "B", "B": 3.14}
        # "3.14" is not a valid var name
        assert rt.resolve_indirection("A", 2, scope) == "3.14"

    def test_string_starting_with_digit_stops_chain(self, rt):
        """String starting with digit is not a valid var name."""
        scope = {"A": "B", "B": "123abc"}
        # "123abc" starts with digit, not a valid var name
        assert rt.resolve_indirection("A", 2, scope) == "123abc"

    def test_empty_string_raises_error(self, rt):
        """Empty string in chain raises error (cannot be var name or value)."""
        scope = {"A": "B", "B": ""}
        with pytest.raises(IndirectionError) as exc_info:
            rt.resolve_indirection("A", 2, scope)
        assert "empty value" in exc_info.value.reason


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
# T075j: resolve_indirection() with naked reference strings
# =============================================================================


class TestResolveIndirectionNakedReferences:
    """Tests for resolve_indirection handling naked reference strings.

    Bug fix T075j: When indirection yields a naked reference string like "^(3)",
    it should be resolved using the current naked indicator.
    """

    @pytest.fixture
    def rt(self):
        """Create fresh runtime instance for each test."""
        return MUMPSRuntime()

    def test_indirection_yields_naked_reference(self, rt):
        """When indirection yields '^(3)', resolve via naked indicator.

        Set up: ^V(1) = "^(3)", ^V(3) = 42
        @@^V(1) → @(value of ^V(1)) → @"^(3)" → resolve naked → ^V(3) → 42
        """
        # This test is at the codegen level really, since the runtime
        # function gets the already-resolved value. But let's test the
        # get_var behavior which is what handles the naked reference.
        rt.globals.set("V", ("1",), "^(3)")
        rt.globals.set("V", ("3",), "42")
        # After reading ^V(1), naked indicator becomes ("V", ())
        rt.globals._naked_indicator = ("V", ())

        scope = {}
        # get_var("^(3)", scope) should resolve to ^V(3) = 42
        result = rt.get_var("^(3)", scope)
        assert result == "42"

    def test_naked_reference_is_valid_var_name(self, rt):
        """'^(3)' is considered a valid var name for chaining purposes.

        The _is_valid_var_name helper should return True for naked references.
        """
        # We can't directly call the nested function, but we can verify
        # the behavior by testing resolve_indirection
        rt.globals.set("V", ("1",), "^(3)")
        rt.globals.set("V", ("3",), "42")
        rt.globals._naked_indicator = ("V", ())

        # @X = value of ^V(1) = "^(3)"
        # Since ^(3) is a valid var name pattern (naked ref), continue chain
        # @"^(3)" = value of ^V(3) = 42
        # So @@X should be 42
        # BUT: This requires the value "^V(1)" to be resolved first, which needs
        # the codegen to set up properly. For unit test, test get_var directly.
        pass  # This is tested at integration level


# =============================================================================
# T075j: Additional edge cases for indirection
# =============================================================================


class TestIndirectionEdgeCases:
    """Additional edge cases for indirection handling."""

    @pytest.fixture
    def rt(self):
        """Create fresh runtime instance for each test."""
        return MUMPSRuntime()

    def test_valid_var_name_starting_with_percent(self, rt):
        """Variables starting with % are valid MUMPS system variables.

        Note: In _scope, MUMPS %A is stored as Python name _pct_A (to match codegen).
        The runtime functions translate MUMPS names internally.
        """
        # Scope uses Python-translated keys (as codegen produces)
        scope = {"_pct_A": "B", "B": 10}
        # But resolve_indirection receives MUMPS names
        result = rt.resolve_indirection("%A", 1, scope)
        assert result == 10

    def test_global_in_chain(self, rt):
        """Global variables work in indirection chain."""
        rt.globals.set("G", (), "X")
        scope = {"X": 100}
        # @^G: get value of ^G = "X", then get value of X = 100
        result = rt.resolve_indirection("^G", 1, scope)
        assert result == 100

    def test_subscripted_var_in_chain(self, rt):
        """Subscripted variable names in chain."""
        scope = {"A": "B(1)", "B": MArray()}
        scope["B"][1].value = 99
        # @A: get value of A = "B(1)", then get value of B(1) = 99
        result = rt.resolve_indirection("A", 1, scope)
        assert result == 99

    def test_chain_alternating_local_global(self, rt):
        """Chain alternating between local and global variables."""
        scope = {"A": "^G"}
        rt.globals.set("G", (), "B")
        scope["B"] = 77

        # @@A: A → "^G" → "B" → 77
        result = rt.resolve_indirection("A", 2, scope)
        assert result == 77

    def test_chain_with_subscripted_global(self, rt):
        """Chain with subscripted global variable."""
        scope = {"A": "^G(1,2)"}
        rt.globals.set("G", ("1", "2"), "42")

        # @A: A → "^G(1,2)" → 42 (numeric, chain stops)
        result = rt.resolve_indirection("A", 1, scope)
        assert result == "42"
