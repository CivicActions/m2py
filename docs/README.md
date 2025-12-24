# M2PY Documentation

M2PY is a MUMPS-to-Python transpiler that uses [textX](https://textx.github.io/textX/) to parse MUMPS source code and produce an **Abstract Semantic Graph (ASG)** for analysis and code generation.

## Quick Start

```python
from m2py import MUMPSParser

# Parse a MUMPS file
parser = MUMPSParser()
routine = parser.parse_file("routine.m")

# Run all analysis passes
parser.resolve_references(routine)
parser.classify_gotos(routine)
parser.analyze_for_loops(routine)
parser.analyze_variables(routine)

# Inspect the ASG
for label in routine.labels:
    print(f"Label: {label.name}")
    print(f"  Input vars: {label.input_variables}")
    print(f"  Output vars: {label.output_variables}")
```

## Documentation Index

### Architecture & Overview

| Document | Description |
|----------|-------------|
| [architecture.md](architecture.md) | System architecture, data flow, and design decisions |
| [grammar_overview.md](grammar_overview.md) | textX grammar structure and organization |

### ASG Reference

| Document | Description |
|----------|-------------|
| [asg/index.md](asg/index.md) | ASG overview and class hierarchy |
| [asg/structural_elements.md](asg/structural_elements.md) | MRoutine, MLabel, MScope, MCall |
| [asg/statements.md](asg/statements.md) | All statement types (SET, IF, FOR, etc.) |
| [asg/expressions.md](asg/expressions.md) | All expression types (literals, variables, operators, functions) |
| [asg/enums.md](asg/enums.md) | Classification enums with code generation guidance |
| [asg/type_helpers.md](asg/type_helpers.md) | Type narrowing utilities for pyright |

### Analysis Passes

| Document | Description |
|----------|-------------|
| [analysis/index.md](analysis/index.md) | Analysis pipeline overview and execution order |
| [analysis/semantic_analyzer.md](analysis/semantic_analyzer.md) | CST to ASG transformation |
| [analysis/resolver.md](analysis/resolver.md) | Reference resolution pass |
| [analysis/goto_analysis.md](analysis/goto_analysis.md) | GOTO classification |
| [analysis/for_analysis.md](analysis/for_analysis.md) | FOR loop analysis |
| [analysis/variable_analysis.md](analysis/variable_analysis.md) | Variable scope analysis |
| [analysis/pattern_compiler.md](analysis/pattern_compiler.md) | MUMPS pattern to regex |

### MUMPS-to-ASG Examples

| Document | Description |
|----------|-------------|
| [examples/index.md](examples/index.md) | How to inspect ASG output |
| [examples/basic_commands.md](examples/basic_commands.md) | SET, WRITE, READ |
| [examples/control_flow.md](examples/control_flow.md) | IF, ELSE, FOR, GOTO |
| [examples/subroutines.md](examples/subroutines.md) | DO, QUIT, parameter passing |
| [examples/expressions.md](examples/expressions.md) | Variables, operators, functions |
| [examples/indirection.md](examples/indirection.md) | @ operator examples |
| [examples/advanced_patterns.md](examples/advanced_patterns.md) | Complex FOR/GOTO patterns |

### Code Generation Guide

| Document | Description |
|----------|-------------|
| [codegen/index.md](codegen/index.md) | Code generation strategy overview |
| [codegen/for_loops.md](codegen/for_loops.md) | FOR loop translation strategies |
| [codegen/goto_handling.md](codegen/goto_handling.md) | GOTO translation strategies |
| [codegen/variable_scoping.md](codegen/variable_scoping.md) | Variable and function signature generation |
| [codegen/operators.md](codegen/operators.md) | Operator translation |
| [codegen/functions.md](codegen/functions.md) | Intrinsic function translation |
| [codegen/runtime_requirements.md](codegen/runtime_requirements.md) | When runtime support is needed |

### Testing & Validation

| Document | Description |
|----------|-------------|
| [testing.md](testing.md) | How to test and validate parser output |

## Source Code Reference

- **ASG Elements**: [`src/m2py/asg/`](../src/m2py/asg/)
- **Parser**: [`src/m2py/parser/`](../src/m2py/parser/)
- **Analysis**: [`src/m2py/analysis/`](../src/m2py/analysis/)
- **Grammar**: [`src/m2py/grammar/`](../src/m2py/grammar/)

## Utilities

```bash
# Validate a MUMPS file and inspect ASG output
uv run python utils/validate_asg.py path/to/routine.m

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src/m2py --cov-report=html
```

## MUMPS Reference

The complete MUMPS language specification is available at [https://71.174.62.16/Demo/AnnoStd](https://71.174.62.16/Demo/AnnoStd).

## textX Reference

Full textX library documentation is available at [https://textx.github.io/textX/](https://textx.github.io/textX/).
