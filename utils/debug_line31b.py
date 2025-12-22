#!/usr/bin/env python3
"""Debug VV2CS.m line 31 parsing."""
from m2py.analysis.command_parser import _get_line_metamodel, parse_commands_from_line
from textx.exceptions import TextXSyntaxError

mm = _get_line_metamodel()

# Full VV2CS lines from II-5
lines_to_test = [
    "F I=6:1:8         Q:I=10       D:1 A:I>0      ;",  # Line 31
    "F I=9:1:15        QUIT:I=11       DO A       ;",   # Line 32
    "F I=6:1:8 Q:I=10 D:1 A:I>0 ;",  # Simplified line 31
    "F I=6:1:8 Q:I=10 D:1 A:I>0",    # Without comment
]

for line in lines_to_test:
    print("Line:", repr(line[:50] + "..." if len(line) > 50 else line))
    
    try:
        model = mm.model_from_str(line)
        if model:
            cmds = model.commands if hasattr(model, 'commands') else []
            print(f"  OK: {len(cmds)} commands")
            for i, lc in enumerate(cmds):
                cmd = lc.cmd if hasattr(lc, 'cmd') else None
                if cmd:
                    cname = cmd.__class__.__name__
                    print(f"    [{i}] {cname}")
                    if hasattr(cmd, "postcond") and cmd.postcond:
                        print(f"         postcond: YES")
        else:
            print("  FAIL: None returned")
    except TextXSyntaxError as e:
        print(f"  ERROR: {e}")
    print()
