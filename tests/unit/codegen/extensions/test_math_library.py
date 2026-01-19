"""Tests for Math Library Functions (Spec 013 Phase 13).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.5 (as library functions)

The MUMPS standard defines math functions as library functions in the %MATH routine,
not as intrinsic functions. The syntax is:
    $$%SIN^MATH(x)   - sine
    $$%COS^MATH(x)   - cosine
    $$%SQRT^MATH(x)  - square root
    etc.

m2py provides a bundled %MATH routine in src/m2py/runtime/routines/MATH.py that
implements these functions using Python's math module.

Note: YottaDB does NOT have a built-in %MATH routine - these tests run with m2py only.
"""

import math

import pytest


@pytest.mark.codegen
class TestMathLibraryFunctionsCodegen:
    """Codegen-level tests for math library functions (Spec 013 Phase 13).

    These functions are implemented as extrinsic function calls to the bundled
    %MATH routine, following standard MUMPS library function syntax.
    """

    def test_function_exp(self, execute_mumps):
        """$$%EXP^MATH returns e^x (exponential function).

        Spec 013 FR-034: Implement %EXP using math.exp.
        """
        # Test 1: e^0 = 1
        result = execute_mumps("TEST W $$%EXP^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(1.0)

        # Test 2: e^1 = e
        result = execute_mumps("TEST W $$%EXP^MATH(1) Q")
        assert float(result.output.strip()) == pytest.approx(math.e)

        # Test 3: e^2
        result = execute_mumps("TEST W $$%EXP^MATH(2) Q")
        assert float(result.output.strip()) == pytest.approx(math.exp(2))

        # Test 4: Negative exponent
        result = execute_mumps("TEST W $$%EXP^MATH(-1) Q")
        assert float(result.output.strip()) == pytest.approx(1 / math.e)

    def test_function_log(self, execute_mumps):
        """$$%LOG^MATH returns natural logarithm (ln).

        Spec 013 FR-035: Implement %LOG using math.log.
        """
        # Test 1: ln(1) = 0
        result = execute_mumps("TEST W $$%LOG^MATH(1) Q")
        assert float(result.output.strip()) == pytest.approx(0.0)

        # Test 2: ln(e) = 1
        result = execute_mumps(f"TEST W $$%LOG^MATH({math.e}) Q")
        assert float(result.output.strip()) == pytest.approx(1.0)

        # Test 3: ln(10)
        result = execute_mumps("TEST W $$%LOG^MATH(10) Q")
        assert float(result.output.strip()) == pytest.approx(math.log(10))

    def test_function_log_domain_error(self, execute_mumps):
        """$$%LOG^MATH raises domain error for non-positive argument."""
        result = execute_mumps("TEST W $$%LOG^MATH(0) Q")
        assert result.success is False
        assert "DOMAIN" in result.error

        result = execute_mumps("TEST W $$%LOG^MATH(-1) Q")
        assert result.success is False
        assert "DOMAIN" in result.error

    def test_function_sqrt(self, execute_mumps):
        """$$%SQRT^MATH returns square root.

        Spec 013 FR-036: Implement %SQRT using math.sqrt.
        """
        # Test 1: sqrt(4) = 2
        result = execute_mumps("TEST W $$%SQRT^MATH(4) Q")
        assert float(result.output.strip()) == pytest.approx(2.0)

        # Test 2: sqrt(2)
        result = execute_mumps("TEST W $$%SQRT^MATH(2) Q")
        assert float(result.output.strip()) == pytest.approx(math.sqrt(2))

        # Test 3: sqrt(0) = 0
        result = execute_mumps("TEST W $$%SQRT^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(0.0)

    def test_function_sqrt_domain_error(self, execute_mumps):
        """$$%SQRT^MATH raises domain error for negative argument."""
        result = execute_mumps("TEST W $$%SQRT^MATH(-1) Q")
        assert result.success is False
        assert "DOMAIN" in result.error

    def test_function_sin(self, execute_mumps):
        """$$%SIN^MATH returns sine (radians).

        Spec 013 FR-037: Implement %SIN using math.sin.
        """
        # Test 1: sin(0) = 0
        result = execute_mumps("TEST W $$%SIN^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(0.0, abs=1e-10)

        # Test 2: sin(π/2) = 1
        result = execute_mumps(f"TEST W $$%SIN^MATH({math.pi / 2}) Q")
        assert float(result.output.strip()) == pytest.approx(1.0)

        # Test 3: sin(π) ≈ 0
        result = execute_mumps(f"TEST W $$%SIN^MATH({math.pi}) Q")
        assert float(result.output.strip()) == pytest.approx(0.0, abs=1e-10)

    def test_function_cos(self, execute_mumps):
        """$$%COS^MATH returns cosine (radians).

        Spec 013 FR-037: Implement %COS using math.cos.
        """
        # Test 1: cos(0) = 1
        result = execute_mumps("TEST W $$%COS^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(1.0)

        # Test 2: cos(π/2) ≈ 0
        result = execute_mumps(f"TEST W $$%COS^MATH({math.pi / 2}) Q")
        assert float(result.output.strip()) == pytest.approx(0.0, abs=1e-10)

        # Test 3: cos(π) = -1
        result = execute_mumps(f"TEST W $$%COS^MATH({math.pi}) Q")
        assert float(result.output.strip()) == pytest.approx(-1.0)

    def test_function_tan(self, execute_mumps):
        """$$%TAN^MATH returns tangent (radians).

        Spec 013 FR-037: Implement %TAN using math.tan.
        """
        # Test 1: tan(0) = 0
        result = execute_mumps("TEST W $$%TAN^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(0.0, abs=1e-10)

        # Test 2: tan(π/4) = 1
        result = execute_mumps(f"TEST W $$%TAN^MATH({math.pi / 4}) Q")
        assert float(result.output.strip()) == pytest.approx(1.0)

    def test_function_arcsin(self, execute_mumps):
        """$$%ARCSIN^MATH returns arc sine (radians).

        Spec 013 FR-038: Implement %ARCSIN using math.asin.
        """
        # Test 1: arcsin(0) = 0
        result = execute_mumps("TEST W $$%ARCSIN^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(0.0, abs=1e-10)

        # Test 2: arcsin(1) = π/2
        result = execute_mumps("TEST W $$%ARCSIN^MATH(1) Q")
        assert float(result.output.strip()) == pytest.approx(math.pi / 2)

        # Test 3: arcsin(-1) = -π/2
        result = execute_mumps("TEST W $$%ARCSIN^MATH(-1) Q")
        assert float(result.output.strip()) == pytest.approx(-math.pi / 2)

    def test_function_arcsin_domain_error(self, execute_mumps):
        """$$%ARCSIN^MATH raises domain error for |x| > 1."""
        result = execute_mumps("TEST W $$%ARCSIN^MATH(2) Q")
        assert result.success is False
        assert "DOMAIN" in result.error

        result = execute_mumps("TEST W $$%ARCSIN^MATH(-2) Q")
        assert result.success is False
        assert "DOMAIN" in result.error

    def test_function_arccos(self, execute_mumps):
        """$$%ARCCOS^MATH returns arc cosine (radians).

        Spec 013 FR-038: Implement %ARCCOS using math.acos.
        """
        # Test 1: arccos(1) = 0
        result = execute_mumps("TEST W $$%ARCCOS^MATH(1) Q")
        assert float(result.output.strip()) == pytest.approx(0.0, abs=1e-10)

        # Test 2: arccos(0) = π/2
        result = execute_mumps("TEST W $$%ARCCOS^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(math.pi / 2)

        # Test 3: arccos(-1) = π
        result = execute_mumps("TEST W $$%ARCCOS^MATH(-1) Q")
        assert float(result.output.strip()) == pytest.approx(math.pi)

    def test_function_arccos_domain_error(self, execute_mumps):
        """$$%ARCCOS^MATH raises domain error for |x| > 1."""
        result = execute_mumps("TEST W $$%ARCCOS^MATH(2) Q")
        assert result.success is False
        assert "DOMAIN" in result.error

    def test_function_arctan(self, execute_mumps):
        """$$%ARCTAN^MATH returns arc tangent (radians).

        Spec 013 FR-038: Implement %ARCTAN using math.atan.
        """
        # Test 1: arctan(0) = 0
        result = execute_mumps("TEST W $$%ARCTAN^MATH(0) Q")
        assert float(result.output.strip()) == pytest.approx(0.0, abs=1e-10)

        # Test 2: arctan(1) = π/4
        result = execute_mumps("TEST W $$%ARCTAN^MATH(1) Q")
        assert float(result.output.strip()) == pytest.approx(math.pi / 4)

        # Test 3: arctan(-1) = -π/4
        result = execute_mumps("TEST W $$%ARCTAN^MATH(-1) Q")
        assert float(result.output.strip()) == pytest.approx(-math.pi / 4)

    def test_function_ln_alias(self, execute_mumps):
        """$$%LN^MATH is an alias for $$%LOG^MATH."""
        # LN is an alias for LOG
        result = execute_mumps("TEST W $$%LN^MATH(10) Q")
        assert float(result.output.strip()) == pytest.approx(math.log(10))

    def test_function_asin_alias(self, execute_mumps):
        """$$%ASIN^MATH is an alias for $$%ARCSIN^MATH."""
        result = execute_mumps("TEST W $$%ASIN^MATH(0.5) Q")
        assert float(result.output.strip()) == pytest.approx(math.asin(0.5))

    def test_function_acos_alias(self, execute_mumps):
        """$$%ACOS^MATH is an alias for $$%ARCCOS^MATH."""
        result = execute_mumps("TEST W $$%ACOS^MATH(0.5) Q")
        assert float(result.output.strip()) == pytest.approx(math.acos(0.5))

    def test_function_atan_alias(self, execute_mumps):
        """$$%ATAN^MATH is an alias for $$%ARCTAN^MATH."""
        result = execute_mumps("TEST W $$%ATAN^MATH(0.5) Q")
        assert float(result.output.strip()) == pytest.approx(math.atan(0.5))

    def test_generated_code_imports_math_routine(self, generate_python):
        """Generated Python code imports MATH from bundled routines.

        The codegen should detect %MATH calls and import the bundled MATH module
        from m2py.runtime.routines instead of looking for an external MATH.py.
        """
        python_code = generate_python("TEST W $$%SQRT^MATH(4) Q")
        assert "from m2py.runtime.routines import MATH" in python_code

    def test_math_functions_in_expressions(self, execute_mumps):
        """Math library functions can be used in expressions."""
        # Use math result in arithmetic
        result = execute_mumps("TEST W $$%SQRT^MATH(16)+1 Q")
        assert float(result.output.strip()) == pytest.approx(5.0)

        # Use math result in SET
        result = execute_mumps("TEST S X=$$%SIN^MATH(0)*2 W X Q")
        assert float(result.output.strip()) == pytest.approx(0.0)

    def test_math_functions_nested(self, execute_mumps):
        """Math library functions can be nested."""
        # sqrt(sqrt(16)) = sqrt(4) = 2
        result = execute_mumps("TEST W $$%SQRT^MATH($$%SQRT^MATH(16)) Q")
        assert float(result.output.strip()) == pytest.approx(2.0)

        # ln(e^2) = 2
        result = execute_mumps("TEST W $$%LOG^MATH($$%EXP^MATH(2)) Q")
        assert float(result.output.strip()) == pytest.approx(2.0)
