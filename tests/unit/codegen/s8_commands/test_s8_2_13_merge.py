"""Tests for MERGE command code generation (§8.2.13).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.13
"""

import pytest


@pytest.mark.codegen
class TestMergeCommandCodegen:
    """Codegen-level tests for MERGE command code generation (§8.2.13)."""

    def test_merge_local_to_local(self, generate_python):
        """MERGE generates merge_from call for local-to-local (§8.2.13)."""
        code = generate_python("TEST M B=A Q")
        # Verify merge_from is called
        assert "merge_from" in code
        # Verify source is fetched from scope
        assert "_scope.get('A', MArray())" in code

    def test_merge_global_to_local(self, generate_python):
        """MERGE generates get_tree for global-to-local (§8.2.13)."""
        code = generate_python("TEST M L=^G Q")
        # Verify get_tree is called on globals
        assert "get_tree" in code
        assert 'get_tree("G"' in code
        # Verify merge_from is called
        assert "merge_from" in code

    def test_merge_copies_values(self, execute_mumps):
        """MERGE copies source values to destination (§8.2.13)."""
        result = execute_mumps("TEST S A(1)=1,A(2)=2,A(3)=3 M B=A W B(1),B(2),B(3),! Q")
        assert result.success
        assert result.output.rstrip() == "123"

    def test_merge_copies_nested_values(self, execute_mumps):
        """MERGE copies nested subscript values (§8.2.13)."""
        result = execute_mumps("TEST S A(1,1)=11,A(1,2)=12 M B=A W B(1,1),B(1,2),! Q")
        assert result.success
        assert result.output.rstrip() == "1112"

    def test_merge_copies_root_value(self, execute_mumps):
        """MERGE copies source root value if present (§8.2.13)."""
        result = execute_mumps('TEST S A="root",A(1)=1 M B=A W $G(B),B(1),! Q')
        assert result.success
        assert result.output.rstrip() == "root1"

    def test_merge_preserves_destination(self, execute_mumps):
        """MERGE does not delete existing destination nodes (§8.2.13)."""
        result = execute_mumps(
            'TEST S B(5)="old" S A(1)=1 M B=A W B(1),$G(B(5),"none"),! Q'
        )
        assert result.success
        assert result.output.rstrip() == "1old"

    def test_merge_global_to_local_copies(self, execute_mumps):
        """MERGE from global to local copies tree (§8.2.13)."""
        result = execute_mumps("TEST S ^G(1)=1,^G(2)=2 M L=^G W L(1),L(2),! Q")
        assert result.success
        assert result.output.rstrip() == "12"

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE to global destination")
    def test_merge_local_to_global(self, generate_python):
        """MERGE to global destination generates global set operations (§8.2.13)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: MERGE global to global")
    def test_merge_global_to_global(self, generate_python):
        """MERGE from global to global generates copy operations (§8.2.13)."""
        pytest.fail("Stub - implement test")
