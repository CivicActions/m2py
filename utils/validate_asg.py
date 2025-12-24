#!/usr/bin/env python3
"""ASG Validation Utility for MUGJ Phase 13 Deep Validation.

This script parses a MUMPS file and displays:
1. Original MUMPS source code
2. ASG structure in a clean, readable format
3. Validation checklist reminders

Purpose: Support deep validation of all 376 MUGJ test files to ensure:
  ✓ ASG 100% correctly captures all source details in proper structure
  ✓ ASG is semantically useful for Python code generation
"""

import sys
from pathlib import Path
from dataclasses import fields
from typing import Any
import argparse


def format_asg_node(node: Any, indent: int = 0, max_depth: int = 5) -> str:
    """Format an ASG node recursively with indentation."""
    if indent > max_depth:
        return "  " * indent + "..."

    if node is None:
        return "None"

    # Handle primitive types
    if isinstance(node, (str, int, float, bool)):
        return repr(node)

    # Handle lists
    if isinstance(node, list):
        if not node:
            return "[]"
        result = "[\n"
        for item in node:
            result += (
                "  " * (indent + 1)
                + format_asg_node(item, indent + 1, max_depth)
                + ",\n"
            )
        result += "  " * indent + "]"
        return result

    # Handle enums
    if hasattr(node, "__class__") and hasattr(node.__class__, "__name__"):
        class_name = node.__class__.__name__
        if class_name.endswith("Type") or class_name.endswith("Operator"):
            return f"{class_name}.{node.name}"

    # Handle ASG nodes (dataclasses)
    if hasattr(node, "__dataclass_fields__"):
        class_name = node.__class__.__name__
        result = f"{class_name}(\n"

        # Get fields, prioritize important ones
        priority_fields = ["name", "type", "value", "targets", "condition", "loop_var"]
        other_fields = []

        for field in fields(node):
            if field.name in priority_fields:
                continue
            other_fields.append(field)

        # Show priority fields first
        for field_name in priority_fields:
            if hasattr(node, field_name):
                field_value = getattr(node, field_name)
                if field_value is not None:
                    formatted_value = format_asg_node(
                        field_value, indent + 1, max_depth
                    )
                    result += "  " * (indent + 1) + f"{field_name}={formatted_value},\n"

        # Show other fields
        for field in other_fields:
            if field.name in ["parent", "source_line", "source_col"]:
                continue  # Skip back-references and source tracking for readability

            field_value = getattr(node, field.name)
            if field_value is not None and field_value != [] and field_value != "":
                formatted_value = format_asg_node(field_value, indent + 1, max_depth)
                result += "  " * (indent + 1) + f"{field.name}={formatted_value},\n"

        result += "  " * indent + ")"
        return result

    return repr(node)


def display_source(filepath: Path) -> None:
    """Display the original MUMPS source code."""
    print("=" * 80)
    print(f"SOURCE: {filepath.name}")
    print("=" * 80)

    lines = filepath.read_text().split("\n")
    for i, line in enumerate(lines, 1):
        print(f"{i:3}: {line}")

    print()


