"""Tests for Event Processing parsing (§6.3.4).

This section is out of scope per FR-055.

Reference: MUMPS 1995 ANSI Standard, Section 6.3.4
"""

import pytest


@pytest.mark.parser
@pytest.mark.skip(
    reason="Out of scope: §6.3.4 Event Processing (ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER). See docs/limitations.md"
)
class TestEventProcessingParsing:
    """Tests for Event Processing (§6.3.4).

    Event processing commands (ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER)
    are out of scope per FR-055.
    """

    def test_event_processing_out_of_scope(self):
        """§6.3.4 Event Processing is out of scope."""
        pass
