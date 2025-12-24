#!/usr/bin/env python3
"""VistA-M Codebase Evaluation Script.

This script evaluates the M2PY parser against the VistA-M codebase to:
1. Identify files that fail to parse into an ASG
2. Identify files that may parse incorrectly (unknown features/functions)
3. Find complex files for manual validation

Usage:
    uv run python utils/evaluate_vista.py [--limit N] [--package NAME] [--verbose]
    uv run python utils/evaluate_vista.py --sample  # Quick sample run
    uv run python utils/evaluate_vista.py --report  # Generate full report
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from m2py.parser.parser import MUMPSParser
from m2py.asg.elements import MRoutine
from m2py.asg.statements import (
    MSetStatement,
    MGotoStatement,
    MForStatement,
    MIfStatement,
    MElseStatement,
    MXecuteStatement,
    MDoBlockStatement,
)
from m2py.asg.expressions import (
    MIntrinsicFunction,
    MExtrinsicFunction,
    MVariable,
    MGlobal,
    MSpecialVariable,
    MIndirection,
    MBinaryOp,
    MUnaryOp,
    MPatternMatch,
)
from m2py.asg.enums import GotoType


VISTA_ROOT = Path(__file__).parent.parent / "VistA-M"
REPORTS_DIR = Path(__file__).parent.parent / "reports" / "vista-evaluation"


@dataclass
class FileMetrics:
    """Metrics captured for a single file."""

    filepath: str
    package: str
    parsed: bool = False
    error_message: str = ""
    error_type: str = ""

    # Structural metrics
    label_count: int = 0
    statement_count: int = 0
    source_lines: int = 0

    # Statement type counts
    statement_types: dict = field(default_factory=dict)

    # Feature usage
    intrinsic_functions: set = field(default_factory=set)
    extrinsic_functions: set = field(default_factory=set)
    special_variables: set = field(default_factory=set)

    # Complexity indicators
    goto_count: int = 0
    for_loop_count: int = 0
    nested_for_count: int = 0
    xecute_count: int = 0
    indirection_count: int = 0
    pattern_match_count: int = 0

    # Flow control complexity
    max_nesting_depth: int = 0
    backward_goto_count: int = 0
    cross_label_goto_count: int = 0

    # Potential issues
    unknown_commands: set = field(default_factory=set)
    unknown_functions: set = field(default_factory=set)

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        d = asdict(self)
        # Convert sets to sorted lists
        for key in [
            "intrinsic_functions",
            "extrinsic_functions",
            "special_variables",
            "unknown_commands",
            "unknown_functions",
        ]:
            d[key] = sorted(list(d[key]))
        return d


@dataclass
class EvaluationResults:
    """Aggregated results from evaluation run."""

    timestamp: str = ""
    total_files: int = 0
    parsed_successfully: int = 0
    parse_failures: int = 0

    # Error categorization
    errors_by_type: dict = field(default_factory=dict)

    # Feature usage aggregates
    intrinsic_function_usage: dict = field(default_factory=dict)
    extrinsic_function_usage: dict = field(default_factory=dict)
    special_variable_usage: dict = field(default_factory=dict)
    statement_type_totals: dict = field(default_factory=dict)

    # Unknown features (potential parsing issues)
    unknown_commands: dict = field(default_factory=dict)
    unknown_functions: dict = field(default_factory=dict)

    # Complexity rankings
    most_complex_files: list = field(default_factory=list)
    files_with_nested_for: list = field(default_factory=list)
    files_with_backward_goto: list = field(default_factory=list)
    files_with_xecute: list = field(default_factory=list)
    files_with_indirection: list = field(default_factory=list)

    # Failed files
    failed_files: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# Known intrinsic functions (from MUMPS standard)
KNOWN_INTRINSICS = {
    "$ASCII",
    "$A",
    "$CHAR",
    "$C",
    "$DATA",
    "$D",
    "$EXTRACT",
    "$E",
    "$FIND",
    "$F",
    "$FNUMBER",
    "$FN",
    "$GET",
    "$G",
    "$JUSTIFY",
    "$J",
    "$LENGTH",
    "$L",
    "$NAME",
    "$NA",
    "$NEXT",
    "$N",
    "$ORDER",
    "$O",
    "$PIECE",
    "$P",
    "$QLENGTH",
    "$QL",
    "$QSUBSCRIPT",
    "$QS",
    "$QUERY",
    "$Q",
    "$RANDOM",
    "$R",
    "$REVERSE",
    "$RE",
    "$SELECT",
    "$S",
    "$STACK",
    "$ST",
    "$TEXT",
    "$T",
    "$TRANSLATE",
    "$TR",
    "$VIEW",
    "$V",
    # Additional common ones
    "$ZBITAND",
    "$ZBITCOUNT",
    "$ZBITFIND",
    "$ZBITGET",
    "$ZBITNOT",
    "$ZBITOR",
    "$ZBITSET",
    "$ZBITSTR",
    "$ZBITXOR",
    "$ZCONVERT",
    "$ZCVT",
    "$ZDATE",
    "$ZD",
    "$ZDATEH",
    "$ZDH",
    "$ZHEX",
    "$ZH",
    "$ZLENGTH",
    "$ZL",
    "$ZPIECE",
    "$ZP",
    "$ZSEARCH",
    "$ZSORT",
    "$ZSTRIP",
    "$ZTIME",
    "$ZT",
    "$ZTIMEH",
    "$ZTH",
    "$ZWIDTH",
    "$ZW",
    # More Z functions
    "$ZBOOLEAN",
    "$ZCRC",
    "$ZINCREMENT",
    "$ZINCRMT",
    "$ZSOCKET",
    "$ZSUBSTR",
    "$ZTRNLNM",
    "$ZZWRITE",
    # Standard abbreviations
    "$ZCRC",
    "$ZCR",
}

# Known special variables
KNOWN_SPECIAL_VARS = {
    "$DEVICE",
    "$D",
    "$ECODE",
    "$EC",
    "$ESTACK",
    "$ES",
    "$ETRAP",
    "$ET",
    "$HOROLOG",
    "$H",
    "$IO",
    "$I",
    "$JOB",
    "$J",
    "$KEY",
    "$K",
    "$PRINCIPAL",
    "$P",
    "$QUIT",
    "$Q",
    "$REFERENCE",
    "$R",
    "$STACK",
    "$ST",
    "$STORAGE",
    "$S",
    "$SYSTEM",
    "$SY",
    "$TEST",
    "$T",
    "$TLEVEL",
    "$TL",
    "$TRESTART",
    "$TR",
    "$X",
    "$Y",
    "$ZA",
    "$ZB",
    "$ZCMDLINE",
    "$ZDEVICE",
    "$ZDIRECTORY",
    "$ZEESSION",
    "$ZERROR",
    "$ZE",
    "$ZGBLDIR",
    "$ZHOROLOG",
    "$ZH",
    "$ZINTERRUPT",
    "$ZIO",
    "$ZJOB",
    "$ZJ",
    "$ZKEY",
    "$ZK",
    "$ZLEVEL",
    "$ZL",
    "$ZMAXTPTIME",
    "$ZMODE",
    "$ZM",
    "$ZNAME",
    "$ZN",
    "$ZPATNUMERIC",
    "$ZPN",
    "$ZPOSITION",
    "$ZPOS",
    "$ZPROMPT",
    "$ZPR",
    "$ZREFERENCE",
    "$ZR",
    "$ZROUTINES",
    "$ZRO",
    "$ZSOURCE",
    "$ZS",
    "$ZSTATUS",
    "$ZST",
    "$ZSYSTEM",
    "$ZSYS",
    "$ZTDATA",
    "$ZTIMEOUT",
    "$ZTLEVEL",
    "$ZTOLDVAL",
    "$ZTRAP",
    "$ZTSTEP",
    "$ZTVALUE",
    "$ZUSEDSTOR",
    "$ZVERSION",
    "$ZV",
    "$ZYERROR",
}


def find_vista_files(
    package_filter: Optional[str] = None, limit: Optional[int] = None
) -> list[Path]:
    """Find all MUMPS files in VistA-M."""
    if not VISTA_ROOT.exists():
        raise FileNotFoundError(f"VistA-M not found at {VISTA_ROOT}")

    files = []
    for m_file in VISTA_ROOT.rglob("*.m"):
        # Skip if package filter specified
        if package_filter:
            if package_filter.lower() not in str(m_file.parent).lower():
                continue
        files.append(m_file)
        if limit and len(files) >= limit:
            break

    return sorted(files)


def get_package_name(filepath: Path) -> str:
    """Extract package name from file path."""
    rel = filepath.relative_to(VISTA_ROOT)
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "Packages":
        return parts[1]
    return "Unknown"


def count_source_lines(filepath: Path) -> int:
    """Count non-comment, non-empty source lines."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
        count = 0
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped and not stripped.startswith(";"):
                count += 1
        return count
    except Exception:
        return 0


