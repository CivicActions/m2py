#!/usr/bin/env python3
"""Compare shared state patterns for Phase 2.2 evaluation.

Run: uv run python specs/006-cross-label-control-flow/spikes/compare_shared_state.py
"""

import ast


def analyze_file(filepath: str) -> dict:
    """Count metrics for a file."""
    with open(filepath) as f:
        source = f.read()
        tree = ast.parse(source)

    lines = len(source.splitlines())
    functions = len([n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)])
    classes = len([n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)])

    # Count nonlocal statements (outer-scope pattern specific)
    nonlocals = len([n for n in ast.walk(tree) if isinstance(n, ast.Nonlocal)])

    return {
        "lines": lines,
        "functions": functions,
        "classes": classes,
        "nonlocals": nonlocals,
    }


def main():
    spikes = {
        "RoutineState Class": "specs/006-cross-label-control-flow/spikes/shared_state_class.py",
        "Outer-Scope Vars": "specs/006-cross-label-control-flow/spikes/shared_state_outer.py",
        "Runtime Dict": "specs/006-cross-label-control-flow/spikes/shared_state_runtime.py",
    }

    metrics = {name: analyze_file(path) for name, path in spikes.items()}

    print("=" * 70)
    print("SHARED STATE PATTERN COMPARISON")
    print("=" * 70)
    print()

    # Metrics table
    print(f"{'Metric':<20} {'Class':>15} {'Outer-Scope':>15} {'Runtime':>15}")
    print("-" * 70)
    print(
        f"{'Lines of code':<20} {metrics['RoutineState Class']['lines']:>15} {metrics['Outer-Scope Vars']['lines']:>15} {metrics['Runtime Dict']['lines']:>15}"
    )
    print(
        f"{'Functions':<20} {metrics['RoutineState Class']['functions']:>15} {metrics['Outer-Scope Vars']['functions']:>15} {metrics['Runtime Dict']['functions']:>15}"
    )
    print(
        f"{'Classes':<20} {metrics['RoutineState Class']['classes']:>15} {metrics['Outer-Scope Vars']['classes']:>15} {metrics['Runtime Dict']['classes']:>15}"
    )
    print(
        f"{'nonlocal stmts':<20} {metrics['RoutineState Class']['nonlocals']:>15} {metrics['Outer-Scope Vars']['nonlocals']:>15} {metrics['Runtime Dict']['nonlocals']:>15}"
    )
    print("-" * 70)
    print()

    # Evaluation matrix
    print("EVALUATION MATRIX")
    print("-" * 70)
    print()
    print(f"{'Criterion':<25} {'Class':>12} {'Outer':>12} {'Runtime':>12}")
    print("-" * 70)
    print(f"{'Rope: Rename Symbol':<25} {'GOOD':>12} {'MODERATE':>12} {'POOR':>12}")
    print(f"{'Rope: Extract Method':<25} {'GOOD':>12} {'POOR':>12} {'GOOD':>12}")
    print(f"{'Rope: Find References':<25} {'GOOD':>12} {'MODERATE':>12} {'POOR':>12}")
    print(f"{'IDE Autocomplete':<25} {'GOOD':>12} {'GOOD':>12} {'POOR':>12}")
    print(f"{'Type Checking':<25} {'GOOD':>12} {'MODERATE':>12} {'POOR':>12}")
    print(f"{'Dynamic Variables':<25} {'POOR':>12} {'POOR':>12} {'GOOD':>12}")
    print(f"{'Name Collision Risk':<25} {'LOW':>12} {'LOW':>12} {'HIGH':>12}")
    print(
        f"{'Subscript Support':<25} {'NEEDS WORK':>12} {'NEEDS WORK':>12} {'NATURAL':>12}"
    )
    print(
        f"{'Matches MUMPS Semantics':<25} {'MODERATE':>12} {'MODERATE':>12} {'GOOD':>12}"
    )
    print("-" * 70)
    print()

    # Analysis
    print("DETAILED ANALYSIS")
    print("-" * 70)
    print()

    print("1. RoutineState Class Pattern:")
    print("   STRENGTHS:")
    print("   - Best IDE/Rope support (symbols, autocomplete, type hints)")
    print("   - Fields are explicit and documented")
    print("   - Easy to pass state to helper functions")
    print("   WEAKNESSES:")
    print("   - Must pre-declare all variables")
    print("   - Dynamic variable creation awkward")
    print("   - Subscripted variables need MArray integration")
    print()

    print("2. Outer-Scope Variables Pattern:")
    print("   STRENGTHS:")
    print("   - Natural Python variable syntax")
    print("   - No class boilerplate for simple routines")
    print("   WEAKNESSES:")
    print("   - Must declare 'nonlocal' for EVERY write in EVERY label")
    print("   - Forgetting 'nonlocal' creates silent bugs")
    print("   - Hard to extract helper functions")
    print("   - Code gen must track which vars each label writes")
    print()

    print("3. Runtime Dict Pattern:")
    print("   STRENGTHS:")
    print("   - Perfect MUMPS semantics (dynamic creation, undefined=empty)")
    print("   - Natural fit for subscripted variables")
    print("   - Easy to implement NEW/KILL")
    print("   WEAKNESSES:")
    print("   - No IDE support (strings not symbols)")
    print("   - Typos in variable names not caught")
    print("   - Verbose syntax: rt.get('X') vs s.X")
    print()

    # Recommendation
    print("=" * 70)
    print("RECOMMENDATION: ROUTINESTATE CLASS PATTERN")
    print("=" * 70)
    print()
    print("Primary strategy: RoutineState dataclass with explicit fields")
    print()
    print("Rationale:")
    print("1. Best Rope refactorability (Rename, Extract, Find References)")
    print("2. IDE autocomplete catches variable name errors at edit time")
    print("3. Type hints enable static analysis")
    print("4. Clean syntax: s.X vs rt.get('X')")
    print("5. Natural fit with trampoline pattern (state passed through)")
    print()
    print("For subscripted variables (MArray):")
    print("- Add MArray instances as RoutineState fields")
    print("- Access: s.A[1, 2] or s.A.get(1, 2)")
    print("- Best of both: class-level organization + dict-like subscripts")
    print()
    print("Alternative for complex routines:")
    print("- If routine has many dynamic variables, consider hybrid:")
    print("  - Known variables as typed fields")
    print("  - Dynamic variables in s._vars dict")


if __name__ == "__main__":
    main()
