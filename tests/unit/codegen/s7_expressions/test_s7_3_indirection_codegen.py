"""Unit tests for indirection code generation module (indirection.py).

Tests for the code generation functions in src/m2py/codegen/indirection.py.
Uses real ASG nodes for more realistic and reliable testing.
"""

import pytest
from unittest.mock import MagicMock

from m2py.asg.expressions import MVariable, MIndirection, MLiteral
from m2py.asg.enums import IndirectionType
from m2py.codegen.indirection import (
    _count_indirection_levels,
    generate_name_indirection,
    generate_name_indirection_write,
    generate_indirect_do,
    generate_indirect_goto,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_ctx():
    """Create a mock GeneratorContext."""
    ctx = MagicMock()
    ctx.indent = 0
    return ctx


# =============================================================================
# Tests for _count_indirection_levels()
# =============================================================================


@pytest.mark.codegen
class TestCountIndirectionLevels:
    """Tests for _count_indirection_levels() helper function."""

    def test_single_level_variable(self):
        """@X has 1 level of indirection."""
        var = MVariable(name="X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        levels, inner = _count_indirection_levels(expr)

        assert levels == 1
        assert inner == var

    def test_double_level_indirection(self):
        """@@X has 2 levels of indirection."""
        var = MVariable(name="X")
        inner_indir = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )
        outer_indir = MIndirection(
            expression=inner_indir,
            indirection_type=IndirectionType.NAME,
        )

        levels, inner = _count_indirection_levels(outer_indir)

        assert levels == 2
        assert inner == var

    def test_triple_level_indirection(self):
        """@@@X has 3 levels of indirection."""
        var = MVariable(name="X")
        level1 = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )
        level2 = MIndirection(
            expression=level1,
            indirection_type=IndirectionType.NAME,
        )
        level3 = MIndirection(
            expression=level2,
            indirection_type=IndirectionType.NAME,
        )

        levels, inner = _count_indirection_levels(level3)

        assert levels == 3
        assert inner == var


# =============================================================================
# Tests for generate_name_indirection() - Read
# =============================================================================


