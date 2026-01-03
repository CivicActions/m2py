#!/usr/bin/env python3
"""
Extract and verify stub test structure from the codebase.

This utility scans all stub test files and extracts the test classes and
test functions, creating a manifest that can be used to verify the structure
is maintained over time.
"""

import ast
import json
from pathlib import Path
from typing import NamedTuple


class TestItem(NamedTuple):
    """A test class or function."""

    name: str
    item_type: str  # "class" or "function"
    markers: list[str]  # pytest markers like "stub", "skip", "xfail"


class TestFileManifest(NamedTuple):
    """Manifest of test items in a file."""

    file_path: str
    classes: list[str]
    functions: dict[str, list[str]]  # class_name -> list of test function names


def get_project_root() -> Path:
    """Get the project root directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            return current
        current = current.parent
    raise RuntimeError("Could not find project root (no pyproject.toml found)")


def extract_pytest_markers(decorator_list: list[ast.expr]) -> list[str]:
    """Extract pytest marker names from decorator list."""
    markers = []
    for dec in decorator_list:
        if isinstance(dec, ast.Attribute):
            # @pytest.mark.stub
            if isinstance(dec.value, ast.Attribute):
                if (
                    isinstance(dec.value.value, ast.Name)
                    and dec.value.value.id == "pytest"
                    and dec.value.attr == "mark"
                ):
                    markers.append(dec.attr)
        elif isinstance(dec, ast.Call):
            # @pytest.mark.skip(reason="...")
            if isinstance(dec.func, ast.Attribute):
                if isinstance(dec.func.value, ast.Attribute):
                    if (
                        isinstance(dec.func.value.value, ast.Name)
                        and dec.func.value.value.id == "pytest"
                        and dec.func.value.attr == "mark"
                    ):
                        markers.append(dec.func.attr)
    return markers


def extract_test_structure(file_path: Path) -> TestFileManifest | None:
    """Extract test classes and functions from a test file."""
    try:
        source = file_path.read_text()
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return None

    classes = []
    functions: dict[str, list[str]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name.startswith("Test"):
                classes.append(node.name)
                functions[node.name] = []
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        if item.name.startswith("test_"):
                            functions[node.name].append(item.name)

    # Also check for module-level test functions
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            if "__module__" not in functions:
                functions["__module__"] = []
            functions["__module__"].append(node.name)

    return TestFileManifest(
        file_path=str(file_path), classes=classes, functions=functions
    )


def scan_stub_test_files(project_root: Path) -> dict[str, TestFileManifest]:
    """Scan all stub test files and extract their structure."""
    import sys

    sys.path.insert(0, str(project_root))
    from utils.extract_stub_test_paths import REQUIRED_STUB_TEST_FILES

    manifests = {}
    for rel_path in REQUIRED_STUB_TEST_FILES:
        # Skip non-test files
        if not rel_path.endswith(".py"):
            continue
        if "conftest.py" in rel_path or "STUB_TEMPLATE" in rel_path:
            continue

        full_path = project_root / rel_path
        if full_path.exists():
            manifest = extract_test_structure(full_path)
            if manifest:
                manifests[rel_path] = manifest

    return manifests


def generate_manifest_snapshot(project_root: Path | None = None) -> dict:
    """Generate a JSON-serializable snapshot of all test structures."""
    if project_root is None:
        project_root = get_project_root()

    manifests = scan_stub_test_files(project_root)

    snapshot = {}
    for rel_path, manifest in manifests.items():
        snapshot[rel_path] = {
            "classes": manifest.classes,
            "functions": manifest.functions,
        }

    return snapshot


def save_manifest_snapshot(output_path: Path | None = None):
    """Save the current manifest snapshot to a JSON file."""
    project_root = get_project_root()
    if output_path is None:
        output_path = project_root / "tests" / "unit" / "meta" / "stub_manifest.json"

    snapshot = generate_manifest_snapshot(project_root)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True)

    return output_path


def load_manifest_snapshot(manifest_path: Path | None = None) -> dict:
    """Load a previously saved manifest snapshot."""
    if manifest_path is None:
        project_root = get_project_root()
        manifest_path = project_root / "tests" / "unit" / "meta" / "stub_manifest.json"

    with open(manifest_path) as f:
        return json.load(f)


def compare_manifests(
    expected: dict, actual: dict
) -> tuple[list[str], list[str], list[str]]:
    """
    Compare expected manifest with actual.

    Returns:
        Tuple of (missing_files, missing_classes, missing_functions)
    """
    missing_files = []
    missing_classes = []
    missing_functions = []

    for file_path, expected_struct in expected.items():
        if file_path not in actual:
            missing_files.append(file_path)
            continue

        actual_struct = actual[file_path]

        # Check classes
        for class_name in expected_struct["classes"]:
            if class_name not in actual_struct["classes"]:
                missing_classes.append(f"{file_path}::{class_name}")

        # Check functions
        for class_name, funcs in expected_struct["functions"].items():
            actual_funcs = actual_struct["functions"].get(class_name, [])
            for func_name in funcs:
                if func_name not in actual_funcs:
                    missing_functions.append(f"{file_path}::{class_name}::{func_name}")

    return missing_files, missing_classes, missing_functions


def verify_against_manifest(manifest_path: Path | None = None) -> tuple[bool, str]:
    """
    Verify current test structure against saved manifest.

    Returns:
        Tuple of (success, message)
    """
    project_root = get_project_root()

    expected = load_manifest_snapshot(manifest_path)
    actual = generate_manifest_snapshot(project_root)

    missing_files, missing_classes, missing_functions = compare_manifests(
        expected, actual
    )

    if not missing_files and not missing_classes and not missing_functions:
        total_classes = sum(len(s["classes"]) for s in expected.values())
        total_functions = sum(
            sum(len(funcs) for funcs in s["functions"].values())
            for s in expected.values()
        )
        return (
            True,
            f"✅ All {len(expected)} files, {total_classes} classes, {total_functions} functions present",
        )

    messages = ["❌ Missing test structure:"]
    if missing_files:
        messages.append(f"\nMissing files ({len(missing_files)}):")
        messages.extend(f"  - {f}" for f in sorted(missing_files)[:10])
        if len(missing_files) > 10:
            messages.append(f"  ... and {len(missing_files) - 10} more")

    if missing_classes:
        messages.append(f"\nMissing classes ({len(missing_classes)}):")
        messages.extend(f"  - {c}" for c in sorted(missing_classes)[:10])
        if len(missing_classes) > 10:
            messages.append(f"  ... and {len(missing_classes) - 10} more")

    if missing_functions:
        messages.append(f"\nMissing functions ({len(missing_functions)}):")
        messages.extend(f"  - {f}" for f in sorted(missing_functions)[:10])
        if len(missing_functions) > 10:
            messages.append(f"  ... and {len(missing_functions) - 10} more")

    return False, "\n".join(messages)


def print_summary(project_root: Path | None = None):
    """Print a summary of all test structures."""
    if project_root is None:
        project_root = get_project_root()

    manifests = scan_stub_test_files(project_root)

    total_files = len(manifests)
    total_classes = sum(len(m.classes) for m in manifests.values())
    total_functions = sum(
        sum(len(funcs) for funcs in m.functions.values()) for m in manifests.values()
    )

    print(f"Total stub test files: {total_files}")
    print(f"Total test classes: {total_classes}")
    print(f"Total test functions: {total_functions}")

    # Group by category
    categories = {}
    for rel_path, manifest in manifests.items():
        parts = rel_path.split("/")
        if len(parts) >= 4:
            category = f"{parts[2]}/{parts[3]}"  # e.g., "parser/s8_commands"
        else:
            category = "other"

        if category not in categories:
            categories[category] = {"files": 0, "classes": 0, "functions": 0}

        categories[category]["files"] += 1
        categories[category]["classes"] += len(manifest.classes)
        categories[category]["functions"] += sum(
            len(funcs) for funcs in manifest.functions.values()
        )

    print("\nBy category:")
    for cat in sorted(categories.keys()):
        stats = categories[cat]
        print(
            f"  {cat}: {stats['files']} files, {stats['classes']} classes, {stats['functions']} functions"
        )


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "save":
            output_path = save_manifest_snapshot()
            print(f"Saved manifest to {output_path}")
            return 0
        elif command == "verify":
            success, message = verify_against_manifest()
            print(message)
            return 0 if success else 1
        elif command == "summary":
            print_summary()
            return 0

    # Default: print summary
    print_summary()
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
