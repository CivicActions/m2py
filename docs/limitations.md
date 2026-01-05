# M2PY Parser Limitations

This document describes known limitations of the M2PY parser and commands
that are not currently supported.

## Unsupported MUMPS Commands

### Unknown Command Handling

Commands that don't match any recognized MUMPS command will produce a clear error:

```
MUMPSUnknownCommandError: Unknown command 'FOOBAR'. Not a recognized MUMPS command or valid abbreviation.
```

This error will be triggered for:
- Misspelled command names
- Vendor-specific extensions (e.g., InterSystems Caché/IRIS proprietary commands)
- Event processing commands (see below)

### Event Processing Commands (Not Implemented)

The following commands are defined in ANSI M X11.1-1995 for event-driven
programming but are not implemented. These commands have **zero usage** in both
the YottaDB test suite and VA Vista codebase, suggesting they are not used in
production MUMPS systems:

| Command | Description |
|---------|-------------|
| ABLOCK | Block asynchronous events during critical sections |
| AUNBLOCK | Unblock asynchronous events |
| ASSIGN | Structured System Variable (SSV) assignment |
| ASTART | Start asynchronous event processing |
| ASTOP | Stop asynchronous event processing |
| ESTART | Start synchronous event processing |
| ESTOP | Stop synchronous event processing |
| ETRIGGER | Trigger an event |

### THEN Command (Deferred)

The THEN command is a standard MUMPS command but has zero usage in YottaDB
tests and VA Vista. It will be implemented if encountered in real codebases.

### Vendor-Specific Commands

M2PY targets standard MUMPS with YottaDB/GT.M extensions. Commands specific to
other implementations (InterSystems Caché/IRIS, MicroM, DSM, etc.) are not currently
supported and will trigger the unknown command error.

If you encounter a command that should be supported, please open an issue.

## MWAPI (Windowing API) - Out of Scope

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
listed above are also part of the MWAPI event model.

**Note**: The parser *can* parse `^$EVENT` syntax (it's valid SSVN syntax), but the
semantics require MWAPI runtime support which is not available in YottaDB.

## $DEXTRACT and $DPIECE (Never Standardized)

These functions were proposed for the 1984/1990 standards but never included in the final ANSI standard.

**M2PY Behavior**: Not supported; raises parse error.

## VIEW Command (Implementation-Defined)

The VIEW command is defined in ANSI M X11.1 §8.2.24 as having "arguments unspecified" -
meaning the syntax and behavior are entirely implementation-specific. Each MUMPS
implementation (YottaDB, GT.M, Caché, etc.) defines its own VIEW keywords and semantics.

**M2PY Behavior**: The parser accepts VIEW commands with YottaDB/GT.M syntax:
- `VIEW "keyword"` - Simple keyword
- `VIEW "keyword":value` - Keyword with value
- `VIEW "keyword":value1:value2` - Keyword with multiple colon-separated values
- `VIEW expr` - Expression form

The ASG produces `MViewStatement` with raw arguments preserved. Code generation
must handle VIEW commands on a per-implementation basis since semantics vary
significantly between MUMPS platforms.

**Common YottaDB VIEW keywords**: `BADCHAR`, `BREAKMSG`, `GDSCERT`, `GVDUPSETNOOP`,
`LVNULLSUBS`, `NOUNDEF`, `PATCODE`, `TRACE`, etc.

## Extended Character Sets (Implementation-Defined)

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

**M2PY Behavior**: M2PY implements charset M (ASCII 0-127) as the default. Extended
character sets beyond ASCII are not fully supported. String handling assumes ASCII/UTF-8
compatibility. The `^$CHARACTER` SSVN is parsed but charset-specific operations
(transforms, collation algorithms) are implementation-defined.

**YottaDB Unicode support**: YottaDB provides UTF-8 mode via the `ydb_chset`
environment variable, but the specific character handling behaviors are outside
the scope of standard MUMPS and must be handled at code generation time.