# Feature Specification: VistA-VEHU-M Complete Transpilation

**Feature Branch**: `024-vista-transpilation-fixes`  
**Created**: 2026-02-17  
**Status**: Draft  
**Input**: User description: "Resolve all VistA-VEHU-M transpilation failures (2,592 routines / 6.6%) across 13 root causes. The only acceptable remaining limitation is MWAPI SSVNs (X11.6). Implement partial IRIS/Caché support for all vendor-specific functions used by VistA. Update the limitations document to reflect resolved items. Target >99% transpilation success from current 93.4%."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Core Codegen Fixes Unblock 80% of Failures (Priority: P1)

A developer transpiling VistA-VEHU-M routines currently encounters 2,592 failures. The majority (80%) are caused by five issues in the code generator: unhandled `ParenExpr` nodes, f-string nested quote incompatibility on Python 3.10, empty indented blocks in TRAMPOLINE strategy, missing `>=`/`<=` operators, and missing `SET $X`/`SET $Y` support. Fixing these five issues unblocks ~2,153 routines and raises success from 93.4% to ~99%.

**Why this priority**: These are the highest-impact fixes (40%, 22%, 8%, 7%, 6% of all failures respectively) and most are low-to-medium complexity. They address systemic codegen defects rather than missing features.

**Independent Test**: Run the full VistA-VEHU-M transpilation scan. Count of failures drops from 2,592 to ~439. Each fix can also be verified independently with the MUMPS test snippets below.

**Acceptance Scenarios**:

1. **Given** a MUMPS routine containing parenthesized expressions like `(X+Y)` in any context, **When** transpiled by m2py, **Then** the generated Python is syntactically valid and semantically equivalent — `ParenExpr` nodes never reach codegen unhandled.
2. **Given** a MUMPS routine using indirection with subscripts containing function calls (e.g., `@Y@($P(X,"^",1))`), **When** transpiled by m2py on Python 3.10, **Then** the generated Python contains no f-strings with nested matching quotes and compiles without `SyntaxError`.
3. **Given** a MUMPS routine where an IF block's only content is a GOTO in TRAMPOLINE strategy, **When** transpiled by m2py, **Then** the generated Python has a valid indented body (not an empty block) and compiles without `SyntaxError: expected an indented block`.
4. **Given** a MUMPS routine using `>=` or `<=` comparison operators, **When** transpiled by m2py, **Then** the generated Python produces correct comparison results (e.g., `5>=3` → true, `3>=5` → false, `5>=5` → true).
5. **Given** a MUMPS routine using `SET $X=0` or `SET $Y=0`, **When** transpiled by m2py, **Then** the generated Python calls the appropriate runtime method to update the cursor position special variables.

---

### User Story 2 — MUMPS Language Completeness Fixes (Priority: P2)

Several MUMPS language features used in VistA are partially implemented: LHS `$EXTRACT` with 1 argument, tuple SET with `$PIECE`/`$EXTRACT` targets, `NEW` with indirection in TRAMPOLINE strategy, and computed/indirected GOTOs. Completing these unblocks an additional ~144 routines.

**Why this priority**: These are standard MUMPS features that VistA relies on. They require more nuanced fixes than P1 but are essential for correct transpilation of core VistA packages like FileMan, Kernel, and Lab Service.

**Independent Test**: Each fix has a standalone MUMPS test routine that can be transpiled and compared against YottaDB output.

**Acceptance Scenarios**:

1. **Given** a MUMPS routine using `SET $E(X)="Z"` (1-argument LHS $EXTRACT), **When** transpiled by m2py, **Then** the generated Python replaces the first character of X with "Z" (equivalent to `SET $E(X,1,1)="Z"`).
2. **Given** a MUMPS routine using tuple SET with `$PIECE` targets like `S ($P(X,"^",2),Y)="Z"`, **When** transpiled by m2py, **Then** the generated Python sets both targets — the piece of X and the variable Y — to the same value.
3. **Given** a MUMPS routine using `NEW @VAR` in TRAMPOLINE strategy, **When** transpiled by m2py, **Then** the generated Python properly saves and restores the dynamically-named variable using the routine state's locals dictionary.
4. **Given** a MUMPS routine using a computed GOTO like `G @$S(%=1:"A",%=2:"B",1:"C")`, **When** transpiled by m2py, **Then** the generated Python evaluates the expression at runtime and dispatches to the correct label function.

