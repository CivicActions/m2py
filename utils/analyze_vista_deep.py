#!/usr/bin/env python3
"""Deep Analysis Script for VistA-M Parser Validation.

This script performs deep analysis of parsed ASGs to identify:
1. Files with unusual control flow patterns
2. Files using rarely-seen MUMPS features
3. Files that may have parsing anomalies
4. Files recommended for manual validation

Usage:
    uv run python utils/analyze_vista_deep.py --limit N
    uv run python utils/analyze_vista_deep.py --file path/to/file.m
    uv run python utils/analyze_vista_deep.py --package "Kernel"
"""

import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from m2py.parser.parser import MUMPSParser
from m2py.asg.elements import MRoutine
from m2py.asg.statements import (
    MSetStatement,
    MDoStatement,
    MGotoStatement,
    MForStatement,
    MIfStatement,
    MElseStatement,
    MXecuteStatement,
    MJobStatement,
)
from m2py.asg.expressions import (
    MIntrinsicFunction,
    MVariable,
    MGlobal,
    MIndirection,
    MBinaryOp,
    MUnaryOp,
    MNakedGlobal,
)
from m2py.asg.enums import GotoType

VISTA_ROOT = Path(__file__).parent.parent / "VistA-M"


@dataclass
class DeepAnalysisResult:
    """Results of deep analysis for a file."""

    filepath: str
    parsed: bool = False
    error_message: str = ""

    # Control flow issues
    has_unresolved_gotos: bool = False
    unresolved_goto_targets: list = field(default_factory=list)
    has_backward_gotos: bool = False
    backward_goto_count: int = 0
    has_cross_label_gotos: bool = False
    cross_label_goto_count: int = 0
    has_computed_gotos: bool = False

    # Nested complexity
    max_for_nesting: int = 0
    has_deeply_nested_for: bool = False  # > 3 levels
    has_goto_inside_for: bool = False
    goto_in_for_count: int = 0

    # Dynamic code
    xecute_count: int = 0
    indirection_count: int = 0
    has_complex_indirection: bool = False  # Nested or computed indirection

    # Special patterns
    has_argumentless_for: bool = False
    argumentless_for_count: int = 0
    has_job_command: bool = False
    has_tstart_trollback: bool = False  # Transaction processing

    # Unusual features
    unusual_intrinsics: set = field(default_factory=set)
    naked_global_count: int = 0

    # Parsing quality indicators
    empty_label_bodies: int = 0
    unrecognized_statements: int = 0

    def is_interesting(self) -> bool:
        """Return True if this file warrants manual validation."""
        return any(
            [
                self.has_unresolved_gotos,
                self.has_backward_gotos,
                self.has_cross_label_gotos,
                self.has_computed_gotos,
                self.has_deeply_nested_for,
                self.has_goto_inside_for,
                self.xecute_count > 3,
                self.has_complex_indirection,
                self.has_argumentless_for,
                self.has_job_command,
                self.empty_label_bodies > 2,
                self.unrecognized_statements > 0,
            ]
        )

    def interest_reasons(self) -> list[str]:
        """Return reasons why this file is interesting."""
        reasons = []
        if self.has_unresolved_gotos:
            reasons.append(f"unresolved GOTOs: {self.unresolved_goto_targets}")
        if self.has_backward_gotos:
            reasons.append(f"backward GOTOs: {self.backward_goto_count}")
        if self.has_cross_label_gotos:
            reasons.append(f"cross-label GOTOs: {self.cross_label_goto_count}")
        if self.has_computed_gotos:
            reasons.append("computed GOTOs (dynamic targets)")
        if self.has_deeply_nested_for:
            reasons.append(f"deeply nested FOR: {self.max_for_nesting} levels")
        if self.has_goto_inside_for:
            reasons.append(f"GOTO inside FOR: {self.goto_in_for_count}")
        if self.xecute_count > 3:
            reasons.append(f"multiple XECUTE: {self.xecute_count}")
        if self.has_complex_indirection:
            reasons.append(f"complex indirection: {self.indirection_count}")
        if self.has_argumentless_for:
            reasons.append(f"argumentless FOR: {self.argumentless_for_count}")
        if self.has_job_command:
            reasons.append("JOB command used")
        if self.empty_label_bodies > 2:
            reasons.append(f"empty labels: {self.empty_label_bodies}")
        if self.unrecognized_statements > 0:
            reasons.append(f"unrecognized statements: {self.unrecognized_statements}")
        return reasons


def analyze_file_deeply(filepath: Path, parser: MUMPSParser) -> DeepAnalysisResult:
    """Perform deep analysis of a MUMPS file."""
    result = DeepAnalysisResult(filepath=str(filepath))

    try:
        routine = parser.parse_file(filepath)
        parser.resolve_references(routine)
        result.parsed = True

        analyze_routine(routine, result)

    except Exception as e:
        result.parsed = False
        result.error_message = str(e)[:200]

    return result


