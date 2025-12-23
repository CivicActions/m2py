#!/usr/bin/env python
"""Test the enhanced indirect DO grammar and ASG generation."""

from m2py.analysis.command_parser import parse_line_content
from m2py.analysis.semantic_analyzer import SemanticAnalyzer


def test_pattern(pattern: str):
    """Test a single pattern through parsing and ASG generation."""
    print(f"\n{'='*60}")
    print(f"Pattern: {pattern}")
    print('='*60)
    
    result = parse_line_content(pattern)
    if result is None:
        print("PARSE FAIL: returned None")
        return
    print("Parse OK")
    
    analyzer = SemanticAnalyzer()
    try:
        # Analyze each command individually (that's the expected usage)
        for line_cmd in result.commands:
            cmd = line_cmd.cmd  # Get the actual command (DoCommand, etc.)
            asg = analyzer.analyze(cmd)
            
            print(f"  Statement: {type(asg).__name__}")
            
            if hasattr(asg, 'targets'):
                for i, target in enumerate(asg.targets):
                    print(f"    Target {i}:")
                    print(f"      name={repr(target.name)}")
                    print(f"      routine={repr(target.routine)}")
                    print(f"      label_is_indirect={target.label_is_indirect}")
                    print(f"      routine_is_indirect={target.routine_is_indirect}")
                    print(f"      indirection_levels={target.indirection_levels}")
                    print(f"      indirection={target.indirection}")
                    print(f"      routine_indirection={target.routine_indirection}")
                    print(f"      offset={target.offset}")
    except Exception as e:
        import traceback
        print("ASG FAIL:")
        traceback.print_exc()


if __name__ == "__main__":
    # Test patterns from simplest to most complex
    patterns = [
        # Basic indirect label
        "D @A",
        # Indirect with offset
        "D @A+5",
        # Nested indirection (@@)
        "D @@A",
        # Indirect label with routine
        "D @A^ROUTINE",
        # Indirect label with indirect routine
        "D @A^@C",
        # Double indirect label with indirect routine
        "D @@A^@C",
        # Regular label with indirect routine
        "D LABEL^@C",
        # Regular label with nested indirect routine
        "D LABEL^@@C",
        # Label with offset containing indirect, and nested indirect routine
        "D V1IDDO+-5+@^V1IDDO1^@@C",
        # Full complex pattern from V1IDGO.m
        "D @A^@C,V1IDDO+-5+@^V1IDDO1^@@C",
        
        # GOTO patterns from V1IDGOA.m
        "G @C",                         # simple indirect
        "G @^V1A",                       # indirect routine only
        "G ^@A",                         # literal ^ with indirect routine
        "G @A^@C",                       # indirect label and routine
        'G @@B+1^V1IDGO1',               # nested indirect with offset
    ]
    
    for p in patterns:
        test_pattern(p)
