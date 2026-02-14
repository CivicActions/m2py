# System Architecture

## Pipeline Overview

```
MUMPS Source (.m)
       │
       ▼
┌─────────────────────────────────────────────────────┐
│  GRAMMAR (grammar/)                                 │
│  Four textX grammar files define MUMPS syntax       │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────┐
│  PARSER (parser/)                                   │
│  Two-layer parsing: routine structure, then lines   │
│  SemanticAnalyzer transforms textX CST → ASG nodes  │
└──────────────────────┬──────────────────────────────┘
                       │ MRoutine (ASG)
                       ▼
┌─────────────────────────────────────────────────────┐
│  ANALYSIS (analysis/)                                │
│  Multi-pass enrichment: references → GOTOs → FOR     │
│  → quit context → variables → signatures             │
└──────────────────────┬──────────────────────────────┘
                       │ Enriched MRoutine
                       ▼
┌─────────────────────────────────────────────────────┐
│  CODEGEN (codegen/)                                  │
│  Strategy selection → Python source generation       │
│  SIMPLE_FUNCTIONS or TRAMPOLINE pattern              │
└──────────────────────┬──────────────────────────────┘
                       │ Python source
                       ▼
┌─────────────────────────────────────────────────────┐
│  RUNTIME (runtime/) + CORE (core/)                   │
│  Execution support: MArray, MUMPSRuntime, globals,   │
│  devices, helpers, shared value semantics            │
└─────────────────────────────────────────────────────┘
```

## Key Architectural Principle

**ASG-first design**: Analysis passes enrich the ASG with semantic information (GOTO classifications, loop types, variable flow, scope strategies). Code generation only *reads* these pre-computed fields — it never recomputes semantic information. If codegen discovers a missing analysis result, the fix belongs in the analysis layer, not codegen.

## Package Responsibilities

### `grammar/` — textX Grammar Files

Four textX grammar files define MUMPS syntax:

| File | Scope |
|------|-------|
| `mumps.tx` | Routine structure: labels, lines, formal parameter lists |
| `line.tx` | Line content: whitespace, command sequences, comments |
| `commands.tx` | All MUMPS commands (~60) with case-insensitive matching |
| `expressions.tx` | Expressions: operators, functions, variables, literals, indirection |

MUMPS has **no operator precedence** — all binary operators evaluate strictly left-to-right. The expression grammar reflects this by chaining `UnaryExpr → BinaryOpTail*` without precedence levels.

### `parser/` — Two-Layer Parsing

Parsing uses a two-layer architecture for error tolerance:

1. **Layer 1** (`mumps.tx` via textX): Parses routine structure — labels, formal parameters, and raw line content strings. Individual lines that fail to parse don't prevent the rest of the routine from being processed.

2. **Layer 2** (`line.tx`/`commands.tx`/`expressions.tx`): For each line's raw content, parses commands and expressions into textX CST nodes.

After textX parsing, `SemanticAnalyzer.analyze_command()` transforms each textX CST command into a fully-typed ASG statement node (`MStatement` subclass). This is where textX wrapper nodes are unwrapped, expression trees are built, `MCall` references are created for DO/GOTO targets, and pattern matches are compiled to regex.

Key classes:
- `MUMPSParser` — orchestrates parsing and delegates to analysis functions
- `SemanticAnalyzer` — CST-to-ASG transformation
- `compile_mumps_line()` (`compiler.py`) — self-contained parse pipeline for XECUTE, so codegen doesn't import parser/analysis internals directly

### `asg/` — Abstract Semantic Graph

Pure data model — Python dataclasses representing MUMPS program structure. No behavior beyond tree traversal helpers. See [asg-reference.md](asg-reference.md) for details.

The ASG root is `MRoutine`, containing `MLabel` nodes, each with a `MScope` body of `MStatement` nodes. Expressions are `MExpr` subtypes. Cross-references (`MCall`) link GOTO/DO targets to their `MLabel` definitions.

### `analysis/` — Multi-Pass Analysis

Six analysis passes run in sequence after parsing. Order matters — later passes depend on results from earlier ones:

