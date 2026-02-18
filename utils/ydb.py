#!/usr/bin/env python3
"""Run MUMPS code through YottaDB via Docker and print the output.

Usage:
    # Run a file
    uv run python utils/ydb.py tests/functional/mugj/inref/V1FORA.m

    # Run from stdin
    echo -e 'TEST\\n write 1+2,!' | uv run python utils/ydb.py -

    # Pass code directly
    uv run python utils/ydb.py --code 'TEST W "Hello" Q'
"""

import argparse
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path


def run_ydb(source: str, timeout: int = 5) -> str:
    """Run MUMPS source through YottaDB via Docker with hard timeout.

    Args:
        source: MUMPS source code
        timeout: Timeout in seconds (container will be force-killed if exceeded)

    Returns:
        Output from YottaDB execution
    """
    # Write source to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".m", delete=False) as f:
        f.write(source)
        temp_path = Path(f.name)

    # Generate unique container name for cleanup
    container_name = f"m2py-ydb-{uuid.uuid4().hex[:12]}"

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

        # Run YottaDB via Docker with named container
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
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
        # Force kill the container
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                timeout=5,
            )
        except Exception:
            pass
        return f"ERROR: YottaDB execution timed out after {timeout}s (container force-killed)"
    except FileNotFoundError:
        return "ERROR: Docker not found. Is Docker installed and running?"
    except Exception as e:
        return f"ERROR: {e}"
    finally:
        # Clean up temp file
        temp_path.unlink(missing_ok=True)
        # Ensure container is removed even on success (in case --rm failed)
        try:
            subprocess.run(
                ["docker", "rm", "-f", container_name],
                capture_output=True,
                timeout=5,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run MUMPS code through YottaDB via Docker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Run a file
    uv run python utils/ydb.py routine.m

    # Run from stdin
    echo -e 'TEST\\n write 1+2,!' | uv run python utils/ydb.py -

    # Pass code directly
    uv run python utils/ydb.py --code 'TEST W "Hello" Q'
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
        default=5,
        help="Execution timeout in seconds (default: 5)",
    )

    args = parser.parse_args()

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

    output = run_ydb(source, timeout=args.timeout)

    if output.startswith("ERROR:"):
        print(output, file=sys.stderr)
        return 1

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
