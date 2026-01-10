# Code Generation Plan

**Created**: 2026-01-06  
**Status**: Draft  
**Priority**: Complexity-first approach - tackle hardest structural problems while codebase is small

---

## Philosophy

1. **Correctness over everything** - Generated Python must match MUMPS semantics exactly
2. **Simplicity enables refactoring** - Clean output works better with Rope and similar tools
3. **Complexity first** - Solve hard structural problems early while codebase is small
4. **Incremental validation** - Each spec should produce testable output against YDB
5. **Layer separation** - If codegen discovers missing AST nodes, unresolved references, or analysis gaps, fix them in the parser or ASG analysis layer—never build parse-like or generic analysis code into codegen. Codegen should only translate a complete, resolved ASG to Python.
6. **Minimize runtime surface** - Prefer inline Python over runtime calls. The runtime exists for truly dynamic cases (globals, indirection, XECUTE). For statically analyzable patterns, emit direct Python code even if slightly verbose. Every runtime call is a refactoring barrier.

### Runtime vs Inline Decision Guide

**Use runtime for:**
| Feature | Why Runtime Required |
|---------|---------------------|
| Global variables (`^name`) | Database persistence, tree structure |
| Special variables (`$TEST`, `$HOROLOG`) | Process-wide state |
| XECUTE / Indirection | Truly dynamic, defeats static analysis |
| `REQUIRES_RUNTIME` scope strategy | Analysis explicitly gave up |
| Naked global references | Runtime naked indicator tracking |

**Emit inline Python for:**
| Feature | Python Translation |
|---------|--------------------|  
| Local variables | `x = value` (Python locals) |
| Parameters | `def foo(a, b):` |
| By-ref outputs | Return tuple: `return (x, y)` |
| FOR loops | `for i in range(...)` or `while` |
| Value coercion | Inline `m_num()` calls (pure helper) |
| Comparisons | Inline `m_compare()` calls (pure helper) |

**Heuristic**: If Rope could refactor it → emit Python variables/functions. If the value depends on runtime state → use runtime.

---

## Research Resources

Each spec has a Research Phase with specific files to review. Common resources:

- **`docs/`**: ASG structure (`docs/asg/`), analysis passes (`docs/analysis/`), codegen strategies (`docs/codegen/`)
- **`validate_asg.py`**: Dump ASG for any M code to understand structure before generating Python
  - File: `uv run python utils/validate_asg.py --compact path/to/file.m`
  - Inline: `uv run python utils/validate_asg.py --compact -c "TEST S X=1 W X Q"`
  - Full detail: omit `--compact` flag
- **MUMPS spec**: https://71.174.62.16/Demo/AnnoStd (local mirror in `mumps-reference/`) - remember to keep scope in mind after reading this, we are implementing in phases!

---

## Post-Implementation Documentation

After completing each spec, update documentation with concrete implementation details:

### This File (codegen-plan.md)

