# Quickstart: MUMPS Semantic Graph Parser

**Feature**: 001-textx-semantic-graph  
**Date**: 2025-12-19  
**Purpose**: Getting started guide for development

---

## Prerequisites

- Python 3.10+
- uv (Python package manager)
- Git

## Setup

### 1. Clone and Install

```bash
# Clone repository (if not already)
git clone <repo-url> m2py
cd m2py

# Install dependencies
uv sync
```

### 2. Verify Environment

```bash
# Check Python version
uv run python --version  # Should be 3.10+

# Run existing tests
uv run pytest -v
```

### 3. Explore MUGJ Test Files

```bash
# List available test files
ls tests/functional/mugj/inref/

# View a simple FOR loop test
cat tests/functional/mugj/inref/V1FORA.m

# View complex GOTO+FOR test
cat tests/functional/mugj/inref/V1FORC2.m
```

---

## Project Structure

```
m2py/
├── src/m2py/
│   ├── __init__.py
│   ├── grammar/                  # textX grammar files
│   │   ├── mumps.tx              # Main routine/label structure grammar
│   │   ├── line.tx               # Line content parsing grammar
│   │   ├── commands.tx           # Command-specific grammar rules
│   │   └── expressions.tx        # Expression grammar
│   ├── asg/                      # ASG element definitions
│   │   ├── __init__.py
│   │   ├── elements.py           # Base classes (ASGElement, MRoutine, MLabel)
│   │   ├── statements.py         # Statement types
│   │   ├── expressions.py        # Expression types
│   │   └── enums.py              # Enumerations (ForLoopType, GotoType, etc.)
│   ├── parser/                   # Parser implementation
│   │   ├── __init__.py
│   │   ├── parser.py             # MUMPSParser class
│   │   ├── exceptions.py         # MUMPSSyntaxError
│   │   └── textx_classes.py      # Custom classes for textX instantiation
│   ├── analysis/                 # ASG analysis passes
│   │   ├── __init__.py
│   │   ├── command_parser.py     # Command parsing via textX grammar
│   │   ├── semantic_analyzer.py  # CST → ASG transformation
│   │   ├── resolver.py           # Reference resolution
│   │   ├── goto_analysis.py      # GOTO classification and analysis
│   │   └── variables.py          # Variable scope analysis
│   └── cli/                      # Command-line interface (future)
│       └── __init__.py
├── tests/
│   ├── unit/                     # Unit tests
│   │   ├── test_grammar.py
│   │   ├── test_command_grammar.py
│   │   ├── test_expression_grammar.py
│   │   ├── test_semantic_analyzer.py
│   │   └── ...
│   ├── integration/              # Integration tests
│   │   └── test_mugj.py
│   └── functional/
│       └── mugj/                 # MUGJ validation suite
├── specs/
│   └── 001-textx-semantic-graph/
│       ├── spec.md
│       ├── plan.md
│       ├── research.md
│       ├── data-model.md
│       └── quickstart.md  # This file
├── mumps-reference/       # MUMPS language spec
└── textX-reference/       # textX documentation
```

---

## First Steps

### Step 1: Create Grammar File

Create `src/m2py/grammar/mumps.tx`:

```textx
// MUMPS Grammar - textX format

Routine:
    labels+=Label
;

Label:
    name=LABEL_NAME formal_list=FormalList? EOL
    lines+=Line
;

Line:
    (level=DOTS)? statements+=Statement[SP]? EOL
;

Statement:
    SetStatement | WriteStatement | ForStatement | 
    IfStatement | GotoStatement | DoStatement | 
    QuitStatement | NewStatement
;

// Terminal patterns
LABEL_NAME: /[%A-Za-z][A-Za-z0-9]*/;
DOTS: /\\.+/;
SP: / +/;
EOL: /\\n/;
```

### Step 2: Define ASG Elements

Create `src/m2py/asg/elements.py`:

