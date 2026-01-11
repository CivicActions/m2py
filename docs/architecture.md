# M2PY Architecture

This document describes the high-level architecture of the M2PY MUMPS-to-Python transpiler.

## Overview

M2PY uses a multi-phase architecture to parse MUMPS source code and produce an Abstract Semantic Graph (ASG) that can be used for Python code generation.

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                                       Data Flow                                          │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│  MUMPS Source    textX Parser    Semantic      Analysis       Annotated      Python     │
│  (.m file)   ──▶ + Custom    ──▶ Analyzer  ──▶ Passes     ──▶ ASG       ──▶ Code        │
│                   Classes         (CST→ASG)                                              │
│                                                                                          │
│                      │               │              │              │           │         │
│                      ▼               ▼              ▼              ▼           ▼         │
│                   ┌──────┐      ┌──────┐      ┌──────────┐    ┌─────────┐  ┌──────┐     │
│                   │ CST  │      │ ASG  │      │ Resolved │    │ Ready   │  │ .py  │     │
│                   │      │      │      │      │ ASG      │    │ for     │  │ file │     │
│                   │      │      │      │      │          │    │ codegen │  │      │     │
│                   └──────┘      └──────┘      └──────────┘    └─────────┘  └──────┘     │
│                                                                                          │
└─────────────────────────────────────────────────────────────────────────────────────────┘
```

## Two-Layer Architecture

M2PY uses a clean two-layer architecture:

### Layer 1: Parsing (textX + Custom Classes)

The textX parser reads MUMPS source and produces a **Concrete Syntax Tree (CST)** where grammar rules directly instantiate ASG-compatible custom classes.

```python
# Grammar rule (expressions.tx)
NumericLiteral: value=/[0-9]+(\.[0-9]+)?/;

# Custom class (textx_classes.py)
class NumericLiteral(MLiteral):
    def __init__(self, parent, value):
        super().__init__(value=value, literal_type=LiteralType.DECIMAL)
```

**Key insight**: textX custom classes inherit from ASG dataclasses, so the parsed tree already contains ASG-typed nodes wrapped in grammar constructs.

### Layer 2: Semantic Analysis (CST → ASG)

The semantic analyzer transforms the CST into a clean ASG by:

1. **Unwrapping textX wrappers** - Grammar nodes like `Expr`, `UnaryExpr` are unwrapped to their semantic equivalents
2. **Setting parent relationships** - `_asg_parent` references are correctly established
3. **Tracking variables** - Symbol tables are built during traversal
4. **Resolving patterns** - Pattern expressions are compiled to regex

## Directory Structure

```
src/m2py/
├── __init__.py              # Public API exports
├── grammar/                 # textX grammar files
│   ├── mumps.tx             # Routine and label structure
│   ├── line.tx              # Line content parsing
│   ├── commands.tx          # Command-specific grammar
│   └── expressions.tx       # Expression grammar
├── asg/                     # ASG element definitions
│   ├── elements.py          # Base classes (ASGElement, MRoutine, MLabel, MScope, MCall)
│   ├── statements.py        # Statement types (MSetStatement, MForStatement, etc.)
│   ├── expressions.py       # Expression types (MLiteral, MVariable, MBinaryOp, etc.)
│   ├── enums.py             # Classification enums (ForLoopType, GotoType, etc.)
│   └── type_helpers.py      # TypeGuard functions for pyright
├── parser/                  # Parser implementation
│   ├── parser.py            # MUMPSParser class
│   ├── line_parser.py       # Line content parsing via textX
│   ├── textx_classes.py     # Custom classes for textX instantiation
│   └── exceptions.py        # MUMPSSyntaxError
├── analysis/                # ASG analysis passes
│   ├── semantic_analyzer.py # CST → ASG transformation
│   ├── dead_code_analysis.py # Unreachable code detection
│   ├── resolver.py          # Reference resolution
│   ├── goto_analysis.py     # GOTO classification
│   ├── for_analysis.py      # FOR loop analysis
│   ├── variables.py         # Variable scope analysis
│   └── pattern_compiler.py  # Pattern to regex compilation
├── codegen/                 # Python code generation
│   ├── __init__.py          # Public API: generate_python()
│   ├── helpers.py           # Runtime helpers: m_num(), m_truth(), m_compare()
│   ├── names.py             # NameTranslator for identifier translation
│   ├── emitter.py           # CodeEmitter for indented output
│   ├── routine.py           # RoutineGenerator for module structure
│   ├── statements.py        # Statement code generation
│   └── expressions.py       # Expression code generation
└── runtime/                 # Execution runtime
    └── __init__.py          # MUMPSRuntime, ExecutionResult
