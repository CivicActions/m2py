"""Tests for §5.1 BNF Notation (§5.1).

This section is informative and describes the metalanguage used in the spec.
It has no executable semantics to test.

Reference: MUMPS 1995 ANSI Standard, Section 5.1
"""

import pytest


@pytest.mark.parser
@pytest.mark.skip(
    reason="Out of scope: §5 Metalanguage is informative, no executable semantics. See docs/limitations.md"
)
class TestBnfNotation:
    """Tests for BNF metalanguage notation (§5.1).

    This section is informative only - it describes the BNF notation used
    throughout the specification but has no testable semantics.
    """

    def test_bnf_notation_informative(self):
        """§5.1 BNF notation is informative only."""
        pass
