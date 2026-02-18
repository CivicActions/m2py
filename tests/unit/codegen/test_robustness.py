"""Tests for transpiler robustness (024-vista-transpilation-fixes, US3).

Contract 10: RecursionError prevention for deeply nested VistA expressions.
Contract 11 encoding: Encoding fallback for non-UTF-8 files.
"""

import pytest

from m2py.codegen import generate_python


# RecursionError Prevention (024-vista-transpilation-fixes, Contract 10)


@pytest.mark.codegen
class TestRecursionErrorPrevention:
    """Transpilation must not raise RecursionError on deeply nested expressions.

    VistA routine PSXRECV.m contains deeply nested concatenation / $SELECT
    expressions that exceed Python's default recursion limit during ASG
    equality checks in goto analysis. The fix uses identity comparison
    for exit_points and raises the recursion limit as a safety net.
    """

    def test_psxrecv_transpiles_without_recursion_error(self):
        """Contract 10: Deeply nested expressions in FOR+GOTO don't cause RecursionError.

        Reproduces the PSXRECV.m failure pattern: a FOR loop containing a GOTO
        and a SET with a deeply nested concatenation expression. The __eq__
        check on ASG nodes (for exit_points dedup) recurses through the entire
        expression tree, exceeding Python's default recursion limit.

        The fix uses identity comparison (``any(stmt is ep ...)``) instead of
        ``stmt not in exit_points`` in goto_analysis._classify_single_goto.
        """
        # 50‑level string concatenation inside FOR+GOTO — same shape as PSXRECV
        parts = "_".join(['"x"'] * 50)
        source = (
            f'TEST\n F I=1:1 S X={parts} G:I=5 DONE Q:I>10\n Q\nDONE\n W "done"\n Q\n'
        )
        # Must not raise RecursionError
        python_code = generate_python(source)
        assert "def TEST(" in python_code

    def test_deeply_nested_concat_expression(self):
        """Deeply nested string concatenation doesn't cause RecursionError."""
        # Build a deeply nested expression similar to PSXRECV patterns:
        # S X="a"_"b"_"c"_..._"z" (26 levels)
        parts = "_".join(f'"{chr(c)}"' for c in range(ord("a"), ord("z") + 1))
        source = f"TEST\n S X={parts}\n W X\n Q"
        python_code = generate_python(source)
        assert "def TEST(" in python_code

    def test_nested_select_in_for_with_goto(self):
        """Nested $SELECT inside FOR with GOTO (PSXRECV-like pattern)."""
        # This pattern triggers the exit_points identity check
        source = (
            "TEST\n"
            ' F I=1:1:10 S X=$S(I=1:"a",I=2:"b",1:"c") G:I=5 DONE\n'
            " Q\n"
            "DONE\n"
            ' W "done",!\n'
            " Q\n"
        )
        python_code = generate_python(source)
        assert "def TEST(" in python_code


# Encoding Fallback (024-vista-transpilation-fixes, T021)


@pytest.mark.codegen
class TestEncodingFallback:
    """CLI transpilation must handle non-UTF-8 files gracefully."""

    def test_latin1_file_transpiles(self, tmp_path):
        """Non-UTF-8 (Latin-1) .m file transpiles via transpile_file()."""
        from m2py.cli.transpile import transpile_file

        # Create a .m file with Latin-1 content (degree symbol \xb0)
        m_file = tmp_path / "LATIN.m"
        m_file.write_bytes(b'LATIN\n ;comment with \xb0 degree symbol\n W "ok",!\n Q\n')
        out_file = tmp_path / "LATIN.py"
        result = transpile_file(m_file, out_file, no_format=True)
        assert result.success, f"Failed: {result.error}"

    def test_utf8_file_still_works(self, tmp_path):
        """Normal UTF-8 .m file still transpiles correctly."""
        from m2py.cli.transpile import transpile_file

        m_file = tmp_path / "UTF8.m"
        m_file.write_text('UTF8\n W "hello",!\n Q\n', encoding="utf-8")
        out_file = tmp_path / "UTF8.py"
        result = transpile_file(m_file, out_file, no_format=True)
        assert result.success, f"Failed: {result.error}"


# Empty Block Patterns (Phase 9 / T048)


