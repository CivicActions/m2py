"""Tests for event processing commands parsing.

Event processing commands (ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER)
are out of scope per FR-055.
Reference: MUMPS 1995 ANSI Standard
"""

import pytest


@pytest.mark.parser
class TestEventProcessingCommandsParsing:
    """Parser-level tests for event processing commands."""

    @pytest.mark.skip(reason="Out of scope per FR-055: ABLOCK not supported")
    def test_ablock_out_of_scope(self):
        """ABLOCK command is out of scope."""
        pass

    @pytest.mark.skip(reason="Out of scope per FR-055: AUNBLOCK not supported")
    def test_aunblock_out_of_scope(self):
        """AUNBLOCK command is out of scope."""
        pass

    @pytest.mark.skip(reason="Out of scope per FR-055: ASTART not supported")
    def test_astart_out_of_scope(self):
        """ASTART command is out of scope."""
        pass

    @pytest.mark.skip(reason="Out of scope per FR-055: ASTOP not supported")
    def test_astop_out_of_scope(self):
        """ASTOP command is out of scope."""
        pass

    @pytest.mark.skip(reason="Out of scope per FR-055: ESTART not supported")
    def test_estart_out_of_scope(self):
        """ESTART command is out of scope."""
        pass

    @pytest.mark.skip(reason="Out of scope per FR-055: ESTOP not supported")
    def test_estop_out_of_scope(self):
        """ESTOP command is out of scope."""
        pass

    @pytest.mark.skip(reason="Out of scope per FR-055: ETRIGGER not supported")
    def test_etrigger_out_of_scope(self):
        """ETRIGGER command is out of scope."""
        pass
