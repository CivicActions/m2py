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
from m2py.asg.enums import ForLoopType, ForParamType, GotoType

if TYPE_CHECKING:
    from m2py.asg.elements import MCall
    from m2py.asg.expressions import MExpr, MVariable


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

    Note: This is a sub-component of MSetStatement, not a standalone ASG node.
    It inherits source position context from its containing MSetStatement.
    This design avoids adding unused source tracking overhead (~40 bytes per instance).
    """

    target: Any = None  # MVariable, MGlobal, or MIndirection
    value: Optional["MExpr"] = None
    postcondition: Optional["MExpr"] = None  # Individual assignment postcondition


@dataclass
class MSetStatement(MStatement):
    """SET command - variable assignment.

    Assigns values to one or more targets:
    SET X=1, SET A=1,B=2, SET (A,B)=1
    """

    assignments: List[MAssignment] = field(default_factory=list)


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

    Note: This is a sub-component of MReadStatement, not a standalone ASG node.
    It inherits source position context from its containing MReadStatement.
    This design avoids adding unused source tracking overhead (~40 bytes per instance).
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

    Note: This is a sub-component of MForStatement, not a standalone ASG node.
    It inherits source position context from its containing MForStatement.
    This design avoids adding unused source tracking overhead (~40 bytes per instance).
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


# =============================================================================
# Control Flow - Jumps
# =============================================================================


@dataclass
class MGotoStatement(MStatement):
    """GOTO command.

    Transfers control to a label:
    G label, G label^routine, G label:condition
    """

    targets: List["MCall"] = field(default_factory=list)

    # Classification (populated in analysis pass)
    goto_type: Optional[GotoType] = None
    exits_loops: List["MForStatement"] = field(default_factory=list, repr=False)
    is_cross_label: bool = False  # True if target is in a different label
    is_loop_continue: bool = False


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

    targets: List[Any] = field(
        default_factory=list
    )  # MVariable, MGlobal - selective kill targets
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

    @property
    def destination(self) -> Any:
        """Backward-compatible access to first merge destination.

        Returns first merge pair's destination or None if empty.
        """
        return self.merges[0].destination if self.merges else None

    @property
    def source(self) -> Any:
        """Backward-compatible access to first merge source.

        Returns first merge pair's source or None if empty.
        """
        return self.merges[0].source if self.merges else None


# =============================================================================
# Other Statements
# =============================================================================


@dataclass
class MHangStatement(MStatement):
    """HANG command - pause execution.

    Pauses for specified seconds:
    H 5, HANG seconds
    """

    duration: Optional["MExpr"] = None


@dataclass
class MHaltStatement(MStatement):
    """HALT command - terminate execution.

    Stops the current job:
    H (argumentless), HALT
    """

    pass


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

    targets: List[Any] = field(default_factory=list)
    lock_type: str = ""  # "", "+", "-"
    timeout: Optional["MExpr"] = None


@dataclass
class MViewStatement(MStatement):
    """VIEW command - implementation-specific.

    Access to implementation-specific features:
    V expr, VIEW expr
    """

    keyword: Optional["MExpr"] = None
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

    @property
    def device_expr(self) -> Optional["MExpr"]:
        """Backward-compatible access to first device expression."""
        return self.devices[0].device_expr if self.devices else None

    @property
    def parameters(self) -> List["MExpr"]:
        """Backward-compatible access to first device parameters."""
        return self.devices[0].parameters if self.devices else []

    @property
    def timeout(self) -> Optional["MExpr"]:
        """Backward-compatible access to first device timeout."""
        return self.devices[0].timeout if self.devices else None


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

    @property
    def device_expr(self) -> Optional["MExpr"]:
        """Backward-compatible access to first device expression."""
        return self.devices[0].device_expr if self.devices else None

    @property
    def parameters(self) -> List["MExpr"]:
        """Backward-compatible access to first device parameters."""
        return self.devices[0].parameters if self.devices else []


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

    @property
    def device_expr(self) -> Optional["MExpr"]:
        """Backward-compatible access to first device expression."""
        return self.devices[0].device_expr if self.devices else None

    @property
    def parameters(self) -> List["MExpr"]:
        """Backward-compatible access to first device parameters."""
        return self.devices[0].parameters if self.devices else []


@dataclass
class MJobStatement(MStatement):
    """JOB command - start concurrent job.

    Starts one or more new processes executing routines:
    J label, JOB label^routine:parameters, J LABEL1,LABEL2

    Supports multiple targets per MUMPS 1995 spec:
    J LABEL1,LABEL2 starts two concurrent jobs

    Supports indirection per MUMPS spec:
    J @VAR, J @VAR^ROUTINE, J @VAR^@ROUTINEVAR
    """

    targets: List["MCall"] = field(default_factory=list)
    parameters: List["MExpr"] = field(default_factory=list)
    timeout: Optional["MExpr"] = None

    @property
    def calls(self) -> List["MCall"]:
        """Backward-compatible alias for targets.

        Deprecated: Use `targets` instead for consistency with MDoStatement.
        """
        return self.targets

    @property
    def call(self) -> Optional["MCall"]:
        """Backward-compatible access to first call target."""
        return self.targets[0] if self.targets else None
