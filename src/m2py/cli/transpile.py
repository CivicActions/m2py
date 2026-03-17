"""Transpile pipeline for converting MUMPS files to Python.

Provides the core transpilation logic:
- lint_fix: Post-generation ruff lint fixing (unused import removal)
- format_code: Post-generation ruff formatting
- TranspileResult / TranspileSummary: Result dataclasses
- transpile_file: Single-file transpilation pipeline
- transpile_sources: Parallel batch transpilation of MUMPS sources
- transpile_paths: Batch transpilation with directory support
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Sequence

from m2py.codegen import generate_python


# =============================================================================
# Result Dataclasses
# =============================================================================


@dataclass
class TranspileResult:
    """Result of transpiling a single MUMPS file.

    Attributes:
        input_path: Absolute path to source .m file
        output_path: Absolute path to written .py file, or None on failure
        success: Whether transpilation succeeded
        error: Error message if success is False
        routine_name: Derived routine name (stem of input file, uppercased)
    """

    input_path: Path
    output_path: Optional[Path]
    success: bool
    error: Optional[str]
    routine_name: str

    def __post_init__(self) -> None:
        # Enforce invariants
        if self.success and self.output_path is None:
            raise ValueError("output_path must be set when success is True")
        if not self.success and self.error is None:
            raise ValueError("error must be set when success is False")


@dataclass
class TranspileSummary:
    """Aggregate result of transpiling multiple files.

    Attributes:
        results: All individual file results
        total: Total files attempted
        succeeded: Count of successful transpilations
        failed: Count of failures
    """

    results: list[TranspileResult] = field(default_factory=list)
    total: int = 0
    succeeded: int = 0
    failed: int = 0

    @property
    def all_ok(self) -> bool:
        """True if no files failed."""
        return self.failed == 0


# =============================================================================
# Ruff Integration Helpers
# =============================================================================


def lint_fix(source: str, filename: str) -> str:
    """Run ruff check --fix on source code via stdin pipe.

    Removes unused imports (F401) and fixes other auto-fixable lint issues.

    Args:
        source: Python source code
        filename: Filename hint for ruff (for config resolution)

    Returns:
        Fixed source code. Returns original source on any ruff error.
    """
    try:
        result = subprocess.run(
            ["ruff", "check", "--fix", "--fix-only", "--stdin-filename", filename, "-"],
            input=source,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
        # Non-zero exit but may still have produced partial output
        # (unfixable issues logged but not fatal)
        if result.stdout:
            return result.stdout
        return source
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        print(f"WARNING: ruff check failed: {e}", file=sys.stderr)
        return source


def format_code(source: str, filename: str) -> str:
    """Run ruff format on source code via stdin pipe.

    Normalizes formatting to ruff's standard style.

    Args:
        source: Python source code
        filename: Filename hint for ruff

    Returns:
        Formatted source code. Returns original source on any ruff error.
    """
    try:
        result = subprocess.run(
            ["ruff", "format", "--stdin-filename", filename, "-"],
            input=source,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
        return source
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
        print(f"WARNING: ruff format failed: {e}", file=sys.stderr)
        return source


# =============================================================================
# Reserved Word Detection
# =============================================================================

# Python reserved words and common built-in module names that would conflict
_PYTHON_RESERVED = frozenset(
    {
        # Keywords
        "False",
        "None",
        "True",
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
        # Common built-in modules that could conflict
        "os",
        "sys",
        "io",
        "re",
        "abc",
        "ast",
        "copy",
        "math",
        "json",
        "time",
        "types",
        "string",
        "decimal",
    }
)


def _safe_output_name(stem: str) -> str:
    """Adjust output filename if it conflicts with Python reserved words.

    MUMPS files like IF.m, FOR.m would produce if.py, for.py which
    conflict with Python keywords. Appends underscore to avoid this.

    Args:
        stem: The file stem (without extension), lowercased

    Returns:
        Safe filename stem (may have _ appended)
    """
    lower = stem.lower()
    if lower in {kw.lower() for kw in _PYTHON_RESERVED}:
        return f"{stem}_"
    return stem


# =============================================================================
# Parallel Batch Transpilation
# =============================================================================


def _transpile_one(args: tuple[str, str, bool]) -> tuple[str, str | None]:
    """Worker function for parallel transpilation.

    Must be a top-level function (not a lambda or closure) so it can be
    pickled for use with ProcessPoolExecutor.

    Args:
        args: Tuple of (source_code, routine_name, validate)

    Returns:
        Tuple of (python_code, error_message_or_none)
    """
    source, routine_name, validate = args
    try:
        code = generate_python(source, routine_name=routine_name, validate=validate)
        return (code, None)
    except Exception as e:
        return ("", f"{type(e).__name__}: {e}")


def _transpile_one_with_warnings(
    args: tuple[str, str, bool],
) -> tuple[str, str | None, list[str]]:
    """Worker function for parallel transpilation with warning capture.

    Like _transpile_one but also captures and returns warnings emitted
    during transpilation.

    Args:
        args: Tuple of (source_code, routine_name, validate)

    Returns:
        Tuple of (python_code, error_message_or_none, list_of_warning_messages)
    """
    import warnings

    source, routine_name, validate = args
    captured_warnings: list[str] = []

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            code = generate_python(source, routine_name=routine_name, validate=validate)
            error = None
        except Exception as e:
            code = ""
            error = f"{type(e).__name__}: {e}"

    # Extract warning messages
    for w in caught:
        captured_warnings.append(str(w.message))

    return (code, error, captured_warnings)


def transpile_sources(
    items: Sequence[tuple[str, str]],
    *,
    max_workers: int | None = None,
    validate: bool = True,
) -> list[tuple[str, str | None]]:
    """Transpile multiple MUMPS sources in parallel.

    Uses ProcessPoolExecutor to distribute CPU-bound transpilation across
    multiple cores. Falls back to sequential execution for small batches.

    Args:
        items: Sequence of (source_code, routine_name) tuples
        max_workers: Maximum parallel workers (default: CPU count).
            Pass 1 to force sequential execution.
        validate: Whether to validate generated Python with ast.parse()

    Returns:
        List of (python_code, error_or_none) in same order as input.
        If error is not None, transpilation failed for that item.

    Example:
        >>> results = transpile_sources([
        ...     ('TEST W "Hello" Q', "TEST"),
        ...     ('ADD(A,B) Q A+B', "ADD"),
        ... ])
        >>> for code, err in results:
        ...     if err:
        ...         print(f"Failed: {err}")
        ...     else:
        ...         print(f"OK: {len(code)} chars")
    """
    if not items:
        return []

    args_list = [(src, name, validate) for src, name in items]

    # Sequential for small batches or when max_workers=1
    if len(items) <= 4 or max_workers == 1:
        return [_transpile_one(a) for a in args_list]

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(_transpile_one, args_list))


def transpile_sources_with_warnings(
    items: Sequence[tuple[str, str]],
    *,
    max_workers: int | None = None,
    validate: bool = True,
) -> list[tuple[str, str | None, list[str]]]:
    """Transpile multiple MUMPS sources in parallel, capturing warnings.

    Like transpile_sources but also captures and returns warnings emitted
    during each transpilation. Warnings are captured per-routine in each
    worker process and returned to the caller.

    Args:
        items: Sequence of (source_code, routine_name) tuples
        max_workers: Maximum parallel workers (default: CPU count).
        validate: Whether to validate generated Python with ast.parse()

    Returns:
        List of (python_code, error_or_none, warnings_list) in same order as input.
    """
    if not items:
        return []

    args_list = [(src, name, validate) for src, name in items]

    # Sequential for small batches or when max_workers=1
    if len(items) <= 4 or max_workers == 1:
        return [_transpile_one_with_warnings(a) for a in args_list]

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(_transpile_one_with_warnings, args_list))


# =============================================================================
# Core Transpilation
# =============================================================================


def transpile_file(
    input_path: Path,
    output_path: Path,
    *,
    no_format: bool = False,
) -> TranspileResult:
    """Transpile a single MUMPS .m file to Python.

    Pipeline: read → parse → analyze → generate → lint-fix → format → write

    Args:
        input_path: Path to source .m file
        output_path: Path to write .py output
        no_format: If True, skip ruff lint-fix and formatting

    Returns:
        TranspileResult with success/failure information
    """
    routine_name = input_path.stem.upper()

    try:
        # Read source (try UTF-8 first, fall back to Latin-1 for legacy files)
        try:
            source = input_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            source = input_path.read_text(encoding="latin-1")
    except OSError as e:
        return TranspileResult(
            input_path=input_path,
            output_path=None,
            success=False,
            error=f"Cannot read file: {e}",
            routine_name=routine_name,
        )

    try:
        # Generate Python code (includes parse + analyze + codegen)
        python_code = generate_python(source, routine_name=routine_name)
    except Exception as e:
        return TranspileResult(
            input_path=input_path,
            output_path=None,
            success=False,
            error=f"{type(e).__name__}: {e}",
            routine_name=routine_name,
        )

    # Post-gen processing (ruff lint-fix and format)
    if not no_format:
        filename = output_path.name
        python_code = lint_fix(python_code, filename)
        python_code = format_code(python_code, filename)

    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(python_code, encoding="utf-8")
    except OSError as e:
        return TranspileResult(
            input_path=input_path,
            output_path=None,
            success=False,
            error=f"Cannot write file: {e}",
            routine_name=routine_name,
        )

    return TranspileResult(
        input_path=input_path,
        output_path=output_path,
        success=True,
        error=None,
        routine_name=routine_name,
    )


def transpile_paths(
    paths: list[str],
    *,
    output_dir: Optional[str] = None,
    no_format: bool = False,
    verbose: bool = False,
    overrides_dir: Optional[str] = None,
) -> TranspileSummary:
    """Resolve paths, discover .m files, and transpile each.

    For files: transpile directly.
    For directories: recursively glob for *.m files.
    When output_dir is specified, mirror input directory structure.
    When overrides_dir is specified, .py files matching an input .m
    stem are copied to the output instead of transpiling.

    Args:
        paths: List of file/directory path strings
        output_dir: Optional output directory (mirrors input structure)
        no_format: If True, skip ruff processing
        verbose: If True, print file-by-file progress
        overrides_dir: Optional directory of .py override files

    Returns:
        TranspileSummary with aggregate results
    """
    # Discover all .m files
    m_files: list[
        tuple[Path, Path]
    ] = []  # (input_path, base_dir for relative path computation)
    not_found_results: list[TranspileResult] = []

    for path_str in paths:
        p = Path(path_str).resolve()
        if p.is_file():
            if p.suffix.lower() == ".m":
                m_files.append((p, p.parent))
            # Silently ignore non-.m files
        elif p.is_dir():
            for m_file in sorted(p.rglob("*.m")):
                # Use case-insensitive matching: also find .M files
                m_files.append((m_file, p))
        else:
            # Path doesn't exist — record as error result
            not_found_results.append(
                TranspileResult(
                    input_path=p,
                    output_path=None,
                    success=False,
                    error=f"Path not found: {path_str}",
                    routine_name=p.stem.upper(),
                )
            )
            if verbose:
                print(f"ERROR: Path not found: {path_str}", file=sys.stderr)

    if not m_files and not not_found_results:
        return TranspileSummary(results=[], total=0, succeeded=0, failed=0)

    results: list[TranspileResult] = list(not_found_results)
    out_dir = Path(output_dir).resolve() if output_dir else None

    # Index override files by upper-cased stem
    overrides: dict[str, Path] = {}
    if overrides_dir is not None:
        ov_dir = Path(overrides_dir).resolve()
        for py_file in ov_dir.glob("*.py"):
            if not py_file.name.startswith("_"):
                overrides[py_file.stem.upper()] = py_file

    # Build list of (input_path, output_path, source) for batch transpilation
    file_specs: list[tuple[Path, Path, str]] = []
    for input_path, base_dir in m_files:
        routine_name = input_path.stem.upper()
        override_py = overrides.get(routine_name)
        if override_py is not None:
            # Copy override file instead of transpiling
            o_path = _compute_output_path(input_path, base_dir, out_dir)
            try:
                o_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(override_py, o_path)
                results.append(
                    TranspileResult(
                        input_path=input_path,
                        output_path=o_path,
                        success=True,
                        error=None,
                        routine_name=routine_name,
                    )
                )
                if verbose:
                    print(
                        f"  Override: {input_path.name} → {override_py.name}",
                        file=sys.stderr,
                    )
            except OSError as e:
                results.append(
                    TranspileResult(
                        input_path=input_path,
                        output_path=None,
                        success=False,
                        error=f"Cannot copy override: {e}",
                        routine_name=routine_name,
                    )
                )
            continue
        output_path = _compute_output_path(input_path, base_dir, out_dir)
        try:
            try:
                source = input_path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                source = input_path.read_text(encoding="latin-1")
            file_specs.append((input_path, output_path, source))
        except OSError as e:
            results.append(
                TranspileResult(
                    input_path=input_path,
                    output_path=None,
                    success=False,
                    error=f"Cannot read file: {e}",
                    routine_name=input_path.stem.upper(),
                )
            )

    if verbose:
        for inp, _, _ in file_specs:
            print(f"  Transpiling: {inp}", file=sys.stderr)

    # Parallel transpilation of all sources
    items = [(src, inp.stem.upper()) for inp, _, src in file_specs]
    transpiled = transpile_sources(items)

    # Post-process results: ruff + write to disk
    for (input_path, output_path, _source), (python_code, error) in zip(
        file_specs, transpiled
    ):
        routine_name = input_path.stem.upper()
        if error is not None:
            results.append(
                TranspileResult(
                    input_path=input_path,
                    output_path=None,
                    success=False,
                    error=error,
                    routine_name=routine_name,
                )
            )
            if verbose:
                print(f"    ERROR: {error}", file=sys.stderr)
            continue

        # Post-gen processing (ruff lint-fix and format)
        if not no_format:
            filename = output_path.name
            python_code = lint_fix(python_code, filename)
            python_code = format_code(python_code, filename)

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(python_code, encoding="utf-8")
        except OSError as e:
            results.append(
                TranspileResult(
                    input_path=input_path,
                    output_path=None,
                    success=False,
                    error=f"Cannot write file: {e}",
                    routine_name=routine_name,
                )
            )
            continue

        results.append(
            TranspileResult(
                input_path=input_path,
                output_path=output_path,
                success=True,
                error=None,
                routine_name=routine_name,
            )
        )

    succeeded = sum(1 for r in results if r.success)
    failed = len(results) - succeeded

    return TranspileSummary(
        results=results,
        total=len(results),
        succeeded=succeeded,
        failed=failed,
    )


def _compute_output_path(
    input_path: Path,
    base_dir: Path,
    output_dir: Optional[Path],
) -> Path:
    """Compute the output .py path for a given input .m file.

    Args:
        input_path: Resolved path to .m file
        base_dir: Base directory for relative path computation
        output_dir: Optional output directory. If None, write alongside input.

    Returns:
        Path for the .py output file
    """
    # Get a safe output stem (avoid Python reserved words)
    stem = _safe_output_name(input_path.stem)

    if output_dir is None:
        # Write alongside input file
        return input_path.parent / f"{stem}.py"

    # Mirror input structure in output directory
    try:
        relative = input_path.parent.relative_to(base_dir)
    except ValueError:
        # input_path is not under base_dir — use flat output
        relative = Path()

    return output_dir / relative / f"{stem}.py"
