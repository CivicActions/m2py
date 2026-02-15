"""Tests for the m2py CLI entry point (Phases 3-4, T012-T022).

Tests cover:
- argparse argument parsing
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

from m2py.cli import _build_parser, main
from m2py.cli.transpile import (
    TranspileResult,
    TranspileSummary,
    _safe_output_name,
    format_code,
    lint_fix,
    transpile_file,
    transpile_paths,
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
    """Test argument parser construction."""

    def test_single_path(self):
        parser = _build_parser()
        args = parser.parse_args(["FILE.m"])
        assert args.paths == ["FILE.m"]
        assert args.output is None
        assert args.verbose is False
        assert args.no_format is False

    def test_multiple_paths(self):
        parser = _build_parser()
        args = parser.parse_args(["A.m", "B.m", "dir/"])
        assert args.paths == ["A.m", "B.m", "dir/"]

    def test_output_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["FILE.m", "-o", "/tmp/out"])
        assert args.output == "/tmp/out"

    def test_output_long_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["FILE.m", "--output", "/tmp/out"])
        assert args.output == "/tmp/out"

    def test_verbose_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["FILE.m", "-v"])
        assert args.verbose is True

    def test_no_format_flag(self):
        parser = _build_parser()
        args = parser.parse_args(["FILE.m", "--no-format"])
        assert args.no_format is True

    def test_all_flags(self):
        parser = _build_parser()
        args = parser.parse_args(["A.m", "dir/", "-o", "out", "-v", "--no-format"])
        assert args.paths == ["A.m", "dir/"]
        assert args.output == "out"
        assert args.verbose is True
        assert args.no_format is True


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
        rc = main([str(sample_m_file)])
        assert rc == 0

    def test_failure_exit_code(self, broken_m_file: Path):
        rc = main([str(broken_m_file)])
        assert rc == 1

    def test_no_files_exit_code(self, tmp_dir: Path):
        empty = tmp_dir / "empty"
        empty.mkdir()
        rc = main([str(empty)])
        assert rc == 1

    def test_verbose_flag(self, sample_m_file: Path, capsys):
        rc = main([str(sample_m_file), "-v"])
        assert rc == 0
        captured = capsys.readouterr()
        assert "Transpiling" in captured.err

    def test_output_dir(self, sample_m_file: Path, tmp_dir: Path):
        out = tmp_dir / "cli_out"
        rc = main([str(sample_m_file), "-o", str(out)])
        assert rc == 0
        assert (out / "HELLO.py").exists()

    def test_no_format_flag(self, sample_m_file: Path):
        rc = main([str(sample_m_file), "--no-format"])
        assert rc == 0

    def test_directory_batch(self, batch_dir: Path, tmp_dir: Path, capsys):
        out = tmp_dir / "cli_batch_out"
        rc = main([str(batch_dir), "-o", str(out)])
        assert rc == 0
        captured = capsys.readouterr()
        assert "3/3" in captured.err

    def test_summary_output(self, sample_m_file: Path, broken_m_file: Path, capsys):
        rc = main([str(sample_m_file), str(broken_m_file)])
        assert rc == 1
        captured = capsys.readouterr()
        assert "1 failed" in captured.err

    def test_nonexistent_path_error(self, tmp_dir: Path, capsys):
        rc = main([str(tmp_dir / "MISSING.m")])
        assert rc == 1
        captured = capsys.readouterr()
        assert "Path not found" in captured.err

    def test_empty_routine(self, tmp_dir: Path):
        """Empty MUMPS file produces valid Python."""
        f = tmp_dir / "EMPTY.m"
        f.write_text("\n")
        out = tmp_dir / "out"
        rc = main([str(f), "-o", str(out)])
        assert rc == 0
        import ast

        ast.parse((out / "EMPTY.py").read_text())
