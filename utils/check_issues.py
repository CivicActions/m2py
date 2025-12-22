#!/usr/bin/env python3
"""Check specific ASG issues for validation."""

from m2py.parser import MUMPSParser


def check_unreachable_code():
    """Check if statements after QUIT are marked unreachable."""
    print("=" * 60)
    print("CHECK: Unreachable code detection after QUIT")
    print("=" * 60)
    
    parser = MUMPSParser()
    routine = parser.parse_file('tests/functional/mugj/inref/V1PRGD.m')
    parser.resolve_references(routine)

    # Check label 2 which has QUIT followed by more statements
    for label in routine.labels:
        if label.name == '2':
            print(f"Label: {label.name}")
            print(f"  has_explicit_exit: {label.has_explicit_exit}")
            for i, stmt in enumerate(label.body.statements):
                stmt_name = stmt.__class__.__name__
                unreachable = getattr(stmt, 'is_unreachable', False)
                print(f"  [{i}] {stmt_name} (is_unreachable={unreachable})")
            break
    print()


def check_implicit_quit():
    """Check if labels without explicit QUIT have has_explicit_exit=False."""
    print("=" * 60)
    print("CHECK: Implicit QUIT detection (has_explicit_exit)")
    print("=" * 60)
    
    parser = MUMPSParser()
    routine = parser.parse_file('tests/functional/mugj/inref/V1PRGD2.m')
    parser.resolve_references(routine)

    for label in routine.labels:
        print(f"Label: {label.name}")
        print(f"  has_explicit_exit: {label.has_explicit_exit}")
        if label.body and label.body.statements:
            last_stmt = label.body.statements[-1]
            print(f"  Last statement: {last_stmt.__class__.__name__}")
        else:
            print("  (no statements)")
    print()


def check_goto_postconditions():
    """Verify GOTO target postconditions and offsets are captured."""
    print("=" * 60)
    print("CHECK: GOTO target postconditions and offsets")
    print("=" * 60)
    
    parser = MUMPSParser()
    routine = parser.parse_file('tests/functional/mugj/inref/V1PCA.m')
    parser.resolve_references(routine)

    # Check label 838: G:$D(PC) BUG+2:" ,"=",",TABLE+1:$F(1E-2,".")
    for label in routine.labels:
        if label.name == '838':
            print(f"Label: {label.name}")
            for i, stmt in enumerate(label.body.statements):
                stmt_name = stmt.__class__.__name__
                if stmt_name == 'MGotoStatement':
                    print(f"  [{i}] {stmt_name}")
                    if hasattr(stmt, 'postcondition') and stmt.postcondition:
                        print(f"      stmt.postcondition: {type(stmt.postcondition).__name__}")
                    for j, target in enumerate(stmt.targets):
                        print(f"      target[{j}]: name={repr(target.name)}")
                        print(f"                 offset={target.offset}")
                        print(f"                 postcondition={type(target.postcondition).__name__ if target.postcondition else None}")
            break
    print()


def check_do_postconditions():
    """Verify DO target postconditions and offsets are captured."""
    print("=" * 60)
    print("CHECK: DO target postconditions and offsets")
    print("=" * 60)
    
    parser = MUMPSParser()
    routine = parser.parse_file('tests/functional/mugj/inref/V1PCB.m')
    parser.resolve_references(routine)

    # Check label 843 which has D BYTE+2:$D(A),BYTE+1:'$D(A)
    for label in routine.labels:
        if label.name == '843':
            print(f"Label: {label.name}")
            for i, stmt in enumerate(label.body.statements):
                stmt_name = stmt.__class__.__name__
                if stmt_name == 'MDoStatement':
                    print(f"  [{i}] {stmt_name}")
                    for j, target in enumerate(stmt.targets):
                        if target.__class__.__name__ == 'MCall':
                            print(f"      target[{j}]: name={repr(target.name)}")
                            print(f"                 offset={target.offset}")
                            print(f"                 postcondition={type(target.postcondition).__name__ if target.postcondition else None}")
            break
    print()


if __name__ == "__main__":
    check_goto_postconditions()
    check_do_postconditions()
    check_unreachable_code()
    check_implicit_quit()
