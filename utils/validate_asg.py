#!/usr/bin/env python3
"""ASG Validation Utility for MUGJ Phase 13 Deep Validation.

This script parses a MUMPS file and displays:
1. Original MUMPS source code
2. ASG structure in a clean, readable format
3. Validation checklist reminders

Purpose: Support deep validation of all 376 MUGJ test files to ensure:
  ✓ ASG 100% correctly captures all source details in proper structure
  ✓ ASG is semantically useful for Python code generation
"""

import sys
from pathlib import Path
from dataclasses import fields
from typing import Any
import argparse


def format_asg_node(node: Any, indent: int = 0, max_depth: int = 5) -> str:
    """Format an ASG node recursively with indentation."""
    if indent > max_depth:
        return "  " * indent + "..."
    
    if node is None:
        return "None"
    
    # Handle primitive types
    if isinstance(node, (str, int, float, bool)):
        return repr(node)
    
    # Handle lists
    if isinstance(node, list):
        if not node:
            return "[]"
        result = "[\n"
        for item in node:
            result += "  " * (indent + 1) + format_asg_node(item, indent + 1, max_depth) + ",\n"
        result += "  " * indent + "]"
        return result
    
    # Handle enums
    if hasattr(node, '__class__') and hasattr(node.__class__, '__name__'):
        class_name = node.__class__.__name__
        if class_name.endswith('Type') or class_name.endswith('Operator'):
            return f"{class_name}.{node.name}"
    
    # Handle ASG nodes (dataclasses)
    if hasattr(node, '__dataclass_fields__'):
        class_name = node.__class__.__name__
        result = f"{class_name}(\n"
        
        # Get fields, prioritize important ones
        priority_fields = ['name', 'type', 'value', 'targets', 'condition', 'loop_var']
        other_fields = []
        
        for field in fields(node):
            if field.name in priority_fields:
                continue
            other_fields.append(field)
        
        # Show priority fields first
        for field_name in priority_fields:
            if hasattr(node, field_name):
                field_value = getattr(node, field_name)
                if field_value is not None:
                    formatted_value = format_asg_node(field_value, indent + 1, max_depth)
                    result += "  " * (indent + 1) + f"{field_name}={formatted_value},\n"
        
        # Show other fields
        for field in other_fields:
            if field.name in ['parent', 'source_line', 'source_col']:
                continue  # Skip back-references and source tracking for readability
            
            field_value = getattr(node, field.name)
            if field_value is not None and field_value != [] and field_value != "":
                formatted_value = format_asg_node(field_value, indent + 1, max_depth)
                result += "  " * (indent + 1) + f"{field.name}={formatted_value},\n"
        
        result += "  " * indent + ")"
        return result
    
    return repr(node)


def display_source(filepath: Path) -> None:
    """Display the original MUMPS source code."""
    print("=" * 80)
    print(f"SOURCE: {filepath.name}")
    print("=" * 80)
    
    lines = filepath.read_text().split('\n')
    for i, line in enumerate(lines, 1):
        print(f"{i:3}: {line}")
    
    print()


def display_asg(routine: Any) -> None:
    """Display the ASG structure."""
    print("=" * 80)
    print("ASG STRUCTURE")
    print("=" * 80)
    
    print(f"\nRoutine: {routine.name}")
    print(f"Labels: {len(routine.labels)}")
    
    for label in routine.labels:
        print(f"\n{'─' * 80}")
        print(f"Label: {label.name}")
        
        if label.body and label.body.statements:
            print(f"Statements: {len(label.body.statements)}")
            
            for i, stmt in enumerate(label.body.statements, 1):
                print(f"\n  [{i}] {stmt.__class__.__name__}")
                
                # Show statement details
                if hasattr(stmt, 'postcondition') and stmt.postcondition:
                    print(f"      postcondition: {format_asg_node(stmt.postcondition, 3, max_depth=3)}")
                
                if hasattr(stmt, 'targets') and stmt.targets:
                    print(f"      targets: {len(stmt.targets)} item(s)")
                    for j, target in enumerate(stmt.targets):
                        target_repr = format_asg_node(target, 3, max_depth=2)
                        print(f"        [{j}] {target_repr}")
                
                if hasattr(stmt, 'value') and stmt.value:
                    print(f"      value: {format_asg_node(stmt.value, 3, max_depth=2)}")
                
                if hasattr(stmt, 'condition') and stmt.condition:
                    print(f"      condition: {format_asg_node(stmt.condition, 3, max_depth=2)}")
                
                if hasattr(stmt, 'arguments') and stmt.arguments:
                    print(f"      arguments: {len(stmt.arguments)} item(s)")
                
                if hasattr(stmt, 'loop_var') and stmt.loop_var:
                    print(f"      loop_var: {stmt.loop_var}")
                
                if hasattr(stmt, 'parameters') and stmt.parameters:
                    print(f"      parameters: {len(stmt.parameters)} item(s)")
                
                if hasattr(stmt, 'body') and stmt.body:
                    if hasattr(stmt.body, 'statements'):
                        print(f"      body: {len(stmt.body.statements)} statement(s)")
        else:
            print("  No statements")
    
    print()


