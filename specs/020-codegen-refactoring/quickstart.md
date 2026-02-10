# Quickstart: Codegen Refactoring (Phase 2)

**Branch**: `020-codegen-refactoring`

## Prerequisites

1. Phase 1 (`019-foundation-cleanup`) is merged to main ✅
2. Python 3.10+, `uv` package manager
3. All 5,883 tests passing: `uv run pytest`

## Setup

```bash
git checkout 020-codegen-refactoring
uv sync
uv run pytest  # Verify baseline: 5883/5885 collected, 0 failures
```

## Development Workflow

Each refactoring item follows this cycle:

1. **Baseline**: Run `uv run pytest` — all pass
2. **Extract/Modify**: Make the change
3. **Test**: Run `uv run pytest` — all still pass
4. **New tests**: Add unit tests for extracted helpers
5. **Commit**: One commit per item (e.g., `refactor(codegen): extract gen_subscripts_tuple (S-02)`)

## Track A — Sequential Items (statements.py)

Items must be done in exact order. Each modifies `codegen/statements.py`:

```
S-02 → S-05 → S-04 → S-14 → C-09 → S-01 → S-13 → S-19 → C-07
```

## Track B — Parallel (indirection.py)

Can run alongside Track A:

```
S-03: Extract shared indirection template
```

## Track C — Parallel (runtime + ASG)

Can run alongside Track A:

```
S-12 → S-16: offset_wrapper then ASG cleanup
```

## Key Commands

```bash
# Run full test suite
uv run pytest

# Run codegen tests only
uv run pytest tests/unit/codegen/ -x

# Run with coverage
uv run pytest --cov=m2py.codegen --cov-report=html

# Validate against YDB
uv run python utils/validate.py --code 'TEST S A(1)=1,A(2)=2 ZWR A(1:2) Q'

# Check line counts (targets: statements.py ≤5759, indirection.py ≤1255)
wc -l src/m2py/codegen/statements.py src/m2py/codegen/indirection.py
```

## Verification Checklist

After each item:
- [ ] `uv run pytest` — 0 failures
- [ ] No new `xfail` or `skip` markers
- [ ] New unit tests for extracted helper
- [ ] Grep confirms no remaining inline copies of extracted pattern
