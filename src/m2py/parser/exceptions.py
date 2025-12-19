"""Parser exception classes.

Defines exceptions used during MUMPS parsing and analysis.
"""

from typing import Optional


class MUMPSSyntaxError(Exception):
    """Exception raised when parsing encounters invalid MUMPS syntax.
    
    Provides detailed location information for error reporting.
    """
    
    def __init__(
        self,
        message: str,
        line: Optional[int] = None,
        column: Optional[int] = None,
        source_file: Optional[str] = None,
        source_line: Optional[str] = None,
    ):
        """Initialize a syntax error with location information.
        
        Args:
            message: Description of the syntax error
            line: Line number where error occurred (1-based)
            column: Column number where error occurred (1-based)
            source_file: Path to the source file
            source_line: The actual source line text
        """
        self.message = message
        self.line = line
        self.column = column
        self.source_file = source_file
        self.source_line = source_line
        
        # Build full error message
        parts = []
        if source_file:
            parts.append(source_file)
        if line is not None:
            parts.append(f"line {line}")
        if column is not None:
            parts.append(f"column {column}")
        
        location = ":".join(parts) if parts else "unknown location"
        full_message = f"{location}: {message}"
        
        if source_line:
            full_message += f"\n  {source_line}"
            if column is not None and column > 0:
                full_message += f"\n  {' ' * (column - 1)}^"
        
        super().__init__(full_message)


class MUMPSSemanticError(Exception):
    """Exception raised during semantic analysis.
    
    Used for errors like unresolved references, invalid control flow, etc.
    """
    
    def __init__(
        self,
        message: str,
        element_type: Optional[str] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
    ):
        """Initialize a semantic error.
        
        Args:
            message: Description of the semantic error
            element_type: The ASG element type where error occurred
            line: Line number where error occurred (1-based)
            column: Column number where error occurred (1-based)
        """
        self.message = message
        self.element_type = element_type
        self.line = line
        self.column = column
        
        parts = []
        if element_type:
            parts.append(f"[{element_type}]")
        if line is not None:
            parts.append(f"line {line}")
        
        prefix = " ".join(parts) + ": " if parts else ""
        super().__init__(f"{prefix}{message}")
