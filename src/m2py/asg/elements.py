"""ASG Element base classes and core structures.

Defines the foundational elements for the MUMPS Abstract Semantic Graph:
- ASGElement: Base class with source tracking
- MRoutine: Top-level routine container
- MLabel: Entry point with back-references
- MScope: Statement container with recursive walking
- MCall: Reference to labels with resolution tracking
- MParseError: Parse error information for error-tolerant parsing
"""

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterator, List, Optional

if TYPE_CHECKING:  # pragma: no cover
    from m2py.asg.statements import MStatement
    from m2py.asg.enums import CallType
    from m2py.asg.expressions import MActualParameter, MExpr


@dataclass
class MParseError:
    """Parse error information for error-tolerant parsing.

    Captures details about lines that failed to parse, allowing the parser
    to continue processing remaining content while preserving error information
    for later reporting.

    This is NOT an ASGElement as it represents a failure to produce ASG nodes,
    not an actual semantic element. It's a data structure for error collection.
    """

    line_number: int
    column: int = 0
    message: str = ""
    line_content: str = ""  # The original line text that failed to parse


@dataclass
class ASGElement(ABC):
    """Base class for all ASG elements.

    Provides source tracking (file, line, column) and tree structure
    (parent reference) for all ASG nodes.

    Note: textX automatically adds _tx_position and _tx_position_end attributes
    to parsed objects. We use our own source tracking fields (line_number,
    column, end_line, end_column) which are more useful for error reporting.
    """

    # Source tracking
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None

    # Tree structure
    parent: Optional["ASGElement"] = field(default=None, repr=False)


@dataclass
class MScope(ASGElement):
    """A container for statements (label body, IF body, FOR body).

    Provides recursive statement walking. Parent references are tracked
    via the inherited `parent` field from ASGElement, and statement scope
    via the `scope` field on each statement.
    """

    statements: List["MStatement"] = field(default_factory=list)

    def walk_statements(self) -> Iterator["MStatement"]:
        """Yield all statements recursively, including nested scopes.

        Walks through all statements in this scope and recurses into
        any nested scopes (IF bodies, FOR bodies, etc.).
        """
        from m2py.asg.type_helpers import get_body_scope, get_then_scope

        for stmt in self.statements:
            yield stmt
            # Recurse into nested scopes using type-safe helpers
            body = get_body_scope(stmt)
            if body is not None:
                yield from body.walk_statements()
            then_scope = get_then_scope(stmt)
            if then_scope is not None:
                yield from then_scope.walk_statements()


@dataclass
class MLabel(ASGElement):
    """A label (entry point) in a routine.

    Represents a named location that can be called with DO or jumped to
    with GOTO. Tracks formal parameters, body statements, and back-references
    from callers.
    """

    name: str = ""
    formal_list: List[str] = field(default_factory=list)
    body: MScope = field(default_factory=MScope)

    # Back-references (populated in resolution pass)
    callers: List["MCall"] = field(default_factory=list, repr=False)
    goto_sources: List[Any] = field(default_factory=list, repr=False)  # MGotoStatement

    # Variable analysis (populated in analysis pass)
    variables_read: set = field(default_factory=set, repr=False)
    variables_written: set = field(default_factory=set, repr=False)
    variables_newed: set = field(default_factory=set, repr=False)
    input_variables: set = field(default_factory=set, repr=False)
    output_variables: set = field(default_factory=set, repr=False)

    # Function signature (populated by compute_signatures)
    signature: Optional[Any] = field(default=None, repr=False)  # FunctionSignature

    # Spec 006 (T069a): Self-loop flag (populated by classify_gotos)
    # True if label contains intra-label backward GOTO to itself (creates while True: pattern)
    has_self_loop: bool = False

    # Spec 011: NEW statement presence flag (populated by variable analysis)
    # True if label contains any MNewStatement (NEW, NEW X, NEW (X))
    # Used by codegen to determine if NewScopeManager context is needed
    has_new_statements: bool = False

    # Spec 013: Fall-through flag (populated by semantic analyzer)
    # True if label should fall through to the next label when it completes
    # (i.e., it doesn't end with QUIT, GOTO, or HALT)
    needs_fallthrough: bool = False

    # Spec 013: Next label reference (populated by semantic analyzer)
    # Points to the next label in sequence for fall-through, None if last label
    next_label: Optional["MLabel"] = field(default=None, repr=False)

    # Parser internal: stores unparsed line content and parsed results
    _line_rest: Optional[str] = field(default=None, repr=False)
    _parsed_content: Optional[Any] = field(default=None, repr=False)
    _parsed_commands: Optional[List[Any]] = field(default=None, repr=False)
    _dot_level: Optional[int] = field(default=None, repr=False)

    @property
    def has_explicit_exit(self) -> bool:
        """Check if label ends with an explicit exit (QUIT, GOTO, or HALT).

        Returns True if the last non-unreachable statement in the label body
        is an unconditional exit statement. Labels without explicit exits
        implicitly return when they fall through to the end.
        """
        from m2py.asg.statements import MQuitStatement, MGotoStatement, MHaltStatement

        if not self.body or not self.body.statements:
            return False

        # Find the last non-unreachable statement
        last_stmt = None
        for stmt in reversed(self.body.statements):
            if not getattr(stmt, "is_unreachable", False):
                last_stmt = stmt
                break

        if last_stmt is None:
            return False

        # Check if it's an unconditional exit
        if isinstance(last_stmt, (MQuitStatement, MGotoStatement, MHaltStatement)):
            return last_stmt.postcondition is None

        return False