```

## Processing Pipeline

The parser processes MUMPS source in distinct phases:

### Phase 1: Parsing

```python
parser = MUMPSParser()
routine = parser.parse_file("routine.m")
```

- textX parses source using the grammar in `mumps.tx`
- Custom classes in `textx_classes.py` are instantiated for matching rules
- Each line's content is parsed separately using `commands.tx`
- Result: Raw ASG with labels, statements, and expressions

### Phase 2: Reference Resolution

```python
parser.resolve_references(routine)
```

- Links `MCall.target` to resolved `MLabel` objects
- Populates back-references: `MLabel.callers`, `MLabel.goto_sources`
- Marks external calls (`label^routine`) as unresolved
- Marks indirect calls (`@expr`) as `INDIRECT_CALL`

See: [`src/m2py/analysis/resolver.py`](../src/m2py/analysis/resolver.py)

### Phase 3: GOTO Classification

```python
parser.classify_gotos(routine)
```

- Classifies each `MGotoStatement` by `GotoType`
- Detects loop exits (single and multi-loop)
- Identifies forward/backward jumps
- Populates `exits_loops` for loop-exiting GOTOs

See: [`src/m2py/analysis/goto_analysis.py`](../src/m2py/analysis/goto_analysis.py)

### Phase 4: FOR Loop Analysis

```python
parser.analyze_for_loops(routine)
```

- Classifies loop type (`ForLoopType`: BOUNDED, OPEN_ENDED, etc.)
- Detects infinite loops (`is_infinite`)
- Identifies internal QUITs (`has_internal_quit`)
- Detects loop variable modification (`loop_var_modified_in_body`)

See: [`src/m2py/analysis/for_analysis.py`](../src/m2py/analysis/for_analysis.py)

### Phase 5: Variable Analysis

```python
parser.analyze_variables(routine)
```

- Computes per-label variable sets: `variables_read`, `variables_written`, `variables_newed`
- Computes input/output variables: `input_variables`, `output_variables`
- Determines `scope_strategy` for code generation
- Builds `FunctionSignature` for each label

See: [`src/m2py/analysis/variables.py`](../src/m2py/analysis/variables.py)

### Phase 6: Code Generation

```python
from m2py.codegen import generate_python

python_code = generate_python(source, routine_name="example", validate=True)
```

- Translates ASG to executable Python code
- Generates module structure with imports and runtime initialization
- Translates labels to Python functions with `global _test` declarations
- Uses `NameTranslator` to convert MUMPS names to valid Python identifiers
- Validates generated code with `ast.parse()` when `validate=True`

See: [`src/m2py/codegen/`](../src/m2py/codegen/)

**Generated code structure:**
```python
from m2py.codegen.helpers import m_num, m_truth, m_compare
from m2py.runtime import MUMPSRuntime

_rt = MUMPSRuntime()
_test = False

def LABEL():
    global _test
    # ... translated statements
```

## Design Decisions

### Why textX?

textX was chosen over alternatives for several reasons:

| Alternative | Why Not |
|-------------|---------|
| PLY/lex+yacc | Lower-level, requires separate lexer/parser, more boilerplate |
| ANTLR | Java-centric, overkill for this scope |
| pyparsing | Less declarative, harder to maintain grammar |

textX provides:
- Declarative grammar syntax
- Automatic AST construction
- Source position tracking (via `_tx_position`, which we convert to line/column)
- Custom class integration for direct ASG instantiation
- Forward reference resolution

### Why Multi-Phase Analysis?

MUMPS has complex semantics that cannot be fully analyzed in a single pass:

1. **Forward references**: Labels can be called before they're defined
2. **GOTO classification**: Requires knowing all label positions first
3. **Variable analysis**: Requires knowing call targets for by-reference tracking
4. **Transitive analysis**: Requires complete local analysis first

The multi-phase approach follows **Constitution Principle III**: All references are resolved before code generation.

### Analysis-First Principle

Code generation follows a strict **analysis-first** principle: semantic properties are computed during
analysis passes and stored as ASG fields, then codegen simply reads those fields. This design provides:

1. **Clean layer separation**: Analysis computes semantics, codegen generates code
2. **Reusable analysis**: The same ASG annotations can be used by linting, visualization, or other tools
3. **Faster codegen**: No repeated ASG traversal during code generation
4. **Easier testing**: Analysis and codegen can be tested independently

**Validation**: The `validate_analysis_complete()` function verifies that required analysis passes have
run before code generation begins. If analysis fields are missing, it raises `AnalysisNotCompleteError`
with a message indicating which analysis pass needs to run.

**Example flow**:
```python
# Analysis pass sets field
stmt.loop_type = ForLoopType.BOUNDED  # analyze_for_loops()

# Codegen reads field (never computes)
if stmt.loop_type == ForLoopType.BOUNDED:
    emit_for_range(stmt)
