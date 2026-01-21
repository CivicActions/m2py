"""Tests for MATH Library Functions codegen (Annex I-2, §7.1.6.5).

Reference: MUMPS 1995 ANSI Standard, Annex I Section 2

MATH library functions fall into two categories:
1. IMPLEMENTED (Spec 013): Basic trig, inverse trig, exp, log, sqrt
   - These functions generate working Python code that calls m2py.runtime.routines.MATH
2. NOT IMPLEMENTED (LIM-014): All other MATH functions
   - These raise NotImplementedError with LIM-014 at codegen time

Implemented functions (13 total):
  - Trigonometric: %SIN, %COS, %TAN
  - Inverse trig: %ARCSIN, %ASIN (alias), %ARCCOS, %ACOS (alias), %ARCTAN, %ATAN (alias)
  - Exponential/logarithmic: %EXP, %LOG, %LN (alias), %SQRT

Unimplemented functions (44 remaining):
  - Hyperbolic: %SINH, %COSH, %TANH, %COTH, %SECH, %CSCH, %ARCSINH, %ARCCOSH, %ARCTANH, %ARCCOTH
  - Other trig: %COT, %SEC, %CSC, %ARCSEC, %ARCCSC
  - Precision-based: %E, %PI, %LOG10, %SIGN, %ABS
  - Angle conversion: %DEGRAD, %RADDEG, %DECDMS, %DMSDEC
  - Complex numbers: All %C* functions (COMPLEX, CONJUG, CABS, CADD, CSUB, CMUL, CDIV, etc.)
  - Matrix operations: All %MTX* functions

Per LIM-014: STRING and CHARACTER libraries are completely blocked;
MATH library has basic functions implemented, others raise LIM-014.
"""

import math

import pytest

from m2py.codegen import generate_python


# =============================================================================
# IMPLEMENTED MATH FUNCTIONS (Spec 013) - Should generate working code
# =============================================================================


