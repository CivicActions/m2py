#!/usr/bin/env python3
"""Analyze GOTO patterns in VistA codebase using m2py parser.

Uses the actual m2py parser and ASG for accurate analysis, avoiding regex pitfalls.
Generates per-module statistics to identify variability across VistA packages.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Import m2py parser and analysis
from m2py.parser import MUMPSParser
from m2py.analysis.resolver import resolve_references
from m2py.analysis.goto_analysis import classify_gotos
from m2py.asg.statements import MGotoStatement
from m2py.asg.enums import GotoType


@dataclass
class ModuleStats:
    """Statistics for a VistA module (package)."""

    name: str
    files_total: int = 0
    files_parsed: int = 0
    files_with_gotos: int = 0
    files_failed: int = 0

    total_gotos: int = 0
    cross_label_forward: int = 0
    cross_label_backward: int = 0
    intra_label_forward: int = 0
    intra_label_backward: int = 0
    loop_exit: int = 0
    multi_loop_exit: int = 0
    external: int = 0
    unresolved: int = 0

    conditional_gotos: int = 0
    files_with_cycles: int = 0
    total_cycles: int = 0

    # Examples for this module
    cycle_examples: List[Dict] = field(default_factory=list)
    backward_examples: List[Dict] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "files_total": self.files_total,
            "files_parsed": self.files_parsed,
            "files_with_gotos": self.files_with_gotos,
            "files_failed": self.files_failed,
            "total_gotos": self.total_gotos,
            "cross_label_forward": self.cross_label_forward,
            "cross_label_backward": self.cross_label_backward,
            "intra_label_forward": self.intra_label_forward,
            "intra_label_backward": self.intra_label_backward,
            "loop_exit": self.loop_exit,
            "multi_loop_exit": self.multi_loop_exit,
            "external": self.external,
            "unresolved": self.unresolved,
            "conditional_gotos": self.conditional_gotos,
            "files_with_cycles": self.files_with_cycles,
            "total_cycles": self.total_cycles,
        }


def analyze_routine(parser: MUMPSParser, filepath: Path) -> Optional[Dict]:
    """Parse a routine and extract GOTO statistics using ASG."""
    try:
        routine = parser.parse_file(str(filepath))
        resolve_references(routine)
        classify_gotos(routine)
    except Exception as e:
        return {"error": str(e), "file": str(filepath)}

    stats = {
        "file": str(filepath),
        "labels": [lbl.name for lbl in routine.labels],
        "has_unstructured_goto": routine.has_unstructured_goto,
        "gotos": [],
        "cross_label_forward": 0,
        "cross_label_backward": 0,
        "intra_label_forward": 0,
        "intra_label_backward": 0,
        "loop_exit": 0,
        "multi_loop_exit": 0,
        "external": 0,
        "unresolved": 0,
        "conditional": 0,
    }

    # Build label position map
    label_positions = {lbl.name: i for i, lbl in enumerate(routine.labels)}

    # Collect all GOTOs
    for label in routine.labels:
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                for target in stmt.targets:
                    goto_info = {
                        "source": label.name,
                        "target": target.name,
                        "type": stmt.goto_type.name if stmt.goto_type else "UNKNOWN",
                        "is_cross_label": stmt.is_cross_label,
                        "has_postcondition": stmt.postcondition is not None,
                        "line": stmt.line_number,
                    }
                    stats["gotos"].append(goto_info)

                    # Count by type
                    if stmt.postcondition is not None:
                        stats["conditional"] += 1

                    if stmt.goto_type == GotoType.EXTERNAL:
                        stats["external"] += 1
                    elif stmt.goto_type == GotoType.UNRESOLVED:
                        stats["unresolved"] += 1
                    elif stmt.goto_type == GotoType.LOOP_EXIT:
                        stats["loop_exit"] += 1
                    elif stmt.goto_type == GotoType.MULTI_LOOP_EXIT:
                        stats["multi_loop_exit"] += 1
                    elif stmt.goto_type == GotoType.FORWARD_JUMP:
                        if stmt.is_cross_label:
                            stats["cross_label_forward"] += 1
                        else:
                            stats["intra_label_forward"] += 1
                    elif stmt.goto_type == GotoType.BACKWARD_JUMP:
                        if stmt.is_cross_label:
                            stats["cross_label_backward"] += 1
                        else:
                            stats["intra_label_backward"] += 1

    # Check for cycles
    stats["cycles"] = detect_cycles(routine, label_positions)

    return stats


def detect_cycles(routine, label_positions: Dict[str, int]) -> List[List[str]]:
    """Detect cyclic GOTO patterns in a routine using DFS."""
    # Build adjacency graph from GOTOs
    graph = defaultdict(set)

    for label in routine.labels:
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                for target in stmt.targets:
                    if target.name in label_positions:
                        graph[label.name].add(target.name)

    # Find cycles using DFS with color marking
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {lbl.name: WHITE for lbl in routine.labels}
    cycles = []

    def dfs(node, path):
        color[node] = GRAY
        path.append(node)

        for next_node in graph.get(node, []):
            if color.get(next_node, WHITE) == GRAY:
                # Found a back edge - cycle
                cycle_start = path.index(next_node)
                cycles.append(path[cycle_start:] + [next_node])
            elif color.get(next_node, WHITE) == WHITE:
                dfs(next_node, path)

        color[node] = BLACK
        path.pop()

    for label in routine.labels:
        if color[label.name] == WHITE:
            dfs(label.name, [])

    return cycles


def get_module_name(filepath: Path) -> str:
    """Extract module name from VistA path."""
    parts = filepath.parts
    try:
        packages_idx = parts.index("Packages")
        if packages_idx + 1 < len(parts):
            return parts[packages_idx + 1]
    except ValueError:
        pass
    return "Unknown"


def analyze_vista(
    vista_path: Path, max_files: int = None, verbose: bool = False
) -> Dict[str, ModuleStats]:
    """Analyze GOTO patterns across VistA codebase by module."""
    parser = MUMPSParser()
    modules: Dict[str, ModuleStats] = defaultdict(lambda: ModuleStats(name=""))

    # Find all .m files
    m_files = sorted(vista_path.rglob("*.m"))
    if max_files:
        m_files = m_files[:max_files]

    total = len(m_files)
    errors = []

    for i, filepath in enumerate(m_files):
        if verbose and i % 500 == 0:
            print(f"  Processing {i}/{total}...", file=sys.stderr)

        module_name = get_module_name(filepath)
        if modules[module_name].name == "":
            modules[module_name].name = module_name

        mod = modules[module_name]
        mod.files_total += 1

        result = analyze_routine(parser, filepath)

        if result is None:
            mod.files_failed += 1
            continue

        if "error" in result:
            mod.files_failed += 1
            if len(errors) < 20:
                errors.append(result)
            continue

        mod.files_parsed += 1

        if result["gotos"]:
            mod.files_with_gotos += 1
            mod.total_gotos += len(result["gotos"])
            mod.cross_label_forward += result["cross_label_forward"]
            mod.cross_label_backward += result["cross_label_backward"]
            mod.intra_label_forward += result["intra_label_forward"]
            mod.intra_label_backward += result["intra_label_backward"]
            mod.loop_exit += result["loop_exit"]
            mod.multi_loop_exit += result["multi_loop_exit"]
            mod.external += result["external"]
            mod.unresolved += result["unresolved"]
            mod.conditional_gotos += result["conditional"]

            if result["cycles"]:
                mod.files_with_cycles += 1
                mod.total_cycles += len(result["cycles"])

                # Store examples
                if len(mod.cycle_examples) < 5:
                    for cycle in result["cycles"][:2]:
                        mod.cycle_examples.append(
                            {"file": filepath.name, "cycle": cycle}
                        )

            # Store backward jump examples
            if result["cross_label_backward"] > 0 and len(mod.backward_examples) < 5:
                for goto in result["gotos"]:
                    if goto["type"] == "BACKWARD_JUMP" and goto["is_cross_label"]:
                        mod.backward_examples.append(
                            {
                                "file": filepath.name,
                                "line": goto["line"],
                                "from": goto["source"],
                                "to": goto["target"],
                            }
                        )
                        break

    return dict(modules), errors


def print_summary(modules: Dict[str, ModuleStats], errors: List[Dict]):
    """Print overall summary across all modules."""
    print("=" * 80)
    print("VISTA GOTO PATTERN ANALYSIS (Using m2py Parser)")
    print("=" * 80)

    # Aggregate totals
    totals = ModuleStats(name="TOTAL")
    for mod in modules.values():
        totals.files_total += mod.files_total
        totals.files_parsed += mod.files_parsed
        totals.files_with_gotos += mod.files_with_gotos
        totals.files_failed += mod.files_failed
        totals.total_gotos += mod.total_gotos
        totals.cross_label_forward += mod.cross_label_forward
        totals.cross_label_backward += mod.cross_label_backward
        totals.intra_label_forward += mod.intra_label_forward
        totals.intra_label_backward += mod.intra_label_backward
        totals.loop_exit += mod.loop_exit
        totals.multi_loop_exit += mod.multi_loop_exit
        totals.external += mod.external
        totals.unresolved += mod.unresolved
        totals.conditional_gotos += mod.conditional_gotos
        totals.files_with_cycles += mod.files_with_cycles
        totals.total_cycles += mod.total_cycles

    print("\n📁 FILES ANALYZED")
    print(f"   Total .m files: {totals.files_total:,}")
    print(
        f"   Successfully parsed: {totals.files_parsed:,} ({100 * totals.files_parsed / max(1, totals.files_total):.1f}%)"
    )
    print(
        f"   Files with GOTOs: {totals.files_with_gotos:,} ({100 * totals.files_with_gotos / max(1, totals.files_parsed):.1f}% of parsed)"
    )
    print(f"   Parse failures: {totals.files_failed:,}")

    print(f"\n📊 GOTO STATISTICS (Total: {totals.total_gotos:,})")
    print(
        f"   Cross-label FORWARD:  {totals.cross_label_forward:,} ({100 * totals.cross_label_forward / max(1, totals.total_gotos):.1f}%)"
    )
    print(
        f"   Cross-label BACKWARD: {totals.cross_label_backward:,} ({100 * totals.cross_label_backward / max(1, totals.total_gotos):.1f}%)"
    )
    print(
        f"   Intra-label FORWARD:  {totals.intra_label_forward:,} ({100 * totals.intra_label_forward / max(1, totals.total_gotos):.1f}%)"
    )
    print(
        f"   Intra-label BACKWARD: {totals.intra_label_backward:,} ({100 * totals.intra_label_backward / max(1, totals.total_gotos):.1f}%)"
    )
    print(
        f"   Loop exit (single):   {totals.loop_exit:,} ({100 * totals.loop_exit / max(1, totals.total_gotos):.1f}%)"
    )
    print(
        f"   Loop exit (multi):    {totals.multi_loop_exit:,} ({100 * totals.multi_loop_exit / max(1, totals.total_gotos):.1f}%)"
    )
    print(
        f"   External (^routine):  {totals.external:,} ({100 * totals.external / max(1, totals.total_gotos):.1f}%)"
    )
    print(
        f"   Unresolved:           {totals.unresolved:,} ({100 * totals.unresolved / max(1, totals.total_gotos):.1f}%)"
    )
    print(
        f"   Conditional:          {totals.conditional_gotos:,} ({100 * totals.conditional_gotos / max(1, totals.total_gotos):.1f}%)"
    )

    print("\n🔄 CYCLE ANALYSIS")
    print(
        f"   Files with cycles: {totals.files_with_cycles:,} ({100 * totals.files_with_cycles / max(1, totals.files_with_gotos):.1f}% of GOTO files)"
    )
    print(f"   Total cycles: {totals.total_cycles:,}")

    # Key metrics for architecture decision
    cross_label_total = totals.cross_label_forward + totals.cross_label_backward
    needs_trampoline = totals.cross_label_backward + totals.intra_label_backward

    print("\n🎯 ARCHITECTURE DECISION METRICS")
    print(
        f"   Cross-label GOTOs (Spec 006 scope): {cross_label_total:,} ({100 * cross_label_total / max(1, totals.total_gotos):.1f}%)"
    )
    print(
        f"   Backward jumps (need trampoline):   {needs_trampoline:,} ({100 * needs_trampoline / max(1, totals.total_gotos):.1f}%)"
    )
    print(f"   Files with cycles (need trampoline): {totals.files_with_cycles:,}")


def print_module_table(modules: Dict[str, ModuleStats]):
    """Print per-module statistics table."""
    print("\n" + "=" * 80)
    print("PER-MODULE STATISTICS")
    print("=" * 80)

    # Sort by total GOTOs descending
    sorted_mods = sorted(modules.values(), key=lambda m: m.total_gotos, reverse=True)

    print(
        f"\n{'Module':<40} {'Files':>6} {'GOTOs':>7} {'X-Fwd':>6} {'X-Bwd':>6} {'Cycles':>6} {'%Cyc':>5}"
    )
    print("-" * 80)

    for mod in sorted_mods[:30]:  # Top 30 modules
        cycle_pct = 100 * mod.files_with_cycles / max(1, mod.files_with_gotos)
        print(
            f"{mod.name[:39]:<40} {mod.files_parsed:>6} {mod.total_gotos:>7} "
            f"{mod.cross_label_forward:>6} {mod.cross_label_backward:>6} "
            f"{mod.files_with_cycles:>6} {cycle_pct:>4.0f}%"
        )

    if len(sorted_mods) > 30:
        print(f"... and {len(sorted_mods) - 30} more modules")


def print_cycle_examples(modules: Dict[str, ModuleStats]):
    """Print cycle examples from various modules."""
    print("\n" + "=" * 80)
    print("CYCLE EXAMPLES (by module)")
    print("=" * 80)

    examples_shown = 0
    for mod in sorted(modules.values(), key=lambda m: m.total_cycles, reverse=True):
        if mod.cycle_examples and examples_shown < 15:
            print(f"\n{mod.name}:")
            for ex in mod.cycle_examples[:3]:
                cycle_str = " → ".join(ex["cycle"])
                print(f"  {ex['file']}: {cycle_str}")
                examples_shown += 1


def save_json_report(
    modules: Dict[str, ModuleStats], errors: List[Dict], output_path: Path
):
    """Save detailed JSON report for further analysis."""
    report = {
        "modules": {name: mod.to_dict() for name, mod in modules.items()},
        "errors_sample": errors[:50],
    }
    output_path.write_text(json.dumps(report, indent=2))
    print(f"\nJSON report saved to: {output_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Analyze GOTO patterns in VistA")
    parser.add_argument(
        "--max-files", type=int, help="Limit number of files to process"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show progress")
    parser.add_argument("--json", type=str, help="Save JSON report to file")
    parser.add_argument(
        "--modules-only", action="store_true", help="Only show module table"
    )
    args = parser.parse_args()

    vista_path = Path("VistA-M/Packages")
    if not vista_path.exists():
        print(f"Error: {vista_path} not found")
        sys.exit(1)

    print("Analyzing VistA GOTO patterns using m2py parser...", file=sys.stderr)
    modules, errors = analyze_vista(vista_path, args.max_files, args.verbose)

    if not args.modules_only:
        print_summary(modules, errors)

    print_module_table(modules)
    print_cycle_examples(modules)

    if args.json:
        save_json_report(modules, errors, Path(args.json))
