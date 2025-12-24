# M2PY - MUMPS to Python Transpiler

M2PY is a MUMPS-to-Python transpiler that uses textX to parse MUMPS source code and produce an Abstract Semantic Graph (ASG) for analysis and code generation.

## Installation

```bash
git clone https://github.com/yourorg/m2py.git
cd m2py
uv sync
```

## Quick Start

```python
from m2py.parser import MUMPSParser

parser = MUMPSParser()
routine = parser.parse_file("routine.m")

# Run analysis passes
parser.resolve_references(routine)
parser.classify_gotos(routine)
parser.analyze_for_loops(routine)

# Inspect the ASG
for label in routine.labels:
    print(f"Label: {label.name}, statements: {len(label.body.statements)}")
```

For more examples, see [docs/examples/](docs/examples/index.md).

## Architecture

```
MUMPS Source → textX Parser → CST → Semantic Analyzer → ASG → Python Code
```

See [docs/architecture.md](docs/architecture.md) for details.

## Development

```bash
uv run pytest                    # Run all tests
uv run pytest --cov=m2py         # Run with coverage
uv run python utils/validate_asg.py <file.m>  # Validate parser output
```

See [docs/testing.md](docs/testing.md) for testing details.

## Documentation

Full documentation in [`docs/`](docs/README.md):

| Topic | Document |
|-------|----------|
| Architecture | [docs/architecture.md](docs/architecture.md) |
| ASG Reference | [docs/asg/index.md](docs/asg/index.md) |
| Analysis Passes | [docs/analysis/index.md](docs/analysis/index.md) |
| Examples | [docs/examples/index.md](docs/examples/index.md) |
| Code Generation | [docs/codegen/index.md](docs/codegen/index.md) |
| Testing | [docs/testing.md](docs/testing.md) |

## License

See LICENSE.md file for details.
