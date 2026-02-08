"""Unit tests for VarRef.

Tests the unified variable reference dataclass per
data-model.md.

Feature: 018-unified-variable-system
Requirements: FR-001
"""

from m2py.core.scope import VarRef


class TestVarRefConstruction:
    """Tests for VarRef construction."""

    def test_simple_local(self):
        """Simple local variable reference."""
        ref = VarRef(name="X")
        assert ref.name == "X"
        assert not ref.is_global
        assert not ref.is_naked
        assert ref.subscripts == []

    def test_with_subscripts(self):
        """Variable with subscripts."""
        ref = VarRef(name="A", subscripts=[1, 2])
        assert ref.name == "A"
        assert ref.subscripts == [1, 2]

    def test_global_variable(self):
        """Global variable reference."""
        ref = VarRef(name="GLO", is_global=True)
        assert ref.name == "GLO"
        assert ref.is_global

    def test_naked_reference(self):
        """Naked global reference (^(subs))."""
        ref = VarRef(is_global=True, is_naked=True, subscripts=[1])
        assert ref.is_global
        assert ref.is_naked
        assert ref.name is None


class TestVarRefPythonName:
    """Tests for automatic python_name computation."""

    def test_auto_computed(self):
        """python_name is computed from name."""
        ref = VarRef(name="TEST")
        assert ref.python_name == "TEST"

    def test_percent_prefix(self):
        """% prefix is translated."""
        ref = VarRef(name="%FOO")
        assert ref.python_name == "_pct_FOO"

    def test_explicit_python_name(self):
        """Explicit python_name is preserved."""
        ref = VarRef(name="X", python_name="custom")
        assert ref.python_name == "custom"


class TestVarRefToAccessString:
    """Tests for to_access_string() method."""

    def test_simple_local(self):
        """Simple local variable."""
        ref = VarRef(name="X")
        assert ref.to_access_string() == "X"

    def test_with_subscripts(self):
        """Variable with subscripts."""
        ref = VarRef(name="X", subscripts=[1, 2])
        assert ref.to_access_string() == "X(1,2)"

    def test_global_no_subscripts(self):
        """Global without subscripts."""
        ref = VarRef(name="GLO", is_global=True)
        assert ref.to_access_string() == "^GLO"

    def test_global_with_subscripts(self):
        """Global with subscripts."""
        ref = VarRef(name="GLO", is_global=True, subscripts=[1, 2])
        assert ref.to_access_string() == "^GLO(1,2)"

    def test_naked_reference(self):
        """Naked reference ^(subs)."""
        ref = VarRef(is_global=True, is_naked=True, subscripts=[1])
        assert ref.to_access_string() == "^(1)"

    def test_subscript_canonicalization(self):
        """Subscripts are canonicalized in access string."""
        ref = VarRef(name="A", subscripts=[1.0, "text"])
        # 1.0 should become "1"
        assert ref.to_access_string() == "A(1,text)"


class TestVarRefWithSubscripts:
    """Tests for with_subscripts() method."""

    def test_append_subscripts(self):
        """Appending subscripts creates new VarRef."""
        ref1 = VarRef(name="A", subscripts=[1])
        ref2 = ref1.with_subscripts([2, 3])

        # Original unchanged
        assert ref1.subscripts == [1]

        # New ref has appended subscripts
        assert ref2.subscripts == [1, 2, 3]
        assert ref2.name == "A"

    def test_preserves_attributes(self):
        """with_subscripts preserves other attributes."""
        ref1 = VarRef(name="GLO", is_global=True, subscripts=[1])
        ref2 = ref1.with_subscripts([2])

        assert ref2.is_global
        assert ref2.name == "GLO"


class TestVarRefEquality:
    """Tests for VarRef equality."""

    def test_equal_simple(self):
        """Equal simple VarRefs."""
        ref1 = VarRef(name="X")
        ref2 = VarRef(name="X")
        assert ref1 == ref2

    def test_equal_with_subscripts(self):
        """Equal VarRefs with subscripts."""
        ref1 = VarRef(name="A", subscripts=[1, 2])
        ref2 = VarRef(name="A", subscripts=[1, 2])
        assert ref1 == ref2

    def test_not_equal_different_name(self):
        """Different names are not equal."""
        ref1 = VarRef(name="X")
        ref2 = VarRef(name="Y")
        assert ref1 != ref2

    def test_not_equal_different_subscripts(self):
        """Different subscripts are not equal."""
        ref1 = VarRef(name="A", subscripts=[1])
        ref2 = VarRef(name="A", subscripts=[2])
        assert ref1 != ref2

    def test_not_equal_global_vs_local(self):
        """Global vs local are not equal."""
        ref1 = VarRef(name="X", is_global=False)
        ref2 = VarRef(name="X", is_global=True)
        assert ref1 != ref2


class TestVarRefMugjPatterns:
    """Tests based on MUGJ test patterns."""

    def test_v1idnm_patterns(self):
        """Variable patterns from V1IDNM indirection tests."""
        # Simple variables used in tests
        for name in ["A", "B", "C", "X", "Y", "Z"]:
            ref = VarRef(name=name)
            assert ref.to_access_string() == name

    def test_vv2vnia_subscript_patterns(self):
        """Subscript patterns from VV2VNIA tests."""
        # Multi-level subscripts
        ref = VarRef(name="A", subscripts=[1, 2])
        assert ref.to_access_string() == "A(1,2)"

        # Appending subscripts (like name indirection resolution)
        ref2 = ref.with_subscripts([5, 6])
        assert ref2.to_access_string() == "A(1,2,5,6)"
