"""Tests for MATH Library Functions ASG analysis (Annex I-2, §7.1.6.5).

Tests verify the ASG correctly captures MATH library function semantics.
MATH library functions are called as $$%FUNC^MATH or $%FUNC^MATH.

Reference: MUMPS 1995 ANSI Standard, Annex I Section 2
Total: 57 MATH library functions
"""

import pytest

from m2py.analysis.semantic_analyzer import analyze_expression
from m2py.asg.expressions import MActualParameter
from m2py.parser.textx_classes import ExtrinsicFunction
from tests.helpers.parsing import parse_expression


def verify_math_function(code: str, expected_label: str, expected_arg_count: int):
    """Helper to verify a MATH library function ASG structure.

    Args:
        code: MUMPS expression like '$$%SIN^MATH(X,10)'
        expected_label: Expected function label like '%SIN'
        expected_arg_count: Expected number of arguments
    """
    expr = parse_expression(code)
    asg = analyze_expression(expr)

    assert isinstance(asg, ExtrinsicFunction), (
        f"Expected ExtrinsicFunction, got {type(asg).__name__}"
    )
    assert asg.label == expected_label, (
        f"Expected label {expected_label}, got {asg.label}"
    )
    assert asg.routine == "MATH", f"Expected routine MATH, got {asg.routine}"
    assert len(asg.arguments) == expected_arg_count, (
        f"Expected {expected_arg_count} args, got {len(asg.arguments)}"
    )

    # Verify all arguments are MActualParameter
    for i, arg in enumerate(asg.arguments):
        assert isinstance(arg, MActualParameter), (
            f"Arg {i} should be MActualParameter, got {type(arg).__name__}"
        )

    return asg


@pytest.mark.asg
class TestMathLibraryTrigonometricASG:
    """ASG-level tests for MATH library trigonometric functions (Annex I-2).

    Trigonometric functions: SIN, COS, TAN, COT, SEC, CSC and their hyperbolics.
    """

    def test_math_sin_asg(self):
        """$%SIN^MATH(X,PREC) ASG captures function call semantics (Annex I-2.47)."""
        verify_math_function("$$%SIN^MATH(X,10)", "%SIN", 2)

    def test_math_cos_asg(self):
        """$%COS^MATH(X,PREC) ASG captures function call semantics (Annex I-2.21)."""
        verify_math_function("$$%COS^MATH(X,10)", "%COS", 2)

    def test_math_tan_asg(self):
        """$%TAN^MATH(X,PREC) ASG captures function call semantics (Annex I-2.50)."""
        verify_math_function("$$%TAN^MATH(X,10)", "%TAN", 2)

    def test_math_cot_asg(self):
        """$%COT^MATH(X,PREC) ASG captures function call semantics (Annex I-2.23)."""
        verify_math_function("$$%COT^MATH(X,10)", "%COT", 2)

    def test_math_sec_asg(self):
        """$%SEC^MATH(X,PREC) ASG captures function call semantics (Annex I-2.44)."""
        verify_math_function("$$%SEC^MATH(X,10)", "%SEC", 2)

    def test_math_csc_asg(self):
        """$%CSC^MATH(X,PREC) ASG captures function call semantics (Annex I-2.25)."""
        verify_math_function("$$%CSC^MATH(X,10)", "%CSC", 2)

    def test_math_sinh_asg(self):
        """$%SINH^MATH(X,PREC) ASG captures function call semantics (Annex I-2.48)."""
        verify_math_function("$$%SINH^MATH(X,10)", "%SINH", 2)

    def test_math_cosh_asg(self):
        """$%COSH^MATH(X,PREC) ASG captures function call semantics (Annex I-2.22)."""
        verify_math_function("$$%COSH^MATH(X,10)", "%COSH", 2)

    def test_math_tanh_asg(self):
        """$%TANH^MATH(X,PREC) ASG captures function call semantics (Annex I-2.51)."""
        verify_math_function("$$%TANH^MATH(X,10)", "%TANH", 2)

    def test_math_coth_asg(self):
        """$%COTH^MATH(X,PREC) ASG captures function call semantics (Annex I-2.24)."""
        verify_math_function("$$%COTH^MATH(X,10)", "%COTH", 2)

    def test_math_sech_asg(self):
        """$%SECH^MATH(X,PREC) ASG captures function call semantics (Annex I-2.45)."""
        verify_math_function("$$%SECH^MATH(X,10)", "%SECH", 2)

    def test_math_csch_asg(self):
        """$%CSCH^MATH(X,PREC) ASG captures function call semantics (Annex I-2.26)."""
        verify_math_function("$$%CSCH^MATH(X,10)", "%CSCH", 2)


