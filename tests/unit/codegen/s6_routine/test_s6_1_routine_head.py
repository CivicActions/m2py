"""Tests for Routine Head code generation (§6.1).

Reference: MUMPS 1995 ANSI Standard, Section 6.1
"""

import pytest


@pytest.mark.codegen
class TestRoutineHeadCodegen:
    """Codegen-level tests for routine head code generation (§6.1)."""

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: routine to function")
    def test_routine_to_function(self, generate_python):
        """Routine generates Python function (§6.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: formal parameters")
    def test_formal_parameters(self, generate_python):
        """Formal parameters generate function parameters (§6.1)."""
        pytest.fail("Stub - implement test")

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: routine docstring")
    def test_routine_docstring(self, generate_python):
        """Routine generates docstring with source info (§6.1)."""
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestNameTranslationCodegen:
    """Codegen tests for MUMPS-to-Python name translation.

    MUMPS allows names that are invalid Python identifiers. The name
    translator must handle: % prefix, pure numeric names, reserved words,
    and empty labels (labelless preamble). Translation must be:
    - Case-preserving (FOO ≠ Foo ≠ foo)
    - Injective (no two M names map to same Python name)
    - Reversible (can recover original M name)

    Reference: §6.1, §6.2
    """

    def test_percent_prefix_translation(self, generate_python):
        """Names starting with % get translated to valid Python.

        User Story 7 acceptance scenario (T051):
        %START becomes _pct_START function name.
        """
        code = generate_python('%START\n W "PASS"\n Q\n')
        assert "def _pct_START" in code

    def test_pure_numeric_name_translation(self):
        """Pure numeric labels get translated to valid Python.

        User Story 7 acceptance scenario (T052):
        Variable '0' becomes _n_0 (preserving leading zeros).
        """
        from m2py.codegen.names import NameTranslator

        nt = NameTranslator()
        assert nt.translate("0") == "_n_0"
        assert nt.translate("01") == "_n_01"

    def test_reserved_word_translation(self):
        """Python reserved words get prefixed.

        User Story 7 acceptance scenario (T053):
        Variable 'if' becomes _m_if (lowercase is Python keyword).
        Note: MUMPS uses uppercase IF which is NOT a Python keyword.
        """
        from m2py.codegen.names import NameTranslator

        nt = NameTranslator()
        # Python keywords are lowercase
        assert nt.translate("if") == "_m_if"
        assert nt.translate("for") == "_m_for"
        # MUMPS uppercase commands are NOT Python keywords
        assert nt.translate("IF") == "IF"
        assert nt.translate("FOR") == "FOR"

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: empty label translation")
    def test_empty_label_translation(self, generate_python):
        """Labelless preamble gets special name.

        Lines before first label become _preamble function.
        """
        pytest.fail("Stub - implement test")

    def test_case_preservation(self):
        """Name translation preserves case distinctions.

        User Story 7 acceptance scenario (T054):
        FOO, Foo, and foo remain distinct after translation.
        """
        from m2py.codegen.names import NameTranslator

        nt = NameTranslator()
        foo_upper = nt.translate("FOO")
        foo_mixed = nt.translate("Foo")
        foo_lower = nt.translate("foo")

        # All must be different
        assert foo_upper != foo_mixed
        assert foo_mixed != foo_lower
        assert foo_upper != foo_lower

        # And must preserve case
        assert foo_upper == "FOO"
        assert foo_mixed == "Foo"
        assert foo_lower == "foo"

    def test_reverse_translation(self):
        """Reverse translation recovers original names.

        User Story 7 acceptance scenario (T055):
        Given a translated Python name, reverse() recovers the original MUMPS name.
        """
        from m2py.codegen.names import NameTranslator

        nt = NameTranslator()

        # % prefix round-trip
        assert nt.reverse(nt.translate("%START")) == "%START"

        # Numeric name round-trip
        assert nt.reverse(nt.translate("0")) == "0"
        assert nt.reverse(nt.translate("01")) == "01"

        # Reserved word round-trip
        assert nt.reverse(nt.translate("if")) == "if"

        # Normal name round-trip
        assert nt.reverse(nt.translate("FOO")) == "FOO"

    @pytest.mark.stub
    @pytest.mark.xfail(reason="Not yet implemented: variable name translation")
    def test_variable_name_translation(self, generate_python):
        """Variable names use same translation rules.

        %X variable becomes _pct_X in generated Python.
        """
        pytest.fail("Stub - implement test")


@pytest.mark.codegen
class TestGeneratorContextCodegen:
    """Tests for GeneratorContext extensions (Spec 005)."""

    def test_generator_context_has_signatures(self):
        """GeneratorContext has signatures dict for function signatures."""
        from m2py.codegen.routine import GeneratorContext
        from m2py.codegen.emitter import CodeEmitter
        from m2py.asg.elements import MRoutine

        routine = MRoutine(name="TEST", labels=[])
        ctx = GeneratorContext(routine=routine, emitter=CodeEmitter())
        assert hasattr(ctx, "signatures")
        assert isinstance(ctx.signatures, dict)

    def test_generator_context_has_loop_stack(self):
        """GeneratorContext has loop_stack for tracking nested FOR loops."""
        from m2py.codegen.routine import GeneratorContext
        from m2py.codegen.emitter import CodeEmitter
        from m2py.asg.elements import MRoutine

        routine = MRoutine(name="TEST", labels=[])
        ctx = GeneratorContext(routine=routine, emitter=CodeEmitter())
        assert hasattr(ctx, "loop_stack")
        assert isinstance(ctx.loop_stack, list)

    def test_generator_context_has_in_extrinsic_call(self):
        """GeneratorContext has in_extrinsic_call flag for $TEST save/restore."""
        from m2py.codegen.routine import GeneratorContext
        from m2py.codegen.emitter import CodeEmitter
        from m2py.asg.elements import MRoutine

        routine = MRoutine(name="TEST", labels=[])
        ctx = GeneratorContext(routine=routine, emitter=CodeEmitter())
        assert hasattr(ctx, "in_extrinsic_call")
        assert ctx.in_extrinsic_call is False


@pytest.mark.codegen
class TestScopeStrategyCodegen:
    """Tests for scope strategy dispatcher (Spec 005)."""

    def test_scope_strategy_pattern_pure_function(self):
        """PURE_FUNCTION strategy returns function pattern description."""
        from m2py.codegen.routine import get_scope_strategy_pattern
        from m2py.asg.enums import ScopeStrategy

        pattern = get_scope_strategy_pattern(ScopeStrategy.PURE_FUNCTION)
        assert "return" in pattern
        assert "def" in pattern

    def test_scope_strategy_pattern_subroutine(self):
        """SUBROUTINE strategy returns subroutine pattern description."""
        from m2py.codegen.routine import get_scope_strategy_pattern
        from m2py.asg.enums import ScopeStrategy

        pattern = get_scope_strategy_pattern(ScopeStrategy.SUBROUTINE)
        assert "None" in pattern or "pass" in pattern

    def test_scope_strategy_pattern_requires_runtime(self):
        """REQUIRES_RUNTIME strategy indicates unsupported."""
        from m2py.codegen.routine import get_scope_strategy_pattern
        from m2py.asg.enums import ScopeStrategy

        pattern = get_scope_strategy_pattern(ScopeStrategy.REQUIRES_RUNTIME)
        assert "runtime" in pattern.lower() or "not supported" in pattern.lower()


@pytest.mark.codegen
class TestValidateAnalysisComplete:
    """Tests for validate_analysis_complete (Spec 005)."""

    def test_validate_empty_routine(self):
        """Empty routine passes validation."""
        from m2py.codegen.routine import validate_analysis_complete
        from m2py.asg.elements import MRoutine

        routine = MRoutine(name="TEST", labels=[])
        # Should not raise
        validate_analysis_complete(routine)

    def test_validate_routine_with_labels(self):
        """Routine with labels passes validation."""
        from m2py.codegen.routine import validate_analysis_complete
        from m2py.asg.elements import MLabel, MRoutine, MScope

        label = MLabel(name="MAIN", body=MScope(statements=[]))
        routine = MRoutine(name="TEST", labels=[label])
        # Should not raise
        validate_analysis_complete(routine)
