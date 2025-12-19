"""MUMPS Parser implementation using textX.

Provides the MUMPSParser class that parses MUMPS source code and
produces an Abstract Semantic Graph (ASG).
"""

from pathlib import Path
from typing import Optional, Union

from textx import metamodel_from_file

from m2py.asg import MRoutine, MLabel, MScope
from m2py.asg.enums import ForLoopType
from m2py.asg.statements import MForStatement
from m2py.parser.exceptions import MUMPSSyntaxError
from m2py.analysis.classifier import classify_for_loop, extract_for_from_line, parse_for_statement
from m2py.analysis.resolver import resolve_references as _resolve_references


class ForPatternResult:
    """Result of FOR loop pattern classification.
    
    Represents a classified FOR loop found in the source code.
    """
    
    def __init__(self, 
                 label_name: str,
                 loop_type: ForLoopType,
                 loop_var: str,
                 line_content: str,
                 statement: Optional[MForStatement] = None):
        self.label_name = label_name
        self.loop_type = loop_type
        self.loop_var = loop_var
        self.line_content = line_content
        self.statement = statement  # The actual ASG node
    
    def __repr__(self):
        return f"ForPatternResult({self.label_name}, {self.loop_type.name}, var={self.loop_var!r})"


class MUMPSParser:
    """Parser for MUMPS source code.
    
    Uses textX to parse MUMPS source and produce an ASG representation.
    The parser performs:
    1. Lexical and syntactic analysis via textX grammar
    2. ASG construction with proper parent/child relationships
    3. Source location tracking for error reporting
    
    Usage:
        parser = MUMPSParser()
        routine = parser.parse(source_code)
        # or
        routine = parser.parse_file("routine.m")
    """
    
    def __init__(self):
        """Initialize the parser with the MUMPS grammar.
        
        Loads the textX grammar file and prepares the metamodel
        for parsing MUMPS source code.
        """
        # Locate the grammar file relative to this module
        grammar_dir = Path(__file__).parent.parent / "grammar"
        grammar_file = grammar_dir / "mumps.tx"
        
        if not grammar_file.exists():
            raise FileNotFoundError(f"Grammar file not found: {grammar_file}")
        
        # Create the textX metamodel
        # IMPORTANT: skipws=False because MUMPS is whitespace-sensitive
        # (tabs separate labels from commands, spaces separate arguments)
        self._metamodel = metamodel_from_file(
            str(grammar_file),
            # Custom classes will be registered here as ASG types are implemented
            classes=[],
            skipws=False,  # Don't auto-skip whitespace
        )
        
        # Track source file for error reporting
        self._current_file: Optional[str] = None
    
    def parse(self, source: str, filename: Optional[str] = None) -> MRoutine:
        """Parse MUMPS source code and return an ASG.
        
        Args:
            source: The MUMPS source code to parse
            filename: Optional filename for error reporting
            
        Returns:
            An MRoutine containing the parsed ASG
            
        Raises:
            MUMPSSyntaxError: If the source contains syntax errors
        """
        self._current_file = filename
        
        try:
            # Parse using textX
            model = self._metamodel.model_from_str(source)
            
            # Convert textX model to our ASG
            routine = self._build_routine(model, filename)
            
            return routine
            
        except Exception as e:
            # Convert textX exceptions to our exception type
            raise MUMPSSyntaxError(
                message=str(e),
                source_file=filename,
            ) from e
    
    def parse_file(self, filepath: Union[str, Path]) -> MRoutine:
        """Parse a MUMPS source file and return an ASG.
        
        Args:
            filepath: Path to the .m file to parse
            
        Returns:
            An MRoutine containing the parsed ASG
            
        Raises:
            FileNotFoundError: If the file does not exist
            MUMPSSyntaxError: If the file contains syntax errors
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"MUMPS source file not found: {filepath}")
        
        source = filepath.read_text(encoding="utf-8")
        routine_name = filepath.stem  # Use filename without extension as routine name
        
        routine = self.parse(source, filename=str(filepath))
        routine.name = routine_name
        routine.source_file = str(filepath)
        
        return routine
    
    def _build_routine(self, model, filename: Optional[str]) -> MRoutine:
        """Convert textX parse model to MRoutine ASG.
        
        This is a placeholder that will be expanded as we implement
        more ASG element mappings.
        
        Args:
            model: The textX parse model
            filename: Source filename for location tracking
            
        Returns:
            An MRoutine ASG node
        """
        routine = MRoutine(source_file=filename)
        
        # Build labels from parsed lines
        if hasattr(model, 'lines') and model.lines:
            for line in model.lines:
                # LabelLine has a label attribute
                if hasattr(line, 'label') and line.label:
                    label = self._build_label(line)
                    routine.add_label(label)
        
        return routine
    
    def _build_label(self, line) -> MLabel:
        """Convert textX LabelLine to MLabel ASG.
        
        Args:
            line: The textX LabelLine model
            
        Returns:
            An MLabel ASG node
        """
        label = MLabel(name=line.label if line.label else "")
        
        # TODO: Parse formal parameters from line.rest if present
        # (format: LABEL(param1,param2)\tcommands)
        
        # Store line content for classification
        label._line_rest = getattr(line, 'rest', '')
        
        # Build the body scope (statements will be added in later phases)
        label.body = MScope()
        label.body.parent = label
        
        return label
    
    def classify_patterns(self, source: str, filename: Optional[str] = None) -> list[ForPatternResult]:
        """Parse source and classify FOR loop patterns.
        
        This is a convenience method that parses the source and then
        extracts and classifies all FOR loops found in the routine.
        
        Args:
            source: The MUMPS source code to parse
            filename: Optional filename for error reporting
            
        Returns:
            List of ForPatternResult objects describing each FOR loop found
        """
        # Parse to get the model directly (we need line content)
        self._current_file = filename
        
        try:
            model = self._metamodel.model_from_str(source)
        except Exception as e:
            raise MUMPSSyntaxError(
                message=str(e),
                source_file=filename,
            ) from e
        
        results = []
        current_label = None
        
        if hasattr(model, 'lines') and model.lines:
            for line in model.lines:
                # Track current label for association
                if hasattr(line, 'label') and line.label:
                    current_label = line.label
                
                # Get line content (rest attribute for LabelLine, ContLine)
                line_rest = getattr(line, 'rest', '')
                
                if not line_rest:
                    continue
                
                # Look for FOR patterns in this line
                for_info = extract_for_from_line(line_rest)
                
                if for_info:
                    loop_type, loop_var, for_content = for_info
                    
                    # Build actual MForStatement ASG node
                    statement = parse_for_statement(for_content)
                    
                    results.append(ForPatternResult(
                        label_name=current_label or "",
                        loop_type=loop_type,
                        loop_var=loop_var,
                        line_content=line_rest,
                        statement=statement,
                    ))
        
        return results
    
    def classify_patterns_from_file(self, filepath: Union[str, Path]) -> list[ForPatternResult]:
        """Parse a file and classify FOR loop patterns.
        
        Args:
            filepath: Path to the .m file to parse
            
        Returns:
            List of ForPatternResult objects describing each FOR loop found
            
        Raises:
            FileNotFoundError: If the file does not exist
            MUMPSSyntaxError: If the file contains syntax errors
        """
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"MUMPS source file not found: {filepath}")
        
        source = filepath.read_text(encoding="utf-8")
        return self.classify_patterns(source, filename=str(filepath))
    
    def resolve_references(self, routine: MRoutine) -> None:
        """Resolve all MCall references in a routine to their targets.
        
        This method connects GOTO and DO targets to their actual label
        definitions. It populates:
        - MCall.target with the resolved MLabel
        - MCall.is_resolved = True for successful resolutions
        - MLabel.callers with back-references from DO calls
        - MLabel.goto_sources with back-references from GOTO jumps
        
        External calls (label^routine) are marked but not resolved
        since they reference other routines.
        
        Args:
            routine: The MRoutine to resolve references in
            
        Side Effects:
            Modifies routine's MCall and MLabel objects in place
        """
        _resolve_references(routine)