def analyze_asg(routine: MRoutine, metrics: FileMetrics) -> None:
    """Analyze ASG structure and collect metrics."""
    metrics.label_count = len(routine.labels)

    def walk_statements(scope, depth=0):
        """Recursively walk all statements."""
        if not scope or not hasattr(scope, "statements"):
            return

        metrics.max_nesting_depth = max(metrics.max_nesting_depth, depth)

        for stmt in scope.statements:
            metrics.statement_count += 1
            stmt_type = stmt.__class__.__name__
            metrics.statement_types[stmt_type] = (
                metrics.statement_types.get(stmt_type, 0) + 1
            )

            # Analyze specific statement types
            if isinstance(stmt, MForStatement):
                metrics.for_loop_count += 1
                if depth > 0:
                    metrics.nested_for_count += 1
                if stmt.body:
                    walk_statements(stmt.body, depth + 1)

            elif isinstance(stmt, MGotoStatement):
                metrics.goto_count += 1
                if hasattr(stmt, "goto_type"):
                    if stmt.goto_type == GotoType.BACKWARD_JUMP:
                        metrics.backward_goto_count += 1
                    elif stmt.goto_type == GotoType.CROSS_LABEL:
                        metrics.cross_label_goto_count += 1

            elif isinstance(stmt, MXecuteStatement):
                metrics.xecute_count += 1

            elif isinstance(stmt, MIfStatement):
                if stmt.then_scope:
                    walk_statements(stmt.then_scope, depth + 1)

            elif isinstance(stmt, MElseStatement):
                if stmt.body:
                    walk_statements(stmt.body, depth + 1)

            elif isinstance(stmt, MDoBlockStatement):
                if stmt.body:
                    walk_statements(stmt.body, depth + 1)

            # Analyze expressions in statement
            analyze_expressions_in_stmt(stmt, metrics)

    for label in routine.labels:
        if label.body:
            walk_statements(label.body, 0)


