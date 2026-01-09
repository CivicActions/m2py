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

### Scope (Minimal)

1. **Literals**
   - Numeric literals (integers only: `1`, `10`, `-5`)
   - String literals (`"A"`, `"PASS"`)

2. **Local Variables**
   - Simple names only (`X`, `I`, `COUNT`)
   - No subscripts, no globals

3. **Operators (Comparison + Basic Arithmetic)**
   - Comparison: `=`, `<`, `>`
   - Arithmetic: `+`, `-`, `*` (for loop increments and left-to-right validation)
   - Left-to-right with parenthesization (e.g., `2+3*4` = 20, not 14)

4. **Statements (Minimal Set)**
   - `SET` - single assignment only (`S X=1`)
   - `WRITE` - single value only (`W X` or `W "text"`)
   - `QUIT` - with and without value (no postconditions)
   - `DO` - label call within same routine (no offset)
   - `IF` / `ELSE` - basic condition
   - `FOR` - bounded and string-list types with **literal parameters** (e.g., `F I=1:1:10`, `F I="A","B"`)
   - `GOTO` - label targets only, **no offsets** (e.g., `G LABEL`, not `G LABEL+5`)

### Explicitly Deferred to Spec 005

- Open-ended FOR (`F I=1:1`) and argumentless FOR (`F`)
- QUIT postcondition (`Q:cond`) for loop exit

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
- Postconditions on other commands (S:cond X=1)
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

The ydb Docker image is already available locally - no need to pull.

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

### Scope

1. **IF/ELSE with $TEST tracking**
   - Track `_test` variable for ELSE and argumentless IF
   - Comma-separated conditions (AND semantics)
   - Postconditions (Spec 008) do NOT update $TEST
   
2. **$TEST Stack Semantics**
   - **Argumentless DO**: `$TEST` is stacked (NEW $TEST), restored on QUIT
   - **Extrinsic calls** (`$$label`): `$TEST` is stacked, restored on QUIT  
   - **DO with arguments**: `$TEST` NOT stacked - callee mutations visible to caller
   - **XECUTE**: `$TEST` NOT stacked - mutations visible to caller
   
   This is critical for ELSE chains that span DO calls.

3. **FOR Loop Variations** (all types including open-ended and argumentless)
   - `ForLoopType.OPEN_ENDED` (`F I=1:1`) → `while True:` with increment
   - `ForLoopType.ARGUMENTLESS` (`F`) → `while True:`
   - `ForLoopType.STRING_LIST` → `for x in [...]`
   - `ForLoopType.MIXED` → `itertools.chain` or unrolling
   - `loop_var_modified_in_body=True` → `while` loop
   - `has_internal_quit=True` → add `break` support
   - QUIT postcondition (`Q:cond`) for loop exit → `if cond: break`

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

#### Option A: Labels-as-Functions with Shared State

```python
class RoutineState:
    """Shared state for cross-label variable visibility."""
    x: int = 0
    y: str = ""

def label_A(state: RoutineState) -> Optional[str]:
    state.x = 1
    if condition:
        return "B"  # Transfer to label B
    return None  # Fall through / exit

def label_B(state: RoutineState) -> Optional[str]:
    state.y = str(state.x)  # x visible from label A
    return "A"  # Loop back

# Trampoline dispatcher (REQUIRED - prevents RecursionError)
# Labels RETURN next label, never CALL next label directly
state = RoutineState()
labels = {"A": label_A, "B": label_B}
next_label = "A"
while next_label:
    next_label = labels[next_label](state)
```

**Pros**: Refactorable, each label is a unit, Rope-friendly  
**Cons**: State class overhead, return values need threading  
**CRITICAL**: Must use trampoline pattern - direct function calls would hit Python's 1000-frame recursion limit

#### Option B: State Machine (Match-Case)

```python
state = "A"
# All variables in outer scope - naturally visible across states
x = 0
y = ""
while True:
    match state:
        case "A":
            x = 1
            if condition:
                state = "B"
                continue
            break
        case "B":
            y = str(x)  # x naturally visible
            state = "A"
            continue
```

**Pros**: Simple, handles any pattern, natural variable visibility  
**Cons**: Not refactorable, large match blocks

#### Option C: Hybrid

- Use structured translation when `has_unstructured_goto=False`
- Fall back to state machine only when truly irreducible
- State machine handles variable visibility naturally; labels-as-functions needs state class