---

### User Story 3 — Robustness and Infrastructure Fixes (Priority: P3)

Some transpilation failures are caused by infrastructure issues: Python recursion depth exceeded on deeply nested routines, ZLINK/ZLOAD commands (used for dynamic routine loading), and miscellaneous issues (encoding errors, `UnaryPrefixedExpr`, device control mnemonics). Fixing these unblocks ~64 routines.

**Why this priority**: These are less common but block specific high-value routines (CMOP, Controlled Substances, Kernel utilities). The recursion fix has low complexity; ZLINK requires a design decision about runtime behavior.

**Independent Test**: Transpile the specific affected routines (e.g., PSXRECV for recursion, Kernel routines for ZLINK) and verify they produce valid Python.

**Acceptance Scenarios**:

1. **Given** a deeply nested MUMPS routine that currently causes `RecursionError`, **When** transpiled by m2py, **Then** the transpilation completes successfully without hitting Python's recursion limit.
2. **Given** a MUMPS routine using `ZLINK` or `ZLOAD`, **When** transpiled by m2py, **Then** the generated Python calls a runtime stub that does not raise an error (the `$TEXT` function can still read from `.m` source files).
3. **Given** a VistA-VEHU-M `.m` file with non-UTF-8 encoding, **When** read by m2py, **Then** the file is handled gracefully (decoded with fallback encoding or skipped with a clear warning).

---

### User Story 4 — IRIS/Caché Vendor Function Support (Priority: P4)

VistA-VEHU-M contains routines that use InterSystems Caché/IRIS-specific intrinsic functions: `$REPLACE`, `$ZBOOLEAN`, `$ZV`/`$ZVERSION`, `$ZF` (OS commands), `$ZA` (I/O status), `$ZR`/`$ZREFERENCE`, `$NAMESPACE`, `$ZU` (utility functions), `$ZC`/`$ZCALL`, and `$VIEW`/`$V`. Implementing the commonly-used subset unblocks ~106 routines.

**Why this priority**: These are vendor extensions, not standard MUMPS. However, VistA code conditionally uses them (often guarded by `$ZV` checks), so full VistA transpilation requires at least stubs. The implementable functions (`$REPLACE`, `$ZBOOLEAN`, `$ZV`, `$ZF`, `$ZR`, `$ZA`, `$NAMESPACE`, `$ZU`) have clear semantics; the rest (`$ZC`, `$VIEW`) are best handled as stubs.

**Independent Test**: Each vendor function has a test case validated against InterSystems IRIS. Transpile and run each test; compare output.

**Acceptance Scenarios**:

1. **Given** a MUMPS routine using `$REPLACE(string,search,replace)`, **When** transpiled by m2py, **Then** the generated Python performs string replacement matching IRIS behavior (including count, start position, and case-insensitive modes).
2. **Given** a MUMPS routine using `$ZBOOLEAN(arg1,arg2,op)`, **When** transpiled by m2py, **Then** the generated Python performs the correct bitwise Boolean operation from the 16-entry truth table, for both integer and string arguments.
3. **Given** a MUMPS routine reading `$ZV` or `$ZVERSION`, **When** transpiled by m2py, **Then** the generated Python returns a version string containing "M2PY" (so VistA platform-detection code can identify the runtime).
4. **Given** a MUMPS routine using `$ZF(-1,cmd)` or `$ZF(-100,flags,cmd,args)`, **When** transpiled by m2py, **Then** the generated Python executes the OS command via `subprocess` and returns the exit code.
5. **Given** a MUMPS routine reading `$ZA`, **When** transpiled by m2py, **Then** the generated Python returns 0 by default (no I/O errors), with the runtime tracking TCP connection state for bit 13 (8192).
6. **Given** a MUMPS routine reading or setting `$ZR`/`$ZREFERENCE`, **When** transpiled by m2py, **Then** the generated Python returns the full name of the last global reference.
7. **Given** a MUMPS routine reading or setting `$NAMESPACE`, **When** transpiled by m2py, **Then** the generated Python returns a configurable namespace string (default: "VISTA") and supports `NEW`/`SET`.
8. **Given** a MUMPS routine using `$ZU(code,...)` with any of the ~12 codes used by VistA, **When** transpiled by m2py, **Then** the generated Python dispatches to the appropriate Python equivalent (e.g., `$ZU(5)` → namespace, `$ZU(168)` → `os.getcwd()`, `$ZU(12)` → config directory).
9. **Given** a MUMPS routine using `$ZC`/`$ZCALL` or `$VIEW`/`$V`, **When** transpiled by m2py, **Then** the generated Python calls a runtime stub that returns an empty string and logs a warning (these are Caché-specific internals with no Python equivalent).

