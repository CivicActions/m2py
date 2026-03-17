"""Tests for _resolve_entry_function and _ResolvedEntry in adapter.py.

The adapter resolves MUMPS invocation strings to Python callables:
- ``D ^ROUTINE``              → module._entry_function
- ``D LABEL^ROUTINE``         → module.LABEL
- ``D EN^%ut("ROUTINE")``     → %ut.EN with routine name as argument
- ``D EN^%ut("ROUTINE",1)``   → with verbosity
- ``D EN^%ut("ROUTINE",1,1)`` → with verbosity and break flag

The key fix was correctly routing ``D EN^%ut("ROUTINE")`` to the %ut
framework module rather than falling back to the target routine's
_entry_function.  This is critical for routines like %utt2, %utt3 that
are designed to be invoked *by* the framework.
"""

from __future__ import annotations

import sys
import types

import pytest

from tests.functional.munit.lib.adapter import (
    _ResolvedEntry,
    _resolve_entry_function,
)
from m2py.runtime import MArray


# ---------------------------------------------------------------------------
# Helpers to create mock modules
# ---------------------------------------------------------------------------


def _make_module(name: str, **attrs) -> types.ModuleType:
    """Create a minimal module with given attributes."""
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


def _entry_stub(rt=None, _scope=None):
    """Stub _entry_function."""
    pass


def _label_stub(rt=None, _scope=None):
    """Stub label function."""
    pass


def _en_stub(rt=None, _scope=None, RNAM=None, VERB=None, BREAK=None):
    """Stub for %ut EN label."""
    pass


# =============================================================================
# _ResolvedEntry tests
# =============================================================================


class TestResolvedEntry:
    """Tests for the _ResolvedEntry helper class."""

    def test_basic_construction(self):
        """_ResolvedEntry stores func, args, description."""
        entry = _ResolvedEntry(func=_entry_stub, description="test")
        assert entry.func is _entry_stub
        assert entry.args == []
        assert entry.description == "test"

    def test_with_args(self):
        """_ResolvedEntry stores args list."""
        arg = MArray()
        arg.value = "MYROUTINE"
        entry = _ResolvedEntry(func=_en_stub, args=[arg], description="EN call")
        assert len(entry.args) == 1
        assert entry.args[0].value == "MYROUTINE"

    def test_default_args_is_empty_list(self):
        """Default args is an empty list, not None."""
        entry = _ResolvedEntry(func=_entry_stub)
        assert entry.args == []
        assert isinstance(entry.args, list)


# =============================================================================
# D ^ROUTINE pattern
# =============================================================================


class TestResolveEntryFunction:
    """Test D ^ROUTINE → _entry_function resolution."""

    def test_d_caret_routine(self):
        """D ^ROUTINE → module._entry_function."""
        mod = _make_module("TESTRTN", _entry_function=_entry_stub)
        result = _resolve_entry_function(mod, "D ^TESTRTN", "TESTRTN")

        assert result is not None
        assert result.func is _entry_stub
        assert result.args == []
        assert "._entry_function" in result.description

    def test_d_caret_routine_no_entry(self):
        """D ^ROUTINE with no _entry_function → None."""
        mod = _make_module("TESTRTN")
        result = _resolve_entry_function(mod, "D ^TESTRTN", "TESTRTN")

        assert result is None

    def test_none_module(self):
        """None module always returns None."""
        result = _resolve_entry_function(None, "D ^TESTRTN", "TESTRTN")
        assert result is None


# =============================================================================
# D LABEL^ROUTINE pattern
# =============================================================================


class TestResolveLabelCall:
    """Test D LABEL^ROUTINE → module.LABEL resolution."""

    def test_d_label_caret_routine(self):
        """D LABEL^ROUTINE → module.LABEL."""
        mod = _make_module("TESTRTN", MYLABEL=_label_stub, _entry_function=_entry_stub)
        result = _resolve_entry_function(mod, "D MYLABEL^TESTRTN", "TESTRTN")

        assert result is not None
        assert result.func is _label_stub
        assert result.args == []
        assert "TESTRTN.MYLABEL" in result.description

    def test_label_not_found_falls_through(self):
        """D LABEL^ROUTINE with unknown label → _entry_function fallback."""
        mod = _make_module("TESTRTN", _entry_function=_entry_stub)
        result = _resolve_entry_function(mod, "D NOLABEL^TESTRTN", "TESTRTN")

        assert result is not None
        assert result.func is _entry_stub
        assert "_entry_function" in result.description

    def test_label_not_found_no_entry(self):
        """D LABEL^ROUTINE, label missing, no _entry_function → None."""
        mod = _make_module("TESTRTN")
        result = _resolve_entry_function(mod, "D NOLABEL^TESTRTN", "TESTRTN")

        assert result is None


# =============================================================================
# D EN^%ut("ROUTINE") pattern — the key fix
# =============================================================================


