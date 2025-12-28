# Data Model: MUMPS Abstract Semantic Graph (ASG)

**Feature**: 001-textx-semantic-graph  
**Date**: 2025-12-19  
**Purpose**: Define the ASG element hierarchy for MUMPS semantic representation

---

## Overview

The Abstract Semantic Graph (ASG) represents the semantic meaning of MUMPS programs, not just their syntax. Key distinctions from an AST:

- **Resolved references**: Labels are linked, not string names
- **Classified patterns**: FOR loops and GOTOs have type annotations
- **Back-references**: Labels know their callers
- **Scope containers**: Control structures contain their child statements

---

## Two-Layer Architecture

The M2PY parser uses a **two-layer approach** for textX integration:

### Layer 1: textX Custom Classes (CST Layer)

Located in `src/m2py/parser/textx_classes.py`, these classes:
- Are instantiated directly by textX during parsing
- Have names matching grammar rules (e.g., `NumericLiteral`, `LocalVariable`)
- Accept textX's constructor convention: `parent` as first parameter
- **Inherit from ASG classes** for seamless integration

```python
# textX creates: NumericLiteral(parent=<textx parent>, value="42")
class NumericLiteral(MLiteral):
    def __init__(self, parent=None, value: str = ""):
        # textX passes parent, we parse the value
        parsed = int(value)
        object.__setattr__(self, 'value', parsed)
        object.__setattr__(self, 'literal_type', LiteralType.INTEGER)
```

### Layer 2: ASG Domain Objects

Located in `src/m2py/asg/`, these are the primary domain classes:
- `MLiteral`, `MVariable`, `MGlobal` - Expressions
- `MForStatement`, `MGotoStatement` - Statements  
- `MRoutine`, `MLabel`, `MScope` - Structure

**Relationship**: textX custom classes **inherit from** ASG classes:
```
NumericLiteral(MLiteral)     # textX creates NumericLiteral → IS-A MLiteral
StringLiteral(MLiteral)
LocalVariable(MVariable)     # textX creates LocalVariable → IS-A MVariable
GlobalVariable(MGlobal)
```

This design means:
1. **Isinstance checks work**: `isinstance(node, MLiteral)` returns True for NumericLiteral
2. **Uniform API**: All code works with ASG types regardless of creation path
3. **Two creation paths**:
   - textX parsing → NumericLiteral/LocalVariable/etc (via custom classes)
   - Direct construction → MLiteral/MVariable/etc (for tests, analysis)

---

## Entity Hierarchy

```
ASGElement (abstract base)
├── MRoutine                    # Top-level routine (file)
│   └── labels: List[MLabel]
│
├── MLabel                      # Named entry point
│   ├── formal_list: List[str]  # Parameters
│   ├── statements: MScope      # Body
│   └── callers: List[MCall]    # Back-references
│
├── MScope                      # Statement container
│   ├── statements: List[MStatement]
│   └── parent_scope: MScope?
│
├── MStatement (abstract)       # Command base
│   ├── MSetStatement
│   ├── MWriteStatement
│   ├── MReadStatement
│   ├── MIfStatement
│   ├── MElseStatement
│   ├── MForStatement
│   ├── MDoStatement
│   ├── MGotoStatement
│   ├── MQuitStatement
│   ├── MNewStatement
│   ├── MKillStatement
│   ├── MHangStatement
│   ├── MHaltStatement
│   ├── MXecuteStatement
│   ├── MLockStatement
│   ├── MMergeStatement
│   └── MViewStatement
│
├── MExpr (abstract)            # Expression base
│   ├── MLiteral
│   ├── MVariable
│   ├── MGlobal
│   ├── MNakedGlobal
│   ├── MBinaryOp
│   ├── MUnaryOp
│   ├── MIntrinsicFunction
│   ├── MExtrinsicFunction
│   ├── MPatternMatch
│   └── MIndirection
│
├── MCall                       # Reference to label
│   ├── target: MLabel?         # Resolved reference
│   ├── routine: str?           # External routine
│   └── call_type: CallType
│
└── MForParameter               # FOR loop parameter
    ├── param_type: ForParamType
    ├── value: MExpr?           # For string-list
    ├── start: MExpr?           # For range
    ├── step: MExpr?
    └── end: MExpr?
```

---

## Core Elements

### ASGElement (Base)

