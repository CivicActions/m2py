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

    def test_merge_local_to_global(self, execute_mumps):
        """MERGE local→global copies tree to global destination (§8.2.13)."""
        result = execute_mumps("TEST S A(1)=1,A(2)=2 M ^G=A W ^G(1),^G(2),! Q")
        assert result.success
        assert result.output.rstrip() == "12"

    def test_merge_global_to_global(self, execute_mumps):
        """MERGE global→global copies tree between globals (§8.2.13)."""
        result = execute_mumps("TEST S ^G1(1)=1,^G1(2)=2 M ^G2=^G1 W ^G2(1),^G2(2),! Q")
        assert result.success
        assert result.output.rstrip() == "12"

    def test_merge_local_to_global_nested(self, execute_mumps):
        """MERGE local→global copies nested structures (§8.2.13)."""
        result = execute_mumps(
            'TEST S A="root",A(1)=1,A(1,2)=12 M ^G=A W $G(^G),^G(1),^G(1,2),! Q'
        )
        assert result.success
        assert result.output.rstrip() == "root112"

    def test_merge_local_to_global_preserves_existing(self, execute_mumps):
        """MERGE local→global preserves existing destination nodes (§8.2.13)."""
        result = execute_mumps(
            'TEST S ^G(5)="old" S A(1)=1 M ^G=A W ^G(1),$G(^G(5),"none"),! Q'
        )
        assert result.success
        assert result.output.rstrip() == "1old"

    def test_merge_local_to_global_subscript(self, execute_mumps):
        """MERGE local to global with destination subscript (§8.2.13)."""
        result = execute_mumps("TEST S A(1)=1,A(2)=2 M ^G(3)=A W ^G(3,1),^G(3,2),! Q")
        assert result.success
        assert result.output.rstrip() == "12"
