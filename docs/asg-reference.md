# ASG Reference

The Abstract Semantic Graph (ASG) is the central data model in m2py. All nodes are Python dataclasses in `src/m2py/asg/`. The ASG is produced by the parser, enriched by analysis passes, and read by code generation.

> For field-level details, refer directly to the source files. This document describes the structure and purpose of each node category.

## Class Hierarchy

```
MParseError                        (plain dataclass, not an ASG node)

ASGElement (ABC)                   (source tracking: line, column, parent)
 ├── MRoutine                      (top-level container)
 ├── MLabel                        (named entry point)
 ├── MScope                        (statement container)
 ├── MCall                         (reference to a label/routine)
 ├── MExpr                         (expression base)
 │    ├── MLiteral                  (string/integer/decimal constant)
 │    ├── MVariable                 (local variable, optionally subscripted)
 │    ├── MGlobal                   (^global variable)
 │    ├── MNakedGlobal              (^(subscripts) naked reference)
 │    ├── MBinaryOp                 (left op right)
 │    ├── MUnaryOp                  (+, -, ' prefix)
 │    ├── MIntrinsicFunction        ($LENGTH, $PIECE, etc.)
 │    ├── MExtrinsicFunction        ($$FUNC^ROUTINE)
 │    ├── MExternalFunction         ($&package.name)
 │    ├── MPatternMatch             (expr ? pattern)
 │    ├── MIndirection              (@expression)
 │    ├── MSpecialVariable          ($TEST, $HOROLOG, etc.)
 │    ├── MStructuredSystemVariable (^$JOB, ^$GLOBAL, etc.)
 │    ├── MFormatControl            (!, #, ?n, *n)
 │    └── MDeviceControl            (/keyword)
 ├── MActualParameter               (function argument with PassingMode)
 ├── MSelectArg                     (condition:value pair for $SELECT)
 └── MStatement                     (statement base)
      ├── MSetStatement, MWriteStatement, MReadStatement
      ├── MIfStatement, MElseStatement
      ├── MForStatement, MGotoStatement, MDoStatement, MQuitStatement
      ├── MNewStatement, MKillStatement, MKSubscriptsStatement, MKValueStatement
      ├── MMergeStatement, MXecuteStatement, MLockStatement
      ├── MHangStatement, MHaltStatement, MBreakStatement, MViewStatement
      ├── MOpenStatement, MCloseStatement, MUseStatement
      ├── MJobStatement
      ├── MTStartStatement, MTCommitStatement, MTRestartStatement, MTRollbackStatement
      └── MZ* statements (ZShow, ZWrite, ZBreak, ZGoto, ZKill, ZLink, etc.)
```

## Structural Elements

### MRoutine

The root ASG node. Contains all labels, original source lines (for `$TEXT`), and parse errors from error-tolerant parsing. Analysis passes populate flags that drive code generation strategy selection:

- **Trampoline flags**: `needs_trampoline`, `has_offset_calls`, `has_external_gotos` — determine whether SIMPLE_FUNCTIONS or TRAMPOLINE strategy is used
- **Dynamic locals flags**: `has_argumentless_kill`, `has_argumentless_new`, `has_exclusive_kill`, `has_exclusive_new`, `has_name_indirection_on_locals`, `has_byref_params`, `has_byref_calls` — determine whether the trampoline uses static state fields or a dynamic `_locals` dict
- **Variable sets**: `routine_state_vars`, `array_vars`, `routine_input_only_vars` — computed by variable analysis for RoutineState generation

### MLabel

A named entry point in a routine. Contains a `formal_list` of parameter names, a `body` scope, and back-references populated by analysis:

- `callers` / `goto_sources` — which `MCall` nodes reference this label
- `input_variables` / `output_variables` — variables read-before-write / visible to caller
- `signature` — `FunctionSignature` computed by variable analysis
- `needs_fallthrough` / `next_label` — label flows into next without explicit exit

### MScope

A container of `MStatement` nodes. Used for label bodies, IF then-branches, FOR bodies, ELSE bodies, and argumentless DO blocks. Provides `walk_statements()` for recursive traversal.

### MCall

A reference to a label or routine, used by DO, GOTO, and extrinsic function calls. Fields track resolution state (`target`, `is_resolved`, `call_type`) and indirection (`label_is_indirect`, `routine_is_indirect`). Resolution is performed by the `resolve_references()` analysis pass.

## Expression Nodes

All expressions inherit from `MExpr`. Key categories:

