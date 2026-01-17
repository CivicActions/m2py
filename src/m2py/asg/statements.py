"""ASG Statement elements.

Defines all statement types for the MUMPS ASG:
- MStatement: Base statement class
- Control flow: MIfStatement, MElseStatement, MForStatement, MGotoStatement
- Subroutines: MDoStatement, MQuitStatement
- Data: MSetStatement, MWriteStatement, MReadStatement
- Variables: MNewStatement, MKillStatement, MMergeStatement
- I/O: MOpenStatement, MCloseStatement, MUseStatement
- Other: MHangStatement, MHaltStatement, MXecuteStatement, MLockStatement, MViewStatement, MBreakStatement, MJobStatement
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, List, Optional, Union

from m2py.asg.elements import ASGElement, MScope
from m2py.asg.enums import ForLoopType, ForParamType, GotoCodegenPattern, GotoType

if TYPE_CHECKING:
    from m2py.asg.elements import MCall
    from m2py.asg.expressions import MExpr, MVariable, MGlobal, MIndirection


# =============================================================================
# Base Statement
# =============================================================================


@dataclass
class MStatement(ASGElement):
    """Base class for all statements.

    A statement represents a single command execution in MUMPS.
    Statements can have postconditions that control execution.
    """

    scope: Optional[MScope] = field(default=None, repr=False)
    postcondition: Optional["MExpr"] = None

    # Analysis flags
    is_unreachable: bool = False

    # Parser internal: dot nesting level (used during DO block structuring)
    _dot_level: int = field(default=0, repr=False)


# =============================================================================
# Assignment Statements
# =============================================================================


@dataclass
class MAssignment:
    """Single assignment within SET.

    Represents one target=value pair in a SET command.
    SET can have multiple assignments: SET A=1,B=2,C=3

    Sub-component of MSetStatement; source position is inherited from container.
    """

    target: Optional[Union["MVariable", "MGlobal", "MIndirection"]] = None
    value: Optional["MExpr"] = None
    postcondition: Optional["MExpr"] = None  # Individual assignment postcondition


@dataclass
class MSetStatement(MStatement):
    """SET command - variable assignment.

    Assigns values to one or more targets:
    SET X=1, SET A=1,B=2, SET (A,B)=1

    Supports argument indirection (Spec 012 Phase 9):
    SET @A where A contains "X=1,Y=2"
    """

    assignments: List[MAssignment] = field(default_factory=list)
    # Argument indirections: @A where A contains complete SET args like "X=1"
    argument_indirections: List["MIndirection"] = field(default_factory=list)


# =============================================================================
# I/O Statements
# =============================================================================


@dataclass
class MWriteStatement(MStatement):
    """WRITE command - output.

    Writes data to the current device:
    W "Hello", W !,?10,"Text", W X
    """

    arguments: List[Any] = field(default_factory=list)  # MExpr, format controls


@dataclass
class MReadTarget:
    """Target variable for READ command with optional timeout and fixed length.

    Represents a variable being read into, with optional modifiers:
    - is_char_read: True for *VAR syntax (single character read)
    - timeout: Optional timeout expression (VAR:timeout syntax)
    - fixed_length: Optional fixed-length expression (VAR#length syntax)

    Examples:
    - R X -> MReadTarget(variable=MVariable('X'))
    - R *X -> MReadTarget(variable=MVariable('X'), is_char_read=True)
    - R X:10 -> MReadTarget(variable=MVariable('X'), timeout=MLiteral(10))
    - R *X:0 -> MReadTarget(variable=MVariable('X'), is_char_read=True, timeout=MLiteral(0))
    - R X#5 -> MReadTarget(variable=MVariable('X'), fixed_length=MLiteral(5))
    - R X#5:10 -> MReadTarget(variable=MVariable('X'), fixed_length=MLiteral(5), timeout=MLiteral(10))

    Sub-component of MReadStatement; source position is inherited from container.
    """

    variable: Optional["MExpr"] = (
        None  # The variable to read into (MVariable or MGlobal)
    )
    is_char_read: bool = False  # True for *VAR (single character read)
    timeout: Optional["MExpr"] = None  # Optional timeout expression
    fixed_length: Optional["MExpr"] = (
        None  # Optional fixed-length expression (VAR#length)
    )


@dataclass
class MReadStatement(MStatement):
    """READ command - input.

    Reads data from the current device:
    R X, R "Prompt: ",X, R X:timeout, R *X

    Arguments can be:
    - MReadTarget: Variable to read into (with optional timeout/char-read flag)
    - MLiteral (StringLiteral): Prompt text to display
    - MFormatControl: Format controls (!, #, ?n)
    """

    arguments: List[Any] = field(
        default_factory=list
    )  # MReadTarget, MLiteral, MFormatControl


# =============================================================================
# Control Flow - Conditional
# =============================================================================


@dataclass
class MIfStatement(MStatement):
    """IF command with conditional body.

    Conditionally executes following commands:
    IF condition commands...
    I X=1 DO SOMETHING

    MUMPS allows comma-separated conditions which act as AND:
    IF cond1,cond2,cond3 is equivalent to IF cond1 IF cond2 IF cond3

    When there's a single condition, use `condition`.
    When there are multiple conditions, use `conditions` list.
    """

    condition: Optional["MExpr"] = (
        None  # Convenience: first condition (set when len(conditions) == 1)
    )
    conditions: List["MExpr"] = field(
        default_factory=list
    )  # Multiple conditions (comma-separated)
    then_scope: MScope = field(default_factory=MScope)

    # Analysis: Pre-computed reference to restructurable GOTO in then_scope
    # Set by classify_gotos() when IF contains an intra-label forward GOTO
    # that can be restructured to if/else pattern. Avoids scanning at codegen time.
    restructurable_goto: Optional["MGotoStatement"] = field(default=None, repr=False)


@dataclass
class MElseStatement(MStatement):
    """ELSE command (uses $TEST).

    Executes if $TEST is false (from previous IF):
    ELSE commands...
    E DO ALTERNATIVE
    """

    body: MScope = field(default_factory=MScope)


# =============================================================================
# Control Flow - Loops
# =============================================================================


@dataclass
class MForParameter:
    """Single forparameter in FOR command.

    Represents one parameter in a FOR loop specification:
    - VALUE: Single expression (7 in F I=7)
    - RANGE: Bounded range (1:1:10 in F I=1:1:10)
    - OPEN_RANGE: Unbounded range (1:1 in F I=1:1)

    Sub-component of MForStatement; source position is inherited from container.
    """

    param_type: ForParamType = ForParamType.VALUE
    value: Optional["MExpr"] = None  # For VALUE type
    start: Optional["MExpr"] = None  # For RANGE types
    step: Optional["MExpr"] = None
    end: Optional["MExpr"] = None


@dataclass
class MForStatement(MStatement):
    """FOR command with loop body.

    Iterates over values, ranges, or indefinitely:
    F I=1:1:10 commands..., F I="A","B","C" commands..., F commands...

    The loop_var can be a simple variable name (str), a subscripted
    variable (MVariable), or an MIndirection for cases like F @A=1:1:10
    """

    loop_var: Optional[Union[str, "MVariable", "MExpr"]] = None
    loop_var_indirect: bool = False  # True if loop_var is indirection
    parameters: List[MForParameter] = field(default_factory=list)
    body: MScope = field(default_factory=MScope)

    # Classification (populated in analysis pass)
    loop_type: Optional[ForLoopType] = None
    has_internal_quit: bool = False
    has_internal_goto: bool = False
    exit_points: List["MStatement"] = field(default_factory=list, repr=False)
    is_infinite: bool = False  # True for step=0 or ARGUMENTLESS loops
    loop_var_modified_in_body: bool = False  # True if loop variable is SET inside body

    # T088-T090: Pre-computed fields for codegen (populated by classify_gotos)
    has_cross_label_exit: bool = False  # True if any exit GOTO targets different label
    needs_exception_wrapper: bool = False  # True if outermost FOR for MULTI_LOOP_EXIT
    exit_target: Optional[str] = (
        None  # Target label name (MUMPS name, codegen translates)
    )


# =============================================================================
# Control Flow - Jumps
# =============================================================================


@dataclass
class MGotoStatement(MStatement):
    """GOTO command.

    Transfers control to a label:
    G label, G label^routine, G label:condition

    Note: GOTO cannot create a Python 'continue' pattern. Per MUMPS spec (MDC 3.6.5):
    "Execution of GOTO effects the immediate termination of all FORs in the line
    containing the GOTO." A GOTO to the same label creates a function call/recursion.
    """

    targets: List["MCall"] = field(default_factory=list)

    # Classification (populated in analysis pass)
    goto_type: Optional[GotoType] = None
    exits_loops: List["MForStatement"] = field(default_factory=list, repr=False)
    is_cross_label: bool = False  # True if target is in a different label

    # For intra-label forward GOTOs: index of target statement in label body
    # Set during classify_gotos() when goto_type=FORWARD_JUMP and is_cross_label=False
    target_stmt_index: Optional[int] = None

    # T096-T098: Pre-computed codegen fields (populated by classify_gotos)
    is_restructurable: bool = False  # True if can be restructured to if/else
    codegen_pattern: Optional[GotoCodegenPattern] = None  # Pattern for code generation


# =============================================================================
# Subroutine Statements
# =============================================================================


@dataclass
class MDoStatement(MStatement):
    """DO command - call subroutine or inline block.

    This class handles BOTH labeled DO calls and argumentless DO blocks:

    1. **Labeled DO** (targets not empty):
       DO label, D label^routine, D label(args)
       - targets contains MCall references to be executed

    2. **Argumentless DO** (targets empty, body populated):
       DO
       . command1
       . command2
       - Creates an inline block scope for dot-indented lines
       - targets is empty, body contains the block statements

    To detect argumentless DO: check `if not statement.targets`.
    """

    targets: List["MCall"] = field(default_factory=list)
    body: MScope = field(default_factory=MScope)  # For argumentless DO block

    # Pre-computed flag set by parser when body is populated with dot-indented lines
    is_inline_block: bool = False  # True for DO blocks with dot-indented body


@dataclass
class MQuitStatement(MStatement):
    """QUIT command.

    Returns from current context:
    Q, Q value (return from extrinsic), Q:condition
    """

    return_value: Optional["MExpr"] = None

    # Context (populated in analysis pass)
    exits_for: Optional["MForStatement"] = field(default=None, repr=False)
    exits_do_block: Optional["MDoStatement"] = field(
        default=None, repr=False
    )  # Argumentless DO (empty targets)


# =============================================================================
# Variable Statements
# =============================================================================


@dataclass
class MNewStatement(MStatement):
    """NEW command - variable scoping.

    Creates new local scope for variables:
    N X, NEW (X,Y,Z), N (X) exclusive
    """

    variables: List[str] = field(default_factory=list)
    exclusive: bool = False  # NEW (X) = all except X
    except_list: List[str] = field(default_factory=list)


@dataclass
class MKillStatement(MStatement):
    """KILL command - delete variables.

    Removes variables and their descendants:
    - K (no args) - kill ALL local variables (is_kill_all=True)
    - K X, KILL ^GLOBAL - selective kill (targets list)
    - K (X,Y) - exclusive kill (keep only X,Y and descendants)
    - K (X,Y,Z),(X,W) - multiple exclusive groups (keep intersection: only X)
    - K (X,W),Z - mixed: exclusive kill, then also kill Z

    When multiple exclusive groups are present, keep only variables that
    appear in ALL groups (intersection semantics).
    """

    targets: List[Union["MVariable", "MGlobal", "MIndirection"]] = field(
        default_factory=list
    )  # Selective kill targets (variables, globals, or indirection)
    exclusive: bool = False  # True if any exclusive groups present
    except_list: List[str] = field(
        default_factory=list
    )  # Computed: intersection of all exclusive groups
    except_groups: List[List[str]] = field(
        default_factory=list
    )  # Raw exclusive groups before intersection

    @property
    def is_kill_all(self) -> bool:
        """Return True if this is a KILL with no arguments (kills all locals)."""
        return not self.targets and not self.exclusive


@dataclass
class MKSubscriptsStatement(MStatement):
    """KSUBSCRIPTS command - delete variable subscripts only.

    Kills only the subscripts (descendants) of a variable, preserving its value:
    - KS (no args) - kill subscripts of ALL local variables (is_kill_all=True)
    - KS X - kills X(1), X(1,2), etc. but preserves X's value
    - KS (X,Y) - exclusive kill of subscripts (keep X,Y subscripts)

    Reference: MUMPS 1995 ANSI Standard, Section 8.2.20
    After KS X: $DATA(X) is 0 or 1 (not 10 or 11)
    """

    targets: List[Union["MVariable", "MGlobal", "MIndirection"]] = field(
        default_factory=list
    )
    exclusive: bool = False
    except_list: List[str] = field(default_factory=list)
    except_groups: List[List[str]] = field(default_factory=list)

    @property
    def is_kill_all(self) -> bool:
        """Return True if this is KSUBSCRIPTS with no arguments."""
        return not self.targets and not self.exclusive


@dataclass
class MKValueStatement(MStatement):
    """KVALUE command - delete variable value only.

    Kills only the value of a variable, preserving its subscripts (descendants):
    - KV (no args) - kill values of ALL local variables (is_kill_all=True)
    - KV X - kills X's value but preserves X(1), X(1,2), etc.
    - KV (X,Y) - exclusive kill of values (keep X,Y values)

    Reference: MUMPS 1995 ANSI Standard, Section 8.2.21
    After KV X: $DATA(X) is 0 or 10 (not 1 or 11)
    """

    targets: List[Union["MVariable", "MGlobal", "MIndirection"]] = field(
        default_factory=list
    )
    exclusive: bool = False
    except_list: List[str] = field(default_factory=list)
    except_groups: List[List[str]] = field(default_factory=list)

    @property
    def is_kill_all(self) -> bool:
        """Return True if this is KVALUE with no arguments."""
        return not self.targets and not self.exclusive


# =============================================================================
# Merge Statement
# =============================================================================


@dataclass
class MMergePair:
    """Single merge pair within MERGE command.

    Represents one destination=source pair in a MERGE command.
    MERGE can have multiple pairs: M X=Y,Z=W

    Note: This is a sub-component of MMergeStatement, not a standalone ASG node.
    It inherits source position context from its containing MMergeStatement.
    """

    destination: Any = None  # MVariable or MGlobal
    source: Any = None  # MVariable or MGlobal


@dataclass
class MMergeStatement(MStatement):
    """MERGE command - copy tree structures.

    Copies entire variable trees:
    M ^DEST=^SOURCE, MERGE LOCAL=^GLOBAL

    Supports multiple merge pairs per MUMPS 1995 spec:
    M X=Y,Z=W copies both Y→X and W→Z
    """

    merges: List[MMergePair] = field(default_factory=list)


# =============================================================================
# Other Statements
# =============================================================================


@dataclass
class MHangStatement(MStatement):
    """HANG command - pause execution.

    Pauses for specified seconds (can have multiple durations):
    H 5, HANG seconds, H 0,1,2,3
    """

    duration: Optional["MExpr"] = None  # Deprecated: use durations
    durations: List["MExpr"] = field(default_factory=list)


@dataclass
class MHaltStatement(MStatement):
    """HALT command - terminate execution.

    Stops the current job:
    H (argumentless), HALT
    """

    pass


@dataclass
class MZHaltStatement(MStatement):
    """ZHALT command - terminate execution with exit code.

    GT.M/YottaDB extension. Stops the current job with an exit code:
    ZHALT exitcode, zh 1

    Examples:
      zhalt 1 - halt with exit code 1
      zhalt +$zstatus - halt with $zstatus as exit code
    """

    exitcode: Optional["MExpr"] = None  # Exit code expression


@dataclass
class MZHelpArg:
    """ZHELP argument: topic[:library].

    Represents a single ZHELP argument with a topic expression
    and optional library expression.
    """

    topic: Optional["MExpr"] = None  # Help topic expression
    library: Optional["MExpr"] = None  # Optional help library expression


@dataclass
class MZHelpStatement(MStatement):
    """ZHELP command - display help from help libraries.

    GT.M/YottaDB extension. Displays help information:
    ZHELP, ZHELP "topic", ZHELP "topic":"library"

    Examples:
      zhelp - interactive help browser
      zhelp "WRITE" - help on WRITE command
      zhelp "MUPIP":"mupip" - help from specific library
    """

    args: List["MZHelpArg"] = field(default_factory=list)


@dataclass
class MBreakStatement(MStatement):
    """BREAK command - enter debugger.

    Transfers control to debugger:
    B, BREAK
    """

    pass


@dataclass
class MXecuteStatement(MStatement):
    """XECUTE command - runtime code execution.

    Executes code from string:
    X "SET X=1", XECUTE code
    """

    code_expressions: List["MExpr"] = field(default_factory=list)

    # Always requires runtime support
    requires_runtime_eval: bool = True

    # Static analysis flags for optimization
    is_constant: bool = False  # True if all expressions are string literals
    constant_values: List[str] = field(default_factory=list)  # Values if constant


@dataclass
class MLockStatement(MStatement):
    """LOCK command - resource locking.

    Controls access to resources:
    L +^GLOBAL, L -^GLOBAL, L ^GLOBAL:timeout
    """

    targets: List[Any] = field(
        default_factory=list
    )  # Lock target dicts with: target/indirection, timeout, postcondition, indirection_levels
    lock_type: str = ""  # "", "+", "-"
    timeout: Optional["MExpr"] = None


@dataclass
class MViewStatement(MStatement):
    """VIEW command - implementation-specific.

    Access to implementation-specific features:
    V expr, VIEW expr

    Per MUMPS 1995 MDC spec section 8.2.24, VIEW is "arguments unspecified"
    meaning the exact syntax is implementation-defined. We capture all
    arguments as a generic list.
    """

    arguments: List["MExpr"] = field(default_factory=list)


# =============================================================================
# I/O Statements
# =============================================================================


@dataclass
class MOpenDevice:
    """Single device in OPEN command.

    Represents one device with its parameters in an OPEN command.
    OPEN can have multiple devices: O DEV1,DEV2

    Note: This is a sub-component of MOpenStatement, not a standalone ASG node.
    """

    device_expr: Optional["MExpr"] = None
    parameters: List["MExpr"] = field(default_factory=list)
    timeout: Optional["MExpr"] = None


@dataclass
class MOpenStatement(MStatement):
    """OPEN command - open device for I/O.

    Opens one or more devices for input/output:
    O device, OPEN device:parameters, O DEV1,DEV2

    Supports multiple devices per MUMPS 1995 spec:
    O DEV1:params,DEV2:params opens both devices
    """

    devices: List[MOpenDevice] = field(default_factory=list)


@dataclass
class MCloseDevice:
    """Single device in CLOSE command.

    Represents one device with its parameters in a CLOSE command.
    CLOSE can have multiple devices: C DEV1,DEV2

    Note: This is a sub-component of MCloseStatement, not a standalone ASG node.
    """

    device_expr: Optional["MExpr"] = None
    parameters: List["MExpr"] = field(default_factory=list)


@dataclass
class MCloseStatement(MStatement):
    """CLOSE command - close device.

    Closes one or more devices:
    C device, CLOSE device:parameters, C DEV1,DEV2

    Supports multiple devices per MUMPS 1995 spec:
    C DEV1,DEV2 closes both devices
    """

    devices: List[MCloseDevice] = field(default_factory=list)


@dataclass
class MUseDevice:
    """Single device in USE command.

    Represents one device with its parameters in a USE command.
    USE can have multiple devices: U DEV1,DEV2

    Note: This is a sub-component of MUseStatement, not a standalone ASG node.
    """

    device_expr: Optional["MExpr"] = None
    parameters: List["MExpr"] = field(default_factory=list)


@dataclass
class MUseStatement(MStatement):
    """USE command - select current device.

    Makes one or more devices current I/O device:
    U device, USE device:parameters, U DEV1,DEV2

    Supports multiple devices per MUMPS 1995 spec:
    U DEV1,DEV2 uses both devices in sequence
    """

    devices: List[MUseDevice] = field(default_factory=list)


@dataclass
class MJobTarget:
    """Single target in JOB command.

    Represents one job target with its per-target parameters and timeout.
    JOB can have multiple targets with individual settings per MUMPS 1995 spec 8.2.10:
    J LABEL1::5,LABEL2:params:10

    Note: This is a sub-component of MJobStatement, not a standalone ASG node.
    """

    call: "MCall" = field(default_factory=lambda: None)  # type: ignore
    processparameters: List["MExpr"] = field(default_factory=list)
    timeout: Optional["MExpr"] = None


@dataclass
class MJobStatement(MStatement):
    """JOB command - start concurrent job.

    Starts one or more new processes executing routines:
    J label, JOB label^routine:parameters, J LABEL1,LABEL2

    Supports multiple targets per MUMPS 1995 spec 8.2.10:
    J LABEL1::5,LABEL2:params:10 starts two concurrent jobs with individual timeouts

    Each target can have its own processparameters and timeout.

    Supports indirection per MUMPS spec:
    J @VAR, J @VAR^ROUTINE, J @VAR^@ROUTINEVAR
    """

    targets: List[MJobTarget] = field(default_factory=list)


# =============================================================================
# Transaction Processing Statements (MUMPS 1995 Spec 8.2.19-8.2.22)
# =============================================================================


@dataclass
class MTStartParam:
    """TSTART parameter (keyword argument).

    Parameters control transaction behavior:
    - SERIAL (S): Transaction is serializable
    - TRANSACTIONID (T): Named transaction identifier
    - Z-prefixed: Implementation-specific parameters

    Examples:
        TS ():serial           -> MTStartParam(name="serial", value=None)
        TS ():T="BA"           -> MTStartParam(name="T", value=MLiteral("BA"))
    """

    # Parameter name (e.g., "serial", "S", "transactionid", "T")
    name: str
    # Optional value expression (for name=value parameters)
    value: Optional["MExpr"] = None


@dataclass
class MTStartStatement(MStatement):
    """TSTART command - begin transaction.

    Begins a transaction:
    TS, TSTART, TS (), TS (A,B), TS ():serial

    Per MUMPS 1995 spec 8.2.22:
    - If $TLEVEL was 0, initiates a new transaction
    - If $TLEVEL > 0, increments $TLEVEL (nested transaction)
    - Optional restart argument specifies variables to restore on restart
    - Optional parameters control serialization and transaction naming

    Examples:
        TS              - Non-restartable transaction
        TS ()           - Restartable transaction (empty restart list)
        TS (A,B)        - Restartable, restore A and B on restart
        TS *            - Restartable, restore all locals on restart
        TS ():serial    - Restartable serial transaction
        TS ():S:T="X"   - Serial with transaction ID
    """

    # Restart argument: empty list = restartable, list = vars to restore
    restart_vars: List["MExpr"] = field(default_factory=list)
    # True if restart argument was '*' (restore all local variables)
    restart_all: bool = False
    # Transaction parameters (SERIAL, TRANSACTIONID, etc.)
    parameters: List[MTStartParam] = field(default_factory=list)


@dataclass
class MTCommitStatement(MStatement):
    """TCOMMIT command - commit transaction.

    Commits the current transaction:
    TC, TCOMMIT

    Per MUMPS 1995 spec 8.2.19:
    - If $TLEVEL = 1, commits the transaction
    - If $TLEVEL > 1, decrements $TLEVEL
    - Error M44 if $TLEVEL = 0
    """

    pass


@dataclass
class MTRestartStatement(MStatement):
    """TRESTART command - restart transaction.

    Restarts the current transaction:
    TRE, TRESTART

    Per MUMPS 1995 spec 8.2.20:
    - If in a restartable transaction, performs restart
    - Error M44 if $TLEVEL = 0
    """

    pass


@dataclass
class MTRollbackStatement(MStatement):
    """TROLLBACK command - rollback transaction.

    Rolls back the current transaction:
    TRO, TROLLBACK, TRO 1

    Per MUMPS 1995 spec 8.2.21:
    - Rolls back all changes since transaction start
    - Sets $TLEVEL = 0 and $TRESTART = 0
    - Optional level argument specifies transaction level to roll back to
    - Error M44 if $TLEVEL = 0
    """

    # Optional transaction level to roll back to
    level: Optional["MExpr"] = None


@dataclass
class MZTStartStatement(MStatement):
    """ZTSTART command - begin journaled transaction (GT.M/YDB extension).

    Begins a journaled (fenced) transaction:
    ZTStart, ZTS

    Per GT.M/YDB documentation:
    - Unlike TSTART, ZTSTART begins journaled transaction processing
    - Must be paired with ZTCOMMIT to complete the fenced transaction
    - Provides additional journaling semantics beyond standard TSTART
    """

    pass


@dataclass
class MZTCommitStatement(MStatement):
    """ZTCOMMIT command - commit journaled transaction (GT.M/YDB extension).

    Commits a journaled (fenced) transaction:
    ZTCommit, ZTC, ZTCommit 1

    Per GT.M/YDB documentation:
    - Commits a transaction started with ZTSTART
    - Optional level argument specifies transaction level to commit to
    - Error if not in a journaled transaction
    """

    # Optional transaction level to commit to
    level: Optional["MExpr"] = None


# =============================================================================
# Z-Command Statements (YottaDB/GT.M Extensions)
# =============================================================================
# These are vendor-specific commands supported by YottaDB and GT.M.
# They are commonly used in real-world MUMPS applications.


@dataclass
class MZShowDestination:
    """Destination for ZSHOW output.

    ZSHOW can write to a variable instead of the current device.
    ZSHOW "V":^RESULT writes variable info to ^RESULT global.
    """

    # The destination variable (local or global)
    variable: Optional["MExpr"] = None


@dataclass
class MZShowArg:
    """Single argument in ZSHOW command.

    Each ZSHOW argument specifies what to show and optionally where.
    ZSHOW "BS" - show breakpoints and stack to current device
    ZSHOW "V":X - show variables to local variable X
    """

    # The codes specifying what to show (B, D, G, I, L, S, V, etc.)
    codes: Optional["MExpr"] = None
    # Optional destination for output
    destination: Optional["MExpr"] = None


@dataclass
class MZShowStatement(MStatement):
    """ZSHOW command - show process information.

    Displays information about the process environment:
    ZSH[OW] [codes] [:destination]

    codes: String specifying what to show:
      - B: Breakpoints
      - D: Devices
      - G: Global variables
      - I: Intrinsic special variables
      - L: Locks held
      - S: Stack trace
      - V: Local variables
      - *: All of the above

    Examples:
      ZSHOW "BS" - show breakpoints and stack
      ZSHOW "*" - show everything
      ZSHOW "V":^RESULT - write variable info to global
    """

    # Arguments (codes and optional destination)
    args: List[MZShowArg] = field(default_factory=list)


@dataclass
class MZWriteSubscriptAll:
    """Wildcard subscript (*) in ZWRITE pattern.

    Matches all remaining subscript levels.
    Example: ZWR ^X("A",*) - write all ^X("A",...) entries
    """

    pass


@dataclass
class MZWriteSubscriptRange:
    """Range subscript (start:end) in ZWRITE pattern.

    Specifies a range of values for a subscript level.
    Either start or end can be omitted:
      a:b - from a to b
      :b  - from beginning to b
      a:  - from a to end
      :   - all values (wildcard for this level)
    """

    start: Optional["MExpr"] = None
    end: Optional["MExpr"] = None


@dataclass
class MZWriteArg:
    """Single argument in ZWRITE command.

    Each ZWRITE argument specifies what to write.
    ZWR X - write variable X
    ZWR @VAR - write via indirection
    """

    # The target to write (variable, global, indirection, or pattern)
    target: Optional["MExpr"] = None


@dataclass
class MZWriteStatement(MStatement):
    """ZWRITE command - write variables with names.

    Writes local or global variables and their values in a format
    that can be read back in. Similar to WRITE but includes variable names.

    Examples:
      ZWR - write all local variables
      ZWR X - write variable X and descendants
      ZWR @indirection - write via indirection
      ZWR ^GLOBAL - write global and descendants
    """

    # Arguments specifying what to write
    args: List[MZWriteArg] = field(default_factory=list)


@dataclass
class MZBreakClearAll:
    """ZBREAK -* (clear all breakpoints) marker.

    Represents the special -* syntax that removes all breakpoints.
    """

    pass


@dataclass
class MZBreakArg:
    """Single argument in ZBREAK command.

    Each ZBREAK argument specifies a breakpoint location and action.
    ZBREAK label^routine:"set x=1":5
    ZBREAK -* (represented by MZBreakClearAll in location)
    """

    # The location for the breakpoint (label reference, indirection, or MZBreakClearAll)
    location: Optional["MExpr"] = None
    # Optional action to execute at breakpoint
    action: Optional["MExpr"] = None
    # Optional count (execute action this many times)
    count: Optional["MExpr"] = None


@dataclass
class MZBreakStatement(MStatement):
    """ZBREAK command - set/remove breakpoints.

    Sets or removes breakpoints for debugging:
    ZB[REAK] location[:action[:count]]

    Examples:
      ZBREAK label^routine - set breakpoint
      ZBREAK +5^routine - set at offset
      ZBREAK label:"set x=1" - set with action
      ZBREAK - remove all breakpoints
    """

    # Breakpoint arguments
    args: List[MZBreakArg] = field(default_factory=list)


@dataclass
class MZStepStatement(MStatement):
    """ZSTEP command - single-step debugging control.

    Controls single-step execution for debugging:
    ZST[EP] [mode[:action]]

    mode: INTO, OVER, OUTOF (controls step behavior)
    action: Code to execute at each step

    Examples:
      ZSTEP - disable single-stepping
      ZSTEP INTO - step into subroutines
      ZSTEP OVER - step over subroutines
      ZSTEP OUTOF - step out of current routine
      ZSTEP INTO:"w x,!" - step into with action
    """

    # Step mode: INTO, OVER, OUTOF, or None (disable)
    mode: Optional[str] = None
    # Action to execute at each step
    action: Optional["MExpr"] = None


@dataclass
class MZGotoArg:
    """Single argument in ZGOTO command.

    ZGOTO level:target - unwind to level and goto target
    ZGOTO @indirection - indirect target
    """

    # Stack level to unwind to
    level: Optional["MExpr"] = None
    # Target to transfer control to
    target: Optional["MExpr"] = None
    # Indirection (alternative to level:target)
    indirection: Optional["MExpr"] = None


@dataclass
class MZGotoStatement(MStatement):
    """ZGOTO command - extended goto with stack unwinding.

    Extended GOTO that can unwind the stack to a specific level:
    ZGO[TO] [level[:target]]

    level: Stack level (0=restart, $ZLEVEL=current)
    target: Label/routine to transfer control to

    Examples:
      ZGOTO - return to direct mode
      ZGOTO 0 - restart from beginning
      ZGOTO 1:label^routine - unwind to level 1 and goto
      ZGOTO $ZLEVEL:label - goto without unwinding
    """

    # ZGOTO arguments
    args: List[MZGotoArg] = field(default_factory=list)


@dataclass
class MZKillStatement(MStatement):
    """ZKILL command - kill variable preserving descendants.

    Kills a variable but preserves its subscripted descendants.
    Opposite of normal KILL behavior. Also known as ZWITHDRAW.

    Examples:
      ZKILL X - kill X but keep X(1), X(2), etc.
      ZKILL myvar(1) - kill myvar(1) but keep myvar(1,1), etc.
    """

    # Variables to zkill
    targets: List["MExpr"] = field(default_factory=list)


@dataclass
class MZWithdrawStatement(MStatement):
    """ZWITHDRAW command - alias for ZKILL.

    GT.M/YottaDB extension. Kills a variable but preserves its descendants.
    Semantically identical to ZKILL.

    Examples:
      ZWITHDRAW X - same as ZKILL X
      zwithdraw ^a(1,2),^b - kill these but preserve descendants
    """

    # Variables to zwithdraw
    targets: List["MExpr"] = field(default_factory=list)


@dataclass
class MZAllocateStatement(MStatement):
    """ZALLOCATE command - incremental lock.

    GT.M/YottaDB extension. Always uses incremental locking (like L +).
    Syntax is similar to LOCK but always incremental.

    Examples:
      Zallocate (@lvar,@gvar):60 - allocate with timeout
      Zallocate:'(i#2) (@lvar,@gvar):60 - with postcondition
      za X:5 - simple allocate with timeout
    """

    targets: List[Any] = field(
        default_factory=list
    )  # Lock target dicts with: target/indirection, timeout, postcondition, indirection_levels
    timeout: Optional["MExpr"] = None


@dataclass
class MZDeallocateStatement(MStatement):
    """ZDEALLOCATE command - decremental unlock.

    GT.M/YottaDB extension. Always uses decremental unlocking (like L -).
    Opposite of ZALLOCATE - releases incremental locks.

    Examples:
      Zdeallocate (@lvar,@gvar) - deallocate list
      Zdeallocate:'(i#2) (@lvar,@gvar) - with postcondition
      zd X - simple deallocate
    """

    targets: List[Any] = field(
        default_factory=list
    )  # Lock target dicts with: target/indirection, indirection_levels


@dataclass
class MZLinkStatement(MStatement):
    """ZLINK command - compile and link routine.

    Compiles and/or links a routine into the current process:
    ZLI[NK] routine[:qualifier]

    Examples:
      ZLINK "routine"
      ZLINK routine
      ZLINK:postcond routine
    """

    # Routine(s) to link
    args: List["MExpr"] = field(default_factory=list)


@dataclass
class MZLoadStatement(MStatement):
    """ZLOAD command - load routine object file.

    Loads a compiled routine object file into memory (YottaDB extension):
    ZL[OAD] routine

    Different from ZLINK - ZLOAD loads without compilation.

    Examples:
      ZLOAD "routine"
      ZL "routine"
    """

    # Routine(s) to load
    args: List["MExpr"] = field(default_factory=list)


@dataclass
class MZPrintArg:
    """Single argument in ZPRINT command.

    Specifies a range of source code to print.
    ZPRINT label^routine - print from label
    ZPRINT label:endlabel - print range
    """

    # Starting label
    start_label: Optional[str] = None
    # Starting offset
    start_offset: Optional["MExpr"] = None
    # Routine name
    routine: Optional[str] = None
    # Routine indirection (for ^@expr)
    routine_indirection: Optional["MExpr"] = None
    # Ending label for range
    end_label: Optional[str] = None
    # Ending offset
    end_offset: Optional["MExpr"] = None


@dataclass
class MZPrintStatement(MStatement):
    """ZPRINT command - print source code.

    Displays source code from the current or specified routine:
    ZP[RINT] [label[:routine]]

    Examples:
      ZPRINT - print current routine
      ZPRINT label - print from label
      ZPRINT label^routine - print from label in routine
      ZPRINT label1:label2 - print range
    """

    # Print arguments
    args: List[MZPrintArg] = field(default_factory=list)


@dataclass
class MZSystemStatement(MStatement):
    """ZSYSTEM command - execute shell command.

    Executes a shell command:
    ZSY[STEM] [command]

    Examples:
      ZSYSTEM - spawn interactive shell
      ZSYSTEM "ls -la"
      ZSYSTEM command_var
    """

    # Shell command(s) to execute
    args: List["MExpr"] = field(default_factory=list)


@dataclass
class MZMessageStatement(MStatement):
    """ZMESSAGE command - generate MUMPS error.

    Generates a MUMPS error:
    ZM[ESSAGE] error_code

    Examples:
      ZMESSAGE 150372994 - generate specific error
      ZM error_code
    """

    # Error code(s) to generate
    args: List["MExpr"] = field(default_factory=list)


@dataclass
class MZTriggerStatement(MStatement):
    """ZTRIGGER command - invoke triggers.

    Invokes triggers associated with global references:
    ZTRIGGER target[,target...]

    Examples:
      ZTRIGGER ^global
      ZTRIGGER ^global(subscript)
      ZTRIGGER ^a,^b - comma-separated globals
      ZTRIGGER @indirection
    """

    # Target expressions (global references or indirection)
    targets: List["MExpr"] = field(default_factory=list)


@dataclass
class MZCompileStatement(MStatement):
    """ZCOMPILE command - compile routine.

    Compiles a routine without linking it:
    ZC[OMPILE] routine

    Examples:
      ZCOMPILE "routine.m"
      ZC routine
    """

    # Routine(s) to compile
    args: List["MExpr"] = field(default_factory=list)


@dataclass
class MZEditStatement(MStatement):
    """ZEDIT command - open routine in editor.

    Opens a routine for editing:
    ZED[IT] routine

    Examples:
      ZEDIT "routine.m"
      ZEDIT @routinename
      ZED routine
    """

    # Routine(s) to edit
    args: List["MExpr"] = field(default_factory=list)


@dataclass
class MZContinueStatement(MStatement):
    """ZCONTINUE command - continue from breakpoint.

    Continues execution after a breakpoint:
    ZC[ONTINUE]

    Used in ZBREAK action strings to resume execution.
    """

    pass
