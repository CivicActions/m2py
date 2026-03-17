"""Tests for DIC override helper functions.

Tests the native DD field lookup, template expression evaluation,
and template level reading functions in tests/functional/munit/overrides/DIC.py.

These functions bypass buggy transpiled MUMPS code paths for:
1. DD field name lookups (non-integer IENs like '.01')
2. DICOMP-compiled CM code (uses D0 instead of field value)

Note: The DIC override module imports partial_override("DIC") at module
level, which requires a full MUMPS auto-importer stack. We work around
this by patching in a mock _base before importing the module.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock


from m2py.runtime import MArray, MUMPSRuntime

_DIC_OVERRIDE_PATH = (
    Path(__file__).resolve().parents[2]
    / "functional"
    / "munit"
    / "overrides"
    / "DIC.py"
)

# ---------------------------------------------------------------------------
# Module-level fixture: import overrides/DIC.py with mocked base
# ---------------------------------------------------------------------------


def _get_dic_module():
    """Load DIC.py override with a mocked partial_override to avoid needing
    the full MUMPS auto-importer stack."""
    mod_name = "_test_overrides_DIC"
    if mod_name in sys.modules:
        return sys.modules[mod_name]

    # Mock partial_override to return a dummy base module
    import m2py.runtime.overrides as ov_mod

    orig_partial = ov_mod.partial_override

    fake_base = types.ModuleType("_m2py_base_DIC")
    fake_base._routine_name = "DIC"
    fake_base._source_lines = []
    fake_base._label_lines = {}
    fake_base._line_map = {}
    fake_base._entry_function = lambda _rt, _scope=None, **kw: None

    def _mock_partial(name):
        if name == "DIC":
            return fake_base
        return orig_partial(name)

    ov_mod.partial_override = _mock_partial
    try:
        # Remove any cached import
        for key in list(sys.modules):
            if mod_name in key or "_m2py_base_DIC" in key:
                del sys.modules[key]

        spec = importlib.util.spec_from_file_location(mod_name, _DIC_OVERRIDE_PATH)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mod_name] = mod
        spec.loader.exec_module(mod)
    finally:
        ov_mod.partial_override = orig_partial

    return mod


_dic = _get_dic_module()


# ---------------------------------------------------------------------------
# Helpers: mock globals for DD metadata
# ---------------------------------------------------------------------------


def _make_globals_with_dd(dd_data: dict[tuple, str]) -> Any:
    """Create a mock globals object with DD data.

    dd_data maps (subscript_tuple) → value.
    Supports get() and order() with proper MUMPS collation.
    """
    g = MUMPSRuntime().globals

    for subs, val in dd_data.items():
        g.set("DD", subs, val)

    return g


def _make_globals_with_data(
    dd_data: dict[tuple, str],
    file_data: dict[tuple, str],
    gname: str = "DMU",
    dibt_data: dict[tuple, str] | None = None,
) -> Any:
    """Create globals with DD metadata and file data."""
    g = MUMPSRuntime().globals

    for subs, val in dd_data.items():
        g.set("DD", subs, val)

    for subs, val in file_data.items():
        g.set(gname, subs, val)

    if dibt_data:
        for subs, val in dibt_data.items():
            g.set("DIBT", subs, val)

    return g


# =============================================================================
# _lookup_dd_field
# =============================================================================


class TestLookupDdField:
    """Tests for _lookup_dd_field() — DD field name → IEN^name lookup."""

    def _lookup(self, g, file_num, field_name):
        rt = MagicMock()
        rt.globals = g
        return _dic._lookup_dd_field(rt, file_num, field_name)

    def test_basic_field_lookup(self):
        """Field name found in B-index returns 'field_num^display_name'."""
        g = _make_globals_with_dd(
            {
                ("100", "B", "NAME", ".01"): "",
                ("100", ".01", "0"): "NAME^F^^",
            }
        )
        result = self._lookup(g, "100", "NAME")
        assert result == ".01^NAME"

    def test_field_not_found(self):
        """Returns None when field name is not in B-index."""
        g = _make_globals_with_dd({})
        result = self._lookup(g, "100", "NOSUCH")
        assert result is None

    def test_case_insensitive_fallback(self):
        """Falls back to uppercase lookup if original case not found."""
        g = _make_globals_with_dd(
            {
                ("100", "B", "NAME", ".01"): "",
                ("100", ".01", "0"): "NAME^F^^",
            }
        )
        result = self._lookup(g, "100", "name")
        # "name" not found, tries "NAME" which exists
        assert result is not None
        assert ".01" in result

    def test_display_name_from_definition(self):
        """Display name is extracted from ^DD(file,field,0) piece 1."""
        g = _make_globals_with_dd(
            {
                ("200", "B", "COUNTY", "1"): "",
                ("200", "1", "0"): "COUNTY^P5'X^0;2^S",
            }
        )
        result = self._lookup(g, "200", "COUNTY")
        assert result == "1^COUNTY"

    def test_missing_field_def_uses_input_name(self):
        """If ^DD(file,field,0) is missing, uses the input field name."""
        g = _make_globals_with_dd(
            {
                ("200", "B", "STATUS", "3"): "",
                # No ("200", "3", "0") definition
            }
        )
        result = self._lookup(g, "200", "STATUS")
        assert result == "3^STATUS"


# =============================================================================
# _dd_aware_entry_function
# =============================================================================


class TestDdAwareEntryFunction:
    """Tests for _dd_aware_entry_function() — DD field lookup interception."""

    def _call(self, scope, g):
        rt = MUMPSRuntime()
        rt._globals = g
        # Mock _base._entry_function to track fallthrough
        base_called = [False]
        orig = _dic._base

        class FakeBase:
            @staticmethod
            def _entry_function(_rt, _scope=None, **kwargs):
                base_called[0] = True

        _dic._base = FakeBase()
        try:
            _dic._dd_aware_entry_function(rt, _scope=scope)
        finally:
            _dic._base = orig

        return base_called[0]

    def test_intercepts_dd_field_lookup(self):
        """DIC='^DD(100,' with X='NAME' is handled natively."""
        g = _make_globals_with_dd(
            {
                ("100", "B", "NAME", ".01"): "",
                ("100", ".01", "0"): "NAME^F^^",
            }
        )

        scope = {
            "DIC": MArray(),
            "X": MArray(),
            "Y": MArray(),
        }
        scope["DIC"].value = "^DD(100,"
        scope["X"].value = "NAME"

        fell_through = self._call(scope, g)
        assert not fell_through, "Should NOT fall through to base"
        assert scope["Y"].value == ".01^NAME"

    def test_falls_through_for_non_dd_dic(self):
        """DIC not starting with '^DD(' falls through to base."""
        g = _make_globals_with_dd({})

        scope = {
            "DIC": MArray(),
            "X": MArray(),
        }
        scope["DIC"].value = "^DMU(1009.802,"
        scope["X"].value = "test"

        fell_through = self._call(scope, g)
        assert fell_through, "Should fall through to base for non-DD DIC"

    def test_falls_through_for_numeric_x(self):
        """X value containing digits falls through (not a simple field name)."""
        g = _make_globals_with_dd({})

        scope = {
            "DIC": MArray(),
            "X": MArray(),
        }
        scope["DIC"].value = "^DD(100,"
        scope["X"].value = "123"  # Not alphabetic

        fell_through = self._call(scope, g)
        assert fell_through, "Should fall through for non-alphabetic X"

    def test_falls_through_for_field_not_found(self):
        """Field name not in B-index falls through to base."""
        g = _make_globals_with_dd({})

        scope = {
            "DIC": MArray(),
            "X": MArray(),
        }
        scope["DIC"].value = "^DD(100,"
        scope["X"].value = "NOSUCHFIELD"

        fell_through = self._call(scope, g)
        assert fell_through, "Should fall through when field not in DD"

    def test_falls_through_for_no_scope(self):
        """No scope provided falls through."""
        base_called = [False]
        orig = _dic._base

        class FakeBase:
            @staticmethod
            def _entry_function(_rt, _scope=None, **kwargs):
                base_called[0] = True

        _dic._base = FakeBase()
        try:
            _dic._dd_aware_entry_function(MUMPSRuntime(), _scope=None)
        finally:
            _dic._base = orig

        assert base_called[0]


# =============================================================================
# _eval_template_expr
# =============================================================================


class TestEvalTemplateExpr:
    """Tests for _eval_template_expr() — native template expression evaluator.

    This function evaluates sort template expressions natively, bypassing
    DICOMP-compiled CM code which has bugs with field value resolution.
    """

    def _setup_dd_and_data(self):
        """Set up DD metadata and data for file 1009.802 (DMU test file).

        Creates a file with fields:
        - .01 NAME (piece 1 of node 0)
        - 1 COUNTY (pointer, piece 2 of node 0)
        - 2 STATE (piece 3 of node 0)
        """
        dd_data = {
            ("1009.802", "B", "NAME", ".01"): "",
            ("1009.802", ".01", "0"): "NAME^RF^^0;1^",
            ("1009.802", "B", "COUNTY", "1"): "",
            ("1009.802", "1", "0"): "COUNTY^P5'^0;2^",
            ("1009.802", "B", "STATE", "2"): "",
            ("1009.802", "2", "0"): "STATE^F^^0;3^",
        }
        file_data = {
            ("1",): "",  # IEN 1 header
            ("1", "0"): "NEW YORK^36^NY",
            ("2",): "",
            ("2", "0"): "NEW JERSEY^21^NJ",
            ("3",): "",
            ("3", "0"): "CALIFORNIA^58^CA",
            ("4",): "",
            ("4", "0"): "NEW BRUNSWICK^5^NB",
            # IEN 5 — name shorter than 3 chars
            ("5",): "",
            ("5", "0"): "OH^88^OH",
        }
        # Also need county sub-entries for COUNT(COUNTY)
        county_dd = {
            # Subfile 1009.8021 for COUNTY multiple
            ("1009.8021", ".01", "0"): "COUNTY^F^^0;1^",
        }
        dd_data.update(county_dd)

        return _make_globals_with_data(dd_data, file_data)

    def _eval(self, g, ien, label, file_num="1009.802"):
        return _dic._eval_template_expr(g, "DMU", (), ien, label, file_num)

    # --- Empty/None handling ---

    def test_empty_label_returns_none(self):
        g = _make_globals_with_dd({})
        result = self._eval(g, "1", "")
        assert result is None

    def test_none_like_label_returns_none(self):
        g = _make_globals_with_dd({})
        result = self._eval(g, "1", "   ")
        # After strip, empty — but we pass it directly
        # The function checks `if not label` at the top
        assert result is None

    # --- $E(FIELD,start,end)="value" equality comparisons ---

    def test_extract_equals_match(self):
        """$E(NAME,1,3)="NEW" returns 1 for 'NEW YORK'."""
        g = self._setup_dd_and_data()
        result = self._eval(g, "1", '$E(NAME,1,3)="NEW"')
        assert result == 1

    def test_extract_equals_no_match(self):
        """$E(NAME,1,3)="NEW" returns 0 for 'CALIFORNIA'."""
        g = self._setup_dd_and_data()
        result = self._eval(g, "3", '$E(NAME,1,3)="NEW"')
        assert result == 0

    def test_extract_equals_exact_boundary(self):
        """$E(NAME,1,3)="NEW" returns 1 for 'NEW BRUNSWICK'."""
        g = self._setup_dd_and_data()
        result = self._eval(g, "4", '$E(NAME,1,3)="NEW"')
        assert result == 1

    def test_extract_equals_short_value(self):
        """$E(NAME,1,3)="NEW" returns 0 for short string 'OH'."""
        g = self._setup_dd_and_data()
        result = self._eval(g, "5", '$E(NAME,1,3)="NEW"')
        assert result == 0

    def test_extract_equals_empty_target(self):
        """$E(NAME,1,3)="" matches when field value is empty."""
        dd_data = {
            ("999", "B", "NAME", ".01"): "",
            ("999", ".01", "0"): "NAME^F^^0;1^",
        }
        file_data = {("1", "0"): "^other"}
        g = _make_globals_with_data(dd_data, file_data)
        result = self._eval(g, "1", '$E(NAME,1,3)=""', file_num="999")
        assert result == 1

    def test_extract_equals_full_extract(self):
        """$EXTRACT(NAME,1,2)="NE" uses long form."""
        g = self._setup_dd_and_data()
        result = self._eval(g, "1", '$EXTRACT(NAME,1,2)="NE"')
        assert result == 1

    def test_extract_equals_case_insensitive_function(self):
        """$e(NAME,1,3)="NEW" (lowercase) still matches."""
        g = self._setup_dd_and_data()
        result = self._eval(g, "1", '$e(NAME,1,3)="NEW"')
        assert result == 1

    # --- Plain $E(FIELD,start,end) — substring extraction ---

    def test_plain_extract(self):
        """$E(NAME,1,3) returns substring of field value."""
        g = self._setup_dd_and_data()
        result = self._eval(g, "1", "$E(NAME,1,3)")
        assert result == "NEW"

    def test_plain_extract_short_value(self):
        """$E(NAME,1,3) on value shorter than range returns partial string."""
        g = self._setup_dd_and_data()
        result = self._eval(g, "5", "$E(NAME,1,3)")
        assert result == "OH"

    def test_plain_extract_unknown_field(self):
        """$E(NOSUCH,1,3) for unknown field returns empty string."""
        g = self._setup_dd_and_data()
        result = self._eval(g, "1", "$E(NOSUCH,1,3)")
        assert result == ""

    # --- Plain field name —  direct field value ---

    def test_plain_field_name(self):
        """Just 'NAME' returns the field value."""
        g = self._setup_dd_and_data()
        result = self._eval(g, "1", "NAME")
        assert result == "NEW YORK"

    def test_plain_field_name_unknown(self):
        """Unknown plain field name returns None (not recognized)."""
        g = self._setup_dd_and_data()
        result = self._eval(g, "1", "UNKNOWNFIELD")
        assert result is None

    # --- COUNT(FIELD) ---

    def test_count_no_entries(self):
        """COUNT(COUNTY) returns 0 when no sub-entries exist."""
        g = self._setup_dd_and_data()
        # IEN 3 (CALIFORNIA) has no county sub-entries
        result = self._eval(g, "3", "COUNT(COUNTY)")
        assert result == 0

    # --- Unrecognized expression ---

    def test_unrecognized_expression(self):
        """Complex expression not matching any pattern returns None."""
        g = self._setup_dd_and_data()
        result = self._eval(g, "1", "X+Y*Z")
        assert result is None


# =============================================================================
# _read_template_levels
# =============================================================================


class TestReadTemplateLevels:
    """Tests for _read_template_levels() — ^DIBT template level parsing."""

    def _read(self, g, ien):
        return _dic._read_template_levels(g, ien)

    def test_reads_levels_in_order(self):
        """Reads levels 1, 2, 3 from ^DIBT(ien,2,level,0)."""
        g = MUMPSRuntime().globals
        g.set("DIBT", ("1", "2", "1", "0"), '100^^NAME^"^^^^^^4')
        g.set("DIBT", ("1", "2", "2", "0"), '100^^COUNTY^-"^^^^^^4')

        levels = self._read(g, "1")
        assert len(levels) == 2
        assert levels[0]["label"] == "NAME"
        assert levels[1]["label"] == "COUNTY"

    def test_parses_descending_flag(self):
        """'-' in flags means descending sort."""
        g = MUMPSRuntime().globals
        g.set("DIBT", ("1", "2", "1", "0"), '100^^FIELD^-"^^^^^^4')

        levels = self._read(g, "1")
        assert levels[0]["descending"] is True

    def test_parses_ascending_by_default(self):
        """No '-' in flags means ascending sort."""
        g = MUMPSRuntime().globals
        g.set("DIBT", ("1", "2", "1", "0"), '100^^FIELD^"^^^^^^4')

        levels = self._read(g, "1")
        assert levels[0]["descending"] is False

    def test_reads_cm_and_qcon(self):
        """Reads CM, GET, QCON, TXT code nodes."""
        g = MUMPSRuntime().globals
        g.set("DIBT", ("1", "2", "1", "0"), '100^^FIELD^"^^^^^^4')
        g.set("DIBT", ("1", "2", "1", "CM"), " I D0>0 S DISX(1)=X")
        g.set("DIBT", ("1", "2", "1", "GET"), " I D0>0 S DISX(1)=X")
        g.set("DIBT", ("1", "2", "1", "QCON"), 'I DISX(1)\'=""')
        g.set("DIBT", ("1", "2", "1", "TXT"), " COUNT(COUNTY) not null")

        levels = self._read(g, "1")
        assert levels[0]["CM"] == " I D0>0 S DISX(1)=X"
        assert levels[0]["QCON"] == 'I DISX(1)\'=""'
        assert levels[0]["TXT"] == " COUNT(COUNTY) not null"

    def test_reads_f_and_t_values(self):
        """Reads F and T range values for boolean screens."""
        g = MUMPSRuntime().globals
        g.set("DIBT", ("1", "2", "1", "0"), '100^^$E(NAME,1,3)="NEW"^"@B^;L1^^^^^4')
        g.set("DIBT", ("1", "2", "1", "F"), "0")
        g.set("DIBT", ("1", "2", "1", "T"), "1")

        levels = self._read(g, "1")
        assert levels[0]["F"] == "0"
        assert levels[0]["T"] == "1"

    def test_empty_template(self):
        """Returns empty list for template with no levels."""
        g = MUMPSRuntime().globals
        levels = self._read(g, "999")
        assert levels == []

    def test_preserves_raw_zero(self):
        """Level dict includes raw_zero for DPP construction."""
        g = MUMPSRuntime().globals
        g.set("DIBT", ("1", "2", "1", "0"), '100^^FIELD^"^^^^^^4')

        levels = self._read(g, "1")
        assert levels[0]["raw_zero"] == '100^^FIELD^"^^^^^^4'

    def test_parses_field_num(self):
        """Field number extracted from zero-node piece 2."""
        g = MUMPSRuntime().globals
        g.set("DIBT", ("1", "2", "1", "0"), '100^.01^NAME^"')

        levels = self._read(g, "1")
        assert levels[0]["field_num"] == ".01"

    def test_multiple_flags(self):
        """Flags like '@B' and '-' are preserved."""
        g = MUMPSRuntime().globals
        g.set("DIBT", ("1", "2", "1", "0"), '100^^EXPR^"@B^;L1^^^^^4')

        levels = self._read(g, "1")
        assert levels[0]["flags"] == '"@B'
        assert levels[0]["descending"] is False  # no '-' in flags
