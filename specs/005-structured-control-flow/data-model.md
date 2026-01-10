# Data Model: Spec 005 - Structured Control Flow Codegen

**Date**: 2025-01-21  
**Spec**: [spec.md](spec.md)

## Overview

This document defines the data models and type contracts for Spec 005. All entities leverage existing ASG structures - no new ASG types are needed. This spec focuses on code generation patterns that consume existing analysis data.

---

## 1. Input Entities (From Analysis)

These entities are populated by analysis passes before code generation.

### 1.1 MForStatement (Extended)

```python
@dataclass
class MForStatement:
    """FOR loop ASG node with analysis fields."""
    
    # Parser fields
    loop_var: str | MVariable
    parameters: List[MForParameter]
    body: MScope
    
    # Analysis fields (populated by for_analysis.py)
    loop_type: ForLoopType
    loop_var_modified_in_body: bool = False
    has_internal_quit: bool = False
    has_internal_goto: bool = False
    exit_points: List[MGotoStatement] = field(default_factory=list)
    is_infinite: bool = False
```

### 1.2 MGotoStatement (Extended)

```python
@dataclass
class MGotoStatement:
    """GOTO ASG node with analysis fields."""
    
    # Parser fields
    targets: List[MCall]
    postcondition: Optional[MExpr] = None
    
    # Analysis fields (populated by goto_analysis.py)
    goto_type: GotoType = GotoType.FORWARD_JUMP
    is_cross_label: bool = False
    is_loop_continue: bool = False
    exits_loops: List[MForStatement] = field(default_factory=list)
```

### 1.3 MQuitStatement

```python
@dataclass
class MQuitStatement:
    """QUIT ASG node with context fields."""
    
    # Parser fields
    return_value: Optional[MExpr] = None
    postcondition: Optional[MExpr] = None
    
    # Context fields (populated during parsing/semantic analysis)
    exits_for: bool = False
    exits_do_block: bool = False
```

### 1.4 FunctionSignature

```python
@dataclass
class FunctionSignature:
    """Computed signature for label code generation."""
    
    label_name: str
    formal_params: List[str]
    
    # Input/Output analysis
    required_inputs: Set[str]
    optional_inputs: Set[str]
    byref_outputs: Set[str]
    side_effect_outputs: Set[str]
    
    # Return analysis
    has_value_quit: bool
    has_void_quit: bool
    
    # Strategy
    scope_strategy: ScopeStrategy
    requires_runtime_scope: bool
    
    # Transitive (from callees)
    transitive_inputs: Set[str]
    transitive_outputs: Set[str]
```

---

## 2. Enums Used in Code Generation

### 2.1 ForLoopType

```python
class ForLoopType(Enum):
    BOUNDED = auto()      # F I=1:1:10  → for i in range()
    OPEN_ENDED = auto()   # F I=1:1     → while or itertools.count
    STRING_LIST = auto()  # F I="A","B" → for i in [...]
    MIXED = auto()        # F I=1:1:3,"X" → chained iteration
    ARGUMENTLESS = auto() # F           → while True
```

### 2.2 GotoType

```python
class GotoType(Enum):
    FORWARD_JUMP = auto()     # Jump ahead (check is_cross_label)
    BACKWARD_JUMP = auto()    # Jump back (creates loops)
    LOOP_EXIT = auto()        # Exit single FOR → break
    MULTI_LOOP_EXIT = auto()  # Exit nested FORs → exception
    EXTERNAL = auto()         # To other routine
    UNRESOLVED = auto()       # Dynamic target
```

### 2.3 ScopeStrategy

```python
class ScopeStrategy(Enum):
    PURE_FUNCTION = auto()         # Clean function, args + return
    FUNCTION_WITH_OUTPUTS = auto() # Return + modified by-ref params
    SUBROUTINE = auto()            # No return value
    REQUIRES_RUNTIME = auto()      # Needs runtime scope (out of scope)
```

---

## 3. Code Generation Contexts

### 3.1 GeneratorContext (Extended)

```python
@dataclass
class GeneratorContext:
    """Context passed through code generation."""
    
    routine: MRoutine
    emitter: CodeEmitter
    name_translator: NameTranslator = field(default_factory=NameTranslator)
    imports: Set[str] = field(default_factory=set)
    current_label: Optional[MLabel] = None
    
    # New for Spec 005
    signatures: Dict[str, FunctionSignature] = field(default_factory=dict)
    loop_stack: List[MForStatement] = field(default_factory=list)
    in_extrinsic_call: bool = False
```

### 3.2 ForGenContext

```python
@dataclass
class ForGenContext:
    """Context for FOR loop code generation decisions."""
    
    stmt: MForStatement
    loop_var: str
    use_while: bool  # True if loop_var_modified_in_body
    needs_break: bool  # True if has_internal_quit or has_internal_goto
    is_infinite: bool
    loop_type: ForLoopType
```

### 3.3 GotoGenContext