def display_asg(routine: Any) -> None:
    """Display the ASG structure."""
    print("=" * 80)
    print("ASG STRUCTURE")
    print("=" * 80)

    print(f"\nRoutine: {routine.name}")
    print(f"Labels: {len(routine.labels)}")

    for label in routine.labels:
        print(f"\n{'─' * 80}")
        print(f"Label: {label.name}")

        if label.body and label.body.statements:
            print(f"Statements: {len(label.body.statements)}")

            for i, stmt in enumerate(label.body.statements, 1):
                print(f"\n  [{i}] {stmt.__class__.__name__}")

                # Show statement details
                if hasattr(stmt, "postcondition") and stmt.postcondition:
                    print(
                        f"      postcondition: {format_asg_node(stmt.postcondition, 3, max_depth=3)}"
                    )

                if hasattr(stmt, "targets") and stmt.targets:
                    print(f"      targets: {len(stmt.targets)} item(s)")
                    for j, target in enumerate(stmt.targets):
                        target_repr = format_asg_node(target, 3, max_depth=5)
                        print(f"        [{j}] {target_repr}")

                if hasattr(stmt, "value") and stmt.value:
                    print(f"      value: {format_asg_node(stmt.value, 3, max_depth=2)}")

                if hasattr(stmt, "condition") and stmt.condition:
                    print(
                        f"      condition: {format_asg_node(stmt.condition, 3, max_depth=2)}"
                    )

                if hasattr(stmt, "arguments") and stmt.arguments:
                    print(f"      arguments: {len(stmt.arguments)} item(s)")

                if hasattr(stmt, "device_expr") and stmt.device_expr:
                    print(
                        f"      device_expr: {format_asg_node(stmt.device_expr, 3, max_depth=2)}"
                    )

                if hasattr(stmt, "timeout") and stmt.timeout:
                    print(
                        f"      timeout: {format_asg_node(stmt.timeout, 3, max_depth=2)}"
                    )

                if hasattr(stmt, "loop_var") and stmt.loop_var:
                    print(f"      loop_var: {stmt.loop_var}")

                if hasattr(stmt, "parameters") and stmt.parameters:
                    print(f"      parameters: {len(stmt.parameters)} item(s)")

                if hasattr(stmt, "body") and stmt.body:
                    if hasattr(stmt.body, "statements"):
                        print(f"      body: {len(stmt.body.statements)} statement(s)")
                        for k, sub_stmt in enumerate(stmt.body.statements):
                            sub_name = sub_stmt.__class__.__name__
                            # Show postcondition on nested statements
                            if (
                                hasattr(sub_stmt, "postcondition")
                                and sub_stmt.postcondition
                            ):
                                sub_name += (
                                    f":{format_compact_expr(sub_stmt.postcondition)}"
                                )
                            print(f"        [{k}] {sub_name}")
                            # Show nested body scopes (e.g., FOR inside FOR)
                            if (
                                hasattr(sub_stmt, "body")
                                and sub_stmt.body
                                and hasattr(sub_stmt.body, "statements")
                                and sub_stmt.body.statements
                            ):
                                print(
                                    f"          body: {len(sub_stmt.body.statements)} statement(s)"
                                )
                            # Show nested then_scope for IF inside FOR body
                            if (
                                hasattr(sub_stmt, "then_scope")
                                and sub_stmt.then_scope
                                and hasattr(sub_stmt.then_scope, "statements")
                                and sub_stmt.then_scope.statements
                            ):
                                print(
                                    f"          then_scope: {len(sub_stmt.then_scope.statements)} statement(s)"
                                )
                                for m, nested in enumerate(
                                    sub_stmt.then_scope.statements
                                ):
                                    print(
                                        f"            [{m}] {nested.__class__.__name__}"
                                    )

                if hasattr(stmt, "then_scope") and stmt.then_scope:
                    if (
                        hasattr(stmt.then_scope, "statements")
                        and stmt.then_scope.statements
                    ):
                        print(
                            f"      then_scope: {len(stmt.then_scope.statements)} statement(s)"
                        )
                        for k, sub_stmt in enumerate(stmt.then_scope.statements):
                            print(f"        [{k}] {sub_stmt.__class__.__name__}")
                            if (
                                hasattr(sub_stmt, "body")
                                and sub_stmt.body
                                and hasattr(sub_stmt.body, "statements")
                                and sub_stmt.body.statements
                            ):
                                print(
                                    f"          body: {len(sub_stmt.body.statements)} statement(s)"
                                )

        else:
            print("  No statements")

    print()


