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


# Batch VistA Transpilation (Phase 9 / T048)


@pytest.mark.codegen
class TestPhase9BatchTranspilation:
    """Verify all Phase 9 affected VistA routines transpile successfully."""

    @pytest.fixture
    def vista_available(self):
        """Check VistA-VEHU-M is available."""
        from pathlib import Path

        if not Path("VistA-VEHU-M").exists():
            pytest.skip("VistA-VEHU-M not available")

    EMPTY_BLOCK_ROUTINES = [
        "A4AARPT",
        "DDS4",
        "DDSU",
        "DGRP1",
        "DIAU",
        "DIBTED",
        "DICL",
        "DICOMP",
        "DICOMP1",
        "DIP100",
        "DIWE3",
        "HLOPRSR3",
        "IBAUTL9",
        "PRC5CON",
        "PRS8MT",
        "PRSARC05",
        "PSADJ",
        "PSAENTO",
        "PSALFM",
        "PSAPUR",
        "PSAREC2",
        "PSATI",
        "PSAVIN1",
        "PSAVIN2",
        "PSAVINC",
        "PSBVDLIV",
        "PSDADJ",
        "PSDADJN",
        "PSDEN",
        "PSDREC",
        "PSDREC1",
        "PSDREC2",
        "PSDREC3",
        "PSJINVW",
        "PSOCAN1",
        "PXRRPCE1",
        "QAPDEM1",
        "QAPEDI1",
        "QAPEDIT1",
        "QAPPT1",
        "QAPQCOPY",
        "QAPSCRN1",
        "QAPUTIL1",
        "XINDX10",
        "XUMF5I",
        "ZVHFIX",
    ]

    @pytest.mark.parametrize("routine_name", EMPTY_BLOCK_ROUTINES)
    def test_empty_block_routine_transpiles(
        self, routine_name, generate_python, vista_available
    ):
        """Each empty-block-affected routine should transpile successfully."""
        from pathlib import Path

        paths = list(Path("VistA-VEHU-M").rglob(f"{routine_name}.m"))
        if not paths:
            pytest.skip(f"{routine_name}.m not found")
        code = paths[0].read_text(errors="replace")
        result = generate_python(code)
        assert result
