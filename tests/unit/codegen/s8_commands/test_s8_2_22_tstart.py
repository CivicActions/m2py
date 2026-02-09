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

    def test_tstart_restart_vars_not_supported(self, generate_python):
        """TSTART (A,B) raises NotImplementedError (§8.2.22).

        T038: Restart variables require infrastructure for saving and restoring
        variable state on TRESTART, which is not yet implemented.
        """
        code = """\
TEST
 TS (A,B)
 Q
"""
        with pytest.raises(
            NotImplementedError, match="restart variables not implemented"
        ):
            generate_python(code)

    def test_tstart_restart_all_not_supported(self, generate_python):
        """TSTART * raises NotImplementedError (§8.2.22).

        T038: Restart all (*) requires infrastructure for saving and restoring
        all variable state on TRESTART, which is not yet implemented.
        """
        code = """\
TEST
 TS *
 Q
"""
        with pytest.raises(
            NotImplementedError, match="restart variables not implemented"
        ):
            generate_python(code)


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


# =============================================================================
# READ codegen (generate_python only to verify structure)
# =============================================================================
