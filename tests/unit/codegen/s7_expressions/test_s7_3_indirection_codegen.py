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
    generate_xecute_constant,
    generate_xecute_dynamic,
    generate_indirect_do,
    generate_indirect_goto,
    generate_pattern_indirection,
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

    def test_null_expression_raises_error(self):
        """Indirection with None expression raises ValueError."""
        expr = MIndirection(
            expression=None,
            indirection_type=IndirectionType.NAME,
        )

        with pytest.raises(ValueError, match="no inner expression"):
            _count_indirection_levels(expr)

    def test_nested_null_expression_raises_error(self):
        """Nested indirection with None expression raises ValueError."""
        inner_indir = MIndirection(
            expression=None,
            indirection_type=IndirectionType.NAME,
        )
        outer_indir = MIndirection(
            expression=inner_indir,
            indirection_type=IndirectionType.NAME,
        )

        with pytest.raises(ValueError, match="Nested indirection has no inner"):
            _count_indirection_levels(outer_indir)


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
class TestXecutePlaceholders:
    """Tests that Phase 4/5 placeholders raise NotImplementedError."""

    def test_generate_xecute_constant_not_implemented(self, mock_ctx):
        """generate_xecute_constant() raises NotImplementedError."""
        stmt = MagicMock()
        with pytest.raises(NotImplementedError, match="Constant XECUTE"):
            generate_xecute_constant(stmt, mock_ctx)

    def test_generate_xecute_dynamic_not_implemented(self, mock_ctx):
        """generate_xecute_dynamic() raises NotImplementedError."""
        stmt = MagicMock()
        with pytest.raises(NotImplementedError, match="Dynamic XECUTE"):
            generate_xecute_dynamic(stmt, "code_expr", mock_ctx)

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
        # Should have actual implementation logic
        assert "parse_call_target" in source
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

    def test_generate_pattern_indirection_implemented(self, mock_ctx):
        """generate_pattern_indirection() is now implemented (Spec 012 Phase 10).

        Pattern indirection generates compile_pattern_indirect call.
        """
        import inspect

        source = inspect.getsource(generate_pattern_indirection)
        # Should NOT raise NotImplementedError anymore
        assert "raise NotImplementedError" not in source
        # Should have actual implementation logic
        assert "compile_pattern_indirect" in source
        assert "re.fullmatch" in source


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
    """Tests for generate_data_indirection_name() subscript quoting.

    The fix uses _format_subscript() to properly quote string subscripts
    in f-string construction. Without this, f'({"A"})' evaluates to '(A)'
    instead of '("A")'.

    Fixed suite: V4MERGE (17 fails → 0)
    """

    def test_data_indirection_uses_format_subscript(self, mock_ctx):
        """$D(@X@(1)) generates code using _format_subscript."""
        from m2py.codegen.indirection import generate_data_indirection_name

        var = MVariable(name="X")
        inner = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
            name_indirection_subscripts=[[MLiteral(value=1)]],
        )

        result = generate_data_indirection_name(inner, mock_ctx)
        assert "_format_subscript" in result


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
