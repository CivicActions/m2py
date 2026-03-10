"""Unit tests for _patch_startup_shutdown and _FIXTURE_OVERRIDES.

Verifies that:
- DMUDIC00 is the only routine with a fixture override
- ZZDGPTCO1 is NOT bypassed (its STARTUP runs natively)
- _patch_startup_shutdown patches STARTUP/SHUTDOWN for overridden routines
- _patch_startup_shutdown is a no-op for non-overridden routines
- _patch_startup_shutdown is a no-op when fixture data is absent
"""

from __future__ import annotations

import types
from unittest.mock import MagicMock


from tests.functional.munit.lib.adapter import (
    _FIXTURE_OVERRIDES,
    _patch_startup_shutdown,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_module(name: str, **attrs) -> types.ModuleType:
    """Create a minimal module with given attributes."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


def _make_runtime(global_data: dict[tuple[str, tuple[str, ...]], str] | None = None):
    """Create a mock runtime with a globals store."""
    rt = MagicMock()
    data = global_data or {}

    def mock_get(name, subscripts):
        return data.get((name, subscripts), "")

    rt.globals.get = mock_get
    return rt


# ---------------------------------------------------------------------------
# _FIXTURE_OVERRIDES membership
# ---------------------------------------------------------------------------


class TestFixtureOverridesMembership:
    """Verify which routines have fixture overrides."""

    def test_dmudic00_is_overridden(self):
        assert "DMUDIC00" in _FIXTURE_OVERRIDES

    def test_zzdgptco1_not_overridden(self):
        """ZZDGPTCO1 bypass was removed — its STARTUP runs natively."""
        assert "ZZDGPTCO1" not in _FIXTURE_OVERRIDES

    def test_only_dmudic00_overridden(self):
        assert list(_FIXTURE_OVERRIDES.keys()) == ["DMUDIC00"]


# ---------------------------------------------------------------------------
# _patch_startup_shutdown behavior
# ---------------------------------------------------------------------------


class TestPatchStartupShutdown:
    """Verify _patch_startup_shutdown patching logic."""

    def test_patches_startup_when_data_present(self):
        """DMUDIC00's STARTUP should be replaced when ^DMU(1009.802,0) exists."""
        original_startup = lambda _rt, _scope: None  # noqa: E731
        mod = _make_module("DMUDIC00", STARTUP=original_startup)
        rt = _make_runtime({("DMU", ("1009.802", "0")): "some_value"})

        _patch_startup_shutdown("DMUDIC00", mod, rt)
        assert mod.STARTUP is not original_startup

    def test_patches_shutdown_when_data_present(self):
        """DMUDIC00's SHUTDOWN should be replaced when fixture data exists."""
        original_shutdown = lambda _rt, _scope: None  # noqa: E731
        mod = _make_module("DMUDIC00", SHUTDOWN=original_shutdown)
        rt = _make_runtime({("DMU", ("1009.802", "0")): "some_value"})

        _patch_startup_shutdown("DMUDIC00", mod, rt)
        assert mod.SHUTDOWN is not original_shutdown

    def test_noop_for_non_overridden_routine(self):
        """ZZDGPTCO1 should not be patched — it's not in _FIXTURE_OVERRIDES."""
        original_startup = lambda _rt, _scope: None  # noqa: E731
        mod = _make_module("ZZDGPTCO1", STARTUP=original_startup)
        rt = _make_runtime({("DG", ("45.86", "0")): "some_value"})

        _patch_startup_shutdown("ZZDGPTCO1", mod, rt)
        assert mod.STARTUP is original_startup

    def test_noop_when_module_is_none(self):
        """No crash when module is None."""
        rt = _make_runtime()
        _patch_startup_shutdown("DMUDIC00", None, rt)  # should not raise

    def test_noop_when_data_absent(self):
        """STARTUP not patched when fixture global is missing."""
        original_startup = lambda _rt, _scope: None  # noqa: E731
        mod = _make_module("DMUDIC00", STARTUP=original_startup)
        rt = _make_runtime()  # empty globals

        _patch_startup_shutdown("DMUDIC00", mod, rt)
        assert mod.STARTUP is original_startup

    def test_noop_when_data_empty_string(self):
        """STARTUP not patched when fixture global is empty string."""
        original_startup = lambda _rt, _scope: None  # noqa: E731
        mod = _make_module("DMUDIC00", STARTUP=original_startup)
        rt = _make_runtime({("DMU", ("1009.802", "0")): ""})

        _patch_startup_shutdown("DMUDIC00", mod, rt)
        assert mod.STARTUP is original_startup

    def test_noop_when_globals_raise(self):
        """STARTUP not patched when runtime.globals.get raises."""
        original_startup = lambda _rt, _scope: None  # noqa: E731
        mod = _make_module("DMUDIC00", STARTUP=original_startup)
        rt = MagicMock()
        rt.globals.get.side_effect = KeyError("not found")

        _patch_startup_shutdown("DMUDIC00", mod, rt)
        assert mod.STARTUP is original_startup

    def test_patched_startup_is_callable(self):
        """The replacement STARTUP should be callable with standard args."""
        mod = _make_module("DMUDIC00", STARTUP=lambda _rt, _scope: None)
        rt = _make_runtime({("DMU", ("1009.802", "0")): "some_value"})

        _patch_startup_shutdown("DMUDIC00", mod, rt)
        # Call the patched startup — should not raise
        mod.STARTUP(rt, {})

    def test_patched_startup_does_not_set_dt(self):
        """After removing ZZDGPTCO1 bypass, the stub no longer sets DT."""
        mod = _make_module("DMUDIC00", STARTUP=lambda _rt, _scope: None)
        rt = _make_runtime({("DMU", ("1009.802", "0")): "some_value"})

        _patch_startup_shutdown("DMUDIC00", mod, rt)
        scope: dict = {}
        mod.STARTUP(rt, scope)
        assert "DT" not in scope

    def test_only_patches_existing_attrs(self):
        """Module without STARTUP/SHUTDOWN attrs should not gain them."""
        mod = _make_module("DMUDIC00")  # no STARTUP or SHUTDOWN
        rt = _make_runtime({("DMU", ("1009.802", "0")): "some_value"})

        _patch_startup_shutdown("DMUDIC00", mod, rt)
        assert not hasattr(mod, "STARTUP")
        assert not hasattr(mod, "SHUTDOWN")
