#!/usr/bin/env python3
"""Debug script to investigate DO block parsing with dot lines."""

from m2py.parser import MUMPSParser

parser = MUMPSParser()


def analyze_case(name: str, code: str):
    print(f"\n{'=' * 60}")
    print(f"=== {name} ===")
    print(f"Code:\n{code}")
    print("-" * 60)

    routine = parser.parse(code)

    for label in routine.labels:
        print(f"\nLabel: {label.name}")
        stmts = label.body.statements if label.body else []
        print(f"  Statements: {len(stmts)}")
        for i, stmt in enumerate(stmts):
            print(f"    [{i}] {stmt.__class__.__name__}", end="")
            if hasattr(stmt, "_dot_level"):
                print(f" (dot_level={stmt._dot_level})", end="")
            if getattr(stmt, "is_unreachable", False):
                print(" [UNREACHABLE]", end="")
            print()

            # For FOR statements, show body
            if hasattr(stmt, "body") and stmt.body and stmt.body.statements:
                print(f"        FOR body ({len(stmt.body.statements)} stmts):")
                for j, body_stmt in enumerate(stmt.body.statements):
                    print(f"          [{j}] {body_stmt.__class__.__name__}", end="")
                    # For DO, show its body
                    if hasattr(body_stmt, "body") and body_stmt.body:
                        do_stmts = body_stmt.body.statements
                        print(f" (DO body: {len(do_stmts)} stmts)", end="")
                    if hasattr(body_stmt, "targets") and body_stmt.targets:
                        print(
                            f" targets={[t.label for t in body_stmt.targets]}", end=""
                        )
                    print()


# Test 1: D alone on its line - WORKS
analyze_case(
    "Test 1: D alone on line",
    """\
TEST
 F I=1:1:5 D
 . W I
 Q
""",
)

# Test 2: D followed by Q on same line - BROKEN
analyze_case(
    "Test 2: D followed by Q on same line",
    """\
TEST
 S X=3
 F  D  Q:X=0
 . S X=X-1
 . W X
 Q
""",
)

# Test 3: Simpler case - D followed by another command on same line
analyze_case(
    "Test 3: D followed by W on same line",
    """\
TEST
 F I=1:1:3 D  W "after"
 . W I
 Q
""",
)
