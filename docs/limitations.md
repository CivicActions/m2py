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