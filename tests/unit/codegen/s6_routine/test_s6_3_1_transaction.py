"""Tests for Transaction Processing code generation (§6.3.1).

Reference: MUMPS 1995 ANSI Standard, Section 6.3.1
See also: §8.2.19 (TCOMMIT), §8.2.21 (TROLLBACK), §8.2.22 (TSTART)
"""

import pytest

from m2py.codegen import generate_python


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

    def test_lim016_trollback_n_raises_error(self):
        """TROLLBACK:n raises NotImplementedError (LIM-016).

        TROLLBACK with level argument has zero VistA usage.
        Reference: docs/limitations.md - LIM-016
        """
        with pytest.raises(NotImplementedError, match="LIM-016"):
            generate_python("TEST\n TS\n TRO 1\n Q")

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

    def test_trestart_raises_error(self):
        """$TRESTART raises NotImplementedError (not yet implemented).

        $TRESTART is a special variable that tracks transaction restart count.
        Per LIM-016, this has zero VistA usage.
        """
        with pytest.raises(NotImplementedError, match="TRESTART"):
            generate_python("TEST W $TRESTART Q")
