"""Tests for LOCK command code generation (§8.2.12).

Spec 013 Phase 9: LOCK codegen via database abstraction layer.

Reference: MUMPS 1995 ANSI Standard, Section 8.2.12
"""

import pytest


@pytest.mark.codegen
class TestLockCommandCodegen:
    """Codegen-level tests for LOCK command code generation (§8.2.12)."""

    def test_lock_to_lock_primitive(self, execute_mumps):
        """LOCK generates lock acquisition (§8.2.12).

        Spec 013 Phase 9: Basic LOCK generates _rt.globals.lock() call.
        Note: Without +, LOCK first releases all then acquires.
        """
        result = execute_mumps("TEST\n IF 1\n L ^DATA\n W $T\n Q")
        # LOCK without timeout preserves $TEST (was 1 from IF 1)
        assert result.output == "1"

    def test_lock_increment(self, execute_mumps):
        """LOCK + generates incremental lock (§8.2.12).

        Spec 013 Phase 9: LOCK + acquires without releasing existing locks.
        """
        result = execute_mumps('TEST\n L +^A\n L +^B\n W "OK"\n Q')
        assert result.output == "OK"

    def test_lock_decrement(self, execute_mumps):
        """LOCK - generates lock release (§8.2.12).

        Spec 013 Phase 9: LOCK - releases specific lock.
        """
        result = execute_mumps('TEST\n L +^DATA\n L -^DATA\n W "OK"\n Q')
        assert result.output == "OK"

    def test_lock_argumentless_releases_all(self, execute_mumps):
        """Argumentless LOCK releases all locks (§8.2.12).

        Spec 013 Phase 9: LOCK with no args calls unlock_all().
        Note: Requires two spaces after L per MUMPS syntax.
        """
        result = execute_mumps('TEST\n L +^A\n L +^B\n L  \n W "OK"\n Q')
        assert result.output == "OK"

    def test_lock_with_subscripts(self, execute_mumps):
        """LOCK with subscripts generates correct tuple (§8.2.12).

        Spec 013 Phase 9: Subscripted lock targets are passed as tuple.
        """
        result = execute_mumps("TEST\n L +^DATA(1,2,3):1\n W $T\n Q")
        assert result.output == "1"

    def test_lock_parenthesized_list(self, execute_mumps):
        """LOCK (^A,^B):timeout locks multiple simultaneously (§8.2.12).

        Spec 013 Phase 9: Parenthesized list with shared timeout.
        """
        result = execute_mumps("TEST\n L (^A,^B):2\n W $T\n Q")
        assert result.output == "1"

    def test_lock_timeout_expression(self, execute_mumps):
        """LOCK timeout can be a variable expression (§8.2.12).

        Spec 013 Phase 9: Timeout expression evaluated at runtime.
        """
        result = execute_mumps("TEST\n S T=1\n L +^DATA:T\n W $T\n Q")
        assert result.output == "1"
