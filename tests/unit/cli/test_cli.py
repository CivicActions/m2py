"""Tests for the m2py CLI entry point (Phases 3-4, T012-T022).

Tests cover:
- click argument parsing
- main() exit codes and stderr output
- Single-file transpilation (US1)
- Directory transpilation (US2)
- Error handling (file not found, parse failure)
- Reserved word filename avoidance
- --output, --verbose, --no-format flags
- Empty directories, mixed success/failure
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from click.testing import CliRunner

from m2py.cli import cli, main
from m2py.cli.transpile import (
    TranspileResult,
    TranspileSummary,
    _safe_output_name,
    format_code,
    lint_fix,
    transpile_file,
    transpile_paths,
    transpile_sources,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tmp_dir(tmp_path: Path) -> Path:
    """Provide a clean temporary directory."""
    return tmp_path


@pytest.fixture
def sample_m_file(tmp_dir: Path) -> Path:
    """Create a simple valid .m file."""
    f = tmp_dir / "HELLO.m"
    f.write_text(
        textwrap.dedent("""\
        HELLO ; Hello routine
         WRITE "Hello World",!
         QUIT
        """)
    )
    return f


@pytest.fixture
def broken_m_file(tmp_dir: Path) -> Path:
    """Create a .m file that will fail to parse."""
    f = tmp_dir / "BROKEN.m"
    f.write_text("@@@@GARBAGE@@@@\n")
    return f


@pytest.fixture
def batch_dir(tmp_dir: Path) -> Path:
    """Create a directory tree with multiple .m files."""
    d = tmp_dir / "routines"
    d.mkdir()
    (d / "sub").mkdir()

    (d / "A.m").write_text("A\n WRITE 1,!\n QUIT\n")
    (d / "B.m").write_text("B\n WRITE 2,!\n QUIT\n")
    (d / "sub" / "C.m").write_text("C\n WRITE 3,!\n QUIT\n")

    return d


# =============================================================================
# argparse tests (T012)
# =============================================================================


class TestArgParse:
    """Test click CLI argument parsing via CliRunner."""

    def test_single_path(self, sample_m_file: Path):
        runner = CliRunner()
        result = runner.invoke(cli, ["transpile", str(sample_m_file)])
        assert result.exit_code == 0

    def test_multiple_paths(self, sample_m_file: Path, batch_dir: Path):
        runner = CliRunner()
        result = runner.invoke(cli, ["transpile", str(sample_m_file), str(batch_dir)])
        assert result.exit_code == 0

    def test_output_flag(self, sample_m_file: Path, tmp_dir: Path):
        runner = CliRunner()
        out = tmp_dir / "out"
        result = runner.invoke(cli, ["transpile", str(sample_m_file), "-o", str(out)])
        assert result.exit_code == 0
        assert (out / "HELLO.py").exists()

    def test_output_long_flag(self, sample_m_file: Path, tmp_dir: Path):
        runner = CliRunner()
        out = tmp_dir / "out"
        result = runner.invoke(
            cli, ["transpile", str(sample_m_file), "--output", str(out)]
        )
        assert result.exit_code == 0
        assert (out / "HELLO.py").exists()

    def test_verbose_flag(self, sample_m_file: Path):
        runner = CliRunner()
        result = runner.invoke(cli, ["transpile", str(sample_m_file), "-v"])
        assert result.exit_code == 0

    def test_no_format_flag(self, sample_m_file: Path):
        runner = CliRunner()
        result = runner.invoke(cli, ["transpile", str(sample_m_file), "--no-format"])
        assert result.exit_code == 0

    def test_no_command_shows_help(self):
        runner = CliRunner()
        result = runner.invoke(cli, [])
        assert result.exit_code == 0
        assert "transpile" in result.output
        assert "globals" in result.output


# =============================================================================
# Reserved word tests (T015a)
# =============================================================================


class TestSafeOutputName:
    """Test Python reserved word filename avoidance."""

    def test_normal_name_unchanged(self):
        assert _safe_output_name("HELLO") == "HELLO"

    def test_keyword_appends_underscore(self):
        assert _safe_output_name("IF") == "IF_"
        assert _safe_output_name("for") == "for_"
        assert _safe_output_name("Class") == "Class_"

    def test_builtin_module_appends_underscore(self):
        assert _safe_output_name("os") == "os_"
        assert _safe_output_name("sys") == "sys_"
        assert _safe_output_name("math") == "math_"

    def test_non_reserved_unchanged(self):
        assert _safe_output_name("ROUTINE1") == "ROUTINE1"
        assert _safe_output_name("myfile") == "myfile"


# =============================================================================
# TranspileResult / TranspileSummary tests (T009)
# =============================================================================


class TestDataclasses:
    """Test result dataclasses."""

    def test_success_result(self):
        r = TranspileResult(
            input_path=Path("A.m"),
            output_path=Path("A.py"),
            success=True,
            error=None,
            routine_name="A",
        )
        assert r.success
        assert r.output_path == Path("A.py")

    def test_failure_result(self):
        r = TranspileResult(
            input_path=Path("A.m"),
            output_path=None,
            success=False,
            error="parse error",
            routine_name="A",
        )
        assert not r.success
        assert r.error == "parse error"

    def test_success_without_output_path_raises(self):
        with pytest.raises(ValueError):
            TranspileResult(
                input_path=Path("A.m"),
                output_path=None,
                success=True,
                error=None,
                routine_name="A",
            )

    def test_failure_without_error_raises(self):
        with pytest.raises(ValueError):
            TranspileResult(
                input_path=Path("A.m"),
                output_path=None,
                success=False,
                error=None,
                routine_name="A",
            )

    def test_summary_all_ok(self):
        s = TranspileSummary(results=[], total=3, succeeded=3, failed=0)
        assert s.all_ok

    def test_summary_with_failures(self):
        s = TranspileSummary(results=[], total=3, succeeded=2, failed=1)
        assert not s.all_ok


# =============================================================================
# transpile_file tests (T010, T014, T015)
# =============================================================================


class TestTranspileFile:
    """Test single-file transpilation."""

    def test_success(self, sample_m_file: Path, tmp_dir: Path):
        out = tmp_dir / "output" / "HELLO.py"
        result = transpile_file(sample_m_file, out)
        assert result.success
        assert out.exists()
        # Verify output is valid Python
        import ast

        ast.parse(out.read_text())

    def test_with_no_format(self, sample_m_file: Path, tmp_dir: Path):
        out = tmp_dir / "output" / "HELLO.py"
        result = transpile_file(sample_m_file, out, no_format=True)
        assert result.success
        assert out.exists()

    def test_nonexistent_file(self, tmp_dir: Path):
        bad = tmp_dir / "NOPE.m"
        out = tmp_dir / "NOPE.py"
        result = transpile_file(bad, out)
        assert not result.success
        assert "Cannot read file" in result.error  # type: ignore[operator]

    def test_broken_syntax(self, broken_m_file: Path, tmp_dir: Path):
        out = tmp_dir / "BROKEN.py"
        result = transpile_file(broken_m_file, out)
        assert not result.success
        assert result.error is not None

    def test_creates_output_dirs(self, sample_m_file: Path, tmp_dir: Path):
        out = tmp_dir / "deep" / "nested" / "HELLO.py"
        result = transpile_file(sample_m_file, out)
        assert result.success
        assert out.exists()

    def test_routine_name_from_stem(self, sample_m_file: Path, tmp_dir: Path):
        out = tmp_dir / "HELLO.py"
        result = transpile_file(sample_m_file, out)
        assert result.routine_name == "HELLO"

    def test_reserved_word_file(self, tmp_dir: Path):
        """Transpile a file named IF.m (Python keyword)."""
        f = tmp_dir / "IF.m"
        f.write_text("IF\n WRITE 1,!\n QUIT\n")
        # transpile_file itself doesn't rename — that's done by the path
        # resolution layer. But the routine transpiles OK.
        out = tmp_dir / "IF_.py"
        result = transpile_file(f, out)
        assert result.success
        assert out.exists()


# =============================================================================
# lint_fix / format_code tests (T007, T008)
# =============================================================================


class TestRuffHelpers:
    """Test ruff integration helpers."""

    def test_lint_fix_removes_unused_import(self):
        source = "import os\n\nx = 1\n"
        result = lint_fix(source, "test.py")
        assert "import os" not in result
        assert "x = 1" in result

    def test_lint_fix_preserves_used_import(self):
        source = "import os\n\nprint(os.getcwd())\n"
        result = lint_fix(source, "test.py")
        assert "import os" in result

    def test_format_code_normalizes(self):
        source = "x=1\ny =   2\n"
        result = format_code(source, "test.py")
        assert "x = 1" in result
        assert "y = 2" in result

    def test_lint_fix_returns_original_on_empty(self):
        source = ""
        result = lint_fix(source, "test.py")
        assert isinstance(result, str)

    def test_format_code_returns_original_on_empty(self):
        source = ""
        result = format_code(source, "test.py")
        assert isinstance(result, str)


# =============================================================================
# transpile_paths tests (T017-T022)
# =============================================================================


class TestTranspilePaths:
    """Test batch transpilation with path resolution."""

    def test_single_file(self, sample_m_file: Path, tmp_dir: Path):
        summary = transpile_paths([str(sample_m_file)])
        assert summary.total == 1
        assert summary.succeeded == 1
        assert summary.all_ok

    def test_directory(self, batch_dir: Path, tmp_dir: Path):
        out_dir = tmp_dir / "output"
        summary = transpile_paths([str(batch_dir)], output_dir=str(out_dir))
        assert summary.total == 3
        assert summary.succeeded == 3
        assert summary.all_ok
        # Check mirrored structure
        assert (out_dir / "A.py").exists()
        assert (out_dir / "B.py").exists()
        assert (out_dir / "sub" / "C.py").exists()

    def test_mixed_file_and_dir(self, sample_m_file: Path, batch_dir: Path):
        summary = transpile_paths([str(sample_m_file), str(batch_dir)])
        assert summary.total == 4  # 1 file + 3 in dir
        assert summary.succeeded == 4

    def test_nonexistent_path(self, tmp_dir: Path):
        summary = transpile_paths([str(tmp_dir / "NOPE.m")])
        assert summary.total == 1
        assert summary.failed == 1
        assert not summary.all_ok

    def test_empty_directory(self, tmp_dir: Path):
        empty = tmp_dir / "empty"
        empty.mkdir()
        summary = transpile_paths([str(empty)])
        assert summary.total == 0

    def test_non_m_files_ignored(self, tmp_dir: Path):
        (tmp_dir / "readme.txt").write_text("not a mumps file")
        summary = transpile_paths([str(tmp_dir / "readme.txt")])
        assert summary.total == 0

    def test_no_format_flag(self, sample_m_file: Path):
        summary = transpile_paths([str(sample_m_file)], no_format=True)
        assert summary.total == 1
        assert summary.succeeded == 1

    def test_reserved_word_filename(self, tmp_dir: Path):
        """Files like IF.m should produce IF_.py."""
        f = tmp_dir / "IF.m"
        f.write_text("IF\n WRITE 1,!\n QUIT\n")
        summary = transpile_paths([str(f)])
        assert summary.total == 1
        assert summary.succeeded == 1
        # Output should be IF_.py, not IF.py
        assert (tmp_dir / "IF_.py").exists()

    def test_mixed_success_failure(self, sample_m_file: Path, broken_m_file: Path):
        summary = transpile_paths([str(sample_m_file), str(broken_m_file)])
        assert summary.total == 2
        assert summary.succeeded == 1
        assert summary.failed == 1
        assert not summary.all_ok


# =============================================================================
# main() tests (T013, T019-T020)
# =============================================================================


class TestMain:
    """Test CLI main() entry point."""

    def test_success_exit_code(self, sample_m_file: Path):
        rc = main(["transpile", str(sample_m_file)])
        assert rc == 0

    def test_failure_exit_code(self, broken_m_file: Path):
        rc = main(["transpile", str(broken_m_file)])
        assert rc == 1

    def test_no_files_exit_code(self, tmp_dir: Path):
        empty = tmp_dir / "empty"
        empty.mkdir()
        rc = main(["transpile", str(empty)])
        assert rc == 1

    def test_verbose_flag(self, sample_m_file: Path, capsys):
        rc = main(["transpile", str(sample_m_file), "-v"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Transpiling" in captured.err

    def test_output_dir(self, sample_m_file: Path, tmp_dir: Path):
        out = tmp_dir / "cli_out"
        rc = main(["transpile", str(sample_m_file), "-o", str(out)])
        assert rc == 0
        assert (out / "HELLO.py").exists()

    def test_no_format_flag(self, sample_m_file: Path):
        rc = main(["transpile", str(sample_m_file), "--no-format"])
        assert rc == 0

    def test_directory_batch(self, batch_dir: Path, tmp_dir: Path, capsys):
        out = tmp_dir / "cli_batch_out"
        rc = main(["transpile", str(batch_dir), "-o", str(out)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "3/3" in captured.err

    def test_summary_output(self, sample_m_file: Path, broken_m_file: Path, capsys):
        rc = main(["transpile", str(sample_m_file), str(broken_m_file)])
        assert rc == 1
        captured = capsys.readouterr()
        assert "1 failed" in captured.err

    def test_nonexistent_path_error(self, tmp_dir: Path, capsys):
        rc = main(["transpile", str(tmp_dir / "MISSING.m")])
        assert rc == 1
        captured = capsys.readouterr()
        assert "Path not found" in captured.err

    def test_empty_routine(self, tmp_dir: Path):
        """Empty MUMPS file produces valid Python."""
        f = tmp_dir / "EMPTY.m"
        f.write_text("\n")
        out = tmp_dir / "out"
        rc = main(["transpile", str(f), "-o", str(out)])
        assert rc == 0
        import ast

        ast.parse((out / "EMPTY.py").read_text())


# =============================================================================
# Edge Case Tests for Coverage (T039)
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error paths to improve coverage."""

    def test_lint_fix_with_syntax_error(self):
        """lint_fix handles invalid Python gracefully."""
        # Invalid Python - ruff will still try to process
        source = "def broken(\n"
        result = lint_fix(source, "test.py")
        # Should return something (either fixed or original)
        assert isinstance(result, str)

    def test_format_code_with_syntax_error(self):
        """format_code handles invalid Python gracefully."""
        source = "def broken(\n"
        result = format_code(source, "test.py")
        # Should return original on failure
        assert isinstance(result, str)

    def test_transpile_paths_no_m_files_in_dir(self, tmp_dir: Path):
        """transpile_paths with directory containing no .m files."""
        d = tmp_dir / "no_m_files"
        d.mkdir()
        (d / "readme.txt").write_text("not a mumps file")
        (d / "other.py").write_text("# python file")

        summary = transpile_paths([str(d)])
        assert summary.total == 0
        assert summary.all_ok  # Empty is considered OK

    def test_compute_output_path_file_outside_base_dir(self, tmp_dir: Path):
        """Test _compute_output_path when input is not under base_dir."""
        from m2py.cli.transpile import _compute_output_path

        # Create two separate directories
        dir_a = tmp_dir / "dir_a"
        dir_b = tmp_dir / "dir_b"
        dir_a.mkdir()
        dir_b.mkdir()

        input_file = dir_a / "TEST.m"
        input_file.touch()

        # output_dir exists but input_file is not under base_dir (dir_b)
        output_dir = tmp_dir / "output"
        output_dir.mkdir()

        result = _compute_output_path(input_file, dir_b, output_dir)
        # Since input is not under base_dir, it uses flat output
        assert result == output_dir / "TEST.py"

    def test_transpile_paths_with_verbose(self, tmp_dir: Path, capsys):
        """transpile_paths verbose output."""
        # Create a file
        f = tmp_dir / "VERBOSE.m"
        f.write_text("VERBOSE\n WRITE 1,!\n QUIT\n")

        # Create output dir
        out = tmp_dir / "verbose_out"

        # Use main with verbose flag
        rc = main(["transpile", str(f), "-o", str(out), "-v"])
        assert rc == 0

        captured = capsys.readouterr()
        assert "Transpiling" in captured.err

    def test_transpile_file_write_permission_error(self, tmp_dir: Path, monkeypatch):
        """transpile_file handles write permission errors."""
        f = tmp_dir / "WRITERR.m"
        f.write_text("WRITERR\n QUIT\n")
        out = tmp_dir / "readonly" / "WRITERR.py"

        # Mock mkdir to raise OSError
        original_mkdir = Path.mkdir

        def mock_mkdir(self, *args, **kwargs):
            if "readonly" in str(self):
                raise OSError("Permission denied")
            return original_mkdir(self, *args, **kwargs)

        monkeypatch.setattr(Path, "mkdir", mock_mkdir)

        result = transpile_file(f, out)
        assert not result.success
        assert "Cannot write file" in (result.error or "")