def analyze_routine(routine: MRoutine, result: DeepAnalysisResult) -> None:
    """Analyze an ASG routine for interesting patterns."""

    for label in routine.labels:
        if not label.body or not label.body.statements:
            result.empty_label_bodies += 1
            continue

        analyze_scope(label.body, result, in_for=False, for_depth=0)


def analyze_scope(
    scope, result: DeepAnalysisResult, in_for: bool, for_depth: int
) -> None:
    """Recursively analyze a scope for patterns."""
    if not scope or not hasattr(scope, "statements"):
        return

    for stmt in scope.statements:
        # Analyze specific statement types
        if isinstance(stmt, MForStatement):
            new_depth = for_depth + 1
            result.max_for_nesting = max(result.max_for_nesting, new_depth)

            if new_depth > 3:
                result.has_deeply_nested_for = True

            # Check for argumentless FOR
            if not stmt.parameters or len(stmt.parameters) == 0:
                result.has_argumentless_for = True
                result.argumentless_for_count += 1

            # Recurse into FOR body
            if stmt.body:
                analyze_scope(stmt.body, result, in_for=True, for_depth=new_depth)

        elif isinstance(stmt, MGotoStatement):
            # Check if in FOR
            if in_for:
                result.has_goto_inside_for = True
                result.goto_in_for_count += 1

            # Check GOTO type
            if hasattr(stmt, "goto_type") and stmt.goto_type:
                if stmt.goto_type == GotoType.BACKWARD_JUMP:
                    result.has_backward_gotos = True
                    result.backward_goto_count += 1
                elif stmt.goto_type == GotoType.UNRESOLVED:
                    result.has_unresolved_gotos = True
            # Check cross-label flag (orthogonal to goto_type)
            if hasattr(stmt, "is_cross_label") and stmt.is_cross_label:
                result.has_cross_label_gotos = True
                result.cross_label_goto_count += 1

            # Check for computed GOTO (indirection in target)
            if hasattr(stmt, "targets"):
                for target in stmt.targets or []:
                    if (
                        hasattr(target, "label_is_indirect")
                        and target.label_is_indirect
                    ):
                        result.has_computed_gotos = True
                    if hasattr(target, "is_resolved") and not target.is_resolved:
                        result.has_unresolved_gotos = True
                        target_name = getattr(target, "name", "unknown")
                        result.unresolved_goto_targets.append(target_name)

        elif isinstance(stmt, MXecuteStatement):
            result.xecute_count += 1

        elif isinstance(stmt, MJobStatement):
            result.has_job_command = True

        elif isinstance(stmt, MIfStatement):
            if stmt.then_scope:
                analyze_scope(
                    stmt.then_scope, result, in_for=in_for, for_depth=for_depth
                )

        elif isinstance(stmt, MElseStatement):
            if stmt.body:
                analyze_scope(stmt.body, result, in_for=in_for, for_depth=for_depth)

        elif isinstance(stmt, MDoStatement):
            if stmt.body:
                analyze_scope(stmt.body, result, in_for=in_for, for_depth=for_depth)

        # Analyze expressions for indirection
        analyze_expressions_for_indirection(stmt, result)


def analyze_expressions_for_indirection(stmt, result: DeepAnalysisResult) -> None:
    """Check for indirection in expressions."""

    def walk_expr(expr, depth=0):
        if expr is None:
            return

        if isinstance(expr, MIndirection):
            result.indirection_count += 1
            if depth > 0:  # Nested indirection
                result.has_complex_indirection = True
            # Check for computed indirection (indirection in expression)
            if hasattr(expr, "expression"):
                walk_expr(expr.expression, depth + 1)

        elif isinstance(expr, MNakedGlobal):
            result.naked_global_count += 1

        elif isinstance(expr, MIntrinsicFunction):
            # Check for unusual intrinsics
            if hasattr(expr, "name"):
                name = expr.name.upper()
                unusual = [
                    "$ZBITAND",
                    "$ZBITCOUNT",
                    "$ZBITFIND",
                    "$ZBOOLEAN",
                    "$ZSOCKET",
                    "$ZTRNLNM",
                    "$ZGETJPI",
                ]
                if any(u in f"${name}" for u in unusual):
                    result.unusual_intrinsics.add(f"${name}")
            if hasattr(expr, "arguments"):
                for arg in expr.arguments or []:
                    walk_expr(arg, depth)

        elif isinstance(expr, MBinaryOp):
            walk_expr(expr.left, depth)
            walk_expr(expr.right, depth)

        elif isinstance(expr, MUnaryOp):
            walk_expr(expr.operand, depth)

        elif isinstance(expr, (MVariable, MGlobal)):
            if hasattr(expr, "subscripts"):
                for sub in expr.subscripts or []:
                    walk_expr(sub, depth)

        elif isinstance(expr, list):
            for item in expr:
                walk_expr(item, depth)

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
            walk_expr(getattr(stmt, attr))

    if isinstance(stmt, MSetStatement) and hasattr(stmt, "assignments"):
        for assign in stmt.assignments or []:
            if hasattr(assign, "target"):
                walk_expr(assign.target)
            if hasattr(assign, "value"):
                walk_expr(assign.value)


