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
