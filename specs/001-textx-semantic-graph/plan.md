# Implementation Plan: MUMPS Semantic Graph Parser

**Branch**: `001-textx-semantic-graph` | **Date**: 2025-12-19 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-textx-semantic-graph/spec.md`

---

## Summary

Build a **textX-based parser** that produces an **Abstract Semantic Graph (ASG)** for MUMPS routines. The ASG captures program semantics including resolved label references, classified FOR loop types, GOTO classifications, and variable scope analysis. This forms the foundation for future Python code generation.

**Primary Requirement**: Parse 100% of MUGJ test suite files and produce complete, correct ASGs with all references resolved and patterns classified.

**Technical Approach**: 
1. Define textX grammar for MUMPS syntax
2. Build ASG using Python dataclasses with textX custom class integration
3. Implement multi-pass analysis (structure → resolution → classification → variable analysis)
4. Validate against MUGJ test suite incrementally

---

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: textX (grammar/parsing), pytest (testing)  
**Storage**: N/A (in-memory ASG only)  
**Testing**: pytest with MUGJ test fixture integration  
**Target Platform**: Linux/macOS (development), any Python environment  
**Project Type**: Single project (`src/`, `tests/`)  
**Performance Goals**: Parse 500-line routine in <2 seconds (SC-005)  
**Constraints**: No external parser dependencies beyond textX  
**Scale/Scope**: ~280 MUGJ test files, 53 functional requirements

---

## Constitution Check

*GATE: Verified against `.specify/memory/constitution.md` v1.0.0*

### Principle I: Semantic Correctness First ✅

- ASG captures program meaning, not just syntax
- GOTO classifications ensure correct control flow translation
- Variable analysis respects NEW command semantics exactly

### Principle II: Test-Driven Validation ✅

- MUGJ test suite is authoritative validation source
- Incremental milestones tied to specific test files
- Each phase has testable success criteria

### Principle III: Multi-Phase Architecture ✅

- **This spec explicitly implements multi-phase processing**:
  - Phase 1: textX parsing (syntax → raw AST)
  - Phase 2: Structure building (AST → unlinked ASG)
  - Phase 3: Reference resolution (labels linked)
  - Phase 4: Pattern classification (types assigned)
  - Phase 5: Variable analysis (scope computed)
- All references resolved before any code generation (future spec)

### Principle IV: Explicit Over Implicit ✅

- Postconditions are first-class ASG nodes
- Scope containers explicitly model control structure boundaries
- Indirection flagged for runtime handling

### Principle V: Incremental Validation ✅

- Milestones M1-M6 progress from simple to complex
- Each milestone validates before advancing
- FOR loops before GOTO; GOTO before nested combinations

---

## Project Structure

### Documentation (this feature)

```text
specs/001-textx-semantic-graph/
├── spec.md              # Feature specification (complete)
├── plan.md              # This file
├── research.md          # Phase 0 output: technology decisions
├── data-model.md        # Phase 1 output: ASG element hierarchy
├── quickstart.md        # Phase 1 output: development guide
├── contracts/           # Phase 1 output: API definitions
│   └── parser-api.md    # Parser public interface
├── checklists/          # Quality gates
│   └── requirements.md  # Requirements tracking
└── tasks.md             # Phase 2 output (created by /speckit.tasks)
```

### Source Code (repository root)

```text
src/
└── m2py/
    ├── __init__.py
    ├── grammar/                  # textX grammar files
    │   ├── mumps.tx              # Main routine/label structure grammar
    │   ├── line.tx               # Line content parsing grammar
    │   ├── commands.tx           # Command-specific grammar rules
    │   └── expressions.tx        # Expression grammar
    ├── asg/                      # ASG element definitions
    │   ├── __init__.py
    │   ├── elements.py           # Base classes (ASGElement, MRoutine, MLabel)
    │   ├── statements.py         # Statement types (MSetStatement, MForStatement, etc.)
    │   ├── expressions.py        # Expression types (MLiteral, MVariable, etc.)
    │   └── enums.py              # Enumerations (ForLoopType, GotoType, etc.)
    ├── parser/                   # Parser implementation
    │   ├── __init__.py
    │   ├── parser.py             # MUMPSParser class
    │   ├── exceptions.py         # MUMPSSyntaxError, MUMPSSemanticError
    │   └── textx_classes.py      # Custom classes for textX instantiation
    ├── analysis/                 # ASG analysis passes
    │   ├── __init__.py
    │   ├── command_parser.py     # Command parsing via textX grammar
    │   ├── semantic_analyzer.py  # CST → ASG transformation
    │   ├── resolver.py           # Reference resolution pass
    │   ├── goto_analysis.py      # GOTO classification and analysis
    │   └── variables.py          # Variable scope analysis pass
    └── cli/                      # Command-line interface (future)
        └── __init__.py

