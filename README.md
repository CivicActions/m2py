# M2PY - MUMPS to Python Transpiler

M2PY is a MUMPS-to-Python transpiler that uses [textX](https://textx.github.io/textX/) to parse MUMPS source code into an Abstract Semantic Graph (ASG), enrich it through multi-pass analysis, and generate executable Python code.

## Installation

```bash
git clone https://github.com/CivicActions/m2py.git
cd m2py
uv sync
```

## Quick Start

### Transpile MUMPS to Python

```python
from m2py.codegen import generate_python

python_code = generate_python('TEST S X=1 W X Q', routine_name="TEST")
print(python_code)
```

### Parse and Inspect the ASG

```python
from m2py.parser import MUMPSParser

parser = MUMPSParser()
routine = parser.parse("TEST S X=1 W X Q")

# Run analysis passes
parser.resolve_references(routine)
parser.classify_gotos(routine)
parser.analyze_for_loops(routine)

# Inspect the ASG
for label in routine.labels:
    print(f"Label: {label.name}, statements: {len(label.body.statements)}")
```

### Validate Against YottaDB

```bash
uv run python utils/validate.py --code 'TEST W "Hello",! Q'
uv run python utils/validate.py --debug --code 'TEST S X=1 W X Q'
```

## Architecture

```
MUMPS Source → textX Grammar → Parser → ASG → Analysis → Codegen → Python
                                                            ↓
                                                     Runtime + Core
```

See [docs/architecture.md](docs/architecture.md) for details.

## Development

```bash
uv run pytest                    # Run tests (parallel, skip slow)
uv run pytest -n0                # Run sequentially (for debugging)
uv run pytest -m slow            # Run only slow tests
uv run pytest --backend sqlite   # Use SQLite global storage
```

See [docs/testing.md](docs/testing.md) for full testing guide.

## Documentation

Full documentation in [`docs/`](docs/README.md):

| Topic | Document |
|-------|----------|
| Architecture | [docs/architecture.md](docs/architecture.md) |
| ASG Reference | [docs/asg-reference.md](docs/asg-reference.md) |
| Code Generation | [docs/codegen.md](docs/codegen.md) |
| Runtime Library | [docs/runtime.md](docs/runtime.md) |
| Testing | [docs/testing.md](docs/testing.md) |
| Limitations | [docs/limitations.md](docs/limitations.md) |

## License

See LICENSE.md file for details.
