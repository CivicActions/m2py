"""Tests for out-of-scope commands ASG analysis.

These commands are part of the ANSI spec but are explicitly out of scope
for the M2PY transpiler project.
"""

import pytest


@pytest.mark.asg
class TestOutOfScopeCommandsAnalysis:
    """ASG-level tests for commands that are out of scope."""

    @pytest.mark.skip(reason="Out of scope: Event processing commands per FR-055")
    def test_event_processing_commands(self):
        """ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER are out of scope."""
        pass

    @pytest.mark.skip(reason="Out of scope: THEN command per FR-055")
    def test_then_command(self):
        """THEN command (§8.2.32) is out of scope."""
        pass

    @pytest.mark.skip(reason="Out of scope: ASSIGN command per FR-055")
    def test_assign_command(self):
        """ASSIGN command is out of scope."""
        pass

    @pytest.mark.skip(reason="Out of scope: RLOAD command per FR-055")
    def test_rload_command(self):
        """RLOAD command is out of scope."""
        pass

    @pytest.mark.skip(reason="Out of scope: RSAVE command per FR-055")
    def test_rsave_command(self):
        """RSAVE command is out of scope."""
        pass
