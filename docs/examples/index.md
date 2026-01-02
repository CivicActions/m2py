# MUMPS-to-ASG Examples

This section provides concrete examples mapping MUMPS syntax to ASG structures.

## How to Generate ASG Output

### Using validate_asg.py

```bash
uv run python utils/validate_asg.py tests/functional/mugj/inref/V1SET.m
```

This displays:
1. Original MUMPS source
2. Formatted ASG structure
3. Validation checklist

### Using Python REPL

```python
from m2py import MUMPSParser

parser = MUMPSParser()
routine = parser.parse_file("tests/functional/mugj/inref/V1SET.m")

# Inspect labels
for label in routine.labels:
    print(f"Label: {label.name}")
    for stmt in label.body.statements:
        print(f"  {type(stmt).__name__}")
```

### Dumping JSON

```python
from m2py.parser import dump_asg_json

json_str = dump_asg_json(routine)
print(json_str)
```

## Test File Locations

The MUGJ validation suite provides comprehensive test cases:

| Path | Description |
|------|-------------|
| `tests/functional/mugj/inref/V1SET.m` | SET command variations |
| `tests/functional/mugj/inref/V1WR.m` | WRITE command |
| `tests/functional/mugj/inref/V1FORA*.m` | FOR loop patterns |
| `tests/functional/mugj/inref/V1DO*.m` | DO/QUIT subroutines |
| `tests/functional/mugj/inref/V1IE*.m` | IF/ELSE patterns |
| `tests/functional/mugj/inref/V1GO*.m` | GOTO patterns |
| `tests/functional/mugj/inref/V1PAT*.m` | Pattern matching |
| `tests/functional/mugj/inref/V1IDNM*.m` | Indirection |

## Examples by Topic

- [Basic Commands](basic_commands.md) - SET, WRITE, READ
- [Control Flow](control_flow.md) - IF, ELSE, FOR, GOTO
- [Subroutines](subroutines.md) - DO, QUIT, parameter passing
- [Expressions](expressions.md) - Variables, operators, functions
- [Indirection](indirection.md) - @ operator patterns
- [Advanced Patterns](advanced_patterns.md) - Complex FOR/GOTO

## Reading Examples

Each example shows:

1. **MUMPS Source** - The original syntax
2. **ASG Structure** - Resulting node hierarchy
3. **Key Fields** - Important properties for code generation
4. **Python Equivalent** - Target translation

## Verifying Examples

Always verify examples against the actual parser:

```python
from m2py import MUMPSParser
from m2py.asg.statements import MSetStatement

parser = MUMPSParser()
routine = parser.parse_string("TEST S X=1")

# Check the structure
stmt = routine.labels[0].body.statements[0]
assert isinstance(stmt, MSetStatement)
assert len(stmt.assignments) == 1
assert stmt.assignments[0].target.name == "X"
```