```python
from dataclasses import dataclass, field
from typing import List, Optional, Any
from abc import ABC

@dataclass
class ASGElement(ABC):
    """Base class for all ASG elements."""
    
    # Source tracking
    source_file: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    
    # Tree structure
    parent: Optional['ASGElement'] = field(default=None, repr=False)
    
    # textX integration
    _tx_position: Optional[int] = field(default=None, repr=False)
    _tx_position_end: Optional[int] = field(default=None, repr=False)
```

### MRoutine

```python
@dataclass
class MRoutine(ASGElement):
    """A MUMPS routine (source file)."""
    
    name: str = ""
    labels: List['MLabel'] = field(default_factory=list)
    
    # Analysis annotations
    has_unstructured_goto: bool = False
    requires_runtime_eval: bool = False  # Has unresolvable indirection
    global_refs: List[str] = field(default_factory=list)  # Names of ^GLOBAL references (strings for efficiency)
    
    def get_label(self, name: str) -> Optional['MLabel']:
        """Look up label by name."""
        for label in self.labels:
            if label.name == name:
                return label
        return None
```

### MLabel

```python
@dataclass
class MLabel(ASGElement):
    """A label (entry point) in a routine."""
    
    name: str = ""
    formal_list: List[str] = field(default_factory=list)
    body: 'MScope' = field(default_factory=lambda: MScope())
    
    # Back-references (populated in resolution pass)
    callers: List['MCall'] = field(default_factory=list, repr=False)
    goto_sources: List['MGotoStatement'] = field(default_factory=list, repr=False)
    
    # Variable analysis (populated in analysis pass)
    variables_read: set = field(default_factory=set, repr=False)
    variables_written: set = field(default_factory=set, repr=False)
    variables_newed: set = field(default_factory=set, repr=False)
    input_variables: set = field(default_factory=set, repr=False)  # Computed
    output_variables: set = field(default_factory=set, repr=False)  # Computed
```

### MScope

```python
@dataclass
class MScope(ASGElement):
    """A container for statements (label body, IF body, FOR body)."""
    
    statements: List['MStatement'] = field(default_factory=list)
    parent: Optional['ASGElement'] = field(default=None, repr=False)  # MLabel, MIfStatement, MForStatement, etc.
    
    def add_statement(self, stmt: 'MStatement') -> None:
        stmt.parent = self
        stmt.scope = self
        self.statements.append(stmt)
    
    def walk_statements(self):
        """Yield all statements recursively."""
        for stmt in self.statements:
            yield stmt
            if hasattr(stmt, 'body') and isinstance(stmt.body, MScope):
                yield from stmt.body.walk_statements()
            if hasattr(stmt, 'then_scope'):
                yield from stmt.then_scope.walk_statements()
            if hasattr(stmt, 'else_scope') and stmt.else_scope:
                yield from stmt.else_scope.walk_statements()
```

> **Note**: The `parent` field points to the containing ASGElement (MLabel, MIfStatement, MForStatement, etc.),
> not a parent MScope. For scoping analysis, use `stmt.scope` on statements.
```

---

## Statement Elements

### MStatement (Base)

```python
@dataclass
class MStatement(ASGElement):
    """Base class for all statements."""
    
    scope: Optional[MScope] = field(default=None, repr=False)
    postcondition: Optional['MExpr'] = None
    
    # Analysis flags
    is_unreachable: bool = False
```

### MSetStatement

```python
@dataclass
class MAssignment:
    """Single assignment within SET."""
    target: 'MReference'
    value: 'MExpr'
    postcondition: Optional['MExpr'] = None

@dataclass
class MSetStatement(MStatement):
    """SET command - variable assignment."""
    
    assignments: List[MAssignment] = field(default_factory=list)
```

### MIfStatement / MElseStatement

```python
@dataclass
class MIfStatement(MStatement):
    """IF command with conditional body."""
    
    condition: Optional['MExpr'] = None  # None = uses $TEST
    then_scope: MScope = field(default_factory=MScope)

@dataclass
class MElseStatement(MStatement):
    """ELSE command (uses $TEST)."""
    
    body: MScope = field(default_factory=MScope)
```

### MForStatement

```python
from enum import Enum, auto

class ForLoopType(Enum):
    BOUNDED = auto()      # F I=1:1:10
    OPEN_ENDED = auto()   # F I=1:1
    STRING_LIST = auto()  # F I="A","B"
    MIXED = auto()        # F I="A",1:1:3
    ARGUMENTLESS = auto() # F