```python
"""Core ASG element definitions."""
from dataclasses import dataclass, field
from typing import List, Optional
from abc import ABC

@dataclass
class ASGElement(ABC):
    """Base for all ASG elements."""
    line_number: Optional[int] = None
    parent: Optional['ASGElement'] = field(default=None, repr=False)

@dataclass
class MRoutine(ASGElement):
    """A MUMPS routine."""
    name: str = ""
    labels: List['MLabel'] = field(default_factory=list)

@dataclass  
class MLabel(ASGElement):
    """A label in a routine."""
    name: str = ""
    formal_list: List[str] = field(default_factory=list)
    statements: List['MStatement'] = field(default_factory=list)
```

### Step 3: Implement Parser

Create `src/m2py/parser/parser.py`:

```python
"""MUMPS Parser using textX."""
from pathlib import Path
from textx import metamodel_from_file
from m2py.asg.elements import MRoutine, MLabel

class MUMPSParser:
    def __init__(self):
        grammar_path = Path(__file__).parent.parent / "grammar" / "mumps.tx"
        self.metamodel = metamodel_from_file(
            grammar_path,
            classes=[MRoutine, MLabel]
        )
    
    def parse(self, source: str) -> MRoutine:
        """Parse MUMPS source code into ASG."""
        return self.metamodel.model_from_str(source)
    
    def parse_file(self, path: Path) -> MRoutine:
        """Parse MUMPS file into ASG."""
        return self.metamodel.model_from_file(str(path))
```

### Step 4: Write First Test

Create `tests/unit/test_grammar.py`:

```python
"""Grammar parsing tests."""
import pytest
from m2py.parser.parser import MUMPSParser

@pytest.fixture
def parser():
    return MUMPSParser()

def test_parse_simple_label(parser):
    source = """
MAIN
    S X=1
    W X
    Q
"""
    asg = parser.parse(source)
    assert len(asg.labels) == 1
    assert asg.labels[0].name == "MAIN"

def test_parse_for_loop(parser):
    source = """
TEST
    F I=1:1:10 W I
    Q
"""
    asg = parser.parse(source)
    # Find FOR statement
    for_stmt = asg.labels[0].statements[0]
    assert for_stmt.loop_var == "I"
```

### Step 5: Run Tests

```bash
# Run unit tests
uv run pytest tests/unit/ -v

# Run with coverage
uv run pytest tests/unit/ --cov=m2py
```

---

## Development Workflow

### Adding a New Command

1. **Update grammar** in `mumps.tx`:
   ```textx
   Statement: ... | NewCommand;
   NewCommand: ('NEW'|'N') vars+=VarName[','];
   ```

2. **Add ASG class** in `statements.py`:
   ```python
   @dataclass
   class MNewStatement(MStatement):
       variables: List[str] = field(default_factory=list)
   ```

3. **Register class** in parser:
   ```python
   self.metamodel = metamodel_from_file(
       grammar_path,
       classes=[..., MNewStatement]
   )
   ```

4. **Write test**:
   ```python
   def test_parse_new(parser):
       source = "TEST\n    N X,Y,Z\n    Q\n"
       asg = parser.parse(source)
       new_stmt = asg.labels[0].statements[0]
       assert new_stmt.variables == ["X", "Y", "Z"]
   ```

### Testing Against MUGJ

```python
# tests/integration/test_mugj.py
import pytest
from pathlib import Path
from m2py.parser.parser import MUMPSParser

MUGJ_DIR = Path(__file__).parent.parent / "functional" / "mugj" / "inref"

@pytest.fixture
def parser():
    return MUMPSParser()

@pytest.mark.parametrize("filename", [
    "V1FORA.m",
    "V1FORA1.m", 
    "V1FORA2.m",
])
def test_parse_mugj_file(parser, filename):
    """Ensure MUGJ files parse without error."""
    path = MUGJ_DIR / filename
    asg = parser.parse_file(path)
    assert asg is not None
    assert len(asg.labels) > 0
```

---

## Key Reference Materials

### Architecture Overview

