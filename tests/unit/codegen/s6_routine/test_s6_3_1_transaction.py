"""Tests for Transaction Processing code generation (§6.3.1).

Reference: MUMPS 1995 ANSI Standard, Section 6.3.1
See also: §8.2.19 (TCOMMIT), §8.2.21 (TROLLBACK), §8.2.22 (TSTART)
"""

import pytest


@pytest.mark.codegen
class TestTransactionNestingCodegen:
    """Codegen tests for transaction nesting behavior.

    Generated Python must correctly implement nested transactions
    with $TLEVEL tracking.
    Reference: §6.3.1, §8.2.19, §8.2.21, §8.2.22, FR-015
    """

    def test_tlevel_increments_on_tstart(self, execute_mumps):
        """TSTART increments $TLEVEL (§8.2.22, FR-015).

        ; $TLEVEL=0
        TSTART
        ; $TLEVEL should be 1
        """
        result = execute_mumps('TEST\n W $TL," "\n TS\n W $TL\n TC\n Q')
        assert result.output == "0 1"

    def test_nested_tstart_increments_tlevel(self, execute_mumps):
        """Nested TSTART increments $TLEVEL (§8.2.22, FR-015).

        TSTART    ; $TLEVEL=1
        TSTART    ; $TLEVEL should be 2
        """
        result = execute_mumps('TEST\n TS\n W $TL," "\n TS\n W $TL\n TC\n TC\n Q')
        assert result.output == "1 2"

    def test_tcommit_decrements_tlevel(self, execute_mumps):
        """TCOMMIT decrements $TLEVEL (§8.2.19, FR-015).

        TSTART    ; $TLEVEL=1
        TSTART    ; $TLEVEL=2
        TCOMMIT   ; $TLEVEL should be 1
        """
        result = execute_mumps('TEST\n TS\n TS\n W $TL," "\n TC\n W $TL\n TC\n Q')
        assert result.output == "2 1"

    @pytest.mark.stub
    @pytest.mark.xfail(reason="TROLLBACK:n syntax not yet implemented in codegen")
    def test_trollback_to_specific_level(self, execute_mumps):
        """TROLLBACK:n rolls back to level n (§8.2.21, FR-015).

        TSTART    ; $TLEVEL=1
        TSTART    ; $TLEVEL=2
        TSTART    ; $TLEVEL=3
        TROLLBACK:1  ; Should rollback to $TLEVEL=1
        """
        result = execute_mumps(
            'TEST\n TS\n TS\n TS\n W $TL," "\n TRO 1\n W $TL\n TC\n Q'
        )
        assert result.output == "3 1"

    def test_trollback_full(self, execute_mumps):
        """Argumentless TROLLBACK rolls back all levels (§8.2.21, FR-015).

        TSTART    ; $TLEVEL=1
        TSTART    ; $TLEVEL=2
        TROLLBACK ; $TLEVEL should be 0
        """
        result = execute_mumps('TEST\n TS\n TS\n W $TL," "\n TRO\n W $TL\n Q')
        assert result.output == "2 0"

    def test_trollback_restores_global_state(self, execute_mumps):
        """TROLLBACK restores global state before transaction (§8.2.21, FR-015).

        Changes made within a transaction are discarded on rollback.
        """
        result = execute_mumps(
            'TEST\n S ^X=5\n TS\n S ^X=99\n W ^X," "\n TRO\n W ^X\n Q'
        )
        assert result.output == "99 5"

    @pytest.mark.stub
    @pytest.mark.xfail(reason="$TRESTART not yet implemented")
    def test_trestart_tracking(self, execute_mumps):
        """$TRESTART counts restart attempts (§7.1.7, FR-015)."""
        pytest.fail("Stub - implement test")
