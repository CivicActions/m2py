# Learnings from YottaDB Test Suite Validation

## Overview

This document captures critical insights, architectural "gotchas," and semantic nuances discovered during the `017-ydb-test-failures` feature branch work. These learnings specifically inform the design of the Unified Variable System (Spec 018) and future architectural refactoring.

All behaviors documented here have been validated against YottaDB (YDB) as the reference implementation.

---

## 1. The Duality of Indirection

MUMPS uses the `@` syntax for two fundamentally different operations depending on the grammatical context. Treating them identically leads to incorrect behavior.

### Name Indirection (`@Variable`)
Used in `SET`, `WRITE`, `MERGE`, `KILL`, `READ`.

*   **Behavior**: The value of the variable is **evaluated as a MUMPS expression**, and the result is used as an **identifier** (variable name).
*   **Example**: `S A="B", @A=1` sets variable `B` to 1.
*   **Recursive**: `S A="B", B="C", @@A=1` sets variable `C` to 1.
*   **Function Evaluation**: If `A="$E(""ABC"",3)"` and `C=99`, then `W @A` outputs `99`.
    *   The string `$E("ABC",3)` is evaluated as a MUMPS expression → `"C"`.
    *   `"C"` is then used as a variable name → outputs value of `C` (99).
*   **Constraints**: The final resolved string *must* be a valid MUMPS variable name.
*   **Error Cases**:
    *   `S A="1+1", @A=5` → Error `%YDB-E-VAREXPECTED` (result `2` is not a valid variable name)
    *   `S A="", @A=5` → Error `%YDB-E-VAREXPECTED` (empty string is not a valid variable name)

### Argument Indirection (`@Variable` in Command arguments)
Used in `IF`, `FOR` (arg), `DO` (arg), `XECUTE`.

*   **Behavior (Critical)**: The value of the variable is **evaluated as a complete MUMPS expression**, and the result is used as the command argument.
*   **Key Difference**: The final result does NOT need to be a variable name - it's evaluated for its value.
*   **Example**: `S A="1=0" I @A` implies `IF 1=0`.
    *   **Incorrect (naive implementation)**: Treat "1=0" as a string → `m_truth("1=0")` → converts to number 1 → True. **WRONG**.
    *   **Correct (MUMPS)**: Evaluate "1=0" as expression → `0` (False).
*   **Variable References in Expressions**: `S A="X>5",X=10 I @A` → evaluates `X>5` with current value of X → True.
*   **Multi-Level**: `S A="B",B="1=0" I @@A` → resolves A→"B", then evaluates "1=0" → False.
*   **Empty String Edge Case**: `S A="" I @A` evaluates to **True** (empty indirection succeeds but produces empty condition which is truthy in this context - YDB-specific behavior, needs more investigation).
*   **Implication**: The runtime requires an `evaluate_expression(str)` capability that can parse and execute MUMPS expression snippets at runtime, similar to `XECUTE`.

---

## 2. Subscript Canonicalization

MUMPS is aggressive about treating numeric-looking values as canonical numbers for subscript purposes.

### Validated Equivalences
*   `A(1)`, `A(01)`, `A(1.0)`, `A("1")` all access the **exact same node**.
*   Verified: `S A(1)="val"` then `W A(01)` → "val", `W A(1.0)` → "val", `W A("1")` → "val".

### String vs Numeric Distinction
*   `A("01")` (explicit non-canonical string) is **distinct** from `A(1)`.
*   Verified: `S A("01")="string01", A(1)="numeric1"` → `W A("01")` outputs "string01", `W A(1)` outputs "numeric1".

### Implementation Gotcha
*   Python dictionaries: `1 == 1.0` (True), but `1 == "1"` (False).
*   MUMPS canonicalization must happen **before** storage key creation.
*   The storage layer (MArray/Global backend) must normalize all numeric-looking subscripts to their canonical string form.

---

## 3. Code Generation: The F-String Trap

Attempting to generate Python variable references using f-strings (e.g., `f"{name}({sub})"`) is fragile and prone to syntax errors when nested.

*   **The Issue**: When generating code for subscripts, the subscript expression itself may contain quotes, parentheses, or complex expressions.
    *   Example: `@A(@A(2))` - the inner indirection generates a runtime call that cannot be safely embedded in an f-string.
    *   If `sub` evaluates to something containing quotes, the generated Python code causes a `SyntaxError`.
