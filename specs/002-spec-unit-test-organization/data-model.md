# Data Model: Unit Test Organization

## Entities

### 1. TestCategory
Represents the transpiler phase being tested.

| Field | Type | Description |
|-------|------|-------------|
| name | enum | `parser`, `asg`, `codegen`, `analysis`, `meta`, `cross_cutting` |
| description | string | Human-readable description |
| directory | path | `tests/unit/{name}/` |
| marker | string | pytest marker name (optional for analysis/meta/cross_cutting) |

**Values**:
- `parser`: Tests textX grammar against source, validates parse trees
- `asg`: Tests semantic analysis, tests analyzed ASG nodes
- `codegen`: Tests Python output, verifies MUMPS semantic equivalence
- `analysis`: Tests internal analysis algorithms (FOR classifier, GOTO classifier, resolver) - not spec-aligned
- `meta`: Tests tooling infrastructure (textX integration, parse tracking) - not spec-aligned
- `cross_cutting`: Tests features spanning multiple commands (indirection, postconditions, timeouts) - spec-aligned but not section-specific

### 2. SpecSection
Represents a section of the MUMPS 1995 specification.

| Field | Type | Constraints |
|-------|------|-------------|
| section_number | string | e.g., "7.1.5.1" |
| title | string | From MUMPS spec |
| parent_section | SpecSection? | nullable, for subsections |
| directory_slug | string | e.g., "s7_expressions" |
| file_slug | string | e.g., "test_s7_1_5_1_ascii" |

**Relationships**:
- One SpecSection → Many TestFiles
- One SpecSection → Many child SpecSections

### 3. TestFile
A pytest test file with a specific focus.

| Field | Type | Constraints |
|-------|------|-------------|
| path | path | Absolute path to .py file |
| category | TestCategory | FK to TestCategory |
| spec_section | SpecSection | FK to SpecSection |
| test_count | int | Number of test functions |
| stub_count | int | Number of xfail stubs |

**Naming Convention**: `test_{spec_section.file_slug}.py`

### 4. TestCase
Individual test function within a TestFile.

| Field | Type | Constraints |
|-------|------|-------------|
| name | string | Function name starting with `test_` |
| file | TestFile | FK to TestFile |
| markers | list[string] | pytest markers applied |
| status | enum | `implemented`, `stub`, `skip` |
| xfail_reason | string? | Reason if status=stub |
| skip_reason | string? | Reason if status=skip |

**Validation Rules**:
- If `status=stub` → `xfail_reason` required
- If `status=skip` → `skip_reason` required
- Markers must include file's category marker

### 5. TestMarker
Custom pytest marker registration.

| Field | Type | Description |
|-------|------|-------------|
| name | string | Marker identifier |
| description | string | Displayed in `pytest --markers` |
| registered_in | path | `tests/conftest.py` |

**Standard Markers**:
| Name | Purpose |
|------|---------|
| `parser` | Tests at parser/grammar level |
| `asg` | Tests at ASG/semantic level |
| `codegen` | Tests at code generation level |
| `stub` | Placeholder test, expected to fail |
| `slow` | Long-running test |
| `pre1995` | Tests pre-1995 syntax |
| `ydb` | YottaDB-specific extension |

## State Transitions

### TestCase Lifecycle

```
[stub] --implement--> [implemented]
                           |
                           v
[stub] --out-of-scope--> [skip]
```

- `stub` → `implemented`: Remove xfail, add test logic
- `stub` → `skip`: Replace xfail with skip, add skip_reason referencing docs/limitations.md

## Directory Structure Model

```
tests/unit/
├── parser/                    # TestCategory: parser
│   ├── s6_routine/           # SpecSection: §6
│   │   └── test_s6_1_routinehead.py
│   ├── s7_expressions/       # SpecSection: §7
│   │   ├── test_s7_1_variables.py
│   │   ├── test_s7_1_3_ssvns.py      # §7.1.3 SSVNs (^$JOB, etc.)
│   │   ├── test_s7_1_5_functions/
│   │   │   ├── test_s7_1_5_1_ascii.py
│   │   │   └── ...
│   │   └── test_s7_3_operators.py
│   ├── s8_commands/          # SpecSection: §8
│   │   ├── test_s8_2_1_close.py
│   │   └── ...
│   └── extensions/
│       └── ydb/
│           └── test_zwrite.py
├── asg/                       # TestCategory: asg
│   └── (parallel structure)
├── codegen/                   # TestCategory: codegen
│   └── (parallel structure)
├── cross_cutting/             # Cross-cutting features (spec-aligned)
│   ├── test_indirection.py
│   ├── test_postconditions.py
│   ├── test_timeouts.py
│   ├── test_naked_references.py
│   └── test_language_semantics.py
├── analysis/                  # TestCategory: analysis (not spec-aligned)
│   ├── test_for_classifier.py
│   ├── test_goto_classifier.py
│   └── test_resolver.py
└── meta/                      # TestCategory: meta (not spec-aligned)
    ├── test_textx_classes.py
    └── test_parse_result_tracking.py
```

## Index File Format

`tests/unit/TEST_INDEX.md`:

```markdown
# Unit Test Coverage Index

## Parser Tests

### §7.1.5 Intrinsic Functions

| Function | File | Status | Stubs | Tests |
|----------|------|--------|-------|-------|
| $ASCII | test_s7_1_5_1_ascii.py | partial | 2 | 5 |
| $CHAR | test_s7_1_5_2_char.py | stub | 8 | 0 |
```
