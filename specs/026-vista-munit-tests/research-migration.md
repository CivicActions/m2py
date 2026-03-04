# Research: M-Unit Migration from vista-test to m2py

**Spec**: 026-vista-munit-tests | **Date**: 2026-03-03  
**Context**: Moving M-Unit test infrastructure from `vista-test/` (separate repo) into `tests/functional/munit/` inside the main m2py repo.

---

## R1: What Must Move from vista-test?

**Question**: Which vista-test files are required for M-Unit tests?

**Decision**: Move the M-Unit library + tests + baselines. Leave RPC/terminal/baseline-capture code behind (only needed for osehravista interaction, not for running transpiled tests).

### Files to move

| Source (vista-test/) | Destination (m2py/) | Lines | Purpose |
|---|---|---|---|
| `src/vista_test/munit/models.py` | `tests/functional/munit/models.py` | 127 | Data models (MUnitResult, BaselineData, etc.) |
| `src/vista_test/munit/parser.py` | `tests/functional/munit/parser.py` | 247 | M-Unit output parser + TestList parser |
| `src/vista_test/munit/adapter.py` | `tests/functional/munit/adapter.py` | 642 | Transpile-and-execute, MUnitTestItem, MUnitCollector |
| `src/vista_test/munit/zish_impl.py` | `tests/functional/munit/zish_impl.py` | 403 | Python %ZISH implementation |
| `tests/vista/munit/conftest.py` | `tests/functional/munit/conftest.py` | 699 | Fixtures, auto-importer, discovery hook |
| `tests/vista/munit/test_self_tests.py` | `tests/functional/munit/test_self_tests.py` | 224 | Tier 1: %utt1–%utt7 + %uttcovr |
| `tests/vista/munit/test_xml_parser.py` | `tests/functional/munit/test_xml_parser.py` | 123 | Tier 2: M XML Parser tests |
| `tests/vista/munit/test_fileman.py` | `tests/functional/munit/test_fileman.py` | 198 | Tier 3: VA FileMan tests |
| `tests/vista/munit/test_dmufinit.py` | `tests/functional/munit/test_dmufinit.py` | 564 | DMUFINIT chain validation |
| `tests/unit/test_munit_parser.py` | `tests/unit/munit/test_munit_parser.py` | 322 | Parser unit tests |
| `tests/unit/test_munit_models.py` | `tests/unit/munit/test_munit_models.py` | 230 | Model serialization tests |
| `baselines/osehravista-baseline.json` | `tests/functional/munit/baselines/osehravista-baseline.json` | 722 | Ground-truth results from live VistA |
| `baselines/globals/*.zwr` | `tests/functional/munit/baselines/globals/*.zwr` | ~11K | ZWR fixture data for FileMan tests |
| `generated/DMUFINIT.py` | `tests/functional/munit/generated/DMUFINIT.py` | ~350 | Pre-transpiled DMUFINIT |

**Total**: ~4,500 lines of Python + ~12K lines of data files

### Files NOT to move

| File | Reason |
|---|---|
| `src/vista_test/munit/baseline.py` | SSH baseline capture — only used to regenerate baseline JSON against live VistA |
| `src/vista_test/munit/__main__.py` | CLI for baseline capture — same reason |
| `src/vista_test/rpc/` | XWB RPC broker — unrelated to transpiled test execution |
| `src/vista_test/terminal/` | SSH terminal driver — unrelated |
| `Dockerfile.test`, `Dockerfile.yottadb` | vista-test's own Docker infrastructure (m2py has its own) |

---

## R2: VistA / VistA-M Data Requirements

**Question**: What specific data from VistA and VistA-M repos is needed, and how should it be obtained?

**Decision**: Download zip archives of VistA and VistA-M rather than using git submodules. Cache by commit hash in GitHub Actions.

### Repo sizes and download considerations

| Repo | Git clone size | ZIP size (est.) | Content needed |
|---|---|---|---|
| WorldVistA/VistA | 372 MB (.git) | ~50-80 MB | TestList files + test `.m` files (< 1 MB actual) |
| WorldVistA/VistA-M | 6.2 GB (.git) | ~200-400 MB | MUMPS routine source files (~50 MB actual) |

### What's actually accessed from each

**VistA (OSEHRA)** — test harness metadata:
- `Packages/*/Testing/MUnit/TestList` — 5 TestList files for package discovery
- `Packages/*/Testing/MUnit/*.m` — 58 test routine `.m` files
- `Packages/VA FileMan/Testing/MUnit/` — DMUFINIT chain for FileMan fixtures

**VistA-M (WorldVistA)** — MUMPS source routines:
- `Packages/MASH Utilities/Routines/*.m` — ~22 files (M-Unit framework + self-tests)
- `Packages/M XML Parser/Routines/*.m` — 13 files (parser library)
- `Packages/VA FileMan/Routines/*.m` — up to 907 files (auto-imported on demand)
- `Packages/Kernel/Routines/*.m` — up to 823 files (auto-imported on demand)
- `Packages/VA FileMan/Globals/*.zwr` — DD, DIC, IX, DIALOG globals

