"""Tests for IF command code generation (§8.2.9).

Reference: MUMPS 1995 ANSI Standard, Section 8.2.9
"""

import pytest


@pytest.mark.codegen
class TestIfCommandCodegen:
    """Codegen-level tests for IF command code generation (§8.2.9)."""

    def test_if_to_if_statement(self, generate_python):
        """IF generates Python if statement (§8.2.9)."""
        code = generate_python('TEST\n I 1 W "YES"\n Q\n')
        assert "if _test:" in code or "if m_truth" in code

    def test_if_test_update(self, generate_python):
        """IF updates $TEST after evaluation (§8.2.9)."""
        code = generate_python('TEST\n I 1>0 W "YES"\n Q\n')
        assert "_test = m_truth(" in code

    def test_if_true_branch(self, execute_mumps):
        """IF executes body when condition is true.

        User Story 2 acceptance scenario 1:
        Given: S X=5 I X>3 W "GT" E W "LE"
        When: generated and executed
        Then: output is "GT"
        """
        result = execute_mumps('TEST\n S X=5\n I X>3 W "GT"\n E W "LE"\n Q\n')
        assert result.output == "GT"
        assert result.success is True

    def test_if_false_branch(self, execute_mumps):
        """IF skips body when condition is false.

        User Story 2 acceptance scenario 2:
        Given: S X=1 I X>3 W "GT" E W "LE"
        When: generated and executed
        Then: output is "LE"
        """
        result = execute_mumps('TEST\n S X=1\n I X>3 W "GT"\n E W "LE"\n Q\n')
        assert result.output == "LE"
        assert result.success is True

    def test_if_zero_is_false(self, execute_mumps):
        """Zero evaluates to false in IF condition.

        User Story 2 acceptance scenario 3:
        Given: S X=0 I X W "TRUE" E W "FALSE"
        When: generated and executed
        Then: output is "FALSE" (zero is false)
        """
        result = execute_mumps('TEST\n S X=0\n I X W "TRUE"\n E W "FALSE"\n Q\n')
        assert result.output == "FALSE"
        assert result.success is True

    def test_if_string_zero_is_false(self, execute_mumps):
        """String "0" coerces to 0 → false in IF condition.

        User Story 6 acceptance scenario (T045):
        Given: I "0" W "TRUE" E W "FALSE"
        When: generated and executed
        Then: output is "FALSE" (string "0" coerces to 0, which is false)
        """
        result = execute_mumps('TEST\n I "0" W "TRUE"\n E W "FALSE"\n Q\n')
        assert result.output == "FALSE"
        assert result.success is True

    def test_if_string_with_leading_one_is_true(self, execute_mumps):
        """String "1A" coerces to 1 → true in IF condition.

        User Story 6 acceptance scenario (T046):
        Given: I "1A" W "TRUE" E W "FALSE"
        When: generated and executed
        Then: output is "TRUE" (string "1A" coerces to 1, which is true)
        """
        result = execute_mumps('TEST\n I "1A" W "TRUE"\n E W "FALSE"\n Q\n')
        assert result.output == "TRUE"
        assert result.success is True

    def test_if_string_with_no_leading_number_is_false(self, execute_mumps):
        """String "A" coerces to 0 → false in IF condition.

        User Story 6 acceptance scenario (T047):
        Given: I "A" W "TRUE" E W "FALSE"
        When: generated and executed
        Then: output is "FALSE" (string "A" coerces to 0, which is false)
        """
        result = execute_mumps('TEST\n I "A" W "TRUE"\n E W "FALSE"\n Q\n')
        assert result.output == "FALSE"
        assert result.success is True

    def test_if_string_coercion_in_comparison(self, execute_mumps):
        """String "3A" coerces to 3 in < comparison.

        User Story 6 acceptance scenario (T048):
        Given: I "3A"<5 W "YES" E W "NO"
        When: generated and executed
        Then: output is "YES" (string "3A" coerces to 3, and 3<5 is true)
        """
        result = execute_mumps('TEST\n I "3A"<5 W "YES"\n E W "NO"\n Q\n')
        assert result.output == "YES"
        assert result.success is True

    def test_if_multiple_conditions(self, execute_mumps):
        """IF with comma-separated conditions (AND) (§8.2.9).

        YDB verified: S X=3 I X>0,X<5 W "OK" → "OK"
        """
        result = execute_mumps('TEST\n S X=3\n I X>0,X<5 W "OK"\n Q\n')
        assert result.output == "OK"
        assert result.success is True

    def test_if_multiple_conditions_test_update(self, execute_mumps):
        """IF with multiple conditions updates $TEST after EACH condition (§8.2.9).

        Bug fix: $TEST must be updated after evaluating each comma-separated
        condition, not just at the end. This allows `I 1,$T` to work correctly:
        - Evaluate 1 → set $T=1
        - Evaluate $T (which is now 1) → set $T=1
        - Body executes

        Previously, all conditions were evaluated first with the original $T,
        so `I 1,$T` after `I 0` would fail because $T was still 0.
        """
        # Test 1: I 1,$T after I 0 - $T from first arg enables second
        result = execute_mumps('TEST\n I 0\n I 1,$T W "PASS"\n E W "FAIL"\n Q\n')
        assert result.output == "PASS"

        # Test 2: I $T,$T after I 1 - both read updated $T
        result = execute_mumps('TEST\n I 1\n I $T,$T W "PASS"\n E W "FAIL"\n Q\n')
        assert result.output == "PASS"

        # Test 3: I '$T,$T,$T after I 0 - NOT of 0 is 1, then 1, then 1
        result = execute_mumps('TEST\n I 0\n I \'$T,$T,$T W "PASS"\n E W "FAIL"\n Q\n')
        assert result.output == "PASS"

        # Test 4: Short-circuit still works - I 0,$T doesn't evaluate $T
        result = execute_mumps('TEST\n I 1\n I 0,$T W "BAD"\n E W "GOOD"\n Q\n')
        assert result.output == "GOOD"

        # Test 5: $T reflects final evaluated condition after short-circuit
        # I 0,1 short-circuits at 0, so $T=0
        result = execute_mumps('TEST\n I 0,1 W "BAD"\n I  W "BAD2"\n E W "OK"\n Q\n')
        assert result.output == "OK"

    def test_if_argumentless(self, execute_mumps):
        """IF argumentless uses $TEST (§8.2.9).

        YDB verified: I 1 I  W "YES" → "YES"
        """
        result = execute_mumps('TEST\n I 1 I  W "YES"\n Q\n')
        assert result.output == "YES"
        assert result.success is True


