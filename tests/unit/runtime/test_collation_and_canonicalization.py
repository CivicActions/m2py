"""Tests for MUMPS collation key and indirection subscript canonicalization.

Covers two bug fixes:

1. **Empty-string collation** (`_mumps_collation_key`):
   In MUMPS, the empty string sorts before all other subscripts.
   Previously, empty string received collation key ``(1, "")`` (string type)
   which sorted *after* numeric keys ``(0, ...)``, causing ``$QUERY`` and
   ``$ORDER`` to skip entire subtrees when traversing from ``""``.

2. **Numeric subscript canonicalization** (``_normalize_parsed_subscript``):
   When ``set_indirected`` parses a global reference like ``^DD(1009.801,.01,0)``,
   ``_convert_subscript(".01")`` returns ``float(0.01)``.  Python's ``str(0.01)``
   produces ``"0.01"`` which the ``SubscriptCanonicalizer`` treats as a
   *non-canonical string* (since the MUMPS canonical form is ``".01"``).
   This caused the subscript to be stored in the string collation range
   instead of the numeric range, making it invisible to ``$QUERY``/``$ORDER``.
"""

from __future__ import annotations


import pytest

from m2py.runtime.helpers import _mumps_collation_key


# ---------------------------------------------------------------------------
# 1. Empty-string collation
# ---------------------------------------------------------------------------


class TestEmptyStringCollation:
    """Verify that empty string sorts before all other subscript types."""

    def test_empty_string_key_type(self):
        """Empty string gets type_order -1."""
        key = _mumps_collation_key("")
        assert key[0] == -1

    def test_none_key_type(self):
        """None treated like empty string."""
        key = _mumps_collation_key(None)
        assert key[0] == -1

    def test_empty_before_zero(self):
        """'' < 0"""
        assert _mumps_collation_key("") < _mumps_collation_key("0")

    def test_empty_before_negative(self):
        """'' < -1"""
        assert _mumps_collation_key("") < _mumps_collation_key("-1")

    def test_empty_before_positive_decimal(self):
        """'' < .01"""
        assert _mumps_collation_key("") < _mumps_collation_key(".01")

    def test_empty_before_string(self):
        """'' < "A" """
        assert _mumps_collation_key("") < _mumps_collation_key("A")

    def test_empty_before_one(self):
        """'' < 1"""
        assert _mumps_collation_key("") < _mumps_collation_key("1")

    def test_numeric_before_string(self):
        """0 < "A" (numeric before strings)."""
        assert _mumps_collation_key("0") < _mumps_collation_key("A")

    def test_mumps_full_collation_order(self):
        """Full MUMPS order: '' < -5 < -1 < 0 < .01 < 1 < 5 < "A" < "Z"."""
        values = ["", "-5", "-1", "0", ".01", "1", "5", "A", "Z"]
        keys = [_mumps_collation_key(v) for v in values]
        assert keys == sorted(keys), (
            f"Collation order mismatch: {list(zip(values, keys))}"
        )

    def test_empty_sorts_first_in_sorted(self):
        """When used with sorted(), empty string is first."""
        subs = ["A", "0", "", "1", "-1"]
        result = sorted(subs, key=_mumps_collation_key)
        assert result[0] == ""

    def test_query_starting_point(self):
        """'' is the correct starting point for $QUERY traversal.

        $QUERY(^GLO(sub,"")) should find all descendants since ""
        sorts before every subscript.
        """
        # Ensure "" sorts before all numeric and string keys
        for sub in ["0", ".01", "1", "100", "A", "ZZ", "-99"]:
            assert _mumps_collation_key("") < _mumps_collation_key(sub), (
                f"empty string should sort before {sub!r}"
            )


# ---------------------------------------------------------------------------
# 2. Numeric subscript canonicalization
# ---------------------------------------------------------------------------


class TestNormalizeParsedSubscript:
    """Test _normalize_parsed_subscript handles numeric types correctly."""

    @pytest.fixture(autouse=True)
    def _import(self):
        from m2py.runtime import _normalize_parsed_subscript

        self.normalize = _normalize_parsed_subscript

    # -- Float subscripts (from _convert_subscript for ".01", ".5", etc.) --

    def test_float_point_01(self):
        """float(0.01) → '.01' (MUMPS canonical, no leading zero)."""
        assert self.normalize(0.01) == ".01"

    def test_float_point_5(self):
        """float(0.5) → '.5'."""
        assert self.normalize(0.5) == ".5"

    def test_float_point_06(self):
        """float(0.06) → '.06'."""
        assert self.normalize(0.06) == ".06"

    def test_float_1009_801(self):
        """float(1009.801) → '1009.801'."""
        assert self.normalize(1009.801) == "1009.801"

    def test_float_negative_point_5(self):
        """float(-0.5) → '-.5'."""
        assert self.normalize(-0.5) == "-.5"

    def test_float_whole_number(self):
        """float(1.0) → '1' (integer canonical form)."""
        assert self.normalize(1.0) == "1"

    def test_float_trailing_zeros(self):
        """float(1.50) → '1.5' (no trailing zeros)."""
        assert self.normalize(1.5) == "1.5"

    # -- Integer subscripts --

    def test_int_zero(self):
        """int(0) → '0'."""
        assert self.normalize(0) == "0"

    def test_int_positive(self):
        """int(42) → '42'."""
        assert self.normalize(42) == "42"

    def test_int_negative(self):
        """int(-3) → '-3'."""
        assert self.normalize(-3) == "-3"

    # -- String subscripts (from quoted values) --

    def test_string_plain(self):
        """Regular string passes through."""
        assert self.normalize("ALABAMA") == "ALABAMA"

    def test_string_mumps_quoted(self):
        """MUMPS-quoted '"^"' → '^'."""
        assert self.normalize('"^"') == "^"

    def test_string_numeric_canonical(self):
        """Canonical numeric string '.01' passes through unchanged."""
        assert self.normalize(".01") == ".01"

    def test_string_numeric_noncanonical(self):
        """Non-canonical '0.01' preserved as string (different node in MUMPS)."""
        # In MUMPS, "0.01" and .01 are DIFFERENT subscripts
        assert self.normalize("0.01") == "0.01"

    def test_string_empty(self):
        """Empty string preserved."""
        assert self.normalize("") == ""


