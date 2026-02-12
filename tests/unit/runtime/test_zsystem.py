"""Unit tests for ZSYSTEM command and $ZSYSTEM ISV.

Spec 021 Phase 11 (T071, T074): ZSYSTEM executes shell commands,
$ZSYSTEM returns exit code.
"""

import pytest
from m2py.runtime import MUMPSRuntime


@pytest.mark.codegen
class TestZsystem:
    """Tests for zsystem() runtime method."""

    def test_successful_command(self):
        """ZSYSTEM with successful command sets exit code to 0."""
        rt = MUMPSRuntime()
        rt.zsystem("true")
        assert rt.zsystem_exit() == 0

    def test_failed_command_exit_code(self):
        """ZSYSTEM with failed command stores nonzero exit code."""
        rt = MUMPSRuntime()
        rt.zsystem("exit 42")
        assert rt.zsystem_exit() == 42

    def test_empty_string_noop(self):
        """ZSYSTEM with empty string is a no-op, exit code 0."""
        rt = MUMPSRuntime()
        # Set a nonzero baseline
        rt.zsystem("exit 5")
        assert rt.zsystem_exit() == 5
        # Empty string resets to 0
        rt.zsystem("")
        assert rt.zsystem_exit() == 0

    def test_no_args_noop(self):
        """ZSYSTEM with no args is a no-op, exit code 0."""
        rt = MUMPSRuntime()
        rt.zsystem("exit 5")
        assert rt.zsystem_exit() == 5
        rt.zsystem()
        assert rt.zsystem_exit() == 0

    def test_default_exit_code_is_zero(self):
        """$ZSYSTEM is 0 before any ZSYSTEM command."""
        rt = MUMPSRuntime()
        assert rt.zsystem_exit() == 0

    def test_exit_code_persists(self):
        """$ZSYSTEM retains value from last ZSYSTEM command."""
        rt = MUMPSRuntime()
        rt.zsystem("exit 1")
        assert rt.zsystem_exit() == 1
        # Call again with success
        rt.zsystem("true")
        assert rt.zsystem_exit() == 0

    def test_exit_code_one(self):
        """ZSYSTEM with exit code 1."""
        rt = MUMPSRuntime()
        rt.zsystem("exit 1")
        assert rt.zsystem_exit() == 1

    def test_command_with_output(self, tmp_path):
        """ZSYSTEM command executes and completes successfully."""
        # Verify command runs by writing to a file (avoids capsys/fd issues)
        outfile = tmp_path / "zsy_output.txt"
        rt = MUMPSRuntime()
        rt.zsystem(f"echo hello_test > {outfile}")
        assert rt.zsystem_exit() == 0
        assert outfile.read_text().strip() == "hello_test"
