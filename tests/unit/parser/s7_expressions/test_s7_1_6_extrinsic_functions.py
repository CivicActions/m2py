"""Tests for Extrinsic Functions parsing (§7.1.6).

Tests verify the textX grammar correctly captures extrinsic function syntax.

Reference: MUMPS 1995 ANSI Standard, Section 7.1.6
"""

import pytest


@pytest.mark.parser
class TestExtrinsicFunctionsParsing:
    """Parser-level tests for Extrinsic Functions (§7.1.6).

    Extrinsic functions are user-defined functions called with $$ prefix.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: extrinsic function basic form")
    def test_extrinsic_function_basic(self, parse_expression):
        """$$FUNC parses correctly (§7.1.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: extrinsic function with arguments")
    def test_extrinsic_function_with_args(self, parse_expression):
        """$$FUNC(arg1,arg2) parses correctly (§7.1.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: extrinsic function with routine")
    def test_extrinsic_function_external(self, parse_expression):
        """$$FUNC^ROUTINE(args) parses correctly (§7.1.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: extrinsic function with label and offset"
    )
    def test_extrinsic_function_label_offset(self, parse_expression):
        """$$LABEL+OFFSET^ROUTINE(args) parses correctly (§7.1.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: extrinsic function pass by reference"
    )
    def test_extrinsic_function_by_ref(self, parse_expression):
        """$$FUNC(.var) pass by reference parses correctly (§7.1.6)."""
        pytest.fail("Stub - implement test")