@pytest.mark.codegen
class TestPhase9EmptyBlockPatterns:
    """Verify empty-block patterns from TRAMPOLINE strategy transpile successfully.

    These inline routines reproduce the patterns found in VistA routines
    (e.g. PSAPUR, XINDX10, DICOMP) where IF+GOTO in TRAMPOLINE strategy
    previously produced empty indented blocks.
    """

    EMPTY_BLOCK_PATTERNS = [
        pytest.param(
            'EB1\n S X=1 I X G DONE\n W "not reached",!\nDONE W "done",!\n Q\n',
            id="simple-if-goto",
        ),
        pytest.param(
            'EB2\n F I=1:1:5 I I=3 G DONE\n Q\nDONE W "done",!\n Q\n',
            id="for-if-goto",
        ),
        pytest.param(
            "EB3\n S X=1 I X G A:X=1,B:X=2\nA Q\nB Q\n",
            id="multi-target-conditional-goto",
        ),
        pytest.param(
            'EB4\n N X,Y S X=1\n I X G DONE\n W "not reached",!\nDONE Q\n',
            id="new-then-if-goto",
        ),
        pytest.param(
            "EB5\n S X=1 I X D:X SUB G DONE\n Q\nSUB Q\nDONE Q\n",
            id="do-then-goto-in-if",
        ),
        pytest.param(
            'EB6\n S X=0 I \'X G SKIP\n W "yes",!\nSKIP Q\n',
            id="negated-condition-goto",
        ),
        pytest.param(
            # Pattern from XINDX10: G LABEL1:cond1,LABEL2:cond2
            "EB7\n G A:1,B:0\nA Q\nB Q\n",
            id="multi-conditional-goto",
        ),
        pytest.param(
            # Pattern from PSAPUR: FOR+QUIT+DO with nested GOTOs
            "EB8\n F  S X=$O(Y) Q:'X  I X=1 G DONE\n Q\nDONE Q\n",
            id="for-quit-if-goto",
        ),
    ]

    @pytest.mark.parametrize("source", EMPTY_BLOCK_PATTERNS)
    def test_empty_block_pattern_transpiles(self, source, generate_python):
        """Each empty-block pattern should transpile to valid Python."""
        import ast

        result = generate_python(source)
        assert result
        ast.parse(result)


@pytest.mark.codegen
class TestPhase11UnresolvedGotoPatterns:
    """Verify unresolved GOTO patterns transpile with runtime fallback.

    These inline routines reproduce the pattern found in VistA routines
    (e.g. A1BFJOBR, XQ11, RMPFDM) where GOTOs reference labels that
    don't exist in the routine. The transpiler emits a warning and
    generates LabelNotFoundError at the GOTO site.
    """

    UNRESOLVED_GOTO_PATTERNS = [
        pytest.param(
            # Pattern from A1BFJOBR: conditional GOTO to non-existent label
            "UG1\n I 1 G NOPE\n Q\n",
            id="simple-unresolved-goto",
        ),
        pytest.param(
            # Pattern from XQ11: multiple GOTOs to non-existent labels
            "UG2\n I 1 G MISS1\n I 0 G MISS2\n Q\n",
            id="multiple-unresolved-gotos",
        ),
        pytest.param(
            # Pattern: unconditional GOTO to non-existent label
            "UG3\n G GONE\n Q\n",
            id="unconditional-unresolved-goto",
        ),
        pytest.param(
            # Pattern: GOTO with postcondition to non-existent label
            "UG4\n S X=1 G:X MISSING\n Q\n",
            id="postconditioned-unresolved-goto",
        ),
        pytest.param(
            # Pattern: multi-target GOTO with one unresolved
            "UG5\n S X=1 G:X MISSING,OK:1\nOK Q\n",
            id="multi-target-one-unresolved",
        ),
        pytest.param(
            # Pattern: unresolved GOTO in unreachable code
            "UG6\n Q\n G NOPE\n Q\n",
            id="unreachable-unresolved-goto",
        ),
    ]

    @pytest.mark.parametrize("source", UNRESOLVED_GOTO_PATTERNS)
    def test_unresolved_goto_pattern_transpiles(self, source, generate_python):
        """Each unresolved-goto pattern should transpile to valid Python."""
        import ast
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = generate_python(source)
        assert result
        ast.parse(result)
