# Research: MUMPS Semantic Graph Parser

**Feature**: 001-textx-semantic-graph  
**Date**: 2025-12-19  
**Purpose**: Document technical decisions and findings from Phase 0 research

---

## 1. textX Capabilities Assessment

### 1.1 Grammar Features for MUMPS

**Decision**: textX is suitable for MUMPS grammar complexity.

**Rationale**: textX provides all necessary grammar constructs:
- **Regex matches**: Handle MUMPS identifiers (`/[%A-Za-z][A-Za-z0-9]*/`), numeric literals, string literals
- **Ordered choice (`|`)**: Handle optional command abbreviations (e.g., `'SET'|'S'`)
- **Optional (`?`) and repetition (`*`, `+`)**: Handle optional postconditions, multiple arguments
- **Syntactic predicates (`!`, `&`)**: Prevent keyword conflicts (e.g., ensure "SET" isn't parsed as identifier)
- **Link references (`[RuleName]`)**: Enable cross-referencing for label resolution

**Alternatives Considered**:
- **PLY/lex+yacc**: Lower-level, requires separate lexer/parser, more boilerplate
- **ANTLR**: Java-centric, overkill for this scope
- **pyparsing**: Less declarative, harder to maintain

**Key Finding**: textX's object model automatically builds AST nodes as Python objects with parent-child relationships via `parent` attribute. Source positions are tracked via `_tx_position`.

### 1.2 Reference Resolution

**Decision**: Use textX's RREL (Reference Resolving Expression Language) for label references, but implement custom scope logic for MUMPS-specific semantics.

**Rationale**: 
- MUMPS has flat label namespace within a routine (no nested scopes for label visibility)
- Labels can be referenced before definition (forward references)
- textX's multi-pass model resolves forward references naturally

**RREL Usage**:
```
GotoStatement: 'G' target=[Label:ID|^labels] postcondition=Postcondition?;
```

This would look up labels from the parent routine's label list.

### 1.3 Custom Classes

**Decision**: Use Python dataclasses with textX custom classes for ASG nodes.

**Rationale**: 
- Dataclasses provide immutability options, `__eq__`, `__hash__` for free
- textX accepts custom classes in `classes` parameter
- Allows adding computed properties and methods

**Implementation Pattern**:
```python
@dataclass
class MForStatement(MStatement):
    loop_var: Optional[str] = None
    parameters: List[MForParameter] = field(default_factory=list)
    body: MScope = field(default_factory=MScope)
    loop_type: Optional[ForLoopType] = None
```

---

## 2. MUMPS Syntax Complexity Analysis

### 2.1 FOR Command Complexity

**Decision**: FOR loops require classification into 5 types for proper code generation.

**Types Identified** (from MUGJ tests and ANSI spec):

| Type | Syntax Example | Behavior |
|------|----------------|----------|
| Bounded | `F I=1:1:10 W I` | Fixed iteration count |
| Open-ended | `F I=1:1 Q:I>10 W I` | Infinite until QUIT |
| String-list | `F I="A","B","C" W I` | Enumerate values |
| Mixed | `F I="A",1:1:3 W I` | Combine types |
| Argumentless | `F  R X Q:X=""` | Infinite until QUIT |

**Grammar Strategy**:
```
ForParameter: value=Expr | start=NumExpr ':' step=NumExpr (':' end=NumExpr)?;
ForCommand: 'F' loop_var=ID? (parameters+=ForParameter[','])? body=Scope;
```

### 2.2 GOTO Classification

**Decision**: GOTO statements must be classified by target relationship and enclosing context.

**Classifications** (from V1GO1, V1GO2, V1FORC2):

| Classification | Description | Python Transformation |
|----------------|-------------|----------------------|
| Loop-exit | Exits single FOR | `break` |
| Multi-loop-exit | Exits nested FORs | Exception or state machine |
| Backward-jump | Creates loop pattern | `while` wrapper |
| Forward-jump | Skip ahead | Nested function or goto label |
| Cross-label | Jump to different label | Function call |
| External | Jump to routine^label | Function call |

**Key Insight**: GOTO inside nested FOR loops (V1FORC2 I-374, I-376) is the hardest case. Previous exception-based approach failed here.

### 2.3 Postcondition Handling

**Decision**: Postconditions are first-class ASG nodes, not string annotations.

**Rationale**: Postconditions affect control flow and must be evaluated in MUMPS order.

**Grammar**:
```
Postcondition: ':' condition=Expr;
Command: keyword=CommandWord postcondition=Postcondition? arguments+=Argument[','];
Argument: postcondition=Postcondition? value=Expr;
```

### 2.4 Indirection Complexity

**Decision**: Flag indirection for runtime handling, with limited static resolution.

**Indirection Types** (from V1IDNM1, V1IDGO1):

| Type | Syntax | Static Resolution? |
|------|--------|-------------------|
| Name | `@"X"` | Yes if constant |
| Subscript | `X@(1,2)` | Partial |
| Argument | `D @routine` | Runtime |
| Pattern | `?@pat` | Runtime |

**Strategy**: ASG captures indirection expressions. Analysis pass attempts constant folding. Remaining cases flagged as `requires_runtime_eval`.

---

## 3. Multi-Pass Architecture

### 3.1 Pass Structure

**Decision**: Adopt ProLeap-inspired 3-pass architecture.

**Rationale**: Single-pass parsing cannot resolve forward references or classify control flow patterns. ProLeap's architecture (proven on COBOL) handles similar challenges.

**Passes**:

| Pass | Purpose | Input | Output |
|------|---------|-------|--------|
| 1: Parse | Build syntax tree | MUMPS source | Raw AST |
| 2: Structure | Build ASG, register labels | AST | ASG with unresolved refs |
| 3: Resolve | Link references, add back-refs | ASG | Complete ASG |
| 4: Classify | Analyze patterns, type loops | ASG | Annotated ASG |

### 3.2 textX Integration

**Decision**: Leverage textX's built-in multi-file model support sparingly.

**Rationale**: MUMPS routines are self-contained. Cross-routine references (label^routine) can be modeled as unresolved external references without loading other files.

**Implementation**:
- Pass 1: `metamodel.model_from_file()` produces raw model
- Pass 2-4: Custom Python code walks and transforms model

---

## 4. Variable Scope Analysis

### 4.1 NEW Command Semantics

**Decision**: Model NEW as scope boundary markers, not scope containers.

**Rationale**: MUMPS NEW doesn't create lexical scope—it pushes variable values onto stack. Variables are still visible after NEW, just with new empty values.

**ASG Model**:
```python
@dataclass
class MNewStatement(MStatement):
    variables: List[str]  # Explicit NEW X,Y,Z
    exclusive: bool = False  # NEW (X) means all EXCEPT X
    except_list: List[str] = field(default_factory=list)
```

**Analysis**: Def-Use analysis must respect NEW boundaries. A variable used after NEW but before SET reads empty string (undefined).

### 4.2 Argumentless DO Scope

**Decision**: Model argumentless DO as inline scope creation.

**Rationale**: MUGJ tests show `D` without arguments creates stack frame for NEW isolation without jumping to a label.

**ASG Model**:
```python
@dataclass
class MDoBlockStatement(MStatement):
    """Argumentless DO - inline scope"""
    body: MScope
```

### 4.3 Variable Flow Analysis

**Decision**: Compute variable inputs/outputs for each label to enable function signature generation.

**Algorithm**:
1. For each label, collect all variable reads and writes
2. Subtract variables set by NEW (they're local)
3. Variables read before first write = inputs (parameters)
4. Variables written and not killed by QUIT = potential outputs

**Limitation**: Indirection defeats this analysis. Flag indirection-using labels as "requires runtime variable access."

---

## 5. Risk Assessment

### 5.1 High-Risk Areas

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|-----------|
| GOTO in nested loops | High | Critical | Design state machine fallback early |
| Pattern matching grammar | Medium | Medium | Use regex rule for pattern strings |
| Performance on large files | Low | Medium | Profile with 500-line files |
| textX learning curve | Low | Low | Tutorials and examples available |

### 5.2 Deferred Decisions

These decisions are intentionally deferred to the code generation phase:

1. **Python GOTO strategy**: Break, exception, nested function, or state machine?
2. **Runtime library design**: MVal class, intrinsic function implementations
3. **Global variable interface**: Existing runtime or new design?

---

## 6. MUGJ Test Coverage Analysis

### 6.1 Test File Categories

| Category | Files | Features Tested |
|----------|-------|-----------------|
| FOR loops | V1FORA, V1FORB, V1FORC, V1FORC2 | All forparameter types |
| GOTO | V1GO, V1GO1, V1GO2 | Local, offset, list |
| DO | V1DO, V1DO1, V1DO2, V1DO3 | Calls, blocks, arguments |
| Indirection | V1IDNM, V1IDGO, V1IDDO | Name, goto, do indirection |
| Pattern | V1PAT, V1PAT1, V1PAT2 | Pattern matching |
| XECUTE | V1XECA, V1XECB | Runtime code execution |
| NEW | V1NX1, V1NX2 | Variable scoping |
| Functions | V1FN*, VV2FN* | Intrinsic functions |

### 6.2 Coverage Gaps

- No test files found for: LOCK, JOB, MERGE (complex/advanced)
- Limited coverage of: nested routines, mutual recursion

**Recommendation**: Start with V1FORA (simple FOR), expand to V1FORC2 (complex GOTO+FOR) as integration milestone.

---

## 7. Technology Validation

### 7.1 textX Version

**Decision**: Use textX 4.0+ (current stable)

**Rationale**: Stable API, good documentation, active maintenance.

### 7.2 Python Version

**Decision**: Python 3.10+ (per constitution)

**Rationale**: Match patterns for cleaner visitor code, dataclass improvements.

### 7.3 Test Framework

**Decision**: pytest with fixtures for MUGJ test loading

**Implementation**:
```python
@pytest.fixture
def parser():
    return MUMPSParser()

def test_parse_v1fora(parser, mugj_files):
    asg = parser.parse(mugj_files["V1FORA.m"])
    assert len(asg.labels) > 0
```

---

## 8. Summary of Key Decisions

| Decision | Choice | Justification |
|----------|--------|---------------|
| Parser library | textX | Declarative grammar, Python-native AST |
| ASG structure | Dataclasses | Immutability, computed properties |
| Reference resolution | Multi-pass + RREL | Forward references require 2+ passes |
| FOR classification | 5 types | Covers all MUGJ test patterns |
| GOTO classification | 6 types | Covers all control flow scenarios |
| Variable analysis | Def-Use with NEW boundaries | Enables function signature inference |
| Scope model | Explicit scope containers | Matches Python nested functions |

All NEEDS CLARIFICATION items from Technical Context have been resolved.
