"""Stub test template for spec-aligned unit tests.

This file serves as a copy-paste template for creating new spec-aligned
test files. Copy this file and modify according to the target spec section.

USAGE:
1. Copy this file to the appropriate directory (parser/, asg/, or codegen/)
2. Rename to match spec section: test_s{section}_{subsection}_{feature}.py
3. Update the docstring with the correct spec section reference
4. Update the class name and test functions
5. Replace @pytest.mark.parser with appropriate category marker
6. Add specific test cases as xfail stubs

See: specs/002-spec-unit-test-organization/contracts/test-naming.md
"""

import pytest


@pytest.mark.parser  # Replace with @pytest.mark.asg or @pytest.mark.codegen as appropriate
class TestFeatureName:
    """Tests for FEATURE parsing (§X.Y.Z).

    Tests verify the textX grammar correctly captures FEATURE syntax variations.
    Reference: MUMPS 1995 ANSI Standard, Section X.Y.Z
    """

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FEATURE basic form")
    def test_feature_basic_form(self):
        """FEATURE basic syntax produces correct AST (§X.Y.Z.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FEATURE with argument")
    def test_feature_with_argument(self):
        """FEATURE with argument parses correctly (§X.Y.Z.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: FEATURE edge case")
    def test_feature_edge_case(self):
        """FEATURE edge case is handled properly (§X.Y.Z.3).

        Edge case description here.
        """
        pytest.fail("Stub - implement test")


# Example of skip marker for out-of-scope features
@pytest.mark.parser
class TestOutOfScopeFeature:
    """Tests for OUT-OF-SCOPE feature (§A.B.C).

    This feature is out of scope per docs/limitations.md.
    """

    @pytest.mark.skip(
        reason="Out of scope: FEATURE not supported. See docs/limitations.md"
    )
    def test_unsupported_feature(self):
        """FEATURE is not supported."""
        pass


# Example of skip marker for implementation-defined features
@pytest.mark.parser
class TestImplementationDefined:
    """Tests for implementation-defined feature (§D.E.F).

    Behavior is implementation-defined per MUMPS spec.
    """

    @pytest.mark.skip(
        reason="Implementation-defined: VIEW command behavior varies by implementation"
    )
    def test_implementation_defined_feature(self):
        """VIEW behavior is implementation-defined."""
        pass