@pytest.mark.codegen
class TestMathLibraryTrigonometricImplemented:
    """Codegen tests for IMPLEMENTED trigonometric functions (Spec 013).

    These generate Python code that calls the bundled MATH routine.
    """

    def test_math_sin_generates_code(self, execute_mumps):
        """$$%SIN^MATH(x) generates working code (Spec 013 FR-037)."""
        # sin(0) = 0
        result = execute_mumps("TEST W $$%SIN^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(0.0, abs=1e-10)

        # sin(π/2) = 1
        result = execute_mumps(f"TEST W $$%SIN^MATH({math.pi / 2}) Q")
        assert float(result.output.strip()) == pytest.approx(1.0)

    def test_math_cos_generates_code(self, execute_mumps):
        """$$%COS^MATH(x) generates working code (Spec 013 FR-037)."""
        # cos(0) = 1
        result = execute_mumps("TEST W $$%COS^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(1.0)

        # cos(π) = -1
        result = execute_mumps(f"TEST W $$%COS^MATH({math.pi}) Q")
        assert float(result.output.strip()) == pytest.approx(-1.0)

    def test_math_tan_generates_code(self, execute_mumps):
        """$$%TAN^MATH(x) generates working code (Spec 013 FR-037)."""
        # tan(0) = 0
        result = execute_mumps("TEST W $$%TAN^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(0.0, abs=1e-10)

        # tan(π/4) = 1
        result = execute_mumps(f"TEST W $$%TAN^MATH({math.pi / 4}) Q")
        assert float(result.output.strip()) == pytest.approx(1.0)


@pytest.mark.codegen
class TestMathLibraryInverseTrigImplemented:
    """Codegen tests for IMPLEMENTED inverse trigonometric functions (Spec 013)."""

    def test_math_arcsin_generates_code(self, execute_mumps):
        """$$%ARCSIN^MATH(x) generates working code (Spec 013 FR-038)."""
        # arcsin(0) = 0
        result = execute_mumps("TEST W $$%ARCSIN^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(0.0, abs=1e-10)

        # arcsin(1) = π/2
        result = execute_mumps("TEST W $$%ARCSIN^MATH(1) Q")
        assert float(result.output.strip()) == pytest.approx(math.pi / 2)

    def test_math_asin_alias_generates_code(self, execute_mumps):
        """$$%ASIN^MATH(x) is alias for %ARCSIN (Spec 013)."""
        result = execute_mumps("TEST W $$%ASIN^MATH(0.5) Q")
        assert float(result.output.strip()) == pytest.approx(math.asin(0.5))

    def test_math_arccos_generates_code(self, execute_mumps):
        """$$%ARCCOS^MATH(x) generates working code (Spec 013 FR-038)."""
        # arccos(1) = 0
        result = execute_mumps("TEST W $$%ARCCOS^MATH(1) Q")
        assert float(result.output.strip()) == pytest.approx(0.0, abs=1e-10)

        # arccos(0) = π/2
        result = execute_mumps("TEST W $$%ARCCOS^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(math.pi / 2)

    def test_math_acos_alias_generates_code(self, execute_mumps):
        """$$%ACOS^MATH(x) is alias for %ARCCOS (Spec 013)."""
        result = execute_mumps("TEST W $$%ACOS^MATH(0.5) Q")
        assert float(result.output.strip()) == pytest.approx(math.acos(0.5))

    def test_math_arctan_generates_code(self, execute_mumps):
        """$$%ARCTAN^MATH(x) generates working code (Spec 013 FR-038)."""
        # arctan(0) = 0
        result = execute_mumps("TEST W $$%ARCTAN^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(0.0, abs=1e-10)

        # arctan(1) = π/4
        result = execute_mumps("TEST W $$%ARCTAN^MATH(1) Q")
        assert float(result.output.strip()) == pytest.approx(math.pi / 4)

    def test_math_atan_alias_generates_code(self, execute_mumps):
        """$$%ATAN^MATH(x) is alias for %ARCTAN (Spec 013)."""
        result = execute_mumps("TEST W $$%ATAN^MATH(0.5) Q")
        assert float(result.output.strip()) == pytest.approx(math.atan(0.5))


@pytest.mark.codegen
class TestMathLibraryExponentialImplemented:
    """Codegen tests for IMPLEMENTED exponential/logarithmic functions (Spec 013)."""

    def test_math_exp_generates_code(self, execute_mumps):
        """$$%EXP^MATH(x) generates working code (Spec 013 FR-034)."""
        # e^0 = 1
        result = execute_mumps("TEST W $$%EXP^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(1.0)

        # e^1 = e
        result = execute_mumps("TEST W $$%EXP^MATH(1) Q")
        assert float(result.output.strip()) == pytest.approx(math.e)

    def test_math_log_generates_code(self, execute_mumps):
        """$$%LOG^MATH(x) generates working code (Spec 013 FR-035)."""
        # ln(1) = 0
        result = execute_mumps("TEST W $$%LOG^MATH(1) Q")
        assert float(result.output.strip()) == pytest.approx(0.0)

        # ln(e) = 1
        result = execute_mumps(f"TEST W $$%LOG^MATH({math.e}) Q")
        assert float(result.output.strip()) == pytest.approx(1.0)

    def test_math_ln_alias_generates_code(self, execute_mumps):
        """$$%LN^MATH(x) is alias for %LOG (Spec 013)."""
        result = execute_mumps("TEST W $$%LN^MATH(10) Q")
        assert float(result.output.strip()) == pytest.approx(math.log(10))

    def test_math_sqrt_generates_code(self, execute_mumps):
        """$$%SQRT^MATH(x) generates working code (Spec 013 FR-036)."""
        # sqrt(4) = 2
        result = execute_mumps("TEST W $$%SQRT^MATH(4) Q")
        assert float(result.output.strip()) == pytest.approx(2.0)

        # sqrt(2)
        result = execute_mumps("TEST W $$%SQRT^MATH(2) Q")
        assert float(result.output.strip()) == pytest.approx(math.sqrt(2))


@pytest.mark.codegen
class TestMathLibraryDomainErrors:
    """Tests that implemented functions raise domain errors appropriately."""

    def test_math_log_domain_error(self, execute_mumps):
        """$$%LOG^MATH raises domain error for non-positive argument."""
        result = execute_mumps("TEST W $$%LOG^MATH(0) Q")
        assert result.success is False
        assert "DOMAIN" in result.error

        result = execute_mumps("TEST W $$%LOG^MATH(-1) Q")
        assert result.success is False
        assert "DOMAIN" in result.error

    def test_math_sqrt_domain_error(self, execute_mumps):
        """$$%SQRT^MATH raises domain error for negative argument."""
        result = execute_mumps("TEST W $$%SQRT^MATH(-1) Q")
        assert result.success is False
        assert "DOMAIN" in result.error

    def test_math_arcsin_domain_error(self, execute_mumps):
        """$$%ARCSIN^MATH raises domain error for |x| > 1."""
        result = execute_mumps("TEST W $$%ARCSIN^MATH(2) Q")
        assert result.success is False
        assert "DOMAIN" in result.error

    def test_math_arccos_domain_error(self, execute_mumps):
        """$$%ARCCOS^MATH raises domain error for |x| > 1."""
        result = execute_mumps("TEST W $$%ARCCOS^MATH(2) Q")
        assert result.success is False
        assert "DOMAIN" in result.error


@pytest.mark.codegen
class TestMathLibraryCodegenDetails:
    """Tests for code generation details of MATH library functions."""

    def test_generated_code_imports_math_routine(self, generate_python):
        """Generated Python code imports MATH from bundled routines."""
        python_code = generate_python("TEST W $$%SQRT^MATH(4) Q")
        assert "from m2py.runtime.routines import MATH" in python_code

    def test_math_functions_in_expressions(self, execute_mumps):
        """Math library functions can be used in expressions."""
        # Use math result in arithmetic
        result = execute_mumps("TEST W $$%SQRT^MATH(16)+1 Q")
        assert float(result.output.strip()) == pytest.approx(5.0)

    def test_math_functions_nested(self, execute_mumps):
        """Math library functions can be nested."""
        # sqrt(sqrt(16)) = sqrt(4) = 2
        result = execute_mumps("TEST W $$%SQRT^MATH($$%SQRT^MATH(16)) Q")
        assert float(result.output.strip()) == pytest.approx(2.0)

        # ln(e^2) = 2
        result = execute_mumps("TEST W $$%LOG^MATH($$%EXP^MATH(2)) Q")
        assert float(result.output.strip()) == pytest.approx(2.0)


# =============================================================================
# UNIMPLEMENTED MATH FUNCTIONS (LIM-014) - Should raise NotImplementedError
# =============================================================================


@pytest.mark.codegen
class TestMathLibraryHyperbolicUnimplemented:
    """Codegen tests for UNIMPLEMENTED hyperbolic functions (LIM-014).

    All should raise NotImplementedError with LIM-014.
    """

    def test_lim014_math_sinh_raises_error(self):
        """$%SINH^MATH(X,PREC) raises NotImplementedError (Annex I-2.48)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%SINH^MATH(1,2) Q")

    def test_lim014_math_cosh_raises_error(self):
        """$%COSH^MATH(X,PREC) raises NotImplementedError (Annex I-2.22)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%COSH^MATH(1,2) Q")

    def test_lim014_math_tanh_raises_error(self):
        """$%TANH^MATH(X,PREC) raises NotImplementedError (Annex I-2.51)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%TANH^MATH(1,2) Q")

    def test_lim014_math_coth_raises_error(self):
        """$%COTH^MATH(X,PREC) raises NotImplementedError (Annex I-2.24)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%COTH^MATH(1,2) Q")

    def test_lim014_math_sech_raises_error(self):
        """$%SECH^MATH(X,PREC) raises NotImplementedError (Annex I-2.45)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%SECH^MATH(1,2) Q")

    def test_lim014_math_csch_raises_error(self):
        """$%CSCH^MATH(X,PREC) raises NotImplementedError (Annex I-2.26)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%CSCH^MATH(1,2) Q")

    def test_lim014_math_arcsinh_raises_error(self):
        """$%ARCSINH^MATH(X,PREC) raises NotImplementedError (Annex I-2.9)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%ARCSINH^MATH(1,2) Q")

    def test_lim014_math_arccosh_raises_error(self):
        """$%ARCCOSH^MATH(X,PREC) raises NotImplementedError (Annex I-2.3)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%ARCCOSH^MATH(2,2) Q")

    def test_lim014_math_arctanh_raises_error(self):
        """$%ARCTANH^MATH(X,PREC) raises NotImplementedError (Annex I-2.11)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%ARCTANH^MATH(0.5,2) Q")

    def test_lim014_math_arccoth_raises_error(self):
        """$%ARCCOTH^MATH(X,PREC) raises NotImplementedError (Annex I-2.5)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%ARCCOTH^MATH(2,2) Q")


@pytest.mark.codegen
class TestMathLibraryOtherTrigUnimplemented:
    """Codegen tests for UNIMPLEMENTED other trig functions (LIM-014).

    COT, SEC, CSC and their inverses are not implemented.
    """

    def test_lim014_math_cot_raises_error(self):
        """$%COT^MATH(X,PREC) raises NotImplementedError (Annex I-2.23)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%COT^MATH(1,2) Q")

    def test_lim014_math_sec_raises_error(self):
        """$%SEC^MATH(X,PREC) raises NotImplementedError (Annex I-2.44)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%SEC^MATH(1,2) Q")

    def test_lim014_math_csc_raises_error(self):
        """$%CSC^MATH(X,PREC) raises NotImplementedError (Annex I-2.25)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%CSC^MATH(1,2) Q")

    def test_lim014_math_arcsec_raises_error(self):
        """$%ARCSEC^MATH(X,PREC) raises NotImplementedError (Annex I-2.7)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%ARCSEC^MATH(2,2) Q")

    def test_lim014_math_arccsc_raises_error(self):
        """$%ARCCSC^MATH(X,PREC) raises NotImplementedError (Annex I-2.6)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%ARCCSC^MATH(2,2) Q")


@pytest.mark.codegen
class TestMathLibraryConstantsUnimplemented:
    """Codegen tests for UNIMPLEMENTED mathematical constants (LIM-014).

    E, PI, LOG10, SIGN, ABS functions are not implemented.
    """

    def test_lim014_math_e_raises_error(self):
        """$%E^MATH(PREC) raises NotImplementedError (Annex I-2.29)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%E^MATH(10) Q")

    def test_lim014_math_pi_raises_error(self):
        """$%PI^MATH(PREC) raises NotImplementedError (Annex I-2.42)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%PI^MATH(10) Q")

    def test_lim014_math_log10_raises_error(self):
        """$%LOG10^MATH(X,PREC) raises NotImplementedError (Annex I-2.32)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%LOG10^MATH(100,2) Q")

    def test_lim014_math_sign_raises_error(self):
        """$%SIGN^MATH(X) raises NotImplementedError (Annex I-2.46)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%SIGN^MATH(-5) Q")

    def test_lim014_math_abs_raises_error(self):
        """$%ABS^MATH(X) raises NotImplementedError (Annex I-2.1)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%ABS^MATH(-5) Q")


@pytest.mark.codegen
class TestMathLibraryAngleConversionUnimplemented:
    """Codegen tests for UNIMPLEMENTED angle conversion functions (LIM-014)."""

    def test_lim014_math_degrad_raises_error(self):
        """$%DEGRAD^MATH(X,PREC) raises NotImplementedError (Annex I-2.28)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%DEGRAD^MATH(180,10) Q")

    def test_lim014_math_raddeg_raises_error(self):
        """$%RADDEG^MATH(X,PREC) raises NotImplementedError (Annex I-2.43)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%RADDEG^MATH(3.14159,2) Q")

    def test_lim014_math_decdms_raises_error(self):
        """$%DECDMS^MATH(X,PREC) raises NotImplementedError (Annex I-2.27)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%DECDMS^MATH(45.5,4) Q")

    def test_lim014_math_dmsdec_raises_error(self):
        """$%DMSDEC^MATH(X) raises NotImplementedError (Annex I-2.28a)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%DMSDEC^MATH(453000) Q")


@pytest.mark.codegen
class TestMathLibraryComplexNumberUnimplemented:
    """Codegen tests for UNIMPLEMENTED complex number functions (LIM-014)."""

    def test_lim014_math_complex_raises_error(self):
        """$%COMPLEX^MATH(REAL,IMAG) raises NotImplementedError (Annex I-2.19)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python("TEST S X=$$%COMPLEX^MATH(3,4) Q")

    def test_lim014_math_conjug_raises_error(self):
        """$%CONJUG^MATH(Z) raises NotImplementedError (Annex I-2.20)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CONJUG^MATH("3,4") Q')

    def test_lim014_math_cabs_raises_error(self):
        """$%CABS^MATH(Z,PREC) raises NotImplementedError (Annex I-2.12)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CABS^MATH("3,4",2) Q')

    def test_lim014_math_cadd_raises_error(self):
        """$%CADD^MATH(Z1,Z2) raises NotImplementedError (Annex I-2.13)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CADD^MATH("1,2","3,4") Q')

    def test_lim014_math_csub_raises_error(self):
        """$%CSUB^MATH(Z1,Z2) raises NotImplementedError (Annex I-2.17)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CSUB^MATH("3,4","1,2") Q')

    def test_lim014_math_cmul_raises_error(self):
        """$%CMUL^MATH(Z1,Z2,PREC) raises NotImplementedError (Annex I-2.18)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CMUL^MATH("1,2","3,4",2) Q')

    def test_lim014_math_cdiv_raises_error(self):
        """$%CDIV^MATH(Z1,Z2,PREC) raises NotImplementedError (Annex I-2.14)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CDIV^MATH("3,4","1,2",2) Q')

    def test_lim014_math_cexp_raises_error(self):
        """$%CEXP^MATH(Z,PREC) raises NotImplementedError (Annex I-2.15)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CEXP^MATH("0,3.14159",2) Q')

    def test_lim014_math_clog_raises_error(self):
        """$%CLOG^MATH(Z,PREC) raises NotImplementedError (Annex I-2.16)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CLOG^MATH("1,1",2) Q')

    def test_lim014_math_cpower_raises_error(self):
        """$%CPOWER^MATH(Z,N,PREC) raises NotImplementedError (Annex I-2.24a)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CPOWER^MATH("1,1",2,2) Q')

    def test_lim014_math_csin_raises_error(self):
        """$%CSIN^MATH(Z,PREC) raises NotImplementedError (Annex I-2.17a)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CSIN^MATH("0,1",2) Q')

    def test_lim014_math_ccos_raises_error(self):
        """$%CCOS^MATH(Z,PREC) raises NotImplementedError (Annex I-2.14a)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%CCOS^MATH("0,1",2) Q')


@pytest.mark.codegen
class TestMathLibraryMatrixUnimplemented:
    """Codegen tests for UNIMPLEMENTED matrix functions (LIM-014)."""

    def test_lim014_math_mtxadd_raises_error(self):
        """$%MTXADD^MATH(A,B,C) raises NotImplementedError (Annex I-2.33)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%MTXADD^MATH("A","B","C") Q')

    def test_lim014_math_mtxsub_raises_error(self):
        """$%MTXSUB^MATH(A,B,C) raises NotImplementedError (Annex I-2.40)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%MTXSUB^MATH("A","B","C") Q')

    def test_lim014_math_mtxmul_raises_error(self):
        """$%MTXMUL^MATH(A,B,C,PREC) raises NotImplementedError (Annex I-2.38)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%MTXMUL^MATH("A","B","C",2) Q')

    def test_lim014_math_mtxsca_raises_error(self):
        """$%MTXSCA^MATH(A,S,B) raises NotImplementedError (Annex I-2.39)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%MTXSCA^MATH("A",2,"B") Q')

    def test_lim014_math_mtxcopy_raises_error(self):
        """$%MTXCOPY^MATH(A,B) raises NotImplementedError (Annex I-2.35)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%MTXCOPY^MATH("A","B") Q')

    def test_lim014_math_mtxtrp_raises_error(self):
        """$%MTXTRP^MATH(A,B) raises NotImplementedError (Annex I-2.41)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%MTXTRP^MATH("A","B") Q')

    def test_lim014_math_mtxdet_raises_error(self):
        """$%MTXDET^MATH(A,PREC) raises NotImplementedError (Annex I-2.36)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%MTXDET^MATH("A",2) Q')

    def test_lim014_math_mtxinv_raises_error(self):
        """$%MTXINV^MATH(A,B,PREC) raises NotImplementedError (Annex I-2.37)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%MTXINV^MATH("A","B",2) Q')

    def test_lim014_math_mtxcof_raises_error(self):
        """$%MTXCOF^MATH(A,B,PREC) raises NotImplementedError (Annex I-2.34)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%MTXCOF^MATH("A","B",2) Q')

    def test_lim014_math_mtxequ_raises_error(self):
        """$%MTXEQU^MATH(A,B) raises NotImplementedError (Annex I-2.36a)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%MTXEQU^MATH("A","B") Q')

    def test_lim014_math_mtxunit_raises_error(self):
        """$%MTXUNIT^MATH(A,N) raises NotImplementedError (Annex I-2.41a)."""
        with pytest.raises(NotImplementedError, match="LIM-014"):
            generate_python('TEST S X=$$%MTXUNIT^MATH("A",3) Q')