@dataclass
class MRoutine(ASGElement):
    """A MUMPS routine (source file).

    The top-level container for a MUMPS program, containing all labels
    and their statements. Tracks analysis flags for transpilation hints.

    The source_lines field stores the original source code lines for
    $TEXT function support during code generation. $TEXT returns the
    actual source line text at runtime, so the code generator needs
    access to the original source.

    The parse_errors field collects any parse errors encountered during
    parsing, allowing error-tolerant parsing that continues even when
    some lines fail to parse. Errors can be inspected after parsing.
    """

    name: str = ""
    labels: List[MLabel] = field(default_factory=list)

    # Original source lines for $TEXT support (1-indexed access via source_lines[line_num-1])
    source_lines: List[str] = field(default_factory=list, repr=False)

    # Parse errors encountered during parsing (for error-tolerant mode)
    parse_errors: List["MParseError"] = field(default_factory=list, repr=False)

    # T102: Pre-computed codegen hint (populated by classify_gotos)
    needs_loop_exit_exception: bool = False  # True if any MULTI_LOOP_EXIT GOTO exists

    # Spec 006 (T033): Trampoline pattern flag (populated by classify_gotos)
    # True if ANY cross-label GOTOs exist - requires trampoline for proper control flow
    needs_trampoline: bool = False

    # Spec 006 (T039a): Variables needing RoutineState fields (populated by compute_all_signatures)
    # Union of all label's output_variables that are read by other labels (cross-label flow)
    routine_state_vars: set = field(default_factory=set, repr=False)

    # Spec 006 (T039b): Variables with subscripted access requiring MArray fields
    # Populated by compute_all_signatures when subscripted local variable access detected
    array_vars: set = field(default_factory=set, repr=False)

    # Variables that are read but never written in the routine (input-only from caller).
    # These must be read from _scope in TRAMPOLINE mode since they come from external
    # callers via GOTO. Populated by compute_all_signatures.
    routine_input_only_vars: set = field(default_factory=set, repr=False)

    # Spec 007: True if any GOTO/DO has offset expression (populated by classify_gotos)
    # Triggers TRAMPOLINE strategy and _line_map generation for line-based dispatch
    has_offset_calls: bool = False

    # Spec 017: True if any argumentless KILL (K with no args) exists in routine
    # Requires runtime local variable tracking (state._locals dict) in TRAMPOLINE mode
    has_argumentless_kill: bool = False

    # Spec 017: True if any argumentless NEW (N with no args) exists in routine
    # Requires runtime scope stack (state._new_stack) in TRAMPOLINE mode
    has_argumentless_new: bool = False

    # True if routine has name indirection that references local variables
    # This requires dynamic_locals mode for runtime variable name resolution
    has_name_indirection_on_locals: bool = False

    # True if routine has external GOTOs (G ^ROUTINE, G LABEL^ROUTINE, etc.)
    # External GOTOs need all local variables synced to _scope for MUMPS semantics
    has_external_gotos: bool = False

    def get_label(self, name: str) -> Optional[MLabel]:
        """Look up label by name.

        Args:
            name: The label name to find.

        Returns:
            The MLabel if found, None otherwise.
        """
        for label in self.labels:
            if label.name == name:
                return label
        return None

    def add_label(self, label: MLabel) -> None:
        """Add a label to this routine, setting its parent reference."""
        label.parent = self
        self.labels.append(label)


@dataclass
class MCall(ASGElement):
    """A reference to a label (for DO/GOTO/extrinsic).

    Represents a call or jump target that may or may not be resolved
    to an actual MLabel. Tracks resolution status and call type.

    For indirect calls (D @VAR, D @@VAR^@ROUTINE), the indirection
    fields capture the structure for runtime evaluation.
    """

    name: str = ""
    offset: Optional["MExpr"] = None  # For label+offset expressions
    routine: Optional[str] = None  # For ^routine external calls
    arguments: List["MActualParameter"] = field(default_factory=list)
    postcondition: Optional["MExpr"] = None  # Conditional execution expression
    indirection: Optional["MExpr"] = None  # For DO @expr indirection (label part)
    routine_indirection: Optional["MExpr"] = None  # For ^@expr (routine part)

    # Indirection analysis flags
    label_is_indirect: bool = False  # True if label comes from indirection
    routine_is_indirect: bool = False  # True if routine comes from indirection

    # Resolution (populated in resolution pass)
    target: Optional[MLabel] = field(default=None, repr=False)
    call_type: Optional["CallType"] = None
    is_resolved: bool = False
