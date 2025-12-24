# Parser API Contract

**Feature**: 001-textx-semantic-graph  
**Version**: 1.0.0  
**Date**: 2025-12-19

---

## Overview

This document defines the public API contract for the MUMPS parser module.

---

## MUMPSParser Class

### Constructor

```python
class MUMPSParser:
    def __init__(self, grammar_path: Optional[Path] = None) -> None:
        """
        Initialize the MUMPS parser.
        
        Args:
            grammar_path: Optional custom grammar file path.
                         If None, uses default grammar.
        
        Raises:
            FileNotFoundError: If grammar file not found.
            TextXSyntaxError: If grammar is invalid.
        """
```

### Methods

#### parse

```python
def parse(self, source: str, filename: str = "<string>") -> MRoutine:
    """
    Parse MUMPS source code string into ASG.
    
    Args:
        source: MUMPS source code as string.
        filename: Optional filename for error messages.
    
    Returns:
        MRoutine: Root of the Abstract Semantic Graph.
    
    Raises:
        MUMPSSyntaxError: If source contains syntax errors.
    
    Example:
        >>> parser = MUMPSParser()
        >>> asg = parser.parse("MAIN\n    S X=1\n    Q\n")
        >>> asg.labels[0].name
        'MAIN'
    """
```

#### parse_file

```python
def parse_file(self, path: Path) -> MRoutine:
    """
    Parse MUMPS source file into ASG.
    
    Args:
        path: Path to MUMPS source file (.m extension).
    
    Returns:
        MRoutine: Root of the Abstract Semantic Graph.
                 MRoutine.name is derived from filename.
    
    Raises:
        FileNotFoundError: If file does not exist.
        MUMPSSyntaxError: If file contains syntax errors.
    
    Example:
        >>> parser = MUMPSParser()
        >>> asg = parser.parse_file(Path("V1FORA.m"))
        >>> asg.name
        'V1FORA'
    """
```

#### resolve_references

```python
def resolve_references(self, routine: MRoutine) -> None:
    """
    Resolve all label references in the ASG (mutation).
    
    This pass links MCall.target to actual MLabel objects
    and populates MLabel.callers back-references.
    
    Args:
        routine: Root of ASG to process.
    
    Side Effects:
        - Sets MCall.target for resolvable references
        - Sets MCall.call_type 
        - Appends to MLabel.callers
        - Appends to MLabel.goto_sources
    
    Post-conditions:
        - All local label references are resolved or marked UNRESOLVED
        - Back-reference integrity: MCall in target.callers
    """
```

#### classify_patterns

```python
def classify_patterns(self, source: str, filename: Optional[str] = None) -> list[ForPatternResult]:
    """
    Parse source and classify FOR loop patterns.
    
    This is a convenience method that parses the source and then
    extracts and classifies all FOR loops found in the routine.
    Uses textX grammar-based parsing to extract FOR commands.
    
    Args:
        source: The MUMPS source code to parse.
        filename: Optional filename for error reporting.
    
    Returns:
        List of ForPatternResult objects describing each FOR loop found.
        Each ForPatternResult contains:
        - loop_type: ForLoopType enum value
        - loop_var: Loop variable name (or None for argumentless)
        - label_name: Name of the containing label
        - line_number: Source line number
        - statement: MForStatement ASG node
    
    Example:
        >>> parser = MUMPSParser()
        >>> results = parser.classify_patterns("TEST\\tF I=1:1:10 W I\\n")
        >>> results[0].loop_type
        ForLoopType.BOUNDED
    """
```

#### classify_patterns_from_file

```python
def classify_patterns_from_file(self, filepath: Union[str, Path]) -> list[ForPatternResult]:
    """
    Parse file and classify FOR loop patterns.
    
    Convenience method combining parse_file() and classify_patterns().
    
    Args:
        filepath: Path to MUMPS source file.
    
    Returns:
        List of ForPatternResult objects describing each FOR loop found.
    """
```