@pytest.mark.codegen
class TestGenerateNameIndirection:
    """Tests for generate_name_indirection() - reads via @VAR.

    Feature: 018-unified-variable-system (T108, T131)
    Tests verify unified implementation that generates _rt.get_indirected() calls.
    """

    def test_simple_indirection_read(self, mock_ctx):
        """@X generates _rt.get_indirected("X", _scope, levels=1)."""
        var = MVariable(name="X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection(expr, mock_ctx)
        assert result == '_rt.get_indirected("X", _scope, levels=1)'

    def test_double_indirection_read(self, mock_ctx):
        """@@X generates _rt.get_indirected("X", _scope, levels=2)."""
        var = MVariable(name="X")
        inner = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )
        outer = MIndirection(
            expression=inner,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection(outer, mock_ctx)
        assert result == '_rt.get_indirected("X", _scope, levels=2)'

    def test_triple_indirection_read(self, mock_ctx):
        """@@@X generates _rt.get_indirected("X", _scope, levels=3)."""
        var = MVariable(name="X")
        level1 = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )
        level2 = MIndirection(
            expression=level1,
            indirection_type=IndirectionType.NAME,
        )
        level3 = MIndirection(
            expression=level2,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection(level3, mock_ctx)
        assert result == '_rt.get_indirected("X", _scope, levels=3)'

    def test_single_subscript_indirection(self, mock_ctx):
        """@NAME@(1) generates get_indirected with per_level_subscripts."""
        var = MVariable(name="NAME")
        sub = MLiteral(value=1)
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
            name_indirection_subscripts=[[sub]],
        )

        result = generate_name_indirection(expr, mock_ctx)
        # Unified uses per_level_subscripts
        assert (
            '_rt.get_indirected("NAME", _scope, levels=1, per_level_subscripts=[["1"]])'
            == result
        )

    def test_multiple_subscripts_indirection(self, mock_ctx):
        """@NAME@(1,2) generates get_indirected with per_level_subscripts."""
        var = MVariable(name="NAME")
        sub1 = MLiteral(value=1)
        sub2 = MLiteral(value=2)
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
            name_indirection_subscripts=[[sub1, sub2]],
        )

        result = generate_name_indirection(expr, mock_ctx)
        # Unified uses per_level_subscripts
        assert (
            '_rt.get_indirected("NAME", _scope, levels=1, per_level_subscripts=[["1", "2"]])'
            == result
        )

    def test_multi_level_with_subscripts(self, mock_ctx):
        """@@NAME@(1) generates get_indirected with levels and subscripts."""
        var = MVariable(name="NAME")
        inner = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )
        sub = MLiteral(value=1)
        outer = MIndirection(
            expression=inner,
            indirection_type=IndirectionType.NAME,
            name_indirection_subscripts=[[sub]],
        )

        result = generate_name_indirection(outer, mock_ctx)
        # Multi-level with subscripts uses levels=2 and per_level_subscripts
        assert "_rt.get_indirected" in result
        assert "levels=2" in result
        assert "per_level_subscripts" in result

    def test_with_literal_expression(self, mock_ctx):
        """@"VAR" uses unified path with levels=0 (expression already evaluates to name).

        Feature: 018-unified-variable-system (T140)
        Complex expressions (like literals) that evaluate to a target name directly
        use get_indirected with levels=0, which is equivalent to get_var.
        """
        literal = MLiteral(value="VAR")
        expr = MIndirection(
            expression=literal,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection(expr, mock_ctx)
        # Complex expressions now use unified get_indirected with levels=0
        assert "_rt.get_indirected" in result
        assert "levels=0" in result


# =============================================================================
# Tests for generate_name_indirection_write() - Write
# =============================================================================


@pytest.mark.codegen
class TestGenerateNameIndirectionWrite:
    """Tests for generate_name_indirection_write() - writes via S @VAR=val.

    Feature: 018-unified-variable-system (T132)
    Now uses unified set_indirected() calls.
    """

    def test_simple_indirection_write(self, mock_ctx):
        """S @X=1 generates _rt.set_indirected with levels=1."""
        var = MVariable(name="X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection_write(expr, "1", mock_ctx)
        assert result == '_rt.set_indirected("X", 1, _scope, levels=1)'

    def test_double_indirection_write(self, mock_ctx):
        """S @@X=1 generates _rt.set_indirected with levels=2."""
        var = MVariable(name="X")
        inner = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )
        outer = MIndirection(
            expression=inner,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection_write(outer, "1", mock_ctx)
        # For @@X=1, use levels=2 with set_indirected
        assert result == '_rt.set_indirected("X", 1, _scope, levels=2)'

    def test_single_subscript_indirection_write(self, mock_ctx):
        """S @NAME@(1)=5 generates set_indirected with per_level_subscripts."""
        var = MVariable(name="NAME")
        sub = MLiteral(value=1)
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
            name_indirection_subscripts=[[sub]],
        )

        result = generate_name_indirection_write(expr, "5", mock_ctx)
        # T132: Uses set_indirected with per_level_subscripts
        assert (
            result
            == '_rt.set_indirected("NAME", 5, _scope, levels=1, per_level_subscripts=[["1"]])'
        )

    def test_string_value_expression(self, mock_ctx):
        """S @X="hello" correctly quotes the string value."""
        var = MVariable(name="X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection_write(expr, '"hello"', mock_ctx)
        # T132: Uses set_indirected
        assert result == '_rt.set_indirected("X", "hello", _scope, levels=1)'

    def test_multiple_subscripts_write(self, mock_ctx):
        """S @NAME@(1,2)=5 generates set_indirected with multiple subs."""
        var = MVariable(name="NAME")
        sub1 = MLiteral(value=1)
        sub2 = MLiteral(value=2)
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
            name_indirection_subscripts=[[sub1, sub2]],
        )

        result = generate_name_indirection_write(expr, "5", mock_ctx)
        # T132: Uses set_indirected with per_level_subscripts
        assert (
            result
            == '_rt.set_indirected("NAME", 5, _scope, levels=1, per_level_subscripts=[["1", "2"]])'
        )


# =============================================================================
# Tests for NotImplementedError placeholders
# =============================================================================


@pytest.mark.codegen
class TestIndirectDoGotoSmoke:
    """Smoke tests for implemented indirect DO/GOTO."""

    def test_generate_indirect_do_implemented(self):
        """generate_indirect_do() is now implemented (Phase 7).

        This is a smoke test. Detailed tests are in test_s8_2_03_do.py
        and test_indirection.py cross-cutting tests.
        """
        # Just verify the function is no longer a stub placeholder
        import inspect

        source = inspect.getsource(generate_indirect_do)
        # Should NOT raise NotImplementedError anymore
        assert "raise NotImplementedError" not in source
        # Should have actual implementation logic (delegates to helpers)
        assert "resolve_do_targets" in source
        assert "_call_target" in source

    def test_generate_indirect_goto_implemented(self):
        """generate_indirect_goto() is now implemented (Phase 8).

        This is a smoke test. Detailed tests are in test_s8_2_06_goto.py
        and test_indirection.py cross-cutting tests.
        """
        # Just verify the function is no longer a stub placeholder
        import inspect

        source = inspect.getsource(generate_indirect_goto)
        # Should NOT raise NotImplementedError anymore
        assert "raise NotImplementedError" not in source
        # Should have actual implementation logic
        # Uses resolve_do_targets for comma-separated targets
        assert "resolve_do_targets" in source
        assert "_call_target" in source


# =============================================================================
# Additional edge case tests
# =============================================================================


@pytest.mark.codegen
class TestEdgeCases:
    """Edge case tests for indirection code generation.

    Feature: 018-unified-variable-system (T108)
    Tests now verify delegation to unified implementation.
    """

    def test_variable_with_percent_prefix(self, mock_ctx):
        """System variable @%X works correctly."""
        var = MVariable(name="%X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection(expr, mock_ctx)
        # Now uses get_indirected with percent variable name
        assert '_rt.get_indirected("%X", _scope, levels=1)' == result

    def test_deeply_nested_indirection(self, mock_ctx):
        """Very deep indirection nesting works (@@@@X = 4 levels)."""
        var = MVariable(name="X")
        current = var
        for _ in range(4):
            current = MIndirection(
                expression=current,
                indirection_type=IndirectionType.NAME,
            )

        result = generate_name_indirection(current, mock_ctx)
        # Unified version uses get_indirected with levels parameter
        assert '_rt.get_indirected("X", _scope, levels=4)' == result

    def test_write_with_variable_value(self, mock_ctx):
        """S @X=Y where Y is another variable expression."""
        var = MVariable(name="X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        # Value expression is already generated Python code (variable Y)
        # T132: Now uses set_indirected
        result = generate_name_indirection_write(
            expr, '_scope.get("Y", MArray()).value', mock_ctx
        )
        assert (
            '_rt.set_indirected("X", _scope.get("Y", MArray()).value, _scope, levels=1)'
            == result
        )


# =============================================================================
# Tests for generate_name_indirection() unified implementation
# =============================================================================


@pytest.mark.codegen
class TestGenerateNameIndirectionUnified:
    """Tests for generate_name_indirection() function (unified implementation).

    Feature: 018-unified-variable-system (T106, T107, T131)
    Tests the unified code generation for NAME indirection reads.
    """

    def test_simple_single_level(self, mock_ctx):
        """@X generates get_indirected call with levels=1."""
        from m2py.codegen.indirection import generate_name_indirection

        var = MVariable(name="X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection(expr, mock_ctx)
        assert result == '_rt.get_indirected("X", _scope, levels=1)'

    def test_double_level(self, mock_ctx):
        """@@X generates get_indirected call with levels=2."""
        from m2py.codegen.indirection import generate_name_indirection

        var = MVariable(name="X")
        inner_indir = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )
        outer_indir = MIndirection(
            expression=inner_indir,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection(outer_indir, mock_ctx)
        assert result == '_rt.get_indirected("X", _scope, levels=2)'

    def test_triple_level(self, mock_ctx):
        """@@@X generates get_indirected call with levels=3."""
        from m2py.codegen.indirection import generate_name_indirection

        var = MVariable(name="X")
        current = var
        for _ in range(3):
            current = MIndirection(
                expression=current,
                indirection_type=IndirectionType.NAME,
            )

        result = generate_name_indirection(current, mock_ctx)
        assert result == '_rt.get_indirected("X", _scope, levels=3)'

    def test_with_single_subscript(self, mock_ctx):
        """@X@(1) generates get_indirected with per_level_subscripts."""
        from m2py.codegen.indirection import generate_name_indirection

        var = MVariable(name="X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
            # name_indirection_subscripts is List[List[MExpr]] - [[1]] for @X@(1)
            name_indirection_subscripts=[[MLiteral(value=1)]],
        )

        result = generate_name_indirection(expr, mock_ctx)
        assert (
            '_rt.get_indirected("X", _scope, levels=1, per_level_subscripts=' in result
        )
        assert '["1"]' in result  # Generated as string literal

    def test_with_multiple_subscripts(self, mock_ctx):
        """@X@(1,2) generates get_indirected with per_level_subscripts."""
        from m2py.codegen.indirection import generate_name_indirection

        var = MVariable(name="X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
            # name_indirection_subscripts is List[List[MExpr]] - [[1, 2]] for @X@(1,2)
            name_indirection_subscripts=[[MLiteral(value=1), MLiteral(value=2)]],
        )

        result = generate_name_indirection(expr, mock_ctx)
        assert (
            '_rt.get_indirected("X", _scope, levels=1, per_level_subscripts=' in result
        )
        assert '["1", "2"]' in result  # Generated as string literals

    def test_global_variable(self, mock_ctx):
        """@^GLO generates get_indirected for global."""
        from m2py.codegen.indirection import generate_name_indirection
        from m2py.parser.textx_classes import GlobalVariable

        gvar = GlobalVariable(name="GLO", subscripts=[])
        expr = MIndirection(
            expression=gvar,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection(expr, mock_ctx)
        assert '_rt.get_indirected("^GLO", _scope, levels=1)' == result

    def test_percent_variable(self, mock_ctx):
        """@%Z generates get_indirected for percent variable."""
        from m2py.codegen.indirection import generate_name_indirection

        var = MVariable(name="%Z")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection(expr, mock_ctx)
        assert '_rt.get_indirected("%Z", _scope, levels=1)' == result

    def test_variable_with_innermost_subscripts(self, mock_ctx):
        """@A(1) generates get_indirected with subscripted source name."""
        from m2py.codegen.indirection import generate_name_indirection

        var = MVariable(name="A", subscripts=[MLiteral(value=1)])
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection(expr, mock_ctx)
        # Should build the source name with subscripts
        # The literal 1 becomes "1" when generated
        # Phase 19: Now uses _format_subscript helper for proper subscript formatting
        assert '"A(" + ",".join(_format_subscript(s) for s in ["1"]) + ")"' in result
        assert "levels=1" in result


@pytest.mark.codegen
class TestGenerateDataIndirectionName:
    """Tests for generate_data_indirection_name() subscript merging.

    Uses data_indirected() with per_level_subscripts to properly merge
    post-resolution subscripts into the resolved name.  This avoids the
    split-parentheses bug where '@X@("A")' produced 'name("sub")("A")'
    instead of 'name("sub","A")'.

    Fixed suite: V4MERGE (17 fails → 0), %uttcovr (13 fails → 0)
    """

    def test_data_indirection_uses_per_level_subscripts(self, mock_ctx):
        """$D(@X@(1)) generates code using data_indirected with per_level_subscripts."""
        from m2py.codegen.indirection import generate_data_indirection_name

        var = MVariable(name="X")
        inner = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
            name_indirection_subscripts=[[MLiteral(value=1)]],
        )

        result = generate_data_indirection_name(inner, mock_ctx)
        assert "data_indirected" in result
        assert "per_level_subscripts" in result


@pytest.mark.codegen
class TestGenerateIndirectionMarrayExpr:
    """Tests for generate_indirection_marray_expr() — by-ref indirection.

    When a by-reference parameter is indirected (.@IX), we need to pass
    the MArray object, not the value. This function generates the
    get_indirected_marray() call.

    Fixed suite: V3DWP (test 31083)
    """

    def test_simple_indirection_marray(self, mock_ctx):
        """@IX generates get_indirected_marray call."""
        from m2py.codegen.indirection import generate_indirection_marray_expr

        var = MVariable(name="IX")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_indirection_marray_expr(expr, mock_ctx)
        assert "get_indirected_marray" in result
        assert '"IX"' in result


# =============================================================================
# Pass 2 Coverage: Global/NakedGlobal/complex expr indirection branches
# =============================================================================


@pytest.mark.codegen
class TestIndirectionGlobalVariableBranches:
    """Tests for indirection with GlobalVariable inner expression.

    Covers uncovered branches in generate_argument_indirection,
    generate_subscript_indirection, generate_name_indirection_for,
    generate_merge_indirection_name, generate_data_indirection_name,
    generate_name_function_indirection, generate_query_indirection_name
    for the GlobalVariable isinstance path.

    Pass 2 ranges: indirection.py L914-919, L987-992, L1285-1287,
    L1388-1390, L321-325, L532-536, L641-645.
    """

    def test_set_global_indirection(self, execute_mumps):
        """S @^V=1 — name indirection with global variable source."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n K ^VV,^V S ^V="^VV" S @^V=1 W ^VV Q\n'),
            capture_output=True,
        )
        assert result.output == "1"

    def test_set_global_indirection_subscripted(self, execute_mumps):
        """S @^V@(1)=5 — global indirection with subscript."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n K ^VV,^V S ^V="^VV" S @^V@(1)=5 W ^VV(1) Q\n'),
            capture_output=True,
        )
        assert result.output == "5"

    def test_write_global_indirection(self, execute_mumps):
        """W @^V — read via global variable indirection."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n K ^VV,^V S ^V="^VV",^VV=42 W @^V Q\n'),
            capture_output=True,
        )
        assert result.output == "42"

    def test_if_global_indirection(self, execute_mumps):
        """I @^V — argument indirection with global variable source."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n K ^V S ^V="1" I @^V W "YES" Q\n'),
            capture_output=True,
        )
        assert result.output == "YES"

    def test_kill_global_indirection(self, execute_mumps):
        """K @^V — kill via global variable indirection."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n K ^V S ^V="X",X=1 K @^V W $D(X) Q\n'),
            capture_output=True,
        )
        assert result.output == "0"


@pytest.mark.codegen
class TestIndirectionSubscriptGlobalBranches:
    """Tests for subscript indirection with global variable inner expr.

    Covers generate_subscript_indirection GlobalVariable branch.
    Pass 2 ranges: indirection.py L641-645, L651-655.
    """

    def test_subscript_indirection_global_raises_lvundef(self, execute_mumps):
        """S X(@^V)=1 — global indirection in subscript position raises LVUNDEF.

        When ^V="A", @^V resolves to the VALUE at A (not the literal "A").
        Since A is undefined, YDB (and m2py) correctly raise LVUNDEF.
        Per Spec 021 Phase 12: LVUNDEF is unconditional.
        """
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n K ^V S ^V="A" S X(@^V)=1 W X("A") Q\n'),
            capture_output=True,
        )
        # Per YDB semantics: @^V where ^V="A" tries to get value of variable A
        # Since A is undefined, LVUNDEF is raised (verified with YDB)
        assert not result.success
        assert "LVUNDEF" in result.error

    def test_order_global_indirection(self, execute_mumps):
        """$O(@^V@("")) — $ORDER with global indirection source."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python(
                'TEST\n K ^VV,^V S ^V="^VV",^VV(1)=1,^VV(3)=3 W $O(@^V@("")) Q\n'
            ),
            capture_output=True,
        )
        assert result.output == "1"

    def test_query_global_indirection(self, execute_mumps):
        """$Q(@^V@("")) — $QUERY with global indirection source."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n K ^VV,^V S ^V="^VV",^VV(1,2)=5 W $Q(@^V@("")) Q\n'),
            capture_output=True,
        )
        assert "^VV(1,2)" in result.output


@pytest.mark.codegen
class TestIndirectionNakedGlobalBranches:
    """Tests for NakedGlobal in indirection contexts.

    Covers generate_indirection_marray_expr NakedGlobal branch and
    generate_subscript_indirection NakedGlobal branch.
    Pass 2 ranges: indirection.py L491-504, L601-605.
    """

    def test_naked_global_after_indirection_set(self, execute_mumps):
        """S @^V@(1)=0,^(1,2)=0 — naked global after indirection."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python(
                'TEST\n K ^VV,^V S ^V="^VV",@^V@(1)=0,^(1,2)=0 W $D(^VV(1,1,2)) Q\n'
            ),
            capture_output=True,
        )
        # Naked global after indirection set is complex; verify it runs
        assert result.success


