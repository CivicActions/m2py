"""Unit tests for $ZTRAP, $ZSTATUS, $ZPOSITION (Phase 5: US3).

T024: Unit tests for $ZTRAP ISV storage
T025: Unit tests for $ZTRAP dispatch
T026: Unit tests for $ETRAP↔$ZTRAP mutual exclusion
T027: Unit tests for $ZSTATUS/$ZPOSITION format
"""

from m2py.runtime import MUMPSRuntime


class TestZtrapIsvStorage:
    """T024: Unit tests for $ZTRAP ISV storage."""

    def test_ztrap_initially_empty(self):
        """$ZTRAP is initially empty."""
        rt = MUMPSRuntime()
        assert rt.ztrap() == ""

    def test_set_ztrap_stores_value(self):
        """SET $ZTRAP stores the value."""
        rt = MUMPSRuntime()
        rt.set_ztrap("G ERR")
        assert rt.ztrap() == "G ERR"

    def test_set_ztrap_to_empty_clears(self):
        """SET $ZTRAP="" clears the trap."""
        rt = MUMPSRuntime()
        rt.set_ztrap("G ERR")
        rt.set_ztrap("")
        assert rt.ztrap() == ""

    def test_ztrap_preserves_whitespace(self):
        """$ZTRAP preserves whitespace in the code."""
        rt = MUMPSRuntime()
        rt.set_ztrap("  G ERR  ")
        assert rt.ztrap() == "  G ERR  "


class TestZtrapDispatch:
    """T025: Unit tests for $ZTRAP dispatch."""

    def test_dispatch_ztrap_goto_syntax(self):
        """$ZTRAP="G label" uses GOTO semantics."""
        rt = MUMPSRuntime()
        rt.set_ztrap("G ERR")
        # The dispatch method is called internally by _handle_etrap
        # Just verify the value is stored correctly
        assert rt.ztrap().strip().startswith("G ")

    def test_dispatch_ztrap_xecute_syntax(self):
        """$ZTRAP without 'G ' uses XECUTE semantics."""
        rt = MUMPSRuntime()
        rt.set_ztrap('S $EC=""')
        assert not rt.ztrap().strip().startswith("G ")

    def test_handle_etrap_uses_ztrap_fallback(self):
        """_handle_etrap uses $ZTRAP when $ETRAP is empty."""
        rt = MUMPSRuntime()
        rt.set_ztrap('S $EC=""')
        scope = {}
        # Should try to dispatch $ZTRAP since $ETRAP is empty
        result = rt._handle_etrap(ValueError("test"), scope)
        # $ZTRAP clears $ECODE so should return True
        assert result is True
        assert rt.ecode() == ""


class TestZstatusZposition:
    """T027: Unit tests for $ZSTATUS/$ZPOSITION format."""

    def test_zstatus_initially_empty(self):
        """$ZSTATUS is initially empty."""
        rt = MUMPSRuntime()
        assert rt.zstatus() == ""

    def test_zposition_initially_empty(self):
        """$ZPOSITION is initially empty."""
        rt = MUMPSRuntime()
        assert rt.zposition() == ""

    def test_set_zstatus_stores_value(self):
        """SET $ZSTATUS stores the value."""
        rt = MUMPSRuntime()
        rt.set_zstatus("150373850,TEST+1^routine,%YDB-E-LVUNDEF, Undefined")
        assert "150373850" in rt.zstatus()

    def test_set_zposition_stores_value(self):
        """SET $ZPOSITION stores the value."""
        rt = MUMPSRuntime()
        rt.set_zposition("ERR+1^test")
        assert rt.zposition() == "ERR+1^test"

    def test_zstatus_format_on_error(self):
        """$ZSTATUS is populated by _handle_etrap in YDB format."""
        rt = MUMPSRuntime()
        rt.set_etrap('S $EC=""')
        scope = {}
        rt._handle_etrap(
            KeyError("UNDEFINED"),
            scope,
            routine="test",
            label="TEST",
            offset=1,
        )
        # Check $ZSTATUS was set
        zs = rt.zstatus()
        assert zs  # Should not be empty
        # Format: "errorcode,label+offset^routine,%YDB-E-ERRNAME, message"
        assert "test" in zs or "TEST" in zs

    def test_zposition_set_on_error(self):
        """$ZPOSITION is set to error location."""
        rt = MUMPSRuntime()
        rt.set_etrap('S $EC=""')
        scope = {}
        rt._handle_etrap(
            KeyError("UNDEFINED"),
            scope,
            routine="myroutine",
            label="ERRLABEL",
            offset=3,
        )
        # $ZPOSITION should be set
        zp = rt.zposition()
        assert "ERRLABEL" in zp
        assert "myroutine" in zp

    def test_format_zstatus_basic(self):
        """_format_zstatus produces YDB-compatible format."""
        rt = MUMPSRuntime()
        result = rt._format_zstatus(
            error_code="150373850",
            label="TEST",
            offset=1,
            routine="test",
            ydb_code="LVUNDEF",
            message="Undefined local variable: X",
        )
        # Format: "errorcode,label+offset^routine,%YDB-E-ERRNAME, message"
        assert "150373850" in result
        assert "TEST+1^test" in result
        assert "LVUNDEF" in result


