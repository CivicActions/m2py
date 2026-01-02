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

## BNF Metalanguage (§5 - Informative)

Section 5 of the ANSI M standard describes the metalanguage (BNF notation) used
to define MUMPS syntax. This section is **informative only** - it describes how
to read the grammar specification but is not part of the MUMPS language itself.

M2PY uses textX for parsing, which has its own grammar notation. The BNF
metalanguage tests in the test suite are marked as skipped since they test
notation conventions, not actual MUMPS syntax.

## Deprecated Functions (Superseded)

The following functions are deprecated and superseded by standard functions:

| Deprecated | Superseded By | Notes |
|------------|---------------|-------|
| `$NEXT(glvn)` | `$ORDER(glvn)` | $NEXT returns "" at end; $ORDER is preferred |
| `$DEXTRACT` | `$EXTRACT` | Destructive extract (modifies in place) |
| `$DPIECE` | `$PIECE` | Destructive piece (modifies in place) |

Note: $DEXTRACT and $DPIECE have limited usage in VistA (6 and 12 uses respectively)
and are marked as xfail for future implementation.

## RLOAD/RSAVE Commands (Not Implemented)

The RLOAD and RSAVE commands are for binary routine loading/saving and have
zero usage in VistA. These are not implemented.

## Embedded Programs (§6.4 - Out of Scope)

Section 6.4 of the ANSI M standard describes embedded MUMPS programs within
host languages. This is not applicable to a standalone transpiler and is
out of scope for M2PY.

## ^$LIBRARY SSVN (Not Implemented)

The ^$LIBRARY Structured System Variable Name has zero usage in VistA and
is not implemented. (Note: ^$EVENT has 7 uses and IS planned for implementation.)

## Extended Character Sets (§9 - Implementation-Defined)

Extended character sets beyond ASCII are implementation-defined and vary
by MUMPS implementation. M2PY uses Python's native Unicode support.
