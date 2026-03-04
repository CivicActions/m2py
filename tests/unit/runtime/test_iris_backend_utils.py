"""Unit tests for IRIS backend utility methods.

Tests pure-function helpers from the null subscript workaround
(commit 0d644f46) that don't require an IRIS connection:
  - _build_gref: builds MUMPS global reference strings
  - _parse_gref: parses MUMPS global reference strings
  - _has_null_subscript: detects empty-string subscripts
  - float/int canonicalization in get() return values
"""

import pytest

from m2py.runtime.iris_backend import IRISGlobalStorage


def _build_gref(name: str, subscripts: tuple[str, ...]) -> str:
    """Call _build_gref as an unbound method (avoids __del__ on instances)."""

    # _build_gref only uses self._make_global_name which is f"^{name}",
    # so we can call it with a minimal mock self.
    class _Stub:
        _make_global_name = staticmethod(lambda n: f"^{n}")

    return IRISGlobalStorage._build_gref(_Stub(), name, subscripts)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# _has_null_subscript
# ---------------------------------------------------------------------------
@pytest.mark.runtime
class TestHasNullSubscript:
    """Tests for _has_null_subscript static method."""

    def test_no_subscripts(self):
        assert IRISGlobalStorage._has_null_subscript(()) is False

    def test_no_null_subscripts(self):
        assert IRISGlobalStorage._has_null_subscript(("a", "b", "c")) is False

    def test_single_null(self):
        assert IRISGlobalStorage._has_null_subscript(("",)) is True

    def test_null_at_start(self):
        assert IRISGlobalStorage._has_null_subscript(("", "a", "b")) is True

    def test_null_in_middle(self):
        assert IRISGlobalStorage._has_null_subscript(("a", "", "b")) is True

    def test_null_at_end(self):
        assert IRISGlobalStorage._has_null_subscript(("a", "b", "")) is True

    def test_all_null(self):
        assert IRISGlobalStorage._has_null_subscript(("", "", "")) is True

    def test_numeric_strings_not_null(self):
        assert IRISGlobalStorage._has_null_subscript(("0", "1", "2")) is False

    def test_space_not_null(self):
        """A single space is not the same as empty string."""
        assert IRISGlobalStorage._has_null_subscript((" ",)) is False


# ---------------------------------------------------------------------------
# _build_gref
# ---------------------------------------------------------------------------
@pytest.mark.runtime
class TestBuildGref:
    """Tests for _build_gref — builds MUMPS global reference strings."""

    def test_no_subscripts(self):
        assert _build_gref("TMP", ()) == "^TMP"

    def test_single_subscript(self):
        assert _build_gref("TMP", ("a",)) == '^TMP("a")'

    def test_multiple_subscripts(self):
        assert _build_gref("TMP", ("a", "b", "c")) == '^TMP("a","b","c")'

    def test_null_subscript(self):
        assert _build_gref("TMP", ("a", "", "c")) == '^TMP("a","","c")'

    def test_all_null_subscripts(self):
        assert _build_gref("TMP", ("", "")) == '^TMP("","")'

    def test_numeric_subscripts_quoted(self):
        """Numeric subscripts are quoted like all subscripts."""
        assert _build_gref("G", ("1", "2")) == '^G("1","2")'

    def test_subscript_with_internal_quotes(self):
        """Internal quotes are doubled per MUMPS convention."""
        assert _build_gref("G", ('say "hi"',)) == '^G("say ""hi""")'

    def test_vista_rcr_pattern(self):
        """Real VistA pattern: ^UTILITY("%RCR","")."""
        assert _build_gref("UTILITY", ("%RCR", "")) == '^UTILITY("%RCR","")'

    def test_vista_mxmlprse_pattern(self):
        """Real VistA pattern: ^TMP("MXMLPRSE",12345,"ELE","")."""
        assert (
            _build_gref("TMP", ("MXMLPRSE", "12345", "ELE", ""))
            == '^TMP("MXMLPRSE","12345","ELE","")'
        )


