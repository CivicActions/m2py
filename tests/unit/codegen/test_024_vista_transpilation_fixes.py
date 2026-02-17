"""Tests for 024-vista-transpilation-fixes: Phase 2 (US1) Core Codegen Fixes.

Validates Contracts 1-5 plus edge cases for:
- ParenExpr / UnaryPrefixedExpr / Expr defensive codegen handlers
- f-string nested quote fixes (Python 3.10 compatibility)
- Empty TRAMPOLINE block fix (pass insertion)
- >= and <= comparison operators
- SET $X / SET $Y codegen and runtime
- DeviceControl stub codegen

Reference: specs/024-vista-transpilation-fixes/contracts/test-contracts.md
"""

from pathlib import Path

import pytest

VISTA_BASE = Path(__file__).parent.parent.parent.parent / "VistA-VEHU-M"


def _find_vista(name: str) -> str:
    """Find and read a VistA-VEHU-M routine by name."""
    files = list(VISTA_BASE.rglob(f"{name}.m"))
    if not files:
        pytest.skip(f"VistA routine {name}.m not found")
    return files[0].read_text(errors="replace")


# ===========================================================================
# Contract 1: ParenExpr Handling (FR-001)
# ===========================================================================


@pytest.mark.codegen
class TestParenExpr:
    """Contract 1: Parenthesized expressions must be handled in codegen."""

    def test_paren_expr_grouping(self, execute_mumps):
        """(X+Y)*2 must group correctly — Contract 1 happy path."""
        code = "PAREN\n S X=3,Y=4\n S Z=(X+Y)*2\n W Z,!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "14\n"

    def test_paren_expr_double_wrapped(self, execute_mumps):
        """((X+Y)) double-parenthesized expression."""
        code = "PAREN\n S X=3,Y=4\n S A=((X+Y))\n W A,!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "7\n"

    def test_paren_expr_nested_operations(self, execute_mumps):
        """((A+B)*(C-D)) nested parentheses with multiple ops."""
        code = "TEST\n S A=2,B=3,C=10,D=4\n W ((A+B)*(C-D)),!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "30\n"

    def test_paren_expr_in_condition(self, execute_mumps):
        """Parenthesized expression in IF condition."""
        code = 'TEST\n S X=5 I (X>3) W "yes",!\n Q\n'
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "yes\n"

    def test_vista_prcacv10_transpiles(self, generate_python):
        """PRCACV10 must transpile without error — Contract 1 VistA test."""
        code = _find_vista("PRCACV10")
        # Must not raise NotImplementedError or any exception
        result = generate_python(code, routine_name="PRCACV10")
        assert isinstance(result, str)

    def test_vista_dgmtxe2_transpiles(self, generate_python):
        """DGMTXE2 must transpile without error — ParenExpr VistA test."""
        code = _find_vista("DGMTXE2")
        result = generate_python(code, routine_name="DGMTXE2")
        assert isinstance(result, str)


# ===========================================================================
# Contract 1 extension: UnaryPrefixedExpr / Expr wrapper nodes
# ===========================================================================


@pytest.mark.codegen
class TestUnaryPrefixedExpr:
    """Contract 20: UnaryPrefixedExpr and Expr wrapper nodes in codegen."""

    def test_unary_not_operator(self, execute_mumps):
        """'X (NOT) operator via UnaryPrefixedExpr path."""
        code = "TEST\n S X=0 W 'X,!\n S X=1 W 'X,!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "1\n0\n"

    def test_unary_negation(self, execute_mumps):
        """Unary minus via UnaryPrefixedExpr path."""
        code = "TEST\n S X=5 W -X,!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "-5\n"

    def test_unary_plus(self, execute_mumps):
        """Unary plus (numeric coercion) via UnaryPrefixedExpr path."""
        code = 'TEST\n S X="3abc" W +X,!\n Q\n'
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "3\n"

    def test_double_not(self, execute_mumps):
        """Double negation ''X."""
        code = "TEST\n S X=5 W ''X,!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "1\n"

    def test_vista_gmrciac2_transpiles(self, generate_python):
        """GMRCIAC2 (Q:'CRNR!('$T(@+ERR))) must transpile — Contract 20."""
        code = _find_vista("GMRCIAC2")
        result = generate_python(code, routine_name="GMRCIAC2")
        assert isinstance(result, str)


# ===========================================================================
# Contract 2: f-string Nested Quotes (FR-002)
# ===========================================================================