@pytest.mark.codegen
class TestIndirectionComplexExprBranches:
    """Tests for indirection wrapping complex expressions (non-variable).

    Covers generate_argument_indirection complex expr branch and
    generate_subscript_indirection complex expr branch.
    Pass 2 ranges: indirection.py L289-296, L508-514, L617-623,
    L1104-1106, L1399-1401.
    """

    def test_argument_indirection_piece(self, execute_mumps):
        """I @$P(X,"^",1) — argument indirection wrapping $PIECE."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n S X="1^0" I @$P(X,"^",1) W "YES" Q\n'),
            capture_output=True,
        )
        assert result.output == "YES"

    def test_argument_indirection_piece_false(self, execute_mumps):
        """I @$P(X,"^",2) — false result from $PIECE indirection."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n S X="1^0" I @$P(X,"^",2) W "YES"\n W "NO" Q\n'),
            capture_output=True,
        )
        assert "NO" in result.output

    def test_set_via_piece_indirection(self, execute_mumps):
        """S @$P(X,"^",1)=5 — set via complex expression indirection."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n S X="Y^Z" S @$P(X,"^",1)=5 W Y Q\n'),
            capture_output=True,
        )
        assert result.output == "5"


@pytest.mark.codegen
class TestIndirectionSubscriptedVarBranches:
    """Tests for MVariable with subscripts in indirection.

    Covers generate_indirection_marray_expr and generate_subscript_indirection
    MVariable-with-subscripts branches.
    Pass 2 ranges: indirection.py L526-528, L542-546, L635-637, L982-984.
    """

    def test_indirection_var_subscript_set(self, execute_mumps):
        """S @X(1)=5 where X(1) contains variable name."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n S X(1)="Y" S @X(1)=5 W Y Q\n'),
            capture_output=True,
        )
        assert result.output == "5"

    def test_indirection_var_subscript_write(self, execute_mumps):
        """W @X(1) where X(1) contains variable name."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n S X(1)="Y",Y=42 W @X(1) Q\n'),
            capture_output=True,
        )
        assert result.output == "42"


@pytest.mark.codegen
class TestIndirectionPerLevelSubscripts:
    """Tests for per_level_subscripts building in indirection functions.

    Covers the per_level_subscripts construction paths in
    generate_argument_indirection, generate_name_indirection_for,
    generate_merge_indirection_name.
    Pass 2 ranges: indirection.py L289-296, L321-325, L542-546,
    L601-605, L651-655, L929-933.
    """

    def test_argument_indirection_with_subscripts(self, execute_mumps):
        """I @X@(1) — argument indirection with subscript indirection."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n S X="A",A(1)="1" I @X@(1) W "YES" Q\n'),
            capture_output=True,
        )
        assert result.output == "YES"


