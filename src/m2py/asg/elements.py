"""ASG Element base classes and core structures.

Defines the foundational elements for the MUMPS Abstract Semantic Graph:
- ASGElement: Base class with source tracking
- MRoutine: Top-level routine container
- MLabel: Entry point with back-references
- MScope: Statement container with recursive walking
- MCall: Reference to labels with resolution tracking
"""

from abc import ABC
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterator, List, Optional

if TYPE_CHECKING:
    from m2py.asg.statements import MStatement, MForStatement, MDoBlockStatement
    from m2py.asg.enums import CallType


@dataclass
class ASGElement(ABC):
    """Base class for all ASG elements.
    
    Provides source tracking (file, line, column) and tree structure
    (parent reference) for all ASG nodes.
    """
    
    # Source tracking
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    
    # Tree structure
    parent: Optional["ASGElement"] = field(default=None, repr=False)
    
    # textX integration - position in source text
    _tx_position: Optional[int] = field(default=None, repr=False)
    _tx_position_end: Optional[int] = field(default=None, repr=False)
    
    def to_dict(self, include_position: bool = False, max_depth: int = 10) -> dict:
        """Serialize this ASG element to a dictionary.
        
        Args:
            include_position: Include source position information
            max_depth: Maximum recursion depth to prevent infinite loops
            
        Returns:
            Dictionary representation of this element
        """
        if max_depth <= 0:
            return {"_type": self.__class__.__name__, "_truncated": True}
        
        result = {"_type": self.__class__.__name__}
        
        if include_position:
            if self.source_file:
                result["source_file"] = self.source_file
            if self.line_number is not None:
                result["line"] = self.line_number
            if self.column is not None:
                result["column"] = self.column
        
        # Serialize dataclass fields (excluding private/internal ones)
        for field_name in self.__dataclass_fields__:
            if field_name.startswith("_") or field_name == "parent":
                continue
            if field_name in ("source_file", "line_number", "column", "end_line", "end_column"):
                continue  # Handled above
                
            value = getattr(self, field_name)
            result[field_name] = self._serialize_value(value, include_position, max_depth - 1)
        
        return result
    
    def _serialize_value(self, value, include_position: bool, max_depth: int):
        """Recursively serialize a value for to_dict()."""
        if value is None:
            return None
        elif isinstance(value, ASGElement):
            return value.to_dict(include_position, max_depth)
        elif isinstance(value, set):
            return [self._serialize_value(v, include_position, max_depth) for v in sorted(value, key=str)]
        elif isinstance(value, list):
            return [self._serialize_value(v, include_position, max_depth) for v in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v, include_position, max_depth) for k, v in value.items()}
        elif hasattr(value, 'name') and hasattr(value, 'value'):  # Enum
            return value.name
        elif hasattr(value, '__dataclass_fields__'):  # Non-ASG dataclass
            return {f: self._serialize_value(getattr(value, f), include_position, max_depth) 
                    for f in value.__dataclass_fields__ if not f.startswith("_")}
        else:
            return value


@dataclass
class MScope(ASGElement):
    """A container for statements (label body, IF body, FOR body).
    
    Provides recursive statement walking and parent scope tracking
    for proper scoping resolution.
    """
    
    statements: List["MStatement"] = field(default_factory=list)
    parent_scope: Optional["MScope"] = field(default=None, repr=False)
    
    def add_statement(self, stmt: "MStatement") -> None:
        """Add a statement to this scope, setting its parent references."""
        stmt.parent = self
        stmt.scope = self
        self.statements.append(stmt)
    
    def walk_statements(self) -> Iterator["MStatement"]:
        """Yield all statements recursively, including nested scopes.
        
        Walks through all statements in this scope and recurses into
        any nested scopes (IF bodies, FOR bodies, etc.).
        """
        for stmt in self.statements:
            yield stmt
            # Recurse into nested scopes
            if hasattr(stmt, "body") and isinstance(stmt.body, MScope):
                yield from stmt.body.walk_statements()
            if hasattr(stmt, "then_scope") and isinstance(stmt.then_scope, MScope):
                yield from stmt.then_scope.walk_statements()
            if hasattr(stmt, "else_scope") and stmt.else_scope is not None:
                yield from stmt.else_scope.walk_statements()


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
            if not getattr(stmt, 'is_unreachable', False):
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
    """
    
    name: str = ""
    labels: List[MLabel] = field(default_factory=list)
    
    # Analysis annotations
    has_unstructured_goto: bool = False
    requires_runtime_eval: bool = False  # Has unresolvable indirection
    global_refs: List[Any] = field(default_factory=list)  # MGlobal references
    
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
    offset: Optional[Any] = None  # MExpr for label+offset
    routine: Optional[str] = None  # For ^routine external calls
    arguments: List[Any] = field(default_factory=list)  # MExpr arguments
    postcondition: Optional[Any] = None  # MExpr condition
    indirection: Optional[Any] = None  # MExpr for DO @expr indirection (label part)
    routine_indirection: Optional[Any] = None  # MExpr for ^@expr (routine part)
    
    # Indirection analysis flags
    label_is_indirect: bool = False  # True if label comes from indirection
    routine_is_indirect: bool = False  # True if routine comes from indirection
    indirection_levels: int = 0  # Number of @ levels (1 for @A, 2 for @@A, etc.)
    
    # Resolution (populated in resolution pass)
    target: Optional[MLabel] = field(default=None, repr=False)
    call_type: Optional["CallType"] = None
    is_resolved: bool = False

