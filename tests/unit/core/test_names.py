"""Unit tests for NameTranslator.

Tests the bidirectional MUMPS ↔ Python name translation per
contracts/name-translator.md.

Feature: 018-unified-variable-system
Requirements: FR-005 through FR-009
"""

import keyword


from m2py.core.names import NameTranslator, translate_name


class TestToPython:
    """Tests for NameTranslator.to_python()"""

    def test_basic_unchanged(self):
        """Regular MUMPS names pass through unchanged."""
        assert NameTranslator.to_python("TEST") == "TEST"
        assert NameTranslator.to_python("VCOMP") == "VCOMP"
        assert NameTranslator.to_python("X") == "X"
        assert NameTranslator.to_python("A123") == "A123"

    def test_percent_prefix(self):
        """% prefix becomes _pct_"""
        assert NameTranslator.to_python("%ABC") == "_pct_ABC"
        assert NameTranslator.to_python("%START") == "_pct_START"
        assert NameTranslator.to_python("%") == "_pct_"  # Just % character

    def test_pure_numeric(self):
        """Pure numeric strings get _n_ prefix."""
        assert NameTranslator.to_python("01") == "_n_01"
        assert NameTranslator.to_python("1") == "_n_1"
        assert NameTranslator.to_python("461") == "_n_461"
        assert NameTranslator.to_python("0123") == "_n_0123"

    def test_python_keywords(self):
        """Python keywords get _m_ prefix."""
        assert NameTranslator.to_python("if") == "_m_if"
        assert NameTranslator.to_python("for") == "_m_for"
        assert NameTranslator.to_python("while") == "_m_while"
        assert NameTranslator.to_python("class") == "_m_class"
        assert NameTranslator.to_python("return") == "_m_return"

    def test_empty_string(self):
        """Empty string (labelless preamble) becomes _preamble."""
        assert NameTranslator.to_python("") == "_preamble"

    def test_case_preservation(self):
        """Case is preserved in translation."""
        assert NameTranslator.to_python("HELLO") == "HELLO"
        assert NameTranslator.to_python("hello") == "hello"
        assert NameTranslator.to_python("HeLLo") == "HeLLo"


class TestFromPython:
    """Tests for NameTranslator.from_python()"""

    def test_basic_unchanged(self):
        """Regular names pass through unchanged."""
        assert NameTranslator.from_python("TEST") == "TEST"
        assert NameTranslator.from_python("VCOMP") == "VCOMP"
        assert NameTranslator.from_python("X") == "X"

    def test_pct_prefix(self):
        """_pct_ prefix becomes %"""
        assert NameTranslator.from_python("_pct_ABC") == "%ABC"
        assert NameTranslator.from_python("_pct_START") == "%START"
        assert NameTranslator.from_python("_pct_") == "%"

    def test_n_prefix(self):
        """_n_ prefix is removed (numeric name)."""
        assert NameTranslator.from_python("_n_01") == "01"
        assert NameTranslator.from_python("_n_1") == "1"
        assert NameTranslator.from_python("_n_461") == "461"

    def test_m_prefix(self):
        """_m_ prefix is removed (keyword)."""
        assert NameTranslator.from_python("_m_if") == "if"
        assert NameTranslator.from_python("_m_for") == "for"
        assert NameTranslator.from_python("_m_while") == "while"

    def test_preamble(self):
        """_preamble becomes empty string."""
        assert NameTranslator.from_python("_preamble") == ""

    def test_empty_string(self):
        """Empty string stays empty."""
        assert NameTranslator.from_python("") == ""

    def test_unknown_prefix_unchanged(self):
        """Unknown prefixes pass through unchanged (identity fallback).

        Names that start with underscore but don't match known prefixes
        (_pct_, _n_, _m_, _preamble) are returned unchanged. This ensures
        internal Python names like _scope, _rt don't get corrupted.
        """
        assert NameTranslator.from_python("_unknown_FOO") == "_unknown_FOO"
        assert NameTranslator.from_python("_xyz_bar") == "_xyz_bar"
        # Partial prefix matches should not translate
        assert NameTranslator.from_python("_p_FOO") == "_p_FOO"  # Not _pct_
        assert NameTranslator.from_python("_pc_FOO") == "_pc_FOO"  # Not _pct_
        # Internal runtime names should be unchanged
        assert NameTranslator.from_python("_scope") == "_scope"
        assert NameTranslator.from_python("_rt") == "_rt"