---

### User Story 5 — Miscellaneous Fixes and Stubs (Priority: P5)

Remaining failures (~54 routines) include: device control mnemonics (`WRITE /command`), setting special variables (`$ZINTERRUPT`, `$ZERR`, `$ZSOURCE`), reading `$DEVICE` and `$REFERENCE`, `$ZGBLDIR`, external C function calls (`$&`), `UnaryPrefixedExpr` unwrapping, `ZPRINT`/`ZMESSAGE` commands (5 routines), and one parse error (malformed source). These are individually low-count but collectively block full VistA compatibility.

**Why this priority**: Each item affects 1–5 routines. Stubs and no-ops are acceptable for most. The parse error (ZZBACSUA) may represent genuinely malformed MUMPS.

**Independent Test**: Transpile each affected routine and verify no errors. Stubs are acceptable — the routines should transpile even if the stubbed functions return default values.

**Acceptance Scenarios**:

1. **Given** a MUMPS routine using `WRITE /command` (device control mnemonics), **When** transpiled by m2py, **Then** the generated Python calls a runtime device control handler (or no-op stub) without raising an error.
2. **Given** a MUMPS routine using `SET $ZINTERRUPT`, `SET $ZERR`, or `SET $ZSOURCE`, **When** transpiled by m2py, **Then** the generated Python handles these as settable special variables in the runtime.
3. **Given** a MUMPS routine reading `$DEVICE`, `$REFERENCE`, or `$ZGBLDIR`, **When** transpiled by m2py, **Then** the generated Python returns an appropriate default value from the runtime.
4. **Given** a MUMPS routine using external C function calls (`$&function`), **When** transpiled by m2py, **Then** the generated Python calls a stub that logs a warning and returns an empty string.
5. **Given** a MUMPS routine with `UnaryPrefixedExpr` ASG nodes surviving into codegen, **When** transpiled by m2py, **Then** the expression is properly unwrapped (analogous to the `ParenExpr` fix).
6. **Given** a MUMPS routine using `ZPRINT` or `ZMESSAGE` commands, **When** transpiled by m2py, **Then** the generated Python calls a runtime stub (no-op for ZPRINT, error-signal stub for ZMESSAGE) without raising a transpilation error.

---

### User Story 6 — Limitations Documentation Update (Priority: P2)

The limitations document must be updated to reflect newly supported features and to document partial IRIS/Caché support as a known scope boundary (similar to the existing YDB extensions documentation).

**Why this priority**: Documentation accuracy is essential for users to understand what m2py supports. This is tied to P2 because it should be done as features are completed.

**Independent Test**: Review the limitations document for accuracy against the implemented feature set.

**Acceptance Scenarios**:

1. **Given** that `>=` and `<=` operators are now supported, **When** reviewing the limitations document, **Then** there is no entry listing them as unsupported.
2. **Given** that vendor functions `$REPLACE`, `$ZBOOLEAN`, `$ZV`, etc. are now supported, **When** reviewing the limitations document, **Then** any previously-listed limitations for these are removed.
3. **Given** that IRIS/Caché vendor functions are partially supported, **When** reviewing the limitations document, **Then** a new limitation entry (e.g., LIM-0XX) describes the scope of IRIS support: which vendor functions are fully implemented, which are stubbed, and which remain unsupported, analogous to the existing LIM-012 for Z-extensions and LIM-015 for YDB-specific features.
4. **Given** that MWAPI SSVNs (`^$EVENT`, `^$WINDOW`, `^$DISPLAY`) remain unsupported (X11.6 standard), **When** reviewing the limitations document, **Then** LIM-003 still correctly documents this as a known limitation.

---

### Edge Cases

