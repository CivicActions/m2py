#!/usr/bin/env python3
"""MUMPS Validation Utility - Compare m2py output vs YottaDB.

This script validates MUMPS code by:
1. Running it through m2py (parse → generate Python → execute)
2. Running it through YottaDB via Docker
3. Comparing the outputs

Usage:
    # Validate a file
    uv run python utils/validate.py tests/functional/mugj/inref/V1FORA.m

    # Validate from stdin
    echo 'TEST W "Hello" Q' | uv run python utils/validate.py -

    # Pass code directly
    uv run python utils/validate.py --code 'TEST W "Hello" Q'

    # Debug mode (show AST and generated Python)
    uv run python utils/validate.py --debug tests/functional/mugj/inref/V1FORA.m
"""

import argparse
import subprocess
import sys
import tempfile
from dataclasses import fields
from pathlib import Path
from typing import Any


# ANSI colors for terminal output
class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def color(text: str, c: str) -> str:
    """Wrap text in ANSI color codes."""
    return f"{c}{text}{Colors.RESET}"


# =============================================================================
# AST Formatting (from validate_asg.py)
# =============================================================================


def format_asg_node(node: Any, indent: int = 0, max_depth: int = 8) -> str:
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
                continue  # Skip back-references and source tracking

            field_value = getattr(node, field.name)
            if field_value is not None and field_value != [] and field_value != "":
                formatted_value = format_asg_node(field_value, indent + 1, max_depth)
                result += "  " * (indent + 1) + f"{field.name}={formatted_value},\n"

        result += "  " * indent + ")"
        return result

    return repr(node)


def display_asg(routine: Any) -> None:
    """Display the ASG structure."""
    print(color("=" * 80, Colors.CYAN))
    print(color("AST STRUCTURE", Colors.CYAN))
    print(color("=" * 80, Colors.CYAN))

    print(f"\nRoutine: {routine.name}")
    print(f"Labels: {len(routine.labels)}")

    for label in routine.labels:
        print(f"\n{'─' * 80}")
        print(f"Label: {label.name}")

        if label.formal_list:
            print(f"Formal params: ({', '.join(label.formal_list)})")

        if label.body and label.body.statements:
            print(f"Statements: {len(label.body.statements)}")

            for i, stmt in enumerate(label.body.statements, 1):
                print(f"\n  [{i}] {stmt.__class__.__name__}")
                _display_stmt_details(stmt, indent=3)
        else:
            print("  No statements")

    print()


def _display_stmt_details(stmt: Any, indent: int = 3) -> None:
    """Display statement details recursively."""
    prefix = "  " * indent

    if hasattr(stmt, "postcondition") and stmt.postcondition:
        print(
            f"{prefix}postcondition: {format_asg_node(stmt.postcondition, indent, max_depth=3)}"
        )

    if hasattr(stmt, "targets") and stmt.targets:
        print(f"{prefix}targets: {len(stmt.targets)} item(s)")
        for j, target in enumerate(stmt.targets):
            target_repr = format_asg_node(target, indent, max_depth=5)
            print(f"{prefix}  [{j}] {target_repr}")

    if hasattr(stmt, "assignments") and stmt.assignments:
        print(f"{prefix}assignments: {len(stmt.assignments)} item(s)")
        for j, assignment in enumerate(stmt.assignments):
            print(f"{prefix}  [{j}] {format_asg_node(assignment, indent, max_depth=4)}")

    if hasattr(stmt, "arguments") and stmt.arguments:
        print(f"{prefix}arguments: {len(stmt.arguments)} item(s)")
        for j, arg in enumerate(stmt.arguments):
            print(f"{prefix}  [{j}] {format_asg_node(arg, indent, max_depth=4)}")

    if hasattr(stmt, "condition") and stmt.condition:
        print(
            f"{prefix}condition: {format_asg_node(stmt.condition, indent, max_depth=3)}"
        )

    if hasattr(stmt, "conditions") and stmt.conditions:
        print(f"{prefix}conditions: {len(stmt.conditions)} item(s)")

    if hasattr(stmt, "loop_var") and stmt.loop_var:
        print(f"{prefix}loop_var: {stmt.loop_var}")

    if hasattr(stmt, "parameters") and stmt.parameters:
        print(f"{prefix}parameters: {len(stmt.parameters)} item(s)")
        for j, param in enumerate(stmt.parameters):
            print(f"{prefix}  [{j}] {format_asg_node(param, indent, max_depth=4)}")

    if hasattr(stmt, "return_value") and stmt.return_value:
        print(
            f"{prefix}return_value: {format_asg_node(stmt.return_value, indent, max_depth=3)}"
        )

    if hasattr(stmt, "body") and stmt.body:
        if hasattr(stmt.body, "statements") and stmt.body.statements:
            print(f"{prefix}body: {len(stmt.body.statements)} statement(s)")
            for k, sub_stmt in enumerate(stmt.body.statements):
                print(f"{prefix}  [{k}] {sub_stmt.__class__.__name__}")
                _display_stmt_details(sub_stmt, indent + 2)

    if hasattr(stmt, "then_scope") and stmt.then_scope:
        if hasattr(stmt.then_scope, "statements") and stmt.then_scope.statements:
            print(f"{prefix}then_scope: {len(stmt.then_scope.statements)} statement(s)")
            for k, sub_stmt in enumerate(stmt.then_scope.statements):
                print(f"{prefix}  [{k}] {sub_stmt.__class__.__name__}")
                _display_stmt_details(sub_stmt, indent + 2)


