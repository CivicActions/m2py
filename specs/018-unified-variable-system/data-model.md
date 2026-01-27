# Data Model: Unified Variable System

**Feature Branch**: `018-unified-variable-system`  
**Created**: 2025-01-25

---

## 1. Core Entities

### 1.1 VarRef (Unified Variable Reference)

A structured representation of any variable reference in MUMPS, normalized for both codegen and runtime use.

```python
@dataclass
class VarRef:
    """Unified variable reference representation.
    
    Captures all forms of MUMPS variable references:
    - Local: X, X(1,2)
    - Global: ^GLO, ^GLO(1,2), ^(subs) (naked)
    - Indirection: @X, @@X, @X@(1,2), @X(1,2)
    
    This structure is used by:
    1. Codegen: To determine generation strategy (inline vs runtime call)
    2. Runtime: To resolve variable access at execution time
    """
    
    # Base identification
    name: Optional[str] = None          # Variable name (None if purely indirected)
    is_global: bool = False             # True for ^NAME
    is_naked: bool = False              # True for ^(subs) naked reference
    environment: Optional[str] = None   # For ^|env|NAME extended reference
    
    # Subscripts (static or dynamic)
    subscripts: List[SubscriptExpr] = field(default_factory=list)
    
    # Indirection (if any)
    indirection: Optional[IndirectionSpec] = None
    
    # Resolution hints (computed during analysis)
    is_static: bool = False             # True if fully resolvable at compile time
    python_name: Optional[str] = None   # Pre-computed Python identifier
    
    def to_access_string(self) -> str:
        """Convert to MUMPS-style access string for runtime.
        
        Examples:
            VarRef(name="X") → "X"
            VarRef(name="X", subscripts=[1,2]) → "X(1,2)"
            VarRef(is_global=True, name="GLO") → "^GLO"
        """
        ...
    
    def is_resolvable_statically(self) -> bool:
        """Check if this reference can be fully resolved at compile time.
        
        True if:
        - No indirection, OR
        - Indirection source is constant string (can pre-resolve)
        AND
        - All subscripts are literals or constants
        """
        ...
```

### 1.2 SubscriptExpr

Represents a single subscript, which may be static or dynamic.

```python
@dataclass 
class SubscriptExpr:
    """A single subscript expression.
    
    Subscripts can be:
    - Static: Literal values known at compile time
    - Dynamic: Expressions requiring runtime evaluation (including indirection)
    """
    
    # Value (mutually exclusive)
    literal_value: Optional[str] = None     # For static subscripts
    expression: Optional[MExpr] = None      # For dynamic subscripts
    
    # Metadata
    is_static: bool = False
    canonical_value: Optional[str] = None   # Pre-canonicalized if static
    
    def canonicalize(self) -> str:
        """Return canonical subscript value.
        
        Rules:
        - Numeric: Remove leading zeros, trailing decimal zeros
        - String: Preserve exactly unless purely numeric
        """
        ...
```

### 1.3 IndirectionSpec

Captures all aspects of an indirection expression.

```python
@dataclass
class IndirectionSpec:
    """Specification for indirection (@-expression).
    
    Handles:
    - Simple: @X
    - Multi-level: @@X, @@@X
    - With subscripts: @X(1,2)
    - Name indirection: @X@(1,2), @X@(1)@(2,3)
    - Recursive: Value contains @-expression
    """
    
    # Source expression
    source: MExpr                           # The expression after @
    
    # Indirection depth
    levels: int = 1                         # 1 for @, 2 for @@, etc.
    
    # Context (determines final resolution step)
    context: IndirectionContext = IndirectionContext.NAME
    
    # Subscripts
    direct_subscripts: List[SubscriptExpr] = field(default_factory=list)
        # For @X(1,2) form
    
    per_level_subscripts: List[List[SubscriptExpr]] = field(default_factory=list)
        # For @X@(1)@(2,3) form - subscripts applied after each resolution
    
    # Static resolution (if possible)
    can_resolve_statically: bool = False
    static_value: Optional[str] = None      # Pre-resolved if constant source
```

### 1.4 IndirectionContext

Enum distinguishing different indirection semantics.

```python
class IndirectionContext(Enum):
    """Context determines how final indirection value is used.
    
    NAME: Result is variable identifier for lookup/set
          Used by: SET @X=, WRITE @X, KILL @X, MERGE, $DATA(@X)
          Error if result is not valid variable name
    
    ARGUMENT: Result is evaluated as MUMPS expression
              Used by: IF @A, FOR @X:..., XECUTE @A, postconditions
              Empty string allowed (evaluates to false)
    
    SUBSCRIPT: Result is used as subscript value
               Used by: A(1,@B,3) - indirection within subscript
    
    PATTERN: Result is pattern for pattern match
             Used by: X?@A (pattern indirection)
    """
    NAME = "name"
    ARGUMENT = "argument"  
    SUBSCRIPT = "subscript"
    PATTERN = "pattern"
```

