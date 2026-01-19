"""Tests for LOCK command code generation (§8.2.12).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.12

Spec 013 Phase 9: LOCK command codegen via database abstraction.
"""

import pytest


@pytest.mark.codegen
class TestLockCommandCodegen:
    """Codegen-level tests for LOCK command code generation (§8.2.12)."""

    def test_lock_to_lock_primitive(self, execute_mumps):
        """LOCK generates lock acquisition (§8.2.12).

        Spec 013 FR-019: LOCK command uses database abstraction.
        L +^GLOBAL acquires a lock on the global.
        """
        result = execute_mumps('TEST\n L +^A\n W "locked"\n Q')
        assert result.output == "locked"

    def test_lock_increment(self, execute_mumps):
        """LOCK + generates incremental lock (§8.2.12).

        Spec 013 FR-019: L +^GLOBAL increments lock count.
        Multiple increments require equal decrements to release.
        """
        result = execute_mumps('TEST\n L +^A\n L +^A\n L -^A\n L -^A\n W "done"\n Q')
        assert result.output == "done"

    def test_lock_decrement(self, execute_mumps):
        """LOCK - generates lock release (§8.2.12).

        Spec 013 FR-019: L -^GLOBAL decrements lock count.
        """
        result = execute_mumps('TEST\n L +^A\n L -^A\n W "unlocked"\n Q')
        assert result.output == "unlocked"

    def test_lock_with_subscripts(self, execute_mumps):
        """LOCK supports subscripted names (§8.2.12).

        Spec 013 FR-019: L +^GLOBAL(sub1,sub2) locks subscripted node.
        """
        result = execute_mumps(
            'TEST\n L +^A(1,2)\n W "locked subscript"\n L -^A(1,2)\n Q'
        )
        assert result.output == "locked subscript"

    def test_argumentless_lock_releases_all(self, execute_mumps):
        """L without arguments releases all locks (§8.2.12).

        Spec 013 FR-019: Argumentless LOCK releases all held locks.
        """
        result = execute_mumps('TEST\n L +^A\n L +^B\n L\n W "released"\n Q')
        assert result.output == "released"

    def test_exclusive_lock_releases_first(self, execute_mumps):
        """L ^A (no +) releases all then locks ^A (§8.2.12).

        Exclusive lock syntax releases all previous locks before
        acquiring the new one.
        """
        result = execute_mumps('TEST\n L +^X\n L ^A\n W "exclusive"\n Q')
        assert result.output == "exclusive"

    def test_lock_parenthesized_list(self, execute_mumps):
        """L (^A,^B) locks multiple simultaneously (§8.2.12).

        Parenthesized list acquires all locks atomically.
        """
        result = execute_mumps('TEST\n L (^A,^B)\n W "both locked"\n L\n Q')
        assert result.output == "both locked"