def format_compact_expr(node: Any, depth: int = 0) -> str:
    """Format an expression compactly for single-line display."""
    if depth > 4:
        return "..."

    if node is None:
        return "∅"

    if isinstance(node, str):
        return f'"{node}"' if len(node) < 20 else f'"{node[:17]}..."'

    if isinstance(node, (int, float, bool)):
        return str(node)

    if isinstance(node, list):
        if not node:
            return "[]"
        items = [format_compact_expr(x, depth + 1) for x in node[:3]]
        suffix = f"...+{len(node) - 3}" if len(node) > 3 else ""
        return f"[{', '.join(items)}{suffix}]"

    # Handle enums
    if hasattr(node, "__class__") and hasattr(node.__class__, "__name__"):
        class_name = node.__class__.__name__
        if class_name.endswith("Type") or class_name.endswith("Operator"):
            return node.name

    # Handle ASG nodes
    if hasattr(node, "__dataclass_fields__"):
        class_name = node.__class__.__name__

        # Special compact formats for common types
        if class_name == "MLiteral":
            return f"L({node.value})"
        if class_name == "StringLiteral":
            return (
                f'"{node.value}"'
                if len(str(node.value)) < 15
                else f'"{str(node.value)[:12]}..."'
            )
        if class_name == "NumericLiteral":
            return str(node.value)
        if class_name in ("MVariable", "LocalVariable"):
            subs = (
                f"({','.join(format_compact_expr(s, depth + 1) for s in node.subscripts[:2])})"
                if node.subscripts
                else ""
            )
            return f"{node.name}{subs}"
        if class_name == "MGlobal":
            subs = (
                f"({','.join(format_compact_expr(s, depth + 1) for s in node.subscripts[:2])})"
                if node.subscripts
                else ""
            )
            return f"^{node.name}{subs}"
        if class_name == "MNakedGlobal":
            subs = (
                f"({','.join(format_compact_expr(s, depth + 1) for s in node.subscripts[:2])})"
                if node.subscripts
                else ""
            )
            return f"^{subs}"
        if class_name == "MBinaryOp":
            left = format_compact_expr(node.left, depth + 1)
            right = format_compact_expr(node.right, depth + 1)
            op = (
                node.operator.name
                if hasattr(node.operator, "name")
                else str(node.operator)
            )
            return f"({left} {op} {right})"
        if class_name == "MUnaryOp":
            operand = format_compact_expr(node.operand, depth + 1)
            op = (
                node.operator.name
                if hasattr(node.operator, "name")
                else str(node.operator)
            )
            return f"({op}{operand})"
        if class_name == "MIntrinsicFunction":
            args = ",".join(
                format_compact_expr(a, depth + 1) for a in (node.arguments or [])[:2]
            )
            return f"${node.name}({args})"
        if class_name == "MExtrinsicFunction":
            return f"$${'^' + node.routine if node.routine else ''}{node.name or ''}"
        if class_name == "MSpecialVariable":
            return f"${node.name}"
        if class_name == "MIndirection":
            return f"@{format_compact_expr(node.target, depth + 1)}"
        if class_name == "MPatternMatch":
            return f"?{node.pattern}"
        if class_name == "MCall":
            target = f"^{node.routine}" if node.routine else ""
            target += node.name or ""
            return f"CALL({target})"
        if class_name == "MSetTarget":
            if node.targets:
                targets = ",".join(
                    format_compact_expr(t, depth + 1) for t in node.targets[:2]
                )
                return f"({targets})"
            return format_compact_expr(node.variable, depth + 1)
        if class_name == "MFormatControl":
            ctrl_type = (
                node.control_type.name
                if hasattr(node, "control_type") and node.control_type
                else "?"
            )
            if node.expression:
                return f"{ctrl_type}({format_compact_expr(node.expression, depth + 1)})"
            return ctrl_type

        # Generic format for other node types
        return f"{class_name[:8]}(...)"

    return str(node)[:20]


def format_compact_stmt(stmt: Any) -> str:
    """Format a statement in one line with key semantic details."""
    class_name = stmt.__class__.__name__
    parts = [class_name.replace("Statement", "")]

    # Add postcondition if present
    if hasattr(stmt, "postcondition") and stmt.postcondition:
        parts[0] += f":{format_compact_expr(stmt.postcondition)}"

    # Add key details based on statement type
    if hasattr(stmt, "targets") and stmt.targets:
        targets = []
        for t in stmt.targets[:3]:
            t_str = format_compact_expr(t)
            # Also show indirection if present
            if hasattr(t, "indirection") and t.indirection:
                t_str = f"@{format_compact_expr(t.indirection)}"
            targets.append(t_str)
        if len(stmt.targets) > 3:
            targets.append(f"...+{len(stmt.targets) - 3}")
        parts.append(f"→ {', '.join(targets)}")

    if hasattr(stmt, "value") and stmt.value:
        parts.append(f"= {format_compact_expr(stmt.value)}")

    if hasattr(stmt, "condition") and stmt.condition:
        parts.append(f"IF {format_compact_expr(stmt.condition)}")

    if hasattr(stmt, "loop_var") and stmt.loop_var:
        parts.append(f"loop={stmt.loop_var}")

    if hasattr(stmt, "parameters") and stmt.parameters:
        params = len(stmt.parameters)
        parts.append(f"({params} params)")

    if hasattr(stmt, "arguments") and stmt.arguments:
        args = [format_compact_expr(a) for a in stmt.arguments[:2]]
        parts.append(f"args=[{', '.join(args)}]")

    if hasattr(stmt, "call") and stmt.call:
        parts.append(format_compact_expr(stmt.call))

    if hasattr(stmt, "body") and stmt.body and hasattr(stmt.body, "statements"):
        parts.append(f"body={len(stmt.body.statements)}stmts")

    # Show then_scope for IF statements
    if (
        hasattr(stmt, "then_scope")
        and stmt.then_scope
        and hasattr(stmt.then_scope, "statements")
    ):
        parts.append(f"then={len(stmt.then_scope.statements)}stmts")

    # Show else_scope for IF statements
    if (
        hasattr(stmt, "else_scope")
        and stmt.else_scope
        and hasattr(stmt.else_scope, "statements")
    ):
        parts.append(f"else={len(stmt.else_scope.statements)}stmts")

    return " ".join(parts)


