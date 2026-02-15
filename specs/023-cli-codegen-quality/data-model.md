# Data Model: CLI & Codegen Quality

**Spec**: [spec.md](spec.md) | **Updated**: 2026-02-15

## New Entities

### ExprResultType (Enum)

**Location**: `src/m2py/asg/enums.py` (extends existing enum file)

| Value | Semantics | Python Type Hint |
|-------|-----------|-----------------|
| `STRING` | String result | `str` |
| `NUMERIC` | Integer or decimal result | `int \| Decimal` |
| `BOOLEAN_INT` | 0 or 1 result (MUMPS truth value) | `int` |
| `NUMERIC_STRING` | Formatted number as string ($JUSTIFY, $FNUMBER) | `str` |
| `UNKNOWN` | Cannot determine statically | (no annotation or `Any`) |

**Constraints**: Immutable enum. Must not be `None` after the type inference pass has run — but the `result_type` *field* on `MExpr` defaults to `None` for backward compatibility (pre-inference).

### TranspileResult (Dataclass)

**Location**: `src/m2py/cli/transpile.py`

| Field | Type | Description |
|-------|------|-------------|
| `input_path` | `Path` | Absolute path to source `.m` file |
| `output_path` | `Path \| None` | Absolute path to written `.py` file, or `None` on failure |
| `success` | `bool` | Whether transpilation succeeded |
| `error` | `str \| None` | Error message if `success` is `False` |
| `routine_name` | `str` | Derived routine name (stem of input file, uppercased) |

**Constraints**: `output_path` is `None` iff `success` is `False`. `error` is `None` iff `success` is `True`. `routine_name` follows MUMPS naming: uppercase, max 8 chars (convention, not enforced).

### TranspileSummary (Dataclass)

**Location**: `src/m2py/cli/transpile.py`

| Field | Type | Description |
|-------|------|-------------|
| `results` | `list[TranspileResult]` | All individual file results |
| `total` | `int` | Total files attempted |
| `succeeded` | `int` | Count of successful transpilations |
| `failed` | `int` | Count of failures |

**Derived**: `succeeded + failed == total`. `all_ok` property returns `failed == 0`.

### CLIArgs (Namespace)

**Location**: Returned by `argparse.ArgumentParser.parse_args()` — no custom class needed.

| Attribute | Type | CLI Flag | Default | Description |
|-----------|------|----------|---------|-------------|
| `paths` | `list[str]` | positional | (required) | Input file/directory paths |
| `output` | `str \| None` | `--output` / `-o` | `None` | Output directory |
| `verbose` | `bool` | `--verbose` / `-v` | `False` | Verbose output |
| `no_format` | `bool` | `--no-format` | `False` | Skip ruff lint-fix and formatting |

## Modified Entities

### MExpr (Dataclass) — MODIFY

**Location**: `src/m2py/asg/expressions.py`

**Change**: Add one field:

```python
result_type: Optional[ExprResultType] = None
```

- Populated by the type inference analysis pass
- `None` before inference runs (backward compatible)
- `ExprResultType.UNKNOWN` for genuinely dynamic expressions
- Not set on non-value expressions (`MFormatControl`, `MDeviceControl`)

### GeneratorContext (Dataclass) — MODIFY

**Location**: `src/m2py/codegen/routine.py`

**Change**: The existing `imports: set[str]` field is currently unused. No change to this field is needed — post-generation `ruff check --fix` handles unused import pruning externally.

## Entity Relationships

```
CLIArgs
  └─ drives → transpile_file() / transpile_directory()
       └─ produces → TranspileResult (one per .m file)
            └─ aggregated into → TranspileSummary

MRoutine (existing)
  └─ contains → MLabel[] (existing)
       └─ contains → MScope (existing)
            └─ contains → MStatement[] (existing)
                 └─ contains → MExpr[] (existing)
                      └─ .result_type → ExprResultType (NEW)
```

## Type Inference Mapping

Full mapping from `MExpr` subclass to `ExprResultType`:

| MExpr Subclass | Condition | Result Type |
|----------------|-----------|-------------|
| `MLiteral` | `literal_type == STRING` | `STRING` |
| `MLiteral` | `literal_type == INTEGER` | `NUMERIC` |
| `MLiteral` | `literal_type == DECIMAL` | `NUMERIC` |
| `MVariable` | always | `UNKNOWN` |
| `MGlobal` | always | `UNKNOWN` |
| `MNakedGlobal` | always | `UNKNOWN` |
| `MBinaryOp` | arithmetic (`+`, `-`, `*`, `/`, `\`, `#`, `**`) | `NUMERIC` |
| `MBinaryOp` | string concat (`_`) | `STRING` |
| `MBinaryOp` | comparison (`=`, `<`, `>`, `'=`, `'<`, `'>`, `[`, `]`, `]]`) | `BOOLEAN_INT` |
| `MBinaryOp` | logical (`&`, `!`) | `BOOLEAN_INT` |
| `MUnaryOp` | arithmetic unary (`+`, `-`) | `NUMERIC` |
| `MUnaryOp` | logical not (`'`) | `BOOLEAN_INT` |
| `MPatternMatch` | always | `BOOLEAN_INT` |
| `MIntrinsicFunction` | `$LENGTH`, `$ASCII`, `$FIND`, `$RANDOM`, `$DATA`, `$QLENGTH`, `$INCREMENT` | `NUMERIC` |
| `MIntrinsicFunction` | `$PIECE`, `$EXTRACT`, `$CHAR`, `$TRANSLATE`, `$REVERSE`, `$TEXT`, `$NAME`, `$QUERY`, `$QSUBSCRIPT`, `$ZDATE` | `STRING` |
| `MIntrinsicFunction` | `$JUSTIFY`, `$FNUMBER` | `NUMERIC_STRING` |
| `MIntrinsicFunction` | `$GET`, `$SELECT`, `$ORDER` | `UNKNOWN` |
| `MIntrinsicFunction` | `$STACK` (1-arg) | `NUMERIC` |
| `MIntrinsicFunction` | `$STACK` (2-arg) | `STRING` |
| `MExtrinsicFunction` | always | `UNKNOWN` |
| `MExternalFunction` | always | `UNKNOWN` |
| `MIndirection` | always | `UNKNOWN` |
| `MSpecialVariable` | `$TEST`, `$TLEVEL` | `BOOLEAN_INT` |
| `MSpecialVariable` | `$HOROLOG`, `$JOB`, `$IO`, `$STORAGE`, `$SYSTEM`, `$PRINCIPAL`, `$DEVICE`, `$KEY`, `$NAMESPACE` | `STRING` |
| `MStructuredSystemVariable` | always | `UNKNOWN` |
| `MFormatControl` | N/A (not a value expression) | not set |
| `MDeviceControl` | N/A (not a value expression) | not set |
| `MActualParameter` | wrapped expression | delegates to wrapped expr |

## State Transitions

### TranspileResult Lifecycle

```
File discovered → transpile_file() called
  ├─ Parse succeeds → analyze → generate → lint-fix → format → write → TranspileResult(success=True)
  └─ Any step fails → TranspileResult(success=False, error="...")
```

No mutable state transitions within the result — it is constructed once and immutable.

### MExpr.result_type Lifecycle

```
Parser creates MExpr → result_type = None
Type inference pass runs → result_type = ExprResultType.X
Codegen reads result_type → emits type hints
```

Read-only after inference. Never mutated by codegen.