```

**Key ASG fields populated by analysis**:
- `MForStatement.loop_type`, `.loop_var_modified_in_body` → `analyze_for_loops()`
- `MGotoStatement.goto_type`, `.exits_loops` → `classify_gotos()`
- `MQuitStatement.exits_for`, `.exits_do_block` → `analyze_quit_context()`
- `MLabel.signature` → `compute_signatures()`

### Why Separate Grammar Files?

The grammar is split into multiple files for maintainability:

- `mumps.tx`: Overall routine structure (labels, lines)
- `line.tx`: Line-level parsing (indentation, continuations)
- `commands.tx`: Individual command syntax
- `expressions.tx`: Expression parsing (operators, functions)

This allows focused testing and easier evolution of individual parts.

### Why Two-Phase Parsing?

The parser uses a deliberate two-phase approach:

1. **Phase 1 (Structure Parsing)**: `MUMPSParser` uses `mumps.tx` with `classes=[]`
   to parse the overall routine structure—labels, line boundaries, and continuations.
   No custom classes are registered at this phase because we only need the raw
   structure, not command semantics.

2. **Phase 2 (Line Parsing)**: `line_parser.py` uses `line.tx`/`commands.tx`
   with the full set of custom classes to parse individual line content into
   typed ASG nodes (commands, expressions, etc.).

This separation provides several benefits:
- **Isolation**: Structure parsing errors are separated from command parsing errors
- **Flexibility**: Line content can be re-parsed or analyzed independently
- **Testing**: Each phase can be tested in isolation
- **Performance**: Structure parsing is lightweight; full parsing happens only where needed

> **Note**: If you see `classes=[]` in `MUMPSParser.__init__`, this is intentional—
> it's part of the two-phase architecture, not incomplete implementation.

### Grammar to ASG Field Naming

The textX grammar uses short attribute names for compactness, while ASG classes use
descriptive names for clarity. The `SemanticAnalyzer` handles this mapping during
CST→ASG transformation:

| Grammar File | Grammar Attribute | ASG Class | ASG Field | Notes |
|--------------|-------------------|-----------|-----------|-------|
| `commands.tx` | `ForCommand.params` | `MForStatement` | `parameters` | FOR loop parameters |
| `commands.tx` | `WriteCommand.args` | `MWriteStatement` | `arguments` | WRITE arguments |
| `commands.tx` | `ReadCommand.args` | `MReadStatement` | `arguments` | READ arguments |
| `expressions.tx` | `IntrinsicFunction.args` | `MIntrinsicFunction` | `arguments` | Function arguments |
| `expressions.tx` | `ExtrinsicFunction.args` | `MExtrinsicFunction` | `arguments` | Function arguments |
| `commands.tx` | `SetArgument` | - | `MAssignment` | Renamed for clarity |
| `commands.tx` | `DoTarget` | - | `MCall` | Unified call reference |
| `commands.tx` | `GotoTarget` | - | `MCall` | Unified call reference |

This intentional separation keeps grammar files concise while making ASG code self-documenting.

## Key Data Structures

### MRoutine

Top-level container for a MUMPS routine. Contains:
- `labels`: List of `MLabel` entry points
- `source_lines`: Original source for `$TEXT` support
- `has_unstructured_goto`: Flag for complex control flow

### MLabel

Entry point within a routine. Contains:
- `formal_list`: Parameter names
- `body`: `MScope` with statements
- `callers`: Back-references from DO statements
- `goto_sources`: Back-references from GOTO statements
- Variable analysis results (`input_variables`, `output_variables`, etc.)

### MScope

Container for statements. Provides:
- `statements`: Ordered list of statements
- `walk_statements()`: Recursive iterator over all statements

### MStatement Subclasses

20+ statement types covering all MUMPS commands:
- Control flow: `MIfStatement`, `MForStatement`, `MGotoStatement`
- Data: `MSetStatement`, `MWriteStatement`, `MReadStatement`
- Subroutines: `MDoStatement`, `MQuitStatement`
- Variables: `MNewStatement`, `MKillStatement`

See: [asg/statements.md](asg/statements.md)

### MExpr Subclasses

15+ expression types:
- `MLiteral`, `MVariable`, `MGlobal`
- `MBinaryOp`, `MUnaryOp`
- `MIntrinsicFunction`, `MExtrinsicFunction`
- `MIndirection`, `MPatternMatch`

See: [asg/expressions.md](asg/expressions.md)

## References

- **Specification**: [`specs/001-textx-semantic-graph/spec.md`](../specs/001-textx-semantic-graph/spec.md)
- **Research Notes**: [`specs/001-textx-semantic-graph/research.md`](../specs/001-textx-semantic-graph/research.md)
- **Data Model**: [`specs/001-textx-semantic-graph/data-model.md`](../specs/001-textx-semantic-graph/data-model.md)
- **textX Reference**: [https://textx.github.io/textX/](https://textx.github.io/textX/)
