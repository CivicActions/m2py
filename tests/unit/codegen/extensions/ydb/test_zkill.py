"""Tests for ZKILL/ZWITHDRAW command code generation (YDB extension).

Reference: YottaDB Z-Commands
"""

import pytest


@pytest.mark.codegen
@pytest.mark.ydb
class TestZkillCodegen:
    """Codegen-level tests for ZKILL/ZWITHDRAW command (YDB)."""

    def test_zkill_generates_node_delete(self, generate_python):
        """ZKILL generates node-only delete (keeps descendants)."""
        code = generate_python("TEST S ^A=1 ZK ^A Q")
        assert "kill_node" in code
        assert "'A'" in code

    def test_zwithdraw_generates_node_delete(self, generate_python):
        """ZWITHDRAW generates node-only delete (keeps descendants)."""
        code = generate_python("TEST S ^A=1 ZWI ^A Q")
        assert "kill_node" in code
        assert "'A'" in code

    def test_zkill_global_preserves_descendants(self, execute_mumps):
        """ZKILL on global removes value but keeps descendants."""
        result = execute_mumps("TEST S ^A=1,^A(1)=2,^A(2)=3 ZK ^A W $D(^A) K ^A Q")
        assert result.success
        # $DATA returns 10 when node has descendants but no value
        assert result.output.strip() == "10"

    def test_zkill_local_preserves_descendants(self, execute_mumps):
        """ZKILL on local removes value but keeps descendants."""
        result = execute_mumps("TEST S X=1,X(1)=2 ZK X W $D(X) Q")
        assert result.success
        assert result.output.strip() == "10"

    def test_zkill_subscripted_node(self, execute_mumps):
        """ZKILL on subscripted node removes only that value."""
        result = execute_mumps(
            "TEST S ^A(1)=1,^A(1,1)=2 ZK ^A(1) W $D(^A(1)),$G(^A(1,1)) K ^A Q"
        )
        assert result.success
        # $DATA=10 (has children, no value), child value=2
        assert result.output.strip() == "102"

    def test_zkill_abbreviation(self, execute_mumps):
        """ZK abbreviation works for ZKILL."""
        result = execute_mumps("TEST S ^A=1,^A(1)=2 ZK ^A W $D(^A) K ^A Q")
        assert result.success
        assert result.output.strip() == "10"