def analyze_expressions_in_stmt(stmt: Any, metrics: FileMetrics) -> None:
    """Analyze expressions within a statement."""

    def walk_expr(expr):
        if expr is None:
            return

        if isinstance(expr, MIntrinsicFunction):
            func_name = expr.name.upper() if hasattr(expr, "name") else str(expr)
            # Store with $ prefix for consistency
            func_name_with_prefix = (
                f"${func_name}" if not func_name.startswith("$") else func_name
            )
            metrics.intrinsic_functions.add(func_name_with_prefix)
            # Check if unknown (need to compare with $ prefix)
            if (
                func_name_with_prefix.upper() not in KNOWN_INTRINSICS
                and not func_name_with_prefix.upper().startswith("$Z")
            ):
                metrics.unknown_functions.add(func_name_with_prefix)
            # Walk arguments
            if hasattr(expr, "arguments"):
                for arg in expr.arguments or []:
                    walk_expr(arg)

        elif isinstance(expr, MExtrinsicFunction):
            func_name = f"$${expr.name}" if hasattr(expr, "name") else str(expr)
            metrics.extrinsic_functions.add(func_name)

        elif isinstance(expr, MSpecialVariable):
            var_name = expr.name.upper() if hasattr(expr, "name") else str(expr)
            metrics.special_variables.add(var_name)

        elif isinstance(expr, MIndirection):
            metrics.indirection_count += 1
            if hasattr(expr, "base"):
                walk_expr(expr.base)

        elif isinstance(expr, MPatternMatch):
            metrics.pattern_match_count += 1

        elif isinstance(expr, MBinaryOp):
            walk_expr(expr.left)
            walk_expr(expr.right)

        elif isinstance(expr, MUnaryOp):
            walk_expr(expr.operand)

        elif isinstance(expr, (MVariable, MGlobal)):
            if hasattr(expr, "subscripts"):
                for sub in expr.subscripts or []:
                    walk_expr(sub)

        elif isinstance(expr, list):
            for item in expr:
                walk_expr(item)

    # Walk all expression-containing attributes
    for attr in [
        "condition",
        "value",
        "arguments",
        "targets",
        "postcondition",
        "device_expr",
        "timeout",
        "parameters",
        "expressions",
    ]:
        if hasattr(stmt, attr):
            val = getattr(stmt, attr)
            walk_expr(val)

    # Special handling for assignments
    if isinstance(stmt, MSetStatement) and hasattr(stmt, "assignments"):
        for assign in stmt.assignments or []:
            if hasattr(assign, "target"):
                walk_expr(assign.target)
            if hasattr(assign, "value"):
                walk_expr(assign.value)


