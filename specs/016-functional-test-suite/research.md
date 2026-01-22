# Research: Functional Test Suite

**Feature**: 016-functional-test-suite  
**Date**: 2026-01-21

## Research Questions Resolved

### Q1: How does m2py execute MUMPS code?

**Decision**: Use existing `generate_python()` → `MUMPSRuntime.execute()` pattern

**Rationale**: The `utils/validate.py` utility demonstrates the working pattern:

```python
from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime

# 1. Transpile MUMPS to Python
python_code = generate_python(mumps_source)

# 2. Execute via runtime (captures output)
runtime = MUMPSRuntime()
result = runtime.execute(python_code, capture_output=True)

# 3. Get output
output = result.output
```

**Alternatives Considered**:
- Direct exec() of generated code: Rejected - loses output capture and runtime context
- Subprocess execution: Rejected - unnecessary overhead, runtime handles execution

### Q2: What outref normalization is required?

**Decision**: Strip YDB infrastructure markers before comparison

**Rationale**: Analysis of outref files shows these YDB-specific patterns:

| Pattern | Description | Action |
|---------|-------------|--------|
| `##TEST_PATH##` | YDB installation path placeholder | Strip line |
| `##SOURCE_PATH##` | Source directory placeholder | Strip line |
| `##REMOTE_TEST_PATH##` | Remote test path | Strip line |
| `##REMOTE_SOURCE_PATH##` | Remote source path | Strip line |
| `##IN_TEST_PATH##` | Test path reference | Strip line |
| `##SUSPEND_OUTPUT...` | Begin conditional block | Strip directive + content |
| `##ALLOW_OUTPUT...` | End conditional block | Strip directive |
| `##TEST_AWK##` | AWK pattern match | Strip line |
| `YDB>` preamble | Database setup before first prompt | Strip all content before first YDB> |

**Alternatives Considered**:
- Include YDB markers in comparison: Rejected - these are infrastructure, not test output
- Use regex replacement: Selected - simpler than line-by-line parsing

### Q3: How are test suites organized in YDBTest?

**Decision**: Preserve YDBTest directory structure with inref/outref/u_inref

**Rationale**: Existing structure in `tests/functional/`:

```
tests/functional/<suite>/
├── inref/      # MUMPS source files (.m)
├── outref/     # Reference output (.txt or <suite>.txt)
└── u_inref/    # Test driver scripts (.csh)
```