class TestResolveUtFrameworkCall:
    """Test D EN^%ut("ROUTINE") pattern resolves to %ut module."""

    @pytest.fixture(autouse=True)
    def _setup_ut_module(self):
        """Install a mock _pct_ut module in sys.modules."""
        self.ut_mod = _make_module("_pct_ut", EN=_en_stub)
        sys.modules["_pct_ut"] = self.ut_mod
        yield
        sys.modules.pop("_pct_ut", None)

    def test_en_ut_basic(self):
        """D EN^%ut("MYROUTINE") → %ut.EN with routine name arg."""
        mod = _make_module("MYROUTINE", _entry_function=_entry_stub)
        result = _resolve_entry_function(mod, 'D EN^%ut("MYROUTINE")', "MYROUTINE")

        assert result is not None
        assert result.func is _en_stub
        assert len(result.args) == 1
        assert isinstance(result.args[0], MArray)
        assert result.args[0].value == "MYROUTINE"
        assert "%ut.EN" in result.description

    def test_en_ut_with_verbosity(self):
        """D EN^%ut("MYROUTINE",1) → args include verbosity."""
        mod = _make_module("MYROUTINE", _entry_function=_entry_stub)
        result = _resolve_entry_function(mod, 'D EN^%ut("MYROUTINE",1)', "MYROUTINE")

        assert result is not None
        assert result.func is _en_stub
        assert len(result.args) == 2
        assert result.args[0].value == "MYROUTINE"
        assert result.args[1].value == "1"

    def test_en_ut_with_verbosity_and_break(self):
        """D EN^%ut("MYROUTINE",1,1) → args include verbosity and break."""
        mod = _make_module("MYROUTINE", _entry_function=_entry_stub)
        result = _resolve_entry_function(mod, 'D EN^%ut("MYROUTINE",1,1)', "MYROUTINE")

        assert result is not None
        assert result.func is _en_stub
        assert len(result.args) == 3
        assert result.args[0].value == "MYROUTINE"
        assert result.args[1].value == "1"
        assert result.args[2].value == "1"

    def test_en_ut_ignores_target_module(self):
        """D EN^%ut resolves to %ut module, NOT the target module."""

        # Even if module has an EN function, we should use %ut's EN
        def target_en(*a, **kw):  # noqa: D401
            return None

        mod = _make_module("MYROUTINE", EN=target_en, _entry_function=_entry_stub)
        result = _resolve_entry_function(mod, 'D EN^%ut("MYROUTINE")', "MYROUTINE")

        assert result is not None
        assert result.func is _en_stub  # %ut.EN, not module.EN
        assert result.func is not target_en

    def test_en_ut_label_not_found_on_ut(self):
        """D NOLABEL^%ut("X") with unknown label on %ut → None."""
        mod = _make_module("TESTRTN", _entry_function=_entry_stub)
        result = _resolve_entry_function(mod, 'D NOLABEL^%ut("TESTRTN")', "TESTRTN")

        assert result is None

    def test_en_ut_no_ut_module_loaded(self):
        """D EN^%ut("X") when %ut not in sys.modules → None."""
        sys.modules.pop("_pct_ut", None)
        mod = _make_module("TESTRTN", _entry_function=_entry_stub)
        result = _resolve_entry_function(mod, 'D EN^%ut("TESTRTN")', "TESTRTN")

        assert result is None

    def test_en_ut_with_percent_routine(self):
        """D EN^%ut("%utt1") — percent-prefixed routine name."""
        mod = _make_module("_pct_utt1", _entry_function=_entry_stub)
        result = _resolve_entry_function(mod, 'D EN^%ut("%utt1")', "%utt1")

        assert result is not None
        assert result.args[0].value == "%utt1"

    def test_en_ut_with_spaces(self):
        """D EN^%ut( "MYROUTINE" ) — extra whitespace in invocation."""
        mod = _make_module("MYROUTINE")
        result = _resolve_entry_function(mod, 'D EN^%ut( "MYROUTINE" )', "MYROUTINE")

        assert result is not None
        assert result.args[0].value == "MYROUTINE"


# =============================================================================
# Edge cases
# =============================================================================


class TestResolveEdgeCases:
    """Edge cases and mixed scenarios."""

    def test_d_with_extra_spaces(self):
        """D   ^ROUTINE  (extra spaces) still resolves."""
        mod = _make_module("TESTRTN", _entry_function=_entry_stub)
        result = _resolve_entry_function(mod, "D   ^TESTRTN", "TESTRTN")

        assert result is not None
        assert result.func is _entry_stub

    def test_empty_invocation(self):
        """Empty invocation string → _entry_function fallback."""
        mod = _make_module("TESTRTN", _entry_function=_entry_stub)
        result = _resolve_entry_function(mod, "", "TESTRTN")

        assert result is not None
        assert result.func is _entry_stub

    def test_invocation_without_d_prefix(self):
        """Invocation without 'D ' prefix → _entry_function fallback."""
        mod = _make_module("TESTRTN", _entry_function=_entry_stub)
        result = _resolve_entry_function(mod, "^TESTRTN", "TESTRTN")

        assert result is not None
        assert result.func is _entry_stub

    def test_none_module_with_ut_pattern(self):
        """D EN^%ut("X") with module=None still resolves to %ut."""
        ut_mod = _make_module("_pct_ut", EN=_en_stub)
        sys.modules["_pct_ut"] = ut_mod
        try:
            result = _resolve_entry_function(None, 'D EN^%ut("TESTRTN")', "TESTRTN")
            assert result is not None
            assert result.func is _en_stub
        finally:
            sys.modules.pop("_pct_ut", None)