# =============================================================================
# m2py Execution
# =============================================================================


def run_m2py(source: str, debug: bool = False) -> tuple[str, str | None, str | None]:
    """Run MUMPS source through m2py.

    Args:
        source: MUMPS source code
        debug: If True, return AST and generated Python

    Returns:
        Tuple of (output, ast_str, python_code) - ast_str and python_code are None if not debug
    """
    try:
        from m2py.codegen import generate_python
        from m2py.parser import MUMPSParser
        from m2py.runtime import MUMPSRuntime

        ast_str = None
        python_code = None

        if debug:
            # Parse and show AST
            parser = MUMPSParser()
            routine = parser.parse(source, filename="<input>")
            parser.resolve_references(routine)
            parser.classify_gotos(routine)
            parser.analyze_for_loops(routine)
            parser.analyze_variables(routine, compute_transitive=True)
            parser.compute_signatures(routine)

            # Capture AST as string
            import io
            import sys

            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            display_asg(routine)
            ast_str = sys.stdout.getvalue()
            sys.stdout = old_stdout

        # Generate Python
        python_code_generated = generate_python(source)
        if debug:
            python_code = python_code_generated

        # Execute
        runtime = MUMPSRuntime()
        result = runtime.execute(python_code_generated)

        if result.success:
            return result.output, ast_str, python_code
        else:
            return f"ERROR: {result.error}", ast_str, python_code

    except Exception as e:
        import traceback

        return f"ERROR: {e}\n{traceback.format_exc()}", None, None


# =============================================================================
# YottaDB Execution via Docker
# =============================================================================