#### analyze_variables

```python
def analyze_variables(self, routine: MRoutine) -> None:
    """
    Analyze variable usage and scope in the ASG (mutation).
    
    This pass identifies variable read/write patterns and
    computes input/output sets for each label.
    
    Args:
        routine: Root of ASG to process.
    
    Side Effects:
        - Sets MLabel.variables_read
        - Sets MLabel.variables_written
        - Sets MLabel.variables_newed
        - Computes MLabel.input_variables
        - Computes MLabel.output_variables
    
    Post-conditions:
        - Variable sets are populated for all labels
    """
```

---

## Exceptions

### MUMPSSyntaxError

```python
class MUMPSSyntaxError(Exception):
    """
    Raised when MUMPS source contains syntax errors.
    
    Attributes:
        message: Error description.
        filename: Source filename.
        line: Line number (1-indexed).
        column: Column number (1-indexed).
    """
    
    def __init__(
        self, 
        message: str, 
        filename: str = "<string>",
        line: int = 0,
        column: int = 0
    ) -> None:
        ...
    
    def __str__(self) -> str:
        """Format: 'filename:line:column: message'"""
```

---

## Semantic Analyzer Functions

The semantic analyzer transforms textX parsed commands into clean ASG objects.
Located in `m2py.analysis.semantic_analyzer`.

### analyze_command

```python
def analyze_command(textx_cmd: Any, parent: Any = None) -> Optional[MStatement]:
    """
    Analyze a textX command and return an ASG statement.
    
    This is the primary entry point for command-to-ASG conversion.
    
    Args:
        textx_cmd: A textX command model (SetCommand, WriteCommand, etc.)
        parent: Optional parent ASG node for back-references.
    
    Returns:
        MStatement: The corresponding ASG statement, or None if unrecognized.
    
    Example:
        >>> from m2py.analysis.command_parser import parse_commands_from_line
        >>> from m2py.analysis.semantic_analyzer import analyze_command
        >>> cmds = parse_commands_from_line("S X=1")
        >>> stmt = analyze_command(cmds[0])
        >>> isinstance(stmt, MSetStatement)
        True
    """
```

### analyze_expression

```python
def analyze_expression(textx_expr: Any, parent: Any = None) -> MExpr:
    """
    Analyze a textX expression and return an ASG expression.
    
    Args:
        textx_expr: A textX expression model.
        parent: Optional parent ASG node.
    
    Returns:
        MExpr: The corresponding ASG expression.
    """
```

---

## Usage Example

```python
from pathlib import Path
from m2py.parser import MUMPSParser
from m2py.asg import MForStatement, ForLoopType

# Initialize parser
parser = MUMPSParser()

# Parse file
asg = parser.parse_file(Path("tests/functional/mugj/inref/V1FORA.m"))

# Run analysis passes
parser.resolve_references(asg)
parser.classify_patterns(asg)
parser.analyze_variables(asg)

# Inspect results
for label in asg.labels:
    print(f"Label: {label.name}")
    print(f"  Inputs: {label.input_variables}")
    print(f"  Outputs: {label.output_variables}")
    
    for stmt in label.body.walk_statements():
        if isinstance(stmt, MForStatement):
            print(f"  FOR loop: {stmt.loop_type.name}")
```

---

## Performance Requirements

| Operation | Target | Max |
|-----------|--------|-----|
| parse() for 100 lines | < 100ms | 500ms |
| parse() for 500 lines | < 500ms | 2000ms |
| resolve_references() | < 50ms | 200ms |
| classify_patterns() | < 50ms | 200ms |
| analyze_variables() | < 100ms | 500ms |

---

## Thread Safety

- `MUMPSParser` instances are thread-safe for concurrent `parse()` calls
- ASG objects are NOT thread-safe; do not share between threads without synchronization
- Analysis methods mutate ASG; ensure sequential access per routine
