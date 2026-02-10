"""Integration tests for ZWRITE subscript range filtering.

Spec 020 Phase 7 (T027): Tests ZWRITE with range subscripts like
ZW X(2:4), ZW ^A("A":"B"), ZW X(2:), ZW X(:2), ZW X(:).
"""

import pytest
from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime, MArray


@pytest.fixture()
def rt():
    """Fresh runtime with captured output."""
    runtime = MUMPSRuntime()
    runtime._output = []
    return runtime


@pytest.fixture()
def scope_with_array():
    """Scope with array X(0)..X(5) and X = 'root'."""

    x = MArray()
    x.value = "root"
    for i in range(6):
        x[str(i)] = str(i * 10)  # X(0)=0, X(1)=10, ...X(5)=50
    return {"X": x}


@pytest.fixture()
def scope_with_string_keys():
    """Scope with array A('A')..A('D')."""

    a = MArray()
    for c in ["A", "B", "C", "D"]:
        a[c] = c.lower()
    return {"A": a}


@pytest.fixture()
def scope_with_mixed_keys():
    """Scope with array M(1), M(2), M('A'), M('B')."""

    m = MArray()
    m["1"] = "one"
    m["2"] = "two"
    m["A"] = "alpha"
    m["B"] = "bravo"
    return {"M": m}


@pytest.mark.integration
class TestZwriteLocalRanges:
    """Test zwrite_local with range_start / range_end."""

    def test_numeric_range(self, rt, scope_with_array):
        """ZW X(2:4) outputs only X(2), X(3), X(4)."""
        rt.zwrite_local("X", (), scope_with_array, range_start="2", range_end="4")
        output = "".join(rt._output)
        assert "X(2)=20" in output
        assert "X(3)=30" in output
        assert "X(4)=40" in output
        assert "X(0)" not in output
        assert "X(1)" not in output
        assert "X(5)" not in output
        # Root value should NOT appear (range filtering active)
        assert output.startswith("X(")

    def test_open_end_range(self, rt, scope_with_array):
        """ZW X(3:) outputs X(3), X(4), X(5)."""
        rt.zwrite_local("X", (), scope_with_array, range_start="3")
        output = "".join(rt._output)
        assert "X(3)=30" in output
        assert "X(4)=40" in output
        assert "X(5)=50" in output
        assert "X(2)" not in output
        assert "X(1)" not in output

    def test_open_start_range(self, rt, scope_with_array):
        """ZW X(:2) outputs X(0), X(1), X(2)."""
        rt.zwrite_local("X", (), scope_with_array, range_end="2")
        output = "".join(rt._output)
        assert "X(0)=0" in output
        assert "X(1)=10" in output
        assert "X(2)=20" in output
        assert "X(3)" not in output
        assert "X(4)" not in output

    def test_string_range(self, rt, scope_with_string_keys):
        """ZW A("A":"B") outputs only A("A") and A("B")."""
        rt.zwrite_local("A", (), scope_with_string_keys, range_start="A", range_end="B")
        output = "".join(rt._output)
        assert 'A("A")=' in output
        assert 'A("B")=' in output
        assert '"C"' not in output
        assert '"D"' not in output

    def test_mixed_type_range(self, rt, scope_with_mixed_keys):
        """ZW M(1:2) outputs only M(1) and M(2) (numerics)."""
        rt.zwrite_local("M", (), scope_with_mixed_keys, range_start="1", range_end="2")
        output = "".join(rt._output)
        assert "M(1)=" in output
        assert "M(2)=" in output
        assert '"A"' not in output
        assert '"B"' not in output

    def test_no_range_shows_all(self, rt, scope_with_array):
        """ZW X (no range) outputs root + all subscripts."""
        rt.zwrite_local("X", (), scope_with_array)
        output = "".join(rt._output)
        assert 'X="root"' in output or "X=root" in output
        for i in range(6):
            assert f"X({i})=" in output

    def test_empty_range_match(self, rt, scope_with_array):
        """ZW X(10:20) with no matching subscripts outputs nothing."""
        rt.zwrite_local("X", (), scope_with_array, range_start="10", range_end="20")
        output = "".join(rt._output)
        assert output == ""


@pytest.mark.integration
class TestZwriteGlobalRanges:
    """Test zwrite_global with range_start / range_end."""

    def test_numeric_range(self, rt):
        """ZW ^A(2:4) on global with subscripts 0-5."""
        for i in range(6):
            rt.globals.set("A", (str(i),), str(i * 10))
        rt.zwrite_global("A", (), range_start="2", range_end="4")
        output = "".join(rt._output)
        assert "^A(2)=20" in output
        assert "^A(3)=30" in output
        assert "^A(4)=40" in output
        assert "^A(0)" not in output
        assert "^A(1)" not in output
        assert "^A(5)" not in output

    def test_open_end_range(self, rt):
        """ZW ^A(3:) outputs ^A(3), ^A(4), ^A(5)."""
        for i in range(6):
            rt.globals.set("A", (str(i),), str(i * 10))
        rt.zwrite_global("A", (), range_start="3")
        output = "".join(rt._output)
        assert "^A(3)=30" in output
        assert "^A(4)=40" in output
        assert "^A(5)=50" in output
        assert "^A(2)" not in output

    def test_open_start_range(self, rt):
        """ZW ^A(:2) outputs ^A(0), ^A(1), ^A(2)."""
        for i in range(6):
            rt.globals.set("A", (str(i),), str(i * 10))
        rt.zwrite_global("A", (), range_end="2")
        output = "".join(rt._output)
        assert "^A(0)=0" in output
        assert "^A(1)=10" in output
        assert "^A(2)=20" in output
        assert "^A(3)" not in output


@pytest.mark.integration
class TestZwriteRangeCodegen:
    """Test that ZWRITE with range syntax generates correct code."""

    def test_zw_range_generates_range_params(self):
        """ZWRITE X(2:4) generates range_start/range_end in code."""
        code = generate_python(
            "TEST\n S X(0)=0,X(1)=1,X(2)=2,X(3)=3,X(4)=4,X(5)=5\n ZWRITE X(2:4)\n Q\n",
            routine_name="TEST",
        )
        assert "range_start" in code
        assert "range_end" in code

    def test_zw_open_end_generates_range_start(self):
        """ZWRITE X(2:) generates only range_start."""
        code = generate_python(
            "TEST\n S X(0)=0,X(1)=1,X(2)=2\n ZWRITE X(2:)\n Q\n",
            routine_name="TEST",
        )
        assert "range_start" in code

    def test_zw_open_start_generates_range_end(self):
        """ZWRITE X(:2) generates only range_end."""
        code = generate_python(
            "TEST\n S X(0)=0,X(1)=1,X(2)=2\n ZWRITE X(:2)\n Q\n",
            routine_name="TEST",
        )
        assert "range_end" in code