- What happens when a `ParenExpr` wraps another `ParenExpr` (double-parenthesized expression like `((X+Y))`)? The fix must handle arbitrary nesting depth.
- What happens when `$EXTRACT` on the LHS has 0 arguments? This is invalid MUMPS — should raise a clear error.
- What happens when a computed GOTO target evaluates to a label that doesn't exist in the routine? The runtime should raise a clear runtime error with the target label name.
- What happens when `$ZU` is called with an unrecognized code not in the VistA-used subset? The runtime should raise a clear error identifying the unimplemented `$ZU` code.
- What happens when `$ZF(-1)` executes a command that fails? The return value should be the non-zero exit code, matching IRIS behavior.
- What happens when `$REPLACE` receives an empty search string? It should return the original string unchanged, matching IRIS behavior.
- What happens when `$ZBOOLEAN` is called with an `op` value outside 0–15? The runtime should raise an error.
- What happens when f-string replacement introduces string concatenation with adjacent string literals? The codegen must ensure proper operator spacing.
- What happens when TRAMPOLINE strategy encounters multiple consecutive GOTOs in an IF body? All should be properly contained within the if block.
- What happens when `NEW @VAR` is called with a variable name that contains subscripts? The runtime should handle both unsubscripted (`NEW @"X"`) and subscripted (`NEW @"X(1)"`) forms.
- What happens when `ZPRINT` is called with a label range argument (e.g., `ZPRINT START:END`)? The stub should accept any arguments without error.
- What happens when `ZMESSAGE` is called with a non-existent error code? The stub should signal the error or log it without crashing.

## Requirements *(mandatory)*

### Functional Requirements

#### Core Codegen Fixes

- **FR-001**: The codegen expression dispatcher MUST handle `ParenExpr` ASG nodes by recursing into the inner expression, ensuring no `NotImplementedError: Unsupported expression type: ParenExpr` is raised during transpilation.
- **FR-002**: All generated Python code MUST be syntactically valid on Python 3.10. F-strings in the codegen MUST NOT contain nested matching quotes. Where f-strings currently embed function calls that produce single-quoted strings, the codegen MUST use string concatenation, `.format()`, or double-quoted f-strings instead.
- **FR-003**: In TRAMPOLINE strategy, when an IF block's body would be empty (e.g., because the only statement is a GOTO converted to a `return`), the codegen MUST produce a valid Python body (e.g., by including the return statement inside the if block, or inserting `pass`).
- **FR-004**: The codegen MUST support `>=` and `<=` as binary comparison operators. `A>=B` MUST be equivalent to `NOT (A < B)`. `A<=B` MUST be equivalent to `NOT (A > B)`. These are YottaDB extensions to the ANSI MUMPS standard.
- **FR-005**: The codegen MUST support `SET $X=expr` and `SET $Y=expr` to update the cursor column and row position special variables via runtime methods.

#### MUMPS Language Completeness

- **FR-006**: The codegen MUST support `SET $EXTRACT(var)=value` (1-argument form) as shorthand for `SET $EXTRACT(var,1,1)=value`, replacing the first character of the variable.
- **FR-007**: The codegen MUST support tuple SET with `$PIECE` and `$EXTRACT` function targets (e.g., `S ($P(X,"^",2),Y)="Z"`), delegating to the existing LHS function handlers.
- **FR-008**: The codegen MUST support `NEW @VAR` (indirected NEW) in TRAMPOLINE strategy by dynamically saving and restoring the named variable using the routine state's locals dictionary.
- **FR-009**: The codegen MUST support computed GOTO (`G @expr`) by evaluating the target expression at runtime and dispatching to the resolved label function. When the target label does not exist, a clear runtime error MUST be raised.

#### Robustness

- **FR-010**: Transpilation MUST NOT fail with `RecursionError` for any VistA-VEHU-M routine. The system MUST handle deeply nested expressions either by increasing the recursion limit during transpilation or by using iterative traversal.
- **FR-011**: The codegen MUST handle `ZLINK` and `ZLOAD` commands by generating a runtime stub call that does not raise an error. The stub MAY be a no-op or MAY load routine source for `$TEXT` access.
- **FR-012**: The transpiler MUST handle input files with non-UTF-8 encoding gracefully, either by using fallback encoding (e.g., Latin-1) or by reporting a clear warning and skipping the file.

#### IRIS/Caché Vendor Function Support

