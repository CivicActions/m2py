# m2py - MUMPS to Python Transpiler

m2py is a MUMPS-to-Python transpiler that uses [textX](https://textx.github.io/textX/) to parse MUMPS source code into an Abstract Semantic Graph (ASG), enrich it through multi-pass analysis, and generate executable Python code, with a runtime library to support MUMPS semantics.

## Status

* Over 7,400 unit, integration, and functional tests covering a wide variety of MUMPS constructs and edge cases.
* 99.99% transpilation success rate on the VistA-VEHU-M routine set (39,299 / 39,304 routines). The only remaining failures are MWAPI SSVNs (X11.6 standard).
* Functional test suites (MUGJ, MVTS, and others) validate transpiled output against YottaDB reference output.
* GT.M/YottaDB and Caché/IRIS-specific extensions are supported, including `$ZBOOLEAN`, `$ZCONVERT`/`$ZCVT`, `$ZF`, `$ZV`, `$ZU`, `$REPLACE`, `$NAMESPACE`, and others.
* A CLI (`m2py`) transpiles individual files or entire directory trees to Python, with automatic ruff lint-fixing and formatting.
* Upcoming goals: YottaDB and IRIS database/lock backends, and VistA-VEHU runtime validation tests.

## Installation

```bash
git clone https://github.com/CivicActions/m2py.git
cd m2py
uv sync
```

### Database Backend Dependencies (Optional)

```bash
# For IRIS backend (TCP SDK, works on any platform)
uv add intersystems-irispython --optional backend

# For YottaDB backend (requires running inside YDB container)
bash utils/ydb.sh uv sync  # yottadb package auto-available in container
```

## Quick Start

### Transpile MUMPS to Python (CLI)

The `m2py` command transpiles `.m` files or directories to Python:

```bash
# Transpile a single file (writes HELLO.py alongside HELLO.m)
m2py HELLO.m

# Transpile a directory tree (mirrors structure in output dir)
m2py VistA-VEHU-M/ -o output/

# Verbose progress, skip ruff formatting
m2py src/ -v --no-format
```

Generated Python files are automatically lint-fixed and formatted by ruff. Use `--no-format` to skip this step.

### Transpile Programmatically

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

### Validate Against YottaDB / IRIS

```bash
# Compare m2py output against YottaDB (requires Docker)
uv run python utils/validate.py --code 'TEST W "Hello",! Q'

# Debug mode: show ASG and generated Python
uv run python utils/validate.py --debug --code 'TEST S X=1 W X Q'

# Compare against both YDB and IRIS
uv run python utils/validate.py --iris --code 'TEST W "Hello" Q'

# Compare against IRIS only
uv run python utils/validate.py --no-ydb --iris --code 'TEST W $ZCV("hello","U") Q'
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

### Database Backends

Global variables can be stored in external databases for persistence and cross-process access:

```bash
# Run with YottaDB (inside Docker container)
bash utils/ydb.sh uv run python my_script.py

# Run with IRIS (container auto-started)
bash utils/iris.sh uv run python my_script.py

# Run backend tests against all three backends
uv run pytest tests/runtime/backend/ -n0                       # InMemory
bash utils/ydb.sh uv run pytest tests/runtime/backend/ -n0     # YottaDB
bash utils/iris.sh uv run pytest tests/runtime/backend/ -n0    # IRIS
```

Set `M2PY_GLOBAL_BACKEND` to `inmemory` (default), `sqlite`, `yottadb`, or `iris`. See [docs/runtime.md](docs/runtime.md) for environment variable details.

See [docs/testing.md](docs/testing.md) for full testing guide.

## Utilities

| Script | Purpose |
|--------|---------|
| `utils/validate.py` | Compare m2py output against YottaDB and/or IRIS (requires Docker) |
| `utils/ydb.sh` | Run commands inside a YottaDB Docker container (auto-builds image) |
| `utils/iris.sh` | Run commands with IRIS Docker container available (auto-starts, exports connection env) |
| `utils/run_mumps_ydb.py` | Run MUMPS through YottaDB via Docker |
| `utils/run_mumps_iris.py` | Run MUMPS through InterSystems IRIS via Docker (persistent container) |
| `utils/scan_vista.py` | Scan VistA-VEHU-M routines and report transpilation metrics with regression detection |
| `utils/validate_asg.py` | Inspect ASG structure for a MUMPS file |
| `utils/rebuild_docs.py` | Regenerate `docs/limitations.md` from source |

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