**Strategy Selection Criteria**:
- `has_unstructured_goto=True` → State Machine (required)
- Label is target of computed offset (`G LABEL+expr` from anywhere) → State Machine (required for line-level dispatch)
- Otherwise → Labels-as-Functions (preferred)

Note: Computed offsets can only target LEVEL 1 lines (MUMPS semantics), so "jumping into blocks" isn't possible. But state machine is still simpler for computed offset dispatch since it naturally supports `goto_line(n)`.

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

## Spec 007: Indirection & XECUTE Runtime

**Goal**: Handle dynamic code patterns pervasive in VistA

### Scope

1. **Runtime Infrastructure**
   
   Build the shared runtime that manages M semantics at execution time.
   **Note**: Basic global variable support (`^VAR`, `^VAR(sub)`) is included here so XECUTE/indirection tests can use realistic VistA patterns (e.g., `^%ZOSF`). Spec 008 adds extended global features (naked refs, complex subscripting).
   
   ```python
   class MUMPSRuntime:
       variables: dict      # Local scope
       globals: dict        # ^globals (basic support)
       test: bool          # $TEST
       
       def execute(self, mumps_code: str) -> Any:
           """Translate and execute MUMPS at runtime"""
           python_code = m2py.translate(mumps_code)
           exec(python_code, self._context())
       
       def get_global(self, name: str, *subscripts) -> Any:
           """Read ^name(sub1,sub2,...) - basic support"""
       
       def set_global(self, name: str, value: Any, *subscripts) -> None:
           """Write ^name(sub1,sub2,...) = value - basic support"""
   ```

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
   
   **Code generation approach**:
   ```python
   # At routine initialization, build line map
   _line_map = {
       1: _line_1,    # First executable line
       5: _line_5,    # Label START
       6: _line_6,    # Next statement
       # ...
   }
   
   # For: G LABEL+expr
   def _goto_with_offset(label_line: int, offset_expr):
       target_line = label_line + int(eval_expr(offset_expr))
       if target_line not in _line_map:
           raise MUMPSError(f"Invalid line offset: {target_line}")
       return _line_dispatch(target_line)
   ```
   
   **Non-executable lines**: Comment-only lines and blank lines are NOT in `_line_map`. Per MUMPS semantics, `G LABEL+n` where n lands on a non-executable line should either error (strict) or skip to next executable (lenient). Validate actual YDB behavior.

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

### Validation

- VistA routines with cross-routine calls
- MUGJ: V1NX series (NEW exclusive)
- Full VistA Kernel package translation attempt

### No Spikes Needed

Patterns are understood, just require careful implementation of runtime infrastructure from Spec 007.

---

## Test Infrastructure (Cross-Cutting)

**Primary approach**: Embedded strings in pytest (no file I/O overhead).

Tests live in `tests/unit/codegen/` organized by ANSI standard section.

### Test Fixtures

From `tests/unit/codegen/conftest.py`:

| Fixture | Use Case | Example |
|---------|----------|---------|
| `generate_python(source)` | Inspect generated Python code | `assert "X = " in generate_python("TEST\n S X=1\n Q")` |
| `execute_mumps(source)` | Full routine execution | `assert execute_mumps("TEST\n S X=1\n W X\n Q").output == "1"` |
| `execute_expr(code)` | Single command (auto-wrapped) | `assert execute_expr('W 1+2') == "3"` |
| `eval_mumps(expr)` | Expression value (no WRITE) | `assert eval_mumps('$L("ABC")') == "3"` |

**When to use each**:
- `execute_mumps`: Multi-line routines, control flow, label interactions
- `execute_expr`: Simple commands, operators, single statements
- `eval_mumps`: Expression evaluation tests (arithmetic, functions, concatenation)
- `generate_python`: Code structure inspection, pattern validation

```python
# Full routine (execute_mumps)
def test_set_executes(execute_mumps):
    result = execute_mumps("TEST\n S X=1\n W X\n Q")
    assert result.output == "1"

# One-liner (execute_expr) - auto-wrapped in label
def test_addition(execute_expr):
    assert execute_expr('W 1+2') == "3"

# Expression eval (eval_mumps) - returns value without WRITE
def test_length(eval_mumps):
    assert eval_mumps('$L("ABC")') == "3"

# Parametrized tests are clean with one-liner fixtures
@pytest.mark.parametrize("expr,expected", [
    ("1+2", "3"),
    ('"A"_"B"', "AB"),
    ("$L(\"ABC\")", "3"),
])
def test_expressions(execute_expr, expr, expected):
    assert execute_expr(f'W {expr}') == expected
```

