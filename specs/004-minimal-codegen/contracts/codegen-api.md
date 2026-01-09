# Codegen API Contract

**Version**: 1.0.0  
**Date**: 2026-01-09

## Public Interface

### generate_python

```python
def generate_python(
    source: str,
    *,
    routine_name: str | None = None,
    validate: bool = True
) -> str:
    """Generate Python code from MUMPS source.
    
    Args:
        source: MUMPS source code (single routine)
        routine_name: Optional name for the routine (extracted from source if not provided)
        validate: If True, validate generated code with ast.parse()
    
    Returns:
        Python source code as a string
    
    Raises:
        ParseError: If MUMPS source cannot be parsed
        CodegenError: If code generation fails
        SyntaxError: If validate=True and generated code is invalid Python
    
    Example:
        >>> code = generate_python("TEST S X=1 W X Q")
        >>> print(code)
        from m2py.codegen.helpers import m_num, m_truth, m_compare
        ...
    """
```

## Internal Interfaces

### RoutineGenerator

```python
class RoutineGenerator:
    """Generates Python code for a complete MUMPS routine."""
    
    def __init__(self, routine: MRoutine) -> None:
        """Initialize with parsed routine."""
    
    def generate(self) -> str:
        """Generate complete Python module."""
```

### Expression Generator

```python
def generate_expr(expr: MExpr, ctx: GeneratorContext) -> str:
    """Generate Python expression from ASG expression node.
    
    Dispatches based on expression type:
    - MLiteral → literal value
    - MVariable → translated variable name
    - MBinaryOp → operation with coercion
    - MUnaryOp → unary operation
    """
```

### Statement Generator

```python
def generate_statement(stmt: MStatement, ctx: GeneratorContext) -> None:
    """Generate Python statement from ASG statement node.
    
    Writes to ctx.emitter. Dispatches based on statement type:
    - MSetStatement → assignment
    - MWriteStatement → _rt.write() call
    - MQuitStatement → return
    - MIfStatement → if block
    - MElseStatement → if not _test block
    - MForStatement → for/while loop
    - MDoStatement → function call
    - MGotoStatement → return function call
    """
```

## Error Types

```python
class CodegenError(Exception):
    """Base exception for code generation errors."""
    pass

class UnsupportedFeatureError(CodegenError):
    """Raised when attempting to generate code for unsupported feature."""
    pass

class NameTranslationError(CodegenError):
    """Raised when name translation fails."""
    pass
```

## Generated Code Contract

Generated Python code MUST:

1. Import required helpers:
   ```python
   from m2py.codegen.helpers import m_num, m_truth, m_compare
   from m2py.runtime import MUMPSRuntime
   ```

2. Initialize runtime:
   ```python
   _rt = MUMPSRuntime()
   ```

3. Initialize $TEST tracking:
   ```python
   _test = False
   ```

4. Define each label as a function:
   ```python
   def LABEL():
       global _test
       # ... body ...
   ```

5. Use translated names for all identifiers

6. Pass `ast.parse()` validation
