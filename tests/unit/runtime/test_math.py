"""Tests for runtime/routines/MATH.py percent math functions.

Tests all 13 %MATH functions:
_pct_SIN, _pct_COS, _pct_TAN, _pct_ARCSIN, _pct_ARCCOS, _pct_ARCTAN,
_pct_SQRT, _pct_EXP, _pct_LOG, _pct_LN, _pct_ASIN, _pct_ACOS, _pct_ATAN

All take (_rt, x_str, _scope=None) → str.
"""

import math
import pytest

from m2py.runtime.routines.MATH import (
    _pct_SIN,
    _pct_COS,
    _pct_TAN,
    _pct_ARCSIN,
    _pct_ARCCOS,
    _pct_ARCTAN,
    _pct_SQRT,
    _pct_EXP,
    _pct_LOG,
    _pct_LN,
    _pct_ASIN,
    _pct_ACOS,
    _pct_ATAN,
)


class TestMathSin:
    """Tests for %SIN."""

    def test_sin_zero(self):
        result = _pct_SIN(None, "0")
        assert float(result) == pytest.approx(0.0)

    def test_sin_pi_half(self):
        result = _pct_SIN(None, str(math.pi / 2))
        assert float(result) == pytest.approx(1.0)

    def test_sin_pi(self):
        result = _pct_SIN(None, str(math.pi))
        assert float(result) == pytest.approx(0.0, abs=1e-10)


class TestMathCos:
    """Tests for %COS."""

    def test_cos_zero(self):
        result = _pct_COS(None, "0")
        assert float(result) == pytest.approx(1.0)

    def test_cos_pi(self):
        result = _pct_COS(None, str(math.pi))
        assert float(result) == pytest.approx(-1.0)


class TestMathTan:
    """Tests for %TAN."""

    def test_tan_zero(self):
        result = _pct_TAN(None, "0")
        assert float(result) == pytest.approx(0.0)

    def test_tan_pi_quarter(self):
        result = _pct_TAN(None, str(math.pi / 4))
        assert float(result) == pytest.approx(1.0)


class TestMathArcsin:
    """Tests for %ARCSIN and %ASIN (alias)."""

    def test_arcsin_zero(self):
        result = _pct_ARCSIN(None, "0")
        assert float(result) == pytest.approx(0.0)

    def test_arcsin_one(self):
        result = _pct_ARCSIN(None, "1")
        assert float(result) == pytest.approx(math.pi / 2)

    def test_arcsin_domain_error(self):
        """ARCSIN(2) should raise domain error."""
        with pytest.raises((ValueError, Exception)):
            _pct_ARCSIN(None, "2")

    def test_asin_is_alias(self):
        """ASIN should give same result as ARCSIN."""
        r1 = _pct_ARCSIN(None, "0.5")
        r2 = _pct_ASIN(None, "0.5")
        assert float(r1) == pytest.approx(float(r2))


class TestMathArccos:
    """Tests for %ARCCOS and %ACOS (alias)."""

    def test_arccos_one(self):
        result = _pct_ARCCOS(None, "1")
        assert float(result) == pytest.approx(0.0)

    def test_arccos_zero(self):
        result = _pct_ARCCOS(None, "0")
        assert float(result) == pytest.approx(math.pi / 2)

    def test_arccos_domain_error(self):
        """ARCCOS(2) should raise domain error."""
        with pytest.raises((ValueError, Exception)):
            _pct_ARCCOS(None, "2")

    def test_acos_is_alias(self):
        r1 = _pct_ARCCOS(None, "0.5")
        r2 = _pct_ACOS(None, "0.5")
        assert float(r1) == pytest.approx(float(r2))


class TestMathArctan:
    """Tests for %ARCTAN and %ATAN (alias)."""

    def test_arctan_zero(self):
        result = _pct_ARCTAN(None, "0")
        assert float(result) == pytest.approx(0.0)

    def test_arctan_one(self):
        result = _pct_ARCTAN(None, "1")
        assert float(result) == pytest.approx(math.pi / 4)

    def test_atan_is_alias(self):
        r1 = _pct_ARCTAN(None, "1")
        r2 = _pct_ATAN(None, "1")
        assert float(r1) == pytest.approx(float(r2))


class TestMathSqrt:
    """Tests for %SQRT."""

    def test_sqrt_four(self):
        result = _pct_SQRT(None, "4")
        assert float(result) == pytest.approx(2.0)

    def test_sqrt_zero(self):
        result = _pct_SQRT(None, "0")
        assert float(result) == pytest.approx(0.0)

    def test_sqrt_domain_error(self):
        """SQRT(-1) should raise domain error."""
        with pytest.raises((ValueError, Exception)):
            _pct_SQRT(None, "-1")


class TestMathExp:
    """Tests for %EXP."""

    def test_exp_zero(self):
        result = _pct_EXP(None, "0")
        assert float(result) == pytest.approx(1.0)

    def test_exp_one(self):
        result = _pct_EXP(None, "1")
        assert float(result) == pytest.approx(math.e)


class TestMathLog:
    """Tests for %LOG and %LN (alias)."""

    def test_log_one(self):
        result = _pct_LOG(None, "1")
        assert float(result) == pytest.approx(0.0)

    def test_log_e(self):
        result = _pct_LOG(None, str(math.e))
        assert float(result) == pytest.approx(1.0)

    def test_log_domain_error(self):
        """LOG(0) should raise domain error."""
        with pytest.raises((ValueError, Exception)):
            _pct_LOG(None, "0")

    def test_log_negative_domain_error(self):
        """LOG(-1) should raise domain error."""
        with pytest.raises((ValueError, Exception)):
            _pct_LOG(None, "-1")

    def test_ln_is_alias(self):
        r1 = _pct_LOG(None, "2")
        r2 = _pct_LN(None, "2")
        assert float(r1) == pytest.approx(float(r2))


class TestMathReturnType:
    """All functions return str."""

    def test_all_return_strings(self):
        funcs = [
            (_pct_SIN, "0"),
            (_pct_COS, "0"),
            (_pct_TAN, "0"),
            (_pct_ARCSIN, "0"),
            (_pct_ARCCOS, "0"),
            (_pct_ARCTAN, "0"),
            (_pct_SQRT, "4"),
            (_pct_EXP, "1"),
            (_pct_LOG, "1"),
        ]
        for func, arg in funcs:
            result = func(None, arg)
            assert isinstance(result, str), f"{func.__name__} should return str"
