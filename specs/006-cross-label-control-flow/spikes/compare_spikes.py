#!/usr/bin/env python3
"""Analyze and compare spike prototypes."""

import ast


def analyze_file(filepath):
    """Count complexity metrics for a file."""
    with open(filepath) as f:
        tree = ast.parse(f.read())

    functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
    classes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    match_cases = [node for node in ast.walk(tree) if isinstance(node, ast.match_case)]
    branches = sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, (ast.If, ast.While, ast.For, ast.ExceptHandler))
    )

    return {
        "functions": len(functions),
        "classes": len(classes),
        "match_cases": len(match_cases),
        "branches": branches,
    }


def main():
    trampoline = "specs/006-cross-label-control-flow/spikes/trampoline_v1go1.py"
    statemachine = "specs/006-cross-label-control-flow/spikes/state_machine_v1go1.py"

    t_metrics = analyze_file(trampoline)
    s_metrics = analyze_file(statemachine)

    # Line counts
    with open(trampoline) as f:
        t_lines = len(f.readlines())
    with open(statemachine) as f:
        s_lines = len(f.readlines())

    print("=" * 60)
    print("STRATEGY BAKE-OFF COMPARISON: V1GO1.m")
    print("=" * 60)
    print()
    print(f"{'Metric':<25} {'Trampoline':>15} {'State Machine':>15}")
    print("-" * 60)
    print(f"{'Lines of code':<25} {t_lines:>15} {s_lines:>15}")
    print(
        f"{'Functions':<25} {t_metrics['functions']:>15} {s_metrics['functions']:>15}"
    )
    print(f"{'Classes':<25} {t_metrics['classes']:>15} {s_metrics['classes']:>15}")
    print(
        f"{'Match cases':<25} {t_metrics['match_cases']:>15} {s_metrics['match_cases']:>15}"
    )
    print(
        f"{'Branch statements':<25} {t_metrics['branches']:>15} {s_metrics['branches']:>15}"
    )
    print("-" * 60)
    print()

    # Refactorability analysis
    print("REFACTORABILITY ANALYSIS:")
    print("-" * 60)
    print()
    print("Trampoline pattern:")
    print("  + Each label is a separate function - easily extractable")
    print("  + Functions can be renamed independently via Rope")
    print("  + New labels add new functions without touching dispatch")
    print("  + State explicitly passed - easy to test individual labels")
    print("  - More boilerplate (function signatures, decorators)")
    print()
    print("State machine pattern:")
    print("  + All logic in single function - simpler scoping")
    print("  + match/case naturally maps to label dispatch")
    print("  + Fewer lines of code overall")
    print("  - Extracting a case to function requires manual refactor")
    print("  - Single large function harder to test in isolation")
    print("  - Variables must use 'nonlocal' for nested write access")
    print()

    # VistA implications
    print("VISTA PRODUCTION IMPLICATIONS:")
    print("-" * 60)
    print()
    print("From VistA analysis (R2.5): 47.5% of files have cycles")
    print()
    print("Trampoline pattern:")
    print("  + Handles cycles naturally (returns to dispatch loop)")
    print("  + Bounded stack depth (1 frame per dispatch iteration)")
    print("  + Backward jumps are just another dispatch")
    print()
    print("State machine pattern:")
    print("  + Also handles cycles naturally (state = reassignment)")
    print("  + No recursion - single while loop")
    print("  + Similar bounded complexity")
    print()

    # Recommendation
    print("=" * 60)
    print("RECOMMENDATION: TRAMPOLINE PATTERN")
    print("=" * 60)
    print()
    print("Rationale:")
    print("1. Better decomposition - labels as functions map naturally to")
    print("   MUMPS routine structure and support IDE navigation")
    print("2. Easier to test individual label functions in isolation")
    print("3. Better Rope refactorability for extract/rename operations")
    print("4. Code gen is more uniform - same pattern for each label")
    print("5. Line count difference (102 lines) is acceptable for benefits")
    print()
    print("The state machine pattern is simpler but the trampoline pattern")
    print("provides better maintainability for real-world VistA routines")
    print("which may have 100+ labels per file.")


if __name__ == "__main__":
    main()