### ZIP download strategy

GitHub archives are available at:
```
https://github.com/{owner}/{repo}/archive/{commit}.zip
```

These extract to `{repo}-{commit}/` directory structure with full repo contents (no `.git` directory), so they're much smaller than git clones.

**Cache key**: Use `vista-{repo}-{commit_hash}` as the cache key. When upstream repos update (new commit hash), the cache misses and a fresh download occurs.

**Refresh strategy**: A scheduled workflow or manual trigger can check for upstream updates and bust the cache. For day-to-day CI, pinning to a known-good commit hash is sufficient.

### Alternative considered: Sparse checkout

Could use `git clone --filter=blob:none --sparse` to only fetch needed paths. Rejected because:
- Still requires git history negotiation (slow for large repos)
- More complex CI setup than `curl + unzip`
- ZIP approach is simpler and well-understood

### Alternative considered: Vendoring only needed files

Could copy just the ~100 needed files into m2py repo. Rejected because:
- Ongoing sync burden when upstream changes
- License considerations (OSEHRA Apache 2.0 / WorldVistA AGPL)
- Loses clear provenance

---

## R3: GitHub Actions Cache Strategy

**Question**: How to implement efficient VistA/VistA-M caching in CI?

**Decision**: Use `actions/cache` with commit-hash-based keys.

### Implementation plan

```yaml
- name: Cache VistA repos
  uses: actions/cache@v4
  id: vista-cache
  with:
    path: |
      .vista-deps/VistA
      .vista-deps/VistA-M
    key: vista-deps-${{ hashFiles('tests/functional/munit/vista-versions.json') }}

- name: Download VistA repos
  if: steps.vista-cache.outputs.cache-hit != 'true'
  run: |
    # Read pinned versions
    VISTA_COMMIT=$(jq -r '.vista' tests/functional/munit/vista-versions.json)
    VISTA_M_COMMIT=$(jq -r '.vista_m' tests/functional/munit/vista-versions.json)

    mkdir -p .vista-deps
    curl -L "https://github.com/WorldVistA/VistA/archive/${VISTA_COMMIT}.zip" -o /tmp/vista.zip
    unzip -q /tmp/vista.zip -d .vista-deps/
    mv ".vista-deps/VistA-${VISTA_COMMIT}" .vista-deps/VistA

    curl -L "https://github.com/WorldVistA/VistA-M/archive/${VISTA_M_COMMIT}.zip" -o /tmp/vista-m.zip
    unzip -q /tmp/vista-m.zip -d .vista-deps/
    mv ".vista-deps/VistA-M-${VISTA_M_COMMIT}" .vista-deps/VistA-M
```

### Version pinning file

```json
// tests/functional/munit/vista-versions.json
{
  "vista": "6c18f1bf98a3c2b33aa0c61ced6282a42c72e1aa",
  "vista_m": "b7aecb9029f9bb8639a7bfa63b635469065ab44d",
  "updated": "2026-03-03"
}
```

When either commit hash changes, the cache key changes, forcing a fresh download. The `hashFiles()` function hashes the version file contents.

### Cache size estimate

| Item | Compressed (ZIP) | Extracted |
|---|---|---|
| VistA archive | ~60 MB | ~200 MB |
| VistA-M archive | ~300 MB | ~1 GB |
| **Total cached** | N/A | **~1.2 GB** |

GitHub Actions cache limit is 10 GB per repo, so this is well within bounds.

---

## R4: Import Path Refactoring

**Question**: How do imports need to change when moving from vista-test to m2py?

**Decision**: Replace `vista_test.munit.*` imports with relative imports within `tests/functional/munit/`.

### Current import pattern (vista-test)

```python
from vista_test.munit.models import MUnitResult, BaselineData
from vista_test.munit.parser import parse_munit_output, parse_testlist
from vista_test.munit.adapter import MUnitCollector, transpile_and_execute
```

### New import pattern (m2py)

```python
# Within tests/functional/munit/ — use relative imports
from .models import MUnitResult, BaselineData
from .parser import parse_munit_output, parse_testlist
from .adapter import MUnitCollector, transpile_and_execute
```

Or absolute from test root:
```python
from tests.functional.munit.models import MUnitResult, BaselineData
```

### Path constants refactoring

The conftest.py currently derives paths from `vista-test/` project root:
```python
_PROJECT_ROOT = Path(__file__).resolve().parents[3]  # vista-test/
_VISTA_M_DIR = _PROJECT_ROOT / "VistA-M"
_VISTA_SUBMODULE = _PROJECT_ROOT / "VistA"
```

After migration, these become:
```python
_REPO_ROOT = Path(__file__).resolve().parents[3]  # /workspaces/m2py/
_VISTA_DEPS = _REPO_ROOT / ".vista-deps"  # or env var
_VISTA_DIR = _VISTA_DEPS / "VistA"
_VISTA_M_DIR = _VISTA_DEPS / "VistA-M"
_BASELINES_DIR = Path(__file__).parent / "baselines"
```

