"""ASG analysis passes for reference resolution, classification, and variable analysis.

This module provides the public API for MUMPS code analysis:
- Command parsing (textX-based)
- GOTO classification (ASG-based)
- Reference resolution
- Variable analysis
"""

# GOTO classification and analysis (high-level ASG functions)
from m2py.analysis.goto_analysis import (
    classify_gotos,
    get_loop_exiting_gotos,
    get_gotos_by_type,
)

# FOR loop analysis (high-level ASG functions)
from m2py.analysis.for_analysis import (
    analyze_for_loops,
)

# textX-based command parsing functions
from m2py.analysis.command_parser import (
    # Line and command parsing
    parse_line_content,
    parse_commands_from_line,
    extract_for_commands,
    classify_for_from_textx,
    parse_for_command_to_asg,
    detect_quit_after_for,
    detect_unreachable_code,
    # FOR loop classification
    classify_for_loop_textx as classify_for_loop,
    # Extraction functions (from line content)
    extract_for_from_line_textx as extract_for_from_line,
    extract_goto_from_line_textx as extract_goto_from_line,
    extract_do_from_line_textx as extract_do_from_line,
    extract_set_from_line_textx as extract_set_from_line,
    extract_quit_from_line_textx as extract_quit_from_line,
    extract_if_from_line_textx as extract_if_from_line,
    extract_new_from_line_textx as extract_new_from_line,
    # Backward-compatible statement parsers (content-only API)
    parse_set_statement,
    parse_write_statement,
    parse_quit_statement,
    parse_if_statement,
    parse_for_statement,
    parse_goto_statement,
    parse_new_statement,
    parse_do_statement,
    # Parse command functions (full command API)
    parse_for_command,
    parse_goto_command,
    parse_new_command,
    parse_do_command,
    parse_set_command,
    parse_write_command,
    parse_quit_command,
    parse_if_command,
    # Extra textX exports
    classify_for_loop_textx,
    extract_for_from_line_textx,
    extract_goto_from_line_textx,
    extract_do_from_line_textx,
    extract_set_from_line_textx,
    extract_quit_from_line_textx,
    extract_if_from_line_textx,
    extract_new_from_line_textx,
)

# Semantic analysis
from m2py.analysis.semantic_analyzer import (
    analyze_command,
    analyze_expression,
    SemanticAnalyzer,
)

# Reference resolution
from m2py.analysis.resolver import (
    resolve_references,
    get_unresolved_calls,
    get_external_calls,
)

# Variable analysis
from m2py.analysis.variables import (
    analyze_variables,
    get_def_use_chains,
    compute_transitive_inputs,
    ScopeVariables,
    VariableInfo,
)

__all__ = [
    # GOTO classification
    "classify_gotos",
    "get_loop_exiting_gotos",
    "get_gotos_by_type",
    # FOR loop analysis
    "analyze_for_loops",
    # Line/command parsing
    "parse_line_content",
    "parse_commands_from_line",
    "extract_for_commands",
    "classify_for_from_textx",
    "parse_for_command_to_asg",
    "detect_quit_after_for",
    "detect_unreachable_code",
    # FOR classification (backward-compatible alias)
    "classify_for_loop",
    "classify_for_loop_textx",
    # Extraction functions (backward-compatible aliases)
    "extract_for_from_line",
    "extract_goto_from_line",
    "extract_do_from_line",
    "extract_set_from_line",
    "extract_quit_from_line",
    "extract_if_from_line",
    "extract_new_from_line",
    # textX extraction names
    "extract_for_from_line_textx",
    "extract_goto_from_line_textx",
    "extract_do_from_line_textx",
    "extract_set_from_line_textx",
    "extract_quit_from_line_textx",
    "extract_if_from_line_textx",
    "extract_new_from_line_textx",
    # Parse statement functions (backward-compatible aliases)
    "parse_for_statement",
    "parse_goto_statement",
    "parse_new_statement",
    "parse_do_statement",
    "parse_set_statement",
    "parse_write_statement",
    "parse_quit_statement",
    "parse_if_statement",
    # Parse command functions (native names)
    "parse_for_command",
    "parse_goto_command",
    "parse_new_command",
    "parse_do_command",
    "parse_set_command",
    "parse_write_command",
    "parse_quit_command",
    "parse_if_command",
    # Semantic analysis
    "analyze_command",
    "analyze_expression",
    "SemanticAnalyzer",
    # Reference resolution
    "resolve_references",
    "get_unresolved_calls",
    "get_external_calls",
    # Variable analysis
    "analyze_variables",
    "get_def_use_chains",
    "compute_transitive_inputs",
    "ScopeVariables",
    "VariableInfo",
]
