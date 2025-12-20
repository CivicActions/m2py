#!/usr/bin/env python3
"""Verify actual I/O command usage (not in strings/comments)."""

import sys
from pathlib import Path
import re


def find_real_io_commands(filepath: Path) -> list[dict]:
    """Find actual I/O commands (not in strings or comments)."""
    issues = []
    source_lines = filepath.read_text().split('\n')
    
    for line_num, line in enumerate(source_lines, 1):
        stripped = line.strip()
        
        # Skip blank lines and comments
        if not stripped or stripped.startswith(';'):
            continue
        
        # Remove any inline comment
        code_part = re.split(r'\s;', line)[0]
        
        # Check for I/O commands at start or after whitespace
        # Must be followed by space (command argument) or colon (postcondition)
        for cmd in ['OPEN', 'CLOSE', 'USE', 'JOB']:
            pattern = rf'\b{cmd}[\s:]'
            if re.search(pattern, code_part, re.IGNORECASE):
                # Additional check: not in a string literal
                # Quick heuristic: if command comes after an odd number of quotes, it's in a string
                before_cmd = code_part[:code_part.upper().find(cmd)]
                quote_count = before_cmd.count('"')
                
                if quote_count % 2 == 0:  # Even quotes = not in string
                    issues.append({
                        'line': line_num,
                        'command': cmd,
                        'text': code_part.strip()
                    })
    
    return issues


def main():
    """Check all files with I/O commands."""
    mugj_dir = Path("tests/functional/mugj/inref")
    
    # All files that might have I/O
    check_files = [
        'V1MJA.m', 'V1MJA2.m', 'V1MJB.m',  # Multi-job
        'VV2NO.m', 'VV2VNIA.m',  # Version 2
        # Previously known:
        'V1HANG.m', 'V1IO.m', 'V1IO1.m', 'V1IO2.m', 'V1BOB8.m', 'V1BOB10.m'
    ]
    
    print("=" * 80)
    print("REAL I/O COMMAND VERIFICATION")
    print("=" * 80)
    print()
    
    total_files = 0
    total_commands = 0
    
    for filename in sorted(check_files):
        filepath = mugj_dir / filename
        if not filepath.exists():
            print(f"⚠️  {filename}: NOT FOUND")
            continue
        
        io_cmds = find_real_io_commands(filepath)
        if io_cmds:
            total_files += 1
            total_commands += len(io_cmds)
            print(f"{filename}:")
            for cmd in io_cmds:
                print(f"  Line {cmd['line']:3}: {cmd['command']:5} - {cmd['text']}")
            print()
        else:
            print(f"✓ {filename}: No I/O commands (false positive)")
    
    print("=" * 80)
    print(f"Total files with real I/O commands: {total_files}")
    print(f"Total I/O commands found: {total_commands}")
    print("=" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
