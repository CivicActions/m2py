"""M2PY Parser Limitations Registry.

This module is the canonical source for all limitation data. It is used by:
- utils/rebuild_docs.py (generates docs/limitations.md and docs/coverage-matrix.md)
- Test files (reference limitation IDs)

Each limitation has a type that determines expected test coverage:

- Parse Error: Parser rejects syntax with MUMPSParseError.
  • Parser tests: Required (verify error raised)
  • ASG/codegen tests: Comment-only (no code to analyze/generate)

- Parses OK: Parser accepts but runtime/codegen behavior undefined.
  • Parser tests: Required (verify syntax parses correctly)
  • ASG tests: Required if analyzable, otherwise comment-only with LIM-XXX
  • Codegen tests: Comment-only with LIM-XXX (no implementation planned)

- Informative: No executable syntax exists. Documentation only.
  • All test files: Comment-only with LIM-XXX
"""

from enum import Enum
from typing import NamedTuple


class LimitationType(Enum):
    """Type of limitation determining expected test coverage."""

    PARSE_ERROR = "Parse Error"
    """Syntax recognized but explicitly rejected. Parser raises MUMPSParseError."""

    PARSES_OK = "Parses OK"
    """Syntax valid but runtime/codegen behavior undefined."""

    INFORMATIVE = "Informative"
    """No executable syntax exists. Documentation only."""


class Limitation(NamedTuple):
    """A parser limitation entry."""

    id: str
    category: str
    type: LimitationType
    short_description: str
    sections: tuple[str, ...]  # Test section IDs this applies to
    details: str  # Full markdown description
    behavior: str  # M2PY Behavior description


# =============================================================================
# Limitation Registry - Full Content
# =============================================================================

