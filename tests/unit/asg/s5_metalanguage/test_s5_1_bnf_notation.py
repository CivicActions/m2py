"""Tests for BNF Notation ASG analysis (§5.1).

Reference: MUMPS 1995 ANSI Standard, Section 5.1
"""

import pytest


@pytest.mark.asg
class TestBnfNotationAnalysis:
    """ASG-level tests for BNF notation (§5.1)."""

    @pytest.mark.skip(
        reason="Out of scope: §5 is informative metalanguage, no executable semantics"
    )
    def test_bnf_metalanguage(self):
        """BNF metalanguage is informative only (§5.1)."""
        pass
