"""Integration tests for unconditional LVUNDEF (Phase 12: US10).

T118: Integration test transpiling LVUNDEF scenarios.
"""

import pytest

from m2py.codegen import generate_python
from m2py.core.exceptions import LVUNDEFError
from m2py.core.scope import CurrentScope
from m2py.runtime import MArray, MUMPSRuntime


def _run(mumps_code: str) -> tuple[MUMPSRuntime, str]:
    """Transpile and execute MUMPS code, return runtime and output."""
    python_code = generate_python(mumps_code)
    runtime = MUMPSRuntime()
    result = runtime.execute(python_code, capture_output=True)
    return runtime, result.output


@pytest.mark.codegen
class TestLVUNDEFCurrentScope:
    """T118: Integration tests for unconditional LVUNDEF in CurrentScope."""

    def test_undefined_local_raises_lvundef(self):
        """Accessing undefined local via CurrentScope raises LVUNDEFError."""
        scope = CurrentScope({})
        with pytest.raises(LVUNDEFError):
            scope.get("UNDEF")

    def test_defined_local_returns_value(self):
        """Accessing defined local via CurrentScope returns value."""
        scope = CurrentScope({"X": MArray(value="hello")})
        assert scope.get("X") == "hello"

    def test_undefined_after_kill_raises_lvundef(self):
        """After KILL, variable access raises LVUNDEFError."""
        scope_dict: dict = {"X": MArray(value="hello")}
        scope = CurrentScope(scope_dict)
        assert scope.get("X") == "hello"
        del scope_dict["X"]
        with pytest.raises(LVUNDEFError):
            scope.get("X")

    def test_undefined_subscripted_raises_lvundef(self):
        """Accessing undefined subscripted variable raises LVUNDEFError."""
        scope = CurrentScope({})
        with pytest.raises(LVUNDEFError):
            scope.get_subscripted("X", ("1",))

    def test_no_strict_mode_parameter(self):
        """CurrentScope does not accept strict_mode parameter."""
        import inspect

        sig = inspect.signature(CurrentScope.__init__)
        params = list(sig.parameters.keys())
        assert "strict_mode" not in params


@pytest.mark.codegen
class TestLVUNDEFWithErrorTrapping:
    """T118: Integration tests for LVUNDEF with $ETRAP error trapping."""

    def test_lvundef_mapped_to_m6_in_ecode(self):
        """LVUNDEFError maps to M6 in $ECODE format."""
        rt = MUMPSRuntime()
        ecode = rt._exception_to_ecode(LVUNDEFError("X"))
        assert ecode == ",M6,"

    def test_etrap_catches_lvundef_from_runtime(self):
        """$ETRAP can catch LVUNDEFError when raised by runtime."""
        rt = MUMPSRuntime()
        rt.set_etrap('S $EC=""')
        scope: dict = {}
        # Simulate LVUNDEFError caught by _handle_etrap
        result = rt._handle_etrap(LVUNDEFError("X"), scope)
        assert result is True
        assert rt.ecode() == ""
        # $ZSTATUS should mention LVUNDEF
        assert "LVUNDEF" in rt.zstatus()


@pytest.mark.codegen
class TestLVUNDEFEndToEnd:
    """T118: End-to-end transpilation tests for LVUNDEF behavior."""

    def test_defined_variable_writes_value(self):
        """Defined variable writes its value correctly."""
        source = 'TEST\n S X="Hello"\n W X,!\n Q'
        rt, output = _run(source)
        assert output == "Hello\n"

    def test_set_then_delete_variable(self):
        """SET then KILL variable: subsequent access after KILL."""
        source = 'TEST\n S X="Hello"\n K X\n W $D(X),!\n Q'
        rt, output = _run(source)
        assert output.strip() == "0"
