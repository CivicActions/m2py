# M2PY - MUMPS to Python Transpiler

M2PY is a MUMPS-to-Python transpiler that uses textX to parse MUMPS source code and produce an Abstract Semantic Graph (ASG) for analysis and code generation.

## Installation

```bash
# Clone the repository
git clone https://github.com/yourorg/m2py.git
cd m2py

# Install with uv (recommended)
uv sync
```

## Quick Start

### Parsing MUMPS Source Code

```python
from m2py.parser import MUMPSParser

# Create a parser instance
parser = MUMPSParser()

# Parse MUMPS source code from a string
source = '''TEST   S X=1,Y=2
       F I=1:1:10 S TOTAL=TOTAL+I
       W "Total: ",TOTAL,!
       Q
'''
routine = parser.parse(source)

# Access the ASG structure
print(f"Routine has {len(routine.labels)} labels")
for label in routine.labels:
    print(f"  Label: {label.name}")
```

### Parsing a MUMPS File

```python
from m2py.parser import MUMPSParser

parser = MUMPSParser()

# Parse a .m file directly
routine = parser.parse_file("path/to/routine.m")

print(f"Routine: {routine.name}")
print(f"Labels: {[label.name for label in routine.labels]}")
```

### Working with the ASG

The parser produces an Abstract Semantic Graph (ASG) with the following key types:

- **MRoutine**: Top-level container for a MUMPS routine
- **MLabel**: Entry point (subroutine) within a routine
- **MScope**: Container for statements (label body, IF body, FOR body)
- **MStatement**: Base class for all MUMPS statements
- **MExpr**: Base class for all MUMPS expressions

```python
from m2py.parser import MUMPSParser
from m2py.asg.statements import MForStatement, MSetStatement

parser = MUMPSParser()
routine = parser.parse_file("routine.m")

# Walk through all statements
for label in routine.labels:
    for stmt in label.body.walk_statements():
        if isinstance(stmt, MForStatement):
            print(f"FOR loop: {stmt.loop_type}")
        elif isinstance(stmt, MSetStatement):
            print(f"SET: {len(stmt.assignments)} assignments")
```

### Analyzing FOR Loops

```python
from m2py.parser import MUMPSParser

parser = MUMPSParser()
source = '''TEST   F I=1:1:10 W I,!
       F J="A","B","C" W J,!
       Q
'''
routine = parser.parse(source)

# Classify FOR patterns
patterns = parser.classify_patterns(source)
for pattern in patterns:
    print(f"FOR variable: {pattern.variable}, type: {pattern.loop_type}")
```

### Debugging with JSON Dump

```python
from m2py.parser import MUMPSParser, dump_asg_json

parser = MUMPSParser()
routine = parser.parse_file("routine.m")

# Dump ASG to JSON for debugging
json_str = dump_asg_json(routine, indent=2)
print(json_str)
```

## Architecture

M2PY uses a two-layer architecture:

1. **textX Parser**: Parses MUMPS source into a Concrete Syntax Tree (CST)
2. **Semantic Analyzer**: Transforms CST into a clean Abstract Semantic Graph (ASG)

```
MUMPS Source → textX Parser → CST (Custom Classes) → Semantic Analyzer → ASG
```

The ASG is designed for:
- Static analysis (variable usage, control flow)
- Code generation (Python output)
- Debugging and visualization

## Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=m2py

# Run specific test file
uv run pytest tests/unit/test_parser.py -v
```

### Project Structure

```
src/m2py/
├── parser/           # textX-based parser
│   ├── parser.py     # MUMPSParser class
│   └── exceptions.py # Error types
├── grammar/          # textX grammar files
│   ├── mumps.tx      # Main grammar
│   ├── line.tx       # Line content grammar
│   ├── commands.tx   # Command grammar
│   └── expressions.tx # Expression grammar
├── asg/              # Abstract Semantic Graph types
│   ├── elements.py   # Core ASG elements
│   ├── statements.py # Statement types
│   └── expressions.py # Expression types
└── analysis/         # Analysis passes
    ├── semantic_analyzer.py  # CST → ASG transformation
    ├── command_parser.py     # Command parsing utilities
    ├── resolver.py           # Reference resolution
    └── variables.py          # Variable analysis
```

## License

See LICENSE file for details.
