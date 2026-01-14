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
- 008-external-calls: Added Python 3.10+ (per pyproject.toml) + extX (grammar/parser), importlib (dynamic module loading)
- 008-external-calls: Added Python 3.10+ (per pyproject.toml) + extX (grammar/parser), importlib (dynamic module loading)
- 007-computed-offsets: Added Python 3.10+ + extX (parser), pytest (testing), dataclasses (ASG/codegen)


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
