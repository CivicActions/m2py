"""Tests for Indirection code generation (§7.3).

Reference: MUMPS 1995 ANSI Standard, Section 7.3
Spec 012: Phase 3 - User Story 1: Name Indirection
"""

import pytest


@pytest.mark.codegen
class TestIndirectionCodegen:
    """Codegen-level tests for indirection code generation (§7.3)."""

    def test_name_indirection_read(self, generate_python):
        """Name indirection read generates _rt.get_var call (T020).

        In MUMPS, @X where X contains a variable name accesses that variable.
        Example: S X="VAR",Y=@X means Y gets the value of VAR
        """
        code = generate_python('TEST S X="VAR",VAR=5,Y=@X Q\n')

        # Should generate runtime get_var call for @X
        assert "_rt.get_var" in code
        # Should include scope reference
        assert "_scope" in code

    def test_name_indirection_write(self, generate_python):
        """Name indirection write generates _rt.set_var call (T021).

        In MUMPS, S @X=1 where X contains a variable name sets that variable.
        Example: S X="VAR",@X=1 means VAR gets the value 1
        """
        code = generate_python('TEST S X="VAR",@X=1 Q\n')

        # Should generate runtime set_var call for @X=1
        assert "_rt.set_var" in code
        # Should include scope reference
        assert "_scope" in code

    def test_multi_level_indirection(self, generate_python):
        """Multi-level indirection generates resolve_indirection call (T022).

        In MUMPS, @@X means double indirection.
        Example: S A="B",B="C",C=100,X=@@A means X gets 100
        """
        code = generate_python('TEST S A="B",B="C",C=100,X=@@A Q\n')

        # Should generate runtime resolve_indirection call for @@A
        assert "_rt.resolve_indirection" in code
        # Should include levels=2 for double indirection
        assert ", 2," in code
        # Should include scope reference
        assert "_scope" in code

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: subscript indirection")
    def test_subscript_indirection(self, generate_python):
        """Subscript indirection generates dynamic access (§7.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: argument indirection")
    def test_argument_indirection(self, generate_python):
        """Argument indirection generates runtime evaluation (§7.3)."""
