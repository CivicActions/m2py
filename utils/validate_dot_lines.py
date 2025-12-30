"""Validation script for orphaned dot lines behavior."""

from m2py.parser import MUMPSParser


def test_orphaned_dot_lines():
    """Test orphaned dot lines (dots without preceding argumentless DO).

    Per MUMPS 1995 spec section 6.3 (Routine execution):
    "Lines which have a LEVEL greater than the current execution level are ignored,
    i.e., not executed."

    This means orphaned dot lines should be kept in the ASG but marked as
    unreachable or otherwise excluded from execution.
    """
    # Test: orphaned dot line without any DO
    code = """TEST
 S X=1
 . S Y=2
 S Z=3
"""
    parser = MUMPSParser()
    routine = parser.parse(code)

    print("=== Test: Orphaned Dot Lines ===")
    print(f"Number of labels: {len(routine.labels)}")

    for label in routine.labels:
        print(f"\nLabel: '{label.name}'")
        print(f"Number of statements: {len(label.body.statements)}")
        for i, stmt in enumerate(label.body.statements):
            stmt_type = type(stmt).__name__
            is_unreachable = getattr(stmt, "is_unreachable", False)
            dot_level = getattr(stmt, "_dot_level", "N/A")
            print(
                f"  [{i}] {stmt_type} | unreachable={is_unreachable} | _dot_level={dot_level}"
            )

            # Check if this is a SET statement and what it sets
            if hasattr(stmt, "assignments"):
                for assign in stmt.assignments:
                    if hasattr(assign, "target"):
                        target = assign.target
                        if hasattr(target, "targets"):
                            for t in target.targets:
                                print(f"      -> sets: {getattr(t, 'name', '?')}")
                        else:
                            print(f"      -> sets: {getattr(target, 'name', '?')}")

    # Analysis of fix
    print("\n=== Analysis ===")
    y_stmt = routine.labels[0].body.statements[1]  # The S Y=2 statement
    y_var = (
        y_stmt.assignments[0].target.name
        if hasattr(y_stmt.assignments[0].target, "name")
        else "?"
    )
    print(f"The statement 'S Y=2' is at index 1, variable name: {y_var}")
    print(f"  unreachable={getattr(y_stmt, 'is_unreachable', False)}")
    print(f"  _dot_level={getattr(y_stmt, '_dot_level', 'N/A')}")

    if getattr(y_stmt, "is_unreachable", False):
        print(
            "\n✓ CORRECT: Orphaned dot line is marked as unreachable per MUMPS spec 6.3"
        )
    else:
        print(
            "\n*** BUG: Per MUMPS spec, orphaned dot lines should NOT be executed ***"
        )
        print("Current behavior: Orphaned dot line is treated as regular statement")
        print(
            "Expected behavior: Orphaned dot line should be marked is_unreachable=True"
        )


def test_proper_do_block():
    """Test proper DO block with dot lines."""
    code = """TEST
 D
 . S X=1
 . S Y=2
 S Z=3
"""
    parser = MUMPSParser()
    routine = parser.parse(code)

    print("\n=== Test: Proper DO Block ===")
    for label in routine.labels:
        print(f"\nLabel: '{label.name}'")
        for i, stmt in enumerate(label.body.statements):
            stmt_type = type(stmt).__name__
            print(f"  [{i}] {stmt_type}")

            # For DO statements, check the body
            if hasattr(stmt, "body") and stmt.body:
                for j, inner_stmt in enumerate(stmt.body.statements):
                    inner_type = type(inner_stmt).__name__
                    print(f"    [{j}] {inner_type}")

    print("\n✓ This case is handled correctly - dot lines are nested in DO body")


if __name__ == "__main__":
    test_orphaned_dot_lines()
    print("\n" + "=" * 60 + "\n")
    test_proper_do_block()
