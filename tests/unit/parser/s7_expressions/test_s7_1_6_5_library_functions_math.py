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

    Reference: MUMPS 1995 ANSI §7.1.6.5
    """

    def test_math_arcsin(self, parse_mumps):
        """$%ARCSIN^MATH(X,PREC) parses correctly (§7.1.6.5.8).

        ARCSIN^MATH returns the trigonometric arcsine in radians.
        Range: -π/2 ≤ result ≤ π/2. Error M28 if |X| > 1.
        """
        routine = parse_mumps("TEST S A=$$ARCSIN^MATH(0.5)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "ARCSIN"
        assert assign.value.target.routine == "MATH"

    def test_math_arccos(self, parse_mumps):
        """$%ARCCOS^MATH(X,PREC) parses correctly (§7.1.6.5.2).

        ARCCOS^MATH returns the trigonometric arccosine in radians.
        Range: 0 ≤ result ≤ π. Error M28 if |X| > 1.
        """
        routine = parse_mumps("TEST S A=$$ARCCOS^MATH(0.5)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "ARCCOS"
        assert assign.value.target.routine == "MATH"

    def test_math_arctan(self, parse_mumps):
        """$%ARCTAN^MATH(X,PREC) parses correctly (§7.1.6.5.10).

        ARCTAN^MATH returns the trigonometric arctangent in radians.
        Range: |result| ≤ π/2.
        """
        routine = parse_mumps("TEST S A=$$ARCTAN^MATH(1)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "ARCTAN"
        assert assign.value.target.routine == "MATH"

    def test_math_arccot(self, parse_mumps):
        """$%ARCCOT^MATH(X,PREC) parses correctly (§7.1.6.5.4).

        ARCCOT^MATH returns the trigonometric arccotangent in radians.
        """
        routine = parse_mumps("TEST S A=$$ARCCOT^MATH(1)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "ARCCOT"
        assert assign.value.target.routine == "MATH"

    def test_math_arcsec(self, parse_mumps):
        """$%ARCSEC^MATH(X,PREC) parses correctly (§7.1.6.5.7).

        ARCSEC^MATH returns the trigonometric arcsecant in radians.
        """
        routine = parse_mumps("TEST S A=$$ARCSEC^MATH(2)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "ARCSEC"
        assert assign.value.target.routine == "MATH"

    def test_math_arccsc(self, parse_mumps):
        """$%ARCCSC^MATH(X,PREC) parses correctly (§7.1.6.5.6).

        ARCCSC^MATH returns the trigonometric arccosecant in radians.
        """
        routine = parse_mumps("TEST S A=$$ARCCSC^MATH(2)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "ARCCSC"
        assert assign.value.target.routine == "MATH"

    def test_math_arcsinh(self, parse_mumps):
        """$%ARCSINH^MATH(X,PREC) parses correctly (§7.1.6.5.9).

        ARCSINH^MATH returns the hyperbolic arcsine.
        """
        routine = parse_mumps("TEST S A=$$ARCSINH^MATH(1)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "ARCSINH"
        assert assign.value.target.routine == "MATH"

    def test_math_arccosh(self, parse_mumps):
        """$%ARCCOSH^MATH(X,PREC) parses correctly (§7.1.6.5.3).

        ARCCOSH^MATH returns the hyperbolic arccosine.
        Error M28 if X < 1.
        """
        routine = parse_mumps("TEST S A=$$ARCCOSH^MATH(1)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "ARCCOSH"
        assert assign.value.target.routine == "MATH"

    def test_math_arctanh(self, parse_mumps):
        """$%ARCTANH^MATH(X,PREC) parses correctly (§7.1.6.5.11).

        ARCTANH^MATH returns the hyperbolic arctangent.
        Error M28 if |X| ≥ 1.
        """
        routine = parse_mumps("TEST S A=$$ARCTANH^MATH(0.5)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "ARCTANH"
        assert assign.value.target.routine == "MATH"

    def test_math_arccoth(self, parse_mumps):
        """$%ARCCOTH^MATH(X,PREC) parses correctly (§7.1.6.5.5).

        ARCCOTH^MATH returns the hyperbolic arccotangent.
        Error M28 if |X| ≤ 1.
        """
        routine = parse_mumps("TEST S A=$$ARCCOTH^MATH(2)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "ARCCOTH"
        assert assign.value.target.routine == "MATH"


@pytest.mark.parser
class TestMathLibraryExponentialParsing:
    """Parser-level tests for MATH library exponential/logarithmic functions (Annex I-2).

    Functions: EXP, LOG, LOG10, E, PI, SQRT, SIGN, ABS.
    """

    def test_math_exp(self, parse_mumps):
        """$%EXP^MATH(X,PREC) parses correctly (Annex I-2.30).

        EXP^MATH returns e raised to the power X.
        """
        routine = parse_mumps("TEST S A=$$EXP^MATH(2)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "EXP"
        assert assign.value.target.routine == "MATH"

    def test_math_log(self, parse_mumps):
        """$%LOG^MATH(X,PREC) parses correctly (Annex I-2.31).

        LOG^MATH returns the natural logarithm of X.
        Error M28 if X ≤ 0.
        """
        routine = parse_mumps("TEST S A=$$LOG^MATH(10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "LOG"
        assert assign.value.target.routine == "MATH"

    def test_math_log10(self, parse_mumps):
        """$%LOG10^MATH(X,PREC) parses correctly (Annex I-2.32).

        LOG10^MATH returns the base-10 logarithm of X.
        Error M28 if X ≤ 0.
        """
        routine = parse_mumps("TEST S A=$$LOG10^MATH(100)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "LOG10"
        assert assign.value.target.routine == "MATH"

    def test_math_e(self, parse_mumps):
        """$%E^MATH(PREC) parses correctly (Annex I-2.29).

        E^MATH returns the mathematical constant e (Euler's number).
        """
        routine = parse_mumps("TEST S A=$$E^MATH(10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "E"
        assert assign.value.target.routine == "MATH"

    def test_math_pi(self, parse_mumps):
        """$%PI^MATH(PREC) parses correctly (Annex I-2.42).

        PI^MATH returns the mathematical constant π.
        """
        routine = parse_mumps("TEST S A=$$PI^MATH(10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "PI"
        assert assign.value.target.routine == "MATH"

    def test_math_sqrt(self, parse_mumps):
        """$%SQRT^MATH(X,PREC) parses correctly (Annex I-2.49).

        SQRT^MATH returns the square root of X.
        Error M28 if X < 0.
        """
        routine = parse_mumps("TEST S A=$$SQRT^MATH(16)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "SQRT"
        assert assign.value.target.routine == "MATH"

    def test_math_sign(self, parse_mumps):
        """$%SIGN^MATH(X) parses correctly (Annex I-2.46).

        SIGN^MATH returns -1 if X<0, 0 if X=0, 1 if X>0.
        """
        routine = parse_mumps("TEST S A=$$SIGN^MATH(-5)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "SIGN"
        assert assign.value.target.routine == "MATH"

    def test_math_abs(self, parse_mumps):
        """$%ABS^MATH(X) parses correctly (Annex I-2.1).

        ABS^MATH returns the absolute value of X.
        """
        routine = parse_mumps("TEST S A=$$ABS^MATH(-42)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "ABS"
        assert assign.value.target.routine == "MATH"


@pytest.mark.parser
class TestMathLibraryAngleConversionParsing:
    """Parser-level tests for MATH library angle conversion functions (Annex I-2).

    Functions: DEGRAD, RADDEG, DECDMS, DMSDEC.
    """

    def test_math_degrad(self, parse_mumps):
        """$%DEGRAD^MATH(X,PREC) parses correctly (Annex I-2.28).

        DEGRAD^MATH converts degrees to radians.
        """
        routine = parse_mumps("TEST S A=$$DEGRAD^MATH(180)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "DEGRAD"
        assert assign.value.target.routine == "MATH"

    def test_math_raddeg(self, parse_mumps):
        """$%RADDEG^MATH(X,PREC) parses correctly (Annex I-2.43).

        RADDEG^MATH converts radians to degrees.
        """
        routine = parse_mumps("TEST S A=$$RADDEG^MATH(3.14159)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "RADDEG"
        assert assign.value.target.routine == "MATH"

    def test_math_decdms(self, parse_mumps):
        """$%DECDMS^MATH(X,PREC) parses correctly (Annex I-2.27).

        DECDMS^MATH converts decimal degrees to degrees/minutes/seconds.
        """
        routine = parse_mumps("TEST S A=$$DECDMS^MATH(45.5)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "DECDMS"
        assert assign.value.target.routine == "MATH"

    def test_math_dmsdec(self, parse_mumps):
        """$%DMSDEC^MATH(X) parses correctly (Annex I-2.28a).

        DMSDEC^MATH converts degrees/minutes/seconds to decimal degrees.
        """
        routine = parse_mumps("TEST S A=$$DMSDEC^MATH(453000)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "DMSDEC"
        assert assign.value.target.routine == "MATH"


@pytest.mark.parser
class TestMathLibraryComplexNumberParsing:
    """Parser-level tests for MATH library complex number functions (Annex I-2).

    Functions: COMPLEX, CONJUG, CABS, CADD, CSUB, CMUL, CDIV, CEXP, CLOG, CPOWER, CSIN, CCOS.
    """

    def test_math_complex(self, parse_mumps):
        """$%COMPLEX^MATH(REAL,IMAG) parses correctly (Annex I-2.19).

        COMPLEX^MATH creates a complex number from real and imaginary parts.
        """
        routine = parse_mumps("TEST S A=$$COMPLEX^MATH(3,4)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "COMPLEX"
        assert assign.value.target.routine == "MATH"

    def test_math_conjug(self, parse_mumps):
        """$%CONJUG^MATH(Z) parses correctly (Annex I-2.20).

        CONJUG^MATH returns the complex conjugate.
        """
        routine = parse_mumps("TEST S A=$$CONJUG^MATH(Z)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CONJUG"
        assert assign.value.target.routine == "MATH"

    def test_math_cabs(self, parse_mumps):
        """$%CABS^MATH(Z,PREC) parses correctly (Annex I-2.12).

        CABS^MATH returns the absolute value (modulus) of a complex number.
        """
        routine = parse_mumps("TEST S A=$$CABS^MATH(Z,10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CABS"
        assert assign.value.target.routine == "MATH"

    def test_math_cadd(self, parse_mumps):
        """$%CADD^MATH(Z1,Z2) parses correctly (Annex I-2.13).

        CADD^MATH adds two complex numbers.
        """
        routine = parse_mumps("TEST S A=$$CADD^MATH(Z1,Z2)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CADD"
        assert assign.value.target.routine == "MATH"

    def test_math_csub(self, parse_mumps):
        """$%CSUB^MATH(Z1,Z2) parses correctly (Annex I-2.17).

        CSUB^MATH subtracts two complex numbers.
        """
        routine = parse_mumps("TEST S A=$$CSUB^MATH(Z1,Z2)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CSUB"
        assert assign.value.target.routine == "MATH"

    def test_math_cmul(self, parse_mumps):
        """$%CMUL^MATH(Z1,Z2,PREC) parses correctly (Annex I-2.18).

        CMUL^MATH multiplies two complex numbers.
        """
        routine = parse_mumps("TEST S A=$$CMUL^MATH(Z1,Z2,10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CMUL"
        assert assign.value.target.routine == "MATH"

    def test_math_cdiv(self, parse_mumps):
        """$%CDIV^MATH(Z1,Z2,PREC) parses correctly (Annex I-2.14).

        CDIV^MATH divides two complex numbers.
        """
        routine = parse_mumps("TEST S A=$$CDIV^MATH(Z1,Z2,10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CDIV"
        assert assign.value.target.routine == "MATH"

    def test_math_cexp(self, parse_mumps):
        """$%CEXP^MATH(Z,PREC) parses correctly (Annex I-2.15).

        CEXP^MATH returns e raised to a complex power.
        """
        routine = parse_mumps("TEST S A=$$CEXP^MATH(Z,10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CEXP"
        assert assign.value.target.routine == "MATH"

    def test_math_clog(self, parse_mumps):
        """$%CLOG^MATH(Z,PREC) parses correctly (Annex I-2.16).

        CLOG^MATH returns the natural logarithm of a complex number.
        """
        routine = parse_mumps("TEST S A=$$CLOG^MATH(Z,10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CLOG"
        assert assign.value.target.routine == "MATH"

    def test_math_cpower(self, parse_mumps):
        """$%CPOWER^MATH(Z,N,PREC) parses correctly (Annex I-2.24a).

        CPOWER^MATH raises a complex number to an integer power.
        """
        routine = parse_mumps("TEST S A=$$CPOWER^MATH(Z,2,10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CPOWER"
        assert assign.value.target.routine == "MATH"

    def test_math_csin(self, parse_mumps):
        """$%CSIN^MATH(Z,PREC) parses correctly (Annex I-2.17a).

        CSIN^MATH returns the sine of a complex number.
        """
        routine = parse_mumps("TEST S A=$$CSIN^MATH(Z,10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CSIN"
        assert assign.value.target.routine == "MATH"

    def test_math_ccos(self, parse_mumps):
        """$%CCOS^MATH(Z,PREC) parses correctly (Annex I-2.14a).

        CCOS^MATH returns the cosine of a complex number.
        """
        routine = parse_mumps("TEST S A=$$CCOS^MATH(Z,10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "CCOS"
        assert assign.value.target.routine == "MATH"


@pytest.mark.parser
class TestMathLibraryMatrixParsing:
    """Parser-level tests for MATH library matrix functions (Annex I-2).

    Functions: MTXADD, MTXSUB, MTXMUL, MTXSCA, MTXCOPY, MTXTRP, MTXDET, MTXINV, MTXCOF, MTXEQU, MTXUNIT.
    """

    def test_math_mtxadd(self, parse_mumps):
        """$%MTXADD^MATH(A,B,C) parses correctly (Annex I-2.33).

        MTXADD^MATH adds two matrices: C = A + B.
        """
        routine = parse_mumps("TEST S X=$$MTXADD^MATH(A,B,C)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "MTXADD"
        assert assign.value.target.routine == "MATH"

    def test_math_mtxsub(self, parse_mumps):
        """$%MTXSUB^MATH(A,B,C) parses correctly (Annex I-2.40).

        MTXSUB^MATH subtracts two matrices: C = A - B.
        """
        routine = parse_mumps("TEST S X=$$MTXSUB^MATH(A,B,C)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "MTXSUB"
        assert assign.value.target.routine == "MATH"

    def test_math_mtxmul(self, parse_mumps):
        """$%MTXMUL^MATH(A,B,C,PREC) parses correctly (Annex I-2.38).

        MTXMUL^MATH multiplies two matrices: C = A * B.
        """
        routine = parse_mumps("TEST S X=$$MTXMUL^MATH(A,B,C,10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "MTXMUL"
        assert assign.value.target.routine == "MATH"

    def test_math_mtxsca(self, parse_mumps):
        """$%MTXSCA^MATH(A,S,B) parses correctly (Annex I-2.39).

        MTXSCA^MATH scales a matrix: B = S * A.
        """
        routine = parse_mumps("TEST S X=$$MTXSCA^MATH(A,2,B)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "MTXSCA"
        assert assign.value.target.routine == "MATH"

    def test_math_mtxcopy(self, parse_mumps):
        """$%MTXCOPY^MATH(A,B) parses correctly (Annex I-2.35).

        MTXCOPY^MATH copies a matrix: B = A.
        """
        routine = parse_mumps("TEST S X=$$MTXCOPY^MATH(A,B)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "MTXCOPY"
        assert assign.value.target.routine == "MATH"

    def test_math_mtxtrp(self, parse_mumps):
        """$%MTXTRP^MATH(A,B) parses correctly (Annex I-2.41).

        MTXTRP^MATH transposes a matrix: B = A^T.
        """
        routine = parse_mumps("TEST S X=$$MTXTRP^MATH(A,B)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "MTXTRP"
        assert assign.value.target.routine == "MATH"

    def test_math_mtxdet(self, parse_mumps):
        """$%MTXDET^MATH(A,PREC) parses correctly (Annex I-2.36).

        MTXDET^MATH computes the determinant of a matrix.
        """
        routine = parse_mumps("TEST S X=$$MTXDET^MATH(A,10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "MTXDET"
        assert assign.value.target.routine == "MATH"

    def test_math_mtxinv(self, parse_mumps):
        """$%MTXINV^MATH(A,B,PREC) parses correctly (Annex I-2.37).

        MTXINV^MATH computes the inverse of a matrix: B = A^-1.
        """
        routine = parse_mumps("TEST S X=$$MTXINV^MATH(A,B,10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "MTXINV"
        assert assign.value.target.routine == "MATH"

    def test_math_mtxcof(self, parse_mumps):
        """$%MTXCOF^MATH(A,B,PREC) parses correctly (Annex I-2.34).

        MTXCOF^MATH computes the cofactor matrix.
        """
        routine = parse_mumps("TEST S X=$$MTXCOF^MATH(A,B,10)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "MTXCOF"
        assert assign.value.target.routine == "MATH"

    def test_math_mtxequ(self, parse_mumps):
        """$%MTXEQU^MATH(A,B) parses correctly (Annex I-2.36a).

        MTXEQU^MATH tests matrix equality: returns 1 if A = B, else 0.
        """
        routine = parse_mumps("TEST S X=$$MTXEQU^MATH(A,B)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "MTXEQU"
        assert assign.value.target.routine == "MATH"

    def test_math_mtxunit(self, parse_mumps):
        """$%MTXUNIT^MATH(A,N) parses correctly (Annex I-2.41a).

        MTXUNIT^MATH creates an N x N identity matrix in A.
        """
        routine = parse_mumps("TEST S X=$$MTXUNIT^MATH(A,3)")
        label = routine.labels[0]
        stmt = label.body.statements[0]

        assign = stmt.assignments[0]
        assert isinstance(assign.value, ExtrinsicFunction)
        assert assign.value.target.name == "MTXUNIT"
        assert assign.value.target.routine == "MATH"