---

## 2. Service Components

### 2.1 NameTranslator

Single source of truth for MUMPS↔Python name translation.

```python
class NameTranslator:
    """Bidirectional MUMPS to Python name translation.
    
    Shared between codegen and runtime for consistency.
    
    Translation rules:
    - %NAME → _pct_NAME
    - 01 (numeric prefix) → _n_01
    - Python keywords (if, for, etc.) → _m_if, _m_for
    - All others unchanged
    
    Constitution VII compliance: Single implementation used by both
    codegen (compile time) and runtime (dynamic resolution).
    """
    
    PYTHON_KEYWORDS = {"if", "for", "while", "class", "def", "return", ...}
    
    @staticmethod
    def to_python(mumps_name: str) -> str:
        """Translate MUMPS identifier to valid Python identifier."""
        if mumps_name.startswith("%"):
            return "_pct_" + mumps_name[1:]
        if mumps_name and mumps_name[0].isdigit():
            return "_n_" + mumps_name
        if mumps_name.lower() in NameTranslator.PYTHON_KEYWORDS:
            return "_m_" + mumps_name
        return mumps_name
    
    @staticmethod
    def from_python(python_name: str) -> str:
        """Translate Python identifier back to MUMPS name.
        
        Used by runtime when parsing variable names from indirection.
        """
        if python_name.startswith("_pct_"):
            return "%" + python_name[5:]
        if python_name.startswith("_n_"):
            return python_name[3:]
        if python_name.startswith("_m_"):
            return python_name[3:]
        return python_name
```

### 2.2 SubscriptCanonicalizer

Canonical form for subscript values.

```python
class SubscriptCanonicalizer:
    """Canonicalize subscript values per MUMPS rules.
    
    MUMPS subscript canonicalization:
    - Numeric values have single canonical form
    - Leading zeros removed (01 → 1)
    - Trailing decimal zeros removed (1.0 → 1, 1.50 → 1.5)
    - Leading decimal zero optional (.5 valid)
    
    String subscripts:
    - Preserved exactly unless purely numeric
    - "1" → canonical "1" (same as numeric 1)
    - "01" → preserved as "01" (NOT numeric - has leading zero)
    - "1X" → preserved as "1X" (not purely numeric)
    """
    
    @staticmethod
    def canonicalize(value: Any) -> str:
        """Return canonical subscript string.
        
        Args:
            value: Subscript value (number, string, or other)
            
        Returns:
            Canonical string representation
        """
        if isinstance(value, (int, float)):
            return SubscriptCanonicalizer._canonicalize_numeric(value)
        
        s = str(value)
        if SubscriptCanonicalizer._is_canonical_numeric(s):
            return SubscriptCanonicalizer._canonicalize_numeric_string(s)
        return s
    
    @staticmethod
    def _is_canonical_numeric(s: str) -> bool:
        """Check if string should be treated as numeric.
        
        A string is numeric if it represents a valid MUMPS number
        without leading zeros (except pure "0" or "0.xxx").
        """
        ...
    
    @staticmethod
    def _canonicalize_numeric(n: Union[int, float]) -> str:
        """Canonicalize numeric value."""
        if isinstance(n, float) and n == int(n):
            return str(int(n))
        s = str(n)
        # Remove trailing zeros after decimal
        if "." in s:
            s = s.rstrip("0").rstrip(".")
        return s
```

### 2.3 IndirectionResolver

Runtime resolution of indirection expressions.