*   **The Solution**: Use explicit string concatenation or structured argument passing.
    *   **Bad**: `f"{base}({sub})"`
    *   **Better**: `base + "(" + str(sub) + ")"`
    *   **Best (Future)**: Pass components to runtime: `rt.get_var(name=base, subscripts=[sub1, sub2])` - avoids string building entirely.

---

## 4. Scope Management and Isolation

Defining where variables "live" is complex due to the mix of compiled Python locals and the shared MUMPS runtime state.

*   **Trampoline vs. Functions**: In `TRAMPOLINE` mode, local variables may live in `state._locals`. In `SIMPLE_FUNCTIONS`, they might be Python locals.
*   **Cross-Routine Visibility**: `XECUTE` and Indirection often need access to the *caller's* scope.
    *   **Gotcha**: `UndefinedVariable` errors occurred because runtime methods (`get_var`, `resolve_indirection`) looked in `_scope` (the shared context dict), but the current routine stored variables as Python locals or in `state._locals`.
*   **Key Learning**: The runtime needs a unified "Current Scope" concept that abstracts away the storage mechanism. All variable access (static or indirected) must use the same lookup path.

---

## 5. Naked Global State Management

The "Naked Indicator" (`^(subs)`) relies on global state side-effects that are easy to miss.

### Rule
*Any* global reference - literal, subscripted, or accessed through indirection - updates the naked indicator.

### Validated Behavior
*   `S ^GLO(1,2)=1, ^GLO(1,3)="naked" W ^(3)` → outputs "naked" (accesses `^GLO(1,3)`)
*   The naked indicator stores the **base global name** and **all but the last subscript**.
*   `^(newsub)` replaces only the **last** subscript level.

### Indirection Interaction
*   `S A="^Other(9)", @A=2` updates naked indicator to `^Other(9)`.
*   Subsequent `W ^(3)` accesses `^Other(3)`.

### Key Lesson
Static analysis cannot optimize naked references. The `NakedGlobal` entity must always resolve dynamically against the runtime's current state at the moment of access.

---

## 6. Name Translation Consistency

Inconsistent identifiers between Code Generation and Runtime Lookup caused subtle bugs.

### The Problem
*   Codegen translates `%A` → `_pct_A` and stores in scope dict.
*   Runtime receives indirection string `"@%A"`.
*   If Runtime looks for key `%A` in the scope dict: **FAIL** (key is `_pct_A`).
*   If Runtime translates `%A` → `_pct_A` differently than Codegen: **FAIL**.

### Translation Rules (Must Be Consistent)
| MUMPS Name | Python Identifier |
|------------|-------------------|
| `%NAME`    | `_pct_NAME`       |
| `01` (numeric start) | `_n_01` |
| `if` (Python keyword) | `_m_if` |

### Requirement
A single, shared `NameTranslator` component must be used by:
1. The Parser/Codegen (when creating Python variables and scope keys).
2. The Runtime (when looking up variables via Name Indirection).

---

## 7. MArray Complexity

The `MArray` wrapper object handles the "node has value AND children" property of MUMPS arrays, but it complicates access patterns.

### MUMPS Array Semantics
In MUMPS, a variable `A` can simultaneously have:
*   A scalar value: `S A="root"`
*   Child nodes: `S A(1)="child1", A(1,2)="grandchild"`

### Python Representation Challenge
*   Python: A variable cannot be both a string and a dict.
*   M2PY: `A` is an `MArray` where `A.value` holds the scalar, and `A._storage` holds children.

### Access Patterns
*   Reading `A` → returns `A.value`
*   Reading `A(1)` → returns `A.get(1)` or `A._storage[(1,)]`
*   Writing `A(1,2)=5` → `A.set((1,2), 5)`

### Common Gotcha
Helper functions (`m_str`, `m_num`, `m_compare`, etc.) often received the `MArray` wrapper object instead of its `.value`, causing:
*   String conversion errors: `str(MArray(...))` returning `"MArray(...)"`
*   Comparison failures: `MArray != "expected_string"`

**Solution**: All helper functions must recursively extract `.value` from MArray objects before processing.

---