LIMITATIONS: dict[str, Limitation] = {
    "LIM-001": Limitation(
        id="LIM-001",
        category="Event Processing Commands",
        type=LimitationType.PARSE_ERROR,
        short_description="ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER",
        sections=("s6_3_4_event_processing", "s8_event_processing"),
        details="""\
The following commands are defined in ANSI M X11.1-1995 for event-driven
programming but are not implemented. These commands have **zero usage** in both
the YottaDB test suite and VA Vista codebase, suggesting they are not used in
production MUMPS systems:

| Command | Description |
|---------|-------------|
| ABLOCK | Block asynchronous events during critical sections |
| AUNBLOCK | Unblock asynchronous events |
| ASTART | Start asynchronous event processing |
| ASTOP | Stop asynchronous event processing |
| ESTART | Start synchronous event processing |
| ESTOP | Stop synchronous event processing |
| ETRIGGER | Trigger an event |""",
        behavior="Parser raises `MUMPSParseError` for these commands.",
    ),
    "LIM-002": Limitation(
        id="LIM-002",
        category="THEN Command",
        type=LimitationType.PARSE_ERROR,
        short_description="Zero real-world usage",
        sections=("s8_then_command",),
        details="""\
The THEN command is a standard MUMPS command but has zero usage in YottaDB
tests and VA Vista. It will be implemented if encountered in real codebases.""",
        behavior="Parser raises `MUMPSParseError`.",
    ),
    "LIM-003": Limitation(
        id="LIM-003",
        category="MWAPI SSVNs",
        type=LimitationType.PARSES_OK,
        short_description="^$EVENT, ^$WINDOW, ^$DISPLAY (X11.6 standard)",
        sections=(),  # Tested within s7_1_3_ssvns
        details="""\
The MUMPS Windowing API (MWAPI, defined in ANSI M X11.6) provides GUI capabilities
through structured system variables and event processing. M2PY does **not** support
MWAPI because:

1. **Limited real-world usage** - Only 5 files in VA VistA reference MWAPI (`ZISG*.m`)
2. **Separate standard** - MWAPI is a distinct specification (X11.6) from core MUMPS (X11.1)

### Unsupported MWAPI Structured System Variables

| SSVN | Description |
|------|-------------|
| `^$WINDOW` | Window definitions and properties |
| `^$DISPLAY` | Display/screen information |
| `^$EVENT` | Event information for GUI callbacks |

### Unsupported MWAPI Commands

Event processing commands (ABLOCK, AUNBLOCK, ASTART, ASTOP, ESTART, ESTOP, ETRIGGER)
listed above are also part of the MWAPI event model.""",
        behavior="""\
Parser accepts `^$EVENT`, `^$WINDOW`, `^$DISPLAY` syntax (valid SSVN grammar).
ASG produces `MStructuredSystemVariable`. Codegen behavior is undefined as MWAPI
runtime support is not available in YottaDB.""",
    ),
    "LIM-004": Limitation(
        id="LIM-004",
        category="Deprecated Functions",
        type=LimitationType.PARSES_OK,
        short_description="$DEXTRACT, $DPIECE (never standardized)",
        sections=(),  # Tested within s7_1_5_intrinsic_functions
        details="""\
These functions were proposed for the 1984/1990 standards but never included in
the final ANSI standard. They follow valid intrinsic function syntax.""",
        behavior="""\
Parser accepts `$DEXTRACT` and `$DPIECE` (valid function syntax). ASG produces
`MFunctionCall`. Codegen behavior is undefined as these functions have no standard
semantics.""",
    ),
    "LIM-005": Limitation(
        id="LIM-005",
        category="VIEW Command",
        type=LimitationType.PARSES_OK,
        short_description="Implementation-defined keywords",
        sections=("s8_2_24_view",),
        details="""\
The VIEW command is defined in ANSI M X11.1 §8.2.24 as having "arguments unspecified" -
meaning the syntax and behavior are entirely implementation-specific. Each MUMPS
implementation (YottaDB, GT.M, Caché, etc.) defines its own VIEW keywords and semantics.

Parser accepts VIEW commands with YottaDB/GT.M syntax:
- `VIEW "keyword"` - Simple keyword
- `VIEW "keyword":value` - Keyword with value
- `VIEW "keyword":value1:value2` - Keyword with multiple colon-separated values
- `VIEW expr` - Expression form

**Common YottaDB VIEW keywords**: `BADCHAR`, `BREAKMSG`, `GDSCERT`, `GVDUPSETNOOP`,
`LVNULLSUBS`, `NOUNDEF`, `PATCODE`, `TRACE`, etc.""",
        behavior="""\
The ASG produces `MViewStatement` with raw arguments preserved. Code generation
must handle VIEW commands on a per-implementation basis since semantics vary
significantly between MUMPS platforms.""",
    ),
    "LIM-006": Limitation(
        id="LIM-006",
        category="Extended Character Sets",
        type=LimitationType.PARSES_OK,
        short_description="Implementation-defined charset operations",
        sections=("s9_1_definitions",),
        details="""\
The MUMPS 1995 standard defines a base character set profile "charset M" (Annex A)
which uses ASCII codes 0-127. Extended character sets (Unicode, UTF-8, ISO 10646,
vendor-specific charsets) are defined through the `^$CHARACTER` structured system
variable and are implementation-specific.

**Per §9 (Character Set Profile)**, a charset defines:
1. Character codes and their meaning
2. Valid characters for names (identifiers)
3. Available pattern codes and definitions
4. Collation order for string comparison

**Charset naming conventions**:
- Names beginning with `Y` - Reserved for user-defined charsets
- Names beginning with `Z` - Reserved for vendor-defined charsets
- All other names - Reserved for future standard enhancement

**YottaDB Unicode support**: YottaDB provides UTF-8 mode via the `ydb_chset`
environment variable, but the specific character handling behaviors are outside
the scope of standard MUMPS and must be handled at code generation time.""",
        behavior="""\
M2PY implements charset M (ASCII 0-127) as the default. Extended character sets
beyond ASCII are not fully supported. String handling assumes ASCII/UTF-8
compatibility. The `^$CHARACTER` SSVN is parsed but charset-specific operations
(transforms, collation algorithms) are implementation-defined.""",
    ),
    "LIM-007": Limitation(
        id="LIM-007",
        category="BNF Metalanguage",
        type=LimitationType.INFORMATIVE,
        short_description="§5 is informative only, no executable syntax",
        sections=("s5_1_bnf_notation",),
        details="""\
Section 5 of the MUMPS standard describes the BNF notation used throughout
the specification. This section is **informative only** and contains no
executable semantics to implement or test.""",
        behavior="""\
No parser or ASG implementation needed. Test files contain comments only,
documenting this as informational content.""",
    ),
    "LIM-008": Limitation(
        id="LIM-008",
        category="Embedded Programs",
        type=LimitationType.INFORMATIVE,
        short_description="§6.4 out of scope for source-to-source transpiler",
        sections=("s6_4_embedded_programs",),
        details="""\
Section 6.4 defines rules for embedding MUMPS code within other programming
languages (e.g., C, FORTRAN). This involves host language interoperability,
foreign function interfaces, and runtime integration that is outside the
scope of a source-to-source transpiler.""",
        behavior="""\
Not applicable. M2PY transpiles standalone MUMPS routines to Python, not MUMPS
embedded within other host programs. Test files contain comments only.""",
    ),
    "LIM-009": Limitation(
        id="LIM-009",
        category="RLOAD/RSAVE Commands",
        type=LimitationType.PARSE_ERROR,
        short_description="Zero real-world usage",
        sections=("s8_2_28_rload", "s8_2_29_rsave"),
        details="""\
The RLOAD (Routine Load) and RSAVE (Routine Save) commands are defined in
ANSI M X11.1-1995 §8.2.17 and §8.2.18 for dynamic routine management at
runtime. These commands have **zero usage** in both the YottaDB test suite
and VA VistA codebase.""",
        behavior="Parser raises `MUMPSParseError`.",
    ),
    # LIM-010 was removed (duplicate)
    "LIM-011": Limitation(
        id="LIM-011",
        category="^$LIBRARY SSVN",
        type=LimitationType.PARSES_OK,
        short_description="Zero real-world usage, runtime undefined",
        sections=(),  # Tested within s7_1_3_ssvns
        details="""\
The `^$LIBRARY` SSVN provides access to routine library information. This
has **zero usage** in the VA VistA codebase.""",
        behavior="""\
Parser accepts `^$LIBRARY` syntax (valid SSVN grammar). ASG produces
`MStructuredSystemVariable`. Codegen behavior is undefined.""",
    ),
    "LIM-012": Limitation(
        id="LIM-012",
        category="Unknown Z-Extensions",
        type=LimitationType.PARSE_ERROR,
        short_description="Unknown Z-commands/functions from other implementations",
        sections=(),  # Not a specific section, applies to unknown Z-*
        details="""\
Per the MUMPS standard, all names beginning with 'Z' are reserved for
vendor-specific extensions (FR-017). M2PY implements support for common
YottaDB Z-commands (ZBREAK, ZCOMPILE, ZGOTO, ZHALT, ZHELP, ZKILL, ZLINK,
ZMESSAGE, ZPRINT, ZSHOW, ZSTEP, ZSYSTEM, ZTRIGGER, ZWRITE, ZALLOCATE,
ZDEALLOCATE) and Z-functions ($ZDATE, $ZSEARCH, etc.).""",
        behavior="""\
Known YottaDB Z-extensions are fully parsed and produce ASG nodes. Unknown
Z-commands or Z-functions from other MUMPS implementations (InterSystems
Caché/IRIS, MicroM, DSM) raise `MUMPSParseError`.""",
    ),
    "LIM-013": Limitation(
        id="LIM-013",
        category="ASSIGN Command",
        type=LimitationType.PARSE_ERROR,
        short_description="Part of MWAPI event model",
        sections=("s8_assign",),
        details="""\
The ASSIGN command is defined in ANSI M X11.1-1995 for structured system
variable assignment as part of the MWAPI event model. It has **zero usage**
in both the YottaDB test suite and VA VistA codebase.""",
        behavior="Parser raises `MUMPSParseError`.",
    ),
    "LIM-014": Limitation(
        id="LIM-014",
        category="ANSI Standard Library Functions (Annex I)",
        type=LimitationType.PARSES_OK,
        short_description="~60 library functions with zero VistA usage",
        sections=(
            "s7_1_6_5_library_functions_character",
            "s7_1_6_5_library_functions_string",
        ),
        details="""\
ANSI M X11.1-1995 Annex I defines standard library functions organized into
three routines: `^MATH`, `^STRING`, and `^CHARACTER`. These are extrinsic
functions called as `$$%FUNC^ROUTINE(args)`. However, VA VistA has **zero usage**
of any ANSI standard library functions. VistA instead uses its own Kernel
Library Functions (`^XLFMTH`, `^XLFHYPER`, `^XLFCRC`, etc.).

### Unimplemented ANSI Library Functions

| Routine | Functions | Count |
|---------|-----------|-------|
| `^CHARACTER` | COLLATE, COMPARE | 2 |
| `^STRING` | CRC16, CRC32, CRCCCITT, FORMAT, LOWER, UPPER, PATCODE | 7 |
| `^MATH` (Extended) | Hyperbolic: SINH, COSH, TANH, COTH, SECH, CSCH | 6 |
| `^MATH` (Extended) | Inverse Hyperbolic: ARCSINH, ARCCOSH, ARCTANH, ARCCOTH | 4 |
| `^MATH` (Extended) | Extended Trig: COT, CSC, SEC, ARCCOT, ARCCSC, ARCSEC | 6 |
| `^MATH` (Extended) | Angle Conversion: DEGRAD, RADDEG, DECDMS, DMSDEC | 4 |
| `^MATH` (Extended) | Complex Numbers: CABS, CADD, CSUB, CMUL, CDIV, CSIN, CCOS, CEXP, CLOG, CPOWER, COMPLEX, CONJUG | 12 |
| `^MATH` (Extended) | Matrix: MTXADD, MTXSUB, MTXMUL, MTXINV, MTXDET, MTXTRP, MTXCOPY, MTXSCA, MTXEQU, MTXCOF, MTXUNIT | 11 |
| `^MATH` (Extended) | Miscellaneous: ABS, SIGN, PI, E, PRODUCE, REPLACE, XOR | 7 |

**Total**: ~59 unimplemented functions

**Note**: Core math functions (EXP, LOG, SQRT, SIN, COS, TAN, ARCSIN, ARCCOS, ARCTAN)
are implemented via the bundled `%MATH` routine in `m2py.runtime.routines.MATH`.""",
        behavior="""\
Parser accepts extrinsic function syntax `$$%FUNC^ROUTINE(args)` (valid grammar).
ASG produces `MExtrinsicFunction`. Code generation imports the target routine module
and calls the function. For unimplemented routines, the generated code will fail at
import time. VistA codebases will work correctly as they use Kernel Library Functions
(`^XLFMTH`, etc.) instead of ANSI standard library routines.""",
    ),
}