1. **Mark deliverables complete**: Change `- [ ]` to `- [x]` for all completed items
2. **Add Implementation Notes section**: Document actual patterns used, key decisions made, and lessons learned
3. **Update subsequent specs**: Add "Pre-requisites from Spec N" sections documenting:
   - Infrastructure now available
   - Key implementation questions answered
   - Patterns that work well (or don't)

### docs/codegen/ Updates

1. **Update illustrative code examples** with actual generated code patterns
2. **Add helper function documentation** (e.g., `m_num()`, `m_truth()` after Spec 004)
3. **Update runtime_requirements.md** with actual `MUMPSRuntime` API
4. **Document name translation** in mumps_gotchas.md with actual `NameTranslator` prefixes

### docs/architecture.md Updates

1. **Update directory structure** to include new modules (e.g., `codegen/`, `runtime/`)
2. **Add new pipeline phases** (e.g., Phase 6: Code Generation)
3. **Update data flow diagram** if architecture changes

### docs/README.md Updates

1. **Add Quick Start examples** for new public APIs (e.g., `generate_python()`)

### Why This Matters

- Future specs build on prior work; concrete details prevent re-learning
- Documentation reflects actual state, not planned state
- Test fixtures and patterns can be reused across specs
- Avoids "change" language and spec references that become stale

---

## Cross-Cutting Concerns

### M Semantic Foundations

These foundational semantics must be correct from the earliest spec to avoid painful refactors:

#### Value Model & Coercion

MUMPS has unusual coercion rules that affect comparisons and truth evaluation:

- **Numeric coercion** (per ANSI 7.1.4.5): Scan left-to-right for longest valid numeric prefix, canonicalize
  - `"3A"` coerces to `3`
  - `"A3"` coerces to `0` (no leading numeric)
  - `"  42"` coerces to `42` (sign reduction rules strip leading +)
  - `""` coerces to `0`
- **Truth values** (per ANSI 1.2.4): Based on **numeric interpretation**
  - The numeric value `0` is false; all other numeric values are true
  - Therefore: `""`, `"0"`, `"A"`, `"0A"` are all **false** (numeric value = 0)
  - And: `"1"`, `"3.14"`, `"1A"`, `"-5"` are all **true** (numeric value ≠ 0)
- **Comparison operators** (`<`, `>`) force numeric evaluation

**Required helpers** (Spec 004): `m_num()`, `m_truth()`, `m_compare()` to enforce M rules even for simple cases.

#### $TEST Special Variable

Critical semantics often missed:

1. **Postconditions do NOT update $TEST** - only IF conditions do
2. **$TEST is stacked for argumentless DO and extrinsic calls** - restored on QUIT
3. **$TEST is NOT stacked for DO with arguments or XECUTE** - mutations visible to caller
4. **$TEST is set by timeout commands** (per ANSI 7.1.4.10): OPEN, LOCK, JOB, READ with timeout set $TEST to indicate success/failure

```mumps
I X=1     ; $TEST = 1
S:Y=2 Z=1 ; Postcondition evaluated but $TEST unchanged (still 1)
E W "no"  ; This executes based on previous IF, not postcondition
```

#### Array/Variable Model

MUMPS arrays are **sparse trees where each node can have both a value AND children**:

```mumps
S A=1         ; A has value 1
S A(1)=2      ; A still has value 1, A(1) has value 2
S A(1,2)=3    ; A(1) still has value 2, A(1,2) has value 3
```

This differs from Python dicts where keys are exclusive. NEW/KILL operate on "variable and all descendants."

### Variable Scoping

MUMPS variable scoping is unusual and affects nearly all code generation decisions:

1. **Default visibility**: Variables are visible to callees unless explicitly NEWed
2. **NEW creates local scope**: `N X` saves caller's X, creates new local X  
3. **Formal parameters are implicitly NEWed**: Parameters are local to callee
4. **Call-by-reference creates aliases**: `.X` in argument list shares the variable

**Analysis infrastructure** (already implemented in `src/m2py/analysis/variables.py`):
- `ScopeVariables`: Tracks reads, writes, NEWed variables per label
- `FunctionSignature`: Computed signature with `scope_strategy` classification
- `input_variables` / `output_variables`: Variables from/to caller scope
- `byref_outputs`: Formal params actually modified (affects call-site code)
- Transitive analysis: Propagates inputs/outputs through call chains

**Code generation implications**:

| ScopeStrategy | Meaning | Python Pattern |
|---------------|---------|----------------|
| `PURE_FUNCTION` | No side effects, returns value | `def f(args) -> T` |
| `FUNCTION_WITH_OUTPUTS` | Returns + side effects | `def f(args) -> Tuple` |
| `SUBROUTINE` | Side effects only | `def f(args) -> None` or return dict |
| `REQUIRES_RUNTIME` | Indirection/XECUTE defeats analysis | Runtime scope |

**Cross-label variable visibility** complicates GOTO translation since variables may be visible across labels without explicit passing. The strategy chosen in Spec 006 must account for this.

### Code Generation Architecture

**Approach**: Section-based Builder/Emitter pattern with `CodeEmitter` class.

#### Why Not Alternatives?

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **String concatenation** | Simple | No indent tracking, error-prone | ❌ |
| **Python `ast` module** | Guaranteed valid AST | Very verbose, hard to read output | ❌ |
| **LibCST** | Preserves formatting | Extremely verbose, overkill | ❌ |
| **Jinja2 templates** | Readable templates | Logic gets messy, indent issues | ❌ |
| **Builder/Emitter** | Clean API, indent-aware | Slightly more setup | ✅ |

#### CodeEmitter Design

Core API (see `src/m2py/codegen/emitter.py` for implementation):

```python
class CodeEmitter:
    def line(self, code: str): ...      # Emit at current indent
    def blank(self): ...                 # Emit empty line
    def indented(self): ...              # Context manager: with emit.indented():
    def append(self, other): ...         # Merge another emitter (re-indented)
    def get_code(self) -> str: ...       # Return final string
```

**Usage pattern**:
```python
def generate_if(emit: CodeEmitter, stmt: MIfStatement, ctx: GeneratorContext):
    emit.line(f"if m_truth({generate_expr(stmt.condition, ctx)}):")
    with emit.indented():
        for substmt in stmt.then_scope.statements:
            generate_statement(emit, substmt, ctx)  # Correct indent automatically!
```

#### Section-Based Generation

For late additions (imports), collect during generation, emit at end:
```python
class RoutineGenerator:
    imports: set[str] = set()  # Populated during _generate_body()
    body = CodeEmitter()
    
    def generate(self) -> str:
        self._generate_body()  # Phase 1: body + imports collected
        result = CodeEmitter()
        for imp in sorted(self.imports): result.line(imp)
        result.append(self.body)  # Phase 2: compose
        return result.get_code()
```

#### Key Benefits

1. **Correct nesting at any depth**: `with emit.indented()` tracks indent automatically
2. **No string splitting**: Nested generators write directly to shared emitter
3. **Late additions**: Imports, declarations collected during generation, emitted at end
4. **Debuggable output**: Generated code is human-readable, easy to inspect
5. **Validation**: Call `ast.parse(result)` at end to catch syntax errors

#### Structural Decisions Before Emission

For patterns like GOTO (Spec 006), analyze ASG structure **before** emitting any code:

```python
def generate_routine(routine: MRoutine) -> str:
    # Analyze which labels are GOTO targets (already in ASG)
    goto_targets = routine.control_flow.goto_targets
    
    if goto_targets:
        return generate_with_state_machine(routine, goto_targets)
    else:
        return generate_linear(routine)
```

The structural decision (state machine vs. linear) is made from ASG analysis, not discovered mid-generation.

### Line Mapping Infrastructure (for Computed Offsets)

Computed offsets like `G LABEL+expr` require line-indexed execution at runtime.

**Existing infrastructure**:
- `MLabel.line_number`: Set during parsing, 1-indexed source line
- `MRoutine.source_lines`: All source lines stored for $TEXT support
- `MRoutine.get_text_line(n)`: Returns nth source line
- `MRoutine.get_text_at_label(label, offset)`: Returns source at label+offset
- `MCall.offset`: Full `MExpr` - can be any expression

**Gap for codegen** (to be built in Spec 008):
- Statement line number tracking: `MStatement.line_number` not yet populated
- Line-to-entry-point mapping: Build `Dict[int, Callable]` at routine init
- Runtime dispatch: `_line_dispatch(label.line + int(offset_expr))`

---

## Spec Overview

| Spec | Focus | Complexity | Key Risk |
|------|-------|------------|----------|
| **004** | Minimal Control Flow Foundation | Low | Just enough for 005/006 |
| **005** | Structured Control Flow + Variable Scoping | Medium | $TEST tracking, scope strategies |
| **006** | Cross-Label GOTO | **High** | Strategy selection, variable visibility |
| **007** | Indirection & XECUTE | **High** | Runtime infrastructure, eval/exec |
| **008** | Core Language Completion | Medium | Computed offsets, naked globals |
| **009** | External Calls & Advanced | Medium | Cross-module coordination |

---

## Spec 004: Minimal Control Flow Foundation

**Goal**: Absolute minimum to validate control flow in specs 005/006

Control flow testing doesn't need computation—just path verification. We output markers to show which branches executed.

### Research Phase

Review before coding:
- **Docs**: `docs/asg/expressions.md`, `docs/asg/statements.md`, `docs/codegen/index.md`
- **Expressions**: `asg/expressions.py` → `MLiteral`, `MVariable`, `MBinaryOp`, `MUnaryOp`
- **Statements**: `asg/statements.py` → `MSetStatement`, `MWriteStatement`, `MIfStatement`, `MForStatement`, `MGotoStatement`
- **Structure**: `asg/elements.py` → `MLabel.body.statements`, `MRoutine.labels`
- **Scope**: `analysis/variables.py` → `ScopeStrategy`, `FunctionSignature.scope_strategy`
- **ASG dump**: `uv run python utils/validate_asg.py --compact -c "TEST S X=1 W X Q"`

### Scope (Minimal)

1. **Literals**
   - Numeric literals (integers only: `1`, `10`, `-5`)
   - String literals (`"A"`, `"PASS"`)

2. **Local Variables**
   - Simple names only (`X`, `I`, `COUNT`)
   - No subscripts, no globals

3. **Operators (Comparison + Basic Arithmetic)**
   - Comparison: `=`, `<`, `>`
   - Arithmetic: `+`, `-` (for loop increments)
   - Left-to-right with parenthesization

4. **Statements (Minimal Set)**
   - `SET` - single assignment only (`S X=1`)
   - `WRITE` - single value only (`W X` or `W "text"`)
   - `QUIT` - with and without value
   - `DO` - label call within same routine (no offset)
   - `IF` / `ELSE` - basic condition
   - `FOR` - all loop types with **literal parameters** (e.g., `F I=1:1:10`, `F I="A","B"`)
   - `GOTO` - label targets only, **no offsets** (e.g., `G LABEL`, not `G LABEL+5`)

### Explicitly Deferred to Spec 008

- Intrinsic functions ($PIECE, $LENGTH, $GET, etc.)
- Global variables (^name)
- READ command
- NEW / KILL commands
- Logical operators (&, !)
- String concatenation (_)
- Pattern match (?)
- Negated comparisons ('=, '<, '>)
- Multiple assignments (S X=1,Y=2)
- Format controls (!, #, ?n)
- Postconditions (S:cond X=1)
- Extrinsic functions ($$func)
- Subscripted variables
- **DO/GOTO with offsets** (`G LABEL+5`, `D SUB+N`)
- **Complex FOR parameters** (`F I=$D(I):1:^MAX`)

### Name Translation (Labels, Routines, Variables)

MUMPS names are **case-sensitive** and allow patterns that would be invalid Python identifiers. The same translation rules apply to labels, routine names, and variable names:

| MUMPS Pattern | Example | Python Translation |
|---------------|---------|-------------------|
| `%` prefix | `%ROUTINE`, `%0` | `_pct_ROUTINE`, `_pct_0` |
| Pure numeric | `0`, `01`, `00000` | `_n_0`, `_n_01`, `_n_00000` |
| Reserved words | `DO`, `IF`, `SET` | `_m_DO`, `_m_IF`, `_m_SET` |
| Empty (labelless preamble) | (first lines before any label) | `_preamble` |

**Critical**: MUMPS is case-sensitive (`FOO` ≠ `Foo` ≠ `foo`). Name translation must be:
- **Case-preserving**: Maintain original case distinction
- **Injective**: No two M names map to the same Python name
- **Reversible**: Can recover original M name from Python name

**Note**: Leading zeros are significant (`01` ≠ `1`).

**Scope by Spec**:
- **Spec 004**: Label names (used as Python function names)
- **Spec 004**: Local variable names (used as Python variable names)  
- **Spec 009**: Routine names (used as Python module names)

### Deliverables

- [x] `src/m2py/codegen/` module structure
- [x] **M value model**: `m_num()`, `m_truth()`, `m_compare()` coercion helpers
  - Tests: `TestNumericCoercionCodegen`, `TestTruthValueCodegen`, `TestComparisonCodegen` in [test_s7_1_1_values.py](../tests/unit/codegen/s7_expressions/test_s7_1_1_values.py)
- [x] **Case-preserving, injective name translator** (handle %, numeric, reserved words for labels and variables)
  - Tests: `TestNameTranslationCodegen` in [test_s6_1_routine_head.py](../tests/unit/codegen/s6_routine/test_s6_1_routine_head.py)
- [x] Expression generator (numeric, string, variable, comparison, arithmetic)
  - Tests: `TestValuesCodegen`, `TestLiteralsCodegen`, `TestOperatorsCodegen` in [s7_expressions/](../tests/unit/codegen/s7_expressions/)
- [x] Statement generators (SET, WRITE, QUIT, DO, IF, ELSE, FOR, GOTO)
  - Tests: `TestSetCommandCodegen`, `TestWriteCommandCodegen`, `TestQuitCommandCodegen`, `TestDoCommandCodegen`, `TestIfCommandCodegen`, `TestElseCommandCodegen`, `TestForCommandCodegen`, `TestGotoCommandCodegen` in [s8_commands/](../tests/unit/codegen/s8_commands/)
- [x] Routine → Python module translation (single routine, labels as structure)
  - Tests: `TestRoutineHeadCodegen`, `TestRoutineBodyCodegen` in [s6_routine/](../tests/unit/codegen/s6_routine/)
- [x] `MUMPSRuntime` class with `_test` tracking for IF/ELSE
  - Tests: `TestTestVariableCodegen` in [test_language_semantics.py](../tests/unit/cross_cutting/test_language_semantics.py)

### Implementation Notes

**Spec 004 Complete** (2025-01-XX): All 60 tasks across 10 phases implemented. Key lessons:

#### Generated Code Structure (Actual)

```python
from m2py.codegen.helpers import m_num, m_truth, m_compare
from m2py.runtime import MUMPSRuntime

_rt = MUMPSRuntime()

_test = False

def TEST():
    global _test
    X = 1
    _rt.write(str(X))
```

Key decisions made:
- **Module-level `_rt`**: Single runtime instance per module for output capture
- **Module-level `_test`**: Simple approach for $TEST tracking; each function declares `global _test`
- **Labels as functions**: Direct translation, `NameTranslator` handles % prefix, numeric, keywords

#### Concrete Helper Implementations

**`m_num()`** (src/m2py/codegen/helpers.py):
- Handles leading sign chains: `+-5` → `-5`, `--5` → `5`
- Leading whitespace stripped: `"  42"` → `42`  
- Extracts longest left-head numeric prefix: `"3.14ABC"` → `3.14`
- Returns `int` when possible: `"3.0"` → `3`

**`m_truth()`**:
- `m_truth(x)` is NOT `bool(m_num(x))` - must return `bool(m_num(x) != 0)`
- Empty string → `False` (via m_num → 0)
- `"0.0"` → `False` (canonicalizes to 0)

**`m_compare()`**:
- `op="="` does type-aware comparison: both look numeric → numeric comparison
- Other ops (`<`, `>`) always do numeric coercion via `m_num()`
- String equality is exact: `"007"` ≠ `"7"`

#### Name Translation Patterns (Actual)

`NameTranslator` class with three prefix patterns:

| MUMPS | Python | Prefix |
|-------|--------|--------|
| `%START` | `_pct_START` | `_pct_` for % prefix |
| `01` | `_n_01` | `_n_` for pure numeric |
| `if` | `_m_if` | `_m_` for Python keywords |

Case preservation verified: `FOO`, `foo`, `Foo` remain distinct.

#### Statement Generation Patterns

**Dispatcher pattern** in `generate_statement()`:
```python
def generate_statement(stmt: MStatement, ctx: GeneratorContext) -> None:
    match stmt:
        case MSetStatement(): _generate_set(stmt, ctx)
        case MWriteStatement(): _generate_write(stmt, ctx)
        case MIfStatement(): _generate_if(stmt, ctx)
        # ...
        case _: raise UnsupportedFeatureError(f"Unsupported: {type(stmt)}")
```

**FOR loop patterns discovered**:
- `F I=1:1:10` → `for I in range(1, 11, 1):` (bounded)
- `F I="A","B"` → `for I in ["A", "B"]:` (string list)  
- Loop variables are local Python vars, not runtime

**GOTO/DO simplified patterns**:
- `G LABEL` → `return LABEL()` (simple function call)
- `D LABEL` → `LABEL()` (call without return)
- Cross-label GOTO deferred to Spec 006 state machine

#### Test Fixture Patterns

`execute_mumps` fixture pattern (conftest.py):
```python
@pytest.fixture
def execute_mumps(generate_python):
    def _execute(source: str) -> ExecutionResult:
        python_code = generate_python(source)
        rt = MUMPSRuntime()
        rt.execute(python_code)  # Uses isolated namespace
        return ExecutionResult(output=rt.get_output(), success=True, ...)
    return _execute
```

`MUMPSRuntime.execute()` pattern:
1. Create isolated `namespace` dict
2. Inject `_rt`, helpers into namespace
3. `exec(python_code, namespace)` - defines functions
4. Find entry point function name
5. `namespace[entry_point]()` - call it
6. Return captured output

#### Insights for Future Specs

1. **$TEST handling is simple at module level** - but Spec 005's stack semantics will require:
   - Per-call context for argumentless DO
   - Return value to restore $TEST after call

2. **Variable locals work well** - but by-reference params (Spec 005) need return-tuple pattern:
   ```python
   def SWAP(A, B):
       return B, A  # Caller does: A, B = SWAP(A, B)
   ```

3. **Labels-as-functions is clean** - but cross-label GOTO (Spec 006) needs either:
   - Shared `RoutineState` class for variables
   - State machine with outer-scope variables

4. **Runtime.execute() already supports eval/exec** - foundation for Spec 007 XECUTE

**Local Variables → Python Locals (NOT runtime)**:
- `S X=5` → `x = 5` (Python assignment)
- `W X` → `print(x)` or `_output.append(str(x))`
- Do NOT use `_rt.get("X")` / `_rt.set("X", value)` for local variables
- Use `NameTranslator` to convert M names to Python identifiers

**Runtime reserved for**:
- Global variables (`^name`) - deferred to Spec 008
- `$TEST` special variable - needs process-wide state
- Output accumulation (`_rt.write()`) - for test harness capture

**Why this matters**: Using runtime for locals would:
1. Bypass all the `ScopeVariables`/`FunctionSignature` analysis work
2. Make Rope refactoring impossible (`_rt.get("X")` is opaque)
3. Turn the transpiler into a MUMPS interpreter

**Scope strategy check**: Even in Spec 004, verify `FunctionSignature.scope_strategy` is `PURE_FUNCTION` or similar before emitting Python locals. If `REQUIRES_RUNTIME`, use runtime scope access.

### Test Strategy: Embedded Unit Tests

**Do NOT use `.m` files or YDB/MUGJ tests directly yet** - they require I/O overhead and additional syntax.

Use embedded strings in pytest, matching existing codegen test patterns in `tests/unit/codegen/`:

```python
@pytest.mark.codegen
class TestForwardGoto:
    def test_forward_goto_skips_intermediate_code(self, execute_mumps):
        """Forward GOTO skips intervening code."""
        result = execute_mumps(
            "TEST S X=1\n"
            "     G DONE\n"
            "     S X=2\n"
            "DONE W X Q\n"
        )
        assert result.output == "1"

    def test_if_true_branch(self, execute_mumps):
        """IF evaluates condition and takes true branch."""
        result = execute_mumps(
            "TEST S X=5\n"
            "     I X>3 W \"GT\" Q\n"
            "     E  W \"LE\" Q\n"
        )
        assert result.output == "GT"

    def test_bounded_for_counts(self, execute_mumps):
        """FOR bounded loop iterates correct count."""
        result = execute_mumps(
            "TEST F I=1:1:3 W I\n"
            "     Q\n"
        )
        assert result.output == "123"
```

**Generating known-good output with YDB**:

Run a file: `docker run --rm -v "$(pwd):/workspace" ydb HELLO.m` → outputs Hello World

Run from stdin: `echo -e 'STDIN\n write "Hello from stdin",!' | docker run --rm -i ydb` → outputs Hello from stdin

Note for stdin: The M code needs to start with a label line (like STDIN) on the first line, followed by the code with proper indentation (space before commands).

**Fixtures available** (from `tests/unit/codegen/conftest.py`):

| Fixture | Use Case | Example |
|---------|----------|---------|
| `generate_python(source)` | Inspect generated Python code | `assert "X = " in generate_python("TEST\n S X=1\n Q")` |
| `execute_mumps(source)` | Full routine execution | `assert execute_mumps("TEST\n S X=1\n W X\n Q").output == "1"` |
| `execute_expr(code)` | Single command (auto-wrapped) | `assert execute_expr('W 1+2') == "3"` |
| `eval_mumps(expr)` | Expression value (no WRITE) | `assert eval_mumps('$L("ABC")') == "3"` |

**One-liner fixtures** (`execute_expr`, `eval_mumps`) reduce boilerplate for simple tests:
```python
# Old pattern (verbose)
def test_addition(execute_mumps):
    result = execute_mumps("TEST\n W 1+2\n Q")
    assert result.output == "3"

# New pattern (concise)
def test_addition(execute_expr):
    assert execute_expr('W 1+2') == "3"

# Parametrized tests become clean
@pytest.mark.parametrize("expr,expected", [
    ("1+2", "3"),
    ('"A"_"B"', "AB"),
    ("$L(\"ABC\")", "3"),
])
def test_expressions(execute_expr, expr, expected):
    assert execute_expr(f'W {expr}') == expected
```

**When to generate expected outputs**: Generate YDB reference outputs **at the start of each phase**, not upfront. This avoids busy-work that may need revision as implementation reveals edge cases. Exception: Generate spike reference outputs (V1GO1.m, indirection-heavy VistA routines) before their respective spikes.

**Validation approach:**
1. Tests run via `uv run pytest tests/unit/codegen/`
2. Expected output is embedded in assertions
3. For complex cases, use `generate_python` to inspect generated code structure

### No Spikes Needed

Minimal, well-understood subset. Just implement and validate against YDB.

---

## Spec 005: Structured Control Flow

**Goal**: Handle common control flow patterns that map cleanly to Python

### Pre-requisites from Spec 004

The following infrastructure is now available:
- `_test` module-level variable with `global _test` in each function
- `m_truth()` for condition evaluation in IF statements
- Labels as Python functions callable via `LABEL()` / `return LABEL()`
- `NameTranslator` for variable/label name translation
- `MUMPSRuntime.execute()` with isolated namespace injection

### Key Implementation Decisions (Resolved)

1. **$TEST stacking for DO blocks**: Use save/restore pattern via local variable.
   - `_saved_test = _test` before block, `_test = _saved_test` after
   - Only DO blocks (D + dot-indented lines) and extrinsics stack $TEST
   - Label calls (D SUB, D SUB(), D SUB(X)) do NOT stack - callee's $TEST visible

2. **By-reference parameters**: Return-tuple pattern.
   - `A, B = SWAP(A, B)` - callee returns modified values
   - Call site destructures result back to original variables
   - Uses `FunctionSignature.byref_outputs` from analysis

3. **FOR loop variable modification**: Use `while` loop when `loop_var_modified_in_body=True`.
   - Track current value and step explicitly
   - `for` loop only when loop var unmodified

4. **Intra-label forward GOTO**: Inverted if/else restructuring.
   - Uses `target_stmt_index` computed from MUMPS offset semantics (LABEL+n)
   - `generate_scope_statements()` handles restructuring at scope level
   - Statements between IF and target go in `if not _test:` block

### Research Phase

Review before coding:
- **Docs**: `docs/analysis/for_analysis.md`, `docs/analysis/goto_analysis.md`, `docs/codegen/for_loops.md`
- **$TEST**: Where is $TEST represented? When stack/restore?
- **FOR analysis**: `analysis/for_analysis.py` → `ForLoopType`, `loop_var_modified_in_body`, `has_internal_quit`
- **GOTO**: `analysis/goto_analysis.py` → `GotoType`, `is_cross_label`, `is_loop_continue`
- **Scope**: `analysis/variables.py` → `FunctionSignature`, `ScopeStrategy`, `input_variables`, `output_variables`
- **QUIT**: `asg/statements.py` → `MQuitStatement.exits_for`, `.exits_do_block`, `.return_value`
- **ASG dump**: `uv run python utils/validate_asg.py --compact tests/functional/mugj/inref/V1FOR*.m`

### Scope

1. **IF/ELSE with $TEST tracking**
   - Track `_test` variable for ELSE and argumentless IF
   - Comma-separated conditions (AND semantics)
   - **Note**: Postconditions (deferred to Spec 008) do NOT update $TEST - document this behavior now
   
2. **$TEST Stack Semantics**
   - **DO block** (D + dot-indented lines): `$TEST` is stacked, restored after block
   - **Extrinsic calls** (`$$label`): `$TEST` is stacked, restored on return  
   - **Label calls** (D SUB, D SUB(), D SUB(X)): `$TEST` NOT stacked - callee mutations visible to caller
   - **XECUTE**: `$TEST` NOT stacked - mutations visible to caller
   
   Note: The term "argumentless DO" is ambiguous. A label call without args (`D SUB`) does NOT stack,
   but a DO block (`D` followed by dot-indented lines) DOES stack.

3. **FOR Loop Variations**
   - `ForLoopType.OPEN_ENDED` → `while True:` with increment
   - `ForLoopType.ARGUMENTLESS` → `while True:`
   - `ForLoopType.STRING_LIST` → `for x in [...]`
   - `ForLoopType.MIXED` → `itertools.chain` or unrolling
   - `loop_var_modified_in_body=True` → `while` loop
   - `has_internal_quit=True` → add `break` support

4. **Intra-Label GOTO** (`is_cross_label=False`)
   - Forward jumps → restructure to if/else
   - `is_loop_continue=True` → `continue`

5. **Loop Exits**
   - `GotoType.LOOP_EXIT` → `break`
   - `GotoType.MULTI_LOOP_EXIT` → Exception pattern

6. **QUIT Context Awareness** (ASG provides `exits_for` and `exits_do_block`)
   ```mumps
   F I=1:1:10 Q:I=5      ; QUIT exits FOR loop → break
   D  Q                  ; QUIT exits DO block → return from block
   Q X                   ; QUIT with value → return value from extrinsic
   ```
   - `MQuitStatement.exits_for` → `break`
   - `MQuitStatement.exits_do_block` → return from nested scope
   - `MQuitStatement.return_value` → return from subroutine/extrinsic

7. **Variable Scope Strategies**

   Generate Python functions using `FunctionSignature.scope_strategy` (see Cross-Cutting Concerns for strategy table).

   **By-reference handling**: When caller uses `.X`:
   ```mumps
   D SWAP(.A,.B)    ; Pass A and B by reference
   ```
   Generate return-value pattern for modified params in `byref_outputs`:
   ```python
   a, b = swap(a, b)  # swap returns modified values
   ```
   
   **Limitation**: Return-tuple breaks true aliasing (e.g., `D FOO(.A,.A)` where both params reference same variable). Such cases require `REQUIRES_RUNTIME` with runtime scope access, or detection + specialized codegen.

### Deliverables

- [x] $TEST tracking infrastructure with stack/restore for DO blocks (dot-indented)
  - Tests: `TestDoBlockTestRestore` → [test_s8_2_03_do.py](../tests/unit/codegen/s8_commands/test_s8_2_03_do.py)
  - Note: Only DO blocks (not label calls) stack $TEST
- [x] $TEST NOT stacked for label calls (D SUB, D SUB(), D SUB(X))
  - Tests: `test_label_call_*_test_visible` → test_s8_2_03_do.py
- [x] FOR loop strategy selector based on analysis flags
  - Tests: `TestForLoopCodegen` → [test_s8_2_05_for.py](../tests/unit/codegen/s8_commands/test_s8_2_05_for.py)
  - Patterns: BOUNDED, OPEN_ENDED (itertools.count), ARGUMENTLESS (while True), STRING_LIST, MIXED (chain)
- [x] Intra-label forward GOTO restructuring
  - Tests: `test_forward_jump_restructures_*` → [test_s8_2_06_goto.py](../tests/unit/codegen/s8_commands/test_s8_2_06_goto.py)
  - Implementation: `_find_forward_goto_in_if()`, `_restructure_forward_goto()`, `generate_scope_statements()`
  - Uses `target_stmt_index` computed from MUMPS offset semantics (LABEL+n)
- [x] Backward intra-label GOTO raises UnsupportedFeatureError
  - Tests: `test_backward_intra_label_goto_raises_error` → test_s8_2_06_goto.py
  - Deferred to Spec 006 for proper loop restructuring
- [ ] Loop exit translation (break, exception) for GOTO
  - Tests: `test_*_loop_exit_*` → test_s8_2_06_goto.py
- [ ] QUIT context-aware code generation
  - Tests: `TestQuitCommandCodegen` → [test_s8_2_16_quit.py](../tests/unit/codegen/s8_commands/test_s8_2_16_quit.py)
- [ ] Scope strategy code generation (PURE_FUNCTION, SUBROUTINE, etc.)
  - Tests: `TestScopeStrategyCodegen` → test_s8_2_03_do.py
- [ ] By-reference parameter return value pattern
  - Tests: `TestByRefParameterCodegen` → test_s8_2_03_do.py
- [ ] Extrinsic function $TEST stacking
  - Tests: `test_extrinsic_*_test_restore` → [test_s7_1_1_values.py](../tests/unit/codegen/s7_expressions/test_s7_1_1_values.py)
- [ ] Postconditions do NOT update $TEST (explicit test)
  - Tests: `TestPostconditionsCodegen` → [test_postconditions.py](../tests/unit/cross_cutting/test_postconditions.py)
- [ ] **Post-implementation documentation** (see [Post-Implementation Documentation](#post-implementation-documentation) section)
  - Update codegen-plan.md: mark deliverables complete, add implementation notes
  - Update docs/codegen/ with actual patterns used
  - Add pre-requisites section to Spec 006

### Validation

- Embedded pytest tests (see 004 test strategy)
- Focus: Every FOR loop type, every GOTO classification within label, every scope strategy
- **Critical $TEST tests**:
  - ELSE after argumentless DO sees restored $TEST
  - ELSE after DO with argument sees mutated $TEST
  - ELSE after postcondition sees $TEST from prior IF (not postcondition)

### Spike: $TEST Elimination

**Hypothesis**: Many IF/ELSE chains can be restructured to eliminate explicit `_test` tracking.

**Test**: Create minimal IF/ELSE/argumentless-IF test case, translate with explicit `_test`, then attempt restructuring. Measure:
- How many `_test` references remain?
- Is restructured code clearer?

**Decision**: If >80% eliminable, make restructuring the default. Otherwise, always use `_test`.

---

## Spec 006: Cross-Label Control Flow

**Goal**: Handle GOTO patterns that cross label boundaries

This is the **highest complexity** area. The ASG provides classification but translation strategy is TBD.

### Pre-requisites from Spec 004

The following infrastructure is now available:
- Labels as functions pattern works for simple cases
- `return LABEL()` pattern for GOTO (tail-call semantics)
- `LABEL()` pattern for DO (call and continue)
- `NameTranslator` for function names

### Key Limitation Discovered in Spec 004

Current pattern `return LABEL()` has stack growth for repeated GOTO:
```python
def A(): 
    return B()  # Calls B, which calls C, which calls A → stack grows
def B():
    return C()
def C():
    return A()  # Back to A but stack depth = 3 now
```

This means **trampoline pattern is required** for cross-label GOTO to avoid RecursionError.

### Variable Visibility Challenge

Spec 004 uses Python locals within each function. Cross-label needs shared state:
```mumps
MAIN S X=1
     G NEXT
NEXT S Y=X+1    ; Needs access to X set in MAIN
     W Y Q
```

Options:
1. **State class**: `RoutineState(x=None, y=None)` passed to all labels
2. **Outer scope**: All vars in module scope, labels are inner functions
3. **Runtime**: `_rt.get("X")` - but this undermines local var optimization

Spec 006 research spike should evaluate these options.

### Research Phase
Review before coding:
- **Docs**: `docs/analysis/goto_analysis.md`, `docs/codegen/goto_handling.md`, `docs/analysis/variable_analysis.md`
- **Cross-label detection**: `analysis/goto_analysis.py` → `is_cross_label`, classification
- **Routine flags**: `asg/elements.py` (`MRoutine`) → `has_unstructured_goto`, targets
- **Variable visibility**: `analysis/variables.py` → `input_variables`, `output_variables` per label
- **Line numbers**: `MLabel.line_number`, `MStatement.line_number` → populated?
- **CFG analysis**: Predecessors, successors, dominators → does it exist?
- **ASG dump**: `uv run python utils/validate_asg.py --compact tests/functional/mugj/inref/V1GO1.m`

**Output**: Decision criteria for labels-as-functions vs state machine.

### Scope

1. **Cross-Label Forward Jump** (`FORWARD_JUMP` + `is_cross_label=True`)
   - Jump to code in a later label
   - Cannot use simple if/else restructuring

2. **Cross-Label Backward Jump** (`BACKWARD_JUMP` + `is_cross_label=True`)
   - Creates implicit loop across labels
   - Most challenging pattern

3. **`has_unstructured_goto=True` Routines**
   - Irreducible control flow
   - Requires fallback strategy

4. **Cross-Label Variable Visibility**
   
   Variables set in one label are visible in another unless NEWed. This complicates translation because:
   - Labels-as-functions need to share state (closure, globals, or explicit passing)
   - State machine approach keeps all vars in outer scope (simpler)
   
   The variable analysis infrastructure provides `input_variables` and `output_variables` per label, enabling explicit state threading if needed.

5. **Line-Based Dispatch Foundation**
   
   Build the dispatch architecture here (even with literal offsets only) to avoid architectural fork with computed offsets in Spec 008:
   - Build `_line_map` keyed by **source line number** (not statement index)
   - Emit per-line entry points
   - Cross-label GOTO uses same dispatch mechanism (jump to label's line number)
   - GOTO targets must be at same execution LEVEL (per ANSI 8.2.6, error M45 if violated)
   
   This prepares for computed offsets (`G LABEL+expr`) without major refactoring.

### DEFERRED to Spec 008: Computed Offsets

Computed offsets like `G LABEL+expr` are deferred because they require full expression evaluation:

```mumps
G STAR+^V1A                    ; Needs global variable evaluation
G NOTES+C+(D*2)+E=29.3+3       ; Needs all arithmetic operators
G 388+$L($E(VCOMP,5,99))       ; Needs intrinsic function evaluation
```

**Why deferred:**
- Offset expressions can include globals, functions, all operators
- Current analysis doesn't account for where offsets land (may cross label boundaries)
- Requires line-indexed execution model (jump to line N, not label)

**Spec 006 handles**: Simple label targets only (`G LABEL`, `G LABEL^ROUTINE` same-routine pattern)
**Spec 008 adds**: Offset targets (`G LABEL+n`, `G LABEL+expr`)
**Spec 009 adds**: Cross-routine external calls (module loading, `G LABEL^OTHER_ROUTINE`)

### Strategy Candidates

#### Option A: Labels-as-Functions with Trampoline

```python
class RoutineState:  # Shared variables across labels
    x: int = 0

def label_A(state) -> str | None:
    state.x = 1
    return "B" if condition else None  # Return next label or None to exit

# Trampoline (REQUIRED - prevents RecursionError)
next_label = "A"
while next_label:
    next_label = labels[next_label](state)
```
**Pros**: Refactorable, Rope-friendly | **Cons**: State class overhead

#### Option B: State Machine (Match-Case)

```python
state, x = "A", 0  # Variables in outer scope
while True:
    match state:
        case "A": x = 1; state = "B" if condition else None
        case "B": state = "A"
    if state is None: break
```
**Pros**: Simple, natural variable visibility | **Cons**: Not refactorable

#### Selection Criteria

- `has_unstructured_goto=True` → State Machine (required)
- Computed offset target (`G LABEL+expr`) → State Machine (line dispatch)
- Otherwise → Labels-as-Functions (preferred)

### Deliverables

- [ ] Cross-label jump detector (which labels are targets?)
  - Tests: `TestCrossLabelGotoCodegen` → [test_s8_2_06_goto.py](../tests/unit/codegen/s8_commands/test_s8_2_06_goto.py)
- [ ] Computed offset target detector (is label referenced with +offset?)
  - Tests: `TestComputedOffsetCodegen.test_computed_offset_target_detection` → [test_s8_2_18_set.py](../tests/unit/codegen/s8_commands/test_s8_2_18_set.py)
- [ ] Labels-as-functions generator with shared state class + trampoline
  - Tests: `TestTrampolinePatternCodegen` → test_s8_2_06_goto.py
- [ ] State machine generator (fallback) with match-case
  - Tests: `TestStateMachineCodegen` → test_s8_2_06_goto.py
- [ ] Strategy selector based on `has_unstructured_goto` AND `is_offset_target`
  - Tests: `TestLineDispatchCodegen` → test_s8_2_06_goto.py
- [ ] Variable visibility handling for both strategies
  - Tests: `TestCrossLabelGotoCodegen.test_cross_label_goto_variable_visibility` → test_s8_2_06_goto.py
- [ ] **Post-implementation documentation** (see [Post-Implementation Documentation](#post-implementation-documentation) section)
  - Update codegen-plan.md: mark deliverables complete, add implementation notes
  - Update docs/codegen/goto_handling.md with actual strategy patterns
  - Add pre-requisites section to Spec 007

### Validation

- Embedded pytest tests with cross-label jumps
- V1GO1.m (for spike bake-off only - after we have enough syntax support)

### Spike: Strategy Bake-off (REQUIRED)

**Hypothesis**: Labels-as-functions produces cleaner output for most real code, with state machine only needed for truly pathological cases.

**Test**: Translate V1GO1.m using both strategies. Measure:

1. **Correctness**: Both produce same output as YDB?
2. **Line count**: Which is more concise?
3. **Refactorability**: Can Rope extract/rename in each?
4. **Percentage needing state machine**: How many V1GO1 patterns are truly irreducible?
5. **Variable visibility**: Does state class feel natural or awkward?

**Inputs for decision**:
- If labels-as-functions handles >90% of patterns → use as primary
- If state machine needed for >30% → consider state machine as primary
- If roughly equal → use hybrid with labels-as-functions preferred

**Secondary hypothesis**: The `is_cross_label` + `goto_type` classification is sufficient to select strategy automatically without runtime detection.

---

## Spec 007: Indirection & XECUTE Runtime

**Goal**: Handle dynamic code patterns pervasive in VistA

### Pre-requisites from Spec 004

The following infrastructure is now available:
- `MUMPSRuntime.execute(python_code)` - already supports dynamic code execution
- Isolated namespace injection pattern (inject `_rt`, helpers, then `exec()`)
- `generate_python()` API for on-demand MUMPS→Python translation

### Key Insight from Spec 004

`MUMPSRuntime.execute()` already does:
1. Create namespace with `_rt` and helpers
2. `exec(python_code, namespace)` to define functions
3. Call entry point function

For XECUTE, we need similar pattern but with MUMPS code as input:
```python
def execute_mumps(self, mumps_code: str) -> None:
    from m2py.codegen import generate_python
    python_code = generate_python(mumps_code)
    # ... same namespace injection pattern
```

This means Spec 007's runtime work is mostly building on Spec 004 foundation.

### Research Phase
Review before coding:
- **Docs**: `docs/asg/expressions.md` (indirection section), `docs/codegen/runtime_requirements.md`
- **Indirection ASG**: `asg/expressions.py` → `MIndirection`, types (name/argument/subscript)
- **Static detection**: `analysis/` → constant propagation? Compile-time resolvable?
- **XECUTE structure**: `asg/statements.py` → `MXecuteStatement` argument representation
- **`^%ZOSF` patterns**: Research VistA node values for lookup table
- **`REQUIRES_RUNTIME`**: `analysis/variables.py` → what triggers this scope?
- **ASG dump**: `uv run python utils/validate_asg.py --compact tests/functional/mugj/inref/V1XECA.m`

**Output**: Document static optimizations vs must-use-runtime patterns.

### Scope

1. **Runtime Infrastructure**
   
   Build the shared runtime that manages M semantics at execution time.
   **Note**: Basic global variable support (`^VAR`, `^VAR(sub)`) is included here so XECUTE/indirection tests can use realistic VistA patterns (e.g., `^%ZOSF`). Spec 008 adds extended global features (naked refs, complex subscripting).
   
   Core `MUMPSRuntime` API: `variables: dict`, `globals: dict`, `test: bool`, `execute(mumps_code)`, `get_global(name, *subs)`, `set_global(name, value, *subs)`

2. **Static Indirection** (resolvable at compile time)
   - `S NAME="X" W @NAME` → inline as `print(x)`
   - Track constant propagation through SET

3. **Dynamic Indirection** (runtime resolution)
   - `R NAME W @NAME` → `runtime.get_var(name)`
   - Name indirection in SET targets
   - Subscript indirection

4. **XECUTE Command**
   - Constant strings → inline translated code
   - Dynamic strings → `runtime.execute(code_string)`

5. **`^%ZOSF` Patterns**
   - Common in VistA: `X ^%ZOSF("TEST")`
   - Build lookup table for known platform codes
   - Fall back to runtime for unknown

### Deliverables

- [ ] MUMPSRuntime class with eval/exec support
  - Tests: `TestMUMPSRuntimeCodegen` → [test_s8_2_26_xecute.py](../tests/unit/codegen/s8_commands/test_s8_2_26_xecute.py)
- [ ] Constant propagation for static indirection
  - Tests: `TestIndirectionCodegen` → [test_indirection.py](../tests/unit/cross_cutting/test_indirection.py)
- [ ] Indirection expression generator
  - Tests: `TestExpressionIndirectionCodegen` → [test_s7_3_indirection.py](../tests/unit/codegen/s7_expressions/test_s7_3_indirection.py)
- [ ] XECUTE statement generator
  - Tests: `TestXecuteCommandCodegen` → test_s8_2_26_xecute.py
- [ ] `^%ZOSF` lookup table
  - Tests: `TestZosfPatternCodegen` → test_s8_2_26_xecute.py
- [ ] **Post-implementation documentation** (see [Post-Implementation Documentation](#post-implementation-documentation) section)
  - Update codegen-plan.md: mark deliverables complete, add implementation notes
  - Update docs/codegen/runtime_requirements.md with actual runtime API
  - Add pre-requisites section to Spec 008

### Validation

- MUGJ: V1IDGOA, V1IDGOB (indirect GOTO)
- MUGJ: V1IDARG series (indirect arguments)
- MUGJ: V1XECA series (XECUTE)
- VistA: Kernel/XUINCON.m (real-world patterns)

### Spike: eval/exec Performance & Safety

**Hypothesis**: eval/exec approach is acceptable for correctness-first translation, with performance optimization deferred.

**Test**: Translate a routine with heavy indirection (pick from VistA). Measure:
1. Translation time
2. Execution time vs. YDB
3. Memory overhead of runtime context
4. Error message quality when MUMPS code fails

**Decision**: If performance is >10x slower than YDB, consider caching translated code. If error messages are poor, add source mapping.

---

## Spec 008: Core Language Completion

**Goal**: Complete the simple constructs deferred from Spec 004

Now that control flow is solid, add the rest of the straightforward language features.

### Research Phase
Review before coding:
- **Docs**: `docs/asg/expressions.md`, `docs/codegen/functions.md`, `docs/codegen/operators.md`
- **Intrinsic functions**: `asg/expressions.py` → `MFunctionCall`, intrinsic vs extrinsic
- **Global variables**: `asg/expressions.py` → `MGlobalRef`, naked ref (`^(sub)`) vs full
- **LHS functions**: Parser/ASG → `MLhsFunctionCall` for SET $P()/$E()?
- **Pattern match**: `asg/` → pattern codes (1N, .A) fully represented?
- **Computed offsets**: `asg/elements.py` → `MCall.offset`, `G LABEL+expr` structure
- **Statement line numbers**: Check if `MStatement.line_number` populated during parsing
- **ASG dump**: `uv run python utils/validate_asg.py --compact tests/functional/mugj/inref/V1FN*.m`

**Output**: List of ASG gaps needing parser/analysis work before codegen.

### Scope

1. **Extended Operators**
   - Negated comparisons: `'=`, `'<`, `'>`
   - Logical operators: `&` (AND), `!` (OR), `'` (NOT)
   - String concatenation: `_`
   - Contains: `[`, Follows: `]`, `]]`
   - Modulo: `#`, Integer division: `\`
   - Pattern match: `?` (basic patterns) — **verify parser captures pattern codes in ASG**

2. **Extended Literals & Variables**
   - Decimal numeric literals
   - Global variable syntax (`^name`, `^name(subs)`) → builds on runtime from Spec 007
   - Local variables with subscripts
   - Naked global references (requires runtime naked indicator tracking)

3. **Extended Statements**
   - SET with multiple assignments (`S X=1,Y=2`)
   - SET with subscripted targets
   - WRITE with format controls (`!`, `#`, `?n`, `*n`)
   - READ (basic, with timeout)
   - NEW (selective)
   - KILL (selective)
   - MERGE (copy array subtrees: `M dest=src`)
   - Postconditions on all commands (`S:cond X=1`)

4. **Intrinsic Functions**
   - String: $PIECE, $LENGTH, $EXTRACT, $FIND, $TRANSLATE, $JUSTIFY
   - Numeric: $RANDOM, $ASCII, $CHAR
   - Data: $GET, $DATA, $ORDER, $QUERY
   - Conditional: $SELECT (special colon syntax: `condition:value` pairs)

5. **Extrinsic Functions**
   - `$$label` and `$$label^routine` calls
   - Parameter passing (by value, by reference)

6. **Left-Hand Function Assignment** (complex semantics)
   ```mumps
   S $P(X,"^",2)="NEW"    ; Replace second ^-piece of X
   S $E(X,1,3)="ABC"      ; Replace first 3 characters
   ```
   - Modifies variable in-place
   - Creates variable if doesn't exist
   - Pads with delimiter if piece index beyond current length
   
   **⚠️ Parser/ASG extension likely needed**: Verify parser distinguishes LHS function calls from RHS. ASG may need `MSetTarget` variant for function-modified targets.

7. **Naked Global References** (runtime tracking required)
   ```mumps
   S ^A(1,2)=1    ; Sets context: ^A with subscript path (1)
   S ^(3)=2       ; Actually ^A(1,3) - replaces last subscript
   S ^(4,5)=3     ; Actually ^A(1,4,5)
   ```
   - Context = global name + all subscripts except the last
   - Must track "naked indicator" at runtime
   
   **⚠️ ASG extension likely needed**: Verify `MGlobalRef` distinguishes naked refs (`^(sub)`) from full refs (`^name(sub)`). Analysis pass may need to flag naked ref usage for runtime tracking.

8. **Computed Offsets in DO/GOTO** (deferred from Spec 006)
   
   Now that full expressions are available, implement offset targets:
   ```mumps
   G STAR+^V1A                    ; Global variable as offset
   G %0+A=2                       ; Binary comparison in offset!
   G HAL9000+^V1A(2)-ZORAC        ; Arithmetic with subscripted global
   G 388+$L($E(VCOMP,5,99))       ; Function call in offset
   D LABEL+^V1A(2)-^(3)/10        ; Naked globals in offset
   ```
   
   **Infrastructure needed** (building on existing analysis):
   
   | Component | Existing | To Build |
   |-----------|----------|----------|
   | Label line numbers | `MLabel.line_number` ✓ | — |
   | Source lines | `MRoutine.source_lines` ✓ | — |
   | Statement line numbers | — | Populate `MStatement.line_number` from textX |
   | Line-to-entry mapping | — | `Dict[int, Callable]` built at init |
   | Runtime dispatch | — | `_line_dispatch(line_num)` method |
   
   **⚠️ Parser extension needed**: Statement line numbers require enhancing textX model classes to capture source positions during parsing.
   
   **Code generation approach**: Build `_line_map: Dict[int, Callable]` at routine init. For `G LABEL+expr`, evaluate `target_line = label_line + int(expr)`, dispatch via `_line_map[target_line]`. Error if line not in map.
   
   **Non-executable lines**: Comment-only and blank lines are NOT in `_line_map`. Per MUMPS semantics, `G LABEL+n` landing on non-executable line should error (strict) or skip (lenient). Validate actual YDB behavior.

### Deliverables

- [ ] Extended expression generators
  - Tests: `TestOperatorsCodegen` → [test_s7_2_operators.py](../tests/unit/codegen/s7_expressions/test_s7_2_operators.py)
- [ ] Global variable infrastructure (tree-based, each node can have value + children)
  - Tests: `TestGlobalCodegen` → [test_globals.py](../tests/unit/cross_cutting/test_globals.py)
- [ ] Naked indicator runtime tracking
  - Tests: `TestNakedReferencesCodegen` → [test_naked_references.py](../tests/unit/cross_cutting/test_naked_references.py)
- [ ] All intrinsic function implementations
  - Tests: `TestIntrinsicFunctionsCodegen` → [test_s7_1_5_intrinsic_functions.py](../tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py)
- [ ] Left-hand $PIECE/$EXTRACT assignment
  - Tests: `TestLhsFunctionAssignmentCodegen` → [test_s8_2_18_set.py](../tests/unit/codegen/s8_commands/test_s8_2_18_set.py)
- [ ] Extended statement generators
  - Tests: Various `Test*CommandCodegen` → tests/unit/codegen/s8_commands/
- [ ] Postcondition support
  - Tests: `TestPostconditionsCodegen` → [test_postconditions.py](../tests/unit/cross_cutting/test_postconditions.py)
- [ ] Statement line number population (parser enhancement)
  - Tests: `TestLineDispatchCodegen` → [test_s8_2_06_goto.py](../tests/unit/codegen/s8_commands/test_s8_2_06_goto.py)
- [ ] Line-to-entry mapping generator
  - Tests: `TestLineDispatchCodegen.test_line_map_generation` → test_s8_2_06_goto.py
- [ ] Computed offset dispatch
  - Tests: `TestComputedOffsetCodegen` → test_s8_2_18_set.py
- [ ] **Post-implementation documentation** (see [Post-Implementation Documentation](#post-implementation-documentation) section)
  - Update codegen-plan.md: mark deliverables complete, add implementation notes
  - Update docs/codegen/functions.md with intrinsic function implementations
  - Add pre-requisites section to Spec 009

### Validation

- MUGJ: V1SET, V1WR, V1NUM, V1FN* series
- MUGJ: V1GO2.m (computed offset patterns)
- YDBTest: basic/* suite

### No Spikes Needed

All patterns understood from prior specs. Straightforward implementation.

---

## Spec 009: External Calls & Advanced Features

**Goal**: Complete coverage for production VistA translation

### Scope

1. **External Routine Calls**
   - `D LABEL^ROUTINE` → `import routine; routine.label()`
   - `G LABEL^ROUTINE` → `return routine.label()` or state transfer
   - Module loading and caching

2. **Cross-Routine Variable Passing**
   - Variables visible across routine calls (not NEWed)
   - Requires shared runtime context

3. **Exclusive NEW/KILL** (rare but required)
   - `N (A,B)` → save all except A,B
   - `K (X,Y)` → kill all except X,Y
   - Runtime scope manipulation

4. **$TEXT Function with Offsets**
   ```mumps
   S A=$T(TEX+I)           ; Get line at TEX+I offset
   S A=$T(+5)              ; Get 5th line of routine
   S A=$T(LABEL+0^ROUTINE) ; Get line from external routine
   ```
   - Returns source code lines (including comments)
   - Store `MRoutine.source_lines` in generated module
   - Offset is evaluated at runtime
   - External routine refs require module access

5. **Special Variables**
   - $HOROLOG, $JOB, $IO, $X, $Y
   - $QUIT (per ANSI 7.1.4.10): Returns 1 if current frame was invoked by exfunc/exvar, 0 otherwise
   - Some static, some require runtime tracking

### Deliverables

- [ ] Cross-routine call infrastructure
  - Tests: `TestExternalRoutineCallsCodegen` → [test_s7_1_6_extrinsic_functions.py](../tests/unit/codegen/s7_expressions/test_s7_1_6_extrinsic_functions.py)
- [ ] Shared runtime context for variable passing
  - Tests: `TestExternalRoutineCallsCodegen.test_cross_routine_variable_visibility` → test_s7_1_6_extrinsic_functions.py
- [ ] Exclusive NEW/KILL implementation
  - Tests: `TestNewCommandCodegen.test_exclusive_new` → [test_s8_2_12_new.py](../tests/unit/codegen/s8_commands/test_s8_2_12_new.py)
  - Tests: `TestKillCommandCodegen.test_exclusive_kill` → [test_s8_2_10_kill.py](../tests/unit/codegen/s8_commands/test_s8_2_10_kill.py)
- [ ] $TEXT support
  - Tests: `TestTextWithOffsetsCodegen` → [test_s7_1_7_special_variables.py](../tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py)
- [ ] Special variable implementations
  - Tests: `TestSpecialVariablesCodegen`, `TestQuitSpecialVariableCodegen` → test_s7_1_7_special_variables.py
- [ ] **Post-implementation documentation** (see [Post-Implementation Documentation](#post-implementation-documentation) section)
  - Update codegen-plan.md: mark deliverables complete, add implementation notes
  - Update docs/ with complete API documentation for production use
  - Final review of all codegen docs for accuracy

### Validation

- VistA routines with cross-routine calls
- MUGJ: V1NX series (NEW exclusive)
- Full VistA Kernel package translation attempt

### No Spikes Needed

Patterns are understood, just require careful implementation of runtime infrastructure from Spec 007.

---

## Test Infrastructure (Cross-Cutting)

Tests live in `tests/unit/codegen/` using embedded strings (no file I/O).

### Fixtures (from `conftest.py`)

| Fixture | Use Case |
|---------|----------|
| `execute_mumps(source)` | Full routine execution |
| `execute_expr(code)` | Single command (auto-wrapped in label) |
| `eval_mumps(expr)` | Expression value (no WRITE needed) |
| `generate_python(source)` | Inspect generated code structure |

```python
def test_addition(execute_expr):
    assert execute_expr('W 1+2') == "3"

@pytest.mark.parametrize("expr,expected", [("1+2", "3"), ("$L(\"ABC\")", "3")])
def test_expressions(execute_expr, expr, expected):
    assert execute_expr(f'W {expr}') == expected
```

### Guidelines

- **Generate expected outputs at phase start** using YDB, not upfront
- **Audit stubs before implementing** - prefer extending existing test classes
- **Coverage goal**: Maintain ≥85% overall (`uv run python utils/coverage_check.py`)

### Validation Progression

| Spec | Test Approach |
|------|---------------|
| 004-006 | Embedded pytest |
| 007-008 | MUGJ files (V1ID*, V1XEC*, V1GO2) |
| 009 | Full MUGJ + VistA Kernel |

---

## Risk Register

| Risk | L/I | Mitigation |
|------|-----|------------|
| Cross-label GOTO strategy fails | M/H | Spike bake-off before committing |
| Variable visibility across labels | M/H | State class or match-case; analysis provides input/output vars |
| Computed offsets need line-indexed model | H/M | `MLabel.line_number` exists; build statement map in 008 |
| eval/exec too slow | L/M | Cache translated code |
| Indirection patterns complex | M/M | Start with static cases |
| VistA patterns not in MUGJ | M/H | Validate against real VistA early |
| By-ref handling awkward | M/M | Return-value pattern; `byref_outputs` tracks modified params |
| Duplicate test stubs | M/L | Audit stubs vs existing classes before each spec |

---

## Reference Documents

- [docs/codegen/variable_scoping.md](../docs/codegen/variable_scoping.md) - Variable scoping strategies
- [docs/codegen/mumps_gotchas.md](../docs/codegen/mumps_gotchas.md) - MUMPS semantics and edge cases
- [tests/functional/mugj/inref/V1GO2.m](../tests/functional/mugj/inref/V1GO2.m) - Computed offset test patterns
- [src/m2py/analysis/variables.py](../src/m2py/analysis/variables.py) - Variable analysis implementation
