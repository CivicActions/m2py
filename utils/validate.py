#!/usr/bin/env python3
"""MUMPS Validation Utility - Compare m2py output vs YottaDB and/or IRIS.

This script validates MUMPS code by:
1. Running it through m2py (parse → generate Python → execute)
2. Running it through YottaDB and/or InterSystems IRIS via Docker
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

    # Compare against IRIS (in addition to YDB)
    uv run python utils/validate.py --iris --code 'TEST W "Hello" Q'

    # Compare against IRIS only (skip YDB)
    uv run python utils/validate.py --no-ydb --iris --code 'TEST W $ZCONVERT("hello","U") Q'
"""

import argparse
import multiprocessing
import queue
import sys
from dataclasses import fields
from pathlib import Path
from typing import Any

from run_mumps_iris import run_iris
from run_mumps_ydb import run_ydb


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


def _run_m2py_worker(
    source: str, debug: bool, result_queue: multiprocessing.Queue
) -> None:
    """Worker function for m2py execution (runs in subprocess for timeout support)."""
    try:
        from m2py.codegen import generate_python
        from m2py.parser import MUMPSParser
        from m2py.runtime import MUMPSRuntime

        ast_str = None
        python_code = None

        if debug:
            # Parse and get routine for AST display
            parser = MUMPSParser()
            routine = parser.parse(source, filename="<input>")
            parser.resolve_references(routine)
            parser.classify_gotos(routine)
            parser.analyze_for_loops(routine)
            parser.analyze_variables(routine, compute_transitive=True)
            parser.compute_signatures(routine)
            # Format AST in worker process (can't pickle textX objects)
            import io

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
            result_queue.put((result.output.rstrip(), ast_str, python_code))
        else:
            result_queue.put((f"ERROR: {result.error}", ast_str, python_code))

    except Exception as e:
        import traceback

        result_queue.put((f"ERROR: {e}\n{traceback.format_exc()}", None, None))


# Use 'spawn' context to avoid deadlocks when forking inside multi-threaded
# processes (e.g. pytest-xdist workers).
_MP_CTX = multiprocessing.get_context("spawn")


def run_m2py(
    source: str, debug: bool = False, timeout: int = 5
) -> tuple[str, str | None, str | None]:
    """Run MUMPS source through m2py with hard timeout.

    Args:
        source: MUMPS source code
        debug: If True, return AST and generated Python
        timeout: Timeout in seconds (process will be killed if exceeded)

    Returns:
        Tuple of (output, ast_str, python_code) - ast_str and python_code are None if not debug
    """
    result_queue: multiprocessing.Queue = _MP_CTX.Queue()
    process = _MP_CTX.Process(
        target=_run_m2py_worker, args=(source, debug, result_queue)
    )

    def _force_kill(proc: multiprocessing.Process) -> None:
        """Force kill the process."""
        if not proc.is_alive():
            return
        # Just use kill() directly - it's more reliable than terminate()
        try:
            proc.kill()
        except Exception:
            pass
        proc.join(timeout=1)

    try:
        process.start()
        try:
            # Wait for result with timeout
            output, ast_str, python_code = result_queue.get(timeout=timeout)
            process.join(timeout=1)  # Give it a second to clean up
            return output, ast_str, python_code
        except queue.Empty:
            # Timeout - kill the process
            pass
    finally:
        # Ensure the process is terminated
        _force_kill(process)
        # Clean up Queue resources (pipe fd + feeder thread)
        result_queue.close()
        result_queue.join_thread()

    return (
        f"ERROR: m2py execution timed out after {timeout}s (process killed)",
        None,
        None,
    )


# =============================================================================
# Diff Display
# =============================================================================


def _show_diff(m2py_output: str, ref_output: str, label: str) -> None:
    """Show a line-by-line diff between m2py and reference output."""
    if "\n" not in m2py_output and "\n" not in ref_output:
        return
    print(color(f"\n─── DIFF (m2py vs {label}) ───", Colors.YELLOW))
    m2py_lines = m2py_output.split("\n")
    ref_lines = ref_output.split("\n")
    max_lines = max(len(m2py_lines), len(ref_lines))
    for i in range(max_lines):
        m_line = m2py_lines[i] if i < len(m2py_lines) else ""
        r_line = ref_lines[i] if i < len(ref_lines) else ""
        if m_line == r_line:
            print(f"  {i + 1:3}  {m_line}")
        else:
            print(color(f"  {i + 1:3}< {m_line}", Colors.RED))
            print(color(f"  {i + 1:3}> {r_line}", Colors.GREEN))


