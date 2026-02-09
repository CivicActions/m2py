"""ASG analysis passes for reference resolution, classification, and variable analysis.

This module provides the public API for MUMPS code analysis:
- Line parsing (re-exported from m2py.parser.line_parser)
- GOTO classification (ASG-based)
- Reference resolution
- Variable analysis
"""

# GOTO classification and analysis (high-level ASG functions)
from m2py.analysis.goto_analysis import (
    classify_gotos,
)

# FOR loop analysis (high-level ASG functions)
from m2py.analysis.for_analysis import (
    analyze_for_loops,
    analyze_quit_context,
)

# textX-based line parsing (re-exported from parser.line_parser)
from m2py.parser.line_parser import (
    parse_line_content,
    parse_commands_from_line,
)

# Semantic analysis
from m2py.analysis.semantic_analyzer import (
    analyze_command,
    analyze_expression,
    analyze_statement,
    SemanticAnalyzer,
)

# Reference resolution
from m2py.analysis.resolver import (
    resolve_references,
)

# Variable analysis
from m2py.analysis.variables import (
    analyze_variables,
    compute_transitive_inputs,
    ScopeVariables,
    VariableInfo,
)

__all__ = [
    # GOTO classification
    "classify_gotos",
    # FOR loop analysis
    "analyze_for_loops",
    "analyze_quit_context",
    # Line/command parsing (from m2py.parser.line_parser)
    "parse_line_content",
    "parse_commands_from_line",
    # Semantic analysis
    "analyze_command",
    "analyze_expression",
    "analyze_statement",
    "SemanticAnalyzer",
    # Reference resolution
    "resolve_references",
    # Variable analysis
    "analyze_variables",
    "compute_transitive_inputs",
    "ScopeVariables",
    "VariableInfo",
]
