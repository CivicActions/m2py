"""Unit tests for indirection code generation module (indirection.py).

Tests for the code generation functions in src/m2py/codegen/indirection.py.
Uses real ASG nodes for more realistic and reliable testing.

Spec 012: Phase 3 - User Story 1: Name Indirection
"""

import pytest
from unittest.mock import MagicMock

from m2py.asg.expressions import MVariable, MIndirection, MLiteral
from m2py.asg.enums import IndirectionType
from m2py.codegen.indirection import (
    _count_indirection_levels,
    _generate_inner_name_expr,
    generate_name_indirection,
    generate_name_indirection_write,
    generate_multi_level_indirection,
    generate_subscripted_indirection,
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
# Tests for _generate_inner_name_expr()
# =============================================================================


@pytest.mark.codegen
class TestGenerateInnerNameExpr:
    """Tests for _generate_inner_name_expr() helper function."""

    def test_simple_variable_generates_scope_get(self, mock_ctx):
        """Simple variable X generates _scope.get("X", MArray()).value."""
        var = MVariable(name="X")
        result = _generate_inner_name_expr(var, mock_ctx)
        assert result == '_scope.get("X", MArray()).value'

    def test_variable_with_long_name(self, mock_ctx):
        """Variable with longer name works correctly."""
        var = MVariable(name="VARNAME")
        result = _generate_inner_name_expr(var, mock_ctx)
        assert result == '_scope.get("VARNAME", MArray()).value'

    def test_literal_uses_generate_expr(self, mock_ctx):
        """Literal expressions use generate_expr."""
        literal = MLiteral(value="test")
        result = _generate_inner_name_expr(literal, mock_ctx)
        # generate_expr returns quoted string for literals
        assert result == '"test"'


# =============================================================================
# Tests for generate_name_indirection() - Read
# =============================================================================


@pytest.mark.codegen
class TestGenerateNameIndirection:
    """Tests for generate_name_indirection() - reads via @VAR."""

    def test_simple_indirection_read(self, mock_ctx):
        """@X generates _rt.get_var(_scope.get("X", MArray()).value, _scope)."""
        var = MVariable(name="X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection(expr, mock_ctx)
        assert result == '_rt.get_var(_scope.get("X", MArray()).value, _scope)'

    def test_double_indirection_read(self, mock_ctx):
        """@@X generates _rt.resolve_indirection("X", 2, _scope)."""
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
        assert result == '_rt.resolve_indirection("X", 2, _scope)'

    def test_triple_indirection_read(self, mock_ctx):
        """@@@X generates _rt.resolve_indirection("X", 3, _scope)."""
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
        assert result == '_rt.resolve_indirection("X", 3, _scope)'

    def test_single_subscript_indirection(self, mock_ctx):
        """@NAME@(1) generates subscripted get_var."""
        var = MVariable(name="NAME")
        sub = MLiteral(value=1)
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
            name_indirection_subscripts=[[sub]],
        )

        result = generate_name_indirection(expr, mock_ctx)
        # MLiteral generates quoted string, so 1 becomes "1"
        assert (
            '_rt.get_var(f\'{_scope.get("NAME", MArray()).value}("1")\', _scope)'
            == result
        )

    def test_multiple_subscripts_indirection(self, mock_ctx):
        """@NAME@(1,2) generates subscripted get_var with multiple subs."""
        var = MVariable(name="NAME")
        sub1 = MLiteral(value=1)
        sub2 = MLiteral(value=2)
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
            name_indirection_subscripts=[[sub1, sub2]],
        )

        result = generate_name_indirection(expr, mock_ctx)
        # MLiteral generates quoted strings
        assert (
            '_rt.get_var(f\'{_scope.get("NAME", MArray()).value}("1", "2")\', _scope)'
            == result
        )

    def test_multi_level_with_subscripts(self, mock_ctx):
        """@@NAME@(1) generates multi-level indirection with subscripts."""
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
        # Multi-level with subscripts resolves first then adds subscripts
        assert "_rt.resolve_indirection" in result
        assert '("1")' in result  # Subscript with quoted string

    def test_with_literal_expression(self, mock_ctx):
        """@"VAR" uses the literal value directly."""
        literal = MLiteral(value="VAR")
        expr = MIndirection(
            expression=literal,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection(expr, mock_ctx)
        assert "_rt.get_var" in result


# =============================================================================
# Tests for generate_name_indirection_write() - Write
# =============================================================================


@pytest.mark.codegen
class TestGenerateNameIndirectionWrite:
    """Tests for generate_name_indirection_write() - writes via S @VAR=val."""

    def test_simple_indirection_write(self, mock_ctx):
        """S @X=1 generates _rt.set_var(_scope.get("X", MArray()).value, 1, _scope)."""
        var = MVariable(name="X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection_write(expr, "1", mock_ctx)
        assert result == '_rt.set_var(_scope.get("X", MArray()).value, 1, _scope)'

    def test_double_indirection_write(self, mock_ctx):
        """S @@X=1 generates _rt.set_var with resolved indirection."""
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
        # For @@X=1, resolve 1 level to get target name, then set
        assert '_rt.resolve_indirection("X", 1, _scope)' in result
        assert "_rt.set_var" in result

    def test_single_subscript_indirection_write(self, mock_ctx):
        """S @NAME@(1)=5 generates subscripted set_var."""
        var = MVariable(name="NAME")
        sub = MLiteral(value=1)
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
            name_indirection_subscripts=[[sub]],
        )

        result = generate_name_indirection_write(expr, "5", mock_ctx)
        # MLiteral generates quoted string
        assert (
            '_rt.set_var(f\'{_scope.get("NAME", MArray()).value}("1")\', 5, _scope)'
            == result
        )

    def test_string_value_expression(self, mock_ctx):
        """S @X="hello" correctly quotes the string value."""
        var = MVariable(name="X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection_write(expr, '"hello"', mock_ctx)
        assert result == '_rt.set_var(_scope.get("X", MArray()).value, "hello", _scope)'

    def test_multiple_subscripts_write(self, mock_ctx):
        """S @NAME@(1,2)=5 generates subscripted set_var with multiple subs."""
        var = MVariable(name="NAME")
        sub1 = MLiteral(value=1)
        sub2 = MLiteral(value=2)
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
            name_indirection_subscripts=[[sub1, sub2]],
        )

        result = generate_name_indirection_write(expr, "5", mock_ctx)
        # MLiteral generates quoted strings
        assert (
            '_rt.set_var(f\'{_scope.get("NAME", MArray()).value}("1", "2")\', 5, _scope)'
            == result
        )


# =============================================================================
# Tests for generate_multi_level_indirection()
# =============================================================================


@pytest.mark.codegen
class TestGenerateMultiLevelIndirection:
    """Tests for generate_multi_level_indirection() explicit level control."""

    def test_level_2_with_variable(self, mock_ctx):
        """Level 2 indirection with variable generates resolve call."""
        var = MVariable(name="X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_multi_level_indirection(expr, 2, mock_ctx)
        assert result == '_rt.resolve_indirection("X", 2, _scope)'

    def test_level_3_with_variable(self, mock_ctx):
        """Level 3 indirection with variable generates resolve call."""
        var = MVariable(name="Y")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_multi_level_indirection(expr, 3, mock_ctx)
        assert result == '_rt.resolve_indirection("Y", 3, _scope)'

    def test_level_with_literal_expression(self, mock_ctx):
        """Multi-level with literal expression generates str() wrapper."""
        literal = MLiteral(value="VAR")
        expr = MIndirection(
            expression=literal,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_multi_level_indirection(expr, 2, mock_ctx)
        assert result == '_rt.resolve_indirection(str("VAR"), 2, _scope)'

    def test_null_expression_raises_error(self, mock_ctx):
        """Null expression raises ValueError."""
        expr = MIndirection(
            expression=None,
            indirection_type=IndirectionType.NAME,
        )

        with pytest.raises(ValueError, match="no inner expression"):
            generate_multi_level_indirection(expr, 2, mock_ctx)


# =============================================================================
# Tests for generate_subscripted_indirection()
# =============================================================================


@pytest.mark.codegen
class TestGenerateSubscriptedIndirection:
    """Tests for generate_subscripted_indirection() explicit subscript control."""

    def test_single_subscript(self, mock_ctx):
        """Single subscript generates correct format."""
        var = MVariable(name="NAME")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_subscripted_indirection(expr, ["1"], mock_ctx)
        assert (
            "_rt.get_var(f'{_scope.get(\"NAME\", MArray()).value}(1)', _scope)"
            == result
        )

    def test_multiple_subscripts(self, mock_ctx):
        """Multiple subscripts are joined correctly."""
        var = MVariable(name="ARRAY")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_subscripted_indirection(expr, ["1", "2", "3"], mock_ctx)
        assert (
            "_rt.get_var(f'{_scope.get(\"ARRAY\", MArray()).value}(1, 2, 3)', _scope)"
            == result
        )

    def test_with_literal_expression(self, mock_ctx):
        """Literal inner expression uses generate_expr."""
        literal = MLiteral(value="MYVAR")
        expr = MIndirection(
            expression=literal,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_subscripted_indirection(expr, ['"key"'], mock_ctx)
        assert '_rt.get_var(f"{str("MYVAR")}("key")", _scope)' == result


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

    def test_generate_indirect_goto_not_implemented(self, mock_ctx):
        """generate_indirect_goto() raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Indirect GOTO"):
            generate_indirect_goto("target", mock_ctx)

    def test_generate_pattern_indirection_not_implemented(self, mock_ctx):
        """generate_pattern_indirection() raises NotImplementedError."""
        with pytest.raises(NotImplementedError, match="Pattern indirection"):
            generate_pattern_indirection("subject", "pattern", mock_ctx)


# =============================================================================
# Additional edge case tests
# =============================================================================


@pytest.mark.codegen
class TestEdgeCases:
    """Edge case tests for indirection code generation."""

    def test_variable_with_percent_prefix(self, mock_ctx):
        """System variable @%X works correctly."""
        var = MVariable(name="%X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        result = generate_name_indirection(expr, mock_ctx)
        assert '_scope.get("%X", MArray()).value' in result

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
        assert '_rt.resolve_indirection("X", 4, _scope)' == result

    def test_write_with_variable_value(self, mock_ctx):
        """S @X=Y where Y is another variable expression."""
        var = MVariable(name="X")
        expr = MIndirection(
            expression=var,
            indirection_type=IndirectionType.NAME,
        )

        # Value expression is already generated Python code
        result = generate_name_indirection_write(
            expr, '_scope.get("Y", MArray()).value', mock_ctx
        )
        assert (
            '_rt.set_var(_scope.get("X", MArray()).value, _scope.get("Y", MArray()).value, _scope)'
            == result
        )
