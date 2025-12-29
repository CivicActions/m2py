#!/usr/bin/env python3
"""Fix all test assertions that compare loop_var to strings.

With the Task 87.3 fix, loop_var is now always an MVariable/MGlobal node,
not a string. This script updates all test assertions to check the node
properties instead.
"""

import re
import sys
from pathlib import Path

# Test files to update
TEST_FILES = [
    "tests/unit/test_parser.py",
    "tests/unit/test_command_parser.py",
    "tests/unit/test_command_analysis.py",
    "tests/unit/test_classifier.py",
    "tests/integration/test_mugj.py",
]


def fix_file(filepath: str) -> tuple[int, list[str]]:
    """Fix loop_var assertions in a test file.

    Returns (number of fixes, list of changed lines).
    """
    path = Path(filepath)
    if not path.exists():
        return 0, [f"File not found: {filepath}"]

    content = path.read_text()
    original = content
    changes = []

    # Pattern 1: stmt.loop_var == "VAR" or similar
    # e.g., assert stmt.loop_var == "I"
    # Replace with: assert stmt.loop_var.name == "I"
    pattern1 = r'(\w+\.loop_var)\s*==\s*"([^"]+)"'

    def replace1(m):
        var = m.group(1)
        name = m.group(2)
        changes.append(f'Changed: {var} == "{name}" → {var}.name == "{name}"')
        return f'{var}.name == "{name}"'

    content = re.sub(pattern1, replace1, content)

    # Add import for MVariable if needed and there were changes
    if changes and "from m2py.asg import" in content and "MVariable" not in content:
        # Find the import line and add MVariable
        content = re.sub(
            r"(from m2py\.asg import .*?)([^a-zA-Z])",
            lambda m: m.group(1) + ", MVariable" + m.group(2)
            if "MVariable" not in m.group(1)
            else m.group(0),
            content,
        )
        changes.append("Added: MVariable to import")

    if content != original:
        path.write_text(content)
        return len(changes), changes

    return 0, []


if __name__ == "__main__":
    total_changes = 0
    for test_file in TEST_FILES:
        num_fixes, change_list = fix_file(test_file)
        if num_fixes > 0:
            print(f"\n{test_file}:")
            print(f"  {num_fixes} changes made:")
            for change in change_list:
                print(f"    - {change}")
            total_changes += num_fixes
        else:
            print(f"\n{test_file}: No changes needed")

    print(f"\n{'=' * 60}")
    print(f"Total changes: {total_changes}")
    sys.exit(0 if total_changes >= 0 else 1)