class TestRoundTrip:
    """Tests that to_python and from_python are inverses."""

    def test_roundtrip_basic(self):
        """Round-trip identity for basic names."""
        for name in ["TEST", "VCOMP", "X", "A123", "ABC"]:
            assert NameTranslator.from_python(NameTranslator.to_python(name)) == name

    def test_roundtrip_percent(self):
        """Round-trip identity for percent-prefixed names."""
        for name in ["%ABC", "%START", "%FOO", "%"]:
            assert NameTranslator.from_python(NameTranslator.to_python(name)) == name

    def test_roundtrip_numeric(self):
        """Round-trip identity for pure numeric names."""
        for name in ["01", "1", "461", "0123", "0"]:
            assert NameTranslator.from_python(NameTranslator.to_python(name)) == name

    def test_roundtrip_keywords(self):
        """Round-trip identity for Python keywords."""
        for name in ["if", "for", "while", "class", "return", "def"]:
            if keyword.iskeyword(name):
                assert (
                    NameTranslator.from_python(NameTranslator.to_python(name)) == name
                )

    def test_roundtrip_empty(self):
        """Round-trip identity for empty string."""
        assert NameTranslator.from_python(NameTranslator.to_python("")) == ""


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_translate_name(self):
        """translate_name delegates to to_python."""
        assert translate_name("TEST") == "TEST"
        assert translate_name("%ABC") == "_pct_ABC"
        assert translate_name("01") == "_n_01"


class TestPythonKeywordsClassVar:
    """Tests for PYTHON_KEYWORDS class variable."""

    def test_contains_known_keywords(self):
        """Check that common Python keywords are present."""
        assert "if" in NameTranslator.PYTHON_KEYWORDS
        assert "for" in NameTranslator.PYTHON_KEYWORDS
        assert "while" in NameTranslator.PYTHON_KEYWORDS
        assert "class" in NameTranslator.PYTHON_KEYWORDS
        assert "def" in NameTranslator.PYTHON_KEYWORDS

    def test_is_frozen(self):
        """PYTHON_KEYWORDS should be a set (immutable after creation)."""
        assert isinstance(NameTranslator.PYTHON_KEYWORDS, set)


class TestMugjPatterns:
    """Tests based on MUGJ test patterns from research.md."""

    def test_v1idnm_patterns(self):
        """Names used in V1IDNM indirection tests."""
        # These are the variable names used in MUGJ tests
        names = ["A", "B", "C", "D", "X", "Y", "Z"]
        for name in names:
            py_name = NameTranslator.to_python(name)
            assert py_name == name  # Simple names unchanged
            assert NameTranslator.from_python(py_name) == name

    def test_vv2vni_global_patterns(self):
        """Global variable patterns (without ^ prefix for simple tests)."""
        # The ^ prefix is NOT part of the variable name stored in scope
        # It indicates global storage, handled separately
        names = ["GLO", "GVN", "V", "VV"]
        for name in names:
            assert NameTranslator.is_valid_varname(name)
            assert NameTranslator.to_python(name) == name


class TestNameTranslatorLive:
    """Tests for NameTranslator LIVE coverage gaps."""

    def test_to_python_keyword(self):
        """Python keyword is escaped with _m_ prefix."""
        assert NameTranslator.to_python("if") == "_m_if"
        assert NameTranslator.to_python("for") == "_m_for"
        assert NameTranslator.to_python("while") == "_m_while"

    def test_to_python_percent(self):
        """Percent variable gets _pct_ prefix."""
        assert NameTranslator.to_python("%X") == "_pct_X"

    def test_from_python_keyword(self):
        """from_python reverses keyword escaping."""
        assert NameTranslator.from_python("_m_if") == "if"
        assert NameTranslator.from_python("_m_for") == "for"

    def test_from_python_percent(self):
        """from_python reverses percent prefix."""
        assert NameTranslator.from_python("_pct_X") == "%X"

    def test_from_python_regular(self):
        """from_python passes through regular names."""
        assert NameTranslator.from_python("X") == "X"
        assert NameTranslator.from_python("MYVAR") == "MYVAR"

    def test_roundtrip(self):
        """to_python → from_python roundtrip preserves name."""
        for name in ["X", "%FOO", "if", "for", "class", "NORMAL"]:
            py = NameTranslator.to_python(name)
            assert NameTranslator.from_python(py) == name


# =============================================================================
# subscripts.py: Canonicalization edge cases
# =============================================================================
