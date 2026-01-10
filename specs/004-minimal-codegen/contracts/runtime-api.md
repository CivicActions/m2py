# Runtime API Contract

**Version**: 1.0.0  
**Date**: 2026-01-09

## Public Interface

### MUMPSRuntime

```python
class MUMPSRuntime:
    """Minimal runtime for executing generated MUMPS code."""
    
    def __init__(self) -> None:
        """Initialize runtime with empty state."""
    
    def write(self, value: str) -> None:
        """Capture WRITE output.
        
        Args:
            value: String value to write
        
        Note: Does not add newlines automatically (MUMPS WRITE doesn't either).
        """
    
    def get_output(self) -> str:
        """Return accumulated WRITE output.
        
        Returns:
            Concatenated string of all write() calls
        """
    
    def clear(self) -> None:
        """Clear accumulated output."""
    
    def execute(
        self,
        python_code: str,
        *,
        capture_output: bool = True,
        entry_point: str | None = None
    ) -> ExecutionResult:
        """Execute generated Python code.
        
        Args:
            python_code: Generated Python source code
            capture_output: If True, capture WRITE output
            entry_point: Label to execute (default: first label)
        
        Returns:
            ExecutionResult with output, status, and error info
        
        Example:
            >>> rt = MUMPSRuntime()
            >>> result = rt.execute(generated_code)
            >>> print(result.output)
            "1"
        """
```

### ExecutionResult

```python
@dataclass
class ExecutionResult:
    """Result of executing generated MUMPS code."""
    
    output: str
    """Captured WRITE output (empty string if capture_output=False)."""
    
    success: bool
    """True if execution completed without exception."""
    
    error: str | None
    """Exception message if success=False, else None."""
    
    test_value: bool
    """Final value of $TEST after execution."""
    
    locals: dict[str, Any] | None = None
    """Optional: local variables at end of execution (for debugging)."""
```

## Behavior Contract

### write() Semantics

1. Values are appended without separator
2. No automatic newlines (MUMPS WRITE doesn't add newlines)
3. Non-string values should be converted to string by caller
4. Called by generated `_rt.write(str(value))` statements

### execute() Semantics

1. Creates isolated namespace for execution
2. Injects `_rt` (self) and helpers into namespace
3. Executes module-level code (defines functions)
4. Calls entry_point function (or first label if not specified)
5. Captures any exceptions and returns in ExecutionResult

### Thread Safety

MUMPSRuntime is **NOT** thread-safe. Each thread should use its own instance.

## Error Handling

```python
class RuntimeError(Exception):
    """Base exception for runtime errors."""
    pass

class MUMPSError(RuntimeError):
    """Error that would occur in actual MUMPS execution."""
    pass

class UndefinedVariableError(MUMPSError):
    """Reference to undefined variable (M9 error in MUMPS)."""
    pass
```

Note: For Spec 004, undefined variable access will raise Python's `NameError`. MUMPS-specific error handling is deferred to later specs.
