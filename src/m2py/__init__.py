"""M2PY - MUMPS to Python transpiler.

This package provides a textX-based parser that produces an Abstract Semantic
Graph (ASG) for MUMPS routines.

Usage:
    from m2py import MUMPSParser
    
    parser = MUMPSParser()
    routine = parser.parse_file("MYROUTINE.m")
    
    # Analyze the routine
    parser.resolve_references(routine)
    parser.analyze_variables(routine)
"""

__version__ = "0.1.0"

# Parser API
from m2py.parser import MUMPSParser, MUMPSSyntaxError

# Core ASG types
from m2py.asg import (
    MRoutine, MLabel, MScope, MCall,
    MStatement, MForStatement, MGotoStatement, MDoStatement,
    MSetStatement, MWriteStatement, MQuitStatement, MIfStatement,
    MNewStatement, MKillStatement,
    MExpr, MLiteral, MVariable, MGlobal,
    ForLoopType, ForParamType, GotoType,
)

# Analysis functions
from m2py.analysis import (
    analyze_command,
    analyze_expression,
    classify_gotos,
    resolve_references,
    analyze_variables,
)

__all__ = [
    "__version__",
    # Parser
    "MUMPSParser",
    "MUMPSSyntaxError",
    # Core ASG
    "MRoutine", "MLabel", "MScope", "MCall",
    "MStatement", "MForStatement", "MGotoStatement", "MDoStatement",
    "MSetStatement", "MWriteStatement", "MQuitStatement", "MIfStatement",
    "MNewStatement", "MKillStatement",
    "MExpr", "MLiteral", "MVariable", "MGlobal",
    "ForLoopType", "ForParamType", "GotoType",
    # Analysis
    "analyze_command",
    "analyze_expression",
    "classify_gotos",
    "resolve_references",
    "analyze_variables",
]