```python
class IndirectionResolver:
    """Runtime resolver for @-expressions.
    
    Handles:
    - Single level: @X → value of X used as var name
    - Multi-level: @@X → resolve X, then resolve result
    - With subscripts: @X@(1,2) → resolve X, append (1,2)
    - Recursive: If resolved value starts with @, re-resolve
    - Context-aware: NAME vs ARGUMENT final step
    
    Constitution VII: Used for truly dynamic cases only.
    Static cases should be resolved by codegen inline.
    """
    
    def __init__(self, state: 'MState', scope: 'CurrentScope'):
        self.state = state
        self.scope = scope
    
    def resolve(self, spec: IndirectionSpec) -> Any:
        """Resolve indirection and return final value.
        
        Args:
            spec: IndirectionSpec with all resolution parameters
            
        Returns:
            - NAME context: Variable value
            - ARGUMENT context: Expression evaluation result
            
        Raises:
            VarExpectedError: NAME context, result not valid var name
            UndefinedVariableError: Reference to undefined variable
        """
        ...
    
    def _resolve_levels(
        self, 
        current: str, 
        levels: int,
        subscripts_per_level: List[List[SubscriptExpr]]
    ) -> str:
        """Resolve N levels of indirection with per-level subscripts.
        
        Algorithm:
        1. For each level:
           a. Get value of current reference
           b. If subscripts for this level, append them
           c. Current = result
        2. Return final current (not yet dereferenced)
        """
        for i in range(levels):
            value = self.scope.get(current)
            
            # Handle recursive @-expression
            while value.startswith("@"):
                value = self._resolve_recursive_at(value)
            
            # Apply subscripts for this level if any
            if i < len(subscripts_per_level):
                subs = subscripts_per_level[i]
                value = self._append_subscripts(value, subs)
            
            current = value
        
        return current
    
    def _resolve_recursive_at(self, value: str) -> str:
        """Handle value that starts with @ (recursive @-expression)."""
        # Parse the @-expression and resolve it
        ...
    
    def _finalize(self, ref: str, context: IndirectionContext) -> Any:
        """Final resolution step based on context.
        
        NAME: Look up ref as variable, return value
        ARGUMENT: Evaluate ref as MUMPS expression, return result
        """
        if context == IndirectionContext.NAME:
            if not self._is_valid_var_name(ref):
                raise VarExpectedError(ref)
            return self.scope.get(ref)
        
        elif context == IndirectionContext.ARGUMENT:
            return self._evaluate_expression(ref)
    
    def _evaluate_expression(self, expr_str: str) -> Any:
        """Evaluate MUMPS expression string.
        
        For argument indirection, the resolved string is
        evaluated as a complete MUMPS expression.
        """
        # Use existing execute_mumps infrastructure
        # Wrap in SET to temp, retrieve result
        ...
```

### 2.4 CurrentScope

Unified variable access abstraction.

```python
class CurrentScope:
    """Unified interface for variable access.
    
    Abstracts over different storage mechanisms:
    - Python locals (PURE_FUNCTION strategy)
    - _scope dict (FUNCTION_WITH_OUTPUTS, SUBROUTINE)
    - state._locals (REQUIRES_RUNTIME)
    
    Constitution VII compliance: All variable access (static or
    indirected) uses same path, preventing "variable not found" bugs.
    """
    
    def __init__(
        self,
        locals_dict: Optional[Dict[str, Any]] = None,
        scope_dict: Optional[Dict[str, Any]] = None,
        state_locals: Optional['MArray'] = None
    ):
        self._locals = locals_dict
        self._scope = scope_dict
        self._state_locals = state_locals
    
    def get(self, name: str, default: Any = "") -> Any:
        """Get variable value by MUMPS name.
        
        Lookup order (first non-None source wins):
        1. _scope dict (if set)
        2. Python locals (if provided)
        3. state._locals (if runtime)
        
        Returns default if not found (MUMPS undefined = empty string).
        """
        py_name = NameTranslator.to_python(name)
        
        if self._scope is not None and py_name in self._scope:
            return self._extract_value(self._scope[py_name])
        
        if self._locals is not None and py_name in self._locals:
            return self._extract_value(self._locals[py_name])
        
        if self._state_locals is not None:
            return self._state_locals.get(py_name, default)
        
        return default
    
    def set(self, name: str, value: Any) -> None:
        """Set variable value by MUMPS name."""
        py_name = NameTranslator.to_python(name)
        
        if self._scope is not None:
            self._scope[py_name] = value
        elif self._locals is not None:
            self._locals[py_name] = value
        elif self._state_locals is not None:
            self._state_locals[py_name] = value
    
    def exists(self, name: str) -> bool:
        """Check if variable is defined."""
        ...
    
    def _extract_value(self, obj: Any) -> Any:
        """Extract value from MArray if needed.
        
        FR-038: All access extracts .value from MArray.
        """
        if hasattr(obj, "value"):
            return obj.value
        return obj
```

---

