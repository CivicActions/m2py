# Quickstart: VistA M-Unit Test Suite via pytest

**Spec**: 026-vista-munit-tests | **Branch**: `026-vista-munit-tests`

## Prerequisites

- Docker (for osehravista container)
- uv (Python package manager)
- m2py workspace at `/workspaces/m2py/`

## Setup

```bash
# 1. Ensure you're on the feature branch
cd /workspaces/m2py
git checkout 026-vista-munit-tests

# 2. Sync m2py dependencies
uv sync

# 3. Sync vista-test dependencies (includes m2py as path dep)
cd vista-test
uv sync
```

## Phase 0a: Capture osehravista Baseline

```bash
# 1. Start osehravista Docker container
docker pull worldvista/osehravista
docker run -d --name osehravista -p 2222:22 -p 9430:9430 worldvista/osehravista

# 2. Wait for osehravista to initialize (~30 seconds)
sleep 30

# 3. Run baseline capture (all packages)
cd /workspaces/m2py/vista-test
uv run python -m vista_test.munit.baseline --output baselines/osehravista-baseline.json

# 4. Run baseline for specific tier
uv run python -m vista_test.munit.baseline --tier 1 --output baselines/osehravista-baseline.json

# 5. Inspect results
uv run python -c "
import json
with open('baselines/osehravista-baseline.json') as f:
    data = json.load(f)
for pkg, info in data['packages'].items():
    total = len(info['routines'])
    passed = sum(1 for r in info['routines'].values() if r['status'] == 'pass')
    print(f'{pkg}: {passed}/{total} pass')
"
```

## Phase 0b: Run Transpiled M-Unit Tests

```bash
# Run all M-Unit tests (discovers from TestList files)
cd /workspaces/m2py/vista-test
uv run pytest tests/vista/munit/ -v

# Run only Tier 1 (M-Unit self-tests)
uv run pytest tests/vista/munit/ -v -k "mash_utilities"

# Run only Tier 2 (M XML Parser)
uv run pytest tests/vista/munit/ -v -k "m_xml_parser"

# Run with extra debug output
uv run pytest tests/vista/munit/ -v --tb=long
```

## Expected Output

```
tests/vista/munit/test_munit_utt1.py PASSED
tests/vista/munit/test_munit_utt2.py PASSED
tests/vista/munit/test_munit_utt3.py PASSED
tests/vista/munit/test_munit_utt4.py PASSED
tests/vista/munit/test_munit_utt5.py PASSED
tests/vista/munit/test_munit_utt6.py PASSED
tests/vista/munit/test_munit_utt7.py PASSED
tests/vista/munit/test_munit_MXMLBLD.py PASSED
tests/vista/munit/test_munit_MXMLDOMT.py PASSED
tests/vista/munit/test_munit_MXMLPATT.py PASSED
tests/vista/munit/test_munit_MXMLTMPT.py PASSED
```

## Running m2py Unit Tests (for transpiler/runtime fixes)

```bash
# From workspace root
cd /workspaces/m2py
uv run pytest tests/ -x
```

## Key Directories

```
vista-test/
├── src/vista_test/munit/       # M-Unit support modules
│   ├── models.py               # Data classes
│   ├── parser.py               # Output parser
│   ├── baseline.py             # osehravista baseline runner
│   └── adapter.py              # pytest adapter
├── tests/
│   ├── unit/                   # Unit tests for parser, models
│   └── vista/munit/            # M-Unit pytest tests + conftest
├── baselines/                  # Committed osehravista baseline JSON
└── VistA/                      # Submodule (read-only)

src/m2py/                       # Transpiler (fixes go here)
tests/                          # m2py standalone tests (fixes go here)
```