def calculate_complexity_score(metrics: FileMetrics) -> float:
    """Calculate a complexity score for ranking files."""
    score = 0.0
    score += metrics.goto_count * 2
    score += metrics.backward_goto_count * 5
    score += metrics.for_loop_count * 1.5
    score += metrics.nested_for_count * 3
    score += metrics.xecute_count * 4
    score += metrics.indirection_count * 3
    score += metrics.max_nesting_depth * 2
    score += metrics.label_count * 0.5
    return score


def evaluate_file(
    filepath: Path, parser: MUMPSParser, verbose: bool = False
) -> FileMetrics:
    """Evaluate a single MUMPS file."""
    metrics = FileMetrics(
        filepath=str(filepath),
        package=get_package_name(filepath),
    )
    metrics.source_lines = count_source_lines(filepath)

    try:
        routine = parser.parse_file(filepath)
        parser.resolve_references(routine)
        # Note: classify_patterns expects source string, not MRoutine
        # Skip for now - the ASG analysis already captures what we need

        metrics.parsed = True
        analyze_asg(routine, metrics)

        if verbose:
            print(
                f"✓ {filepath.name}: {metrics.label_count} labels, {metrics.statement_count} stmts"
            )

    except Exception as e:
        metrics.parsed = False
        metrics.error_type = type(e).__name__
        metrics.error_message = str(e)[:500]

        if verbose:
            print(f"✗ {filepath.name}: {metrics.error_type}: {str(e)[:100]}")

    return metrics


def run_evaluation(
    package_filter: Optional[str] = None,
    limit: Optional[int] = None,
    verbose: bool = False,
    sample: bool = False,
) -> EvaluationResults:
    """Run full evaluation across VistA-M files."""

    if sample:
        limit = 100
        print("Running sample evaluation (100 files)...")

    results = EvaluationResults(
        timestamp=datetime.now().isoformat(),
    )

    files = find_vista_files(package_filter, limit)
    results.total_files = len(files)

    print(f"Found {len(files)} MUMPS files to evaluate")

    parser = MUMPSParser()
    all_metrics = []

    for i, filepath in enumerate(files):
        if i > 0 and i % 500 == 0:
            print(f"Progress: {i}/{len(files)} ({100 * i // len(files)}%)")

        metrics = evaluate_file(filepath, parser, verbose)
        all_metrics.append(metrics)

        if metrics.parsed:
            results.parsed_successfully += 1

            # Aggregate intrinsic functions
            for func in metrics.intrinsic_functions:
                results.intrinsic_function_usage[func] = (
                    results.intrinsic_function_usage.get(func, 0) + 1
                )

            # Aggregate extrinsic functions
            for func in metrics.extrinsic_functions:
                results.extrinsic_function_usage[func] = (
                    results.extrinsic_function_usage.get(func, 0) + 1
                )

            # Aggregate special variables
            for var in metrics.special_variables:
                results.special_variable_usage[var] = (
                    results.special_variable_usage.get(var, 0) + 1
                )

            # Aggregate statement types
            for stmt_type, count in metrics.statement_types.items():
                results.statement_type_totals[stmt_type] = (
                    results.statement_type_totals.get(stmt_type, 0) + count
                )

            # Aggregate unknowns
            for cmd in metrics.unknown_commands:
                results.unknown_commands[cmd] = results.unknown_commands.get(cmd, 0) + 1
            for func in metrics.unknown_functions:
                results.unknown_functions[func] = (
                    results.unknown_functions.get(func, 0) + 1
                )

        else:
            results.parse_failures += 1
            results.errors_by_type[metrics.error_type] = (
                results.errors_by_type.get(metrics.error_type, 0) + 1
            )
            results.failed_files.append(
                {
                    "file": str(filepath),
                    "package": metrics.package,
                    "error_type": metrics.error_type,
                    "error": metrics.error_message,
                }
            )

    # Rank files by complexity
    successful_metrics = [m for m in all_metrics if m.parsed]

    # Most complex files
    for m in successful_metrics:
        m._complexity = calculate_complexity_score(m)
    successful_metrics.sort(key=lambda m: m._complexity, reverse=True)
    results.most_complex_files = [
        {
            "file": m.filepath,
            "package": m.package,
            "score": m._complexity,
            "gotos": m.goto_count,
            "fors": m.for_loop_count,
            "nested_for": m.nested_for_count,
            "xecute": m.xecute_count,
            "indirection": m.indirection_count,
        }
        for m in successful_metrics[:100]
    ]

    # Files with nested FOR loops
    results.files_with_nested_for = [
        {"file": m.filepath, "package": m.package, "count": m.nested_for_count}
        for m in successful_metrics
        if m.nested_for_count > 0
    ][:50]

    # Files with backward GOTOs
    results.files_with_backward_goto = [
        {"file": m.filepath, "package": m.package, "count": m.backward_goto_count}
        for m in successful_metrics
        if m.backward_goto_count > 0
    ][:50]

    # Files with XECUTE
    results.files_with_xecute = [
        {"file": m.filepath, "package": m.package, "count": m.xecute_count}
        for m in successful_metrics
        if m.xecute_count > 0
    ][:50]

    # Files with indirection
    results.files_with_indirection = [
        {"file": m.filepath, "package": m.package, "count": m.indirection_count}
        for m in successful_metrics
        if m.indirection_count > 0
    ][:50]

    return results


