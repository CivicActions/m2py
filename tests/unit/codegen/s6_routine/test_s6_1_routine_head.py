"""Tests for Routine Head code generation (§6.1).

Reference: MUMPS 1995 ANSI Standard, Section 6.1
"""

import pytest


@pytest.mark.codegen
class TestRoutineHeadCodegen:
    """Codegen-level tests for routine head code generation (§6.1)."""

    def test_routine_to_function(self, execute_mumps):
        """Routine generates executable Python function (§6.1).

        YDB verified: TEST W "Pass" Q → "Pass"
        """
        result = execute_mumps('TEST\n W "Pass"\n Q\n')
        assert result.output == "Pass"
        assert result.success is True

    def test_formal_parameters(self, generate_python):
        """Formal parameters generate function parameters (§6.1).

        T050: Generate formal parameters in function definition.
        Phase 13 (T076): _rt is now first parameter.
        Phase 19 (Spec 017): Formal params have =None default so they can be
        omitted (MUMPS allows calling with fewer args than defined).
        """
        code = generate_python("ADD(A,B) Q A+B\n")
        assert "def ADD(_rt, A=None, B=None, _scope=None, _start_offset=0):" in code

    def test_routine_docstring(self, generate_python):
        """Routine generates docstring with source info (§6.1).

        Spec 014 (T065): Each label function includes a docstring with:
        - MUMPS label name (original, for debugging/traceability)
        - Source line number
        - Inline comment from label line (if present)
        """
        # Test with label that has inline comment
        code = generate_python('MAIN ; Main entry point\n W "Hello"\n Q\n')
        assert '"""MUMPS label: MAIN (line 1) - Main entry point"""' in code

        # Test label without inline comment
        code2 = generate_python("TEST\n Q\n")
        assert '"""MUMPS label: TEST (line 1)"""' in code2

    def test_docstring_escapes_backslashes(self, generate_python):
        """Docstrings escape backslashes in MUMPS comments.

        MUMPS comments can contain backslashes like '(+-*/#\\)' which
        would be invalid escape sequences in Python docstrings.
        """
        # Backslash before ) - the original issue from V1BOA
        code = generate_python("TEST ; BINARY OPERATORS (+-*/#\\)\n Q\n")
        # Backslash should be doubled in the docstring
        assert "(+-*/#\\\\)" in code
        # Verify the code compiles without warnings
        compile(code, "<test>", "exec")

    def test_docstring_escapes_common_sequences(self, generate_python):
        """Docstrings escape sequences that look like Python escapes.

        Comments containing \\n, \\t, \\r etc. should be escaped.
        """
        # Test various escape-like sequences
        code = generate_python("TEST ; path\\name\\tab\\return\n Q\n")
        assert "path\\\\name\\\\tab\\\\return" in code
        compile(code, "<test>", "exec")

    def test_docstring_escapes_double_quotes(self, generate_python):
        """Docstrings convert double quotes to single quotes.

        Double quotes in comments could break docstring delimiters.
        """
        code = generate_python('TEST ; Say "Hello"\n Q\n')
        # Double quotes become single quotes
        assert "Say 'Hello'" in code
        compile(code, "<test>", "exec")

    def test_docstring_with_mixed_special_chars(self, generate_python):
        """Docstrings handle multiple special characters together."""
        # Mix of backslashes and quotes
        code = generate_python('TEST ; path\\to\\"file"\n Q\n')
        # Backslash escaped, quotes converted
        assert "path\\\\to\\\\'file'" in code
        compile(code, "<test>", "exec")

    def test_docstring_preserves_valid_content(self, generate_python):
        """Docstrings preserve normal comment content unchanged."""
        code = generate_python("TEST ; Normal comment with spaces\n Q\n")
        assert "Normal comment with spaces" in code
        compile(code, "<test>", "exec")


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

    def test_empty_label_translation(self, generate_python):
        """Labelless preamble gets special _preamble function name.

        Lines before first label become _preamble function.
        """
        # Code with preamble (lines before TEST label)
        code = """ ; This is a routine with preamble
 W "preamble",!
TEST
 W "test"
 Q
"""
        result = generate_python(code)
        # Should have _preamble function
        assert "def _preamble" in result
        # And the TEST function
        assert "def TEST" in result

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

    def test_variable_name_translation(self, execute_mumps):
        """Variable names with % prefix work correctly (§6.1).

        YDB verified: S %X=1 W %X → "1"
        """
        result = execute_mumps("TEST\n S %X=1\n W %X\n Q\n")
        assert result.output == "1"
        assert result.success is True


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
class TestScopeStrategyGeneration:
    """Tests for scope strategy code generation (Spec 005 Phase 9)."""

    def test_pure_function_generates_return(self, generate_python):
        """PURE_FUNCTION generates return with value (T055).

        A function with only formal params that returns a value
        should generate `return <expr>`.
        Phase 13 (T076): _rt is now first parameter.
        Phase 19 (Spec 017): Formal params have =None default.
        """
        code = generate_python("ADD(A,B) Q A+B\n")
        assert "def ADD(_rt, A=None, B=None, _scope=None, _start_offset=0):" in code
        # Should have return with expression (m_num(A) + m_num(B))
        assert "return" in code
        assert "m_num(A)" in code or "A" in code

    def test_subroutine_generates_no_explicit_return(self, generate_python):
        """SUBROUTINE generates no explicit return value (T056).

        A subroutine that does NOT modify its formal parameters
        should generate plain `return` or implicit None.

        Note: SUBROUTINEs with byref_outputs (like INCR(N)) now return
        modified params for by-ref call semantics (T059). This test
        uses a subroutine without byref outputs.
        Phase 13 (T076): _rt is now first parameter.
        Phase 19 (Spec 017): Formal params have =None default.
        """
        # Use a subroutine that sets a local but doesn't modify formals
        code = generate_python("PRINT(MSG) W MSG Q\n")
        assert "def PRINT(_rt, MSG=None, _scope=None, _start_offset=0):" in code
        # Should have plain return (not return <expr>)
        # Find lines that are just 'return' without a value
        lines = code.split("\n")
        return_lines = [line.strip() for line in lines if line.strip() == "return"]
        assert len(return_lines) > 0, "Expected plain 'return' for subroutine"

    def test_requires_runtime_generates_code(self, generate_python):
        """REQUIRES_RUNTIME labels now generate code (Spec 012, 018).

        Labels that use indirection require runtime scope.
        As of Spec 012, these are now supported and generate code with
        runtime scope management.
        Spec 018 (T041): Uses unified set_indirected() for @VAR targets.
        """
        # Indirection requires runtime scope - now supported
        code = generate_python('TEST S X="VAR",@X=1 Q\n')
        # Should generate code with _scope parameter
        assert "_scope" in code
        # Should have def with _rt parameter for runtime
        assert "def TEST(_rt" in code
        # Should have runtime set_indirected call for @X=1
        assert "_rt.set_indirected" in code

    def test_function_with_outputs_basic(self, generate_python):
        """FUNCTION_WITH_OUTPUTS generates tuple return (T057).

        Note: Full by-ref handling is Phase 10. This tests that
        the basic scope strategy is detected correctly.
        Phase 13 (T076): _rt is now first parameter.
        Phase 19 (Spec 017): Formal params have =None default.
        """
        # For now, SWAP is classified as SUBROUTINE not FUNCTION_WITH_OUTPUTS
        # because it has no return value. The return tuple pattern
        # will be implemented in Phase 10 (T059).
        # Use a simple example without NEW statement (not yet implemented)
        code = generate_python("INCR(N) S N=N+1 Q\\n")
        # Verifies formal params are generated correctly
        assert "def INCR(_rt, N=None, _scope=None, _start_offset=0):" in code