def display_statements_recursive(statements, indent: int = 1) -> None:
    """Display statements with recursive nesting for control flow bodies."""
    for i, stmt in enumerate(statements, 1):
        compact = format_compact_stmt(stmt)
        print(f"{'  ' * indent}{i:2}. {compact}")

        # Recursively show IF then_scope
        if (
            hasattr(stmt, "then_scope")
            and stmt.then_scope
            and hasattr(stmt.then_scope, "statements")
            and stmt.then_scope.statements
        ):
            print(f"{'  ' * (indent + 1)}┌─ then:")
            display_statements_recursive(stmt.then_scope.statements, indent + 2)

        # Recursively show FOR/ELSE body
        if (
            hasattr(stmt, "body")
            and stmt.body
            and hasattr(stmt.body, "statements")
            and stmt.body.statements
        ):
            print(f"{'  ' * (indent + 1)}┌─ body:")
            display_statements_recursive(stmt.body.statements, indent + 2)


def display_compact_asg(routine: Any) -> None:
    """Display compact ASG - one line per statement with key details."""
    print("=" * 80)
    print(f"COMPACT ASG: {routine.name}")
    print("=" * 80)

    for label in routine.labels:
        print(f"\n▸ {label.name or '(anonymous)'}" + (":" if label.formal_list else ""))
        if label.formal_list:
            print(f"  params: ({', '.join(label.formal_list)})")

        # Show variable analysis results if populated
        if label.input_variables or label.output_variables:
            if label.input_variables:
                print(f"  inputs: {{{', '.join(sorted(label.input_variables))}}}")
            if label.output_variables:
                print(f"  outputs: {{{', '.join(sorted(label.output_variables))}}}")

        # Show function signature if computed
        if hasattr(label, "signature") and label.signature:
            sig = label.signature
            strategy = sig.scope_strategy.name if sig.scope_strategy else "UNKNOWN"
            print(f"  strategy: {strategy}")
            if sig.has_value_quit:
                print("  returns: value")
            if sig.requires_runtime_scope:
                print("  ⚠️ requires runtime scope")

        if label.body and label.body.statements:
            display_statements_recursive(label.body.statements, indent=1)
        else:
            print("  (no statements)")

    print()


def display_validation_checklist() -> None:
    """Display validation checklist."""
    print("=" * 80)
    print("VALIDATION CHECKLIST")
    print("=" * 80)
    print("""
TASK 1: Verify 100% Correct ASG Capture
  □ Every line in source has corresponding ASG node(s)?
  □ All labels captured with correct names?
  □ All commands captured (SET, WRITE, DO, GOTO, FOR, IF, etc.)?
  □ All expressions captured (variables, literals, operators, functions)?
  □ Postconditions captured where present?
  □ Control flow structures (IF/ELSE, FOR) captured correctly?
  □ Function calls (intrinsic and extrinsic) captured?
  □ Special variables ($HOROLOG, $STORAGE, etc.) captured?
  □ Indirection (@variable) captured?
  □ Pattern matches (?) captured?

TASK 2: Evaluate Python Code Generation Readiness
  □ Does ASG distinguish commands vs functions clearly?
  □ Are expression trees properly structured (not just strings)?
  □ Is operator precedence captured correctly?
  □ Are variable scopes/references identifiable?
  □ Can control flow be translated to Python (if/for/while)?
  □ Are label targets resolved (for GOTO/DO)?
  □ Is there enough semantic info to generate equivalent Python?
  □ What additional analysis would simplify code generation?
  □ Are there ambiguities that need clarification?
  □ Missing semantic information that affects correctness?

CROSS-REFERENCE: Check mumps-reference/ documentation as needed
  - Operator precedence and behavior
  - Intrinsic function semantics
  - Special variable meanings
  - Command syntax and postconditions
  - Pattern match syntax
""")


