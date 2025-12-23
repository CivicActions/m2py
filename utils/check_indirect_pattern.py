#!/usr/bin/env python
"""Test script for indirect pattern match parsing."""
from m2py.analysis.command_parser import parse_commands_from_line

# Line 7 from VV2PAT2.m - indirect pattern match
line1 = 'S VCOMP="ABC123#$!"?@(".4AN2.N1.99999999PN")_("12.34"?2.N.P.2N)'
print(f'Line 155 test:')
print(f'  {line1[:60]}...')
cmds = parse_commands_from_line(line1)
print(f'  Result: {len(cmds)} commands')
for c in cmds:
    print(f'    {type(c).__name__}')

# Try just the first part  
line1a = 'S VCOMP="ABC123#$!"?@(".4AN2.N1.99999999PN")'
print(f'\nFirst part only:')
print(f'  {line1a}')
cmds = parse_commands_from_line(line1a)
print(f'  Result: {len(cmds)} commands')

# Try simpler version
line1b = 'S X="ABC"?@(".4AN")'
print(f'\nSimpler version:')
print(f'  {line1b}')
cmds = parse_commands_from_line(line1b)
print(f'  Result: {len(cmds)} commands')

# Simple indirect pattern test
line2 = 'S X=Y?@Z'
print(f'\nSimple indirect pattern:')
print(f'  {line2}')
cmds = parse_commands_from_line(line2)
print(f'  Result: {len(cmds)} commands')
for c in cmds:
    print(f'    {type(c).__name__}')

# Even simpler
line3 = 'S X=1?@A'
print(f'\nEven simpler indirect:')
print(f'  {line3}')
cmds = parse_commands_from_line(line3)
print(f'  Result: {len(cmds)} commands')