# =============================================================================
# Document Sections (static content for limitations.md)
# =============================================================================

DOC_HEADER = """\
# M2PY Parser Limitations

This document describes known limitations of the M2PY parser and commands
that are not currently supported. Each limitation has a unique ID (LIM-XXX)
for traceability to test files.

<!-- This file is auto-generated by utils/rebuild_docs.py from src/m2py/limitations.py -->
<!-- Do not edit directly - edit limitations.py instead -->
"""

DOC_TYPES_TABLE = """\
## Limitation Types

| Type | Description | M2PY Behavior |
|------|-------------|---------------|
| **Parse Error** | Syntax is recognized but explicitly rejected | Parser raises `MUMPSParseError` |
| **Parses OK** | Syntax is valid but runtime/codegen behavior is undefined | Parser accepts, codegen may be incomplete |
| **Informative** | No executable syntax exists | No tests needed, comment-only files |
"""

DOC_UNKNOWN_COMMANDS = """\
## Unsupported MUMPS Commands

### Unknown Command Handling

Commands that don't match any recognized MUMPS command will produce a clear error:

```
MUMPSUnknownCommandError: Unknown command 'FOOBAR'. Not a recognized MUMPS command or valid abbreviation.
```

This error will be triggered for:
- Misspelled command names
- Vendor-specific extensions (e.g., InterSystems Caché/IRIS proprietary commands)
- Event processing commands (see LIM-001)
"""