### Test Stub Guidelines

**Before implementing each spec, audit test stubs for overlap**:
- New test classes (e.g., `TestNumericCoercionCodegen`) may overlap with existing classes (e.g., `TestValuesCodegen`)
- Prefer adding tests to existing classes when the concept is already covered
- Create new test classes only for genuinely new concepts not represented

**Generate expected outputs at phase start, not upfront**:
- Run YDB to get reference outputs when implementing each test
- Avoids generating 300+ outputs that may need revision
- Exception: Generate spike reference outputs before starting spikes

**YDB validation** (for complex cases only):

```bash
# When debugging discrepancies
echo 'D ^TEST' | ydb  # Get reference output from YDB
```

### Coverage Metrics

**Goal: Maintain ≥85% overall test coverage** throughout development.

**Quick check** (both metrics):
```bash
uv run python utils/coverage_check.py
```

**Individual metrics**:
```bash
uv run python utils/coverage_check.py overall   # Must stay ≥85%
uv run python utils/coverage_check.py transpile # Progress toward full transpilation
```

**Transpilation Readiness**: Measures parser/asg/analysis coverage when running *only* codegen tests. Normalized to 0-100% progress (15% baseline = 0%, 85% target = 100%).

| Milestone | Transpilation Coverage | Notes |
|-----------|----------------------|-------|
| Baseline (stubs only) | 15% | Import overhead only |
| Spec 004 complete | TBD | Basic control flow |
| Spec 005 complete | TBD | Structured control flow |
| Spec 006 complete | TBD | Cross-label GOTO |
| Spec 007 complete | TBD | Indirection/XECUTE |
| Spec 008 complete | TBD | Core language |
| Spec 009 complete | TBD |  |

**Interpreting the gap**: Low coverage in specific files reveals codegen implementation gaps:
- `for_analysis.py` at 5% → FOR loop codegen incomplete
- `goto_analysis.py` at 6% → GOTO codegen incomplete
- `variables.py` at 7% → Scope strategy codegen incomplete

### Validation Progression

| Spec | Test Approach | Focus |
|------|---------------|-------|
| 004 | Embedded pytest tests | Basic syntax for control flow |
| 005 | Embedded pytest tests | FOR/IF/scope strategies, by-ref patterns |
| 006 | Embedded pytest + V1GO1 (spike) | Cross-label GOTO, variable visibility |
| 007 | MUGJ files: V1ID*, V1XEC* | Indirection/XECUTE (need full syntax) |
| 008 | MUGJ files: V1SET, V1WR, V1FN*, V1GO2 | Full language, computed offsets |
| 009 | Full MUGJ + VistA Kernel | Production readiness |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Cross-label GOTO strategy fails | Medium | High | Spike bake-off before committing |
| Variable visibility across labels | Medium | High | State class or match-case scope; analysis provides input/output vars |
| Computed offsets require line-indexed model | High | Medium | Existing `MLabel.line_number`; build statement line map in 008 |
| eval/exec too slow | Low | Medium | Cache translated code |
| Indirection patterns more complex than expected | Medium | Medium | Start with static cases |
| VistA has patterns not in MUGJ | Medium | High | Validate against real VistA early |
| Rope can't handle generated code | Low | Medium | Simplify output patterns |
| By-ref parameter handling awkward | Medium | Medium | Use return-value pattern; `byref_outputs` tells which params modified |
| Duplicate test stubs waste effort | Medium | Low | Audit new stubs vs existing classes before implementing each spec |
| Coverage regression during development | Low | Medium | Maintain ≥85% overall; track transpilation readiness per spec |

---

## Reference Documents

- [docs/codegen/variable_scoping.md](../docs/codegen/variable_scoping.md) - Variable scoping strategies
- [docs/codegen/mumps_gotchas.md](../docs/codegen/mumps_gotchas.md) - MUMPS semantics and edge cases
- [tests/functional/mugj/inref/V1GO2.m](../tests/functional/mugj/inref/V1GO2.m) - Computed offset test patterns
- [src/m2py/analysis/variables.py](../src/m2py/analysis/variables.py) - Variable analysis implementation