The M2PY parser uses a **two-layer architecture**:

```
MUMPS Source → textX Grammar → CST → Semantic Analyzer → ASG → Analysis Passes → Python Code
                    ↓            ↓           ↓              ↓
              Grammar rules   Custom      Semantic       Domain
              (mumps.tx)      Classes     Analysis      Objects
```

**Layer 1: textX Custom Classes (CST)**
- Located in: `src/m2py/parser/textx_classes.py`
- Classes like `NumericLiteral`, `LocalVariable`, `IntrinsicFunction` are constructed by textX
- Follow textX constructor rules (parent/position as first args)
- **Inherit from ASG classes** for seamless integration

**Layer 2: Semantic Analyzer**  
- Located in: `src/m2py/analysis/semantic_analyzer.py`
- Transforms CST into clean ASG with proper parent relationships
- Unwraps textX wrapper objects (Expr, UnaryExpr)
- Tracks variables and builds symbol tables
- Entry points: `analyze_command()`, `analyze_expression()`

**Why Two Layers?**
1. textX requires specific constructor signatures for custom classes
2. ASG objects need rich relationships (parent references, resolved targets)
3. Separating concerns allows grammar evolution without breaking analysis
4. Semantic analyzer normalizes/validates during transformation

**Key Functions:**
- `analyze_command(textx_cmd) → MStatement`: Converts any textX command to ASG statement
- `analyze_expression(textx_expr) → MExpr`: Converts textX expression to ASG expression
- `parse_for_command_to_asg(for_cmd) → MForStatement`: Converts textX ForCommand model to ASG
- `parse_commands_from_line(line) → List[Command]`: Parses line content into command list

### MUMPS Syntax

- **FOR command**: `mumps-reference/1995__a108031.md`
- **GOTO command**: `mumps-reference/1995__a108032.md`  
- **Expressions**: `mumps-reference/1995__a107*.md`

### textX Documentation

- **Grammar syntax**: `textX-reference/grammar.md`
- **Custom classes**: `textX-reference/metamodel.md`
- **Reference resolution**: `textX-reference/rrel.md`
- **Scoping**: `textX-reference/scoping.md`

### ProLeap Patterns

- **Multi-pass architecture**: `proleap-research/proleap-1/proleap-02-multi-pass-visitor-pattern.md`
- **ASG design**: `proleap-research/proleap-1/proleap-03-abstract-semantic-graph-design.md`
- **MUMPS application**: `proleap-research/proleap-1/proleap-10-applying-to-mumps-transpilation.md`

---

## Validation Milestones

| Milestone | Test | Criteria |
|-----------|------|----------|
| M1 | `V1FORA.m` parses | Basic FOR/SET/WRITE |
| M2 | `V1GO1.m` parses | GOTO with labels |
| M3 | FOR classification | All 5 types identified |
| M4 | GOTO classification | All 6 types identified |
| M5 | `V1FORC2.m` passes | Nested FOR+GOTO |
| M6 | All MUGJ files parse | 100% coverage |

---

## Common Issues

### textX Grammar Errors

**Symptom**: `TextXSyntaxError: Expected ...`

**Solution**: Check grammar for:
- Missing semicolons after rules
- Incorrect regex escaping (`/\\.+/` not `/.+/`)
- Undefined rule references

### Circular Imports

**Symptom**: `ImportError: cannot import name 'X'`

**Solution**: 
- Use `from __future__ import annotations`
- Put all ASG classes in single module or use TYPE_CHECKING

### Forward References

**Symptom**: Labels referenced before definition not found

**Solution**: Ensure multi-pass resolution:
1. Parse all labels first
2. Resolve references in second pass

---

## Next Steps

1. Start with minimal grammar (SET, WRITE, QUIT, label)
2. Validate against simplest MUGJ files
3. Incrementally add commands per priority:
   - P1: FOR, IF
   - P2: GOTO, DO
   - P3: NEW, XECUTE, indirection
4. Add analysis passes after parsing works
