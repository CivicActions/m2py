"""Tests for SSVNs code generation (§7.1.3).

Reference: MUMPS 1995 ANSI Standard, Section 7.1.3

Spec 013 Phase 16 (FR-029): Implements ^$GLOBAL, ^$JOB, ^$LOCK, ^$ROUTINE via
database abstraction layer. YDB does not support SSVNs natively, so m2py provides
an in-memory implementation.
"""

import pytest


@pytest.mark.codegen
class TestSsvnsCodegen:
    """Codegen-level tests for structured system variables code generation (§7.1.3)."""

    def test_ssvn_global_exists(self, execute_mumps):
        """^$GLOBAL returns non-empty when global exists (§7.1.3).

        Spec 013 FR-029: Returns "1" for existing globals.
        """
        result = execute_mumps('TEST\n S ^MYTEST=1\n W ^$GLOBAL("MYTEST")\n Q\n')
        assert result.output == "1"
        assert result.success is True

    def test_ssvn_global_not_exists(self, execute_mumps):
        """^$GLOBAL returns empty when global does not exist (§7.1.3).

        Spec 013 FR-029: Returns "" for non-existent globals.
        """
        result = execute_mumps('TEST\n W ^$GLOBAL("NONEXISTENT")\n Q\n')
        assert result.output == ""
        assert result.success is True

    def test_ssvn_job_current(self, execute_mumps):
        """^$JOB returns non-empty for current process (§7.1.3).

        Spec 013 FR-029: Returns "1" when queried with $JOB (current PID).
        """
        result = execute_mumps("TEST\n W ^$JOB($J)\n Q\n")
        assert result.output == "1"
        assert result.success is True

    def test_ssvn_job_not_exists(self, execute_mumps):
        """^$JOB returns empty for non-existent process (§7.1.3).

        Spec 013 FR-029: Returns "" for non-existent PIDs.
        """
        result = execute_mumps("TEST\n W ^$JOB(99999999)\n Q\n")
        assert result.output == ""
        assert result.success is True

    def test_ssvn_lock_not_held(self, execute_mumps):
        """^$LOCK returns empty when lock not held (§7.1.3).

        Spec 013 FR-029: Returns "" when no lock exists.
        """
        result = execute_mumps('TEST\n W ^$LOCK("TESTLOCK")\n Q\n')
        assert result.output == ""
        assert result.success is True

    def test_ssvn_routine(self, execute_mumps):
        """^$ROUTINE returns empty (not implemented) (§7.1.3).

        Spec 013 FR-029: Routine metadata not available in transpiler context.
        """
        result = execute_mumps('TEST\n W ^$ROUTINE("MYROUTINE")\n Q\n')
        assert result.output == ""
        assert result.success is True

    def test_ssvn_abbreviation(self, execute_mumps):
        """SSVN names can be abbreviated (§7.1.3).

        Spec 013: ^$G is valid abbreviation for ^$GLOBAL.
        """
        result = execute_mumps('TEST\n S ^X=1\n W ^$G("X")\n Q\n')
        assert result.output == "1"
        assert result.success is True


@pytest.mark.codegen
class TestMwapiSsvnsCodegen:
    """Codegen tests for MWAPI SSVNs (LIM-003).

    MWAPI SSVNs (^$EVENT, ^$WINDOW, ^$DISPLAY) are from ANSI M X11.6 standard.
    They are parsed correctly but have zero VistA usage and no runtime support.
    Codegen should raise NotImplementedError.

    Reference: MUMPS 1995 ANSI Standard, Section 7.1.3
    Limitation: docs/limitations.md - LIM-003: MWAPI SSVNs
    """

    def test_lim003_ssvn_event_raises_error(self, generate_python):
        """^$EVENT should raise NotImplementedError (LIM-003).

        MWAPI SSVNs are not supported. Codegen must fail explicitly.
        """
        with pytest.raises(NotImplementedError, match="LIM-003"):
            generate_python('TEST W ^$EVENT("test") Q')

    def test_lim003_ssvn_window_raises_error(self, generate_python):
        """^$WINDOW should raise NotImplementedError (LIM-003).

        MWAPI SSVNs are not supported. Codegen must fail explicitly.
        """
        with pytest.raises(NotImplementedError, match="LIM-003"):
            generate_python('TEST W ^$WINDOW("test") Q')

    def test_lim003_ssvn_display_raises_error(self, generate_python):
        """^$DISPLAY should raise NotImplementedError (LIM-003).

        MWAPI SSVNs are not supported. Codegen must fail explicitly.
        """
        with pytest.raises(NotImplementedError, match="LIM-003"):
            generate_python('TEST W ^$DISPLAY("test") Q')


@pytest.mark.codegen
class TestLibrarySsvnCodegen:
    """Codegen tests for ^$LIBRARY SSVN (LIM-011).

    ^$LIBRARY provides routine library information but has zero VistA usage.
    Codegen should raise NotImplementedError.

    Reference: MUMPS 1995 ANSI Standard, Section 7.1.3
    Limitation: docs/limitations.md - LIM-011: ^$LIBRARY SSVN
    """

    def test_lim011_ssvn_library_raises_error(self, generate_python):
        """^$LIBRARY should raise NotImplementedError (LIM-011).

        ^$LIBRARY has zero VistA usage. Codegen must fail explicitly.
        """
        with pytest.raises(NotImplementedError, match="LIM-011"):
            generate_python('TEST W ^$LIBRARY("RTN") Q')