## 3. Entity Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                        MUMPS Source                              │
│  S @X@(1,2)=@@Y   I @A   W ^GLO(1,@B)                          │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Parser
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ASG (Existing)                               │
│  MIndirection, MVariable, MGlobal, MNakedGlobal                 │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Analysis
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    VarRef (New)                                  │
│  Unified representation for codegen decisions                   │
│  ┌─────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│  │ SubscriptExpr│  │ IndirectionSpec  │  │IndirectionContext│   │
│  │ (per subscript)│  │ (if indirected) │  │ (NAME/ARGUMENT) │   │
│  └─────────────┘  └──────────────────┘  └──────────────────┘   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Codegen
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Generated Python                               │
│  Static: x = value                                              │
│  Dynamic: x = _rt.resolve_indirection(...)                     │
└─────────────────────────┬───────────────────────────────────────┘
                          │ Runtime
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Runtime Services                               │
│  ┌────────────────┐  ┌──────────────────┐  ┌──────────────┐    │
│  │NameTranslator  │  │SubscriptCanonical│  │CurrentScope  │    │
│  │(MUMPS↔Python)  │  │    izer          │  │(unified get) │    │
│  └────────────────┘  └──────────────────┘  └──────────────┘    │
│                            ▲                                     │
│                            │                                     │
│  ┌─────────────────────────┴─────────────────────────────────┐  │
│  │           IndirectionResolver                              │  │
│  │  - Multi-level resolution                                  │  │
│  │  - Per-level subscripts                                    │  │
│  │  - Recursive @-expressions                                 │  │
│  │  - Context-aware finalization                             │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. State Transitions

### 4.1 IndirectionSpec Resolution

```
┌──────────────┐
│   Created    │  Source expression, levels, context known
└──────┬───────┘
       │ Analysis phase
       ▼
┌──────────────┐
│  Classified  │  IndirectionContext set (NAME/ARGUMENT/etc.)
└──────┬───────┘
       │ Static analysis
       ▼
┌──────────────┐
│ Static Check │  can_resolve_statically determined
└──────┬───────┘
       │
       ├─── Static: static_value populated
       │
       └─── Dynamic: Requires runtime resolution
```

### 4.2 VarRef Lifecycle

```
┌─────────────────┐
│ From ASG Node   │  MVariable, MGlobal, MIndirection → VarRef
└────────┬────────┘
         │ Analysis
         ▼
┌─────────────────┐
│   Normalized    │  name, subscripts, indirection populated
└────────┬────────┘
         │ Classification
         ▼
┌─────────────────┐
│  Classified     │  is_static, python_name computed
└────────┬────────┘
         │ Codegen
         ▼
┌─────────────────┐         ┌─────────────────┐
│ Static Path     │    OR   │ Dynamic Path    │
│ Direct Python   │         │ Runtime call    │
└─────────────────┘         └─────────────────┘
```

---

## 5. Invariants and Constraints

### 5.1 Name Translation Invariants

```
∀ name: from_python(to_python(name)) == name
∀ name: to_python(name) is valid Python identifier
```

### 5.2 Subscript Canonicalization Invariants

```
canonicalize(1) == canonicalize(01) == canonicalize(1.0) == "1"
canonicalize("01") == "01"  # String preserved (leading zero)
canonicalize("1") == "1"    # Numeric string canonicalized
```

### 5.3 Indirection Context Rules

| Command/Context | Indirection Type | Error on Invalid Name |
|-----------------|------------------|----------------------|
| SET @X= | NAME | Yes (VAREXPECTED) |
| WRITE @X | NAME | Yes |
| KILL @X | NAME | Yes |
| IF @A | ARGUMENT | No (empty → false) |
| FOR @X:... | ARGUMENT | No |
| A(1,@B,3) | SUBSCRIPT | Yes |
| X?@P | PATTERN | Pattern-specific |

### 5.4 Resolution Order

Multi-level indirection with subscripts:
```
@@X@(1)@(2,3) resolves as:
1. Evaluate X → "A"
2. Look up A → "B(5)"
3. Apply (1) → "B(5,1)"
4. Look up B(5,1) → "C"
5. Apply (2,3) → "C(2,3)"
6. Final step based on context
```

---

## 6. Validation Rules

### 6.1 VarRef Validation

```python
def validate_varref(ref: VarRef) -> List[str]:
    errors = []
    
    # Must have name OR indirection
    if ref.name is None and ref.indirection is None:
        errors.append("VarRef must have name or indirection")
    
    # Naked requires global
    if ref.is_naked and not ref.is_global:
        errors.append("Naked reference must be global")
    
    # Static flag consistency
    if ref.is_static:
        if ref.indirection and not ref.indirection.can_resolve_statically:
            errors.append("Static ref cannot have dynamic indirection")
        for sub in ref.subscripts:
            if not sub.is_static:
                errors.append("Static ref cannot have dynamic subscripts")
    
    return errors
```

### 6.2 IndirectionSpec Validation

```python
def validate_indirection_spec(spec: IndirectionSpec) -> List[str]:
    errors = []
    
    # Levels must be positive
    if spec.levels < 1:
        errors.append("Indirection levels must be >= 1")
    
    # Per-level subscripts alignment
    if len(spec.per_level_subscripts) > spec.levels:
        errors.append("More subscript levels than indirection levels")
    
    # Context required
    if spec.context is None:
        errors.append("Indirection context must be set")
    
    return errors
```
