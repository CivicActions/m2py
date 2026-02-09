"""Tests for Generic Indirection code generation (§6.3.1).

Reference: MUMPS 1995 ANSI Standard, Section 6.3.1

Generic indirection (the @ operator) allows runtime evaluation of names
and expressions. This file tests code generation for indirection used in
routine-level constructs (SET targets, DO calls, XECUTE, etc.).

Note: Expression-level indirection codegen is in
tests/unit/codegen/s7_expressions/test_s7_3_indirection.py.
"""

import pytest


@pytest.mark.codegen
class TestGenericIndirectionCodegen:
    """Codegen-level tests for Generic Indirection (§6.3.1).

    The @ operator provides indirection — runtime evaluation of names.
    Per §6.3.1, indirection can appear in any context where a name is
    expected, including SET targets, DO/GOTO labels, and command arguments.
    """

    def test_name_indirection_in_set_target(self, generate_python):
        """SET @VAR=value generates indirected set call (§6.3.1).

        Name indirection in SET target uses runtime resolution.
        """
        code = generate_python('TEST S X="Y",@X=1 Q\n')
        assert "_rt.set_indirected" in code

    def test_indirection_in_do_target(self, generate_python):
        """DO @VAR generates indirected call (§6.3.1).

        When the DO target is indirected, the label name is resolved
        at runtime.
        """
        code = generate_python('TEST S X="SUB" D @X Q\nSUB Q\n')
        # Should generate runtime indirection dispatch
        assert "indirect" in code.lower() or "_rt." in code

    def test_indirection_in_xecute(self, generate_python):
        """XECUTE @VAR generates runtime eval with indirection (§6.3.1).

        XECUTE with indirection resolves the code string at runtime.
        """
        code = generate_python('TEST S X="W 1" X @X Q\n')
        # Should generate xecute handling with indirection
        assert "_rt." in code

    def test_subscript_indirection_in_set(self, generate_python):
        """SET @X@(1)=value generates subscript indirection (§6.3.1).

        Subscript indirection appends subscripts to an indirected name.
        """
        code = generate_python('TEST S X="ARR",@X@(1)=99 Q\n')
        assert "_rt.set_indirected" in code

    def test_indirection_generates_scope_reference(self, generate_python):
        """Indirection codegen includes scope reference for runtime resolution (§6.3.1)."""
        code = generate_python('TEST S X="Y",@X=1 Q\n')
        assert "_scope" in code