- **Values**: `MLiteral` (typed constant), `MVariable` (local, optionally subscripted), `MGlobal` / `MNakedGlobal` (global variables)
- **Operations**: `MBinaryOp` (arithmetic, string, comparison, logical), `MUnaryOp` (sign, NOT)
- **Functions**: `MIntrinsicFunction` (40+ built-in functions), `MExtrinsicFunction` (user-defined `$$FUNC`), `MExternalFunction` (`$&callout`)
- **Pattern matching**: `MPatternMatch` — carries both the source pattern and `compiled_regex` (compiled during semantic analysis)
- **Indirection**: `MIndirection` — `@` expressions with `indirection_type` (NAME, SUBSCRIPT, ARGUMENT, PATTERN) and optional static resolution
- **Special variables**: `MSpecialVariable` (ISVs like `$TEST`, `$HOROLOG`), `MStructuredSystemVariable` (SSVNs like `^$JOB`)
- **I/O controls**: `MFormatControl` (write format: `!`, `#`, `?n`, `*n`), `MDeviceControl` (device mnemonics)
- **Parameters**: `MActualParameter` wraps an expression with `PassingMode` (BY_VALUE, BY_REFERENCE, OMITTED)

## Statement Nodes

All statements inherit from `MStatement`, which provides `scope` (parent scope), `postcondition` (optional guard expression), `comment`, and `is_unreachable` (set by dead code detection in the parser).

### Core Commands

| Node | MUMPS | Key Structure |
|------|-------|---------------|
| `MSetStatement` | SET | List of `MAssignment(target, value, postcondition)` |
| `MWriteStatement` | WRITE | Mixed list of expressions and format controls |
| `MReadStatement` | READ | List of `MReadTarget` with timeout/length options |
| `MIfStatement` | IF | `conditions` list (comma = AND), `then_scope` body, `restructurable_goto` back-ref |
| `MElseStatement` | ELSE | `body` scope (MUMPS ELSE is a separate command, not part of IF) |
| `MForStatement` | FOR | `loop_var`, `parameters` (value/range/open-range), `body` scope, plus 10+ analysis fields |
| `MGotoStatement` | GOTO | `targets` list of `MCall`, classification fields set by GOTO analysis |
| `MDoStatement` | DO | `targets` list of `MCall` or `body` scope (argumentless DO block) |
| `MQuitStatement` | QUIT | Optional `return_value`, context flags `exits_for`/`exits_do_block` |
| `MNewStatement` | NEW | `variables` list or `exclusive` with `except_list` |
| `MKillStatement` | KILL | `targets` list, `exclusive` mode, `except_groups` |
| `MMergeStatement` | MERGE | List of `MMergePair(destination, source)` |
| `MXecuteStatement` | XECUTE | List of `MXecuteArg(expression, postcondition)`, `is_constant` optimization flag |
| `MLockStatement` | LOCK | List of `MLockTarget` with per-target `lockop` (+ / - / none) |

### I/O, JOB, and Transaction Commands

`MOpenStatement`, `MCloseStatement`, `MUseStatement` (device I/O), `MJobStatement` (subprocess), `MTStartStatement` / `MTCommitStatement` / `MTRollbackStatement` (transactions).

### Z-Commands (YottaDB Extensions)

Approximately 20 Z-command statement types (`MZShowStatement`, `MZWriteStatement`, `MZBreakStatement`, `MZGotoStatement`, `MZKillStatement`, `MZLinkStatement`, etc.) for YottaDB-specific functionality.

## Enums

Defined in `src/m2py/asg/enums.py`:

| Enum | Purpose |
|------|---------|
| `ForLoopType` | FOR classification: BOUNDED, OPEN_ENDED, STRING_LIST, MIXED, ARGUMENTLESS |
| `ForParamType` | Individual FOR parameter: VALUE, RANGE, OPEN_RANGE |
| `GotoType` | GOTO classification: FORWARD_JUMP, BACKWARD_JUMP, LOOP_EXIT, MULTI_LOOP_EXIT, EXTERNAL, INDIRECT, UNRESOLVED |
| `GotoCodegenPattern` | How to emit this GOTO: BREAK, MULTI_BREAK, FORWARD, FUNCTION_CALL, UNSUPPORTED |
| `CallType` | Reference type: LABEL_CALL, OFFSET_CALL, ROUTINE_CALL, INDIRECT_CALL, UNRESOLVED |
| `LiteralType` | Literal kind: STRING, INTEGER, DECIMAL |
| `FormatControlType` | I/O format: NEWLINE, FORMFEED, TAB, CHARCODE |
| `IndirectionType` | Indirection kind: NAME, SUBSCRIPT, ARGUMENT, PATTERN, UNKNOWN |
| `PassingMode` | Parameter passing: BY_VALUE, BY_REFERENCE, OMITTED |
| `ScopeStrategy` | Label scope model: PURE_FUNCTION, FUNCTION_WITH_OUTPUTS, SUBROUTINE, REQUIRES_RUNTIME |

## Traversal Helpers

In `src/m2py/asg/type_helpers.py`:

- `get_body_scope(stmt)` — returns `stmt.body` if the statement has one (FOR, ELSE, DO block)
- `get_then_scope(stmt)` — returns `stmt.then_scope` if present (IF)
- `get_else_scope(stmt)` — always returns `None` (MUMPS ELSE is a separate command)

These are used by `MScope.walk_statements()` for recursive ASG traversal.
