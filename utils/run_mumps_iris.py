#!/usr/bin/env python3
"""Run MUMPS code through InterSystems IRIS via Docker and print the output.

Uses a persistent Docker container (started on first use) to avoid the long
IRIS startup time on every invocation.

Usage:
    # Run a file
    uv run python utils/run_mumps_iris.py tests/functional/mugj/inref/V1FORA.m

    # Run from stdin
    echo -e 'TEST\\n write 1+2,!' | uv run python utils/run_mumps_iris.py -

    # Pass code directly
    uv run python utils/run_mumps_iris.py --code 'TEST W "Hello" Q'

    # Container management
    uv run python utils/run_mumps_iris.py --start   # Pre-start the container
    uv run python utils/run_mumps_iris.py --stop    # Stop and remove the container
"""

import argparse
import platform
import re
import subprocess
import sys
import time
import uuid
from pathlib import Path

CONTAINER_NAME = "m2py-iris"

# Select Docker image based on CPU architecture
_arch = platform.machine()
IMAGE = (
    "intersystems/iris-community-arm64:latest-cd"
    if _arch in ("aarch64", "arm64")
    else "intersystems/iris-community:latest-cd"
)

# Sentinel characters to delimit routine output (unlikely in real output)
_START_SENTINEL = "\x01\x02\x03"
_END_SENTINEL = "\x03\x02\x01"


def _container_status() -> str:
    """Return 'running', 'stopped', or 'absent'."""
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.Status}}", CONTAINER_NAME],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return "absent"
    status = result.stdout.strip()
    if status == "running":
        return "running"
    return "stopped"


def _wait_for_ready(max_wait: int = 120) -> None:
    """Wait for IRIS to accept session connections."""
    start = time.time()
    while time.time() - start < max_wait:
        try:
            result = subprocess.run(
                [
                    "docker",
                    "exec",
                    "-i",
                    CONTAINER_NAME,
                    "iris",
                    "session",
                    "IRIS",
                    "-U",
                    "USER",
                ],
                input="H\n",
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and "USER>" in result.stdout:
                return
        except subprocess.TimeoutExpired:
            pass
        time.sleep(2)
    raise RuntimeError(f"IRIS container did not become ready within {max_wait}s")


def start_container() -> None:
    """Start the IRIS container if not already running."""
    status = _container_status()
    if status == "running":
        return

    if status == "stopped":
        subprocess.run(
            ["docker", "start", CONTAINER_NAME],
            capture_output=True,
        )
    else:
        # Create new container
        result = subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                CONTAINER_NAME,
                IMAGE,
                "--check-caps",
                "false",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Failed to start IRIS container: {result.stderr.strip()}"
            )

    _wait_for_ready()


def stop_container() -> None:
    """Stop and remove the IRIS container."""
    subprocess.run(
        ["docker", "rm", "-f", CONTAINER_NAME],
        capture_output=True,
    )


def _find_entry_label(source: str) -> str | None:
    """Find the first label in MUMPS source (same logic as ydb.py)."""
    for line in source.split("\n"):
        line = line.rstrip()
        if (
            line
            and not line.startswith(";")
            and not line.startswith(" ")
            and not line.startswith("\t")
        ):
            parts = line.split()
            if parts:
                return parts[0].split("(")[0]
    return None


def _escape_for_mumps_string(s: str) -> str:
    """Escape a string for use inside a MUMPS double-quoted string literal."""
    return s.replace('"', '""')


def _parse_output(raw: str) -> str:
    """Extract the routine output from IRIS session output using sentinels."""
    start_idx = raw.find(_START_SENTINEL)
    end_idx = raw.find(_END_SENTINEL)

    if start_idx != -1 and end_idx != -1:
        # Both sentinels found — clean extraction
        return raw[start_idx + len(_START_SENTINEL) : end_idx]

    if start_idx != -1:
        # Only start sentinel (routine errored or halted before end sentinel)
        tail = raw[start_idx + len(_START_SENTINEL) :]
        # Strip IRIS prompts from the tail
        tail = re.sub(r"\n?USER\s*\w*>\s*", "", tail)
        return tail.rstrip()

    # No sentinels — fallback: strip all IRIS framing
    lines = raw.split("\n")
    filtered = []
    for line in lines:
        if re.match(r"^Node:", line):
            continue
        if re.match(r"^USER\s*\w*>\s*$", line):
            continue
        if "Compiling routine" in line:
            continue
        filtered.append(line)
    return "\n".join(filtered).strip()