class ForParamType(Enum):
    VALUE = auto()        # Single expr
    RANGE = auto()        # start:step:end
    OPEN_RANGE = auto()   # start:step

@dataclass
class MForParameter:
    """Single forparameter in FOR command."""
    
    param_type: ForParamType = ForParamType.VALUE
    value: Optional['MExpr'] = None      # For VALUE type
    start: Optional['MExpr'] = None      # For RANGE types
    step: Optional['MExpr'] = None
    end: Optional['MExpr'] = None

@dataclass
class MForStatement(MStatement):
    """FOR command with loop body."""
    
    loop_var: Optional[str] = None
    parameters: List[MForParameter] = field(default_factory=list)
    body: MScope = field(default_factory=MScope)
    
    # Classification (populated in analysis pass)
    loop_type: Optional[ForLoopType] = None
    has_internal_quit: bool = False
    has_internal_goto: bool = False
    exit_points: List['MStatement'] = field(default_factory=list, repr=False)
```

### MGotoStatement

```python
class GotoType(Enum):
    FORWARD_JUMP = auto()
    BACKWARD_JUMP = auto()
    LOOP_EXIT = auto()
    MULTI_LOOP_EXIT = auto()
    CROSS_LABEL = auto()
    EXTERNAL = auto()
    UNRESOLVED = auto()

@dataclass
class MGotoStatement(MStatement):
    """GOTO command."""
    
    targets: List['MCall'] = field(default_factory=list)  # May have multiple with postconditions
    
    # Classification (populated in analysis pass)
    goto_type: Optional[GotoType] = None
    exits_loops: List['MForStatement'] = field(default_factory=list, repr=False)
    is_loop_continue: bool = False
```

### MDoStatement

```python
@dataclass
class MDoStatement(MStatement):
    """DO command - call subroutine or inline block.
    
    Handles both labeled calls (targets populated) and
    argumentless DO blocks (targets empty, body populated).
    """
    
    targets: List['MCall'] = field(default_factory=list)
    body: MScope = field(default_factory=MScope)  # For argumentless DO
```

### MQuitStatement

```python
@dataclass
class MQuitStatement(MStatement):
    """QUIT command."""
    
    return_value: Optional['MExpr'] = None
    
    # Context (populated in analysis pass)
    exits_for: Optional['MForStatement'] = field(default=None, repr=False)
    exits_do_block: Optional['MDoStatement'] = field(default=None, repr=False)  # Argumentless DO
```

### MNewStatement

```python
@dataclass
class MNewStatement(MStatement):
    """NEW command - variable scoping."""
    
    variables: List[str] = field(default_factory=list)
    exclusive: bool = False  # NEW (X) = all except X
    except_list: List[str] = field(default_factory=list)
```

### MXecuteStatement

```python
@dataclass
class MXecuteStatement(MStatement):
    """XECUTE command - runtime code execution."""
    
    code_expressions: List['MExpr'] = field(default_factory=list)
    
    # Always requires runtime support
    requires_runtime_eval: bool = True
```

---

## Expression Elements

### MExpr (Base)

```python
@dataclass
class MExpr(ASGElement):
    """Base class for expressions."""
    
    # Type annotation (may be computed)
    result_type: Optional[str] = None  # "string", "number", "unknown"
```

### Literals

```python
class LiteralType(Enum):
    STRING = auto()
    INTEGER = auto()
    DECIMAL = auto()

@dataclass
class MLiteral(MExpr):
    """Literal value."""
    
    value: Any = None
    literal_type: LiteralType = LiteralType.STRING
```

### Variables

```python
@dataclass
class MVariable(MExpr):
    """Local variable reference."""
    
    name: str = ""
    subscripts: List['MExpr'] = field(default_factory=list)

@dataclass
class MGlobal(MExpr):
    """Global variable reference."""
    
    name: str = ""
    subscripts: List['MExpr'] = field(default_factory=list)

@dataclass
class MNakedGlobal(MExpr):
    """Naked global reference ^(subs) - uses last global context."""
    
    subscripts: List['MExpr'] = field(default_factory=list)
    requires_runtime_tracking: bool = True
```

### Operations

```python
@dataclass
class MBinaryOp(MExpr):
    """Binary operation."""
    
    operator: str = ""  # +, -, *, /, \, #, **, =, <, >, &, !, _, [, ], ]]
    left: Optional['MExpr'] = None
    right: Optional['MExpr'] = None

