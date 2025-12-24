# Analysis Pipeline

This document describes the analysis passes that annotate the ASG with semantic information.

## Overview

After parsing, the ASG contains syntactic structure but lacks semantic annotations. The analysis pipeline runs multiple passes to populate:

- Reference resolution (linking calls to targets)
- GOTO classification
- FOR loop analysis
- Variable scope analysis

**Critical**: Analysis passes must run in order due to data dependencies.

```
parse
  │
  ▼
resolve_references     ← Links MCall.target to MLabel
  │                    ← Builds MLabel.callers, MLabel.goto_sources
  ▼
classify_gotos         ← Classifies MGotoStatement.goto_type
  │                    ← Populates exits_loops
  ▼
analyze_for_loops      ← Classifies MForStatement.loop_type
  │                    ← Detects infinite loops, internal exits
  ▼
analyze_variables      ← Computes variable sets per label
  │                    ← Determines scope_strategy
  ▼
Annotated ASG          (Ready for code generation)
```

## Running Analysis

```python
from m2py import MUMPSParser

parser = MUMPSParser()
routine = parser.parse_file("routine.m")

# Run all analysis passes
parser.resolve_references(routine)
parser.classify_gotos(routine)
parser.analyze_for_loops(routine)
parser.analyze_variables(routine)

# Or use the combined method
routine = parser.parse_file("routine.m")
parser.analyze(routine)  # Runs all passes
```

## Analysis Pass Summary

| Pass | Populates | Dependencies |
|------|-----------|--------------|
| `resolve_references` | `MCall.target`, `MCall.call_type`, `MLabel.callers`, `MLabel.goto_sources` | None |
| `classify_gotos` | `MGotoStatement.goto_type`, `MGotoStatement.exits_loops` | resolve_references |
| `analyze_for_loops` | `MForStatement.loop_type`, `is_infinite`, `has_internal_quit`, etc. | classify_gotos |
| `analyze_variables` | `MLabel.input_variables`, `output_variables`, `signature` | resolve_references |

## Documentation Index

| Document | Description |
|----------|-------------|
| [semantic_analyzer.md](semantic_analyzer.md) | CST to ASG transformation |
| [resolver.md](resolver.md) | Reference resolution |
| [goto_analysis.md](goto_analysis.md) | GOTO classification |
| [for_analysis.md](for_analysis.md) | FOR loop analysis |
| [variable_analysis.md](variable_analysis.md) | Variable scope analysis |
| [pattern_compiler.md](pattern_compiler.md) | Pattern to regex compilation |

## Source Code

- **Pipeline Entry**: [`src/m2py/parser/parser.py`](../../src/m2py/parser/parser.py) (MUMPSParser methods)
- **Analysis Modules**: [`src/m2py/analysis/`](../../src/m2py/analysis/)