- **FR-013**: The runtime MUST implement `$REPLACE(string,search,replace[,start[,count[,case]]])` matching IRIS semantics: replace all occurrences by default, support count limiting, start position (returning substring from that position onward), and case-insensitive mode.
- **FR-014**: The runtime MUST implement `$ZBOOLEAN(arg1,arg2,op)` supporting all 16 Boolean operations (op 0–15) for both integer and string arguments, matching IRIS semantics including sign behavior for bitwise NOT operations.
- **FR-015**: The runtime MUST provide `$ZV`/`$ZVERSION` as a read-only special variable returning a version string containing "M2PY". `$ZVERSION(1)` MUST return 3 on UNIX/Linux systems.
- **FR-016**: The runtime MUST implement `$ZF(-1,cmd)` (synchronous OS command, returns exit code), `$ZF(-2,cmd)` (asynchronous OS command), and `$ZF(-100,flags,cmd,args)` (structured OS command with flag parsing). VMS-only variants (`$ZF("GETSYM",...)`, `$ZF("GETJPI",...)`, `$ZF("TRNLNM",...)`) MUST be stubbed as no-ops.
- **FR-017**: The runtime MUST provide `$ZA` as a read-only special variable defaulting to 0, with bit 13 (8192) set when a TCP socket is in connected state.
- **FR-018**: The runtime MUST provide `$ZR`/`$ZREFERENCE` returning the full global reference string of the last global GET, SET, or KILL operation. Setting `$ZR` to `""` MUST clear the reference.
- **FR-019**: The runtime MUST provide `$NAMESPACE` as a settable and NEW-able special variable, returning a configurable namespace string (default: "VISTA"). SET changes the value; NEW pushes and restores it.
- **FR-020**: The runtime MUST implement a `$ZU(code,...)` dispatcher for the ~12 codes used by VistA:
  - `$ZU(0)` → namespace info (mapped to `$NAMESPACE`)
  - `$ZU(5)` → current namespace
  - `$ZU(5,ns)` → switch namespace (mapped to `SET $NAMESPACE`)
  - `$ZU(12)` → manager directory path
  - `$ZU(53)` → current device (mapped to `$IO`)
  - `$ZU(56,2)` → collation info (return 0)
  - `$ZU(68,15,1)`, `$ZU(68,28,0/1)`, `$ZU(68,40,1)` → runtime configuration (no-ops)
  - `$ZU(140,4,file)` → file existence check (mapped to `os.path.exists()`)
  - `$ZU(168)` → current working directory (mapped to `os.getcwd()`)
  - `$ZU(190,17)` → block collision info (return 0)
  - Unrecognized codes MUST raise a clear error identifying the code.
- **FR-021**: `$ZC`/`$ZCALL` and `$VIEW`/`$V` function calls MUST generate runtime stubs that return an empty string and log a warning. These are Caché-specific internals with no direct Python equivalent.

#### Miscellaneous Completeness

- **FR-022**: The codegen MUST handle `WRITE /command` (device control mnemonics) by generating a runtime device control call or no-op stub.
- **FR-023**: The codegen MUST support `SET $ZINTERRUPT=expr`, `SET $ZERR=expr`, and `SET $ZSOURCE=expr` as settable special variables in the runtime.
- **FR-024**: The codegen MUST support reading `$DEVICE` (I/O error info), `$REFERENCE` (naked global indicator), and `$ZGBLDIR` (global directory path) as special variables with appropriate default values.
- **FR-025**: External C function calls (`$&function(args)`) MUST generate a runtime stub that logs a warning and returns an empty string, rather than causing a transpilation error.
- **FR-026**: `UnaryPrefixedExpr` ASG nodes MUST be properly unwrapped in codegen (analogous to `ParenExpr`), not falling through to `NotImplementedError`.
- **FR-030**: The codegen MUST handle `ZPRINT` and `ZMESSAGE` commands by generating runtime stubs (no-op or error-signal stub respectively). `MZPrintStatement` (4 VistA routines) and `MZMessageStatement` (1 VistA routine) have ASG nodes but currently no codegen dispatch, causing `NotImplementedError`.

#### Documentation

