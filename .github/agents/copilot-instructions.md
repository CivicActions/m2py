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
- N/A (codegen focus) (014-xfail-elimination)
- Python 3.10+ + extX (parser), pytest (testing), coverage.py (015-transpilation-coverage-completion)
- Python 3.10+ + pytest, textX (existing m2py deps) (016-functional-test-suite)
- N/A (in-memory global storage via m2py runtime) (016-functional-test-suite)
- N/A (transpiler, no persistence except global variables via runtime) (017-ydb-test-failures)
- Python 3.10+ + textX (parser), pytest (testing), uv (package management) (018-unified-variable-system)
- MArray (in-memory sparse tree), globals database (MState.globals) (018-unified-variable-system)
- In-memory globals (MArray), filesystem for test routines (017-ydb-test-failures)
- Python 3.10+ + textX ≥4.0 (parser), pytest ≥7.0 (testing) (020-codegen-refactoring)
- N/A (transpiler — no persistent storage) (020-codegen-refactoring)
- Python 3.10+ + textX ≥ 4.0 (parser), `copy` (stdlib, deepcopy for transactions), `subprocess` (stdlib, ZSYSTEM), `glob`/`pathlib` (stdlib, $ZSEARCH), `importlib` (stdlib, ZLINK — already used), `datetime` (stdlib, $ZDATE) (021-correctness-features)
- N/A (in-memory global storage, no persistence changes) (021-correctness-features)
- Python 3.10+ + textX (parser), sqlite3 (stdlib — shared storage), subprocess (stdlib — JOB) (022-large-architecture)
- SQLite file-backed database (WAL mode) for cross-process globals and lock table (022-large-architecture)
- Python 3.10+ (constitution constraint; runtime uses 3.10) + textX 4.0+ (parser), argparse (CLI, stdlib), ruff 0.15+ (lint/format), pyright 1.1.408+ (type check) (023-cli-codegen-quality)
- File system (`.m` input → `.py` output) (023-cli-codegen-quality)
- Python 3.10+ (generated code must be valid on 3.10; transpiler itself runs on 3.10+) + textX (parser), pytest (testing), uv (package management) (024-vista-transpilation-fixes)
- SQLite-backed global storage (existing `sqlite_storage.py`) (024-vista-transpilation-fixes)

- (001-textx-semantic-graph)

## Recent Changes
- 024-vista-transpilation-fixes: Added Python 3.10+ (generated code must be valid on 3.10; transpiler itself runs on 3.10+) + textX (parser), pytest (testing), uv (package management)
- 023-cli-codegen-quality: Added Python 3.10+ (constitution constraint; runtime uses 3.10) + textX 4.0+ (parser), argparse (CLI, stdlib), ruff 0.15+ (lint/format), pyright 1.1.408+ (type check)
- 022-large-architecture: Added Python 3.10+ + textX (parser), sqlite3 (stdlib — shared storage), subprocess (stdlib — JOB)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
