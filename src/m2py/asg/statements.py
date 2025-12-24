"""ASG Statement elements.

Defines all statement types for the MUMPS ASG:
- MStatement: Base statement class
- Control flow: MIfStatement, MElseStatement, MForStatement, MGotoStatement
- Subroutines: MDoStatement, MDoBlockStatement, MQuitStatement
- Data: MSetStatement, MWriteStatement, MReadStatement
- Variables: MNewStatement, MKillStatement, MMergeStatement
- Other: MHangStatement, MHaltStatement, MXecuteStatement, MLockStatement, MViewStatement, MBreakStatement
"""

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

    condition: Optional["MExpr"] = None  # Single condition (legacy support)
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
    goto_exits_loop: bool = False
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
    is_loop_continue: bool = False


# =============================================================================
# Subroutine Statements
# =============================================================================


@dataclass
class MDoStatement(MStatement):
    """DO command - call subroutine or inline block.

    When targets are present, calls one or more labels:
    DO label, D label^routine, D label(args)

    When targets are empty (argumentless DO), creates a block scope
    for following dot-indented lines:
    DO
    . command1
    . command2
    """

    targets: List["MCall"] = field(default_factory=list)
    body: MScope = field(default_factory=MScope)  # For argumentless DO block


@dataclass
class MDoBlockStatement(MStatement):
    """Argumentless DO - inline scope block.

    Creates an indented block scope:
    DO
    . command1
    . command2
    """

    body: MScope = field(default_factory=MScope)


@dataclass
class MQuitStatement(MStatement):
    """QUIT command.

    Returns from current context:
    Q, Q value (return from extrinsic), Q:condition
    """

    return_value: Optional["MExpr"] = None

    # Context (populated in analysis pass)
    exits_for: Optional["MForStatement"] = field(default=None, repr=False)
    exits_do_block: Optional["MDoBlockStatement"] = field(default=None, repr=False)


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


@dataclass
class MMergeStatement(MStatement):
    """MERGE command - copy tree structures.

    Copies entire variable trees:
    M ^DEST=^SOURCE, MERGE LOCAL=^GLOBAL
    """

    destination: Any = None  # MVariable or MGlobal
    source: Any = None  # MVariable or MGlobal


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
class MOpenStatement(MStatement):
    """OPEN command - open device for I/O.

    Opens a device for input/output:
    O device, OPEN device:parameters
    """

    device_expr: Optional["MExpr"] = None
    parameters: List["MExpr"] = field(default_factory=list)
    timeout: Optional["MExpr"] = None


@dataclass
class MCloseStatement(MStatement):
    """CLOSE command - close device.

    Closes a device:
    C device, CLOSE device:parameters
    """

    device_expr: Optional["MExpr"] = None
    parameters: List["MExpr"] = field(default_factory=list)


@dataclass
class MUseStatement(MStatement):
    """USE command - select current device.

    Makes device current I/O device:
    U device, USE device:parameters
    """

    device_expr: Optional["MExpr"] = None
    parameters: List["MExpr"] = field(default_factory=list)


@dataclass
class MJobStatement(MStatement):
    """JOB command - start concurrent job.

    Starts a new process executing a routine:
    J label, JOB label^routine:parameters
    """

    call: Optional["MCall"] = None
    parameters: List["MExpr"] = field(default_factory=list)
    timeout: Optional["MExpr"] = None