- **FR-027**: The limitations document MUST be updated to remove entries for features that are now supported (e.g., `>=`/`<=` if previously listed, any vendor functions now implemented).
- **FR-028**: A new limitation entry MUST be added documenting partial IRIS/Caché support scope: which vendor functions are fully implemented, which are stubbed, and which remain unsupported. This follows the pattern of LIM-012 (Z-extensions) and LIM-015 (YDB-specific features).
- **FR-029**: LIM-003 (MWAPI SSVNs) MUST remain documented as an unsupported limitation — these require the X11.6 standard and are out of scope.

### Key Entities

- **ParenExpr / UnaryPrefixedExpr**: ASG wrapper nodes produced by the textX parser. Must be transparently unwrapped before or during codegen.
- **Special Variables ($X, $Y, $ZA, $ZR, $ZV, $NAMESPACE, $DEVICE, $REFERENCE)**: MUMPS system state variables that must be readable and (for some) settable through the runtime.
- **Vendor Functions ($REPLACE, $ZBOOLEAN, $ZF, $ZU, $ZC, $VIEW)**: InterSystems IRIS/Caché-specific intrinsic functions. Varying levels of implementability.
- **TRAMPOLINE Strategy**: The code generation strategy for routines with complex control flow (GOTO). Uses function-per-label with shared `RoutineState`.
- **VistA-VEHU-M Routines**: The 39,304 MUMPS source files from the VistA-VEHU distribution. The transpilation target and validation corpus.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: VistA-VEHU-M transpilation success rate reaches **99% or higher** (at least 38,911 of 39,304 routines), up from the current 93.4% (36,712 routines).
- **SC-002**: The only routines that may still fail are those using MWAPI SSVNs (`^$EVENT`, `^$WINDOW`, `^$DISPLAY` — LIM-003), genuinely malformed source files, or truly exotic vendor-specific features with zero reasonable mapping to Python.
- **SC-003**: All generated Python code compiles without `SyntaxError` on Python 3.10 — zero SyntaxError failures in the transpilation scan.
- **SC-004**: Zero `NotImplementedError` failures for any MUMPS syntax or function that appears in VistA-VEHU-M routines (excluding MWAPI SSVNs).
- **SC-005**: Zero `RecursionError` failures during transpilation of any VistA-VEHU-M routine.
- **SC-006**: Every MUMPS test snippet provided in the failure analysis document produces correct output when transpiled and executed, matching the YottaDB or IRIS reference output.
- **SC-007**: The limitations document accurately reflects the current state: no stale entries for now-supported features, a clear new entry for partial IRIS support scope.
- **SC-008**: All IRIS vendor function implementations pass their respective test cases validated against InterSystems IRIS 2025.2.

## Assumptions

- **Python 3.10 target**: All generated Python code must be valid on Python 3.10+. While Python 3.12+ relaxes f-string restrictions (PEP 701), we target the earlier version for broader compatibility.
- **ZLINK is primarily for $TEXT**: VistA's primary use of ZLINK/ZLOAD is to load routine source text for inspection via `$TEXT`. A stub that allows `$TEXT` to read from `.m` source files is sufficient.
- **Single namespace**: VistA runs in a single logical namespace. `$NAMESPACE` and `$ZU(5)` return a constant string. Namespace switching is a no-op.
- **$ZA defaults to 0**: In the absence of TCP I/O, `$ZA` returns 0. Real TCP state tracking is a future enhancement.
- **$ZC/$ZCALL and $VIEW are dead paths**: In VistA, code using `$ZC` and `$VIEW` is typically guarded by `$ZV` checks for Caché/IRIS. Since m2py's `$ZV` returns "M2PY", these code paths won't execute at runtime. Stubs are sufficient.
- **VMS code is dead**: VistA routines checking `$ZV["VMS"` contain VMS-specific code paths (`$ZF("GETSYM",...)` etc.) that will never execute. Stubs are sufficient.
- **Malformed source files are excluded**: If a `.m` file contains genuinely invalid MUMPS syntax (not a parser limitation), it is acceptable for m2py to report a parse error.
- **Recursion limit increase is acceptable**: Increasing Python's recursion limit during transpilation (not during generated code execution) is an acceptable short-term fix. Long-term iterative refactoring is optional.
- **$ZU codes outside the VistA-used subset are not required**: Only the ~12 `$ZU` codes actually used in VistA-VEHU-M need implementation. Other codes can raise an explicit error.
