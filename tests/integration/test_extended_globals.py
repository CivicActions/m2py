"""Integration tests for extended global references.

Spec 021 Phase 15: Tests that extended global references (^|"env"|NAME
and ^["env"]NAME) generate correct code and execute properly.
"""

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


@pytest.fixture
def execute_mumps():
    """Execute MUMPS code through the full pipeline (parse → codegen → exec)."""

    def _execute(source: str):
        python_code = generate_python(source)
        runtime = MUMPSRuntime()
        return runtime.execute(python_code, capture_output=True)

    return _execute


class TestExtendedGlobalSetGet:
    """Test SET and GET with extended globals."""

    def test_pipe_set_and_write(self, execute_mumps):
        """S ^|"NS"|X=42 W ^|"NS"|X → 42"""
        result = execute_mumps('TEST\n S ^|"NS"|X=42 W ^|"NS"|X\n Q\n')
        assert result.output == "42"

    def test_bracket_set_and_write(self, execute_mumps):
        """S ^["NS"]X=42 W ^["NS"]X → 42"""
        result = execute_mumps('TEST\n S ^["NS"]X=42 W ^["NS"]X\n Q\n')
        assert result.output == "42"

    def test_namespace_isolation(self, execute_mumps):
        """Values in different namespaces are isolated."""
        code = (
            "TEST\n"
            ' S ^|"NS1"|X="hello"\n'
            ' S ^|"NS2"|X="world"\n'
            ' W ^|"NS1"|X,^|"NS2"|X\n'
            " Q\n"
        )
        result = execute_mumps(code)
        assert result.output == "helloworld"

    def test_namespace_isolated_from_default(self, execute_mumps):
        """Extended global namespace is isolated from default."""
        code = 'TEST\n S ^X="default"\n S ^|"NS"|X="namespaced"\n W ^X,^|"NS"|X\n Q\n'
        result = execute_mumps(code)
        assert result.output == "defaultnamespaced"

    def test_subscripted_extended_global(self, execute_mumps):
        """Extended globals with subscripts."""
        code = (
            'TEST\n S ^|"NS"|X(1)="a",^|"NS"|X(2)="b"\n W ^|"NS"|X(1),^|"NS"|X(2)\n Q\n'
        )
        result = execute_mumps(code)
        assert result.output == "ab"


class TestExtendedGlobalData:
    """Test $DATA with extended globals."""

    def test_data_defined(self, execute_mumps):
        """$D(^|"NS"|X) returns 1 for defined value."""
        code = 'TEST\n S ^|"NS"|X=1\n W $D(^|"NS"|X)\n Q\n'
        result = execute_mumps(code)
        assert result.output == "1"

    def test_data_undefined(self, execute_mumps):
        """$D(^|"NS"|X) returns 0 for undefined value."""
        code = 'TEST\n W $D(^|"NS"|X)\n Q\n'
        result = execute_mumps(code)
        assert result.output == "0"


class TestExtendedGlobalOrder:
    """Test $ORDER with extended globals."""

    def test_order_traversal(self, execute_mumps):
        """$O(^|"NS"|X("")) iterates namespace globals."""
        code = (
            "TEST\n"
            ' S ^|"NS"|X("a")=1,^|"NS"|X("b")=2,^|"NS"|X("c")=3\n'
            ' S Y=$O(^|"NS"|X("")) W Y,","\n'
            ' S Y=$O(^|"NS"|X(Y)) W Y\n'
            " Q\n"
        )
        result = execute_mumps(code)
        assert result.output == "a,b"


class TestExtendedGlobalKill:
    """Test KILL with extended globals."""

    def test_kill_extended_global(self, execute_mumps):
        """K ^|"NS"|X removes the value in namespace."""
        code = 'TEST\n S ^|"NS"|X=1\n K ^|"NS"|X\n W $D(^|"NS"|X)\n Q\n'
        result = execute_mumps(code)
        assert result.output == "0"

    def test_kill_does_not_affect_other_ns(self, execute_mumps):
        """KILL in one namespace doesn't affect another."""
        code = (
            "TEST\n"
            ' S ^|"NS1"|X=1,^|"NS2"|X=2\n'
            ' K ^|"NS1"|X\n'
            ' W $D(^|"NS1"|X),$D(^|"NS2"|X)\n'
            " Q\n"
        )
        result = execute_mumps(code)
        assert result.output == "01"


class TestExtendedGlobalMerge:
    """Test MERGE with extended globals."""

    def test_merge_to_extended_global(self, execute_mumps):
        """MERGE ^|"NS"|Y=^X copies default to namespace."""
        code = (
            "TEST\n"
            ' S ^X(1)="a",^X(2)="b"\n'
            ' M ^|"NS"|Y=^X\n'
            ' W ^|"NS"|Y(1),^|"NS"|Y(2)\n'
            " Q\n"
        )
        result = execute_mumps(code)
        assert result.output == "ab"

    def test_merge_from_extended_global(self, execute_mumps):
        """MERGE ^Y=^|"NS"|X copies namespace to default."""
        code = (
            "TEST\n"
            ' S ^|"NS"|X(1)="a",^|"NS"|X(2)="b"\n'
            ' M ^Y=^|"NS"|X\n'
            " W ^Y(1),^Y(2)\n"
            " Q\n"
        )
        result = execute_mumps(code)
        assert result.output == "ab"


class TestExtendedGlobalGet:
    """Test $GET with extended globals."""

    def test_get_defined(self, execute_mumps):
        """$G(^|"NS"|X) returns the value when defined."""
        code = 'TEST\n S ^|"NS"|X=42\n W $G(^|"NS"|X)\n Q\n'
        result = execute_mumps(code)
        assert result.output == "42"

    def test_get_undefined_default(self, execute_mumps):
        """$G(^|"NS"|X,"def") returns default when undefined."""
        code = 'TEST\n W $G(^|"NS"|X,"none")\n Q\n'
        result = execute_mumps(code)
        assert result.output == "none"