@pytest.mark.asg
class TestMathLibraryInverseTrigASG:
    """ASG-level tests for MATH library inverse trigonometric functions (Annex I-2).

    Inverse functions: ARCSIN, ARCCOS, ARCTAN, ARCCOT, ARCSEC, ARCCSC and hyperbolics.
    """

    def test_math_arcsin_asg(self):
        """$%ARCSIN^MATH(X,PREC) ASG captures function call semantics (Annex I-2.8)."""
        verify_math_function("$$%ARCSIN^MATH(X,10)", "%ARCSIN", 2)

    def test_math_arccos_asg(self):
        """$%ARCCOS^MATH(X,PREC) ASG captures function call semantics (Annex I-2.2)."""
        verify_math_function("$$%ARCCOS^MATH(X,10)", "%ARCCOS", 2)

    def test_math_arctan_asg(self):
        """$%ARCTAN^MATH(X,Y,PREC) ASG captures function call semantics (Annex I-2.10)."""
        verify_math_function("$$%ARCTAN^MATH(Y,X,8)", "%ARCTAN", 3)

    def test_math_arccot_asg(self):
        """$%ARCCOT^MATH(X,PREC) ASG captures function call semantics (Annex I-2.4)."""
        verify_math_function("$$%ARCCOT^MATH(X,10)", "%ARCCOT", 2)

    def test_math_arcsec_asg(self):
        """$%ARCSEC^MATH(X,PREC) ASG captures function call semantics (Annex I-2.7)."""
        verify_math_function("$$%ARCSEC^MATH(X,10)", "%ARCSEC", 2)

    def test_math_arccsc_asg(self):
        """$%ARCCSC^MATH(X,PREC) ASG captures function call semantics (Annex I-2.6)."""
        verify_math_function("$$%ARCCSC^MATH(X,10)", "%ARCCSC", 2)

    def test_math_arcsinh_asg(self):
        """$%ARCSINH^MATH(X,PREC) ASG captures function call semantics (Annex I-2.9)."""
        verify_math_function("$$%ARCSINH^MATH(X,10)", "%ARCSINH", 2)

    def test_math_arccosh_asg(self):
        """$%ARCCOSH^MATH(X,PREC) ASG captures function call semantics (Annex I-2.3)."""
        verify_math_function("$$%ARCCOSH^MATH(X,10)", "%ARCCOSH", 2)

    def test_math_arctanh_asg(self):
        """$%ARCTANH^MATH(X,PREC) ASG captures function call semantics (Annex I-2.11)."""
        verify_math_function("$$%ARCTANH^MATH(X,10)", "%ARCTANH", 2)

    def test_math_arccoth_asg(self):
        """$%ARCCOTH^MATH(X,PREC) ASG captures function call semantics (Annex I-2.5)."""
        verify_math_function("$$%ARCCOTH^MATH(X,10)", "%ARCCOTH", 2)


@pytest.mark.asg
class TestMathLibraryExponentialASG:
    """ASG-level tests for MATH library exponential/logarithmic functions (Annex I-2).

    Functions: EXP, LOG, LOG10, E, PI, SQRT, SIGN, ABS.
    """

    def test_math_exp_asg(self):
        """$%EXP^MATH(X,PREC) ASG captures function call semantics (Annex I-2.30)."""
        verify_math_function("$$%EXP^MATH(X,10)", "%EXP", 2)

    def test_math_log_asg(self):
        """$%LOG^MATH(X,PREC) ASG captures function call semantics (Annex I-2.31)."""
        verify_math_function("$$%LOG^MATH(X,10)", "%LOG", 2)

    def test_math_log10_asg(self):
        """$%LOG10^MATH(X,PREC) ASG captures function call semantics (Annex I-2.32)."""
        verify_math_function("$$%LOG10^MATH(X,10)", "%LOG10", 2)

    def test_math_e_asg(self):
        """$%E^MATH(PREC) ASG captures function call semantics (Annex I-2.29)."""
        verify_math_function("$$%E^MATH(10)", "%E", 1)

    def test_math_pi_asg(self):
        """$%PI^MATH(PREC) ASG captures function call semantics (Annex I-2.42)."""
        verify_math_function("$$%PI^MATH(10)", "%PI", 1)

    def test_math_sqrt_asg(self):
        """$%SQRT^MATH(X,PREC) ASG captures function call semantics (Annex I-2.49)."""
        verify_math_function("$$%SQRT^MATH(X,10)", "%SQRT", 2)

    def test_math_sign_asg(self):
        """$%SIGN^MATH(X) ASG captures function call semantics (Annex I-2.46)."""
        verify_math_function("$$%SIGN^MATH(X)", "%SIGN", 1)

    def test_math_abs_asg(self):
        """$%ABS^MATH(X) ASG captures function call semantics (Annex I-2.1)."""
        verify_math_function("$$%ABS^MATH(X)", "%ABS", 1)


