# Implementation Plan: Minimal Control Flow Foundation

**Branch**: `004-minimal-codegen` | **Date**: 2026-01-09 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/004-minimal-codegen/spec.md`

## Summary

Implement the absolute minimum code generation infrastructure to translate MUMPS routines to executable Python code. This establishes foundational patterns (value coercion, name translation, statement generators) that all subsequent specs build upon. The scope is deliberately minimal—just enough syntax to validate control flow patterns.

**Technical Approach**: Use the existing `CodeEmitter` for indent-aware generation. Emit local variables as Python locals (not runtime scope). Provide `m_num()`, `m_truth()`, `m_compare()` pure helpers for MUMPS semantics. Generate Python functions for each label, with $TEST tracking via `_test` module-level variable.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: textX (parser), pytest (testing)  
**Storage**: N/A - in-memory code generation  
**Testing**: pytest with embedded MUMPS strings, YDB for reference output  
**Target Platform**: Any Python 3.10+ environment  
**Project Type**: Single (library package with CLI)  
**Performance Goals**: Not a concern for initial codegen; correctness first  
**Constraints**: Generated code must be valid Python (ast.parse() validation)  
**Scale/Scope**: Single-routine translation only (no external calls)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Semantic Correctness First** | ✅ | All acceptance criteria compare output to YDB reference |
| **II. YDB as Reference Implementation** | ✅ | Test strategy uses YDB for expected output generation |
| **III. Strict Layer Separation** | ✅ | Codegen only translates ASG→Python; parser/analysis unchanged |
| **IV. Explicit Over Implicit** | ✅ | m_num(), m_truth(), m_compare() make coercion explicit |
| **V. Foundational Correctness** | ✅ | Value model is implemented first (FR-007 through FR-009) |
| **VI. Cross-Cutting Semantics** | ✅ | Coercion helpers are shared, $TEST tracking centralized |
| **VII. Minimize Runtime Surface** | ✅ | Local vars → Python locals, runtime only for $TEST |
| **VIII. Research Before Implementation** | ✅ | Research phase completed, ASG structure understood |

**No violations requiring justification.**

## Project Structure

### Documentation (this feature)

```text
specs/004-minimal-codegen/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output (below)
├── checklists/
│   └── requirements.md  # Quality checklist
└── tasks.md             # Phase 2 output (via /speckit.tasks)
```

### Source Code (repository root)

```text
src/m2py/
├── codegen/
│   ├── __init__.py          # Public API: generate_python()
│   ├── emitter.py           # EXISTING: CodeEmitter class
│   ├── helpers.py           # NEW: m_num(), m_truth(), m_compare()
│   ├── names.py             # NEW: NameTranslator class
│   ├── expressions.py       # NEW: generate_expr() dispatcher
│   ├── statements.py        # NEW: generate_statement() dispatcher
│   └── routine.py           # NEW: RoutineGenerator class
└── runtime/
    └── __init__.py          # NEW: MUMPSRuntime class (minimal)