# =============================================================================
# Main
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate MUMPS code by comparing m2py output vs YottaDB and/or IRIS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Validate a file (compares m2py vs YDB)
    uv run python utils/validate.py tests/functional/mugj/inref/V1FORA.m
    
    # Pass code directly
    uv run python utils/validate.py --code 'TEST W "Hello" Q'
    
    # Compare against both YDB and IRIS
    uv run python utils/validate.py --iris --code 'TEST W "Hello" Q'
    
    # Compare against IRIS only (skip YDB)
    uv run python utils/validate.py --no-ydb --iris --code 'TEST W $ZCV("hello","U") Q'
    
    # Debug mode (show AST and generated Python)
    uv run python utils/validate.py --debug --code 'TEST S X=1 W X Q'
    
    # Skip all comparisons (m2py only)
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
    parser.add_argument("--no-ydb", action="store_true", help="Skip YottaDB comparison")
    parser.add_argument(
        "--iris",
        action="store_true",
        help="Also compare against InterSystems IRIS",
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=5,
        help="Execution timeout in seconds for m2py, YDB, and IRIS (default: 5)",
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
    m2py_output, ast_str, python_code = run_m2py(
        source, debug=args.debug, timeout=args.timeout
    )

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

    use_ydb = not args.no_ydb
    use_iris = args.iris

    if not use_ydb and not use_iris:
        print(color("\n─── RESULT ───", Colors.YELLOW))
        print("Comparison skipped (--no-ydb, no --iris)")
        return 0

    # Run reference implementations
    ydb_output: str | None = None
    iris_output: str | None = None

    if use_ydb:
        ydb_output = run_ydb(source, timeout=args.timeout)
        print(color("\n─── YDB OUTPUT ───", Colors.BLUE))
        print(repr(ydb_output))

    if use_iris:
        iris_output = run_iris(source, timeout=max(args.timeout, 10))
        print(color("\n─── IRIS OUTPUT ───", Colors.BLUE))
        print(repr(iris_output))

    # Compare outputs
    print(color("\n─── RESULT ───", Colors.BOLD))
    exit_code = 0
    m2py_error = m2py_output.startswith("ERROR:")

    for label, ref_output in [("YDB", ydb_output), ("IRIS", iris_output)]:
        if ref_output is None:
            continue

        ref_error = ref_output.startswith("ERROR:")

        if m2py_error and ref_error:
            print(color(f"⚠️  BOTH ERRORED (m2py vs {label})", Colors.YELLOW))
            print(f"   m2py: {m2py_output.split(chr(10))[0]}")
            print(f"   {label.lower()}:  {ref_output.split(chr(10))[0]}")
            exit_code = max(exit_code, 2)
        elif m2py_error:
            print(color(f"❌ M2PY ERROR (vs {label})", Colors.RED))
            exit_code = max(exit_code, 1)
        elif ref_error:
            print(color(f"⚠️  {label} ERROR (m2py succeeded)", Colors.YELLOW))
            print(f"   {label.lower()}: {ref_output.split(chr(10))[0]}")
            exit_code = max(exit_code, 2)
        elif m2py_output == ref_output:
            print(color(f"✅ MATCH (m2py vs {label})", Colors.GREEN))
        else:
            print(color(f"❌ MISMATCH (m2py vs {label})", Colors.RED))
            print(f"\n   m2py: {repr(m2py_output)}")
            print(f"   {label.lower()}:  {repr(ref_output)}")
            _show_diff(m2py_output, ref_output, label)
            exit_code = max(exit_code, 1)

    # If both references ran, also compare them against each other
    if ydb_output is not None and iris_output is not None:
        ydb_err = ydb_output.startswith("ERROR:")
        iris_err = iris_output.startswith("ERROR:")
        if not ydb_err and not iris_err:
            if ydb_output == iris_output:
                print(color("✅ YDB == IRIS", Colors.GREEN))
            else:
                print(color("⚠️  YDB != IRIS", Colors.YELLOW))
                print(f"   ydb:  {repr(ydb_output)}")
                print(f"   iris: {repr(iris_output)}")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