## 8. Runtime Expression Evaluation

MUMPS allows dynamic code execution in more contexts than typical languages.

### Contexts Requiring Runtime Evaluation
*   `XECUTE string` - explicit code execution
*   Argument Indirection (`I @A`) - expression in condition
*   Name Indirection with functions (`W @A` where `A="$E(""ABC"",3)"`) - evaluates function, uses result as name
*   `$TEXT` with computed arguments

### Implementation Requirements
Use of Python's `exec()` or a mini-parser is necessary, requiring careful preparation:
*   Inject runtime helpers (`m_num`, `m_str`, `m_truth`, etc.)
*   Provide access to current variable scope
*   Handle return values for expression evaluation

### Key Insight
The existing `execute_mumps()` method (used for XECUTE) provides a template: parse MUMPS code, generate Python, execute with injected namespace. A lighter-weight `evaluate_expression()` method could reuse this pattern for single expressions.

---

## 9. Order of Operations in Complex Indirection

Consider `S @A@(@B)=1`:
1. Resolve `@A` → let's say it returns `^G`
2. Evaluate `@B` → let's say it returns `2`
3. Operation becomes `S ^G(2)=1`

### Per-Level Subscript Application
For `@@X@(1,2)@(5,6)`:
1. Resolve `X` → get value (e.g., `"A"`)
2. Apply `(1,2)` → access `A(1,2)` → get value (e.g., `"B(3,4)"`)
3. Apply `(5,6)` → final target is `B(3,4,5,6)`

### Evaluation Order Guarantee
*   Left-to-right evaluation is mandatory.
*   If resolving `@A` has side effects (e.g., via `$$Extrinsic` function), they must complete *before* `@B` is evaluated.
*   Generated Python code must enforce this sequential evaluation order - no parallel evaluation of subscripts.

---

## 10. MUMPS Truth Value Semantics

### The `m_truth()` Trap
MUMPS truth evaluation is numeric:
*   `0` and `""` (empty string, which converts to 0) are **false**
*   Any non-zero numeric value is **true**
*   Strings are converted to numbers first: `"1=0"` → `1` (leading numeric portion) → **true**

### The Argument Indirection Difference
For `I @A` where `A="1=0"`:
*   **Wrong**: `m_truth("1=0")` → `m_num("1=0")` → `1` → true
*   **Right**: Evaluate `"1=0"` as MUMPS expression → `1=0` → `0` → false

This is the critical semantic difference between treating the indirection value as:
1. A **literal value** to convert to truth (wrong for argument indirection)
2. An **expression** to evaluate (correct for argument indirection)

---

## 11. Error Handling in Indirection

### Name Indirection Errors
*   Empty string: `S A="", @A=5` → `%YDB-E-VAREXPECTED`
*   Invalid result: `S A="1+1", @A=5` → `%YDB-E-VAREXPECTED` (result `2` is not a variable name)
*   Undefined variable: `S @UNDEFINED=5` → `%YDB-E-LVUNDEF`

### Argument Indirection Behavior
*   Empty string: `S A="" I @A` → Succeeds (evaluates to truthy - YDB-specific behavior)
*   Expression error: Propagates the expression evaluation error

### Key Insight
Error messages should include the original indirection source and the resolved value to aid debugging:
`IndirectionError: A="1+1" - resolved to "2" which is not a valid variable name`

---

## 12. Multi-Level Indirection Resolution

### Resolution Algorithm
For `@@@A`:
1. Get value of `A` → `"B"`
2. Get value of `B` → `"C"`
3. Get value of `C` → `99`
4. Result: `99`

### Argument Indirection Variant
For `I @@@A` where `A="B"`, `B="C"`, `C="1=0"`:
1. Resolve `A` → `"B"`
2. Resolve `B` → `"C"`
3. Resolve `C` → `"1=0"`
4. **Evaluate** `"1=0"` as expression → `0` (false)

The final step changes from "get value" to "evaluate expression" only in argument indirection context.

### Recursive @ in Values
If `A="@B"`, `B="C"`, `C=99`, then `W @@A`:
1. Resolve `A` → `"@B"`
2. Evaluate `"@B"` as expression → resolves to value of `C` → `99`

The intermediate value containing `@` triggers recursive indirection evaluation.
