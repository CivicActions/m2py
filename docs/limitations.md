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
