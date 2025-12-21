#!/usr/bin/env python
"""Test parsing of nested FOR loops."""

from m2py.analysis.command_parser import _get_line_metamodel
line_meta = _get_line_metamodel()

# Simple nested FOR
test_line = 'F I=1:1:3 F J=1:1:3 S V=V_1'
print(f'Parsing: {test_line}')
try:
    result = line_meta.model_from_str(test_line)
    print(f'Result type: {type(result).__name__}')
    if hasattr(result, 'commands'):
        for i, cmd in enumerate(result.commands):
            print(f'  [{i}] {type(cmd).__name__} cmd={type(cmd.cmd).__name__}')
            if type(cmd.cmd).__name__ == 'ForCommand':
                c = cmd.cmd
                print(f'       loop_var: {c.loop_var}, forparams: {c.forparams}')
                print(f'       body type: {type(c.body).__name__ if c.body else "None"}')
                if c.body:
                    print(f'       body: {c.body}')
except Exception as e:
    import traceback
    traceback.print_exc()
