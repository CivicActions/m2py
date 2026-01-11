# Analysis Requirements for Code Generation

This document specifies the analysis data that MUST be populated before code generation can proceed.

## Required Analysis Passes

The following analysis passes must be run in order:

1. **`resolve_references(routine)`** - Resolves label and routine references
2. **`analyze_for_loops(routine)`** - Classifies FOR loops and detects modifications
3. **`classify_gotos(routine)`** - Classifies GOTO patterns and loop exits
4. **`analyze_variables(routine)`** - Computes function signatures

## Data Dependencies

### MForStatement Requirements

| Field | Type | Populated By | Required For |
|-------|------|--------------|--------------|
| `loop_type` | `ForLoopType` | Parser/Semantic | Pattern selection |
| `loop_var_modified_in_body` | `bool` | `analyze_for_loops` | while vs for decision |
| `has_internal_quit` | `bool` | `analyze_for_loops` | break generation |
| `has_internal_goto` | `bool` | `classify_gotos` | break generation |
| `exit_points` | `List[MGotoStatement]` | `classify_gotos` | Exit tracking |
| `is_infinite` | `bool` | Parser/Semantic | Pattern selection |

### MGotoStatement Requirements

| Field | Type | Populated By | Required For |
|-------|------|--------------|--------------|
| `goto_type` | `GotoType` | `classify_gotos` | Pattern selection |
| `is_cross_label` | `bool` | `classify_gotos` | Scope determination |
| `exits_loops` | `List[MForStatement]` | `classify_gotos` | Break/exception |
| `target_stmt_index` | `Optional[int]` | `classify_gotos` | Forward restructuring |

**Note on `target_stmt_index`**: For intra-label forward GOTOs (`is_cross_label=False`, `FORWARD_JUMP`),
this field contains the index of the target statement in the label body. Computed from MUMPS offset
semantics: `LABEL+n` targets line n from the label, mapped to statement index via `_find_stmt_index_for_line()`.

**Note on GOTO semantics (MDC 3.6.5)**: GOTO terminates all FOR loops on the line containing the GOTO.
GOTO cannot create Python `continue` semantics. For skip-iteration patterns, MUMPS uses conditional
execution (`I cond <commands>`) or QUIT from DO blocks.

### MQuitStatement Requirements

| Field | Type | Populated By | Required For |
|-------|------|--------------|--------------|
| `exits_for` | `bool` | Parser/Semantic | break vs return |
| `exits_do_block` | `bool` | Parser/Semantic | return generation |
| `return_value` | `Optional[MExpr]` | Parser | Return expression |
| `postcondition` | `Optional[MExpr]` | Parser | Conditional quit |

### FunctionSignature Requirements

| Field | Type | Populated By | Required For |
|-------|------|--------------|--------------|
| `scope_strategy` | `ScopeStrategy` | `analyze_variables` | Code gen approach |
| `formal_params` | `List[str]` | `analyze_variables` | Function signature |
| `byref_outputs` | `Set[str]` | `analyze_variables` | Return tuple |
| `has_value_quit` | `bool` | `analyze_variables` | Return type |
| `requires_runtime_scope` | `bool` | `analyze_variables` | Error detection |

## Validation Before Code Generation

```python
def ensure_analysis_complete(routine: MRoutine) -> None:
    """Verify all analysis has been run before code generation."""
    
    # Check routine-level flags
    if not hasattr(routine, 'references_resolved') or not routine.references_resolved:
        raise ValueError("resolve_references() not run")
    
    if not hasattr(routine, 'for_loops_analyzed') or not routine.for_loops_analyzed:
        raise ValueError("analyze_for_loops() not run")
    
    if not hasattr(routine, 'gotos_classified') or not routine.gotos_classified:
        raise ValueError("classify_gotos() not run")
    
    if not hasattr(routine, 'variables_analyzed') or not routine.variables_analyzed:
        raise ValueError("analyze_variables() not run")
```

## Error Handling

If analysis data is missing:

1. **Fail Fast**: Raise `AnalysisNotCompleteError` with specific missing field
2. **No Defaults**: Never assume default values for analysis data
3. **Clear Messages**: Include which analysis pass needs to run

```python
class AnalysisNotCompleteError(Exception):
    """Raised when code generation is attempted without complete analysis."""
    
    def __init__(self, missing_field: str, required_pass: str):
        super().__init__(
            f"Analysis field '{missing_field}' not set. "
            f"Run {required_pass}() before code generation."
        )
```

## Data Flow Diagram

```
                    ┌─────────────────┐
                    │  MUMPS Source   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │     Parser      │
                    │ (basic fields)  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │resolve_references│
                    │ (label refs)    │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
              ▼              ▼              ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │analyze_for_loops│ │ classify_gotos  │ │analyze_variables│
    │ (FOR fields)    │ │ (GOTO fields)   │ │ (signatures)    │
    └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
              │              │              │
              └──────────────┼──────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Code Generator │
                    │   (Spec 005)    │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Python Output  │
                    └─────────────────┘
```
