"""Tests for TSTART command code generation (§8.2.22).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.22
"""

import pytest


@pytest.mark.codegen
class TestTstartCommandCodegen:
    """Codegen-level tests for TSTART command code generation (§8.2.22)."""

    def test_tstart_to_begin(self, generate_python):
        """TSTART generates transaction begin (§8.2.22)."""
        code = """\
TEST
 TSTART
 Q
"""
        result = generate_python(code)
        assert "_rt.globals.transaction_start()" in result

    def test_tstart_abbreviated(self, generate_python):
        """TS (abbreviated) generates transaction begin (§8.2.22)."""
        code = """\
TEST
 TS
 Q
"""
        result = generate_python(code)
        assert "_rt.globals.transaction_start()" in result

    def test_tstart_serial(self, generate_python):
        """TSTART ():SERIAL generates transaction begin (§8.2.22).

        Note: SERIAL parameter is parsed but transaction start is generated.
        Full serialization semantics deferred per spec 013.
        """
        code = """\
TEST
 TS ():SERIAL
 Q
"""
        result = generate_python(code)
        # SERIAL is parsed but basic transaction_start is generated
        assert "_rt.globals.transaction_start()" in result

    def test_tstart_restart_vars_generates_snapshot(self, generate_python):
        """TSTART (A,B) generates snapshot_locals() call (§8.2.22).

        Spec 021 Phase 8: Restart variables snapshot locals for potential
        TRESTART support.
        """
        code = """\
TEST
 TS (A,B)
 Q
"""
        result = generate_python(code)
        assert "_rt.globals.transaction_start()" in result
        assert "_rt.snapshot_locals(_scope, var_names=['A', 'B'])" in result

    def test_tstart_restart_all_generates_snapshot(self, generate_python):
        """TSTART * generates snapshot_locals(all_vars=True) call (§8.2.22).

        Spec 021 Phase 8: TSTART * snapshots all local variables.
        """
        code = """\
TEST
 TS *
 Q
"""
        result = generate_python(code)
        assert "_rt.globals.transaction_start()" in result
        assert "_rt.snapshot_locals(_scope, all_vars=True)" in result


@pytest.mark.codegen
class TestTransactionCodegen:
    """Tests for TSTART/TCOMMIT/TROLLBACK codegen."""

    def test_tstart_tcommit(self, execute_mumps):
        """Basic TS ... TC transaction."""
        result = execute_mumps("TEST\n\tTS\n\tS ^X=1\n\tTC\n\tW ^X\n\tQ\n")
        assert result.output == "1"

    def test_trollback(self, execute_mumps):
        """TROLLBACK undoes transaction changes."""
        result = execute_mumps("TEST\n\tS ^X=0\n\tTS\n\tS ^X=1\n\tTRO\n\tW ^X\n\tQ\n")
        assert result.output == "0"

    def test_tstart_with_restart_vars(self, execute_mumps):
        """TS (X,Y) — transactional restart variables (coverage: analyzer L1895-1980)."""
        result = execute_mumps(
            "TEST\n S X=1,Y=2\n TS (X,Y)\n S X=99\n TC\n W X,!\n Q\n"
        )
        assert "99" in result.output


# =============================================================================
# READ codegen (generate_python only to verify structure)
# =============================================================================