@pytest.mark.asg
class TestMathLibraryAngleConversionASG:
    """ASG-level tests for MATH library angle conversion functions (Annex I-2).

    Functions: DEGRAD, RADDEG, DECDMS, DMSDEC.
    """

    def test_math_degrad_asg(self):
        """$%DEGRAD^MATH(X,PREC) ASG captures function call semantics (Annex I-2.28)."""
        verify_math_function("$$%DEGRAD^MATH(X,10)", "%DEGRAD", 2)

    def test_math_raddeg_asg(self):
        """$%RADDEG^MATH(X,PREC) ASG captures function call semantics (Annex I-2.43)."""
        verify_math_function("$$%RADDEG^MATH(X,10)", "%RADDEG", 2)

    def test_math_decdms_asg(self):
        """$%DECDMS^MATH(X,PREC) ASG captures function call semantics (Annex I-2.27)."""
        verify_math_function("$$%DECDMS^MATH(X,10)", "%DECDMS", 2)

    def test_math_dmsdec_asg(self):
        """$%DMSDEC^MATH(X) ASG captures function call semantics (Annex I-2.28a)."""
        verify_math_function("$$%DMSDEC^MATH(X)", "%DMSDEC", 1)


@pytest.mark.asg
class TestMathLibraryComplexNumberASG:
    """ASG-level tests for MATH library complex number functions (Annex I-2).

    Functions: COMPLEX, CONJUG, CABS, CADD, CSUB, CMUL, CDIV, CEXP, CLOG, CPOWER, CSIN, CCOS.
    """

    def test_math_complex_asg(self):
        """$%COMPLEX^MATH(REAL,IMAG) ASG captures function call semantics (Annex I-2.19)."""
        verify_math_function("$$%COMPLEX^MATH(R,I)", "%COMPLEX", 2)

    def test_math_conjug_asg(self):
        """$%CONJUG^MATH(Z) ASG captures function call semantics (Annex I-2.20)."""
        verify_math_function("$$%CONJUG^MATH(Z)", "%CONJUG", 1)

    def test_math_cabs_asg(self):
        """$%CABS^MATH(Z,PREC) ASG captures function call semantics (Annex I-2.12)."""
        verify_math_function("$$%CABS^MATH(Z,10)", "%CABS", 2)

    def test_math_cadd_asg(self):
        """$%CADD^MATH(Z1,Z2) ASG captures function call semantics (Annex I-2.13)."""
        verify_math_function("$$%CADD^MATH(Z1,Z2)", "%CADD", 2)

    def test_math_csub_asg(self):
        """$%CSUB^MATH(Z1,Z2) ASG captures function call semantics (Annex I-2.17)."""
        verify_math_function("$$%CSUB^MATH(Z1,Z2)", "%CSUB", 2)

    def test_math_cmul_asg(self):
        """$%CMUL^MATH(Z1,Z2,PREC) ASG captures function call semantics (Annex I-2.18)."""
        verify_math_function("$$%CMUL^MATH(Z1,Z2,10)", "%CMUL", 3)

    def test_math_cdiv_asg(self):
        """$%CDIV^MATH(Z1,Z2,PREC) ASG captures function call semantics (Annex I-2.14)."""
        verify_math_function("$$%CDIV^MATH(Z1,Z2,10)", "%CDIV", 3)

    def test_math_cexp_asg(self):
        """$%CEXP^MATH(Z,PREC) ASG captures function call semantics (Annex I-2.15)."""
        verify_math_function("$$%CEXP^MATH(Z,10)", "%CEXP", 2)

    def test_math_clog_asg(self):
        """$%CLOG^MATH(Z,PREC) ASG captures function call semantics (Annex I-2.16)."""
        verify_math_function("$$%CLOG^MATH(Z,10)", "%CLOG", 2)

    def test_math_cpower_asg(self):
        """$%CPOWER^MATH(Z,N,PREC) ASG captures function call semantics (Annex I-2.24a)."""
        verify_math_function("$$%CPOWER^MATH(Z,N,10)", "%CPOWER", 3)

    def test_math_csin_asg(self):
        """$%CSIN^MATH(Z,PREC) ASG captures function call semantics (Annex I-2.17a)."""
        verify_math_function("$$%CSIN^MATH(Z,10)", "%CSIN", 2)

    def test_math_ccos_asg(self):
        """$%CCOS^MATH(Z,PREC) ASG captures function call semantics (Annex I-2.14a)."""
        verify_math_function("$$%CCOS^MATH(Z,10)", "%CCOS", 2)


