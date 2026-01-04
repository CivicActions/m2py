"""Tests for MATH Library Functions parsing (Annex I-2, §7.1.6.5).

Tests verify the textX grammar correctly captures MATH library function syntax.
MATH library functions are called as $$%FUNC^MATH or $$FUNC^MATH.

Reference: MUMPS 1995 ANSI Standard, Annex I Section 2
Total: 57 MATH library functions
"""

import pytest

from m2py.parser.textx_classes import ExtrinsicFunction, NumericLiteral


@pytest.mark.parser
class TestMathLibraryTrigonometricParsing:
    """Parser-level tests for MATH library trigonometric functions (Annex I-2).

    Trigonometric functions: SIN, COS, TAN, COT, SEC, CSC and their hyperbolics.

    MATH library functions are extrinsic functions called as $$FUNC^MATH(args).
    Each function takes an angle in radians and optional precision parameter.

    Reference: MUMPS 1995 ANSI §7.1.6.5
    """

    def test_math_sin(self, parse_mumps):
        """$%SIN^MATH(X,PREC) parses correctly (§7.1.6.5.53).

        SIN^MATH returns the trigonometric sine of X (radians).
        Returns value in range [-1, 1].
        """
        routine = parse_mumps("TEST S X=$$SIN^MATH(3.14159)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        # Value is an ExtrinsicFunction
        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)

        # Check the target call
        call = assign.value.target
        assert call.name == "SIN"
        assert call.routine == "MATH"

        # Check argument
        assert len(assign.value.arguments) == 1
        arg = assign.value.arguments[0]
        assert isinstance(arg.expression, NumericLiteral)
        assert arg.expression.value == 3.14159

    def test_math_cos(self, parse_mumps):
        """$%COS^MATH(X,PREC) parses correctly (§7.1.6.5.21).

        COS^MATH returns the trigonometric cosine of X (radians).
        Returns value in range [-1, 1].
        """
        routine = parse_mumps("TEST S Y=$$COS^MATH(0)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "COS"
        assert assign.value.target.routine == "MATH"

    def test_math_tan(self, parse_mumps):
        """$%TAN^MATH(X,PREC) parses correctly (§7.1.6.5.56).

        TAN^MATH returns the trigonometric tangent of X (radians).
        """
        routine = parse_mumps("TEST S Z=$$TAN^MATH(0.785)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "TAN"
        assert assign.value.target.routine == "MATH"

    def test_math_cot(self, parse_mumps):
        """$%COT^MATH(X,PREC) parses correctly (§7.1.6.5.23).

        COT^MATH returns the trigonometric cotangent of X (radians).
        """
        routine = parse_mumps("TEST S C=$$COT^MATH(1.57)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "COT"
        assert assign.value.target.routine == "MATH"

    def test_math_sec(self, parse_mumps):
        """$%SEC^MATH(X,PREC) parses correctly (§7.1.6.5.44).

        SEC^MATH returns the trigonometric secant of X (radians).
        """
        routine = parse_mumps("TEST S S=$$SEC^MATH(0)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "SEC"
        assert assign.value.target.routine == "MATH"

    def test_math_csc(self, parse_mumps):
        """$%CSC^MATH(X,PREC) parses correctly (§7.1.6.5.25).

        CSC^MATH returns the trigonometric cosecant of X (radians).
        """
        routine = parse_mumps("TEST S C=$$CSC^MATH(1.57)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CSC"
        assert assign.value.target.routine == "MATH"

    def test_math_sinh(self, parse_mumps):
        """$%SINH^MATH(X,PREC) parses correctly (§7.1.6.5.54).

        SINH^MATH returns the hyperbolic sine of X.
        """
        routine = parse_mumps("TEST S H=$$SINH^MATH(1)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "SINH"
        assert assign.value.target.routine == "MATH"

    def test_math_cosh(self, parse_mumps):
        """$%COSH^MATH(X,PREC) parses correctly (§7.1.6.5.22).

        COSH^MATH returns the hyperbolic cosine of X.
        """
        routine = parse_mumps("TEST S H=$$COSH^MATH(0)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "COSH"
        assert assign.value.target.routine == "MATH"

    def test_math_tanh(self, parse_mumps):
        """$%TANH^MATH(X,PREC) parses correctly (§7.1.6.5.57).

        TANH^MATH returns the hyperbolic tangent of X.
        """
        routine = parse_mumps("TEST S H=$$TANH^MATH(1)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "TANH"
        assert assign.value.target.routine == "MATH"

    def test_math_coth(self, parse_mumps):
        """$%COTH^MATH(X,PREC) parses correctly (§7.1.6.5.24).

        COTH^MATH returns the hyperbolic cotangent of X.
        """
        routine = parse_mumps("TEST S H=$$COTH^MATH(1)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "COTH"
        assert assign.value.target.routine == "MATH"

    def test_math_sech(self, parse_mumps):
        """$%SECH^MATH(X,PREC) parses correctly (§7.1.6.5.45).

        SECH^MATH returns the hyperbolic secant of X.
        """
        routine = parse_mumps("TEST S H=$$SECH^MATH(0)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "SECH"
        assert assign.value.target.routine == "MATH"

    def test_math_csch(self, parse_mumps):
        """$%CSCH^MATH(X,PREC) parses correctly (§7.1.6.5.26).

        CSCH^MATH returns the hyperbolic cosecant of X.
        """
        routine = parse_mumps("TEST S H=$$CSCH^MATH(1)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CSCH"
        assert assign.value.target.routine == "MATH"


@pytest.mark.parser
class TestMathLibraryInverseTrigParsing:
    """Parser-level tests for MATH library inverse trigonometric functions (Annex I-2).

    Inverse functions: ARCSIN, ARCCOS, ARCTAN, ARCCOT, ARCSEC, ARCCSC and hyperbolics.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%ARCSIN^MATH library function parsing"
    )
    def test_math_arcsin(self):
        """$%ARCSIN^MATH(X,PREC) parses correctly (Annex I-2.8)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%ARCCOS^MATH library function parsing"
    )
    def test_math_arccos(self):
        """$%ARCCOS^MATH(X,PREC) parses correctly (Annex I-2.2)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%ARCTAN^MATH library function parsing"
    )
    def test_math_arctan(self):
        """$%ARCTAN^MATH(X,Y,PREC) parses correctly (Annex I-2.10)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%ARCCOT^MATH library function parsing"
    )
    def test_math_arccot(self):
        """$%ARCCOT^MATH(X,PREC) parses correctly (Annex I-2.4)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%ARCSEC^MATH library function parsing"
    )
    def test_math_arcsec(self):
        """$%ARCSEC^MATH(X,PREC) parses correctly (Annex I-2.7)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%ARCCSC^MATH library function parsing"
    )
    def test_math_arccsc(self):
        """$%ARCCSC^MATH(X,PREC) parses correctly (Annex I-2.6)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%ARCSINH^MATH library function parsing"
    )
    def test_math_arcsinh(self):
        """$%ARCSINH^MATH(X,PREC) parses correctly (Annex I-2.9)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%ARCCOSH^MATH library function parsing"
    )
    def test_math_arccosh(self):
        """$%ARCCOSH^MATH(X,PREC) parses correctly (Annex I-2.3)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%ARCTANH^MATH library function parsing"
    )
    def test_math_arctanh(self):
        """$%ARCTANH^MATH(X,PREC) parses correctly (Annex I-2.11)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%ARCCOTH^MATH library function parsing"
    )
    def test_math_arccoth(self):
        """$%ARCCOTH^MATH(X,PREC) parses correctly (Annex I-2.5)."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestMathLibraryExponentialParsing:
    """Parser-level tests for MATH library exponential/logarithmic functions (Annex I-2).

    Functions: EXP, LOG, LOG10, E, PI, SQRT, SIGN, ABS.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%EXP^MATH library function parsing"
    )
    def test_math_exp(self):
        """$%EXP^MATH(X,PREC) parses correctly (Annex I-2.30)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%LOG^MATH library function parsing"
    )
    def test_math_log(self):
        """$%LOG^MATH(X,PREC) parses correctly (Annex I-2.31)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%LOG10^MATH library function parsing"
    )
    def test_math_log10(self):
        """$%LOG10^MATH(X,PREC) parses correctly (Annex I-2.32)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $%E^MATH library function parsing")
    def test_math_e(self):
        """$%E^MATH(PREC) parses correctly (Annex I-2.29)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: $%PI^MATH library function parsing")
    def test_math_pi(self):
        """$%PI^MATH(PREC) parses correctly (Annex I-2.42)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%SQRT^MATH library function parsing"
    )
    def test_math_sqrt(self):
        """$%SQRT^MATH(X,PREC) parses correctly (Annex I-2.49)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%SIGN^MATH library function parsing"
    )
    def test_math_sign(self):
        """$%SIGN^MATH(X) parses correctly (Annex I-2.46)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%ABS^MATH library function parsing"
    )
    def test_math_abs(self):
        """$%ABS^MATH(X) parses correctly (Annex I-2.1)."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestMathLibraryAngleConversionParsing:
    """Parser-level tests for MATH library angle conversion functions (Annex I-2).

    Functions: DEGRAD, RADDEG, DECDMS, DMSDEC.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%DEGRAD^MATH library function parsing"
    )
    def test_math_degrad(self):
        """$%DEGRAD^MATH(X,PREC) parses correctly (Annex I-2.28)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%RADDEG^MATH library function parsing"
    )
    def test_math_raddeg(self):
        """$%RADDEG^MATH(X,PREC) parses correctly (Annex I-2.43)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%DECDMS^MATH library function parsing"
    )
    def test_math_decdms(self):
        """$%DECDMS^MATH(X,PREC) parses correctly (Annex I-2.27)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%DMSDEC^MATH library function parsing"
    )
    def test_math_dmsdec(self):
        """$%DMSDEC^MATH(X) parses correctly (Annex I-2.28a)."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestMathLibraryComplexNumberParsing:
    """Parser-level tests for MATH library complex number functions (Annex I-2).

    Functions: COMPLEX, CONJUG, CABS, CADD, CSUB, CMUL, CDIV, CEXP, CLOG, CPOWER, CSIN, CCOS.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%COMPLEX^MATH library function parsing"
    )
    def test_math_complex(self):
        """$%COMPLEX^MATH(REAL,IMAG) parses correctly (Annex I-2.19)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CONJUG^MATH library function parsing"
    )
    def test_math_conjug(self):
        """$%CONJUG^MATH(Z) parses correctly (Annex I-2.20)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CABS^MATH library function parsing"
    )
    def test_math_cabs(self):
        """$%CABS^MATH(Z,PREC) parses correctly (Annex I-2.12)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CADD^MATH library function parsing"
    )
    def test_math_cadd(self):
        """$%CADD^MATH(Z1,Z2) parses correctly (Annex I-2.13)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CSUB^MATH library function parsing"
    )
    def test_math_csub(self):
        """$%CSUB^MATH(Z1,Z2) parses correctly (Annex I-2.17)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CMUL^MATH library function parsing"
    )
    def test_math_cmul(self):
        """$%CMUL^MATH(Z1,Z2,PREC) parses correctly (Annex I-2.18)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CDIV^MATH library function parsing"
    )
    def test_math_cdiv(self):
        """$%CDIV^MATH(Z1,Z2,PREC) parses correctly (Annex I-2.14)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CEXP^MATH library function parsing"
    )
    def test_math_cexp(self):
        """$%CEXP^MATH(Z,PREC) parses correctly (Annex I-2.15)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CLOG^MATH library function parsing"
    )
    def test_math_clog(self):
        """$%CLOG^MATH(Z,PREC) parses correctly (Annex I-2.16)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CPOWER^MATH library function parsing"
    )
    def test_math_cpower(self):
        """$%CPOWER^MATH(Z,N,PREC) parses correctly (Annex I-2.24a)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CSIN^MATH library function parsing"
    )
    def test_math_csin(self):
        """$%CSIN^MATH(Z,PREC) parses correctly (Annex I-2.17a)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%CCOS^MATH library function parsing"
    )
    def test_math_ccos(self):
        """$%CCOS^MATH(Z,PREC) parses correctly (Annex I-2.14a)."""
        pytest.fail("Stub - implement test")


@pytest.mark.parser
class TestMathLibraryMatrixParsing:
    """Parser-level tests for MATH library matrix functions (Annex I-2).

    Functions: MTXADD, MTXSUB, MTXMUL, MTXSCA, MTXCOPY, MTXTRP, MTXDET, MTXINV, MTXCOF, MTXEQU, MTXUNIT.
    """

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%MTXADD^MATH library function parsing"
    )
    def test_math_mtxadd(self):
        """$%MTXADD^MATH(A,B,C) parses correctly (Annex I-2.33)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%MTXSUB^MATH library function parsing"
    )
    def test_math_mtxsub(self):
        """$%MTXSUB^MATH(A,B,C) parses correctly (Annex I-2.40)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%MTXMUL^MATH library function parsing"
    )
    def test_math_mtxmul(self):
        """$%MTXMUL^MATH(A,B,C,PREC) parses correctly (Annex I-2.38)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%MTXSCA^MATH library function parsing"
    )
    def test_math_mtxsca(self):
        """$%MTXSCA^MATH(A,S,B) parses correctly (Annex I-2.39)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%MTXCOPY^MATH library function parsing"
    )
    def test_math_mtxcopy(self):
        """$%MTXCOPY^MATH(A,B) parses correctly (Annex I-2.35)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%MTXTRP^MATH library function parsing"
    )
    def test_math_mtxtrp(self):
        """$%MTXTRP^MATH(A,B) parses correctly (Annex I-2.41)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%MTXDET^MATH library function parsing"
    )
    def test_math_mtxdet(self):
        """$%MTXDET^MATH(A,PREC) parses correctly (Annex I-2.36)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%MTXINV^MATH library function parsing"
    )
    def test_math_mtxinv(self):
        """$%MTXINV^MATH(A,B,PREC) parses correctly (Annex I-2.37)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%MTXCOF^MATH library function parsing"
    )
    def test_math_mtxcof(self):
        """$%MTXCOF^MATH(A,B,PREC) parses correctly (Annex I-2.34)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%MTXEQU^MATH library function parsing"
    )
    def test_math_mtxequ(self):
        """$%MTXEQU^MATH(A,B) parses correctly (Annex I-2.36a)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(
        reason="Not yet implemented: $%MTXUNIT^MATH library function parsing"
    )
    def test_math_mtxunit(self):
        """$%MTXUNIT^MATH(A,N) parses correctly (Annex I-2.41a)."""
        pytest.fail("Stub - implement test")
