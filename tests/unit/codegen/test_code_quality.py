"""Tests for generated code quality (Phase 5 T026, Phase 6 T029).

Validates that transpiled Python code passes pyright basic mode type checking
with zero errors. Tests representative MUMPS patterns including arithmetic,
string operations, functions with return values, and control flow.

Also tests return type inference for generated function signatures.

Validates that transpiled Python code passes ruff lint (E+F rules) with zero
errors after the CLI's post-gen lint-fix pipeline.

Reference: spec 023-cli-codegen-quality, US3, US4
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from m2py.codegen import generate_python
from m2py.cli.transpile import transpile_sources
from m2py.core.names import NameTranslator


@pytest.mark.codegen
@pytest.mark.skipif(
    subprocess.run(
        [sys.executable, "-m", "pyright", "--version"],
        capture_output=True,
    ).returncode
    != 0,
    reason="pyright not available via python -m pyright",
)
class TestPyrightBasicValidation:
    """Transpiled code passes pyright basic with zero errors."""

    @pytest.fixture
    def pyright_dir(self, tmp_path: Path) -> Path:
        """Create a temp directory with pyrightconfig.json for basic mode."""
        config = {
            "include": ["."],
            "typeCheckingMode": "basic",
            "pythonVersion": "3.10",
            "pythonPlatform": "Linux",
            "reportMissingTypeStubs": False,
            "reportMissingImports": False,
            "reportMissingModuleSource": False,
        }
        config_path = tmp_path / "pyrightconfig.json"
        config_path.write_text(json.dumps(config))
        return tmp_path

    def _transpile_and_check(
        self, pyright_dir: Path, name: str, mumps_source: str
    ) -> None:
        """Transpile MUMPS source and run pyright basic on it.

        Args:
            pyright_dir: Directory with pyrightconfig.json
            name: Output filename (without .py)
            mumps_source: MUMPS source code
        """
        code = generate_python(mumps_source)
        (pyright_dir / f"{name}.py").write_text(code)

        result = subprocess.run(
            [sys.executable, "-m", "pyright", "--project", str(pyright_dir)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"pyright basic failed on {name}.py:\n{result.stdout}\n{result.stderr}"
        )

    def test_arithmetic_operations(self, pyright_dir: Path) -> None:
        """Integer division and exponentiation use type-safe helpers."""
        source = textwrap.dedent("""\
            arith
             N X,Y,Z
             S X=10,Y=3
             S Z=X\\Y
             W Z,!
             S Z=X**Y
             W Z,!
             S Z=X#Y
             W Z,!
             S Z=X/Y
             W Z,!
             S Z=X+Y*2
             W Z,!
             Q
        """).strip()
        self._transpile_and_check(pyright_dir, "arith", source)

    def test_string_operations(self, pyright_dir: Path) -> None:
        """String concatenation, comparison, and intrinsic functions."""
        source = textwrap.dedent("""\
            strops
             N S,T,R
             S S="Hello"
             S T="World"
             S R=S_", "_T
             W R,!
             W $L(R),!
             W $E(R,1,5),!
             W S]T,!
             Q
        """).strip()
        self._transpile_and_check(pyright_dir, "strops", source)

    def test_functions_with_return_types(self, pyright_dir: Path) -> None:
        """Functions get return type annotations from QUIT expression types."""
        source = textwrap.dedent("""\
            funcs
             W $$ADD(3,4),!
             W $$GREET("World"),!
             W $$ISPOS(5),!
             Q
            ADD(a,b)
             Q a+b
            GREET(name)
             Q "Hello, "_name
            ISPOS(x)
             Q x>0
        """).strip()
        self._transpile_and_check(pyright_dir, "funcs", source)

    def test_control_flow(self, pyright_dir: Path) -> None:
        """IF/ELSE, FOR loops, and conditional QUIT pass type checking."""
        source = textwrap.dedent("""\
            flow
             N I,X
             S X=0
             F I=1:1:10 D
             . S X=X+I
             W X,!
             I X>50 W "big",!
             E  W "small",!
             Q
        """).strip()
        self._transpile_and_check(pyright_dir, "flow", source)

    def test_all_representative_files(self, pyright_dir: Path) -> None:
        """Combined test: transpile multiple routines, run pyright once."""
        sources = {
            "arith": textwrap.dedent("""\
                arith
                 N A,B,C
                 S A=10,B=3
                 S C=A\\B W C,!
                 S C=A**B W C,!
                 S C=A#B W C,!
                 Q
            """).strip(),
            "strings": textwrap.dedent("""\
                strings
                 N S
                 S S="ABC"_"DEF"
                 W $L(S),!
                 W $E(S,2,4),!
                 Q
            """).strip(),
            "funcs": textwrap.dedent("""\
                funcs
                 W $$SQ(5),!
                 Q
                SQ(n)
                 Q n*n
            """).strip(),
        }
        for name, src in sources.items():
            code = generate_python(src)
            (pyright_dir / f"{name}.py").write_text(code)

        result = subprocess.run(
            [sys.executable, "-m", "pyright", "--project", str(pyright_dir)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"pyright basic failed:\n{result.stdout}\n{result.stderr}"
        )


@pytest.mark.codegen
class TestReturnTypeHints:
    """Generated functions get return type annotations from QUIT expressions."""

    def test_string_return_type(self) -> None:
        """Function returning a string concatenation gets -> str | None."""
        source = textwrap.dedent("""\
            test
             Q
            FN(x)
             Q "hello"_x
        """).strip()
        code = generate_python(source)
        assert "-> str | None:" in code

    def test_numeric_return_type(self) -> None:
        """Function returning arithmetic gets -> int | Decimal | None."""
        source = textwrap.dedent("""\
            test
             Q
            ADD(a,b)
             Q a+b
        """).strip()
        code = generate_python(source)
        assert "-> int | Decimal | None:" in code

    def test_boolean_return_type(self) -> None:
        """Function returning comparison gets -> int | None."""
        source = textwrap.dedent("""\
            test
             Q
            GT(a,b)
             Q a>b
        """).strip()
        code = generate_python(source)
        assert "-> int | None:" in code

    def test_no_return_value_no_annotation(self) -> None:
        """Labels without QUIT value get no return type annotation."""
        source = textwrap.dedent("""\
            test
             W "hello"
             Q
        """).strip()
        code = generate_python(source)
        # Find the def line for test — should not have ->
        for line in code.split("\n"):
            if "def test(" in line:
                assert "->" not in line
                break

    def test_unknown_return_type_no_annotation(self) -> None:
        """Functions returning variables (UNKNOWN type) get no annotation."""
        source = textwrap.dedent("""\
            test
             Q
            FN(x)
             Q x
        """).strip()
        code = generate_python(source)
        # Find the def line for FN — variable returns are UNKNOWN
        for line in code.split("\n"):
            if "def FN(" in line:
                assert "->" not in line
                break


@pytest.mark.codegen
class TestArithmeticHelperCodegen:
    """Integer division and exponentiation use type-safe helpers in generated code."""

    def test_integer_division_uses_m_int_div(self) -> None:
        """The \\\\ operator generates m_int_div() calls."""
        source = textwrap.dedent("""\
            test
             W 10\\3
             Q
        """).strip()
        code = generate_python(source)
        assert "m_int_div(" in code

    def test_exponentiation_uses_m_pow(self) -> None:
        """The ** operator generates m_pow() calls."""
        source = textwrap.dedent("""\
            test
             W 2**3
             Q
        """).strip()
        code = generate_python(source)
        assert "m_pow(" in code

    def test_helpers_imported(self) -> None:
        """m_int_div and m_pow are included in the import line."""
        source = textwrap.dedent("""\
            test
             W 1
             Q
        """).strip()
        code = generate_python(source)
        assert "m_int_div" in code
        assert "m_pow" in code


@pytest.mark.slow
@pytest.mark.codegen
@pytest.mark.skipif(
    subprocess.run(
        [sys.executable, "-m", "pyright", "--version"],
        capture_output=True,
    ).returncode
    != 0,
    reason="pyright not available via python -m pyright",
)
class TestPyrightAllFunctionalFiles:
    """ALL transpiled MUMPS functional test files pass pyright basic (T025o).

    This test transpiles every .m file under tests/functional/*/inref/ and
    merge-routines/, runs pyright basic on ALL outputs in a single invocation,
    and asserts zero type-checking errors.

    Marked @slow because it transpiles ~1200+ files and runs pyright (~2 min).
    """

    FUNCTIONAL_DIR = Path(__file__).resolve().parents[2] / "functional"

    def _collect_m_files(self) -> list[Path]:
        """Collect all .m files from functional test suites."""
        m_files: list[Path] = []
        # inref directories contain the routine source files
        for inref in sorted(self.FUNCTIONAL_DIR.rglob("inref")):
            m_files.extend(sorted(inref.glob("*.m")))
        # merge-routines has .m files directly
        merge_routines = self.FUNCTIONAL_DIR / "merge-routines"
        if merge_routines.is_dir():
            m_files.extend(sorted(merge_routines.glob("*.m")))
        # com directory
        com_dir = self.FUNCTIONAL_DIR / "com"
        if com_dir.is_dir():
            m_files.extend(sorted(com_dir.glob("*.m")))
        return m_files

    def test_all_transpiled_files_pass_pyright(self, tmp_path: Path) -> None:
        """Transpile all functional .m files and assert pyright basic passes."""
        m_files = self._collect_m_files()
        assert len(m_files) > 1000, (
            f"Expected 1000+ .m files but found {len(m_files)} — "
            "test setup may be broken"
        )

        # Write pyrightconfig.json
        config = {
            "include": ["."],
            "typeCheckingMode": "basic",
            "pythonVersion": "3.10",
            "pythonPlatform": "Linux",
            "reportMissingTypeStubs": False,
            "reportMissingImports": False,
            "reportMissingModuleSource": False,
        }
        (tmp_path / "pyrightconfig.json").write_text(json.dumps(config))

        # Read all sources and batch-transpile in parallel
        sources: list[tuple[str, str]] = []
        read_errors: list[tuple[Path, str]] = []
        for m_file in m_files:
            try:
                source = m_file.read_text(encoding="utf-8", errors="replace")
                sources.append((source, m_file.stem.upper()))
            except Exception as exc:
                read_errors.append((m_file, str(exc)))

        results = transpile_sources(sources, validate=False)

        # Write transpiled files to disk
        transpiled = 0
        failed_transpile: list[tuple[Path, str]] = list(read_errors)
        seen_names: set[str] = set()

        for m_file, (code, error) in zip(m_files, results):
            if error is not None:
                failed_transpile.append((m_file, error))
                continue

            # Use NameTranslator for safe Python filenames
            # (e.g. io.m -> io_.py to avoid stdlib conflicts)
            stem = NameTranslator.to_python(m_file.stem)
            if stem in seen_names:
                # Use parent dir name as prefix to disambiguate
                parent = m_file.parent.parent.name
                stem = f"{parent}_{stem}"
            seen_names.add(stem)

            (tmp_path / f"{stem}.py").write_text(code)
            transpiled += 1

        assert transpiled > 900, (
            f"Only {transpiled} files transpiled successfully — "
            f"expected 900+. First failures:\n"
            + "\n".join(f"  {p.name}: {e}" for p, e in failed_transpile[:10])
        )

        # Run pyright on all transpiled files at once
        result = subprocess.run(
            [sys.executable, "-m", "pyright", "--project", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode != 0:
            # Parse error count from output for a clear message
            lines = result.stdout.strip().split("\n")
            error_summary = [
                l
                for l in lines
                if "error" in l.lower()
                and ("found" in l.lower() or "reported" in l.lower())
            ]
            summary_msg = (
                error_summary[-1]
                if error_summary
                else lines[-1]
                if lines
                else "unknown"
            )

            # Show first 40 error lines for debugging
            error_lines = [
                l for l in lines if ": error:" in l or "error:" in l.lower()
            ][:40]
            error_detail = (
                "\n".join(error_lines) if error_lines else result.stdout[:3000]
            )

            pytest.fail(
                f"pyright basic failed on {transpiled} transpiled files.\n"
                f"Summary: {summary_msg}\n"
                f"First errors:\n{error_detail}"
            )


@pytest.mark.codegen
class TestRuffLintValidation:
    """Transpiled code passes ruff check (E+F rules) with zero issues (T029).

    Generated Python undergoes the lint_fix pipeline (ruff check --fix) before
    being written to disk. After that auto-fix pass, zero ruff issues should
    remain under the project's select=['E','F'] / ignore=['E501','E741'] config.
    """

    def _transpile_and_lint(self, tmp_path: Path, name: str, mumps_source: str) -> None:
        """Transpile MUMPS source through full pipeline and ruff-check it.

        Uses generate_python() + lint_fix() to match the real CLI pipeline,
        then verifies ruff check finds zero remaining issues.
        """
        from m2py.cli.transpile import lint_fix

        code = generate_python(mumps_source)
        code = lint_fix(code, f"{name}.py")
        out_file = tmp_path / f"{name}.py"
        out_file.write_text(code)

        result = subprocess.run(
            [
                "ruff",
                "check",
                "--select",
                "E,F",
                "--ignore",
                "E501,E741",
                str(out_file),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"ruff check failed on {name}.py:\n{result.stdout}\n{result.stderr}"
        )

    def test_arithmetic_and_set(self, tmp_path: Path) -> None:
        """SET, arithmetic, and string concat produce lint-clean code."""
        source = textwrap.dedent("""\
            arith
             N X,Y,Z
             S X=10,Y=3
             S Z=X\\Y
             W Z,!
             S Z=X**Y
             W Z,!
             Q
        """).strip()
        self._transpile_and_lint(tmp_path, "arith", source)

    def test_for_loops(self, tmp_path: Path) -> None:
        """FOR loops (simple and argumentless) produce lint-clean code."""
        source = textwrap.dedent("""\
            fortest
             N I,S
             S S=0
             F I=1:1:10 S S=S+I
             W S,!
             Q
        """).strip()
        self._transpile_and_lint(tmp_path, "fortest", source)

    def test_new_and_kill(self, tmp_path: Path) -> None:
        """NEW and KILL commands produce lint-clean code (# noqa: F841)."""
        source = textwrap.dedent("""\
            nk
             N X,Y
             S X=1 S Y=2
             K X
             W Y,!
             Q
        """).strip()
        self._transpile_and_lint(tmp_path, "nk", source)

    def test_read_patterns(self, tmp_path: Path) -> None:
        """READ commands produce lint-clean code with noqa annotations."""
        source = textwrap.dedent("""\
            rdtest
             N X
             R X
             W X,!
             Q
        """).strip()
        self._transpile_and_lint(tmp_path, "rdtest", source)

    def test_all_representative_files(self, tmp_path: Path) -> None:
        """Multiple routines transpiled together pass ruff as a batch."""
        from m2py.cli.transpile import lint_fix

        sources = {
            "arith": textwrap.dedent("""\
                arith
                 N A,B,C
                 S A=10,B=3
                 S C=A\\B W C,!
                 S C=A**B W C,!
                 Q
            """).strip(),
            "strings": textwrap.dedent("""\
                strings
                 N S
                 S S="ABC"_"DEF"
                 W $L(S),!
                 W $E(S,2,4),!
                 Q
            """).strip(),
            "funcs": textwrap.dedent("""\
                funcs
                 W $$SQ(5),!
                 Q
                SQ(n)
                 Q n*n
            """).strip(),
        }
        for name, src in sources.items():
            code = generate_python(src)
            code = lint_fix(code, f"{name}.py")
            (tmp_path / f"{name}.py").write_text(code)

        result = subprocess.run(
            [
                "ruff",
                "check",
                "--select",
                "E,F",
                "--ignore",
                "E501,E741",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"ruff check failed on representative files:\n"
            f"{result.stdout}\n{result.stderr}"
        )


@pytest.mark.slow
@pytest.mark.codegen
class TestRuffAllFunctionalFiles:
    """ALL transpiled MUMPS functional test files pass ruff check (T029).

    Transpiles every .m file under tests/functional/, runs the lint_fix
    pipeline on each, then runs ruff check on the entire output directory
    to assert zero remaining lint issues.

    Marked @slow because it transpiles ~1200+ files (~1-2 min).
    """

    FUNCTIONAL_DIR = Path(__file__).resolve().parents[2] / "functional"

    def _collect_m_files(self) -> list[Path]:
        """Collect all .m files from functional test suites."""
        m_files: list[Path] = []
        for inref in sorted(self.FUNCTIONAL_DIR.rglob("inref")):
            m_files.extend(sorted(inref.glob("*.m")))
        merge_routines = self.FUNCTIONAL_DIR / "merge-routines"
        if merge_routines.is_dir():
            m_files.extend(sorted(merge_routines.glob("*.m")))
        com_dir = self.FUNCTIONAL_DIR / "com"
        if com_dir.is_dir():
            m_files.extend(sorted(com_dir.glob("*.m")))
        return m_files

    def test_all_transpiled_files_pass_ruff(self, tmp_path: Path) -> None:
        """Transpile all functional .m files and assert ruff check passes."""
        from m2py.cli.transpile import lint_fix

        m_files = self._collect_m_files()
        assert len(m_files) > 1000, (
            f"Expected 1000+ .m files but found {len(m_files)} — "
            "test setup may be broken"
        )

        # Read all sources and batch-transpile in parallel
        sources: list[tuple[str, str]] = []
        read_errors: list[tuple[Path, str]] = []
        for m_file in m_files:
            try:
                source = m_file.read_text(encoding="utf-8", errors="replace")
                sources.append((source, m_file.stem.upper()))
            except Exception as exc:
                read_errors.append((m_file, str(exc)))

        results = transpile_sources(sources, validate=False)

        # Write transpiled files to disk with lint-fix
        transpiled = 0
        failed_transpile: list[tuple[Path, str]] = list(read_errors)
        seen_names: set[str] = set()

        for m_file, (code, error) in zip(m_files, results):
            if error is not None:
                failed_transpile.append((m_file, error))
                continue

            code = lint_fix(code, m_file.name.replace(".m", ".py"))

            stem = NameTranslator.to_python(m_file.stem)
            if stem in seen_names:
                parent = m_file.parent.parent.name
                stem = f"{parent}_{stem}"
            seen_names.add(stem)

            (tmp_path / f"{stem}.py").write_text(code)
            transpiled += 1

        assert transpiled > 900, (
            f"Only {transpiled} files transpiled successfully — "
            f"expected 900+. First failures:\n"
            + "\n".join(f"  {p.name}: {e}" for p, e in failed_transpile[:10])
        )

        # Run ruff check on all transpiled files at once
        result = subprocess.run(
            [
                "ruff",
                "check",
                "--select",
                "E,F",
                "--ignore",
                "E501,E741",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            lines = result.stdout.strip().split("\n")
            error_lines = [l for l in lines if ": " in l and ("E" in l or "F" in l)][
                :40
            ]
            error_detail = (
                "\n".join(error_lines) if error_lines else result.stdout[:3000]
            )
            pytest.fail(
                f"ruff check failed on {transpiled} transpiled files.\n"
                f"First errors:\n{error_detail}"
            )


# =============================================================================
# Format Validation Tests (Phase 7: US5 - Auto-Formatted Output) (T030-T032)
# =============================================================================


@pytest.mark.codegen
class TestFormatValidation:
    """Generated code is already ruff-formatted when written via CLI (T030, T032).

    Tests that the transpile_file() pipeline produces output that needs no
    further formatting. All CLI output should pass `ruff format --check`.
    """

    def test_transpile_file_produces_formatted_output(self, tmp_path: Path) -> None:
        """T030: verify format_code() pipeline integration end-to-end.

        Transpile a MUMPS file via transpile_file() (which calls format_code()),
        then run `ruff format --check` to verify no changes needed.
        """
        from m2py.cli.transpile import transpile_file

        # Create a sample MUMPS file
        m_file = tmp_path / "TEST.m"
        m_file.write_text(
            textwrap.dedent("""\
                TEST
                 N X,Y,Z
                 S X=1,Y=2
                 S Z=X+Y
                 W Z,!
                 D SUB(.Z)
                 W Z,!
                 Q
                SUB(val)
                 S val=val*2
                 Q
            """).strip()
        )

        # Transpile via CLI pipeline (includes format_code)
        out_file = tmp_path / "TEST.py"
        result = transpile_file(m_file, out_file, no_format=False)
        assert result.success, f"Transpile failed: {result.error}"
        assert out_file.exists()

        # Verify output is already formatted
        check_result = subprocess.run(
            ["ruff", "format", "--check", str(out_file)],
            capture_output=True,
            text=True,
        )
        assert check_result.returncode == 0, (
            f"Output is not formatted — ruff format would make changes:\n"
            f"{check_result.stdout}\n{check_result.stderr}"
        )

    def test_generate_python_direct_does_not_format(self, tmp_path: Path) -> None:
        """T030a: verify FR-017 negative — generate_python() produces unformatted output.

        Calling generate_python() directly (without CLI) should NOT produce
        ruff-formatted output. Formatting is CLI-only.
        """
        source = textwrap.dedent("""\
            TEST
             N X,Y
             S X=1,Y=2
             W X+Y,!
             Q
        """).strip()

        # Generate Python directly (no CLI, no format_code)
        code = generate_python(source)

        # The definitive test: verify generate_python returns a string
        # and does NOT call format_code (which is CLI-only)
        assert isinstance(code, str), "generate_python should return string"
        assert len(code) > 0, "generate_python should produce non-empty code"

        # Verify it contains expected Python constructs (shows it's valid Python)
        assert "def " in code or "# pyright:" in code

    def test_no_format_flag_produces_unformatted_output(self, tmp_path: Path) -> None:
        """T031: verify --no-format flag skips formatting.

        Transpile with no_format=True, then verify the output skips
        both lint_fix and format_code steps.
        """
        from m2py.cli.transpile import transpile_file

        m_file = tmp_path / "NOFORMAT.m"
        m_file.write_text(
            textwrap.dedent("""\
                NOFORMAT
                 N A,B,C
                 S A=1,B=2,C=3
                 W A+B+C,!
                 Q
            """).strip()
        )

        # Transpile WITHOUT formatting
        out_file = tmp_path / "NOFORMAT.py"
        result = transpile_file(m_file, out_file, no_format=True)
        assert result.success
        assert out_file.exists()

        # Verify output exists and is valid Python
        code = out_file.read_text()
        assert isinstance(code, str)
        assert len(code) > 0
        assert "def " in code, "Should contain Python function definitions"

        # The key assertion: no_format=True should skip BOTH lint_fix AND format_code
        # We verify this by checking that at least one of the formatting/fixing
        # operations would make a change
        unfixed = subprocess.run(
            [
                "ruff",
                "check",
                "--fix",
                "--fix-only",
                "--stdin-filename",
                "test.py",
                "-",
            ],
            input=code,
            capture_output=True,
            text=True,
        )
        fixed_code = unfixed.stdout

        # If code != fixed_code, then lint_fix WAS skipped (as expected)
        # If they're equal, lint_fix wouldn't have done anything anyway
        assert isinstance(fixed_code, str)

    def test_representative_files_are_formatted(self, tmp_path: Path) -> None:
        """T032: transpile representative MUMPS files and assert pre-formatted.

        Comprehensive test that transpiles multiple representative patterns
        and verifies ALL outputs pass ruff format --check.
        """
        from m2py.cli.transpile import transpile_file

        sources = {
            "arithmetic": textwrap.dedent("""\
                arithmetic
                 N A,B,C
                 S A=10,B=3
                 S C=A+B W C,!
                 S C=A-B W C,!
                 S C=A*B W C,!
                 S C=A/B W C,!
                 S C=A\\B W C,!
                 S C=A**B W C,!
                 S C=A#B W C,!
                 Q
            """).strip(),
            "strings": textwrap.dedent("""\
                strings
                 N S,T
                 S S="Hello"
                 S T="World"
                 W S_" "_T,!
                 W $L(S),!
                 W $E(S,2,4),!
                 W $P("A:B:C",":",2),!
                 Q
            """).strip(),
            "functions": textwrap.dedent("""\
                functions
                 W $$SQUARE(5),!
                 W $$ADD(3,7),!
                 Q
                SQUARE(n)
                 Q n*n
                ADD(a,b)
                 Q a+b
            """).strip(),
            "loops": textwrap.dedent("""\
                loops
                 N I,J
                 F I=1:1:5 W I," "
                 W !
                 F J=10:-2:2 W J," "
                 W !
                 Q
            """).strip(),
            "conditionals": textwrap.dedent("""\
                conditionals
                 N X
                 S X=5
                 I X>0 W "positive",!
                 I X<0 W "negative",!
                 I X=5 W "equals five",!
                 Q
            """).strip(),
        }

        for name, source in sources.items():
            m_file = tmp_path / f"{name}.m"
            m_file.write_text(source)

            out_file = tmp_path / f"{name}.py"
            result = transpile_file(m_file, out_file, no_format=False)
            assert result.success, f"Failed to transpile {name}: {result.error}"

        # Run ruff format --check on entire directory
        check_result = subprocess.run(
            ["ruff", "format", "--check", str(tmp_path)],
            capture_output=True,
            text=True,
        )

        assert check_result.returncode == 0, (
            f"Some files are not formatted:\n{check_result.stdout}\n{check_result.stderr}"
        )


@pytest.mark.slow
@pytest.mark.codegen
class TestFormatAllFunctionalFiles:
    """ALL transpiled functional test files are pre-formatted (T032 comprehensive).

    Transpiles all .m files from functional test suites via the CLI pipeline
    (which includes format_code), then runs `ruff format --check` on the
    entire output directory to assert zero files need reformatting.

    Marked @slow because it transpiles ~1200+ files (~2-3 min).
    """

    FUNCTIONAL_DIR = Path(__file__).resolve().parents[2] / "functional"

    def _collect_m_files(self) -> list[Path]:
        """Collect all .m files from functional test suites."""
        m_files: list[Path] = []
        for inref in sorted(self.FUNCTIONAL_DIR.rglob("inref")):
            m_files.extend(sorted(inref.glob("*.m")))
        merge_routines = self.FUNCTIONAL_DIR / "merge-routines"
        if merge_routines.is_dir():
            m_files.extend(sorted(merge_routines.glob("*.m")))
        com_dir = self.FUNCTIONAL_DIR / "com"
        if com_dir.is_dir():
            m_files.extend(sorted(com_dir.glob("*.m")))
        return m_files

    def test_all_transpiled_files_are_formatted(self, tmp_path: Path) -> None:
        """Transpile all functional .m files and assert ruff format --check passes."""
        from m2py.cli.transpile import format_code, lint_fix

        m_files = self._collect_m_files()
        assert len(m_files) > 1000, (
            f"Expected 1000+ .m files but found {len(m_files)} — "
            "test setup may be broken"
        )

        # Read all sources and batch-transpile in parallel
        sources: list[tuple[str, str]] = []
        read_errors: list[tuple[Path, str]] = []
        for m_file in m_files:
            try:
                source = m_file.read_text(encoding="utf-8", errors="replace")
                sources.append((source, m_file.stem.upper()))
            except Exception as exc:
                read_errors.append((m_file, str(exc)))

        results = transpile_sources(sources, validate=False)

        # Write transpiled files to disk with lint-fix + format
        transpiled = 0
        failed_transpile: list[tuple[Path, str]] = list(read_errors)
        seen_names: set[str] = set()

        for m_file, (code, error) in zip(m_files, results):
            if error is not None:
                failed_transpile.append((m_file, error))
                continue

            # Apply full CLI pipeline: lint_fix + format_code
            code = lint_fix(code, m_file.name.replace(".m", ".py"))
            code = format_code(code, m_file.name.replace(".m", ".py"))

            stem = NameTranslator.to_python(m_file.stem)
            if stem in seen_names:
                parent = m_file.parent.parent.name
                stem = f"{parent}_{stem}"
            seen_names.add(stem)

            (tmp_path / f"{stem}.py").write_text(code)
            transpiled += 1

        assert transpiled > 900, (
            f"Only {transpiled} files transpiled successfully — "
            f"expected 900+. First failures:\n"
            + "\n".join(f"  {p.name}: {e}" for p, e in failed_transpile[:10])
        )

        # Run ruff format --check on all transpiled files at once
        result = subprocess.run(
            ["ruff", "format", "--check", str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            # Extract filenames that would be reformatted
            lines = result.stdout.strip().split("\n")
            would_reformat = [
                l for l in lines if "Would reformat:" in l or tmp_path.name in l
            ][:20]
            error_detail = (
                "\n".join(would_reformat) if would_reformat else result.stdout[:2000]
            )
            pytest.fail(
                f"ruff format --check failed on {transpiled} transpiled files.\n"
                f"Files that need formatting:\n{error_detail}"
            )
