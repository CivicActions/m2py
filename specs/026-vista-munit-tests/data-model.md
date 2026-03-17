# Data Model: VistA M-Unit Test Suite via pytest

**Spec**: 026-vista-munit-tests | **Date**: 2025-07-22

## Entities

### 1. MUnitResult

Structured result from parsing M-Unit output for a single routine execution.

```python
@dataclass
class MUnitResult:
    """Parsed result of a single M-Unit test routine execution."""
    routine: str                      # e.g. "%utt1", "MXMLBLD"
    package: str                      # e.g. "MASH Utilities", "M XML Parser"
    total_tests: int                  # Total assertion count from summary
    failures: int                     # Failure count from summary
    errors: int                       # Error count from summary
    entry_tags: int                   # Number of entry tags (test methods) run
    routines_ran: int                 # Number of routines in the run (usually 1)
    status: Literal["pass", "fail", "error", "timeout", "skip"]
    failure_details: list[FailureDetail]  # Individual failure/error records
    raw_output: str                   # Full captured output text
    duration_seconds: float | None    # Wall-clock execution time
    error_message: str | None         # High-level error (timeout, crash, etc.)
```

**Validation rules**:
- `total_tests >= 0`, `failures >= 0`, `errors >= 0`
- `failures + errors <= total_tests` (failures and errors are subsets)
- `status == "pass"` iff `failures == 0 and errors == 0 and total_tests > 0`
- `status == "fail"` iff `failures > 0 or errors > 0`
- `status == "error"` if no summary line could be parsed (partial output)
- `status == "timeout"` if routine exceeded execution timeout
- `status == "skip"` if routine was intentionally not run

### 2. FailureDetail

Individual failure or error record within a routine execution.

```python
@dataclass
class FailureDetail:
    """One failure or error within a routine execution."""
    entry_tag: str               # e.g. "T1", "START"
    routine: str                 # e.g. "%utt1", "MXMLBLD"
    test_name: str               # Description from @TEST annotation or XTENT
    message: str                 # Assertion message or error text
    kind: Literal["failure", "error"]  # Assertion failure vs runtime error
    expected: str | None         # For CHKEQ: expected value
    actual: str | None           # For CHKEQ: actual value
```

**Validation rules**:
- `entry_tag` and `routine` must be non-empty
- `kind == "failure"` for CHKTF/CHKEQ assertion failures
- `kind == "error"` for runtime errors (caught by `$ETRAP`)
- `expected`/`actual` are only set for `CHKEQ` failures, `None` for `CHKTF`

### 3. BaselineData

Top-level container for VistA baseline results, serialized to JSON.

```python
@dataclass
class BaselineData:
    """Complete VistA baseline for all M-Unit test routines."""
    version: str                      # Schema version, e.g. "1.0"
    captured_at: str                  # ISO 8601 timestamp
    docker_image: str                 # Docker image tag, e.g. "worldvista/osehravista:latest"
    packages: dict[str, PackageBaseline]  # Keyed by package name
```

### 4. PackageBaseline

Per-package section of the baseline.

```python
@dataclass
class PackageBaseline:
    """Baseline results for one VistA package's M-Unit tests."""
    package_name: str                 # e.g. "M XML Parser"
    test_list_path: str               # Relative path to TestList file
    routines: dict[str, MUnitResult]  # Keyed by routine name
```

### 5. TestRoutineConfig

Configuration for a single test routine, derived from TestList files.

```python
@dataclass
class TestRoutineConfig:
    """Configuration for running one M-Unit test routine."""
    routine_name: str             # e.g. "MXMLBLD", "%utt1"
    package_name: str             # e.g. "M XML Parser"
    invocation: str               # e.g. "D TEST^MXMLBLD", "D ^%utt1"
    source_path: str              # Path to .m file in VistA submodule
    tier: int                     # 1=self-tests, 2=XML, 3=FileMan, 4=clinical
    dependencies: list[str]       # Other routines that must be transpiled
```

**Validation rules**:
- `invocation` must match pattern `D\s+(\w+\^)?\w+`
- `source_path` must exist in the VistA submodule
- `tier` in {1, 2, 3, 4}

## Relationships

```
BaselineData
└── packages: dict[str, PackageBaseline]
    └── routines: dict[str, MUnitResult]
        └── failure_details: list[FailureDetail]

TestRoutineConfig  ←→  MUnitResult  (linked by routine_name + package_name)
```

## State Transitions

### MUnitResult.status