tests/unit/codegen/
├── s7_expressions/
│   └── test_s7_1_1_values.py     # EXISTING: extend with implementation
├── s8_commands/
│   └── test_s8_2_*.py            # EXISTING: extend stubs
└── conftest.py                   # EXISTING: add generate_python fixture impl
```

**Structure Decision**: Single project with existing `src/m2py/` layout. New codegen modules follow established patterns. Tests fill existing stub classes.

## Complexity Tracking

> No violations requiring justification.

---

## Phase 0 Research Findings

### ASG Structure Confirmed

From `validate_asg.py` output and source inspection:

- **MRoutine**: Contains `labels: List[MLabel]`, `name: str`
- **MLabel**: Contains `name: str`, `formal_list: List[str]`, `body: MScope`, analysis fields (`signature`, `variables_read`, etc.)
- **MScope**: Contains `statements: List[MStatement]`
- **MSetStatement**: Contains `assignments: List[MAssignment]` where each has `target: MVariable`, `value: MExpr`
- **MWriteStatement**: Contains `arguments: List[MExpr|MFormatControl]`
- **MIfStatement**: Contains `condition: MExpr`, `conditions: List[MExpr]`, `then_scope: MScope`
- **MElseStatement**: Contains `body: MScope`
- **MForStatement**: Contains `loop_var`, `parameters: List[MForParameter]`, `body: MScope`
- **MDoStatement**: Contains `targets: List[MCall]`
- **MGotoStatement**: Contains `targets: List[MCall]`
- **MQuitStatement**: Contains `return_value: Optional[MExpr]`
- **MLiteral**: Contains `value`, `literal_type: LiteralType` (STRING, INTEGER, DECIMAL)
- **MVariable**: Contains `name: str`, `subscripts: List[MExpr]`
- **MBinaryOp**: Contains `operator: str`, `left: MExpr`, `right: MExpr`

### Analysis Infrastructure Available

From `src/m2py/analysis/variables.py`:

- **ScopeStrategy enum**: `PURE_FUNCTION`, `FUNCTION_WITH_OUTPUTS`, `SUBROUTINE`, `REQUIRES_RUNTIME`
- **FunctionSignature**: Computed per-label with `scope_strategy`, `formal_params`, `input_variables`, etc.
- Labels have `signature` field populated after analysis
- For Spec 004, expect `SUBROUTINE` or `PURE_FUNCTION` strategies (no indirection)

### CodeEmitter Already Exists

From `src/m2py/codegen/emitter.py`:
- `line(code: str)` - emit at current indent
- `blank()` - empty line
- `indented()` - context manager for indent
- `get_code()` - return final string

### Test Fixtures Need Implementation

`tests/unit/codegen/conftest.py` has fixture definitions but they import from non-existent `m2py.codegen.generate_python` and `m2py.runtime.MUMPSRuntime`. These must be implemented.

### MUMPS Coercion Rules (ANSI 7.1.4.5)

1. Apply sign reduction rules (++→+, +-→-, -+→-, --→+) repeatedly
2. Find longest head matching `numlit` syntax
3. Canonicalize per 7.1.4.4 (strip leading zeros except for decimal <1)

Examples:
- `"3A"` → 3
- `"A3"` → 0  
- `"  42"` → 42 (leading whitespace preserved in sign reduction)
- `""` → 0
- `"007"` → 7
- `"+3"` → 3
- `"--5"` → 5
- `"+-5"` → -5

### Python Reserved Words

Must escape: `False`, `None`, `True`, `and`, `as`, `assert`, `async`, `await`, `break`, `class`, `continue`, `def`, `del`, `elif`, `else`, `except`, `finally`, `for`, `from`, `global`, `if`, `import`, `in`, `is`, `lambda`, `nonlocal`, `not`, `or`, `pass`, `raise`, `return`, `try`, `while`, `with`, `yield`

### Generated Code Pattern Target

```python
# Generated from: TEST S X=1 W X Q
from m2py.codegen.helpers import m_num, m_truth

_test = False  # $TEST tracking

def TEST():
    global _test
    X = 1
    _rt.write(str(X))