@dataclass
class MUnaryOp(MExpr):
    """Unary operation."""
    
    operator: str = ""  # +, -, '
    operand: Optional['MExpr'] = None
```

### Functions

```python
@dataclass
class MIntrinsicFunction(MExpr):
    """Intrinsic function call ($LENGTH, $PIECE, etc.)."""
    
    name: str = ""
    arguments: List['MExpr'] = field(default_factory=list)

@dataclass
class MExtrinsicFunction(MExpr):
    """Extrinsic function call ($$FUNC^ROUTINE)."""
    
    target: 'MCall' = field(default_factory=lambda: MCall())
    arguments: List['MExpr'] = field(default_factory=list)
```

### Special Expressions

```python
@dataclass
class MPatternMatch(MExpr):
    """Pattern match expression (X?1A.N)."""
    
    subject: Optional['MExpr'] = None
    pattern: str = ""  # Raw pattern string
    pattern_indirect: Optional['MExpr'] = None  # For ?@X

@dataclass
class MIndirection(MExpr):
    """Indirection expression (@variable)."""
    
    expression: Optional['MExpr'] = None
    indirection_type: str = ""  # "name", "subscript", "argument"
    
    # Analysis flags
    can_resolve_statically: bool = False
    resolved_value: Optional[str] = None

@dataclass
class MSpecialVariable(MExpr):
    """Special variable reference ($TEST, $HOROLOG, etc.)."""
    
    name: str = ""  # Without $
```

---

## Reference Elements

### MCall

```python
class CallType(Enum):
    LABEL_CALL = auto()       # DO label
    OFFSET_CALL = auto()      # DO label+offset
    ROUTINE_CALL = auto()     # DO label^routine
    INDIRECT_CALL = auto()    # DO @expr
    UNRESOLVED = auto()

@dataclass
class MCall(ASGElement):
    """A reference to a label (for DO/GOTO/extrinsic)."""
    
    name: str = ""
    offset: Optional['MExpr'] = None  # For label+offset
    routine: Optional[str] = None     # For ^routine
    postcondition: Optional['MExpr'] = None
    
    call_type: CallType = CallType.UNRESOLVED
    
    # Resolution (populated in resolution pass)
    target: Optional['MLabel'] = field(default=None, repr=False)
    
    def is_resolved(self) -> bool:
        return self.call_type != CallType.UNRESOLVED and self.target is not None
    
    def is_external(self) -> bool:
        return self.routine is not None
```

---

## Validation Rules

### Entity Relationships

| Entity | Relationship | Target | Cardinality |
|--------|--------------|--------|-------------|
| MRoutine | contains | MLabel | 1:N |
| MLabel | has | MScope (body) | 1:1 |
| MScope | contains | MStatement | 1:N |
| MStatement | has | MScope (body) | 0..1 |
| MCall | references | MLabel | 0..1 |
| MLabel | back-ref | MCall (callers) | 0:N |
| MForStatement | has | MForParameter | 0:N |

### State Transitions

```
Raw Parse → Structure Pass → Resolution Pass → Classification Pass
    ↓              ↓                ↓                   ↓
  AST          Unlinked ASG    Linked ASG       Annotated ASG
             (labels exist)  (refs resolved)  (types classified)
```

### Invariants

1. After resolution pass, all local MCall targets must be resolved or marked UNRESOLVED
2. Every MStatement has a non-null scope reference
3. MScope.parent_scope forms a tree (no cycles)
4. MLabel.callers is inverse of MCall.target (back-reference integrity)
5. MForStatement.loop_type is non-null after classification pass
6. MGotoStatement.goto_type is non-null after classification pass

---

## Serialization

ASG can be serialized to JSON for debugging:

```python
def to_dict(element: ASGElement) -> dict:
    """Serialize ASG element to dictionary."""
    result = {
        "type": type(element).__name__,
        "source_line": element.line_number,
    }
    for field_name, field_value in element.__dict__.items():
        if field_name.startswith("_") or field_name in ("parent", "scope"):
            continue  # Skip internal/circular refs
        if isinstance(field_value, ASGElement):
            result[field_name] = to_dict(field_value)
        elif isinstance(field_value, list):
            result[field_name] = [
                to_dict(v) if isinstance(v, ASGElement) else v
                for v in field_value
            ]
        elif isinstance(field_value, Enum):
            result[field_name] = field_value.name
        else:
            result[field_name] = field_value
    return result
```
