# M2PY Copilot Instructions

M2PY is a MUMPS-to-Python transpiler using textX to build an Abstract Semantic Graph (ASG).

## Critical: Use uv Exclusively

**All Python commands MUST use `uv`** for package management, running scripts, and testing:

```bash
uv run pytest                    # Run tests
uv run python <script>           # Run any Python script
uv add <package>                 # Add dependencies
uv sync                          # Sync environment
```

Never use bare `python`, `pip`, or `pytest` commands. Avoid creating /tmp files - either run with `uv run python -c`, or create a permanent helper script in `/utils`.

## Key Reference Materials

- `docs/` - **Project documentation** (architecture, ASG reference, examples, codegen strategies)
- **MUMPS Specification**: https://71.174.62.16/Demo/AnnoStd (local mirror may be available in `mumps-reference/`)
- **textX Documentation**: https://textx.github.io/textX/ (local mirror may be available in `textX-reference/`)
- `tests/functional/mugj/` - MUGJ functional test suite (authoritative validation)
- `.specify/memory/constitution.md` - Project principles and constraints

## Architecture

```
MUMPS Source → textX Parser → ASG (Semantic Graph) → Python Code
```

Core implementation in `src/m2py/`. Feature specs in `specs/<number>-<name>/`.

## Development Workflow

Uses **Speckit** for spec-driven development via `.github/prompts/speckit.*.prompt.md` agents.

## Core Principles

1. **Semantic Correctness First** - Generated Python must match MUMPS behavior exactly
2. **Test-Driven Validation** - MUGJ tests are the source of truth
3. **Multi-Phase Architecture** - Parse → Analyze → Generate (all references resolved before codegen)
4. **Incremental Validation** - Start simple, prove correct, then add complexity
