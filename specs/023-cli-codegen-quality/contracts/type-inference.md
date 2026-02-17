# Type Inference Contract

**Type**: Analysis pass (read-only ASG annotation)  
**Location**: `src/m2py/analysis/type_inference.py`  
**Pipeline position**: After `compute_signatures` (step 6), as step 7

## Public API

### `infer_expression_types(routine: MRoutine) -> None`

Walk all `MExpr` nodes in the routine's ASG and populate `result_type` with the appropriate `ExprResultType` value.

**Preconditions**:
- All prior analysis passes (resolution, scoping, signatures) have completed
- `MExpr.result_type` is `None` for all nodes

**Postconditions**:
- Every `MExpr` subclass that represents a value expression has `result_type` set to a non-`None` `ExprResultType`
- Non-value expressions (`MFormatControl`, `MDeviceControl`) retain `result_type = None`
- `MActualParameter` delegates to its wrapped expression

**Side effects**: Mutates `result_type` field on `MExpr` nodes. No other ASG modifications.

**Error handling**: Never raises. Unknown or unrecognized expressions get `ExprResultType.UNKNOWN`.

## Inference Rules

See [data-model.md](../data-model.md#type-inference-mapping) for the complete mapping table.

### Key Design Decisions

1. **No recursive fixpoint**: MUMPS operator output types depend only on the operator, not operand types. A single bottom-up pass suffices.
2. **Variables are UNKNOWN**: MUMPS variables can be retyped across assignments. Variable-level type tracking is future work.
3. **$STACK is polymorphic**: 1-arg → NUMERIC, 2-arg → STRING. Dispatch based on argument count.
4. **$SELECT is UNKNOWN**: Heterogeneous return values make static typing impossible.

## Integration with Codegen

The codegen layer reads `result_type` to:
1. Emit type annotations on function return types where all QUIT expressions share a type
2. Emit type annotations on simple `SET` assignments where the RHS type is known
3. Skip annotation when `result_type` is `UNKNOWN` or `None` (backward compatible)