DOC_VENDOR_COMMANDS = """\
### Vendor-Specific Commands

M2PY targets standard MUMPS with YottaDB/GT.M extensions. Commands specific to
other implementations (InterSystems Caché/IRIS, MicroM, DSM, etc.) are not currently
supported and will trigger the unknown command error.

If you encounter a command that should be supported, please open an issue.
"""

DOC_WORKFLOW = """\
---

## Limitation Management Workflow

### Adding a New Limitation

1. **Assign ID**: Use the next available LIM-XXX number
2. **Add to limitations.py**: Add entry to `LIMITATIONS` dict in `src/m2py/limitations.py`
3. **Regenerate docs**: Run `uv run python utils/rebuild_docs.py`
4. **Check VistA-M usage**: Run `rg 'PATTERN' VistA-M/` to verify zero usage
5. **Create test**: Add parse error test referencing the LIM-XXX ID

### Test Requirements

Each limitation MUST have a corresponding test that:
- References the limitation ID in the docstring (e.g., "See LIM-001")
- Verifies the parser raises an appropriate error for unsupported syntax
- Does NOT use `@pytest.mark.skip` - must be an active passing test

### Cross-Reference Format

Tests should reference limitations as:
```python
def test_ablock_raises_parse_error(self):
    \"\"\"ABLOCK command raises parse error. See LIM-001.\"\"\"
    with pytest.raises(MUMPSParseError):
        parser.parse(" ABLOCK")
```
"""

