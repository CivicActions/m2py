"""Tests for coverage gaps in analysis modules.

Spec 015 Phase 2 (Category A): Tests that exercise uncovered analysis paths
in semantic_analyzer, for_analysis, goto_analysis, and resolver modules.

These tests target specific code paths identified by coverage analysis that
are reached during transpilation but were not covered by existing tests.
"""

import pytest


@pytest.mark.codegen
class TestIndirectGotoCoverage:
    """Tests for indirect GOTO patterns (G @X).

    Exercises analysis paths in semantic_analyzer and goto_analysis for
    indirect GOTO targets that cannot be resolved statically.
    """

    def test_indirect_goto_local_label(self, execute_mumps):
        """Indirect GOTO to local label (G @X where X="LABEL").

        Exercises:
        - semantic_analyzer: _analyze_goto with indirection
        - resolver: marks call as INDIRECT_CALL, is_resolved=False
        - goto_analysis: classifies as UNRESOLVED type
        """
        result = execute_mumps('TEST S X="L2" G @X Q\nL2 W "indirect",! Q\n')
        assert result.success is True
        assert result.output == "indirect\n"

    def test_indirect_goto_skips_intervening_code(self, execute_mumps):
        """Indirect GOTO skips code after GOTO on same line.

        Verifies control flow: code after G @X is unreachable.
        """
        result = execute_mumps('TEST S X="END" G @X W "skip" Q\nEND W "done" Q\n')
        assert result.success is True
        assert result.output == "done"


@pytest.mark.codegen
class TestIndirectDoCoverage:
    """Tests for indirect DO patterns (D @X).

    Exercises analysis paths in semantic_analyzer for indirect DO targets.
    """

    def test_indirect_do_local_label(self, execute_mumps):
        """Indirect DO to local label (D @X where X="LABEL").

        Exercises:
        - semantic_analyzer: _analyze_do with indirection
        - resolver: marks call as INDIRECT_CALL
        """
        result = execute_mumps('TEST S X="SUB" D @X W "after",! Q\nSUB W "sub",! Q\n')
        assert result.success is True
        assert result.output == "sub\nafter\n"

    def test_indirect_do_returns_to_caller(self, execute_mumps):
        """Indirect DO returns to caller after subroutine QUIT.

        Verifies D @X returns control flow properly.
        """
        result = execute_mumps('TEST S X="WORK" W "1" D @X W "3" Q\nWORK W "2" Q\n')
        assert result.success is True
        assert result.output == "123"


@pytest.mark.codegen
class TestForLoopVarModificationCoverage:
    """Tests for FOR loop variable modification detection.

    Exercises for_analysis._check_var_modified_in_scope() paths for
    detecting when loop variable is modified by SET, READ, or KILL.
    """

    def test_for_loop_var_set_in_body(self, execute_mumps):
        """FOR with SET modifying loop variable in body.

        Exercises: for_analysis lines 190-197 (SET check)
        Loop var modification detected, uses while pattern.
        """
        # When loop var is SET, it should affect iteration
        result = execute_mumps("TEST F I=1:1:5 S I=I+10 W I,! Q\n Q\n")
        assert result.success is True
        # S I=I+10 changes I from 1 to 11, which is >5, so loop exits after first iteration
        assert result.output == "11\n"

    def test_for_loop_var_kill_in_body(self, execute_mumps):
        """FOR with KILL modifying loop variable in body.

        Exercises: for_analysis lines 214-223 (KILL check)
        KILL on loop var removes it, terminating loop.
        """
        result = execute_mumps('TEST F I=1:1:5 K I W "after K",! Q\n Q\n')
        assert result.success is True
        # K I kills I, loop terminates
        assert result.output == "after K\n"

    def test_for_loop_var_kill_all(self, execute_mumps):
        """FOR with argumentless KILL (K) removing all locals.

        Exercises: for_analysis line 214 (is_kill_all check)
        K without arguments kills ALL local variables including loop var.
        Note: K must be followed by two spaces to be argumentless (K  W)
        """
        result = execute_mumps('TEST S X=99 F I=1:1:3 K  W "killed",! Q\n Q\n')
        assert result.success is True
        # K kills everything including I, loop exits
        assert result.output == "killed\n"

    def test_for_loop_nested_set_outer_var(self, execute_mumps):
        """Nested FOR where inner loop SETs outer loop variable.

        Exercises: for_analysis recursive check in nested scopes.
        Outer loop var modified in inner loop body is detected.
        """
        result = execute_mumps(
            'TEST F I=1:1:3 F J=1:1:2 I J=2 S I=10 W I,"-",J,! Q\n Q\n'
        )
        assert result.success is True
        # When J=2, I is set to 10, which exits outer loop (>3)
        assert "10" in result.output