| Pass | Function | Enriches |
|------|----------|----------|
| 1. Reference resolution | `resolve_references()` | `MCall.target`, `MCall.is_resolved`, `MLabel.callers/goto_sources` |
| 2. GOTO classification | `classify_gotos()` | `MGotoStatement.goto_type/codegen_pattern`, `MRoutine.needs_trampoline` |
| 3. FOR analysis | `analyze_for_loops()` | `MForStatement.loop_type`, loop variable modification detection |
| 4. QUIT context | `analyze_quit_context()` | `MQuitStatement.exits_for/exits_do_block` |
| 5. Variable analysis | `analyze_variables()` | `MLabel.input_variables/output_variables`, scope strategy |
| 6. Signature computation | `compute_signatures()` | `MLabel.signature` (FunctionSignature), `MRoutine.routine_state_vars` |

Additional analysis:
- `PatternCompiler` converts MUMPS pattern match syntax to Python regex during semantic analysis (pass 0, integrated into parsing)
- Fallthrough detection identifies labels that flow into the next label without explicit exit

### `codegen/` — Python Code Generation

Translates the enriched ASG into executable Python. See [codegen.md](codegen.md) for full details.

Two strategies are automatically selected based on ASG analysis flags:

- **SIMPLE_FUNCTIONS**: Labels become plain Python functions. Variables live in a `_scope` dict. Used when there are no cross-label GOTOs or computed offsets.
- **TRAMPOLINE**: Labels return `(next_label, state)` tuples dispatched by a `while` loop. A `RoutineState` dataclass carries variables across label boundaries. Prevents stack overflow for cyclic GOTO patterns.

Key files: `routine.py` (module structure), `statements.py` (~6800 lines, all statement types), `expressions.py` (~2600 lines, all expression types), `var_access.py` (3-way variable access dispatch), `indirection.py` (@ expressions and XECUTE), `shared_state.py` (RoutineState generation).

### `runtime/` — Execution Support

The runtime library imported by generated Python code. See [runtime.md](runtime.md) for full details.

- `MArray` — MUMPS hierarchical sparse arrays (each node has both a value AND children)
- `MUMPSRuntime` — central runtime instance: I/O, global variables, indirection resolution, XECUTE compilation, error handling, stack frames, intrinsic special variables
- `GlobalStorageBackend` — pluggable global storage (`InMemoryGlobalStorage` default, `SQLiteGlobalStorage` for cross-process JOB/LOCK)
- Device layer — `PrincipalDevice` (stdin/stdout), `FileDevice`, `TCPDevice`
- JOB subprocess support via `job_runner.py`

### `core/` — Shared Foundation

Canonical implementations of MUMPS semantics shared identically by both compile-time codegen and runtime. This layer was created (spec 018–019) to break backward imports from runtime→codegen.

| Module | Purpose |
|--------|---------|
| `values.py` | `m_str()`, `m_num()`, `m_truth()`, `m_compare()`, `mumps_canonical_str()` |
| `names.py` | `NameTranslator` — bidirectional MUMPS↔Python name mapping |
| `subscripts.py` | `SubscriptCanonicalizer` — canonical subscript forms per MUMPS spec |
| `scope.py` | `CurrentScope` — unified variable access abstraction |
| `indirection.py` | `IndirectionResolver` — runtime `@`-expression resolution |
| `tokenizer.py` | `split_at_toplevel()` — delimiter splitting respecting nesting and quotes |
| `parsing.py` | `parse_subscripted_name()` — parse `ARR(1,2)` to `('ARR', ['1', '2'])` |
| `exceptions.py` | `LVUNDEFError` (M6), `VarExpectedError` |

### `cli/` — Command-Line Interface

Minimal placeholder. The primary CLI entry points are the utility scripts in `utils/`.

## Design Decisions

### Why textX?

The previous approach using YottaDB opcodes failed due to difficulty with sequential processing of compiler IR, constant folding, and complex control flow reconstruction. textX provides a declarative grammar-to-model transformation that directly produces structured ASG nodes, making the parser maintainable and the CST-to-ASG transformation straightforward.

### Why Trampoline over State Machine?

Both patterns were prototyped for cross-label GOTO handling (spec 006). The trampoline pattern was selected because:
- Better testability — each label is an independent function
- Better refactorability — labels can be extracted, inlined, or composed
- Clearer control flow — the dispatch loop is a simple `while` with a dictionary lookup
- The state machine approach had fewer lines but was harder to test in isolation

### Why a Shared `core/` Layer?

Early in development, the runtime module imported codegen utilities for name translation and subscript handling, creating a backward dependency (runtime→codegen). Spec 018–019 extracted these shared concerns into `core/`, establishing a clean dependency direction: both codegen and runtime depend on core, but never on each other.