@pytest.mark.codegen
class TestFStringNestedQuotes:
    """Contract 2: Generated Python must not have f-string nested quote issues."""

    def test_fstring_contract_2(self, execute_mumps):
        """Contract 2 happy path: indirected $D with $P subscript."""
        code = (
            "FSTR1\n"
            ' S Y="Y"\n'
            ' S Y(1)="found"\n'
            ' S X="1^2" I $D(@Y@($P(X,"^",1))) W "yes",!\n'
            " Q\n"
        )
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "yes\n"

    def test_fstring_compiles_on_py310(self, generate_python):
        """Generated Python must compile() without SyntaxError."""
        code = (
            "FSTR1\n"
            ' S Y="Y"\n'
            ' S Y(1)="found"\n'
            ' S X="1^2" I $D(@Y@($P(X,"^",1))) W "yes",!\n'
            " Q\n"
        )
        py_code = generate_python(code)
        # compile() verifies Python syntax at the current interpreter level
        compile(py_code, "<test>", "exec")

    def test_vista_scapmcu3_transpiles(self, generate_python):
        """SCAPMCU3 must transpile — f-string VistA test."""
        code = _find_vista("SCAPMCU3")
        result = generate_python(code, routine_name="SCAPMCU3")
        assert isinstance(result, str)
        compile(result, "<SCAPMCU3>", "exec")

    def test_vista_dsicddbr_transpiles(self, generate_python):
        """DSICDDBR must transpile — f-string VistA test."""
        code = _find_vista("DSICDDBR")
        result = generate_python(code, routine_name="DSICDDBR")
        assert isinstance(result, str)
        compile(result, "<DSICDDBR>", "exec")


# ===========================================================================
# Contract 3: Empty Indented Block (FR-003, TRAMPOLINE)
# ===========================================================================


@pytest.mark.codegen
class TestEmptyTrampolineBlock:
    """Contract 3: Empty IF/ELSE blocks must get 'pass' to avoid SyntaxError."""

    def test_empty_block_if_goto(self, execute_mumps):
        """Contract 3 happy path: IF with GOTO in TRAMPOLINE mode."""
        code = 'EMPTYB\n S X=1 I X G DONE\n W "not reached",!\nDONE W "done",!\n Q\n'
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "done\n"

    def test_empty_block_compiles(self, generate_python):
        """Generated Python for GOTO-bearing code must compile()."""
        code = 'EMPTYB\n S X=1 I X G DONE\n W "not reached",!\nDONE W "done",!\n Q\n'
        py_code = generate_python(code)
        compile(py_code, "<test>", "exec")

    def test_if_with_argumentless_do(self, generate_python):
        """IF with argumentless DO (multi-condition) must compile."""
        code = 'TEST\n S X=1,Y=1\n I X,Y D\n . W "both true",!\n Q\n'
        py_code = generate_python(code)
        compile(py_code, "<test>", "exec")

    def test_vista_fhwor6_transpiles(self, generate_python):
        """FHWOR6 must transpile — empty block VistA test."""
        code = _find_vista("FHWOR6")
        result = generate_python(code, routine_name="FHWOR6")
        assert isinstance(result, str)
        compile(result, "<FHWOR6>", "exec")

    def test_vista_hmpdmc_transpiles(self, generate_python):
        """HMPDMC must transpile — empty block VistA test."""
        code = _find_vista("HMPDMC")
        result = generate_python(code, routine_name="HMPDMC")
        assert isinstance(result, str)
        compile(result, "<HMPDMC>", "exec")

    def test_vista_scmccv_transpiles(self, generate_python):
        """SCMCCV must transpile — empty block VistA test."""
        code = _find_vista("SCMCCV")
        result = generate_python(code, routine_name="SCMCCV")
        assert isinstance(result, str)
        compile(result, "<SCMCCV>", "exec")

    def test_vista_fscevenp_transpiles(self, generate_python):
        """FSCEVENP must transpile — empty block VistA test."""
        code = _find_vista("FSCEVENP")
        result = generate_python(code, routine_name="FSCEVENP")
        assert isinstance(result, str)
        compile(result, "<FSCEVENP>", "exec")


# ===========================================================================
# Contract 4: >= and <= Operators (FR-004)
# ===========================================================================