# Order for rendering sections (some limitations are grouped)
SECTION_ORDER: list[tuple[str, str | None]] = [
    # Parse Error commands first
    ("LIM-001", "### {id}: Event Processing Commands (Not Implemented)"),
    ("LIM-002", "### {id}: THEN Command (Deferred)"),
    ("_vendor", None),  # Insert vendor commands section here
    # MWAPI and other "Parses OK" limitations
    ("LIM-003", "## {id}: MWAPI (Windowing API) - Out of Scope"),
    ("LIM-004", "## {id}: $DEXTRACT and $DPIECE (Never Standardized)"),
    ("LIM-005", "## {id}: VIEW Command (Implementation-Defined)"),
    ("LIM-006", "## {id}: Extended Character Sets (Implementation-Defined)"),
    # Informative
    ("LIM-007", "## {id}: §5 BNF Metalanguage (Informative Only)"),
    ("LIM-008", "## {id}: §6.4 Embedded Programs (Out of Scope)"),
    # More Parse Error commands
    ("LIM-009", "## {id}: RLOAD and RSAVE Commands (Not Implemented)"),
    ("LIM-011", "## {id}: ^$LIBRARY Structured System Variable (Not Implemented)"),
    ("LIM-012", "## {id}: Unknown Z-Commands and Z-Functions"),
    ("LIM-013", "## {id}: ASSIGN Command (Not Implemented)"),
    # Library functions
    ("LIM-014", "## {id}: ANSI Standard Library Functions (Annex I)"),
]


# =============================================================================
# Lookup Helpers
# =============================================================================


def _build_section_to_limitation() -> dict[str, str]:
    """Build reverse mapping from section_id to limitation_id."""
    mapping: dict[str, str] = {}
    for lim_id, lim in LIMITATIONS.items():
        for section in lim.sections:
            mapping[section] = lim_id
    return mapping


SECTION_TO_LIMITATION: dict[str, str] = _build_section_to_limitation()
"""Map from test section ID to limitation ID."""


def get_limitation_for_section(section_id: str) -> Limitation | None:
    """Get the limitation that applies to a test section, if any."""
    lim_id = SECTION_TO_LIMITATION.get(section_id)
    if lim_id:
        return LIMITATIONS[lim_id]
    return None


def get_limitation(lim_id: str) -> Limitation | None:
    """Get a limitation by ID."""
    return LIMITATIONS.get(lim_id)


def generate_limitations_md() -> str:
    """Generate the full limitations.md content from the registry."""
    lines: list[str] = []

    # Header
    lines.append(DOC_HEADER)
    lines.append("")

    # Types table
    lines.append(DOC_TYPES_TABLE)
    lines.append("")

    # Index table
    lines.append("## Limitation Index")
    lines.append("")
    lines.append("| ID | Category | Type | Description |")
    lines.append("|----|----------|------|-------------|")
    for lim_id in sorted(LIMITATIONS.keys(), key=lambda x: int(x.split("-")[1])):
        lim = LIMITATIONS[lim_id]
        lines.append(
            f"| {lim.id} | {lim.category} | {lim.type.value} | {lim.short_description} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Unknown commands section
    lines.append(DOC_UNKNOWN_COMMANDS)
    lines.append("")

    # Render each limitation section
    for section_key, heading_template in SECTION_ORDER:
        if section_key == "_vendor":
            lines.append(DOC_VENDOR_COMMANDS)
            lines.append("")
            continue

        lim = LIMITATIONS.get(section_key)
        if not lim:
            continue

        # Heading
        assert heading_template is not None
        heading = heading_template.format(id=lim.id)
        lines.append(heading)
        lines.append("")

        # Type
        lines.append(f"**Type**: {lim.type.value}")
        lines.append("")

        # Details
        lines.append(lim.details)
        lines.append("")

        # Behavior
        lines.append(f"**M2PY Behavior**: {lim.behavior}")
        lines.append("")

    # Workflow section
    lines.append(DOC_WORKFLOW)
    lines.append("")

    return "\n".join(lines)