```
                    ┌─────────────────┐
                    │   not_started    │
                    └────────┬────────┘
                             │ routine begins execution
                    ┌────────▼────────┐
                    │    running       │
                    └────────┬────────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
   ┌────────▼──────┐  ┌─────▼─────┐  ┌──────▼───────┐
   │   pass        │  │   fail    │  │   error      │
   │ (0 fail/err)  │  │ (>0 fail) │  │ (no summary) │
   └───────────────┘  └───────────┘  └──────────────┘
                                            │
                                     ┌──────▼───────┐
                                     │   timeout    │
                                     │ (exceeded)   │
                                     └──────────────┘
```

## JSON Schema: baseline.json

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VistA M-Unit Baseline",
  "type": "object",
  "required": ["version", "captured_at", "docker_image", "packages"],
  "properties": {
    "version": { "type": "string", "const": "1.0" },
    "captured_at": { "type": "string", "format": "date-time" },
    "docker_image": { "type": "string" },
    "packages": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "required": ["package_name", "test_list_path", "routines"],
        "properties": {
          "package_name": { "type": "string" },
          "test_list_path": { "type": "string" },
          "routines": {
            "type": "object",
            "additionalProperties": {
              "type": "object",
              "required": ["routine", "package", "total_tests", "failures", "errors", "status"],
              "properties": {
                "routine": { "type": "string" },
                "package": { "type": "string" },
                "total_tests": { "type": "integer", "minimum": 0 },
                "failures": { "type": "integer", "minimum": 0 },
                "errors": { "type": "integer", "minimum": 0 },
                "entry_tags": { "type": "integer", "minimum": 0 },
                "routines_ran": { "type": "integer", "minimum": 0 },
                "status": { "enum": ["pass", "fail", "error", "timeout", "skip"] },
                "failure_details": {
                  "type": "array",
                  "items": {
                    "type": "object",
                    "required": ["entry_tag", "routine", "test_name", "message", "kind"],
                    "properties": {
                      "entry_tag": { "type": "string" },
                      "routine": { "type": "string" },
                      "test_name": { "type": "string" },
                      "message": { "type": "string" },
                      "kind": { "enum": ["failure", "error"] },
                      "expected": { "type": ["string", "null"] },
                      "actual": { "type": ["string", "null"] }
                    }
                  }
                },
                "raw_output": { "type": "string" },
                "duration_seconds": { "type": ["number", "null"] },
                "error_message": { "type": ["string", "null"] }
              }
            }
          }
        }
      }
    }
  }
}
```

## Tier Classification

| Tier | Package | Routines | Assertions | Global Dependencies | Priority |
|------|---------|----------|------------|-------------------|----------|
| 1 | MASH Utilities (self-tests) | %utt1–%utt7, %uttcovr (8) | ~28 | `^TMP($J)` only | P1 — MVP |
| 2 | M XML Parser | MXMLBLD, MXMLDOMT, MXMLPATT, MXMLTMPT (4) | ~96 | `^TMP($J)`, file I/O (`%ZISH` for MXMLDOMT) | P1 — MVP |
| 3 | VA FileMan | ZZUTDIDT, DMUDIC00, DMUDT000, DMUDTC00, DMUDIQ00 (5) | ~174 | `^DD`, `^DIC`, `%ZISH`, `DMUFINIT` fixtures | Stretch |
| 4a | Problem List | ZZRGUT–ZZRGUT5, ZZRGUTRB, ZZRGUTEX (8) | ~349 | `^AUPNPROB`, `^GMPL*`, `^SC`, patient data | Stretch |
| 4b | Scheduling | ZZUTGETAPPT, ZZUTNEXTAPPT, ZZUTSDAPI, ZZUTSDIMO, ZZUTGETPLIST, ZZUTPATAPPT, ZZRGUSD1–ZZRGUSD6 (12) | ~547 | `^DPT`, `^SC`, `^SD*`, clinic/appointment data | Stretch |
| 4c | Registration | ZZDGPTCO1 (1) | ~10 | `^DG*`, `^DICRW`, patient data | Stretch |

### Totals

| Scope | Routines | Assertions |
|-------|----------|------------|
| MVP (Tier 1+2) | 12 | ~124 |
| + Tier 3 (FileMan) | 17 | ~298 |
| + Tier 4 (all) | 38 | ~1,204 |
| **Full (all tiers)** | **38** | **~1,204** |

### Routine-Level Assertion Breakdown

#### Tier 1 — MASH Utilities Self-Tests
| Routine | Assertions | Dependencies | Risk |
|---------|-----------|-------------|------|
| %utt1 | 2 | `%ut` only | Minimal |
| %utt2 | 2 | `%ut`, self-ref | Minimal |
| %utt3 | 2 | `%ut` only | Minimal |
| %utt4 | 4 | Standalone (local `NOW`) | Minimal |
| %utt5 | 10 | `%ut`, `%utt4` | Low |
| %utt6 | 4 | `%ut`, `%uttcovr`, guarded `^DIC` | Low |
| %utt7 | 2 | `%ut` only | Minimal |
| %uttcovr | 2 | `%ut` | Minimal |

#### Tier 2 — M XML Parser
| Routine | Assertions | Dependencies | Risk |
|---------|-----------|-------------|------|
| MXMLBLD | 13 | `MXMLUTL`, `MXMLTMP1` | Low |
| MXMLDOMT | 9 | `MXMLDOM`, `%ZISH` (file I/O) | **High** |
| MXMLPATT | 25 | `MXMLDOM`, `MXMLPATH` | Medium |
| MXMLTMPT | 49 | `MXMLTMP1`, `MXMLTMPL`, `DT^DICRW` | Medium |

#### Tier 3 — VA FileMan
| Routine | Assertions | Key Dependencies | Risk |
|---------|-----------|-----------------|------|
| ZZUTDIDT | 3 | `%DT` | Low |
| DMUDIC00 | 14 | `^DIC`, `^DIBT`, `DMUFINIT`, `XPDUTL` | High |
| DMUDT000 | 58 | `%DT`, `%ZISH`, `%ZOSF` | High |
| DMUDTC00 | 92 | `%DTC`, `%ZISH` | High |
| DMUDIQ00 | 7 | `^DD`, `^DIC`, `DIQ`, `%ZISH` | High |

#### Tier 4a — Problem List
| Routine | Assertions | Key Dependencies | Risk |
|---------|-----------|-----------------|------|
| ZZRGUT | 83 | `GMPLAPI2–4`, `GMPLMGR`, `^AUPNPROB` | Very High |
| ZZRGUT1 | 87 | `GMPLAPI1`, `GMPLAPI6`, `^SC`, `^TMP` | Very High |
| ZZRGUT2 | 6 | `GMPLSITE` | Medium |
| ZZRGUT3 | 60 | `GMPLAPI1`, `GMPLAPI5–6`, `^SC` | Very High |
| ZZRGUT4 | 38 | `GMPLAPI1–2`, `GMPLAPI6`, `^SC` | Very High |
| ZZRGUT5 | 8 | `GMPLAPI2`, `GMPLAPI7`, `GMPLHIST` | High |
| ZZRGUTRB | 38 | `GMPLMGR`, `GMPLSAVE`, `ORQQPL1–3` | Very High |
| ZZRGUTEX | 29 | `ACKQUTL6`, `IBDFBK3`, `PXRMPROB`, many packages | Very High |

#### Tier 4b — Scheduling
| Routine | Assertions | Key Dependencies | Risk |
|---------|-----------|-----------------|------|
| ZZUTGETAPPT | 14 | `SDAMA201`, `ZZUTSDCOM` | High |
| ZZUTNEXTAPPT | 11 | `SDAMA201`, `ZZUTSDCOM` | High |
| ZZUTSDAPI | 35 | `SDAMA301`, `ZZUTSDCOM` | High |
| ZZUTSDIMO | 4 | `SDAMA203`, `ZZUTSDCOM` | High |
| ZZUTGETPLIST | 15 | `SDAMA202`, `ZZUTSDCOM` | High |
| ZZUTPATAPPT | 5 | `SDAMA204`, `^DPT`, `ZZUTSDCOM` | High |
| ZZRGUSD1 | 103 | `SDMAPI1–2`, `^DIC`, `^SC`, `^DPT` | Very High |
| ZZRGUSD2 | 68 | `SDCAPI1`, `SDMAPI1–2`, `^DPT` | Very High |
| ZZRGUSD3 | 81 | `SDCAPI1`, `SDMAPI1–4`, `^DPT`, `^SC` | Very High |
| ZZRGUSD4 | 60 | `SDMAPI1–2`, `SDMAPI5`, `^DPT`, `^SC` | Very High |
| ZZRGUSD5 | 82 | `DGSAAPI`, `SDMAPI1–4`, `^DPT`, many globals | Very High |
| ZZRGUSD6 | 69 | `SCAPMC21`, `SCTMAPI1`, `SDMAPI1–2`, `^DIC` | Very High |

#### Tier 4c — Registration
| Routine | Assertions | Key Dependencies | Risk |
|---------|-----------|-----------------|------|
| ZZDGPTCO1 | 10 | `DGPTCO1`, `^DG`, `DICRW` | Medium |
