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
| Local variables (SIMPLE_FUNCTIONS) | `_scope['X'] = value` (shared dict for cross-routine visibility) |
| Local variables (TRAMPOLINE) | `state.X = value` (RoutineState dataclass for cross-label visibility) |
| Parameters | `def LABEL(_rt, _scope=None, A=None, B=None, **_kwargs):` |
| By-ref outputs | Return from `_scope`: `return _scope.get('N', '')` |
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

**Gap for codegen** (to be built in Spec 007):
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
| **007** | Computed Offsets & Line Dispatch | **Highest** | Parser extension for line numbers |
| **008** | External Calls & Cross-Routine | **High** | Module loading, variable passing |
| **009** | LHS Functions & Global Variables | Medium | Parser extension, MArray runtime |
| **010** | Intrinsic Functions | Low | Large volume, well-defined semantics |
| **011** | Operators, Commands & Completion | Low | Mechanical translation |
| **012** | Indirection & XECUTE | **High** | Runtime infrastructure, eval/exec |
| **013** | Label Fall-Through Support | Medium | SIMPLE_FUNCTIONS limitation, MUGJ compatibility |

**Complexity-First Rationale**: Specs 007-008 tackle the highest-risk architectural work (parser extensions, module loading) while the codebase is small. Spec 012 (Indirection/XECUTE) is last because `runtime.execute()` can run any MUMPS code, so all static constructs must be implemented first.

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

### Explicitly Deferred (Later Specs)

**Spec 007** (Computed Offsets):
- **DO/GOTO with offsets** (`G LABEL+5`, `D SUB+N`)
- **Complex FOR parameters** (`F I=$D(I):1:^MAX`)

**Spec 008** (External Calls):
- External routine calls (`D LABEL^ROUTINE`, `G LABEL^ROUTINE`)
- $TEXT function

**Spec 009** (LHS Functions & Globals):
- Global variables (^name)
- Subscripted variables

**Spec 010** (Intrinsic Functions):
- Intrinsic functions ($PIECE, $LENGTH, $GET, etc.)
- Extrinsic functions ($$func)