def display_validation_checklist() -> None:
    """Display validation checklist."""
    print("=" * 80)
    print("VALIDATION CHECKLIST")
    print("=" * 80)
    print("""
TASK 1: Verify 100% Correct ASG Capture
  □ Every line in source has corresponding ASG node(s)?
  □ All labels captured with correct names?
  □ All commands captured (SET, WRITE, DO, GOTO, FOR, IF, etc.)?
  □ All expressions captured (variables, literals, operators, functions)?
  □ Postconditions captured where present?
  □ Control flow structures (IF/ELSE, FOR) captured correctly?
  □ Function calls (intrinsic and extrinsic) captured?
  □ Special variables ($HOROLOG, $STORAGE, etc.) captured?
  □ Indirection (@variable) captured?
  □ Pattern matches (?) captured?

TASK 2: Evaluate Python Code Generation Readiness
  □ Does ASG distinguish commands vs functions clearly?
  □ Are expression trees properly structured (not just strings)?
  □ Is operator precedence captured correctly?
  □ Are variable scopes/references identifiable?
  □ Can control flow be translated to Python (if/for/while)?
  □ Are label targets resolved (for GOTO/DO)?
  □ Is there enough semantic info to generate equivalent Python?
  □ What additional analysis would simplify code generation?
  □ Are there ambiguities that need clarification?
  □ Missing semantic information that affects correctness?

CROSS-REFERENCE: Check mumps-reference/ documentation as needed
  - Operator precedence and behavior
  - Intrinsic function semantics
  - Special variable meanings
  - Command syntax and postconditions
  - Pattern match syntax
""")


def analyze_completeness(routine: Any, source_lines: list[str]) -> dict:
    """Analyze ASG completeness vs source."""
    total_source_lines = len([l for l in source_lines if l.strip() and not l.strip().startswith(';')])
    
    total_statements = 0
    label_count = len(routine.labels)
    
    statement_types = {}
    missing_commands = []
    
    for label in routine.labels:
        if label.body and label.body.statements:
            for stmt in label.body.statements:
                total_statements += 1
                stmt_type = stmt.__class__.__name__
                statement_types[stmt_type] = statement_types.get(stmt_type, 0) + 1
    
    return {
        'source_lines': total_source_lines,
        'label_count': label_count,
        'statement_count': total_statements,
        'statement_types': statement_types,
        'missing_commands': missing_commands
    }


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description='Validate MUMPS ASG structure for Phase 13',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a single file
  uv run python utils/validate_asg.py tests/functional/mugj/inref/RESTORE.m
  
  # Validate multiple files
  uv run python utils/validate_asg.py tests/functional/mugj/inref/V1*.m
  
  # Show only summary
  uv run python utils/validate_asg.py --summary tests/functional/mugj/inref/RESTORE.m
        """
    )
    parser.add_argument('files', nargs='+', help='MUMPS files to validate')
    parser.add_argument('--summary', action='store_true', help='Show only summary, not full ASG')
    parser.add_argument('--no-checklist', action='store_true', help='Skip validation checklist')
    
    args = parser.parse_args()
    
    # Import here to avoid issues if m2py not installed
    try:
        from m2py.parser import MUMPSParser
    except ImportError:
        print("ERROR: Cannot import m2py. Make sure it's installed.")
        print("Run: uv sync")
        return 1
    
    parser_obj = MUMPSParser()
    
    for file_path_str in args.files:
        filepath = Path(file_path_str)
        
        if not filepath.exists():
            print(f"ERROR: File not found: {filepath}")
            continue
        
        print("\n" + "█" * 80)
        print(f"VALIDATING: {filepath.name}")
        print("█" * 80 + "\n")
        
        # Display source
        display_source(filepath)
        
        # Parse and display ASG
        try:
            routine = parser_obj.parse_file(str(filepath))
            
            if not args.summary:
                display_asg(routine)
            
            # Analyze completeness
            source_lines = filepath.read_text().split('\n')
            analysis = analyze_completeness(routine, source_lines)
            
            print("=" * 80)
            print("SUMMARY")
            print("=" * 80)
            print(f"Source lines (non-comment): {analysis['source_lines']}")
            print(f"Labels captured: {analysis['label_count']}")
            print(f"Statements captured: {analysis['statement_count']}")
            print(f"\nStatement types:")
            for stmt_type, count in sorted(analysis['statement_types'].items()):
                print(f"  {stmt_type}: {count}")
            
            if analysis['missing_commands']:
                print(f"\n⚠️  Missing commands: {', '.join(analysis['missing_commands'])}")
            
            print()
            
        except Exception as e:
            print(f"ERROR: Failed to parse {filepath.name}: {e}")
            import traceback
            traceback.print_exc()
            continue
        
        # Display validation checklist
        if not args.no_checklist:
            display_validation_checklist()
        
        print("\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