```python
@dataclass
class GotoGenContext:
    """Context for GOTO code generation decisions."""
    
    stmt: MGotoStatement
    in_for_loop: bool
    enclosing_loops: List[MForStatement]
    target_label: str
    pattern: str  # 'continue' | 'break' | 'multi_break' | 'forward' | 'function_call' | 'unsupported'
```

---

## 4. Generated Code Patterns

### 4.1 Function Signature Patterns

```python
# PURE_FUNCTION
def label(param1: Any, param2: Any) -> Any:
    return result

# FUNCTION_WITH_OUTPUTS
def label(param1: Any, param2: Any) -> Tuple[Any, ...]:
    # ... computation ...
    return result, param2  # return value + modified by-ref

# SUBROUTINE
def label(param1: Any, param2: Any) -> None:
    # ... side effects ...
    pass  # implicit return None
```

### 4.2 FOR Loop Patterns

```python
# BOUNDED - no modifications
for loop_var in range(start, end + step_sign, step):
    body()

# BOUNDED - with loop var modification
loop_var = start
while (step > 0 and loop_var <= end) or (step < 0 and loop_var >= end):
    body()  # may modify loop_var
    loop_var = loop_var + step  # only if not modified in body

# OPEN_ENDED
for loop_var in itertools.count(start, step):
    body()
    if exit_condition:
        break

# ARGUMENTLESS
while True:
    body()
    if exit_condition:
        break

# STRING_LIST
for loop_var in [val1, val2, val3]:
    body()
```

### 4.3 GOTO Patterns

```python
# LOOP_EXIT with is_loop_continue=True
continue

# LOOP_EXIT 
break

# MULTI_LOOP_EXIT
raise _LoopExit()

# FORWARD_JUMP (intra-label, is_cross_label=False)
# Restructure to if/else - no explicit goto

# FORWARD_JUMP (cross-label, is_cross_label=True)
# Function call pattern (deferred to Spec 006 for full support)
return target_label()

# BACKWARD_JUMP (any)
# Unsupported in Spec 005 - raises UnsupportedFeatureError
# Intra-label backward (G LABEL without offset) creates implicit loops
# Cross-label backward requires state machine - deferred to Spec 006
```

### 4.4 QUIT Patterns

```python
# QUIT in FOR (exits_for=True)
break

# QUIT in DO block (exits_do_block=True)
return

# QUIT with value
return expr_value

# QUIT with postcondition
if m_truth(condition):
    break  # or return
```

---

## 5. Validation Rules

### 5.1 Pre-Generation Validation

```python
def validate_for_codegen(routine: MRoutine) -> List[str]:
    """Validate routine is ready for Spec 005 code generation."""
    errors = []
    
    for label in routine.labels:
        sig = routine.signatures.get(label.name)
        if sig and sig.scope_strategy == ScopeStrategy.REQUIRES_RUNTIME:
            errors.append(f"Label {label.name} requires runtime scope (Spec 006+)")
        
        for stmt in label.body.walk_statements():
            if isinstance(stmt, MGotoStatement):
                if stmt.is_cross_label and stmt.goto_type != GotoType.LOOP_EXIT:
                    errors.append(f"Cross-label GOTO to {stmt.targets[0].name} not supported (Spec 006)")
                if stmt.goto_type == GotoType.BACKWARD_JUMP:
                    # All backward jumps (cross-label and intra-label) are unsupported in Spec 005
                    # Intra-label backward (G LABEL without offset) creates implicit loops
                    # Cross-label backward requires state machine
                    label_type = "cross-label" if stmt.is_cross_label else "intra-label"
                    errors.append(f"Backward {label_type} GOTO not supported (Spec 006)")
    
    return errors
```

### 5.2 Post-Generation Validation

```python
def validate_generated_code(code: str) -> bool:
    """Validate generated Python is syntactically correct."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False
```

---

## 6. Type Summary

| Entity | Source | Used For |
|--------|--------|----------|
| `MForStatement` | Parser + Analysis | FOR loop code generation |
| `MGotoStatement` | Parser + Analysis | GOTO pattern selection |
| `MQuitStatement` | Parser | QUIT code generation |
| `FunctionSignature` | variables.py | Function signature generation |
| `ForLoopType` | enums.py | Loop pattern selection |
| `GotoType` | enums.py | GOTO strategy selection |
| `ScopeStrategy` | enums.py | Return pattern selection |
| `GeneratorContext` | codegen/routine.py | State during code generation |

---

## 7. State Transitions

### 7.1 $TEST State Machine

```
State: _test (bool)

Transitions:
- IF cond → _test = m_truth(cond)
- Multiple IF conds → _test = m_truth(c1) and m_truth(c2) and ...
- $$extrinsic() → save _test, call, restore _test
- No explicit set from QUIT, GOTO, FOR
```

### 7.2 Loop State During Generation

```
State: loop_stack (List[MForStatement])

Transitions:
- Enter FOR → push to stack
- Exit FOR → pop from stack  
- GOTO with exits_loops → break/exception based on len(exits_loops)
- QUIT with exits_for → break, don't pop (natural exit)
```