@pytest.mark.codegen
class TestMergeIndirectionBranches:
    """Tests for MERGE with name indirection on source or destination.

    Covers generate_merge_indirection_name GlobalVariable and MVariable
    with subscripts branches.
    Pass 2 ranges: indirection.py L982-984, L987-992.
    """

    def test_merge_indirection_source(self, execute_mumps):
        """M A=@B — merge from indirected source."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n S B="C",C(1)=10,C(2)=20 M A=@B W A(1),A(2) Q\n'),
            capture_output=True,
        )
        assert result.output == "1020"

    def test_merge_indirection_dest(self, execute_mumps):
        """M @A=B — merge into indirected destination."""
        from m2py.codegen import generate_python
        from m2py.runtime import MUMPSRuntime

        result = MUMPSRuntime().execute(
            generate_python('TEST\n S A="C",B(1)=10,B(2)=20 M @A=B W C(1),C(2) Q\n'),
            capture_output=True,
        )
        assert result.output == "1020"


@pytest.mark.codegen
class TestNameIndirectionKill:
    """Tests for name indirection in KILL context."""

    def test_kill_name_indirection(self, execute_mumps):
        """K @A — kills variable named by A."""
        result = execute_mumps('TEST\n\tS X=1,A="X"\n\tK @A\n\tW $D(X)\n\tQ\n')
        assert result.output == "0"


@pytest.mark.codegen
class TestNameIndirectionWrite:
    """Tests for name indirection in WRITE context."""

    def test_write_name_indirection(self, execute_mumps):
        """W @A — writes value of variable named by A."""
        result = execute_mumps('TEST\n\tS X=42,A="X"\n\tW @A\n\tQ\n')
        assert result.output == "42"

    def test_write_name_indirection_global(self, execute_mumps):
        """W @A where A is a global variable name."""
        result = execute_mumps('TEST\n\tS ^X=99,A="^X"\n\tW @A\n\tQ\n')
        assert result.output == "99"


# =============================================================================
# Transaction-related codegen
# =============================================================================


@pytest.mark.codegen
class TestWriteIndirectionGlobalPass2:
    """WRITE indirection with GlobalVariable + per_level subs.

    Covers codegen/statements.py L1848-1876.
    """

    def test_write_global_indirection(self, execute_mumps):
        """W @^V — write via global variable indirection."""
        result = execute_mumps('TEST\n K ^VV,^V S ^V="^VV",^VV=42 W @^V Q\n')
        assert result.output == "42"

    def test_write_global_indirection_subscripted(self, execute_mumps):
        """W @^V@(1) — write via global indirection with subscript."""
        result = execute_mumps('TEST\n K ^VV,^V S ^V="^VV",^VV(1)=99 W @^V@(1) Q\n')
        assert result.output == "99"


@pytest.mark.codegen
class TestContainsNakedGlobalPass2:
    """contains_naked_global traversing name_indirection_subscripts.

    Covers codegen/expressions.py L258-260.
    """

    def test_naked_global_after_indirection(self, execute_mumps):
        """S @^V@(1)=0,^(2)=0 — naked global after indirection set."""
        result = execute_mumps(
            'TEST\n K ^VV,^V S ^V="^VV",@^V@(1)=0,^(2)=0 W $D(^VV(1)),",",$D(^VV(2)) Q\n'
        )
        assert "1" in result.output


# =============================================================================
# f-string Nested Quotes Fix (024-vista-transpilation-fixes, Contract 2)
# =============================================================================


@pytest.mark.codegen
class TestFStringNestedQuotes:
    """Contract 2: Generated Python must not have f-string nested quote issues.

    Validates FR-002: no nested matching quotes in f-strings (Python 3.10).
    """

    def test_fstring_contract_2(self, execute_mumps):
        """Contract 2 happy path: indirected $D with $P subscript."""
        code = (
            "FSTR1\n"
            ' S Y="Y"\n'
            ' S Y(1)="found"\n'
            ' S X="1^2" I $D(@Y@($P(X,"^",1))) W "yes",!\n'
            " Q\n"
        )
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "yes\n"

    def test_fstring_compiles_on_py310(self, generate_python):
        """Generated Python must compile() without SyntaxError."""
        code = (
            "FSTR1\n"
            ' S Y="Y"\n'
            ' S Y(1)="found"\n'
            ' S X="1^2" I $D(@Y@($P(X,"^",1))) W "yes",!\n'
            " Q\n"
        )
        py_code = generate_python(code)
        compile(py_code, "<test>", "exec")

    def test_fstring_multiple_subscripts(self, generate_python):
        """f-string with multiple indirection subscripts compiles."""
        code = (
            "TEST\n"
            ' S A="A"\n'
            ' S X="1^2"\n'
            ' S A($P(X,"^",1),$P(X,"^",2))=99\n'
            ' W @A@($P(X,"^",1),$P(X,"^",2)),!\n'
            " Q\n"
        )
        py_code = generate_python(code)
        compile(py_code, "<test>", "exec")

    def test_fstring_subscript_indirection_data(self, generate_python):
        """$D(@GLB@(+X,0)) — subscript indirection in $DATA (SCAPMCU3 pattern)."""
        code = (
            "TEST\n"
            ' S GLB="^TMP($J)"\n'
            ' S @GLB@(1,0)="hello"\n'
            ' I $D(@GLB@(1,0)) W "found",!\n'
            " Q\n"
        )
        result = generate_python(code)
        assert isinstance(result, str)
        compile(result, "<test>", "exec")

    def test_fstring_order_indirection(self, generate_python):
        """$O(@SRC@(I)) — subscript indirection in $ORDER (DSICDDBR pattern)."""
        code = (
            "TEST\n"
            ' S SRC="^TMP($J)"\n'
            ' S @SRC@(1)="a",@SRC@(2)="b"\n'
            " S I=0 F  S I=$O(@SRC@(I)) Q:'I  W @SRC@(I),!\n"
            " Q\n"
        )
        result = generate_python(code)
        assert isinstance(result, str)
        compile(result, "<test>", "exec")