def run_iris(source: str, timeout: int = 10) -> str:
    """Run MUMPS source through IRIS via Docker.

    Args:
        source: MUMPS source code
        timeout: Timeout in seconds

    Returns:
        Output from IRIS execution
    """
    try:
        start_container()
    except RuntimeError as e:
        return f"ERROR: {e}"

    entry_label = _find_entry_label(source)
    if not entry_label:
        return "ERROR: No entry label found in source"

    routine_name = f"m2pyT{uuid.uuid4().hex[:8]}"

    # Build IRIS commands to create, save, compile, execute, and clean up
    cmd_lines: list[str] = []

    # Create routine via %Routine API
    cmd_lines.append(f'S rtn=##class(%Routine).%New("{routine_name}")')

    source_lines = source.split("\n")
    # Remove trailing empty line (artifact of trailing newline in source)
    if source_lines and source_lines[-1] == "":
        source_lines = source_lines[:-1]

    for src_line in source_lines:
        escaped = _escape_for_mumps_string(src_line)
        cmd_lines.append(f'D rtn.WriteLine("{escaped}")')

    cmd_lines.append("S sc=rtn.Save()")
    cmd_lines.append("S sc=rtn.Compile()")

    # Execute with sentinels on a single line so no prompts appear between them
    cmd_lines.append(f"W $C(1,2,3) D {entry_label}^{routine_name} W $C(3,2,1)")

    # Clean up the routine (best-effort; may not run if routine HALTed)
    cmd_lines.append(f'D ##class(%Routine).Delete("{routine_name}")')

    # Terminate session
    cmd_lines.append("H")

    commands = "\n".join(cmd_lines) + "\n"

    try:
        result = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                CONTAINER_NAME,
                "iris",
                "session",
                "IRIS",
                "-U",
                "USER",
            ],
            input=commands,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        output = result.stdout
        if result.stderr:
            output += result.stderr

        return _parse_output(output).strip()

    except subprocess.TimeoutExpired:
        return f"ERROR: IRIS execution timed out after {timeout}s"
    except FileNotFoundError:
        return "ERROR: Docker not found. Is Docker installed and running?"
    except Exception as e:
        return f"ERROR: {e}"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run MUMPS code through InterSystems IRIS via Docker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run a file
    uv run python utils/run_mumps_iris.py routine.m

    # Run from stdin
    echo -e 'TEST\\n write 1+2,!' | uv run python utils/run_mumps_iris.py -

    # Pass code directly
    uv run python utils/run_mumps_iris.py --code 'TEST W "Hello" Q'

    # Manage the container
    uv run python utils/run_mumps_iris.py --start   # Start the container
    uv run python utils/run_mumps_iris.py --stop    # Stop and remove
        """,
    )
    parser.add_argument(
        "file", nargs="?", default=None, help="MUMPS file to run (use - for stdin)"
    )
    parser.add_argument(
        "--code", "-c", type=str, help="M code to run directly (instead of file)"
    )
    parser.add_argument(
        "--timeout",
        "-t",
        type=int,
        default=10,
        help="Execution timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--start",
        action="store_true",
        help="Start the IRIS container (pre-warm)",
    )
    parser.add_argument(
        "--stop",
        action="store_true",
        help="Stop and remove the IRIS container",
    )

    args = parser.parse_args()

    # Container management commands
    if args.stop:
        stop_container()
        print("IRIS container stopped.", file=sys.stderr)
        return 0

    if args.start:
        try:
            start_container()
            print("IRIS container is running.", file=sys.stderr)
        except RuntimeError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 1
        return 0

    # Get source code
    if args.code:
        source = args.code.replace("\\n", "\n").replace("\\t", "\t")
    elif args.file == "-":
        source = sys.stdin.read()
    elif args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"ERROR: File not found: {path}", file=sys.stderr)
            return 1
        source = path.read_text()
    else:
        parser.error("Must provide a file, use - for stdin, or use --code")

    output = run_iris(source, timeout=args.timeout)

    if output.startswith("ERROR:"):
        print(output, file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