class TestCanonicalSubscriptRoundtrip:
    """Verify that subscripts from S @"^GLO(.01)" are stored canonically.

    The critical flow:
    1. S @"^DD(1009.801,.01,0)"=v → set_indirected parses ".01" as float(0.01)
    2. _normalize_parsed_subscript(0.01) → ".01"
    3. backend.set("DD", (".01",), v) → canonicalize → ".01" (already canonical)
    4. $QUERY finds ".01" as numeric subscript in correct position
    """

    @pytest.fixture
    def runtime(self):
        from m2py.runtime import MUMPSRuntime

        return MUMPSRuntime()

    def test_set_indirected_decimal_subscript(self, runtime):
        """S @"^GLO(.01)"=v stores at canonical '.01' key."""
        scope = {}
        runtime.set_indirected("^GLO(.01,0)", "test_value", scope, levels=0)
        val = runtime.globals.get("GLO", (".01", "0"))
        assert val == "test_value"

    def test_set_indirected_decimal_via_variable(self, runtime):
        """S @X where X="^GLO(.01,0)" stores at canonical '.01'."""
        from m2py.runtime import MArray

        scope = {}
        x = MArray()
        x.value = "^GLO(.01,0)"
        scope["X"] = x
        runtime.set_indirected("X", "via_var", scope, levels=1)
        val = runtime.globals.get("GLO", (".01", "0"))
        assert val == "via_var"

    def test_query_finds_decimal_subscript(self, runtime):
        """$QUERY traverses through .01 subscript correctly."""
        runtime.globals.set("GLO", ("0",), "header")
        runtime.globals.set("GLO", (".01", "0"), "field_def")
        runtime.globals.set("GLO", (".02", "0"), "other_field")

        # $QUERY from empty string should find: 0, .01/0, .02/0
        ref = runtime.globals.query("GLO", ("",))
        assert ref == "^GLO(0)", f"First should be 0, got {ref}"

        ref = runtime.globals.query("GLO", ("0",))
        assert ref == "^GLO(.01,0)", f"After 0 should be .01, got {ref}"

    def test_set_and_retrieve_multiple_decimals(self, runtime):
        """Multiple decimal subscripts (.001, .01, .02, ..., .06) roundtrip."""
        scope = {}
        for n in (".001", ".01", ".02", ".03", ".04", ".05", ".06"):
            runtime.set_indirected(f"^DD(1009,{n},0)", f"field_{n}", scope, levels=0)

        # Verify all stored correctly
        for n in (".001", ".01", ".02", ".03", ".04", ".05", ".06"):
            val = runtime.globals.get("DD", ("1009", n, "0"))
            assert val == f"field_{n}", f"Missing DD(1009,{n},0)"

    def test_order_traversal_decimal_subscripts(self, runtime):
        """$ORDER traverses decimal subscripts in correct numeric order."""
        for n in (".06", ".01", ".03", ".02"):
            runtime.globals.set("DD", ("1009", n, "0"), f"field_{n}")

        # $ORDER should return in numeric order: .01, .02, .03, .06
        result = []
        sub = runtime.globals.order("DD", ("1009", ""), 1)
        while sub:
            result.append(sub)
            sub = runtime.globals.order("DD", ("1009", sub), 1)

        assert result == [".01", ".02", ".03", ".06"]

    def test_dmufi001_pattern(self, runtime):
        """Reproduce DMUFI001 data loading pattern: S @X=Y for DD entries."""
        scope = {}
        # Simulate what DMUFI001 does: S @"^DD(1009.801,.01,0)"=value
        entries = [
            ("^DD(1009.801,0)", "FIELD^^.06^6"),
            ("^DD(1009.801,.01,0)", "NAME^RF^^0;1^K:X"),
            ("^DD(1009.801,.01,3)", "Answer must be 3-60 characters."),
            ("^DD(1009.801,.02,0)", "POINTER^P.85'^DI(.85,^0;2^Q"),
        ]
        for ref, value in entries:
            runtime.set_indirected(ref, value, scope, levels=0)

        # Verify all stored at canonical subscripts
        assert runtime.globals.get("DD", ("1009.801", "0")) == "FIELD^^.06^6"
        assert runtime.globals.get("DD", ("1009.801", ".01", "0")) is not None
        assert runtime.globals.get("DD", ("1009.801", ".02", "0")) is not None

        # $ORDER should find: 0, .01, .02 (numeric order)
        subs = []
        sub = runtime.globals.order("DD", ("1009.801", ""), 1)
        while sub:
            subs.append(sub)
            sub = runtime.globals.order("DD", ("1009.801", sub), 1)
        assert subs == ["0", ".01", ".02"]