@pytest.mark.codegen
class TestExternalCallCoverage:
    """Tests for external routine call handling.

    Exercises resolver and semantic_analyzer paths for external calls.
    """

    def test_external_do_generates_import(self, generate_python):
        """D ^ROUTINE generates import statement.

        Exercises:
        - resolver: marks call as ROUTINE_CALL, is_resolved=False
        - codegen: generates import for external routine
        """
        code = generate_python("TEST D ^MATH Q\n")
        assert "import MATH" in code
        # External DO calls the routine's entry point
        assert "MATH.MATH(_rt" in code

    def test_external_do_with_label(self, generate_python):
        """D LABEL^ROUTINE generates import and label call.

        Exercises resolver external call with label specification.
        """
        code = generate_python("TEST D HELPER^UTILS Q\n")
        assert "import UTILS" in code
        assert "UTILS.HELPER(_rt" in code

    def test_external_goto_generates_exception(self, generate_python):
        """G ^ROUTINE generates GotoExternal exception.

        Exercises:
        - goto_analysis: classifies as GotoType.EXTERNAL
        - codegen: generates GotoExternal raise
        """
        code = generate_python("TEST G ^OTHER Q\n")
        assert "import OTHER" in code
        assert "raise GotoExternal" in code

    def test_external_goto_with_label(self, generate_python):
        """G LABEL^ROUTINE generates GotoExternal with label name.

        Exercises goto_analysis external call classification.
        """
        code = generate_python("TEST G ENTRY^MODULE Q\n")
        assert "import MODULE" in code
        # Should include label name in GotoExternal
        assert "'ENTRY'" in code or '"ENTRY"' in code


@pytest.mark.codegen
class TestMultiLoopExitCoverage:
    """Tests for multi-loop exit patterns.

    Exercises goto_analysis paths for GOTO exiting multiple nested FOR loops.
    """

    def test_multi_loop_exit_nested_for(self, execute_mumps):
        """Nested FOR with GOTO exiting both loops.

        Exercises:
        - goto_analysis: GotoType.MULTI_LOOP_EXIT classification
        - goto_analysis: exits_loops populated with both FOR statements
        - codegen: generates _MultiLoopExit exception pattern
        """
        result = execute_mumps(
            'TEST F I=1:1:3 F J=1:1:5 I J>3 G END W I,"-",J,!\nEND W "done",! Q\n'
        )
        assert result.success is True
        # When J>3 (J=4), GOTO END exits both loops
        assert result.output == "done\n"

    def test_multi_loop_exit_preserves_variables(self, execute_mumps):
        """Variables set before multi-loop exit are preserved.

        Verifies state is maintained across the exception-based exit.
        """
        result = execute_mumps(
            "TEST S X=0 F I=1:1:3 S X=X+1 F J=1:1:3 S X=X+10 I J=2 G END\nEND W X,! Q\n"
        )
        assert result.success is True
        # X starts at 0, outer loop sets X=1, inner loop: J=1 sets X=11, J=2 sets X=21, then GOTO
        assert result.output == "21\n"

    def test_triple_nested_loop_exit(self, execute_mumps):
        """Triple-nested FOR with GOTO exiting all three.

        Exercises multi_loop_exit with more than 2 loops.
        """
        result = execute_mumps(
            "TEST F I=1:1:2 F J=1:1:2 F K=1:1:2 I K=2 G OUT W I,J,K\n"
            'OUT W "exit:",I,J,K,! Q\n'
        )
        assert result.success is True
        # K=2 triggers exit from all 3 loops, I=1, J=1, K=2
        assert "exit:112" in result.output


@pytest.mark.codegen
class TestGotoOffsetCoverage:
    """Tests for GOTO with offset patterns.

    Exercises goto_analysis paths for G LABEL+N offset handling.
    """

    def test_goto_forward_offset_within_label(self, execute_mumps):
        """G LABEL+N with offset jumping forward within same label.

        Exercises:
        - goto_analysis: offset comparison for forward jump detection
        - goto_analysis: target_stmt_index computation
        """
        result = execute_mumps('TEST G TEST+2\n W "line1",!\n W "line2",! Q\n')
        assert result.success is True
        # G TEST+2 jumps to line 2 (continuation lines), skipping line 1
        assert result.output == "line2\n"

    def test_goto_offset_skips_lines(self, generate_python):
        """GOTO with offset generates correct dispatch.

        Verifies offset handling in generated code.
        """
        code = generate_python('TEST G TEST+1\n W "target" Q\n')
        # Should have offset handling logic or target computation
        assert "offset" in code.lower() or "_line" in code.lower() or "m_num" in code