def print_summary(results: EvaluationResults) -> None:
    """Print a summary of evaluation results."""
    print("\n" + "=" * 80)
    print("VISTA-M PARSER EVALUATION SUMMARY")
    print("=" * 80)

    print(f"\nTotal files evaluated: {results.total_files}")
    print(
        f"Successfully parsed:   {results.parsed_successfully} ({100 * results.parsed_successfully // results.total_files}%)"
    )
    print(
        f"Parse failures:        {results.parse_failures} ({100 * results.parse_failures // results.total_files}%)"
    )

    if results.errors_by_type:
        print("\n--- Errors by Type ---")
        for error_type, count in sorted(
            results.errors_by_type.items(), key=lambda x: -x[1]
        ):
            print(f"  {error_type}: {count}")

    if results.statement_type_totals:
        print("\n--- Statement Types ---")
        for stmt_type, count in sorted(
            results.statement_type_totals.items(), key=lambda x: -x[1]
        )[:20]:
            print(f"  {stmt_type}: {count:,}")

    if results.intrinsic_function_usage:
        print("\n--- Top Intrinsic Functions ---")
        for func, count in sorted(
            results.intrinsic_function_usage.items(), key=lambda x: -x[1]
        )[:15]:
            print(f"  {func}: {count:,}")

    if results.special_variable_usage:
        print("\n--- Top Special Variables ---")
        for var, count in sorted(
            results.special_variable_usage.items(), key=lambda x: -x[1]
        )[:15]:
            print(f"  {var}: {count:,}")

    if results.unknown_functions:
        print("\n--- Unknown Functions (potential issues) ---")
        for func, count in sorted(
            results.unknown_functions.items(), key=lambda x: -x[1]
        )[:20]:
            print(f"  {func}: {count}")

    if results.most_complex_files:
        print("\n--- Most Complex Files (top 20) ---")
        for i, f in enumerate(results.most_complex_files[:20], 1):
            print(
                f"  {i:2}. {Path(f['file']).name}: score={f['score']:.1f} "
                f"(goto={f['gotos']}, for={f['fors']}, nested={f['nested_for']}, xecute={f['xecute']})"
            )

    if results.failed_files:
        print("\n--- Sample Failed Files (first 10) ---")
        for f in results.failed_files[:10]:
            print(f"  {Path(f['file']).name}: {f['error_type']}")
            print(f"    {f['error'][:100]}")


def save_report(results: EvaluationResults, name: str = "evaluation") -> Path:
    """Save evaluation results to JSON file."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORTS_DIR / f"{name}_{timestamp}.json"

    with open(report_path, "w") as f:
        json.dump(results.to_dict(), f, indent=2, default=str)

    print(f"\nReport saved to: {report_path}")
    return report_path


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate M2PY parser against VistA-M codebase"
    )
    parser.add_argument("--limit", type=int, help="Limit number of files to evaluate")
    parser.add_argument("--package", type=str, help="Filter to specific package name")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--sample", action="store_true", help="Quick sample run (100 files)"
    )
    parser.add_argument(
        "--report", action="store_true", help="Generate full report and save"
    )
    parser.add_argument(
        "--no-save", action="store_true", help="Don't save report to file"
    )

    args = parser.parse_args()

    results = run_evaluation(
        package_filter=args.package,
        limit=args.limit,
        verbose=args.verbose,
        sample=args.sample,
    )

    print_summary(results)

    if args.report or not args.no_save:
        save_report(results, "vista_evaluation")


if __name__ == "__main__":
    main()