**Spec 011** (Operators, Commands & Completion):
- READ command
- NEW / KILL commands
- Logical operators (&, !)
- String concatenation (_)
- Pattern match (?)
- Negated comparisons ('=, '<, '>)
- Multiple assignments (S X=1,Y=2)
- Format controls (!, #, ?n)
- Postconditions (S:cond X=1)

**Spec 012** (Indirection & XECUTE):
- Indirection (@VAR)
- XECUTE command
- `^%ZOSF` patterns

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
- **Spec 008**: Routine names (used as Python module names)

### Deliverables

- [ ] `src/m2py/codegen/` module structure
- [ ] **M value model**: `m_num()`, `m_truth()`, `m_compare()` coercion helpers
  - Tests: `TestNumericCoercionCodegen`, `TestTruthValueCodegen`, `TestComparisonCodegen` in [test_s7_1_1_values.py](../tests/unit/codegen/s7_expressions/test_s7_1_1_values.py)
- [ ] **Case-preserving, injective name translator** (handle %, numeric, reserved words for labels and variables)
  - Tests: `TestNameTranslationCodegen` in [test_s6_1_routine_head.py](../tests/unit/codegen/s6_routine/test_s6_1_routine_head.py)
- [ ] Expression generator (numeric, string, variable, comparison, arithmetic)
  - Tests: `TestValuesCodegen`, `TestLiteralsCodegen`, `TestOperatorsCodegen` in [s7_expressions/](../tests/unit/codegen/s7_expressions/)
- [ ] Statement generators (SET, WRITE, QUIT, DO, IF, ELSE, FOR, GOTO)
  - Tests: `TestSetCommandCodegen`, `TestWriteCommandCodegen`, `TestQuitCommandCodegen`, `TestDoCommandCodegen`, `TestIfCommandCodegen`, `TestElseCommandCodegen`, `TestForCommandCodegen`, `TestGotoCommandCodegen` in [s8_commands/](../tests/unit/codegen/s8_commands/)
- [ ] Routine → Python module translation (single routine, labels as structure)
  - Tests: `TestRoutineHeadCodegen`, `TestRoutineBodyCodegen` in [s6_routine/](../tests/unit/codegen/s6_routine/)
- [ ] `MUMPSRuntime` class with `_test` tracking for IF/ELSE
  - Tests: `TestTestVariableCodegen` in [test_language_semantics.py](../tests/unit/cross_cutting/test_language_semantics.py)

### Implementation Notes

**Local Variables → Strategy-Dependent Storage** (Phase 13):

Variable storage depends on the codegen strategy selected for the routine:

| Strategy | Variable Storage | Variable Read | Cross-Boundary Visibility |
|----------|-----------------|---------------|---------------------------|
| SIMPLE_FUNCTIONS | `_scope['X'] = value` | `_scope.get('X', '')` | Via shared `_scope` dict |
| TRAMPOLINE | `state.X = value` | `state.X` | Via RoutineState dataclass |

**SIMPLE_FUNCTIONS pattern** (most common):
- `S X=5` → `_scope['X'] = 5`
- `W X` → `_rt.write(_scope.get('X', ''))`
- Function signature: `def LABEL(_rt, _scope=None, **_kwargs):`
- Entry point: `if __name__ == "__main__": _rt = MUMPSRuntime(); _scope = {}; LABEL(_rt, _scope)`
- Cross-routine visibility automatic via shared `_scope` dictionary

**TRAMPOLINE pattern** (for `needs_trampoline=True` routines):
- Uses `RoutineState` dataclass for cross-label variable visibility
- `S X=5` → `state.X = 5`
- `W X` → `_rt.write(state.X)`

**Runtime reserved for**:
- Global variables (`^name`) - deferred to Spec 009
- `$TEST` special variable - accessed via `_rt._test`
- Output accumulation (`_rt.write()`) - for test harness capture

**Why `_scope` instead of Python locals**: MUMPS variables are visible across routine boundaries by default. Using `_scope['X']` enables:
1. Caller's variables visible to callee without explicit passing
2. Callee modifications visible to caller after return
3. NEW command can save/restore entries (future Spec 011)

**Scope strategy check**: Verify `FunctionSignature.scope_strategy` to select appropriate pattern. If `REQUIRES_RUNTIME`, use runtime scope access.

### Test Strategy: Embedded Unit Tests

**Do NOT use `.m` files or YDB/MUGJ tests** - they require I/O overhead and additional syntax.

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
   - **Note**: Postconditions (deferred to Spec 011) do NOT update $TEST - document this behavior now
   
2. **$TEST Stack Semantics**
   - **Argumentless DO**: `$TEST` is stacked (NEW $TEST), restored on QUIT
   - **Extrinsic calls** (`$$label`): `$TEST` is stacked, restored on QUIT  
   - **DO with arguments**: `$TEST` NOT stacked - callee mutations visible to caller
   - **XECUTE**: `$TEST` NOT stacked - mutations visible to caller
   
   This is critical for ELSE chains that span DO calls.

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

- [ ] $TEST tracking infrastructure with stack/restore for argumentless DO and extrinsics
  - Tests: `TestTestStackSemanticsCodegen` → [test_language_semantics.py](../tests/unit/cross_cutting/test_language_semantics.py)
- [ ] $TEST NOT stacked for DO with arguments (explicit test)
  - Tests: `test_do_with_arguments_mutates_test` → TestTestStackSemanticsCodegen
- [ ] Postconditions do NOT update $TEST (explicit test)
  - Tests: `TestPostconditionsCodegen` → [test_postconditions.py](../tests/unit/cross_cutting/test_postconditions.py)
- [ ] FOR loop strategy selector based on analysis flags
  - Tests: `TestForLoopCodegen` → [test_s8_2_05_for.py](../tests/unit/codegen/s8_commands/test_s8_2_05_for.py)
- [ ] Intra-label GOTO restructuring
  - Tests: `TestIntraLabelGotoCodegen` → [test_s8_2_06_goto.py](../tests/unit/codegen/s8_commands/test_s8_2_06_goto.py)
- [ ] Loop exit translation (break, exception)
  - Tests: `TestForLoopCodegen.test_quit_in_for_loop_*` → test_s8_2_05_for.py
- [ ] QUIT context-aware code generation
  - Tests: `TestQuitCommandCodegen` → [test_s8_2_16_quit.py](../tests/unit/codegen/s8_commands/test_s8_2_16_quit.py)
- [ ] Scope strategy code generation (PURE_FUNCTION, SUBROUTINE, etc.)
  - Tests: `TestScopeStrategyCodegen` → [test_s8_2_03_do.py](../tests/unit/codegen/s8_commands/test_s8_2_03_do.py)
- [ ] By-reference parameter return value pattern
  - Tests: `TestByRefParameterCodegen` → test_s8_2_03_do.py

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
   
   Build the dispatch architecture here (even with literal offsets only) to avoid architectural fork with computed offsets in Spec 007:
   - Build `_line_map` keyed by **source line number** (not statement index)
   - Emit per-line entry points
   - Cross-label GOTO uses same dispatch mechanism (jump to label's line number)
   - GOTO targets must be at same execution LEVEL (per ANSI 8.2.6, error M45 if violated)
   
   This prepares for computed offsets (`G LABEL+expr`) without major refactoring.

### DEFERRED: Computed Offsets (Spec 007) & External Calls (Spec 008)

Computed offsets like `G LABEL+expr` are deferred because they require full expression evaluation:

```mumps
G STAR+^V1A                    ; Needs global variable evaluation (Spec 009)
G NOTES+C+(D*2)+E=29.3+3       ; Needs all arithmetic operators (Spec 011)
G 388+$L($E(VCOMP,5,99))       ; Needs intrinsic function evaluation (Spec 010)
```

**Why deferred:**
- Offset expressions can include globals, functions, all operators
- Current analysis doesn't account for where offsets land (may cross label boundaries)
- Requires line-indexed execution model (jump to line N, not label)

**Spec 006 handles**: Simple label targets only (`G LABEL`, `G LABEL^ROUTINE` same-routine pattern)
**Spec 007 adds**: Offset targets (`G LABEL+n`, `G LABEL+expr`) with line dispatch
**Spec 008 adds**: Cross-routine external calls (module loading, `G LABEL^OTHER_ROUTINE`)

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

## Spec 007: Computed Offsets & Line Dispatch (Highest Risk)

**Goal**: Tackle the hardest architectural problem first — parser enhancement for line numbers and line-indexed execution

This is the highest-risk feature because it requires **parser/ASG extension** before codegen can proceed. Discovering issues here early prevents costly rework.

### Research Phase
Review before coding:
- **Docs**: `docs/codegen/goto_handling.md`, `docs/asg/statements.md` (computed offsets)
- **Offset ASG**: `asg/elements.py` → `MCall.offset` (full `MExpr` structure)
- **Line numbers**: `MLabel.line_number`, `MStatement.line_number` — is latter populated?
- **Source lines**: `MRoutine.source_lines` for $TEXT support
- **textX positions**: How to capture source positions during parsing?
- **ASG dump**: `uv run python utils/validate_asg.py --compact tests/functional/mugj/inref/V1GO2.m`
- **ASG dump**: `uv run python utils/validate_asg.py --compact tests/functional/mvts_inref/V1GO3.m`

**Output**: Line dispatch architecture, statement line number population strategy.

### Scope

1. **Statement Line Number Population** (parser enhancement) ⚠️ **HIGHEST RISK**
   
   Enhance textX model classes to capture source positions during parsing:
   - Add `line_number` attribute to `MStatement`
   - Populate during textX post-processing
   - Measure performance impact
   
   **Decision point**: If overhead >10%, consider separate line numbering pass.

2. **Line-to-Entry Mapping Generator**
   
   Build `_line_map: Dict[int, Callable]` at routine init:
   ```python
   _line_map = {
       1: self._line_1,   # Label A
       3: self._line_3,   # First statement after A
       5: self._line_5,   # Label B
       ...
   }
   ```
   
   **Non-executable lines**: Comment-only and blank lines are NOT in `_line_map`. Per MUMPS semantics, `G LABEL+n` landing on non-executable line should error.

3. **Computed Offset Dispatch**
   
   For `G LABEL+expr`, evaluate `target_line = label_line + int(expr)`, dispatch via `_line_map[target_line]`:
   ```mumps
   G STAR+^V1A                    ; Global variable as offset
   G %0+A=2                       ; Binary comparison in offset!
   G HAL9000+^V1A(2)-ZORAC        ; Arithmetic with subscripted global
   G 388+$L($E(VCOMP,5,99))       ; Function call in offset
   D LABEL+^V1A(2)-^(3)/10        ; Naked globals in offset
   ```

4. **Minimal Expression Evaluator for Offsets**
   
   Phase 1 evaluator handles subset needed for literal offsets:
   ```python
   def _evaluate_offset(self, expr: MExpr) -> int:
       """Evaluate offset expression - minimal version for Spec 007."""
       match expr:
           case MNumericLiteral(value): return int(value)
           case MVariableRef(name): return int(self._get_var(name))
           case MBinaryOp("+", left, right): 
               return self._evaluate_offset(left) + self._evaluate_offset(right)
           case _:
               raise NotImplementedError(f"Complex offset {type(expr)} - Spec 009")
   ```
   
   Full expression support (globals, functions) added in Spec 009 after those are implemented.

### Infrastructure Needed

| Component | Existing | To Build |
|-----------|----------|----------|
| Label line numbers | `MLabel.line_number` ✓ | — |
| Source lines | `MRoutine.source_lines` ✓ | — |
| Statement line numbers | `MStatement.line_number` ✓ | Populated from textX ✓ |
| Line-to-entry mapping | `_line_map` ✓ | `Dict[int, Tuple[str, int]]` ✓ |
| Runtime dispatch | Trampoline ✓ | Handles `int` targets via `_line_map` ✓ |

### Deliverables ✅ COMPLETE

- [X] Statement line number population (parser already populates via `_set_line_number_recursive()`)
  - Tests: Line numbers verified in codegen tests
- [X] Line-to-entry mapping generator (`generate_line_map()` in `line_dispatch.py`)
  - Tests: `TestLineMapGeneration` → [test_line_dispatch.py](../tests/unit/codegen/test_line_dispatch.py)
- [X] Computed offset dispatch (literal, variable, arithmetic offsets)
  - Tests: `TestLineDispatchCodegen` → [test_s8_2_06_goto.py](../tests/unit/codegen/s8_commands/test_s8_2_06_goto.py)
- [X] Offset expression evaluation via `generate_expr()` + `int()` wrapper
  - Tests: Arithmetic, float truncation, variable offsets all covered
- [X] Non-executable line handling (comments/blanks skip to next executable)
  - Tests: `test_offset_landing_on_comment_continues`, `test_offset_landing_on_blank_continues`
- [X] Invalid offset error handling ("Entry point LABEL+N not valid")
  - Tests: `test_invalid_offset_raises_error`, `test_variable_offset_past_end_raises_error`
- [X] **Post-implementation documentation**
  - Updated docs/codegen/goto_handling.md with computed offset architecture
  - Added pre-requisites section referencing Spec 007 infrastructure

**Implementation Notes (Spec 007)**:
- Parser already populated statement line numbers - no changes needed
- Line map is `Dict[int, Tuple[str, int]]` mapping line → (label_name, offset_within_label)
- Offset dispatch uses trampoline pattern: `return (label_line + int(offset), state)`
- Label functions accept `_start_offset=0` parameter with `if _start_offset <= N:` guards
- Non-integer offsets truncated via `int()` (matches MUMPS truncation-toward-zero)
- Comment/blank lines not in `_line_map`; offset landing on them finds next executable

### Validation

- MUGJ: V1GO2.m (computed offset patterns - literal offsets)
- Embedded pytest tests with computed offsets

### Spike: Parser Line Number Performance

**Hypothesis**: Statement line numbers can be populated during textX parsing without significant performance cost.

**Test**: Enhance textX model to capture line numbers. Measure:
1. Parsing time increase for V1GO2.m
2. ASG size increase  
3. Memory overhead

**Decision**: If overhead <10%, implement during parsing. Otherwise, add separate line numbering pass.

---

## Spec 008: External Calls & Cross-Routine Infrastructure ✅ COMPLETE

**Goal**: Tackle cross-routine coordination and module loading — architecturally significant for VistA

**Status**: All user stories implemented and tested. External DO, GOTO, extrinsics, and $TEXT function are fully operational.

External routine calls affect codegen design significantly. Getting this right early prevents late rework.

### Pre-requisites from Spec 007

- Statement line numbers populated (for $TEXT with offsets)
- Line dispatch infrastructure (for cross-routine GOTO)

### Research Phase
Review before coding:
- **Docs**: `docs/codegen/runtime_requirements.md`, `docs/asg/elements.py` (routine references)
- **Routine refs**: `asg/elements.py` → `MCall.routine_name`, external ref detection
- **Module loading**: Python import semantics, `importlib.import_module()`
- **Variable visibility**: Which variables cross routine boundaries?
- **ASG dump**: `uv run python utils/validate_asg.py --compact VistA-M/Packages/Kernel/*.m | head -100`

**Output**: Module loading pattern, shared runtime context design.

### Scope ✅ COMPLETE

1. **External Routine Calls** ✅
   - `D LABEL^ROUTINE` → `import routine; routine.label(_scope=_scope)`
   - `G LABEL^ROUTINE` → `raise GotoExternal(routine, "label")`
   - Standard Python `import` statements (no importlib)
   - Python's `sys.modules` provides automatic caching

2. **Routine Discovery & Loading** ✅
   
   Uses standard Python import mechanism. No custom module loading needed:
   ```python
   # Generated code:
   import ext2
   ext2.HELPER(_scope=_scope)
   ```
   
   Search paths configured via `sys.path` or `PYTHONPATH` environment variable.

3. **Cross-Routine Variable Passing** ✅
   - `_scope` dictionary passed to all external calls
   - Variables visible across routine calls (not NEWed)
   - Initialized at entry point: `_scope = _scope if _scope is not None else {}`

4. **$TEXT Function with Offsets** ✅
   ```mumps
   S A=$T(+1)             ; Get 1st line of current routine
   S A=$T(+0)             ; Get routine name
   S A=$T(LABEL+N)        ; Get line at label + offset
   S A=$T(+N^ROUTINE)     ; Get line from external routine
   S A=$T(LABEL^ROUTINE)  ; Get label line from external routine
   ```
   - Each module embeds `_source_lines`, `_routine_name`, `_label_lines`
   - External $TEXT imports module and accesses its constants

### Deliverables ✅ COMPLETE

- [X] Cross-routine call infrastructure (`D LABEL^ROUTINE`, `D ^ROUTINE`)
  - Codegen: `src/m2py/codegen/statements.py` `_generate_do()` handles external patterns
  - Tests: `tests/integration/test_external_calls.py`
- [X] Module loading via standard Python `import` (no custom caching)
  - Python's `sys.modules` provides automatic caching
  - Tests verify import happens once per module
- [X] Shared scope via `_scope` dictionary parameter
  - Codegen: All external calls pass `_scope=_scope`
  - Tests: Cross-routine variable visibility verified
- [X] $TEXT function implementation (current and external routines)
  - Codegen: `src/m2py/codegen/expressions.py` `_generate_text()` 
  - Tests: All offset patterns tested
- [X] External GOTO with `GotoExternal` exception
  - Runtime: `src/m2py/runtime/__init__.py` provides exception class and `run_with_goto_support()`
  - Codegen: `src/m2py/codegen/statements.py` `_generate_external_goto()`
- [X] External extrinsic functions with $TEST isolation
  - Codegen: `src/m2py/codegen/expressions.py` `_generate_extrinsic()`
- [X] **Post-implementation documentation**
  - Updated docs/codegen/statements.md with external call patterns
  - Updated docs/codegen/expressions.md with $TEXT patterns

**Implementation Notes (Spec 008)**:
- Standard Python `import` statements eliminate need for importlib or custom loaders
- Function signature: `def LABEL(_rt, _scope=None, **_kwargs):` - `_rt` is first parameter
- Entry point: `if __name__ == "__main__": _rt = MUMPSRuntime(); _scope = {}; LABEL(_rt, _scope)`
- Variable storage: `_scope['varname']` for SIMPLE_FUNCTIONS strategy (Phase 13)
- Variable reads: `_scope.get('varname', '')` for undefined safety (Phase 13)
- Formal params copied to `_scope` at function entry: `_scope['N'] = N`
- External calls: `routine.LABEL(_rt, _scope=_scope)` - both `_rt` and `_scope` passed
- External GOTO raises `GotoExternal(module, label, offset=N, _rt=_rt)` caught by caller's trampoline
- Each generated module embeds: `_source_lines`, `_routine_name`, `_label_lines`
- Deferred to Spec 011: NEW semantics verification across routine boundaries (requires NEW command)

### Validation ✅ COMPLETE

- Integration tests: `tests/integration/test_external_calls.py` (29 tests)
- Covers: External DO, GOTO, extrinsics, $TEXT, module caching, error handling
- Circular routine calls verified to work correctly
- VistA compatibility: Cross-routine patterns used in production codebases

---

## Spec 009: LHS Functions & Global Variables (Parser + Runtime)

**Goal**: Complete parser extensions and core runtime infrastructure

LHS functions have unusual semantics requiring parser changes. Globals need the MArray runtime.

### Pre-requisites from Spec 007/008 ✅ Available

**From Spec 007:**
- Line dispatch infrastructure (`_line_map`) for computed offset validation tests
- Statement line numbers populated by parser

**From Spec 008 (Phase 13):**
- Module loading via standard Python `import` statements
- `_scope` dictionary pattern for cross-routine variable visibility
- Variable storage: `_scope['varname'] = value` (SIMPLE_FUNCTIONS strategy)
- Variable reads: `_scope.get('varname', '')` for undefined safety
- `_source_lines`, `_label_lines` module constants pattern
- External call codegen patterns in `statements.py` and `expressions.py`
- Function signatures: `def LABEL(_rt, _scope=None, **_kwargs):`

**Important note for Spec 009**: Cross-routine variable visibility uses `_scope` dictionary. When implementing subscripted local variables (MArray), arrays accessed across routines must be stored in `_scope`. The existing `RoutineState` pattern (for TRAMPOLINE strategy) uses `MArray` fields for cross-label visibility.

### Research Phase
Review before coding:
- **Docs**: `docs/asg/expressions.md` (global variables), `docs/codegen/runtime_requirements.md`
- **LHS functions**: Parser/ASG → does `MLhsFunctionCall` exist? Need `MSetTarget` variant?
- **Global ASG**: `asg/expressions.py` → `MGlobalRef`, naked vs full refs
- **MArray semantics**: Each node can have value + children (unlike Python dicts)
- **ASG dump**: `uv run python utils/validate_asg.py --compact -c "TEST S ^A(1,2)=1 S ^(3)=2 Q"`

**Output**: LHS function ASG design, MArray implementation plan.

### Scope

1. **Left-Hand Function Assignment** (parser extension)
   ```mumps
   S $P(X,"^",2)="NEW"    ; Replace second ^-piece of X
   S $E(X,1,3)="ABC"      ; Replace first 3 characters
   ```
   - Modifies variable in-place
   - Creates variable if doesn't exist
   - Pads with delimiter if piece index beyond current length
   
   **⚠️ Parser/ASG extension needed**: Verify parser distinguishes LHS function calls from RHS. ASG may need `MSetTarget` variant for function-modified targets.

2. **MArray Class** (core runtime)
   ```python
   class MArray:
       """MUMPS array node - can have value AND children."""
       value: Any = None  # Node's own value
       children: dict[str, MArray] = {}  # Sub-nodes
   ```
   - Differentiates MUMPS semantics from Python dicts
   - Used for both local subscripted vars and globals

3. **Global Variable Infrastructure**
   - Basic syntax: `^name`, `^name(sub1,sub2,...)`
   - Tree structure where each node can have **both** value and children
   - SET to global: `S ^A=1`, `S ^A(1)=2`
   - READ from global: `W ^A`, `W ^A(1)`

4. **Pluggable Global Storage Backend**
   
   Globals require a pluggable storage system to support different use cases:
   
   **Abstract Interface** (`GlobalStorageBackend`):
   ```python
   class GlobalStorageBackend(Protocol):
       """Abstract interface for global variable storage."""
       
       def get(self, name: str, *subscripts: str) -> str | None:
           """Get value at global node. Returns None if undefined."""
           ...
       
       def set(self, value: str, name: str, *subscripts: str) -> None:
           """Set value at global node."""
           ...
       
       def kill(self, name: str, *subscripts: str) -> None:
           """Delete global node and all descendants."""
           ...
       
       def is_defined(self, name: str, *subscripts: str) -> int:
           """Return $DATA value: 0=none, 1=value, 10=descendants, 11=both."""
           ...
       
       def order(self, name: str, *subscripts: str, reverse: bool = False) -> str:
           """Return next/previous subscript at level (for $ORDER)."""
           ...
       
       def query(self, name: str, *subscripts: str) -> tuple[str, ...] | None:
           """Return full subscript path of next node with value (for $QUERY)."""
           ...
   ```
   
   **Implementations**:
   
   a. **InMemoryGlobalStorage** (default for sandbox/tests)
      - Uses `MArray` tree structure internally
      - Fast, no external dependencies
      - Perfect for unit tests, functional tests, sandbox mode
      - Data does not persist between runs
      ```python
      storage = InMemoryGlobalStorage()
      runtime = MUMPSRuntime(global_storage=storage)
      ```
   
   b. **YottaDBGlobalStorage** (production M database)
      - Uses YottaDB Python wrapper (`yottadb` package)
      - Full MUMPS semantics, ACID transactions
      - Requires YottaDB installation
      - Reference: https://docs.yottadb.com/MultiLangProgGuide/pythonprogram.html
      ```python
      # Key YottaDB API mapping:
      # yottadb.get(varname, subscripts...) → get value
      # yottadb.set(value, varname, subscripts...) → set value
      # yottadb.delete_tree(varname, subscripts...) → KILL
      # yottadb.data(varname, subscripts...) → $DATA
      # yottadb.subscript_next(varname, subscripts...) → $ORDER
      # yottadb.node_next(varname, subscripts...) → $QUERY
      
      storage = YottaDBGlobalStorage()
      runtime = MUMPSRuntime(global_storage=storage)
      ```
   
   c. **IRISGlobalStorage** (InterSystems IRIS/Caché)
      - Uses InterSystems Native SDK for Python (`iris` package)
      - Full MUMPS semantics, supports IRIS and Caché
      - Requires IRIS installation and network connection
      - Reference: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=BPYNAT_refapi
      ```python
      # Key IRIS API mapping:
      # irispy.get(globalName, *subscripts) → get value
      # irispy.set(value, globalName, *subscripts) → set value
      # irispy.kill(globalName, *subscripts) → KILL
      # irispy.isDefined(globalName, *subscripts) → $DATA
      # irispy.nextSubscript(reversed, globalName, *subscripts) → $ORDER
      # IRISGlobalNode.node() for iteration → $QUERY
      
      import iris
      conn = iris.connect(hostname='127.0.0.1', port=1972, namespace='USER', ...)
      irispy = iris.createIRIS(conn)
      storage = IRISGlobalStorage(irispy)
      runtime = MUMPSRuntime(global_storage=storage)
      ```
   
   **Configuration**:
   - Environment variable: `M2PY_GLOBAL_BACKEND=inmemory|yottadb|iris`
   - Or programmatic: `MUMPSRuntime(global_storage=backend_instance)`
   - Tests default to `InMemoryGlobalStorage` for speed and isolation
   - Functional tests can optionally run against real databases via pytest fixtures

5. **Subscripted Local Variables**
   - Basic syntax: `X(sub1,sub2,...)`
   - SET: `S X(1)=1`, `S X(1,2)="value"`
   - READ: `W X(1)`, `W X(1,2)`
   - Uses MArray, same as globals

6. **Naked Global References** (runtime tracking)
   ```mumps
   S ^A(1,2)=1    ; Sets context: ^A with subscript path (1)
   S ^(3)=2       ; Actually ^A(1,3) - replaces last subscript
   S ^(4,5)=3     ; Actually ^A(1,4,5)
   ```
   
   Runtime tracking:
   ```python
   class MUMPSRuntime:
       naked_global: str | None = None  # Last global name
       naked_subscripts: tuple = ()      # All but last subscript
   ```

### Deliverables

- [ ] LHS function parser/ASG extension
  - Tests: `TestLhsFunctionParsingParser` → [test_parser.py](../tests/unit/parser/test_parser.py)
- [ ] LHS $PIECE assignment codegen
  - Tests: `TestLhsPieceCodegen` → [test_s8_2_18_set.py](../tests/unit/codegen/s8_commands/test_s8_2_18_set.py)
- [ ] LHS $EXTRACT assignment codegen
  - Tests: `TestLhsExtractCodegen` → test_s8_2_18_set.py
- [ ] MArray class (value + children at each node)
  - Tests: `TestMArrayCodegen` → [test_globals.py](../tests/unit/cross_cutting/test_globals.py)
- [ ] `GlobalStorageBackend` protocol (abstract interface)
  - Tests: `TestGlobalStorageProtocol` → test_globals.py
- [ ] `InMemoryGlobalStorage` implementation (using MArray)
  - Tests: `TestInMemoryGlobalStorage` → test_globals.py
  - Default for unit tests and sandbox mode
- [ ] `YottaDBGlobalStorage` implementation (optional, requires yottadb package)
  - Tests: `TestYottaDBGlobalStorage` → test_globals.py (marked pytest.importorskip)
  - Reference: YDBDoc/MultiLangProgGuide/pythonprogram.rst
- [ ] `IRISGlobalStorage` implementation (optional, requires iris package)
  - Tests: `TestIRISGlobalStorage` → test_globals.py (marked pytest.importorskip)
  - Reference: https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=BPYNAT_refapi
- [ ] Backend configuration (env var + programmatic)
  - `M2PY_GLOBAL_BACKEND` environment variable
  - `MUMPSRuntime(global_storage=...)` constructor parameter
- [ ] Global variable SET/READ generation
  - Tests: `TestGlobalSetCodegen`, `TestGlobalReadCodegen` → test_globals.py
- [ ] Subscripted local variables (using MArray)
  - Tests: `TestSubscriptedVariablesCodegen` → [test_s7_1_2_variables.py](../tests/unit/codegen/s7_expressions/test_s7_1_2_variables.py)
- [ ] Naked indicator runtime tracking
  - Tests: `TestNakedReferencesCodegen` → [test_naked_references.py](../tests/unit/cross_cutting/test_naked_references.py)
- [ ] **Upgrade offset evaluator** to handle globals
  - Tests: `TestComputedOffsetWithGlobalsCodegen` → test_s8_2_06_goto.py
- [ ] **Post-implementation documentation**
  - Update codegen-plan.md: mark deliverables complete, add implementation notes
  - Update docs/codegen/runtime_requirements.md with MArray design
  - Add pre-requisites section to Spec 010

### Validation

- MUGJ: V1SET (LHS function tests)
- MUGJ: V1BOA (basic global operations)
- MUGJ: V1NKD (naked reference patterns)
- MUGJ: V1GO3.m (computed offsets with globals - now with full support)
- YDBTest: global/* suite

**Backend-specific validation**:
- Unit tests: Run with `InMemoryGlobalStorage` (default, fast, isolated)
- Integration tests: Optionally run with real databases via pytest fixtures:
  ```bash
  # Test with YottaDB (requires Docker or local installation)
  M2PY_GLOBAL_BACKEND=yottadb uv run pytest tests/integration/globals/
  
  # Test with IRIS (requires connection details)
  M2PY_GLOBAL_BACKEND=iris M2PY_IRIS_HOST=localhost M2PY_IRIS_PORT=1972 uv run pytest tests/integration/globals/
  ```
- Functional tests should verify behavior is identical across all backends

### Spike: LHS Function Detection

**Hypothesis**: Parser already distinguishes LHS/RHS context, just needs codegen support.

**Test**: Dump ASG for `S $P(X,"^",2)="NEW"` and compare with `W $P(X,"^",2)`. Measure:
1. Does ASG distinguish the two contexts?
2. If not, is the change to parser simple or complex?

**Decision**: If parser change needed, do it first. If codegen-only, proceed directly.

---

## Spec 010: Intrinsic Functions (Large but Straightforward)

**Goal**: Implement all MUMPS intrinsic functions — large volume, well-defined semantics

Now that globals and MArray are available, implement all intrinsic functions.

### Pre-requisites from Spec 009

- MArray class (for data functions)
- Global variable infrastructure (for $DATA, $ORDER, $QUERY)

### Research Phase
Review before coding:
- **Docs**: `docs/codegen/functions.md`, `docs/asg/expressions.md` (intrinsic functions section)
- **Function ASG**: `asg/expressions.py` → `MIntrinsicFunction`, argument list
- **MUMPS spec**: Functions are in ANSI §7.1.5 - https://71.174.62.16/Demo/AnnoStd
- **ASG dump**: `uv run python utils/validate_asg.py --compact tests/functional/mugj/inref/V1FN*.m`

**Output**: List of functions with implementation priority, edge case documentation.

### Scope

1. **String Functions**
   - $PIECE(string, delimiter, piece#) - extract delimited piece
   - $LENGTH(string [, delimiter]) - length or piece count
   - $EXTRACT(string, start [, end]) - substring extraction
   - $FIND(string, substring [, start]) - search position
   - $TRANSLATE(string, from, to) - character translation
   - $JUSTIFY(string, width [, decimals]) - formatting
   - $CHAR(code, ...) - ASCII codes to string
   - $ASCII(string [, position]) - string to ASCII code
   - $REVERSE(string) - reverse string order
   - $FNUMBER(number, codes [, decimals]) - formatted numeric output

2. **Numeric Functions**
   - $RANDOM(limit) - random integer 0 to limit-1

3. **Data Functions** (require Spec 009 globals)
   - $DATA(variable) - existence test (0=none, 1=value, 10=children, 11=both)
   - $GET(variable [, default]) - safe read with default
   - $ORDER(global(subscripts)) - next subscript in tree
   - $QUERY(global) - next node in tree walk

4. **Array Utility Functions**
   - $NAME(variable [, depth]) - return name with subscripts as string
   - $QLENGTH(name) - count subscripts in name string
   - $QSUBSCRIPT(name, position) - extract subscript from name string

5. **Conditional Function**
   - $SELECT(cond1:val1, cond2:val2, ..., 1:default) - conditional selection
   - Special syntax - colon separates condition from value

6. **Extrinsic Functions** ($$label)
   - `$$label` - call label as function, return QUIT value
   - `$$label^routine` - external routine call (uses Spec 008 infrastructure)
   - Parameter passing (by value, by reference)

### Deliverables

- [ ] All string function implementations
  - Tests: `TestStringFunctionsCodegen` → [test_s7_1_5_intrinsic_functions.py](../tests/unit/codegen/s7_expressions/test_s7_1_5_intrinsic_functions.py)
- [ ] $RANDOM implementation
  - Tests: `TestRandomFunctionCodegen` → test_s7_1_5_intrinsic_functions.py
- [ ] Data function implementations ($DATA, $GET, $ORDER, $QUERY)
  - Tests: `TestDataFunctionsCodegen` → test_s7_1_5_intrinsic_functions.py
- [ ] Array utility functions ($NAME, $QLENGTH, $QSUBSCRIPT)
  - Tests: `TestArrayUtilityFunctionsCodegen` → test_s7_1_5_intrinsic_functions.py
- [ ] $SELECT implementation (special colon syntax)
  - Tests: `TestSelectFunctionCodegen` → test_s7_1_5_intrinsic_functions.py
- [ ] Extrinsic function support ($$label)
  - Tests: `TestExtrinsicFunctionCodegen` → [test_s7_1_6_extrinsic_functions.py](../tests/unit/codegen/s7_expressions/test_s7_1_6_extrinsic_functions.py)
- [ ] **Upgrade offset evaluator** to handle function calls
  - Tests: `TestComputedOffsetWithFunctionsCodegen` → test_s8_2_06_goto.py
- [ ] **Post-implementation documentation**
  - Update codegen-plan.md: mark deliverables complete, add implementation notes
  - Update docs/codegen/functions.md with all intrinsic function implementations
  - Add pre-requisites section to Spec 011

### Validation

- MUGJ: V1FN* series (all intrinsic function tests)
- MUGJ: V1BOA (data functions with globals)
- MUGJ: V1GO3.m (computed offsets with functions - full expression support)
- YDBTest: functions/* suite

### No Spikes Needed

All functions have well-defined ANSI semantics. Implementation is straightforward translation to Python.

---

## Spec 011: Extended Operators, Commands & Completion

**Goal**: Complete remaining operators, statements, and edge cases — mechanical translation work

This is cleanup work. Low risk, just filling in the remaining gaps.

### Pre-requisites from Spec 009/010

- MArray class (for MERGE, NEW/KILL semantics)
- Intrinsic functions (for validation tests)
- Global variables (for MERGE)

### Research Phase
Review before coding:
- **Docs**: `docs/codegen/operators.md`, `docs/asg/statements.md`
- **Operators**: `asg/expressions.py` → operator enums
- **Statements**: `asg/statements.py` → all statement types
- **Pattern match**: `asg/` → pattern codes (1N, .A) fully represented?
- **ASG dump**: `uv run python utils/validate_asg.py --compact -c "TEST S X=1&2 W X!3 Q"`

**Output**: Implementation order for operators and commands based on dependencies.

### Scope

1. **Extended Operators**
   - Negated comparisons: `'=`, `'<`, `'>`
   - Logical operators: `&` (AND), `!` (OR), `'` (NOT)
   - String concatenation: `_`
   - Contains: `[`, Follows: `]`, `]]`
   - Modulo: `#`, Integer division: `\`
   - Pattern match: `?` (basic patterns) — **verify parser captures pattern codes in ASG**

2. **Extended Statements**
   - SET with multiple assignments (`S X=1,Y=2`)
   - SET with subscripted targets
   - WRITE with format controls (`!`, `#`, `?n`, `*n`)
   - READ (basic, with timeout)
   - NEW (selective)
   - KILL (selective)
   - MERGE (copy array subtrees: `M dest=src`)
   - HANG (delay: `H seconds`)
   - HALT (terminate: `H` argumentless)
   - Postconditions on all commands (`S:cond X=1`)

3. **Exclusive NEW/KILL**
   - `N (A,B)` → save all except A,B
   - `K (X,Y)` → kill all except X,Y
   - Runtime scope manipulation

4. **Special Variables**
   - $HOROLOG, $JOB, $IO, $X, $Y
   - $STORAGE (memory available), $STACK (call level)
   - $QUIT (per ANSI 7.1.4.10): Returns 1 if current frame was invoked by exfunc/exvar, 0 otherwise
   - Some static, some require runtime tracking
   - **Note**: $TEST is covered in Spec 005; Spec 011 adds remaining special variables

5. **Decimal Numeric Literals**
   - Already parsed, just need codegen support

### Deliverables

- [ ] Extended operator generators
  - Tests: `TestOperatorsCodegen` → [test_s7_2_operators.py](../tests/unit/codegen/s7_expressions/test_s7_2_operators.py)
- [ ] SET with multiple assignments
  - Tests: `TestMultipleAssignmentCodegen` → [test_s8_2_18_set.py](../tests/unit/codegen/s8_commands/test_s8_2_18_set.py)
- [ ] WRITE format controls
  - Tests: `TestWriteFormatControlsCodegen` → [test_s8_2_25_write.py](../tests/unit/codegen/s8_commands/test_s8_2_25_write.py)
- [ ] READ command implementation
  - Tests: `TestReadCommandCodegen` → [test_s8_2_17_read.py](../tests/unit/codegen/s8_commands/test_s8_2_17_read.py)
- [ ] NEW/KILL selective implementation
  - Tests: `TestNewCommandCodegen` → [test_s8_2_12_new.py](../tests/unit/codegen/s8_commands/test_s8_2_12_new.py)
  - Tests: `TestKillCommandCodegen` → [test_s8_2_10_kill.py](../tests/unit/codegen/s8_commands/test_s8_2_10_kill.py)
- [ ] Exclusive NEW/KILL implementation
  - Tests: `TestExclusiveNewCodegen` → test_s8_2_12_new.py
  - Tests: `TestExclusiveKillCodegen` → test_s8_2_10_kill.py
- [ ] MERGE command implementation
  - Tests: `TestMergeCommandCodegen` → [test_s8_2_11_merge.py](../tests/unit/codegen/s8_commands/test_s8_2_11_merge.py)
- [ ] HANG command implementation
  - Tests: `TestHangCommandCodegen` → [test_s8_2_07_hang.py](../tests/unit/codegen/s8_commands/test_s8_2_07_hang.py)
- [ ] HALT command implementation
  - Tests: `TestHaltCommandCodegen` → [test_s8_2_08_halt.py](../tests/unit/codegen/s8_commands/test_s8_2_08_halt.py)
- [ ] Postcondition support
  - Tests: `TestPostconditionsCodegen` → [test_postconditions.py](../tests/unit/cross_cutting/test_postconditions.py)
- [ ] Special variable implementations
  - Tests: `TestSpecialVariablesCodegen` → [test_s7_1_7_special_variables.py](../tests/unit/codegen/s7_expressions/test_s7_1_7_special_variables.py)
- [ ] Pattern match operator
  - Tests: `TestPatternMatchCodegen` → test_s7_2_operators.py
- [ ] **Post-implementation documentation** (see [Post-Implementation Documentation](#post-implementation-documentation) section)
  - Update codegen-plan.md: mark all deliverables complete
  - Update docs/codegen/operators.md with all operator implementations
  - Final review of all codegen docs for accuracy

### Validation

- MUGJ: V1SET, V1WR, V1NUM series
- MUGJ: V1PAT (pattern match)
- MUGJ: V1NX series (NEW exclusive)
- YDBTest: basic/* suite
- Full VistA Kernel package translation attempt

### No Spikes Needed

All patterns are straightforward. Implementation builds on existing codegen patterns.

---

## Spec 012: Indirection & XECUTE Runtime (Dynamic Fallback)

**Goal**: Handle dynamic code patterns pervasive in VistA — the ultimate fallback for code that cannot be statically analyzed

This is the final spec because XECUTE and indirection can execute ANY MUMPS construct dynamically. All static constructs must be implemented first so `runtime.execute()` can handle them.

### Pre-requisites from Specs 007-011

- Line dispatch infrastructure (for computed targets in dynamic code)
- External routine loading (for `D ^ROUTINE` in dynamic code)
- Global variable support (for `^%ZOSF` patterns)
- All intrinsic functions (for dynamic code with `$PIECE`, `$LENGTH`, etc.)
- All operators and commands (dynamic code can contain anything)

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
   Uses global variable support from Spec 009 for `^%ZOSF` patterns.
   
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
  - Update codegen-plan.md: mark all deliverables complete
  - Final review: all MUMPS language constructs now covered

### Validation

- MUGJ: V1IDGOA, V1IDGOB (indirect GOTO)
- MUGJ: V1IDARG series (indirect arguments)
- MUGJ: V1XECA series (XECUTE)
- VistA: Kernel/XUINCON.m (real-world patterns)
- Full MUGJ suite (all tests should now pass)

### Spike: eval/exec Performance & Safety

**Hypothesis**: eval/exec approach is acceptable for correctness-first translation, with performance optimization deferred.

**Test**: Translate a routine with heavy indirection (pick from VistA). Measure:
1. Translation time
2. Execution time vs. YDB
3. Memory overhead of runtime context
4. Error message quality when MUMPS code fails

**Decision**: If performance is >10x slower than YDB, consider caching translated code. If error messages are poor, add source mapping.

---

## Spec 013: Label Fall-Through Support

**Goal**: Enable SIMPLE_FUNCTIONS strategy to support MUMPS implicit fall-through semantics

### Problem Statement

In MUMPS, control flow implicitly falls through from one label to the next when a label body doesn't end with QUIT, GOTO, or HALT. This is fundamental to MUMPS semantics:

```mumps
TEST   S PASS=0,FAIL=0
       W "Starting tests",!
FOR    W "FOR tests",!
       ; ... test code ...
489    W "Test I-489",!
       ; ... more tests ...
END    W "END",!
       Q
```

When `D TEST` is called, execution flows: `TEST` → `FOR` → `489` → `END` → QUIT.

**Current SIMPLE_FUNCTIONS limitation**: Each label is generated as a separate Python function. Calling `TEST()` only executes that function's body—it does NOT call `FOR()`, `_n_489()`, etc.

```python
def TEST(_rt, _scope=None, **_kwargs):
    _scope.setdefault('PASS', MArray()).value = 0
    _scope.setdefault('FAIL', MArray()).value = 0
    _rt.write("Starting tests")
    _rt.write("\n")
    # NO CALL TO FOR() - execution stops here!

def FOR(_rt, _scope=None, **_kwargs):
    # This is never reached when TEST is the entry point
```

**Impact**: MUGJ test files (V1IDNM1.m, V1FOR*.m, etc.) cannot be validated because they rely heavily on fall-through patterns. This blocks full MUMPS compatibility.

### Research Phase

Review before coding:
- **Docs**: `docs/codegen/goto_handling.md`, existing fall-through handling in TRAMPOLINE
- **Current TRAMPOLINE**: `routine.py` → `_generate_trampoline_label()` uses `next_label_map` for fall-through
- **Strategy selection**: `goto_analysis.py` → `classify_gotos()`, `needs_trampoline` flag
- **Label analysis**: `asg/elements.py` → `MLabel.has_explicit_exit`, `MLabel.ends_with_quit`
- **Dead code analysis**: `analysis/dead_code_analysis.py` → `label_ends_with_unconditional_exit()`
- **ASG dump**: `uv run python utils/validate_asg.py --compact tests/functional/mugj/inref/V1IDNM1.m`

**Key question**: Can we extend SIMPLE_FUNCTIONS without breaking existing tests, or do we need a new strategy?

### Strategy Candidates

#### Option A: Explicit Fall-Through Calls (SIMPLE_FUNCTIONS Extension)

Extend SIMPLE_FUNCTIONS to add explicit calls to the next label when the current label doesn't end with an exit:

```python
def TEST(_rt, _scope=None, **_kwargs):
    _scope.setdefault('PASS', MArray()).value = 0
    _scope.setdefault('FAIL', MArray()).value = 0
    _rt.write("Starting tests")
    _rt.write("\n")
    # Fall-through: call next label
    FOR(_rt, _scope=_scope)  # Added automatically

def FOR(_rt, _scope=None, **_kwargs):
    _rt.write("FOR tests")
    _rt.write("\n")
    # Fall-through: call next label
    _n_489(_rt, _scope=_scope)  # Added automatically

def END(_rt, _scope=None, **_kwargs):
    _rt.write("END")
    _rt.write("\n")
    # No fall-through: ends with QUIT
```

**Pros**:
- Minimal change to existing infrastructure
- Preserves function-based structure (Rope-friendly)
- Each label remains independently callable
- Shared `_scope` handles variable visibility naturally

**Cons**:
- Deep call stacks for routines with many sequential labels
- QUIT in nested label returns to wrong place (need careful semantics)
- RecursionError risk for very long label chains (>1000 labels)

**Mitigation for QUIT**: QUIT should return from the current subroutine context, not just the current function. This requires tracking "subroutine entry point" vs "fall-through entry":

```python
def TEST(_rt, _scope=None, _entry_point=True, **_kwargs):
    # ... body ...
    FOR(_rt, _scope=_scope, _entry_point=False)  # Fall-through

def FOR(_rt, _scope=None, _entry_point=False, **_kwargs):
    # ... body ...
    if some_condition:
        return  # QUIT - if _entry_point=False, just return; caller handles
    _n_489(_rt, _scope=_scope, _entry_point=False)
```

#### Option B: Flatten to Single Function (No Fall-Through Calls)

Generate all sequential labels as a single function with internal labels as comments:

```python
def TEST(_rt, _scope=None, **_kwargs):
    # --- TEST ---
    _scope.setdefault('PASS', MArray()).value = 0
    _scope.setdefault('FAIL', MArray()).value = 0
    _rt.write("Starting tests")
    _rt.write("\n")
    # --- FOR ---
    _rt.write("FOR tests")
    _rt.write("\n")
    # --- 489 ---
    _rt.write("Test I-489")
    _rt.write("\n")
    # --- END ---
    _rt.write("END")
    _rt.write("\n")
    return  # QUIT
```

**Pros**:
- No call stack issues
- QUIT semantics trivial (just `return`)
- More like original MUMPS execution model

**Cons**:
- Labels not independently callable (breaks `D FOR^ROUTINE`)
- Massive functions for large routines
- Less refactorable
- Internal GOTO becomes problematic

#### Option C: Expand TRAMPOLINE Usage

Use TRAMPOLINE strategy more broadly—not just for cross-label GOTOs:

```python
def _TEST(state) -> str | None:
    state.PASS = 0
    state.FAIL = 0
    _rt.write("Starting tests\n")
    return "FOR"  # Fall-through to next label

def _FOR(state) -> str | None:
    _rt.write("FOR tests\n")
    return "489"  # Fall-through

# Trampoline dispatcher
next_label = "TEST"
while next_label:
    next_label = _labels[next_label](state)
```

**Pros**:
- Already implemented and working
- No call stack issues
- Clean QUIT semantics (return `None`)
- External entry points work (`D FOR^ROUTINE` starts trampoline at FOR)

**Cons**:
- State class overhead for all routines
- Variable access via `state.X` instead of `_scope['X']`
- May require converting existing SIMPLE_FUNCTIONS code

#### Option D: Hybrid Strategy Selection

Extend strategy selection to consider fall-through patterns:

| Routine Pattern | Strategy | Rationale |
|-----------------|----------|-----------|
| All labels end with QUIT | SIMPLE_FUNCTIONS | No fall-through needed |
| Has cross-label GOTO | TRAMPOLINE | Already required |
| Has fall-through between labels | TRAMPOLINE or EXTENDED_SIMPLE | Fall-through needed |
| Simple extrinsic function | SIMPLE_FUNCTIONS | Single entry/exit |

**Implementation**: Add `has_fall_through` flag to `MRoutine` during analysis. Strategy selector uses:

```python
def select_strategy(routine: MRoutine) -> GotoStrategy:
    if routine.needs_trampoline:
        return GotoStrategy.TRAMPOLINE
    if routine.has_fall_through:
        return GotoStrategy.TRAMPOLINE  # or EXTENDED_SIMPLE
    return GotoStrategy.SIMPLE_FUNCTIONS
```

### Recommended Approach

**Option D (Hybrid)** with **Option A (Explicit Fall-Through)** as the implementation:

1. **Analysis phase**: Detect which routines have fall-through (labels not ending with exit)
2. **Strategy selection**: Routines with fall-through use extended strategy
3. **Code generation**: Add explicit next-label calls for fall-through cases
4. **QUIT handling**: Track entry context to handle nested QUIT correctly

This preserves the benefits of SIMPLE_FUNCTIONS for simple routines while enabling full MUMPS compatibility for complex ones.

### Scope

1. **Fall-Through Detection** (analysis enhancement)
   - Add `MLabel.ends_with_unconditional_exit` flag
   - Add `MRoutine.has_fall_through` computed property
   - Integrate with `classify_gotos()` or create new analysis pass

2. **Strategy Selection Update**
   - Extend `GotoStrategy` enum if needed: `SIMPLE_FUNCTIONS_WITH_FALLTHROUGH`
   - Update strategy selector to consider fall-through

3. **Fall-Through Code Generation**
   - Build `next_label_map` for SIMPLE_FUNCTIONS (like TRAMPOLINE has)
   - Generate explicit calls to next label when no exit statement
   - Handle QUIT semantics in fall-through context

4. **Entry Point Tracking**
   - Distinguish "subroutine entry" from "fall-through entry"
   - QUIT from fall-through should return to caller, not exit entirely

5. **External Entry Support**
   - `D FOR^ROUTINE` should work (start execution at FOR label)
   - Fall-through continues from that point

### Deliverables

- [ ] Fall-through detection in analysis pass
  - Tests: `TestFallThroughDetection` → new test file
- [ ] Strategy selection update for fall-through routines
  - Tests: `TestStrategySelectionFallthrough` → extend existing tests
- [ ] Fall-through code generation for SIMPLE_FUNCTIONS
  - Tests: `TestFallThroughCodegen` → new test file
- [ ] QUIT semantics in fall-through context
  - Tests: `TestQuitInFallThrough` → extend test_s8_2_16_quit.py
- [ ] External entry point support with fall-through
  - Tests: `TestExternalEntryFallThrough` → extend test_s8_2_03_do.py

### Validation

- MUGJ: V1IDNM1.m - 8 sequential test blocks with fall-through
- MUGJ: V1FOR*.m series - FOR loop tests with fall-through between test sections
- MUGJ: V1GO*.m series - GOTO tests (may also need fall-through)
- Construct minimal fall-through test cases:
  ```mumps
  TEST W "A"
  L2   W "B"
  L3   W "C" Q
  ; Expected output: ABC
  ```

### Spike: Fall-Through Semantics Validation

**Hypothesis**: Explicit fall-through calls match YDB behavior for all common patterns.

**Test cases to validate against YDB**:

1. **Simple fall-through**: `TEST → L2 → L3 → Q`
2. **Fall-through with external entry**: `D L2^ROUTINE` starts at L2, falls through to L3
3. **QUIT from fall-through context**: Does QUIT return to original caller or intermediate label?
4. **Fall-through into FOR loop**: Does FOR body fall-through work correctly?
5. **Conditional QUIT in fall-through**: `I cond Q` - partial fall-through

**Decision criteria**:
- If Option A (explicit calls) matches YDB for >95% of cases → implement Option A
- If QUIT semantics are problematic → consider Option C (TRAMPOLINE) as fallback
- If performance is critical → measure call stack depth for real VistA routines

### Dependencies

- **Spec 006**: Cross-label GOTO (TRAMPOLINE infrastructure exists)
- **Spec 008**: External calls (`D LABEL^ROUTINE`) - needed for full validation
- **Analysis infrastructure**: Dead code detection, exit statement classification

### Risk Assessment

| Risk | L/I | Mitigation |
|------|-----|------------|
| Deep call stacks for long routines | M/M | Monitor max depth in VistA; consider trampoline fallback |
| QUIT semantics break existing tests | M/H | Careful entry-point tracking; comprehensive test coverage |
| Performance regression | L/M | Benchmark before/after; explicit calls are just function calls |
| Strategy selection complexity | M/M | Clear decision tree; well-documented selection criteria |

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
| 004-007 | Embedded pytest only (unit tests with minimal syntax) |
| 008 | Embedded pytest + simple multi-routine tests (external calls) |
| 009-010 | Begin simple MUGJ files (now have globals + intrinsics) |
| 011 | More MUGJ files (have operators + commands) |
| 012 | Full MUGJ suite + VistA Kernel translation attempt (indirection/XECUTE) |
| 013 | MUGJ V1IDNM*, V1FOR*, V1GO* series validation (fall-through patterns) |

**Reality check**: MUGJ test files use globals, intrinsic functions, operators, and cross-routine calls extensively. Until Specs 009-010 are complete, most MUGJ files won't parse or execute correctly. Early specs should focus on small, focused unit tests that exercise specific features in isolation. **Additionally**, many MUGJ files rely on label fall-through (Spec 013), so full MUGJ validation requires both feature completeness AND fall-through support.

---

## Future Spec: Production Database Integration Testing (Spec TBD)

After Spec 009 implements the `GlobalStorageBackend` protocol with stub implementations for YottaDB and IRIS, a dedicated integration testing spec is needed to validate these backends work correctly with real databases.

### Scope

1. **Docker-based Test Environment**
   - YottaDB container with `yottadb` Python package installed
   - IRIS Community Edition container with `intersystems-irispython` package
   - CI/CD pipeline integration (GitHub Actions)

2. **YottaDB Integration Tests**
   - Test all `GlobalStorageBackend` methods against real YDB
   - Validate MUMPS→Python→YDB round-trip correctness
   - Test encoding edge cases (UTF-8, binary data)
   - Test connection failure handling

3. **IRIS Integration Tests**
   - Test all `GlobalStorageBackend` methods against real IRIS
   - Validate connection setup and teardown
   - Test transaction handling if supported

4. **Cross-Platform Consistency**
   - Same MUMPS code should produce same results on both backends
   - Subscript collation order verification
   - Numeric vs string subscript handling

### Deferred Items from Spec 009

The following were identified in Spec 009 as requiring production database testing:
- `YottaDBGlobalStorage.kill_node()` behavior verification
- `IRISGlobalStorage.query()` - not directly supported, needs workaround validation
- Connection timeout and retry handling
- Large value handling (>1MB values)
- Deep nesting limits (>100 subscript levels)

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
| **Label fall-through not supported** | **M/H** | **Spec 013: extend SIMPLE_FUNCTIONS or use TRAMPOLINE for fall-through routines** |
| QUIT semantics in fall-through | M/M | Track entry context; distinguish subroutine entry from fall-through |

---

## Reference Documents

- [docs/codegen/variable_scoping.md](../docs/codegen/variable_scoping.md) - Variable scoping strategies
- [docs/codegen/mumps_gotchas.md](../docs/codegen/mumps_gotchas.md) - MUMPS semantics and edge cases
- [tests/functional/mugj/inref/V1GO2.m](../tests/functional/mugj/inref/V1GO2.m) - Computed offset test patterns
- [src/m2py/analysis/variables.py](../src/m2py/analysis/variables.py) - Variable analysis implementation
