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


@pytest.mark.codegen
class TestMergeIndirection:
    """Tests for MERGE command with indirection (Phase 13, §8.2.13)."""

    # ==========================================================================
    # Codegen Tests - Verify generated code structure
    # ==========================================================================

    def test_merge_indirection_destination_codegen(self, generate_python):
        """MERGE @X=Y generates merge_var for indirection destination."""
        code = generate_python('TEST S X="B" S A(1)=1 M @X=A Q')
        # Verify merge_var is called for indirection destination
        assert "merge_var" in code
        # Feature: 018-unified-variable-system (T143e)
        # Verify resolve_for_target is used to resolve X (unified API)
        assert "resolve_for_target" in code

    def test_merge_indirection_source_codegen(self, generate_python):
        """MERGE Y=@X generates get_tree_var for indirection source."""
        code = generate_python('TEST S X="A" S A(1)=1 M B=@X Q')
        # Verify get_tree_var is called for indirection source
        assert "get_tree_var" in code
        # Feature: 018-unified-variable-system (T143e)
        # Verify resolve_for_target is used to resolve X (unified API)
        assert "resolve_for_target" in code

    def test_merge_naked_global_destination_codegen(self, generate_python):
        """MERGE ^(subs)=X generates naked global handling."""
        code = generate_python("TEST S ^G(1)=1 S A(1)=1 M ^(2)=A Q")
        # Verify resolve_naked is called for destination
        assert "resolve_naked" in code
        # Verify merge_tree is called
        assert "merge_tree" in code

    # ==========================================================================
    # Execution Tests - Verify runtime behavior
    # ==========================================================================

    def test_merge_indirection_destination_simple(self, execute_mumps):
        """MERGE @X=Y copies tree to variable named in X."""
        result = execute_mumps('TEST S X="B" S A(1)=1,A(2)=2 M @X=A W B(1),B(2),! Q')
        assert result.success
        assert result.output.rstrip() == "12"

    def test_merge_indirection_destination_subscripted(self, execute_mumps):
        """MERGE @X=Y where X contains subscripted name."""
        result = execute_mumps(
            'TEST S X="B(1)" S A(1)=11,A(2)=22 M @X=A W B(1,1),B(1,2),! Q'
        )
        assert result.success
        assert result.output.rstrip() == "1122"

    def test_merge_indirection_destination_global(self, execute_mumps):
        """MERGE @X=Y where X contains global name."""
        result = execute_mumps('TEST S X="^G" S A(1)=1,A(2)=2 M @X=A W ^G(1),^G(2),! Q')
        assert result.success
        assert result.output.rstrip() == "12"

    def test_merge_indirection_source_simple(self, execute_mumps):
        """MERGE Y=@X copies tree from variable named in X."""
        result = execute_mumps('TEST S X="A" S A(1)=1,A(2)=2 M B=@X W B(1),B(2),! Q')
        assert result.success
        assert result.output.rstrip() == "12"

    def test_merge_indirection_source_subscripted(self, execute_mumps):
        """MERGE Y=@X where X contains subscripted name."""
        result = execute_mumps(
            'TEST S X="A(1)" S A(1,1)=11,A(1,2)=22 M B=@X W B(1),B(2),! Q'
        )
        assert result.success
        assert result.output.rstrip() == "1122"

    def test_merge_indirection_source_global(self, execute_mumps):
        """MERGE Y=@X where X contains global name."""
        result = execute_mumps('TEST S X="^G" S ^G(1)=1,^G(2)=2 M B=@X W B(1),B(2),! Q')
        assert result.success
        assert result.output.rstrip() == "12"

    def test_merge_indirection_both_sides(self, execute_mumps):
        """MERGE @X=@Y both source and destination indirect."""
        result = execute_mumps(
            'TEST S X="B",Y="A" S A(1)=1,A(2)=2 M @X=@Y W B(1),B(2),! Q'
        )
        assert result.success
        assert result.output.rstrip() == "12"

    def test_merge_indirection_preserves_existing(self, execute_mumps):
        """MERGE @X=Y preserves existing destination nodes."""
        result = execute_mumps(
            'TEST S X="B" S B(5)="old" S A(1)="new" M @X=A W B(1),$G(B(5)),! Q'
        )
        assert result.success
        assert result.output.rstrip() == "newold"

    def test_merge_naked_global_destination_simple(self, execute_mumps):
        """MERGE ^(subs)=X uses naked indicator from previous global ref."""
        result = execute_mumps(
            "TEST S ^G(1)=1 S A(1)=11,A(2)=22 M ^(2)=A W ^G(2,1),^G(2,2),! Q"
        )
        assert result.success
        assert result.output.rstrip() == "1122"

    def test_merge_naked_global_from_source(self, execute_mumps):
        """MERGE ^(subs)=X where naked comes from a previous global access."""
        # Access ^SRC(1) to set naked indicator, then use naked ref
        result = execute_mumps("TEST S ^G(1)=1 S B(1)=99 M ^(2)=B W ^G(2,1),! Q")
        assert result.success
        assert result.output.rstrip() == "99"


@pytest.mark.codegen
class TestMergeExtendedGlobal:
    """Tests for MERGE with extended global references (Phase 13)."""

    def test_merge_extended_global_pipe_destination_codegen(self, generate_python):
        """MERGE ^|"env"|G=X generates global set ignoring environment."""
        code = generate_python('TEST S A(1)=1 M ^|"env"|G=A Q')
        # Should call merge_tree on globals (environment ignored)
        assert "merge_tree" in code
        assert '"G"' in code

    def test_merge_extended_global_bracket_source_codegen(self, generate_python):
        """MERGE X=^["gld"]G generates get_tree ignoring environment."""
        code = generate_python('TEST M B=^["gld"]G Q')
        # Should call get_tree on globals (environment ignored)
        assert "get_tree" in code
        assert '"G"' in code

    def test_merge_extended_global_destination(self, execute_mumps):
        """MERGE ^|"env"|G=X copies to global (environment ignored)."""
        result = execute_mumps('TEST S A(1)=1,A(2)=2 M ^|"env"|G=A W ^G(1),^G(2),! Q')
        assert result.success
        assert result.output.rstrip() == "12"

    def test_merge_extended_global_source(self, execute_mumps):
        """MERGE X=^["gld"]G copies from global (environment ignored)."""
        result = execute_mumps('TEST S ^G(1)=1,^G(2)=2 M B=^["gld"]G W B(1),B(2),! Q')
        assert result.success
        assert result.output.rstrip() == "12"

    def test_merge_extended_global_with_subscripts(self, execute_mumps):
        """MERGE ^|"env"|G(sub)=X copies to subscripted extended global."""
        result = execute_mumps(
            'TEST S A(1)=1,A(2)=2 M ^|"x"|G(3)=A W ^G(3,1),^G(3,2),! Q'
        )
        assert result.success
        assert result.output.rstrip() == "12"