# ---------------------------------------------------------------------------
# _parse_gref
# ---------------------------------------------------------------------------
@pytest.mark.runtime
class TestParseGref:
    """Tests for _parse_gref — parses MUMPS global reference strings."""

    def test_empty_string(self):
        assert IRISGlobalStorage._parse_gref("") is None

    def test_bare_global(self):
        assert IRISGlobalStorage._parse_gref("^X") == ("X", ())

    def test_bare_global_no_caret(self):
        assert IRISGlobalStorage._parse_gref("X") == ("X", ())

    def test_single_quoted_subscript(self):
        result = IRISGlobalStorage._parse_gref('^G("a")')
        assert result == ("G", ("a",))

    def test_multiple_quoted_subscripts(self):
        result = IRISGlobalStorage._parse_gref('^G("a","b","c")')
        assert result == ("G", ("a", "b", "c"))

    def test_null_subscript(self):
        result = IRISGlobalStorage._parse_gref('^TMP("a","","c")')
        assert result == ("TMP", ("a", "", "c"))

    def test_all_null_subscripts(self):
        result = IRISGlobalStorage._parse_gref('^G("","")')
        assert result == ("G", ("", ""))

    def test_unquoted_numeric_subscript(self):
        result = IRISGlobalStorage._parse_gref("^G(1,2,3)")
        assert result == ("G", ("1", "2", "3"))

    def test_mixed_quoted_and_numeric(self):
        result = IRISGlobalStorage._parse_gref('^G("a",1,"b")')
        assert result == ("G", ("a", "1", "b"))

    def test_doubled_internal_quotes(self):
        """Doubled quotes inside a quoted subscript represent a literal quote."""
        result = IRISGlobalStorage._parse_gref('^G("say ""hi""")')
        assert result == ("G", ('say "hi"',))

    def test_vista_rcr_pattern(self):
        result = IRISGlobalStorage._parse_gref('^UTILITY("%RCR","")')
        assert result == ("UTILITY", ("%RCR", ""))

    def test_vista_mxmlprse_pattern(self):
        result = IRISGlobalStorage._parse_gref('^TMP("MXMLPRSE","12345","ELE","")')
        assert result == ("TMP", ("MXMLPRSE", "12345", "ELE", ""))

    def test_roundtrip_with_build_gref(self):
        """_parse_gref should be the inverse of _build_gref."""
        cases = [
            ("TMP", ()),
            ("G", ("a",)),
            ("G", ("a", "b", "c")),
            ("TMP", ("a", "", "c")),
            ("UTILITY", ("%RCR", "")),
            ("G", ('say "hi"',)),
        ]
        for name, subs in cases:
            gref = _build_gref(name, subs)
            parsed = IRISGlobalStorage._parse_gref(gref)
            assert parsed == (name, subs), (
                f"Roundtrip failed for ({name}, {subs}): gref={gref!r}, parsed={parsed}"
            )

    def test_negative_numeric_subscript(self):
        result = IRISGlobalStorage._parse_gref("^G(-1)")
        assert result == ("G", ("-1",))

    def test_decimal_numeric_subscript(self):
        result = IRISGlobalStorage._parse_gref("^G(3.14)")
        assert result == ("G", ("3.14",))


# ---------------------------------------------------------------------------
# Float/int canonicalization (get() return value coercion)
# ---------------------------------------------------------------------------
@pytest.mark.runtime
class TestIRISGetCanonicalization:
    """Test the float/int canonicalization logic from iris_backend get().

    These test the standalone logic extracted from the get() method.
    The actual code path requires an IRIS connection, but the canonicalization
    rules can be verified by testing the same conditional branches directly.
    """

    @staticmethod
    def _canonicalize_numeric(val):
        """Reproduce the canonicalization logic from IRISGlobalStorage.get()."""
        if isinstance(val, float):
            if val == int(val):
                return str(int(val))
            s = f"{val:.15g}"
            if "." in s:
                s = s.rstrip("0").rstrip(".")
            if s.startswith("0."):
                s = s[1:]
            elif s.startswith("-0."):
                s = "-" + s[2:]
            return s
        if isinstance(val, int):
            return str(val)
        return str(val)

    def test_float_whole_number(self):
        """5.0 → '5' (MUMPS canonical, no trailing .0)."""
        assert self._canonicalize_numeric(5.0) == "5"

    def test_float_zero(self):
        """0.0 → '0'."""
        assert self._canonicalize_numeric(0.0) == "0"

    def test_float_negative_whole(self):
        """-3.0 → '-3'."""
        assert self._canonicalize_numeric(-3.0) == "-3"

    def test_float_with_fraction(self):
        """3.14 stays as '3.14'."""
        assert self._canonicalize_numeric(3.14) == "3.14"

    def test_float_leading_zero_removed(self):
        """0.5 → '.5' (MUMPS canonical: no leading zero)."""
        assert self._canonicalize_numeric(0.5) == ".5"

    def test_float_negative_leading_zero_removed(self):
        """-0.5 → '-.5' (MUMPS canonical: no leading zero)."""
        assert self._canonicalize_numeric(-0.5) == "-.5"

    def test_float_trailing_zeros_stripped(self):
        """1.10 → '1.1' (trailing zeros removed)."""
        assert self._canonicalize_numeric(1.10) == "1.1"

    def test_float_small_value(self):
        """0.001 → '.001'."""
        assert self._canonicalize_numeric(0.001) == ".001"

    def test_float_negative_small_value(self):
        """-0.001 → '-.001'."""
        assert self._canonicalize_numeric(-0.001) == "-.001"

    def test_int_positive(self):
        assert self._canonicalize_numeric(42) == "42"

    def test_int_zero(self):
        assert self._canonicalize_numeric(0) == "0"

    def test_int_negative(self):
        assert self._canonicalize_numeric(-7) == "-7"

    def test_large_float_whole(self):
        """1000000.0 → '1000000'."""
        assert self._canonicalize_numeric(1000000.0) == "1000000"

    def test_string_passthrough(self):
        """Non-numeric values pass through via str()."""
        assert self._canonicalize_numeric("hello") == "hello"
