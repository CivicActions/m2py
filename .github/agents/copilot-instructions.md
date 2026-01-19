# m2py Development Guidelines

Auto-generated from all feature plans. Last updated: 2025-12-19

## Active Technologies
- Python 3.10+ + extX (grammar/parsing), pytest (testing) (001-textx-semantic-graph)
- N/A (in-memory ASG only) (001-textx-semantic-graph)
- Python 3.10+ + pytest, textX 4.0+ (002-spec-unit-test-organization)
- N/A (test reorganization only) (002-spec-unit-test-organization)
- Python 3.10+ + pytest, textX, pytest-cov (003-complete-stub-tests)
- N/A (test files only) (003-complete-stub-tests)
- Python 3.10+ + pytest, textX, pytest-cov, pytest-xdis (003-complete-stub-tests)
- Python 3.10+ + extX (parser), pytest (testing) (004-minimal-codegen)
- N/A - in-memory code generation (004-minimal-codegen)
- Python 3.10+ (target output); textX for parser + extX (parsing), itertools (FOR codegen), pytest (testing) (005-structured-control-flow)
- N/A (transpiler, no persistence) (005-structured-control-flow)
- Python 3.10+ + extX (parsing), pytest (testing), uv (package management) (006-cross-label-control-flow)
- Python 3.10+ + extX (parser), pytest (testing), dataclasses (ASG/codegen) (007-computed-offsets)
- Python 3.10+ (per pyproject.toml) + extX (grammar/parser), importlib (dynamic module loading) (008-external-calls)
- In-memory module cache (dict), source lines stored per MRoutine (008-external-calls)
- InMemoryGlobalStorage (default), YottaDB/IRIS backends (future) (009-globals-lhs-functions)
- Python 3.10+ + extX (parser), pytest (testing), MArray (Spec 009), GlobalStorageBackend (Spec 009) (010-intrinsic-functions)
- InMemoryGlobalStorage for tests (Spec 009) (010-intrinsic-functions)
- Python 3.10+ + extX (parser), pytest (testing), MArray (Spec 009), pattern_compiler (analysis) (011-operators-commands-completion)
- Python 3.10+ (per pyproject.toml) + extX (grammar/parser), existing m2py codegen pipeline (012-indirection-xecute)
- `_scope` dict for variable access, `_rt` for runtime state (012-indirection-xecute)
- Python 3.10+ + extX (parser), pytest (testing), yottadb (YDB backend via YDBPython) (013-test-consolidation)
- Database abstraction layer with Memory (testing), YottaDB (production), IRIS (future) backends (013-test-consolidation)

- (001-textx-semantic-graph)

## Project Structure

```text
backend/
frontend/
tests/
```

## Commands

# Add commands for 

## Code Style

: Follow standard conventions

## Recent Changes
- 013-test-consolidation: Added Python 3.10+ + extX (parser), pytest (testing), yottadb (YDB backend via YDBPython)
- 012-indirection-xecute: Added Python 3.10+ (per pyproject.toml) + extX (grammar/parser), existing m2py codegen pipeline
- 011-operators-commands-completion: Added Python 3.10+ + extX (parser), pytest (testing), MArray (Spec 009), pattern_compiler (analysis)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