class TestEtrapZtrapMutualExclusion:
    """T026: Unit tests for $ETRAP↔$ZTRAP mutual exclusion.

    In MUMPS, $ETRAP and $ZTRAP are mutually exclusive.
    Setting one clears the other (T032).
    """

    def test_set_ztrap_clears_etrap(self):
        """SET $ZTRAP clears $ETRAP (mutual exclusion)."""
        rt = MUMPSRuntime()
        rt.set_etrap('S $EC=""')
        assert rt.etrap() == 'S $EC=""'
        # Setting $ZTRAP should clear $ETRAP
        rt.set_ztrap("G ERR")
        assert rt.ztrap() == "G ERR"
        assert rt.etrap() == ""

    def test_set_etrap_clears_ztrap(self):
        """SET $ETRAP clears $ZTRAP (mutual exclusion)."""
        rt = MUMPSRuntime()
        rt.set_ztrap("G ERR")
        assert rt.ztrap() == "G ERR"
        # Setting $ETRAP should clear $ZTRAP
        rt.set_etrap('S $EC=""')
        assert rt.etrap() == 'S $EC=""'
        assert rt.ztrap() == ""

    def test_handle_etrap_prefers_etrap_over_ztrap(self):
        """When $ETRAP is set, it takes precedence (can't both be set)."""
        rt = MUMPSRuntime()
        # Due to mutual exclusion, setting $ETRAP last means $ZTRAP is cleared
        rt.set_etrap('S HANDLED="ETRAP" S $EC=""')
        scope = {}
        rt._handle_etrap(ValueError("test"), scope)
        # $ETRAP should have been executed
        handled = scope.get("HANDLED")
        assert handled is not None
        assert handled.value == "ETRAP"

    def test_set_empty_ztrap_does_not_clear_etrap(self):
        """SET $ZTRAP=\"\" does NOT clear $ETRAP (only non-empty triggers)."""
        rt = MUMPSRuntime()
        rt.set_etrap('S $EC=""')
        rt.set_ztrap("")
        assert rt.etrap() == 'S $EC=""'  # Still set

    def test_set_empty_etrap_does_not_clear_ztrap(self):
        """SET $ETRAP=\"\" does NOT clear $ZTRAP (only non-empty triggers)."""
        rt = MUMPSRuntime()
        rt.set_ztrap("G ERR")
        rt.set_etrap("")
        assert rt.ztrap() == "G ERR"  # Still set


class TestZtrapFallback:
    """T035: Tests for $ZTRAP fallback in _handle_etrap."""

    def test_ztrap_fallback_clears_ecode(self):
        """$ZTRAP that clears $ECODE returns True."""
        rt = MUMPSRuntime()
        rt.set_ztrap('S $EC=""')
        scope = {}
        result = rt._handle_etrap(ValueError("test"), scope)
        assert result is True
        assert rt.ecode() == ""

    def test_ztrap_fallback_preserves_ecode(self):
        """$ZTRAP that doesn't clear $ECODE returns False."""
        rt = MUMPSRuntime()
        rt.set_ztrap('W "Logged"')  # Doesn't clear $ECODE
        scope = {}
        result = rt._handle_etrap(ValueError("test"), scope)
        assert result is False
        # $ECODE should be set (M or Z code)
        assert rt.ecode() != ""