def run_ydb(source: str, timeout: int = 30) -> str:
    """Run MUMPS source through YottaDB via Docker.

    Args:
        source: MUMPS source code
        timeout: Timeout in seconds

    Returns:
        Output from YottaDB execution
    """
    # Write source to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".m", delete=False) as f:
        f.write(source)
        temp_path = Path(f.name)

    try:
        # Get the first label name from the source
        entry_label = None
        for line in source.split("\n"):
            line = line.strip()
            if (
                line
                and not line.startswith(";")
                and not line.startswith(" ")
                and not line.startswith("\t")
            ):
                # First non-comment, non-indented line is a label
                parts = line.split()
                if parts:
                    # Label may have formal parameters
                    label = parts[0].split("(")[0]
                    entry_label = label
                    break

        if not entry_label:
            return "ERROR: No entry label found in source"

        # Run YottaDB via Docker
        # Use --entrypoint to override the container's default entrypoint
        # This allows us to run bash commands directly
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--entrypoint",
            "/bin/bash",
            "-v",
            f"{temp_path}:/tmp/test.m:ro",
            "yottadb/yottadb:latest",
            "-c",
            f"source /opt/yottadb/current/ydb_env_set && "
            f"mkdir -p $ydb_dir/r && "
            f"cp /tmp/test.m $ydb_dir/r/test.m && "
            f"cd $ydb_dir && "
            f"yottadb -run {entry_label}^test",
        ]

        result = subprocess.run(
            docker_cmd, capture_output=True, text=True, timeout=timeout
        )

        # YottaDB output
        output = result.stdout
        if result.stderr:
            output += result.stderr

        return output.rstrip()

    except subprocess.TimeoutExpired:
        return "ERROR: YottaDB execution timed out"
    except FileNotFoundError:
        return "ERROR: Docker not found. Is Docker installed and running?"
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        # Clean up temp file
        temp_path.unlink(missing_ok=True)


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate MUMPS code by comparing m2py output vs YottaDB",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Validate a file
    uv run python utils/validate.py tests/functional/mugj/inref/V1FORA.m
    
    # Validate from stdin
    echo 'TEST W "Hello" Q' | uv run python utils/validate.py -
    
    # Pass code directly
    uv run python utils/validate.py --code 'TEST W "Hello" Q'
    
    # Debug mode (show AST and generated Python)
    uv run python utils/validate.py --debug --code 'TEST S X=1 W X Q'
    
    # Skip YDB comparison (m2py only)
    uv run python utils/validate.py --no-ydb --code 'TEST W 1+2 Q'
        """,
    )
    parser.add_argument(
        "file", nargs="?", default=None, help="MUMPS file to validate (use - for stdin)"
    )
    parser.add_argument(
        "--code", "-c", type=str, help="M code to validate directly (instead of file)"
    )
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Show AST structure and generated Python code",
    )
    parser.add_argument(
        "--no-ydb", action="store_true", help="Skip YottaDB comparison (m2py only)"
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=30,
        help="YottaDB execution timeout in seconds (default: 30)",
    )

    args = parser.parse_args()

    # Get source code
    if args.code:
        source = args.code.replace("\\n", "\n").replace("\\t", "\t")
        source_name = "<code>"
    elif args.file == "-":
        source = sys.stdin.read()
        source_name = "<stdin>"
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"ERROR: File not found: {path}")
            return 1
        source = path.read_text()
        source_name = path.name
    else:
        parser.error("Must provide a file, use - for stdin, or use --code")

    # Header
    print(color("=" * 80, Colors.BOLD))
    print(color(f"VALIDATING: {source_name}", Colors.BOLD))
    print(color("=" * 80, Colors.BOLD))

    # Show source
    print(color("\n─── SOURCE ───", Colors.CYAN))
    for i, line in enumerate(source.split("\n"), 1):
        print(f"{i:3}: {line}")

    # Run m2py
    m2py_output, ast_str, python_code = run_m2py(source, debug=args.debug)

    # Debug output
    if args.debug:
        if ast_str:
            print(ast_str)

        if python_code:
            print(color("=" * 80, Colors.CYAN))
            print(color("GENERATED PYTHON", Colors.CYAN))
            print(color("=" * 80, Colors.CYAN))
            for i, line in enumerate(python_code.split("\n"), 1):
                print(f"{i:3}: {line}")
            print()

    # Show m2py output
    print(color("\n─── M2PY OUTPUT ───", Colors.BLUE))
    print(repr(m2py_output))

    if args.no_ydb:
        print(color("\n─── RESULT ───", Colors.YELLOW))
        print("YDB comparison skipped (--no-ydb)")
        return 0

    # Run YottaDB
    ydb_output = run_ydb(source, timeout=args.timeout)

    # Show YDB output
    print(color("\n─── YDB OUTPUT ───", Colors.BLUE))
    print(repr(ydb_output))

    # Compare outputs
    print(color("\n─── RESULT ───", Colors.BOLD))

    # Handle error cases
    m2py_error = m2py_output.startswith("ERROR:")
    ydb_error = ydb_output.startswith("ERROR:")

    if m2py_error and ydb_error:
        print(color("⚠️  BOTH ERRORED", Colors.YELLOW))
        print(f"   m2py: {m2py_output.split(chr(10))[0]}")
        print(f"   ydb:  {ydb_output.split(chr(10))[0]}")
        return 2
    elif m2py_error:
        print(color("❌ M2PY ERROR", Colors.RED))
        return 1
    elif ydb_error:
        print(color("⚠️  YDB ERROR (m2py succeeded)", Colors.YELLOW))
        print(f"   ydb: {ydb_output.split(chr(10))[0]}")
        return 2

    # Compare actual outputs
    if m2py_output == ydb_output:
        print(color("✅ MATCH", Colors.GREEN))
        return 0
    else:
        print(color("❌ MISMATCH", Colors.RED))
        print(f"\n   m2py: {repr(m2py_output)}")
        print(f"   ydb:  {repr(ydb_output)}")

        # Show diff if outputs are multi-line
        if "\n" in m2py_output or "\n" in ydb_output:
            print(color("\n─── DIFF ───", Colors.YELLOW))
            m2py_lines = m2py_output.split("\n")
            ydb_lines = ydb_output.split("\n")
            max_lines = max(len(m2py_lines), len(ydb_lines))
            for i in range(max_lines):
                m_line = m2py_lines[i] if i < len(m2py_lines) else ""
                y_line = ydb_lines[i] if i < len(ydb_lines) else ""
                if m_line == y_line:
                    print(f"  {i + 1:3}  {m_line}")
                else:
                    print(color(f"  {i + 1:3}< {m_line}", Colors.RED))
                    print(color(f"  {i + 1:3}> {y_line}", Colors.GREEN))

        return 1


if __name__ == "__main__":
    sys.exit(main())
