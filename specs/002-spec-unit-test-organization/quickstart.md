# Quickstart: MUMPS Spec-Aligned Unit Test Organization

## Goal

Reorganize M2PY unit tests to directly map to MUMPS 1995 specification sections, with three-level testing (parser, asg, codegen) and stub management for tracking coverage.

## Prerequisites

- Python 3.10+
- uv package manager
- Git (branch: `002-spec-unit-test-organization`)

## Setup

```bash
# Ensure you're on the right branch
git checkout 002-spec-unit-test-organization

# Sync dependencies
uv sync
```

## Key Concepts

### Three Test Categories

| Category | What it tests | Example assertion |
|----------|--------------|-------------------|
| `parser` | textX grammar produces correct AST | `assert parsed.command_type == 'SET'` |
| `asg` | Semantic analyzer produces correct ASG | `assert asg_node.resolved_variable is not None` |
| `codegen` | Generated Python matches MUMPS behavior | `assert runtime.get('X') == 'HELLO'` |

### Directory Structure

```
tests/unit/
├── parser/s7_expressions/test_s7_1_5_1_ascii.py  # §7.1.5.1 $ASCII
├── asg/s7_expressions/test_s7_1_5_1_ascii.py     # Same section, ASG level
└── codegen/s7_expressions/test_s7_1_5_1_ascii.py # Same section, codegen level
```

### Stub Pattern

```python
@pytest.mark.stub
@pytest.mark.parser
@pytest.mark.xfail(reason="Not yet implemented: $ASCII parsing")
def test_ascii_basic():
    pytest.fail("Stub - implement test")
```

## Quick Tasks

### Add a New Test

1. Identify MUMPS spec section (e.g., §7.1.5.1 for $ASCII)
2. Choose category (`parser`, `asg`, or `codegen`)
3. Create/edit file: `tests/unit/{category}/s7_expressions/test_s7_1_5_1_ascii.py`
4. Add category marker + test

### Convert Stub to Test

```python
# Before
@pytest.mark.stub
@pytest.mark.parser
@pytest.mark.xfail(reason="Not implemented")
def test_ascii_basic():
    pytest.fail("Stub")

# After (remove stub, xfail, add implementation)
@pytest.mark.parser
def test_ascii_basic(parser):
    result = parser.parse('W $A("A")')
    assert result.commands[0].arguments[0].function == 'ASCII'
```

### Run Tests by Category

```bash
# All parser tests
uv run pytest -m parser

# Only implemented codegen tests
uv run pytest -m "codegen and not stub"

# See pending work
uv run pytest -m stub --collect-only
```

## Implementation Order

1. **Phase 1**: Create directory structure + register markers
2. **Phase 2**: Create stub files for all spec sections
3. **Phase 3**: Migrate existing tests to new structure
4. **Phase 4**: Fill in stubs incrementally

## Reference Files

- [spec.md](spec.md) - Full specification
- [data-model.md](data-model.md) - Entity definitions
- [contracts/test-markers.md](contracts/test-markers.md) - Marker conventions
- [research.md](research.md) - Background research

## CI Considerations

- All stubs use `xfail` → CI stays green
- `pytest -m "not stub"` runs only implemented tests
- Coverage script tracks stub→implemented ratio
