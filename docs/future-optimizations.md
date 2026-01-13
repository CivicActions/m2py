# Future Optimizations

This document tracks potential optimizations that were considered but deferred in favor of simpler, correct implementations. These can be revisited once the core transpiler is stable and performance profiling identifies actual bottlenecks.

## Cross-Routine Variable Passing (Static Analysis)

**Current approach** (Spec 008): Pass a `_scope` dictionary to all external calls. All non-NEWed variables are stored in this shared dictionary.

**Potential optimization**: Use the existing variable analysis infrastructure (`MLabel.input_variables`, `output_variables`, `compute_transitive_inputs()`) to:

1. Recursively analyze external routines at transpile-time
2. Determine exactly which variables each external call reads and writes
3. Generate explicit Python function parameters and return values instead of `_scope` dict

**Benefits**:
- Cleaner generated Python: `result = ext2(X, Y)` instead of `ext2(_scope)`
- Better IDE support (type hints, autocomplete)
- Potential performance improvement (dict lookups vs direct variables)

**Why deferred**:
- MUMPS semantics allow any variable to be read/written anywhere
- Indirection (`@VAR`) and XECUTE defeat static analysis
- Callers can pass variables not explicitly declared
- Correctness is more important than aesthetics initially

**Prerequisites to implement**:
- Stable cross-routine calling infrastructure
- Whole-program analysis capability (multi-file transpilation)
- Clear strategy for handling analysis-defeating patterns (fallback to `_scope`)

**Related code**:
- `src/m2py/analysis/variables.py` - existing variable analysis
- `MLabel.input_variables`, `output_variables` - per-label analysis results
- `compute_transitive_inputs()` - call-chain propagation

---

## Conditional $TEXT Source Embedding

**Current approach** (Spec 008): Every generated `.py` file includes `_source_lines = [...]` with the original MUMPS source.

**Potential optimization**: Whole-program analysis to determine which routines are referenced by `$TEXT(^routine)` calls, and only embed source in those routines.

**Benefits**:
- Reduced generated file sizes (typically 1-5KB per routine saved)
- Faster module loading for routines that don't need $TEXT

**Why deferred**:
- VistA routines are typically small, overhead is negligible
- Whole-program analysis requires multi-pass transpilation
- External $TEXT queries (routine A reading B's source) are unpredictable
- "Always correct" beats "optimized but potentially broken"

**Prerequisites to implement**:
- Multi-file transpilation with dependency tracking
- $TEXT reference extraction during parsing
- CLI option to opt-in to optimization (with clear documentation of limitations)

---

## Contributing

When adding optimizations to this document, include:
1. Current approach and its rationale
2. Proposed optimization with concrete benefits
3. Why it was deferred (complexity, correctness risk, etc.)
4. Prerequisites or triggers for revisiting
5. Related code locations