# =============================================================================
# Empty TRAMPOLINE Block (024-vista-transpilation-fixes, Contract 3)
# =============================================================================


@pytest.mark.codegen
class TestEmptyTrampolineBlock:
    """Contract 3: Empty IF/ELSE blocks must get 'pass' to avoid SyntaxError.

    Validates FR-003: empty indented blocks in TRAMPOLINE strategy.
    """

    def test_empty_block_if_goto(self, execute_mumps):
        """Contract 3 happy path: IF with GOTO in TRAMPOLINE mode."""
        code = 'EMPTYB\n S X=1 I X G DONE\n W "not reached",!\nDONE W "done",!\n Q\n'
        result = execute_mumps(code)
        assert result.success is True
        assert result.output == "done\n"

    def test_empty_block_compiles(self, generate_python):
        """Generated Python for GOTO-bearing code must compile()."""
        code = 'EMPTYB\n S X=1 I X G DONE\n W "not reached",!\nDONE W "done",!\n Q\n'
        py_code = generate_python(code)
        compile(py_code, "<test>", "exec")

    def test_if_with_argumentless_do(self, generate_python):
        """IF with argumentless DO (multi-condition) must compile."""
        code = 'TEST\n S X=1,Y=1\n I X,Y D\n . W "both true",!\n Q\n'
        py_code = generate_python(code)
        compile(py_code, "<test>", "exec")

    def test_if_false_no_body_compiles(self, generate_python):
        """IF false with empty body (e.g., G after IF) must compile."""
        code = 'TEST\n S X=0 I X G DONE\n W "ran",!\nDONE W "done",!\n Q\n'
        py_code = generate_python(code)
        compile(py_code, "<test>", "exec")

    def test_else_empty_block_compiles(self, generate_python):
        """ELSE with empty body must compile (pass inserted)."""
        code = 'TEST\n I 1 G DONE\n E  G DONE\nDONE W "ok",!\n Q\n'
        py_code = generate_python(code)
        compile(py_code, "<test>", "exec")

    def test_multi_target_goto_empty_block(self, generate_python):
        """G A:c1,B:c2,C:c3 — multi-target GOTO chain (FHWOR6 pattern)."""
        code = (
            "TEST S CHK=2\n"
            " G A:CHK=1,B:CHK=2,C:CHK=3\n"
            ' W "fallthrough",! Q\n'
            'A W "A",! Q\nB W "B",! Q\nC W "C",! Q\n'
        )
        result = generate_python(code)
        assert isinstance(result, str)
        compile(result, "<test>", "exec")

    def test_if_not_paren_with_do_quit(self, generate_python):
        """I '(DFN>0) D label Q — IF-NOT-paren-DO-QUIT (HMPDMC pattern)."""
        code = 'TEST S DFN=5\n I \'(DFN>0) W "bad",! Q\n W "good",!\n Q\n'
        result = generate_python(code)
        assert isinstance(result, str)
        compile(result, "<test>", "exec")

    def test_if_goto_guard_clause(self, generate_python):
        """IF cond ... G label — IF-GOTO guard clause (SCMCCV pattern)."""
        code = 'TEST S OK=1\n IF \'OK W "not ok",! G DONE\n W "ok",!\nDONE Q\n'
        result = generate_python(code)
        assert isinstance(result, str)
        compile(result, "<test>", "exec")

    def test_if_not_quit_guard(self, generate_python):
        """I 'START Q — IF-QUIT guard clause (FSCEVENP pattern)."""
        code = 'TEST S X=0\n I \'X Q\n W "X is nonzero",!\n Q\n'
        result = generate_python(code)
        assert isinstance(result, str)
        compile(result, "<test>", "exec")
