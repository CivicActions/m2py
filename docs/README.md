# m2py Documentation

m2py is a MUMPS-to-Python transpiler that uses [textX](https://textx.github.io/textX/) to parse MUMPS source code into an Abstract Semantic Graph (ASG), enrich it through multi-pass analysis, and generate executable Python code.

## Quick Start

### CLI

```bash
# Transpile a single file
m2py transpile MYROUTINE.m

# Transpile a directory tree to an output directory
m2py transpile VistA-VEHU-M/ -o output/

# Import/export ZWR global data
m2py globals import data.zwr
m2py globals export out.zwr --globals '^DD,^DIC'

# Show available commands
m2py --help
```

### Python API

```python
from m2py.codegen import generate_python

# Transpile to Python
python_code = generate_python(open("MYROUTINE.m").read(), routine_name="MYROUTINE")
```

`generate_python()` handles the full pipeline internally: parse → analyze → select strategy → generate → validate.

## Contents

| Document | Description |
|----------|-------------|
| [architecture.md](architecture.md) | System architecture, pipeline, package responsibilities |
| [asg-reference.md](asg-reference.md) | ASG node hierarchy, enums, analysis fields |
| [codegen.md](codegen.md) | Code generation strategies and output patterns |
| [runtime.md](runtime.md) | Runtime library, MArray, globals, devices |
| [testing.md](testing.md) | Test organization, fixtures, running tests |
| [limitations.md](limitations.md) | Known limitations (auto-generated) |

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