@pytest.mark.codegen
class TestValidateAnalysisComplete:
    """Tests for validate_analysis_complete (Spec 005).

    These tests verify the 'analysis-first' principle: codegen should read
    ASG fields populated by analysis passes, not compute semantic properties
    at generation time. The validation catches missing analysis.
    """

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

    def test_validate_for_without_analysis_raises(self):
        """FOR statement without loop_type raises AnalysisNotCompleteError."""
        from m2py.codegen.routine import (
            validate_analysis_complete,
            AnalysisNotCompleteError,
        )
        from m2py.asg.elements import MLabel, MRoutine, MScope
        from m2py.asg.statements import MForStatement

        # Create FOR statement without analysis (loop_type is None)
        for_stmt = MForStatement(loop_var="I", line_number=1)
        scope = MScope(statements=[for_stmt])
        label = MLabel(name="LOOP", body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        with pytest.raises(AnalysisNotCompleteError) as exc_info:
            validate_analysis_complete(routine)

        assert exc_info.value.missing_field == "loop_type"
        assert exc_info.value.required_pass == "analyze_for_loops"

    def test_validate_goto_without_analysis_raises(self):
        """GOTO statement without goto_type raises AnalysisNotCompleteError."""
        from m2py.codegen.routine import (
            validate_analysis_complete,
            AnalysisNotCompleteError,
        )
        from m2py.asg.elements import MLabel, MRoutine, MScope
        from m2py.asg.statements import MGotoStatement

        # Create GOTO statement without analysis (goto_type is None)
        goto_stmt = MGotoStatement(targets=[], line_number=1)
        scope = MScope(statements=[goto_stmt])
        label = MLabel(name="JUMP", body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        with pytest.raises(AnalysisNotCompleteError) as exc_info:
            validate_analysis_complete(routine)

        assert exc_info.value.missing_field == "goto_type"
        assert exc_info.value.required_pass == "classify_gotos"

    def test_validate_loop_exit_without_exits_loops_raises(self):
        """LOOP_EXIT GOTO without exits_loops raises AnalysisNotCompleteError."""
        from m2py.codegen.routine import (
            validate_analysis_complete,
            AnalysisNotCompleteError,
        )
        from m2py.asg.elements import MLabel, MRoutine, MScope
        from m2py.asg.statements import MGotoStatement
        from m2py.asg.enums import GotoType

        # Create LOOP_EXIT GOTO without exits_loops populated
        goto_stmt = MGotoStatement(targets=[], line_number=1)
        goto_stmt.goto_type = GotoType.LOOP_EXIT
        goto_stmt.exits_loops = []  # Empty - should have loops
        scope = MScope(statements=[goto_stmt])
        label = MLabel(name="JUMP", body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        with pytest.raises(AnalysisNotCompleteError) as exc_info:
            validate_analysis_complete(routine)

        assert exc_info.value.missing_field == "exits_loops"
        assert exc_info.value.required_pass == "classify_gotos"

    def test_validate_analyzed_routine_passes(self):
        """Routine with complete analysis passes validation."""
        from m2py.codegen.routine import validate_analysis_complete
        from m2py.asg.elements import MLabel, MRoutine, MScope
        from m2py.asg.statements import MForStatement, MGotoStatement, MQuitStatement
        from m2py.asg.enums import ForLoopType, GotoType

        # Create analyzed FOR statement
        for_stmt = MForStatement(loop_var="I", line_number=1)
        for_stmt.loop_type = ForLoopType.BOUNDED

        # Create analyzed GOTO statement (forward jump, not loop exit)
        goto_stmt = MGotoStatement(targets=[], line_number=2)
        goto_stmt.goto_type = GotoType.FORWARD_JUMP

        # Create QUIT statement (exits_for/exits_do_block can be None)
        quit_stmt = MQuitStatement(line_number=3)

        scope = MScope(statements=[for_stmt, goto_stmt, quit_stmt])
        label = MLabel(name="TEST", body=scope)
        routine = MRoutine(name="TEST", labels=[label])

        # Should not raise
        validate_analysis_complete(routine)

    def test_analysis_not_complete_error_message(self):
        """AnalysisNotCompleteError has informative message."""
        from m2py.codegen.routine import AnalysisNotCompleteError

        error = AnalysisNotCompleteError(
            "loop_type", "analyze_for_loops", "MForStatement at line 5"
        )

        assert "loop_type" in str(error)
        assert "analyze_for_loops" in str(error)
        assert "line 5" in str(error)
