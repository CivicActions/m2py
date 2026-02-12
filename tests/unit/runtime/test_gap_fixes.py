"""Tests for Phase 3 gap fixes — verifying all audit findings are resolved.

Covers:
- T020: $ETRAP level-aware unwind ($ECODE not re-accumulated during unwind)
- T022: $ESTACK read via expressions (runtime estack() method)
- T023: Configurable max error nesting depth
- T031: _dispatch_ztrap regex GOTO detection
- T033: NEW $ZTRAP/$ZSTATUS/$ZPOSITION support
- T068: m_zdate 64-char format limit enforcement
- T086: ^$JOB liveness check with os.kill
- T087: ^$ROUTINE with importlib
- T088: ^$SYSTEM configurable (delegates to runtime)
- T095: $ZRO getter/setter
"""

import os

import pytest

from m2py.runtime import MUMPSRuntime
from m2py.runtime.globals import InMemoryGlobalStorage


@pytest.mark.codegen
class TestEstackRead:
    """T022: $ESTACK read — runtime estack() method and codegen wiring."""

    def test_estack_zero_at_init(self):
        """$ESTACK is 0 at initialization (no frames, set_level=0)."""
        rt = MUMPSRuntime()
        assert rt.estack() == 0

    def test_estack_increments_with_stack(self):
        """$ESTACK increases as stack frames are pushed."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="TEST", label="A")
        assert rt.estack() == 1
        rt.push_stack_frame("DO", routine="TEST", label="B")
        assert rt.estack() == 2

    def test_estack_resets_on_new_estack(self):
        """NEW $ESTACK resets estack to 0 relative to current level."""
        rt = MUMPSRuntime()
        rt.push_stack_frame("DO", routine="TEST", label="A")
        rt.push_stack_frame("DO", routine="TEST", label="B")
        assert rt.estack() == 2
        # Simulate NEW $ESTACK
        rt._etrap_set_level = len(rt._stack_frames)
        assert rt.estack() == 0
        # Push another frame
        rt.push_stack_frame("DO", routine="TEST", label="C")
        assert rt.estack() == 1

    def test_estack_codegen(self):
        """$ESTACK generates str(_rt.estack()) in codegen."""
        from m2py.codegen import generate_python

        code = "TEST W $ES,! Q\n"
        result = generate_python(code)
        assert "_rt.estack()" in result


@pytest.mark.codegen
class TestConfigurableMaxNesting:
    """T023: Configurable max error nesting depth."""

    def test_default_max_nesting_is_20(self):
        """Default max error nesting is 20."""
        rt = MUMPSRuntime()
        assert rt._max_error_nesting == 20

    def test_custom_max_nesting(self):
        """max_error_nesting constructor parameter sets the limit."""
        rt = MUMPSRuntime(max_error_nesting=5)
        assert rt._max_error_nesting == 5

    def test_custom_max_nesting_enforced(self):
        """Excessive nesting raises RuntimeError at custom limit."""
        rt = MUMPSRuntime(max_error_nesting=2)
        rt._error_nesting_depth = 3
        with pytest.raises(RuntimeError, match="Maximum error handler nesting depth"):
            rt._handle_etrap(Exception("test"), {}, routine="TEST", label="A", offset=0)


@pytest.mark.codegen
class TestDispatchZtrapRegex:
    """T031: _dispatch_ztrap regex GOTO detection."""

    def test_goto_uppercase_prefix(self):
        """'G ERR' is detected as GOTO pattern."""
        rt = MUMPSRuntime()
        assert rt._ZTRAP_GOTO_RE.match("G ERR") is not None

    def test_goto_full_word(self):
        """'GOTO ERR' is detected as GOTO pattern."""
        rt = MUMPSRuntime()
        assert rt._ZTRAP_GOTO_RE.match("GOTO ERR") is not None

    def test_goto_case_insensitive(self):
        """'goto err' is detected as GOTO pattern."""
        rt = MUMPSRuntime()
        assert rt._ZTRAP_GOTO_RE.match("goto err") is not None

    def test_goto_with_routine(self):
        """'G ERR^RTN' is detected as GOTO pattern."""
        rt = MUMPSRuntime()
        assert rt._ZTRAP_GOTO_RE.match("G ERR^RTN") is not None

    def test_bare_label_reference(self):
        """'ERR' (bare label) is detected as implicit GOTO."""
        rt = MUMPSRuntime()
        assert rt._ZTRAP_LABEL_RE.match("ERR") is not None

    def test_bare_label_with_routine(self):
        """'ERR^RTN' (bare label+routine) is detected as implicit GOTO."""
        rt = MUMPSRuntime()
        assert rt._ZTRAP_LABEL_RE.match("ERR^RTN") is not None

    def test_bare_label_with_offset(self):
        """'ERR+2^RTN' (label+offset+routine) is detected as implicit GOTO."""
        rt = MUMPSRuntime()
        assert rt._ZTRAP_LABEL_RE.match("ERR+2^RTN") is not None

    def test_xecute_not_detected_as_goto(self):
        """'W \"error\"' is NOT detected as GOTO."""
        rt = MUMPSRuntime()
        assert rt._ZTRAP_GOTO_RE.match('W "error"') is None
        assert rt._ZTRAP_LABEL_RE.match('W "error"') is None

    def test_xecute_set_not_detected_as_goto(self):
        """'S $EC=\"\"' is NOT detected as GOTO."""
        rt = MUMPSRuntime()
        assert rt._ZTRAP_GOTO_RE.match('S $EC=""') is None
        assert rt._ZTRAP_LABEL_RE.match('S $EC=""') is None

    def test_percent_label_detected(self):
        """%ERR (percent label) is detected as implicit GOTO."""
        rt = MUMPSRuntime()
        assert rt._ZTRAP_LABEL_RE.match("%ERR") is not None


@pytest.mark.codegen
class TestNewZtrapZstatusZposition:
    """T033: NEW $ZTRAP/$ZSTATUS/$ZPOSITION support in codegen."""

    def test_new_ztrap_codegen(self):
        """NEW $ZTRAP generates new_special_var('ztrap', ...) code."""
        from m2py.codegen import generate_python

        code = 'TEST() N $ZTRAP S $ZT="G ERR" Q\n'
        result = generate_python(code)
        assert "new_special_var('ztrap'" in result

    def test_new_zstatus_codegen(self):
        """NEW $ZSTATUS generates new_special_var('zstatus', ...) code."""
        from m2py.codegen import generate_python

        code = "TEST() N $ZSTATUS Q\n"
        result = generate_python(code)
        assert "new_special_var('zstatus'" in result

    def test_new_zposition_codegen(self):
        """NEW $ZPOSITION generates new_special_var('zposition', ...) code."""
        from m2py.codegen import generate_python

        code = "TEST() N $ZPOSITION Q\n"
        result = generate_python(code)
        assert "new_special_var('zposition'" in result

    def test_new_ztrap_runtime_save_restore(self):
        """NEW $ZTRAP saves/restores via scope manager."""
        from m2py.runtime.helpers import NewScopeManager

        rt = MUMPSRuntime()
        rt.set_ztrap("G ERR")
        scope = {}
        with NewScopeManager(scope) as mgr:
            mgr.new_special_var("ztrap", rt.ztrap(), rt.set_ztrap)
            # NEW initializes to empty
            assert rt.ztrap() == ""
            # Set a new value inside the scope
            rt.set_ztrap("G NEW_ERR")
            assert rt.ztrap() == "G NEW_ERR"
        # After scope exit, $ZTRAP should be restored to original
        assert rt.ztrap() == "G ERR"

    def test_new_zstatus_runtime_save_restore(self):
        """NEW $ZSTATUS saves/restores via scope manager."""
        from m2py.runtime.helpers import NewScopeManager

        rt = MUMPSRuntime()
        rt.set_zstatus("original status")
        scope = {}
        with NewScopeManager(scope) as mgr:
            mgr.new_special_var("zstatus", rt.zstatus(), rt.set_zstatus)
            rt.set_zstatus("new status")
            assert rt.zstatus() == "new status"
        assert rt.zstatus() == "original status"


@pytest.mark.codegen
class TestEtrapUnwindNoReaccumulate:
    """T020: $ETRAP does not re-accumulate $ECODE during unwind."""

    def test_ecode_not_duplicated_on_refire(self):
        """$ECODE keeps first error only during refire at each level."""
        rt = MUMPSRuntime()
        # Set up $ETRAP that doesn't clear $ECODE
        rt.set_etrap('W "trap"')
        rt.push_stack_frame("DO", routine="TEST", label="A")

        # First error — should set $ECODE
        from decimal import DivisionByZero

        exc = DivisionByZero("Division by zero")
        rt._handle_etrap(exc, {}, routine="TEST", label="A", offset=1)
        ecode_first = rt._ecode
        assert ecode_first == ",M9,"

        # Second refire — $ECODE should NOT change (was_empty is False)
        rt._in_error_handler = False  # Reset guard for re-entry
        rt._handle_etrap(exc, {}, routine="TEST", label="A", offset=1)
        assert rt._ecode == ecode_first  # No re-accumulation


@pytest.mark.codegen
class TestZdateFormatLimit:
    """T068: m_zdate 64-char format string limit enforcement."""

    def test_valid_format_accepted(self):
        """Format strings ≤64 chars are accepted."""
        from m2py.runtime.helpers import m_zdate

        result = m_zdate("66337", "MM/DD/YYYY")
        assert result == "08/16/2022"

    def test_exact_64_chars_accepted(self):
        """Format string of exactly 64 chars is accepted."""
        from m2py.runtime.helpers import m_zdate

        fmt = "M" * 64  # 64 chars
        # Should not raise
        m_zdate("66337", fmt)

    def test_65_chars_rejected(self):
        """Format string of 65 chars raises error."""
        from m2py.runtime.helpers import m_zdate
        from m2py.runtime.exceptions import MRuntimeError

        fmt = "M" * 65
        with pytest.raises(MRuntimeError, match="exceeds 64 characters"):
            m_zdate("66337", fmt)


@pytest.mark.codegen
class TestSsvnJobLiveness:
    """T086: ^$JOB liveness check with os.kill."""

    def test_current_pid_returns_one(self):
        """^$JOB($J) returns '1' for current process."""
        g = InMemoryGlobalStorage()
        assert g.ssvn_job(str(os.getpid())) == "1"

    def test_nonexistent_pid_returns_empty(self):
        """^$JOB(99999999) returns '' for nonexistent process."""
        g = InMemoryGlobalStorage()
        # Use a very high PID that's unlikely to exist
        result = g.ssvn_job("99999999")
        assert result == ""

    def test_pid_1_exists(self):
        """^$JOB(1) returns '1' — init process always exists."""
        g = InMemoryGlobalStorage()
        result = g.ssvn_job("1")
        # PID 1 exists on Linux (might get PermissionError but still returns "1")
        assert result == "1"

    def test_negative_pid_returns_empty(self):
        """^$JOB(-1) returns '' for negative PID."""
        g = InMemoryGlobalStorage()
        assert g.ssvn_job("-1") == ""

    def test_zero_pid_returns_empty(self):
        """^$JOB(0) returns '' for PID 0."""
        g = InMemoryGlobalStorage()
        assert g.ssvn_job("0") == ""

    def test_invalid_pid_returns_empty(self):
        """^$JOB(abc) returns '' for non-numeric PID."""
        g = InMemoryGlobalStorage()
        assert g.ssvn_job("abc") == ""


@pytest.mark.codegen
class TestSsvnRoutine:
    """T087: ^$ROUTINE with importlib/file check."""

    def test_nonexistent_routine_returns_empty(self):
        """^$ROUTINE(nonexistent) returns ''."""
        g = InMemoryGlobalStorage()
        assert g.ssvn_routine("NONEXISTENT_ROUTINE_XYZ") == ""

    def test_empty_routine_returns_empty(self):
        """^$ROUTINE('') returns ''."""
        g = InMemoryGlobalStorage()
        assert g.ssvn_routine("") == ""


@pytest.mark.codegen
class TestZroSetterGetter:
    """T095: $ZRO getter/setter."""

    def test_default_zro_is_dot(self):
        """Default $ZRO is '.'."""
        rt = MUMPSRuntime()
        assert rt.zro() == "."

    def test_set_zro(self):
        """set_zro() changes $ZRO value."""
        rt = MUMPSRuntime()
        rt.set_zro("/usr/local/routines")
        assert rt.zro() == "/usr/local/routines"

    def test_set_zro_converts_to_string(self):
        """set_zro() converts value to string."""
        rt = MUMPSRuntime()
        rt.set_zro(42)
        assert rt.zro() == "42"


@pytest.mark.codegen
class TestSsvnSystemConfigurable:
    """T088: ^$SYSTEM SSVN uses runtime system() method."""

    def test_ssvn_system_codegen(self):
        """^$SYSTEM codegen generates _rt.system() call."""
        from m2py.codegen import generate_python

        code = "TEST W ^$SYSTEM,! Q\n"
        result = generate_python(code)
        assert "_rt.system()" in result

    def test_runtime_system_value(self):
        """_rt.system() returns '47,M2PY' by default."""
        rt = MUMPSRuntime()
        assert rt.system() == "47,M2PY"