The test driver scripts (u_inref/*.csh) define execution order:
```csh
# From mugj.csh
W !!,"V1WR" D ^V1WR
W !!,"V1IF" D ^V1IF
...
```

**Alternatives Considered**:
- Flatten structure: Rejected - breaks YDB compatibility, harder to update
- Generate drivers programmatically: Rejected - lose authoritative execution order

### Q4: How to integrate limitation IDs for xfail?

**Decision**: Reference `src/m2py/limitations.py` directly for xfail markers

**Rationale**: `limitations.py` is the canonical source of limitation data:

```python
# Example usage in tests
import pytest
from m2py.limitations import LIMITATIONS

@pytest.mark.xfail(
    reason=f"LIM-003: {LIMITATIONS['LIM-003'].short_description}",
    strict=False  # Allow unexpected passes
)
def test_mwapi_ssvn():
    ...
```

Key limitation IDs for test suite:
- **LIM-003**: MWAPI SSVNs (^$EVENT, ^$WINDOW, ^$DISPLAY)
- **LIM-005**: VIEW command implementation-specific keywords
- **LIM-012**: Unknown Z-extensions from other MUMPS implementations
- **LIM-015**: Zero-VistA-usage YDB Z-commands

**Alternatives Considered**:
- Hard-code xfail reasons: Rejected - duplication, drift from canonical source
- Skip instead of xfail: Rejected - loses visibility into limitation coverage

### Q5: What existing test infrastructure can be reused?

**Decision**: Reuse `tests/conftest.py` TEST_SUITES dict and add functional fixtures

**Rationale**: `conftest.py` already defines:

```python
TEST_SUITES = {
    "mugj": FUNCTIONAL_BASE / "mugj" / "inref",
    "mvts": FUNCTIONAL_BASE / "mvts" / "inref",
    "basic": FUNCTIONAL_BASE / "basic" / "inref",
    ...
}
```

New fixtures needed:
- `outref_content(suite, test_name)` - Load and normalize outref
- `run_routine(source)` - Execute via m2py runtime
- `compare_output(actual, expected)` - Byte-for-byte comparison with diff

**Alternatives Considered**:
- New conftest.py in tests/functional/: Selected - scope fixtures to functional tests
- Extend root conftest.py: Rejected - keeps functional test concerns isolated

### Q6: How to handle multi-routine test sequences?

**Decision**: Parse driver scripts to determine execution order

**Rationale**: Drivers like `mugj.csh` call multiple routines in sequence:
```csh
W !!,"V1WR" D ^V1WR
W !!,"V1CMT" D ^V1CMT
```

Each routine call outputs its name (e.g., "V1WR") then executes the routine.
The driver defines the concatenated output that matches outref.

Implementation approach:
1. Parse driver script to extract routine sequence
2. Execute each routine via m2py, concatenating output
3. Compare concatenated output against outref

**Alternatives Considered**:
- Run routines independently: Rejected - loses output ordering, breaks comparison
- Transpile driver scripts: Rejected - too complex, unnecessary

### Q7: What tests should be removed from tests/integration/?

**Decision**: Remove parsing-focused tests, keep useful integration tests

**Rationale**: Files to remove:
- `test_ydb_suites.py` - Tests parsing only, not transpilation
- `test_mugj.py` - Tests ASG structure, not runtime behavior

Files to evaluate:
- `test_external_calls.py` - May have useful patterns
- `test_indirection_edge_cases.py` - May test runtime behavior

**Alternatives Considered**:
- Keep all: Rejected - obsolete tests cause confusion
- Remove entire directory: Rejected - some tests may have value

## Technology Decisions

### Test Runner Pattern

```python
def run_mumps_test(mumps_source: str) -> str:
    """Execute MUMPS via m2py and return output."""
    python_code = generate_python(mumps_source)
    runtime = MUMPSRuntime()
    result = runtime.execute(python_code, capture_output=True)
    return result.output
```

### Outref Normalization

```python
def normalize_outref(content: str) -> str:
    """Strip YDB infrastructure from outref content."""
    lines = []
    in_suspended = False
    found_first_prompt = False
    
    for line in content.splitlines():
        # Skip preamble before first YDB>
        if not found_first_prompt:
            if "YDB>" in line:
                found_first_prompt = True
            continue
            
        # Handle suspend/allow blocks
        if "##SUSPEND_OUTPUT" in line:
            in_suspended = True
            continue
        if "##ALLOW_OUTPUT" in line:
            in_suspended = False
            continue
        if in_suspended:
            continue
            
        # Skip path placeholder lines
        if any(marker in line for marker in [
            "##TEST_PATH##", "##SOURCE_PATH##",
            "##REMOTE_TEST_PATH##", "##REMOTE_SOURCE_PATH##",
            "##IN_TEST_PATH##", "##TEST_AWK##"
        ]):
            continue
            
        lines.append(line)
    
    return "\n".join(lines)
```

### Pytest Parametrization

```python
@pytest.mark.parametrize("routine", get_mugj_routines())
def test_mugj_routine(routine, run_routine, expected_output):
    """Test each mugj routine against expected output."""
    actual = run_routine(routine)
    assert actual == expected_output[routine]
```

## Dependencies Verified

| Dependency | Status | Notes |
|------------|--------|-------|
| `m2py.codegen.generate_python()` | ✅ Exists | Public API, well-documented |
| `m2py.runtime.MUMPSRuntime` | ✅ Exists | execute() method returns ExecutionResult |
| `m2py.limitations.LIMITATIONS` | ✅ Exists | Dict mapping IDs to Limitation namedtuples |
| `tests/conftest.py:TEST_SUITES` | ✅ Exists | Path mappings for all 11 suites |
| pytest fixtures | ✅ Available | Standard pytest fixture system |

## Open Questions

None - all research questions resolved.
