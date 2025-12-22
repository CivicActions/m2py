#!/usr/bin/env python3
"""Debug VV2CS.m line 31 parsing."""
from m2py.analysis.command_parser import parse_commands_from_line, extract_for_commands, parse_line_content
from textx.exceptions import TextXSyntaxError

# Issue: D:1 causes parse failure after QUIT with postcond
lines_to_test = [
    "Q:I=10 D A",           # OK - no DO postcond
    "Q:I=10 D:1 A",         # FAIL - DO postcond
    "S X=1 D:1 A",          # SET + DO with postcond
    "W X D:1 A",            # WRITE + DO with postcond
    "Q D:1 A",              # QUIT (no postcond) + DO with postcond
]

for line in lines_to_test:
    print("Line:", repr(line))
    
    # Try parse_line_content first
    try:
        model = parse_line_content(line)
        if model:
            cmds = model.commands if hasattr(model, 'commands') else []
            print(f"  OK: {len(cmds)} commands")
        else:
            print("  FAIL: None returned")
    except TextXSyntaxError as e:
        print(f"  ERROR: {e}")
    print()

print("Line:", repr(line))
print()

# Parse all commands
cmds = parse_commands_from_line(line)
print(f"Commands found: {len(cmds)}")
for i, cmd in enumerate(cmds):
    print(f"  [{i}] {cmd.__class__.__name__}")
    if hasattr(cmd, 'postcondition') and cmd.postcondition:
        print(f"       postcondition: {cmd.postcondition}")

print()

# Extract FOR commands specifically  
fors = extract_for_commands(line)
print(f"FOR commands: {len(fors)}")
for i, f in enumerate(fors):
    print(f"  [{i}] var={f.var.name if f.var else None} params={f.params}")
    if hasattr(f, 'body') and f.body:
        print(f"       body commands: {len(f.body)}")
        for j, bcmd in enumerate(f.body):
            print(f"         [{j}] {bcmd.__class__.__name__}")
            if hasattr(bcmd, 'postcondition') and bcmd.postcondition:
                print(f"              postcondition: {bcmd.postcondition}")
            if hasattr(bcmd, 'args') and bcmd.args:
                for k, arg in enumerate(bcmd.args):
                    print(f"              arg[{k}]: {arg}")
                    if hasattr(arg, 'postcondition') and arg.postcondition:
                        print(f"                   arg postcondition: {arg.postcondition}")