def find_files(
    package_filter: Optional[str] = None, limit: Optional[int] = None
) -> list[Path]:
    """Find VistA-M MUMPS files."""
    files = []
    for m_file in VISTA_ROOT.rglob("*.m"):
        if package_filter:
            if package_filter.lower() not in str(m_file.parent).lower():
                continue
        files.append(m_file)
        if limit and len(files) >= limit:
            break
    return sorted(files)


def main():
    parser_arg = argparse.ArgumentParser(description="Deep analysis of VistA-M files")
    parser_arg.add_argument("--limit", type=int, help="Limit number of files")
    parser_arg.add_argument("--file", type=str, help="Analyze single file")
    parser_arg.add_argument("--package", type=str, help="Filter to package")
    parser_arg.add_argument(
        "--show-all",
        action="store_true",
        help="Show all files, not just interesting ones",
    )

    args = parser_arg.parse_args()

    mumps_parser = MUMPSParser()

    if args.file:
        filepath = Path(args.file)
        result = analyze_file_deeply(filepath, mumps_parser)
        print(f"\n{'=' * 60}")
        print(f"File: {filepath.name}")
        print(f"Parsed: {result.parsed}")
        if not result.parsed:
            print(f"Error: {result.error_message}")
        else:
            print(f"Interesting: {result.is_interesting()}")
            if result.is_interesting():
                print("Reasons:")
                for reason in result.interest_reasons():
                    print(f"  - {reason}")
            print("\nMetrics:")
            print(f"  Max FOR nesting: {result.max_for_nesting}")
            print(f"  Backward GOTOs: {result.backward_goto_count}")
            print(f"  GOTO in FOR: {result.goto_in_for_count}")
            print(f"  XECUTE count: {result.xecute_count}")
            print(f"  Indirection count: {result.indirection_count}")
            print(f"  Naked globals: {result.naked_global_count}")
            print(f"  Empty labels: {result.empty_label_bodies}")
        return

    files = find_files(args.package, args.limit)
    print(f"Analyzing {len(files)} files...")

    interesting_files = []
    total_analyzed = 0
    parse_errors = 0

    for i, filepath in enumerate(files):
        if i > 0 and i % 500 == 0:
            print(f"Progress: {i}/{len(files)}")

        result = analyze_file_deeply(filepath, mumps_parser)
        total_analyzed += 1

        if not result.parsed:
            parse_errors += 1
            continue

        if result.is_interesting() or args.show_all:
            interesting_files.append(result)

    # Sort by number of interesting reasons
    interesting_files.sort(key=lambda r: len(r.interest_reasons()), reverse=True)

    print(f"\n{'=' * 60}")
    print("DEEP ANALYSIS RESULTS")
    print(f"{'=' * 60}")
    print(f"Total files analyzed: {total_analyzed}")
    print(f"Parse errors: {parse_errors}")
    print(f"Interesting files: {len(interesting_files)}")

    print("\n--- Top Interesting Files (for manual validation) ---")
    for i, result in enumerate(interesting_files[:30], 1):
        print(f"\n{i}. {Path(result.filepath).name}")
        for reason in result.interest_reasons():
            print(f"   - {reason}")

    # Aggregate statistics
    backward_goto_files = [r for r in interesting_files if r.has_backward_gotos]
    computed_goto_files = [r for r in interesting_files if r.has_computed_gotos]
    deep_for_files = [r for r in interesting_files if r.has_deeply_nested_for]
    goto_in_for_files = [r for r in interesting_files if r.has_goto_inside_for]
    xecute_files = [r for r in interesting_files if r.xecute_count > 3]

    print("\n--- Aggregate Statistics ---")
    print(f"Files with backward GOTOs: {len(backward_goto_files)}")
    print(f"Files with computed GOTOs: {len(computed_goto_files)}")
    print(f"Files with deeply nested FOR (>3): {len(deep_for_files)}")
    print(f"Files with GOTO inside FOR: {len(goto_in_for_files)}")
    print(f"Files with multiple XECUTE (>3): {len(xecute_files)}")

    # Print files for validate_asg.py
    print("\n--- Recommended for manual validation with utils/validate_asg.py ---")
    for result in interesting_files[:10]:
        print(f"uv run python utils/validate_asg.py {result.filepath}")


if __name__ == "__main__":
    main()