@pytest.mark.asg
class TestMathLibraryMatrixASG:
    """ASG-level tests for MATH library matrix functions (Annex I-2).

    Functions: MTXADD, MTXSUB, MTXMUL, MTXSCA, MTXCOPY, MTXTRP, MTXDET, MTXINV, MTXCOF, MTXEQU, MTXUNIT.
    """

    def test_math_mtxadd_asg(self):
        """$%MTXADD^MATH(A,B,C) ASG captures function call semantics (Annex I-2.33)."""
        verify_math_function("$$%MTXADD^MATH(A,B,C)", "%MTXADD", 3)

    def test_math_mtxsub_asg(self):
        """$%MTXSUB^MATH(A,B,C) ASG captures function call semantics (Annex I-2.40)."""
        verify_math_function("$$%MTXSUB^MATH(A,B,C)", "%MTXSUB", 3)

    def test_math_mtxmul_asg(self):
        """$%MTXMUL^MATH(A,B,C,PREC) ASG captures function call semantics (Annex I-2.38)."""
        verify_math_function("$$%MTXMUL^MATH(A,B,C,10)", "%MTXMUL", 4)

    def test_math_mtxsca_asg(self):
        """$%MTXSCA^MATH(A,S,B) ASG captures function call semantics (Annex I-2.39)."""
        verify_math_function("$$%MTXSCA^MATH(A,S,B)", "%MTXSCA", 3)

    def test_math_mtxcopy_asg(self):
        """$%MTXCOPY^MATH(A,B) ASG captures function call semantics (Annex I-2.35)."""
        verify_math_function("$$%MTXCOPY^MATH(A,B)", "%MTXCOPY", 2)

    def test_math_mtxtrp_asg(self):
        """$%MTXTRP^MATH(A,B) ASG captures function call semantics (Annex I-2.41)."""
        verify_math_function("$$%MTXTRP^MATH(A,B)", "%MTXTRP", 2)

    def test_math_mtxdet_asg(self):
        """$%MTXDET^MATH(A,PREC) ASG captures function call semantics (Annex I-2.36)."""
        verify_math_function("$$%MTXDET^MATH(A,10)", "%MTXDET", 2)

    def test_math_mtxinv_asg(self):
        """$%MTXINV^MATH(A,B,PREC) ASG captures function call semantics (Annex I-2.37)."""
        verify_math_function("$$%MTXINV^MATH(A,B,10)", "%MTXINV", 3)

    def test_math_mtxcof_asg(self):
        """$%MTXCOF^MATH(A,B,PREC) ASG captures function call semantics (Annex I-2.34)."""
        verify_math_function("$$%MTXCOF^MATH(A,B,10)", "%MTXCOF", 3)

    def test_math_mtxequ_asg(self):
        """$%MTXEQU^MATH(A,B) ASG captures function call semantics (Annex I-2.36a)."""
        verify_math_function("$$%MTXEQU^MATH(A,B)", "%MTXEQU", 2)

    def test_math_mtxunit_asg(self):
        """$%MTXUNIT^MATH(A,N) ASG captures function call semantics (Annex I-2.41a)."""
        verify_math_function("$$%MTXUNIT^MATH(A,N)", "%MTXUNIT", 2)
