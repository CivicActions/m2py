# Semantic Analyzer

The semantic analyzer transforms the textX-parsed Concrete Syntax Tree (CST) into a properly structured Abstract Semantic Graph (ASG).

**Source**: [`src/m2py/analysis/semantic_analyzer.py`](../../src/m2py/analysis/semantic_analyzer.py)

## Overview

The analyzer performs several transformations:

1. **Unwrap textX wrappers** - Remove grammar artifacts (Expr, UnaryExpr)
2. **Set parent references** - Build proper parent-child relationships
3. **Track variables** - Build symbol tables during traversal
4. **Compile patterns** - Convert pattern match syntax to regex

## Architecture

```
textX Parser
     │
     ▼
CST (with custom classes)
├── Routine
│   └── lines (LabelLine, ContLine)
│       └── label, rest (unparsed line content)
     │
     ▼ (line parsing via command grammar)
     │
     ▼ (semantic analysis)
ASG (clean structure)
├── MRoutine
│   └── MLabel
│       └── MScope
│           └── MStatement subclasses
```

## SemanticScope

During analysis, a `SemanticScope` tracks context:

```python
@dataclass
class SemanticScope:
    parent_scope: Optional[SemanticScope] = None
    variables: Dict[str, ScopeVariableInfo] = field(default_factory=dict)
    globals_accessed: Set[str] = field(default_factory=set)
    labels_called: Set[str] = field(default_factory=set)
    
    label_name: Optional[str] = None
    routine_name: Optional[str] = None
    is_for_body: bool = False
    nesting_level: int = 0
```

**ScopeVariableInfo** tracks variable usage:

```python
@dataclass
class ScopeVariableInfo:
    name: str
    first_reference: Any = None
    is_newed: bool = False
    is_set: bool = False
    is_read: bool = False
    is_passed_by_ref: bool = False
    subscript_patterns: List[int] = field(default_factory=list)
```

## Expression Unwrapping

textX grammar produces wrapper nodes that need unwrapping:

```
# CST (from grammar)
Expr
├── left: UnaryExpr
│   ├── operators: []
│   └── operand: NumericLiteral(value="1")
└── tail: [BinaryOpTail(op="+", right=UnaryExpr(...))]

# ASG (after analysis)
MBinaryOp
├── operator: "+"
├── left: MLiteral(value=1, literal_type=INTEGER)
└── right: MLiteral(value=2, literal_type=INTEGER)
```

The analyzer recursively processes expression trees:

```python
def analyze_expression(self, expr: Any) -> Optional[MExpr]:
    """Convert textX expression to ASG expression."""
    cls_name = expr.__class__.__name__
    
    if cls_name == "Expr":
        # Unwrap Expr wrapper, build binary op tree from tail
        return self._analyze_expr_with_tail(expr)
    elif cls_name == "UnaryExpr":
        # Unwrap UnaryExpr, apply unary operators
        return self._analyze_unary_expr(expr)
    elif isinstance(expr, MLiteral):
        # Already an ASG node (custom class)
        return expr
    # ... etc
```

## Command Parsing Flow

Each line's commands are parsed separately:

1. **Line parsing**: textX parses routine structure
2. **Command parsing**: Line content parsed with command grammar
3. **Semantic analysis**: Commands converted to statements

```python
# In parser.py
def _process_label_content(self, label: MLabel, line_rest: str):
    # Parse line content with command grammar
    commands = parse_line_content(line_rest)
    
    # Analyze each command to produce statements
    for cmd in commands:
        stmt = analyze_command(cmd, label.body)
        label.body.add_statement(stmt)
```

## analyze_command Function

The main entry point for command analysis:

```python
def analyze_command(cmd: Any, scope: MScope) -> MStatement:
    """Convert a parsed command to an ASG statement.
    
    Args:
        cmd: The parsed command from textX
        scope: The enclosing scope
        
    Returns:
        An MStatement subclass instance
    """
```

Dispatches based on command type:
- SET → `MSetStatement`
- WRITE → `MWriteStatement`
- IF → `MIfStatement`
- FOR → `MForStatement`
- etc.

## Pattern Compilation

Pattern match expressions are compiled to regex:

```python
from m2py.analysis.pattern_compiler import compile_pattern_to_regex

# During pattern match analysis
if hasattr(expr, 'pattern') and expr.pattern:
    try:
        compiled = compile_pattern_to_regex(expr.pattern)
        pattern_match.compiled_regex = compiled
    except PatternCompileError:
        # Store raw pattern, runtime will handle
        pass
```

See: [pattern_compiler.md](pattern_compiler.md)

## Key Functions

| Function | Purpose |
|----------|---------|
| `SemanticAnalyzer.analyze()` | Main entry point |
| `analyze_expression()` | Convert textX expr to MExpr |
| `analyze_command()` | Convert command to MStatement |
| `_analyze_expr_with_tail()` | Build binary op tree |
| `_analyze_unary_expr()` | Handle unary operators |

## Usage

The semantic analyzer is typically invoked by the parser internally:

```python
from m2py import MUMPSParser

parser = MUMPSParser()
routine = parser.parse_file("routine.m")
# semantic_analyzer is called internally during parse
```

For direct use:

```python
from m2py.analysis.semantic_analyzer import SemanticAnalyzer

analyzer = SemanticAnalyzer()
asg_node = analyzer.analyze(textx_node)
```