@pytest.mark.codegen
class TestComparisonOperators:
    """Contract 4: >= and <= operators must work correctly."""

    def test_gte_true(self, execute_mumps):
        """5>=3 is true."""
        result = execute_mumps('CMPOP\n I 5>=3 W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_gte_false(self, execute_mumps):
        """3>=5 is false."""
        result = execute_mumps('CMPOP\n I 3>=5 W "yes",!\n Q\n')
        assert result.output == ""

    def test_gte_equal(self, execute_mumps):
        """5>=5 is true."""
        result = execute_mumps('CMPOP\n I 5>=5 W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_lte_true(self, execute_mumps):
        """3<=5 is true."""
        result = execute_mumps('CMPOP\n I 3<=5 W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_lte_false(self, execute_mumps):
        """5<=3 is false."""
        result = execute_mumps('CMPOP\n I 5<=3 W "yes",!\n Q\n')
        assert result.output == ""

    def test_lte_equal(self, execute_mumps):
        """5<=5 is true."""
        result = execute_mumps('CMPOP\n I 5<=5 W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_contract_4_full(self, execute_mumps):
        """Full Contract 4 scenario."""
        code = (
            "CMPOP\n"
            ' I 5>=3 W "5>=3:yes",!\n'
            ' I 3>=5 W "3>=5:yes",!\n'
            ' I 5>=5 W "5>=5:yes",!\n'
            ' I 3<=5 W "3<=5:yes",!\n'
            ' I 5<=3 W "5<=3:yes",!\n'
            ' I 5<=5 W "5<=5:yes",!\n'
            " Q\n"
        )
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "5>=3:yes\n5>=5:yes\n3<=5:yes\n5<=5:yes\n"

    def test_gte_with_string_coercion(self, execute_mumps):
        """>=/<= with string operands use MUMPS numeric coercion."""
        result = execute_mumps('TEST\n I "5">="3" W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_lte_negative_numbers(self, execute_mumps):
        """-3<=-1 is true."""
        result = execute_mumps('TEST\n I -3<=-1 W "yes",!\n Q\n')
        assert result.output == "yes\n"

    def test_vista_icdselds_transpiles(self, generate_python):
        """ICDSELDS must transpile — <= VistA test."""
        code = _find_vista("ICDSELDS")
        result = generate_python(code, routine_name="ICDSELDS")
        assert isinstance(result, str)

    def test_vista_dvbacer1_transpiles(self, generate_python):
        """DVBACER1 must transpile — <= VistA test."""
        code = _find_vista("DVBACER1")
        result = generate_python(code, routine_name="DVBACER1")
        assert isinstance(result, str)


# ===========================================================================
# Contract 5: SET $X and SET $Y (FR-005)
# ===========================================================================


@pytest.mark.codegen
class TestSetSpecialXY:
    """Contract 5: SET $X/$Y must update cursor position in runtime."""

    def test_set_x_codegen(self, generate_python):
        """SET $X=0 generates _rt.set_x() call."""
        code = "TEST\n S $X=0\n Q\n"
        py = generate_python(code)
        assert "_rt.set_x(" in py

    def test_set_y_codegen(self, generate_python):
        """SET $Y=0 generates _rt.set_y() call."""
        code = "TEST\n S $Y=0\n Q\n"
        py = generate_python(code)
        assert "_rt.set_y(" in py

    def test_set_x_executes(self, execute_mumps):
        """Contract 5: SET $X=0, W $X outputs 0."""
        code = "SETXY\n S $X=0 W $X,!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "0\n"

    def test_set_y_executes(self, execute_mumps):
        """Contract 5: SET $Y=0, W $Y outputs 0."""
        code = "SETXY\n S $Y=0 W $Y,!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "0\n"

    def test_set_x_numeric_coercion(self, execute_mumps):
        """SET $X with string value coerces to numeric."""
        code = 'TEST\n S $X="5abc" W $X,!\n Q\n'
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "5\n"

    def test_set_y_zero_resets(self, execute_mumps):
        """SET $Y=0 resets line counter (common VistA pattern)."""
        code = "TEST\n W !,! S $Y=0 W $Y,!\n Q\n"
        result = execute_mumps(code)
        assert result.success is True
        # After write of two newlines, $Y is 2. SET $Y=0 resets. W $Y writes 0.
        assert "0\n" in result.output

    def test_vista_pxrmrxty_transpiles(self, generate_python):
        """PXRMRXTY must transpile — SET $Y VistA test."""
        code = _find_vista("PXRMRXTY")
        result = generate_python(code, routine_name="PXRMRXTY")
        assert isinstance(result, str)


# ===========================================================================
# DeviceControl stub handling
# ===========================================================================


@pytest.mark.codegen
class TestDeviceControl:
    """DeviceControl mnemonics generate stub runtime calls."""

    def test_device_control_transpiles(self, generate_python):
        """W /CUP(10,5) generates device_control() call."""
        code = "TEST\n W /CUP(10,5)\n Q\n"
        result = generate_python(code)
        assert "_rt.device_control(" in result

    def test_device_control_no_params(self, generate_python):
        """W /EOF generates device_control() call without params."""
        code = "TEST\n W /EOF\n Q\n"
        result = generate_python(code)
        assert "_rt.device_control(" in result

    def test_device_control_executes(self, execute_mumps):
        """DeviceControl stub doesn't crash at runtime."""
        code = 'TEST\n W /EOF\n W "ok",!\n Q\n'
        result = execute_mumps(code)
        assert result.success is True
        assert "ok" in result.output

    def test_vista_xushsh_transpiles(self, generate_python):
        """XUSHSH must transpile — DeviceControl VistA test."""
        code = _find_vista("XUSHSH")
        result = generate_python(code, routine_name="XUSHSH")
        assert isinstance(result, str)