def analyze_completeness(routine: Any, source_lines: list[str]) -> dict:
    """Analyze ASG completeness vs source."""
    total_source_lines = len(
        [
            line
            for line in source_lines
            if line.strip() and not line.strip().startswith(";")
        ]
    )

    total_statements = 0
    label_count = len(routine.labels)

    statement_types = {}
    missing_commands = []

    for label in routine.labels:
        if label.body and label.body.statements:
            for stmt in label.body.statements:
                total_statements += 1
                stmt_type = stmt.__class__.__name__
                statement_types[stmt_type] = statement_types.get(stmt_type, 0) + 1

    return {
        "source_lines": total_source_lines,
        "label_count": label_count,
        "statement_count": total_statements,
        "statement_types": statement_types,
        "missing_commands": missing_commands,
    }


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description="Validate MUMPS ASG structure for Phase 14 preparation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a single file with full detail
  uv run python utils/validate_asg.py tests/functional/mugj/inref/RESTORE.m
  
  # Validate multiple files
  uv run python utils/validate_asg.py tests/functional/mugj/inref/V1*.m
  
  # Compact mode - concise ASG output for validation review
  uv run python utils/validate_asg.py tests/functional/mugj/inref/V1BOA.m
  
  # Show only summary
  uv run python utils/validate_asg.py --summary tests/functional/mugj/inref/RESTORE.m
        """,
    )
    parser.add_argument("files", nargs="+", help="MUMPS files to validate")
    parser.add_argument(
        "--summary", action="store_true", help="Show only summary, not full ASG"
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Compact ASG output - one line per statement with key details",
    )
    parser.add_argument(
        "--no-checklist", action="store_true", help="Skip validation checklist"
    )

    args = parser.parse_args()

    # Import here to avoid issues if m2py not installed
    try:
        from m2py.parser import MUMPSParser
    except ImportError:
        print("ERROR: Cannot import m2py. Make sure it's installed.")
        print("Run: uv sync")
        return 1

    parser_obj = MUMPSParser()

    for file_path_str in args.files:
        filepath = Path(file_path_str)

        if not filepath.exists():
            print(f"ERROR: File not found: {filepath}")
            continue

        print("\n" + "█" * 80)
        print(f"VALIDATING: {filepath.name}")
        print("█" * 80 + "\n")

        # Display source
        display_source(filepath)

        # Parse and display ASG
        try:
            routine = parser_obj.parse_file(str(filepath))
            # Run reference resolution so DO/GOTO calls show resolved targets
            parser_obj.resolve_references(routine)
            # Run GOTO classification to populate goto_type, exits_loops, and FOR analysis fields
            parser_obj.classify_gotos(routine)
            # Run FOR loop analysis to detect loop variable modification
            parser_obj.analyze_for_loops(routine)
            # Run variable analysis to populate input/output variables
            parser_obj.analyze_variables(routine, compute_transitive=True)
            # Compute function signatures for code generation
            parser_obj.compute_signatures(routine)

            if args.compact:
                display_compact_asg(routine)
            elif not args.summary:
                display_asg(routine)

            # Analyze completeness
            source_lines = filepath.read_text().split("\n")
            analysis = analyze_completeness(routine, source_lines)

            print("=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"Source lines (non-comment): {analysis['source_lines']}")
            print(f"Labels captured: {analysis['label_count']}")
            print(f"Statements captured: {analysis['statement_count']}")
            print("\nStatement types:")
            for stmt_type, count in sorted(analysis["statement_types"].items()):
                print(f"  {stmt_type}: {count}")

            if analysis["missing_commands"]:
                print(
                    f"\n⚠️  Missing commands: {', '.join(analysis['missing_commands'])}"
                )

            print()

        except Exception as e:
            print(f"ERROR: Failed to parse {filepath.name}: {e}")
            import traceback

            traceback.print_exc()
            continue

        # Display validation checklist
        if not args.no_checklist:
            display_validation_checklist()

        print("\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
