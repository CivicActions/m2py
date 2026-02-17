# M2PY Documentation

M2PY is a MUMPS-to-Python transpiler that uses [textX](https://textx.github.io/textX/) to parse MUMPS source code into an Abstract Semantic Graph (ASG), enrich it through multi-pass analysis, and generate executable Python code.

## Quick Start

```python
from m2py.parser import MUMPSParser
from m2py.codegen import generate_python

# Parse and inspect
parser = MUMPSParser()
routine = parser.parse_file("MYROUTINE.m")
for label in routine.labels:
    print(f"{label.name}: {len(label.body.statements)} statements")

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

## Guiding Principles

The project constitution at [`.specify/memory/constitution.md`](../.specify/memory/constitution.md) defines eight core principles:

1. **Semantic Correctness First** — generated Python must match MUMPS behavior exactly
2. **YDB as Reference Implementation** — YottaDB output is the source of truth
3. **Strict Layer Separation** — parse, analyze, generate are distinct phases with clear boundaries
4. **Explicit Over Implicit** — MUMPS implicit behaviors made explicit via helpers (coercion, truth evaluation)
5. **Foundational Correctness** — hard structural problems solved early (GOTO, scoping, control flow)
6. **Cross-Cutting Semantics** — value model, `$TEST`, arrays, scoping correct from day one
7. **Minimize Runtime Surface** — prefer inline Python; runtime only for truly dynamic cases
8. **Research Before Implementation** — structured research before each phase

## Reference Materials

- **MUMPS Specification**: https://71.174.62.16/Demo/AnnoStd (local mirror in `mumps-reference/`)
- **textX Documentation**: https://textx.github.io/textX/ (local mirror in `textX-reference/`)
- **YDB Test Suite**: `YDBTest/` — YottaDB functional test corpus
- **Spec History**: `specs/` — numbered feature specifications documenting design evolution

## Utilities

| Script | Purpose |
|--------|---------|
| `utils/validate.py` | Compare m2py output against YottaDB (requires Docker) |
| `utils/ydb.py` | Run MUMPS through YottaDB via Docker |
| `utils/validate_asg.py` | Inspect ASG structure for a MUMPS file |
| `utils/rebuild_docs.py` | Regenerate `docs/limitations.md` from source |
