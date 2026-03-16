"""Tests for _build_kernel_scope in adapter.py.

Validates that the VistA Kernel standard variables are correctly
initialized in the scope dictionary used by transpile_and_execute().

Variables tested:
  U       = "^"          — piece delimiter
  DUZ     = 1            — user IEN
  DUZ(0)  = "@"          — programmer access
  DTIME   = 999          — terminal timeout
  DT      = <today>      — FileMan internal date (YYYMMDD)
  IO      = "0"          — principal device
  IO(0)   = "0"          — principal device at login
"""

from __future__ import annotations

import datetime
from unittest.mock import MagicMock


from tests.functional.munit.lib.adapter import _build_kernel_scope


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_runtime(principal: str = "0") -> MagicMock:
    """Create a minimal mock runtime with principal() method."""
    rt = MagicMock()
    rt.principal.return_value = principal
    return rt


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBuildKernelScope:
    """Tests for _build_kernel_scope."""

    def test_returns_dict(self):
        scope = _build_kernel_scope(_make_runtime())
        assert isinstance(scope, dict)

    def test_u_piece_delimiter(self):
        scope = _build_kernel_scope(_make_runtime())
        assert scope["U"].value == "^"

    def test_duz_user_ien(self):
        scope = _build_kernel_scope(_make_runtime())
        assert scope["DUZ"].value == 1

    def test_duz_zero_programmer_access(self):
        scope = _build_kernel_scope(_make_runtime())
        assert scope["DUZ"].get("0") == "@"

    def test_dtime_timeout(self):
        scope = _build_kernel_scope(_make_runtime())
        assert scope["DTIME"].value == 999

    def test_dt_is_filemandate_today(self):
        scope = _build_kernel_scope(_make_runtime())
        today = datetime.date.today()
        expected = (today.year - 1700) * 10000 + today.month * 100 + today.day
        assert scope["DT"].value == expected

    def test_dt_format_is_integer(self):
        """FileMan dates are integers like 3260316 (not strings)."""
        scope = _build_kernel_scope(_make_runtime())
        assert isinstance(scope["DT"].value, int)

    def test_io_principal_device(self):
        scope = _build_kernel_scope(_make_runtime())
        assert scope["IO"].value == "0"

    def test_io_zero_principal_at_login(self):
        scope = _build_kernel_scope(_make_runtime())
        assert scope["IO"].get("0") == "0"

    def test_io_uses_runtime_principal(self):
        """IO should reflect the runtime's actual $PRINCIPAL value."""
        rt = _make_runtime(principal="/dev/pts/1")
        scope = _build_kernel_scope(rt)
        assert scope["IO"].value == "/dev/pts/1"
        assert scope["IO"].get("0") == "/dev/pts/1"

    def test_all_expected_keys_present(self):
        scope = _build_kernel_scope(_make_runtime())
        expected_keys = {"U", "DUZ", "DTIME", "DT", "IO"}
        assert expected_keys == set(scope.keys())

    def test_values_are_marray(self):
        """All scope values should be MArray instances."""
        from m2py.runtime import MArray

        scope = _build_kernel_scope(_make_runtime())
        for key, val in scope.items():
            assert isinstance(val, MArray), f"scope[{key!r}] is not MArray"
