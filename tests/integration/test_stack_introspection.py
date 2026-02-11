"""Integration tests for $STACK introspection (Phase 7: US4).

T044: Integration test transpiling nested DO routine with $STACK queries.
"""

import pytest

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime


def _run(mumps_code: str) -> tuple[MUMPSRuntime, str]:
    """Transpile and execute MUMPS code, return runtime and output."""
    python_code = generate_python(mumps_code)
    runtime = MUMPSRuntime()
    result = runtime.execute(python_code, capture_output=True)
    return runtime, result.output


@pytest.mark.codegen
class TestStackDepthIntegration:
    """T044: Integration tests for $STACK depth tracking."""

    def test_stack_depth_increases_with_nested_do(self):
        """$STACK increases with each DO call."""
        source = (
            "TEST\n"
            " W $ST,!\n"
            " D SUB1\n"
            " Q\n"
            "SUB1\n"
            " W $ST,!\n"
            " D SUB2\n"
            " Q\n"
            "SUB2\n"
            " W $ST,!\n"
            " Q"
        )
        rt, output = _run(source)
        lines = output.strip().split("\n")
        assert len(lines) == 3
        # Each nested DO increases stack depth
        depths = [int(x) for x in lines]
        assert depths[0] < depths[1] < depths[2]

    def test_stack_depth_returns_to_original(self):
        """$STACK depth returns to original after DO completes."""
        source = "TEST\n W $ST,!\n D SUB\n W $ST,!\n Q\nSUB\n Q"
        rt, output = _run(source)
        lines = output.strip().split("\n")
        assert lines[0] == lines[1]  # Same depth before and after DO


@pytest.mark.codegen
class TestStackFunctionIntegration:
    """T044: Integration tests for $STACK function with info codes."""

    def test_stack_minus_1_returns_depth(self):
        """$STACK(-1) returns current stack depth."""
        source = "TEST\n D SUB\n Q\nSUB\n W $ST(-1),!\n Q"
        rt, output = _run(source)
        depth = int(output.strip())
        assert depth >= 1  # At least 1 frame from DO SUB

    def test_stack_level_returns_frame_type(self):
        """$STACK(n) returns frame type for given level."""
        source = "TEST\n D SUB\n Q\nSUB\n W $ST(1),!\n Q"
        rt, output = _run(source)
        assert output.strip() == "DO"


@pytest.mark.codegen
class TestStackSnapshotIntegration:
    """T044: Integration tests for $STACK snapshot during errors."""

    def test_stack_snapshot_on_error(self):
        """$STACK snapshot is taken when $ECODE becomes non-empty."""
        source = 'TEST\n S $ET="S $EC="""""\n D SUB\n Q\nSUB\n S X=1/0\n Q'
        rt, _output = _run(source)
        # After $ETRAP clears $ECODE, snapshot should be cleared
        assert rt._stack_snapshot is None
        assert rt.ecode() == ""