```

---

## Implementation Phases

### Phase 1: Foundation (Value Model + Infrastructure)

**Goal**: Establish core helpers and module structure that all code generation depends on.

**Deliverables**:

1. **`src/m2py/codegen/helpers.py`** - Pure coercion functions
   - `m_num(value)` - MUMPS numeric coercion
   - `m_truth(value)` - MUMPS truth evaluation  
   - `m_compare(left, op, right)` - Comparison with coercion
   - Tests in `test_s7_1_1_values.py`: `TestNumericCoercionCodegen`, `TestTruthValueCodegen`, `TestComparisonCodegen`

2. **`src/m2py/codegen/names.py`** - Name translation
   - `NameTranslator.translate(mumps_name)` - M→Python
   - `NameTranslator.reverse(python_name)` - Python→M
   - Handle: %, pure numeric, reserved words, case preservation
   - Tests in `test_s6_1_routine_head.py`: `TestNameTranslationCodegen`

3. **`src/m2py/runtime/__init__.py`** - Minimal runtime
   - `MUMPSRuntime` class with `write()`, `get_output()`, `execute()`
   - `ExecutionResult` dataclass
   - Tests in `test_language_semantics.py`: `TestMUMPSRuntimeCodegen`

4. **`src/m2py/codegen/__init__.py`** - Public API stub
   - `generate_python(source)` - placeholder that calls parser + generator

**Acceptance Criteria**:
- [ ] `m_num("3A")` returns `3`
- [ ] `m_num("")` returns `0`
- [ ] `m_truth("0")` returns `False`
- [ ] `m_truth("1A")` returns `True`
- [ ] `translate("%START")` returns `"_pct_START"`
- [ ] `translate("if")` returns `"_m_if"`
- [ ] `MUMPSRuntime().write("X"); rt.get_output()` returns `"X"`

---

### Phase 2: Expression Generation

**Goal**: Generate Python expressions from ASG expression nodes.

**Deliverables**:

1. **`src/m2py/codegen/expressions.py`** - Expression generator
   - `generate_expr(expr: MExpr, ctx: GeneratorContext) -> str`
   - Handle: `MLiteral`, `MVariable`, `MBinaryOp`, `MUnaryOp`
   - Tests in `test_s7_1_4_literals.py`, `test_s7_1_2_variables.py`, `test_s7_2_operators.py`

**Expression Mapping**:

| ASG Type | Python Output |
|----------|---------------|
| `MLiteral(INTEGER, 42)` | `42` |
| `MLiteral(STRING, "foo")` | `"foo"` |
| `MVariable("X")` | `X` (translated) |
| `MBinaryOp("+", a, b)` | `(m_num(a) + m_num(b))` |
| `MBinaryOp("=", a, b)` | `m_compare(a, "=", b)` |
| `MBinaryOp("<", a, b)` | `m_compare(a, "<", b)` |
| `MUnaryOp("-", x)` | `(-m_num(x))` |

**Acceptance Criteria**:
- [ ] Integer literal generates Python int
- [ ] String literal generates Python string with proper escaping
- [ ] Variable reference uses translated name
- [ ] Arithmetic preserves left-to-right evaluation
- [ ] Comparisons use `m_compare()` wrapper

---

### Phase 3: Basic Statement Generation

**Goal**: Generate Python statements for SET, WRITE, QUIT.

**Deliverables**:

1. **`src/m2py/codegen/statements.py`** - Statement generator
   - `generate_statement(stmt: MStatement, ctx: GeneratorContext)`
   - Handle: `MSetStatement`, `MWriteStatement`, `MQuitStatement`
   - Tests in `test_s8_2_18_set.py`, `test_s8_2_25_write.py`, `test_s8_2_16_quit.py`

**Statement Mapping**:

| ASG Type | Python Output |
|----------|---------------|
| `MSetStatement(X=1)` | `X = 1` |
| `MWriteStatement("hi")` | `_rt.write("hi")` |
| `MWriteStatement(X)` | `_rt.write(str(X))` |
| `MQuitStatement()` | `return` |

**Acceptance Criteria**:
- [ ] `S X=1` generates `X = 1`
- [ ] `W "hello"` generates `_rt.write("hello")`
- [ ] `W X` generates `_rt.write(str(X))`
- [ ] `Q` generates `return`

---

### Phase 4: Control Flow (IF/ELSE)

**Goal**: Generate Python if/else with $TEST tracking.

**Deliverables**:

1. Extend `statements.py` with IF/ELSE handling
   - `MIfStatement` → `if m_truth(cond): ...` with `_test = m_truth(cond)`
   - `MElseStatement` → `if not _test: ...`
   - Tests in `test_s8_2_09_if.py`, `test_s8_2_04_else.py`

**Pattern**:
```python
# IF X>3 W "GT"
_test = m_truth(m_compare(X, ">", 3))
if _test:
    _rt.write("GT")

# ELSE W "LE"  
if not _test:
    _rt.write("LE")
```

**Acceptance Criteria**:
- [ ] IF condition sets `_test`
- [ ] IF true branch executes when condition true
- [ ] ELSE executes when `_test` is False
- [ ] Nested IF/ELSE chains work correctly

---

### Phase 5: FOR Loops

**Goal**: Generate Python loops from FOR statements.

**Deliverables**:

1. Extend `statements.py` with FOR handling
   - Bounded range → Python `for i in range(...)`
   - String list → Python `for i in [...]`
   - Tests in `test_s8_2_05_for.py`

**Pattern**:
```python
# F I=1:1:3 W I
for I in range(1, 3 + 1, 1):
    _rt.write(str(I))

