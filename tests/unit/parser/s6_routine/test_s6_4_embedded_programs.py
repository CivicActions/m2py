"""Tests for Embedded Programs parsing (§6.4).

This section is out of scope per FR-055.

Reference: MUMPS 1995 ANSI Standard, Section 6.4
"""

import pytest


@pytest.mark.parser
@pytest.mark.skip(
    reason="Out of scope: §6.4 Embedded Programs. See docs/limitations.md"
)
class TestEmbeddedProgramsParsing:
    """Tests for Embedded Programs (§6.4).

    Embedded programs are out of scope per FR-055.
    """

    def test_embedded_programs_out_of_scope(self):
        """§6.4 Embedded Programs is out of scope."""
        pass