The `.vista-deps/` directory is gitignored and populated by CI cache or a local setup script.

---

## R5: Integration with Existing CI

**Question**: How should munit tests fit into the existing CI matrix?

**Decision**: Add a new `munit` split to the CI matrix, running only on `inmemory` backend initially.

### Current CI matrix

13 test jobs = 3 backends × 5 splits - 2 exclusions:
- Backends: inmemory, yottadb, iris
- Splits: unit, functional-mvts, functional-other, slow, quality

### Proposed addition

Add `munit` split running on `inmemory` backend:
- New job: `test (inmemory, munit)`
- Pytest args: `tests/functional/munit/ -m "not slow"` (fast tier)
- Slow munit: merged into existing `slow` split or separate `munit-slow`

### Why inmemory only (initially)?

- M-Unit tests exercise transpiled MUMPS which uses the m2py runtime
- The global store backend doesn't matter for most M-Unit tests (they use `^TMP($J)`)
- FileMan tests (Tier 3+) could benefit from YDB backend later
- Starting simple, expand when proven

### Timeout

- Tier 1+2 (12 routines): ~2-5 minutes
- Tier 3 (FileMan): ~5-10 minutes
- Timeout: 20 minutes (matches existing functional splits)

---

## R6: Local Development Setup

**Question**: How do developers run munit tests locally without CI?

**Decision**: Provide a setup script that downloads VistA/VistA-M zips (or symlinks to existing vista-test submodules).

### Option A: Download script (CI-compatible)

```bash
# utils/setup-vista-deps.sh
# Downloads VistA and VistA-M archives to .vista-deps/
uv run python tests/functional/munit/setup_deps.py
```

### Option B: Symlink to existing vista-test (for developers who already have it)

```bash
ln -s vista-test/VistA .vista-deps/VistA
ln -s vista-test/VistA-M .vista-deps/VistA-M
```

### Environment variable override

```bash
# Point to existing checkouts
VISTA_DIR=/path/to/VistA VISTA_M_DIR=/path/to/VistA-M uv run pytest tests/functional/munit/
```

The conftest.py should check for env vars first, then `.vista-deps/`, then skip gracefully if neither exists:

```python
_VISTA_DIR = Path(os.environ.get("VISTA_DIR", _REPO_ROOT / ".vista-deps" / "VistA"))
_VISTA_M_DIR = Path(os.environ.get("VISTA_M_DIR", _REPO_ROOT / ".vista-deps" / "VistA-M"))

if not _VISTA_M_DIR.exists():
    pytest.skip("VistA-M not available; run utils/setup-vista-deps.sh", allow_module_level=True)
```

---

## R7: Reuse of Existing m2py Infrastructure

**Question**: What existing m2py infrastructure can be reused?

**Decision**: Reuse YDB Docker integration, functional test patterns, and conftest utilities.

### Reusable infrastructure

| m2py Component | Reuse in M-Unit | Notes |
|---|---|---|
| `Dockerfile.yottadb` + `utils/ydb.sh` | Run munit tests with YDB backend | No changes needed |
| `tests/functional/conftest.py` fixtures | Pattern for `run_mumps()`, output comparison | Different approach (M-Unit) but same runtime |
| `src/m2py/runtime/` | Full runtime used by transpiled code | Already a dependency |
| `src/m2py/codegen/` | `generate_python()` for transpilation | Already a dependency |
| `utils/validate.py` | Debug individual routines | Useful for development |
| `utils/run_mumps_ydb.py` | Generate reference output for specific routines | Already available |
| CI workflow patterns | Docker caching, matrix setup | Extend existing `ci.yml` |

### Not reusable (must be ported)

| Component | Reason |
|---|---|
| `MumpsAutoImporter` | vista-test specific paths; must update for new layout |
| `conftest.py` fixtures | Path constants, fixture chain need redesign |
| `MUnitCollector` | TestList discovery paths need update |

---

## R8: pytest Marker and Skip Strategy

**Question**: How should munit tests be marked and skipped?

**Decision**: Use `@pytest.mark.munit` marker + `@pytest.mark.slow` for expensive tiers. Auto-skip when VistA deps are missing.

### Markers

```python
@pytest.mark.munit       # All M-Unit tests
@pytest.mark.slow         # Tiers that take > 10s
@pytest.mark.munit_tier1  # MASH Utilities self-tests
@pytest.mark.munit_tier2  # M XML Parser
@pytest.mark.munit_tier3  # VA FileMan
@pytest.mark.munit_tier4  # Problem List, Scheduling, Registration
```

### Skip behavior

- If `.vista-deps/` is missing → entire munit directory skipped with clear message
- If specific package directory is missing → individual test skipped
- In CI: deps always available (cached/downloaded)
- Locally: skip is the safe default unless developer sets up deps