# F I="A","B","C" W I
for I in ["A", "B", "C"]:
    _rt.write(str(I))
```

**Edge Cases**:
- Negative step: `F I=5:-1:3` → `range(5, 3-1, -1)` → [5,4,3]
- MUMPS is end-inclusive; Python range is end-exclusive

**Acceptance Criteria**:
- [ ] Bounded ascending loop iterates correct count
- [ ] Bounded descending loop iterates correct count
- [ ] String list iterates all values
- [ ] Loop variable has correct value at each iteration

**NOT in scope** (Spec 005):
- Open-ended FOR (`F I=1:1` no end) → `ForLoopType.OPEN_ENDED`
- Argumentless FOR (`F`) → `ForLoopType.ARGUMENTLESS`
- `loop_var_modified_in_body` analysis flag checks
- `has_internal_quit` / break pattern handling

---

### Phase 6: DO/GOTO Subroutines

**Goal**: Generate function calls for DO and GOTO to labels.

**Deliverables**:

1. Extend `statements.py` with DO/GOTO handling
   - `MDoStatement` → function call: `label()`
   - `MGotoStatement` → function call + return: `label(); return`
   - Tests in `test_s8_2_03_do.py`, `test_s8_2_06_goto.py`

2. **`src/m2py/codegen/routine.py`** - RoutineGenerator
   - Generate complete Python module from MRoutine
   - Each label becomes a Python function
   - Handle preamble (code before first label)
   - Tests in `test_s6_1_routine_head.py`, `test_s6_routine/`

**Pattern**:
```python
# TEST D SUB W "END" Q
def TEST():
    global _test
    SUB()
    _rt.write("END")

def SUB():
    global _test
    _rt.write("SUB")

# G LABEL pattern (transfer control, don't return)
def CALLER():
    global _test
    TARGET()  # call target
    return    # exit caller (GOTO semantics)
```

**Spec 004 Limitation**: GOTO is translated as call+return. No intra-label restructuring (forward jumps → if/else) which requires Spec 005. No cross-label variable visibility handling which requires Spec 006.

**Acceptance Criteria**:
- [ ] DO calls label as function
- [ ] Nested DO calls work
- [ ] GOTO generates function call + return (transfers control to label)
- [ ] Routine generates all labels as functions
- [ ] Generated code passes `ast.parse()`

**NOT in scope** (clarification):
- Intra-label GOTO restructuring (skipping statements within same label) → Spec 005
- Cross-label variable visibility threading → Spec 006

---

### Phase 7: Integration & Polish

**Goal**: End-to-end generation works for all acceptance scenarios.

**Deliverables**:

1. Wire up `generate_python()` public API
2. Implement fixture functions in `conftest.py`
3. Run all acceptance scenarios from spec
4. Generate YDB reference outputs for comparison
5. Achieve ≥85% coverage on codegen module

**Acceptance Criteria**:
- [ ] All 7 user stories pass
- [ ] All edge cases pass
- [ ] `ast.parse()` succeeds for all generated code
- [ ] Coverage ≥85%

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| GOTO complexity creep | Spec 004 only: call+return pattern. Restructuring (Spec 005) and variable visibility (Spec 006) explicitly deferred |
| FOR off-by-one errors | Explicit test cases for boundary conditions; only bounded literal ranges in scope |
| Coercion edge cases | Comprehensive test suite based on ANSI spec examples |
| Generated code invalid | `ast.parse()` validation after every generation |
| Scope creep from Spec 005/006 | Explicit "NOT in scope" notes in each phase; no ForLoopType analysis, no is_cross_label checks |

---

## Reference Documents

- [spec.md](spec.md) - Feature specification
- [research.md](research.md) - Research findings
- [data-model.md](data-model.md) - Entity definitions
- [quickstart.md](quickstart.md) - Usage guide
- [contracts/codegen-api.md](contracts/codegen-api.md) - API contract
- [contracts/runtime-api.md](contracts/runtime-api.md) - Runtime contract
- [codegen-plan.md](../codegen-plan.md) - Overall codegen strategy