tests/
├── unit/
│   ├── test_grammar.py           # Grammar rule tests (basic)
│   ├── test_command_grammar.py   # Command-specific grammar tests
│   ├── test_expression_grammar.py # Expression grammar tests
│   ├── test_parser.py            # Parser initialization and basic parsing
│   ├── test_textx_classes.py     # textX custom class integration tests
│   ├── test_semantic_analyzer.py # CST → ASG conversion tests
│   ├── test_command_analysis.py  # Command analysis tests
│   ├── test_classifier.py        # FOR loop classification tests
│   ├── test_command_parser.py    # Command parsing tests
│   ├── test_resolver.py          # Resolution pass tests
│   └── test_variables.py         # Variable analysis tests
├── integration/
│   └── test_mugj.py              # MUGJ test file parsing
└── functional/
    └── mugj/                     # MUGJ validation suite (existing)
```

**Structure Decision**: Single project with standard Python layout. Grammar files are split for maintainability. Analysis is separated into command parsing (textX → raw structures), semantic analysis (CST → ASG), reference resolution, GOTO classification, and variable analysis for clear separation of concerns per Constitution Principle III.

---

## Architecture

### Two-Layer Design: CST → Semantic Analyzer → ASG

The parser uses a clean two-layer architecture:

1. **Parsing Layer (textX + Custom Classes)**: Produces a Concrete Syntax Tree (CST) where textX grammar rules directly instantiate ASG-compatible classes (NumericLiteral → MLiteral, LocalVariable → MVariable, etc.)

2. **Semantic Layer (Semantic Analyzer)**: Transforms the CST into a proper ASG by unwrapping textX wrappers, setting parent relationships, tracking variables, and resolving references.

This approach provides:
- **Clean separation**: Grammar concerns vs semantic concerns
- **Type safety**: Custom classes inherit from ASG dataclasses  
- **Proper parents**: Semantic analyzer sets correct `_asg_parent` references
- **Variable tracking**: Analyzer builds symbol tables during traversal

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         MUMPSParser                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ textX        │    │ Semantic     │    │ Analysis Passes  │   │
│  │ + Custom     │───▶│ Analyzer     │───▶│                  │   │
│  │ Classes      │    │              │    │ (Resolution,     │   │
│  │              │    │              │    │  Classification, │   │
│  └──────────────┘    └──────────────┘    │  Variables)      │   │
│         │                   │            └──────────────────┘   │
│         ▼                   ▼                    │               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ CST          │    │ Clean ASG    │    │ Annotated ASG    │   │
│  │ (ASG types   │    │ (parents set,│    │ (types, refs,    │   │
│  │ w/ wrappers) │    │  unwrapped)  │    │  variables)      │   │
│  └──────────────┘    └──────────────┘    └──────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
MUMPS Source Code
       │
       ▼ (textX parse with custom classes)
   CST (Concrete Syntax Tree)
   ├── Grammar wrapper objects (Expr, UnaryExpr, etc.)
   │   containing ASG-typed leaves:
   │   ├── NumericLiteral (is-a MLiteral)
   │   ├── LocalVariable (is-a MVariable)
   │   └── IntrinsicFunction (is-a MIntrinsicFunction)
       │
       ▼ (semantic analyzer)
   Clean ASG (unwrapped, parents set)
   ├── MRoutine
   │   └── labels: [MLabel, ...]
   │       └── body: MScope
   │           └── statements: [MStatement, ...]
   │               └── All expressions are MExpr subclasses
       │
       ▼ (reference resolution)
   Linked ASG
   ├── MCall.target → MLabel
   ├── MLabel.callers → [MCall, ...]
       │
       ▼ (pattern classification)
   Classified ASG
   ├── MForStatement.loop_type = BOUNDED|OPEN_ENDED|...
   ├── MGotoStatement.goto_type = LOOP_EXIT|BACKWARD_JUMP|...
       │
       ▼ (variable analysis)
   Complete ASG
   ├── MLabel.input_variables = {X, Y}
   ├── MLabel.output_variables = {Z}
```

### Custom Classes (textx_classes.py)

Custom classes inherit from ASG dataclasses and adapt to textX's constructor convention:

| Grammar Rule | Custom Class | Inherits From |
|-------------|--------------|---------------|
| NumericLiteral | NumericLiteral | MLiteral |
| StringLiteral | StringLiteral | MLiteral |
| LocalVariable | LocalVariable | MVariable |
| GlobalVariable | GlobalVariable | MGlobal |
| NakedGlobal | NakedGlobal | MNakedGlobal |
| SpecialVariable | SpecialVariable | MSpecialVariable |
| IntrinsicFunction | IntrinsicFunction | MIntrinsicFunction |
| ExtrinsicFunction | ExtrinsicFunction | MExtrinsicFunction |
| Indirection | Indirection | MIndirection |

### Multi-Pass Processing