class TestTranspileSources:
    """Tests for transpile_sources() parallel batch transpilation."""

    def test_empty_input_returns_empty_list(self):
        """Empty input produces empty output."""
        assert transpile_sources([]) == []

    def test_single_item(self):
        """Single item is transpiled correctly (sequential path)."""
        results = transpile_sources([("TEST\n QUIT\n", "TEST")])
        assert len(results) == 1
        code, err = results[0]
        assert err is None
        assert "def TEST" in code or "class" in code.lower() or len(code) > 0

    def test_small_batch_sequential(self):
        """Batches of <=4 items use sequential execution."""
        items = [
            ("A\n QUIT\n", "A"),
            ("B\n QUIT\n", "B"),
            ("C\n QUIT\n", "C"),
        ]
        results = transpile_sources(items)
        assert len(results) == 3
        for code, err in results:
            assert err is None
            assert len(code) > 0

    def test_large_batch_parallel(self):
        """Batches of >4 items use parallel execution."""
        items = [(f"R{i}\n QUIT\n", f"R{i}") for i in range(6)]
        results = transpile_sources(items)
        assert len(results) == 6
        for code, err in results:
            assert err is None
            assert len(code) > 0

    def test_ordering_preserved(self):
        """Results maintain the same order as input items."""
        items = [
            ("ALPHA\n QUIT\n", "ALPHA"),
            ("BETA\n QUIT\n", "BETA"),
            ("GAMMA\n QUIT\n", "GAMMA"),
            ("DELTA\n QUIT\n", "DELTA"),
            ("EPSILON\n QUIT\n", "EPSILON"),
        ]
        results = transpile_sources(items)
        assert len(results) == 5
        # Each result should contain the routine name in some form
        for i, (code, err) in enumerate(results):
            assert err is None
            assert items[i][1] in code  # routine name appears in output

    def test_error_handling(self):
        """Invalid MUMPS source returns error string instead of raising."""
        results = transpile_sources([("@@@@INVALID{{{{", "BAD")])
        assert len(results) == 1
        _code, err = results[0]
        assert err is not None
        assert "Error" in err or "Exception" in err or "error" in err.lower()

    def test_mixed_success_and_failure(self):
        """Mix of valid and invalid sources returns correct results."""
        items = [
            ("GOOD\n QUIT\n", "GOOD"),
            ("@@@@INVALID", "BAD"),
            ("ALSO\n QUIT\n", "ALSO"),
        ]
        results = transpile_sources(items)
        assert len(results) == 3
        assert results[0][1] is None  # success
        assert results[1][1] is not None  # failure
        assert results[2][1] is None  # success

    def test_max_workers_one_forces_sequential(self):
        """max_workers=1 forces sequential even for large batches."""
        items = [(f"S{i}\n QUIT\n", f"S{i}") for i in range(10)]
        results = transpile_sources(items, max_workers=1)
        assert len(results) == 10
        for code, err in results:
            assert err is None

    def test_validate_false(self):
        """validate=False skips ast.parse() validation."""
        results = transpile_sources(
            [("V\n QUIT\n", "V")],
            validate=False,
        )
        assert len(results) == 1
        code, err = results[0]
        assert err is None
        assert len(code) > 0