| Pass | Name | Input | Output | Key Operations |
|------|------|-------|--------|----------------|
| 1 | Parse | Source | CST | textX grammar match with custom classes |
| 2 | Semantic | CST | Clean ASG | Unwrap wrappers, set parents, track vars |
| 3 | Resolve | Clean ASG | Linked ASG | Label lookup, back-refs |
| 4 | Classify | Linked ASG | Classified ASG | FOR/GOTO typing |
| 5 | Analyze | Classified ASG | Complete ASG | Variable flow analysis |

---

## Implementation Phases

### Phase 1: Grammar & Core ASG (M1-M2)

**Goal**: Parse basic MUMPS constructs and produce minimal ASG.

**Deliverables**:
- `mumps.tx` grammar with Label, SET, WRITE, QUIT, basic FOR, GOTO
- ASG element classes: MRoutine, MLabel, MScope, MStatement hierarchy
- MUMPSParser class with parse() and parse_file()

**Success Criteria**:
- V1FORA.m parses without error
- V1GO1.m parses without error
- Labels correctly extracted

**Risk Mitigation**: Start with simplest grammar subset. Validate MUGJ parsing before adding complexity.

### Phase 2: Reference Resolution (M3)

**Goal**: Link label references and build back-references.

**Deliverables**:
- `resolver.py` with resolve_references()
- MCall.target populated
- MLabel.callers populated

**Success Criteria**:
- All GOTO targets in V1GO1 resolved
- Back-reference integrity verified

### Phase 3: FOR Loop Classification (M4)

**Goal**: Classify all FOR loop types.

**Deliverables**:
- `command_parser.py` with `classify_for_loop()`
- ForLoopType enum applied
- Loop exit points identified

**Success Criteria**:
- All 5 FOR types correctly classified in MUGJ files
- V1FORA, V1FORB, V1FORC series pass

### Phase 4: GOTO Classification (M5)

**Goal**: Classify all GOTO types with respect to enclosing structures.

**Deliverables**:
- `goto_analysis.py` with `classify_gotos()`
- GotoType enum applied
- Nested loop exits identified

**Success Criteria**:
- V1FORC2 (GOTO inside nested FOR) correctly analyzed
- All 6 GOTO types classified

### Phase 5: Variable Analysis (M6)

**Goal**: Compute variable scope and flow.

**Deliverables**:
- `variables.py` with analyze_variables()
- Input/output sets computed
- NEW boundaries respected

**Success Criteria**:
- Variable inputs match expected for test labels
- NEW shadowing correctly tracked

### Phase 6: Full MUGJ Validation

**Goal**: 100% MUGJ parsing coverage.

**Deliverables**:
- All MUGJ files parse
- Comprehensive integration tests
- Performance validation

**Success Criteria**:
- SC-001: 100% MUGJ parse rate
- SC-005: <2s for 500 lines

---

## Milestones

| Milestone | Target Files | Features Validated |
|-----------|--------------|-------------------|
| M1 | V1FORA.m | Basic parsing, labels, SET, WRITE, FOR |
| M2 | V1GO1.m | GOTO, label references |
| M3 | V1FORA, V1GO1 | Reference resolution |
| M4 | V1FORA, V1FORB, V1FORC | FOR classification (all 5 types) |
| M5 | V1FORC2 | GOTO classification (nested loops) |
| M6 | All MUGJ | 100% coverage |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| GOTO in nested FOR complexity | High | Critical | Design state machine fallback early; prototype on V1FORC2 |
| textX grammar limitations | Low | Medium | textX is proven; fallback to object processors |
| Performance on large files | Low | Medium | Profile early; optimize grammar if needed |
| Forward reference edge cases | Medium | Medium | Multi-pass resolves by design |
| Indirection static analysis | High | Low | Flag for runtime; don't block on it |

---

## Dependencies

### External

- **textX 4.0+**: Grammar definition and parsing
- **pytest 7.0+**: Test framework
- **pytest-cov**: Coverage reporting

### Internal

- **mumps-reference/**: ANSI MUMPS standard for syntax rules
- **tests/functional/mugj/**: Validation test suite
- **proleap-research/**: Architecture patterns reference

---

## Success Criteria Mapping

| SC | Description | Validation Method |
|----|-------------|-------------------|
| SC-001 | 100% MUGJ parse | Integration test loop |
| SC-002 | FOR classification | Unit tests per type |
| SC-003 | GOTO target resolution | V1GO1, V1GO2 assertions |
| SC-004 | GOTO-loop exit detection | V1FORC2 specific tests |
| SC-005 | <2s parse time | pytest benchmark |
| SC-006 | NEW scope tracking | V1NX tests |
| SC-007 | Source location in errors | Exception format test |
| SC-008 | Grammar coverage | MUGJ parse loop |

---

## Generated Artifacts

- [research.md](research.md) - Technology decisions and findings
- [data-model.md](data-model.md) - ASG element hierarchy
- [quickstart.md](quickstart.md) - Development guide
- [contracts/parser-api.md](contracts/parser-api.md) - Parser API contract

---

## Complexity Tracking

> No constitution violations to justify. Architecture aligns with all principles.
