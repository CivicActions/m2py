# ASG Reference

The **Abstract Semantic Graph (ASG)** is the core data structure produced by the M2PY parser. It represents the semantic meaning of MUMPS source code in a form suitable for analysis and Python code generation.

## Overview

The ASG is a tree structure rooted at `MRoutine`, with the following hierarchy:

```
MRoutine (top-level)
├── labels: List[MLabel]
│   ├── name: str
│   ├── formal_list: List[str]
│   ├── body: MScope
│   │   └── statements: List[MStatement]
│   │       ├── MSetStatement
│   │       │   └── assignments: List[MAssignment]
│   │       │       ├── target: MVariable | MGlobal
│   │       │       └── value: MExpr
│   │       ├── MIfStatement
│   │       │   ├── condition: MExpr
│   │       │   └── then_scope: MScope
│   │       ├── MForStatement
│   │       │   ├── loop_var: str
│   │       │   ├── parameters: List[MForParameter]
│   │       │   └── body: MScope
│   │       ├── MDoStatement
│   │       │   └── targets: List[MCall]
│   │       └── ... (20+ statement types)
│   ├── callers: List[MCall]  (back-refs)
│   └── goto_sources: List[MGotoStatement]  (back-refs)
└── source_lines: List[str]  (for $TEXT support)
```

## Class Hierarchy

### Base Classes

```
ASGElement (abstract base)
├── source_file, line_number, column
├── parent: ASGElement
└── to_dict() method

MScope (statement container)
├── statements: List[MStatement]
├── parent_scope: MScope
└── walk_statements() iterator
```

### Structural Elements

```
MRoutine (top-level container)
├── name: str
├── labels: List[MLabel]
├── source_lines: List[str]
├── has_unstructured_goto: bool
└── requires_runtime_eval: bool

MLabel (entry point)
├── name: str
├── formal_list: List[str]
├── body: MScope
├── callers: List[MCall]
├── goto_sources: List[MGotoStatement]
├── variables_read/written/newed: set
├── input_variables/output_variables: set
└── signature: FunctionSignature

MCall (reference to label)
├── name: str
├── offset: MExpr (optional)
├── routine: str (optional, for ^routine)
├── arguments: List[MExpr]
├── target: MLabel (resolved)
├── call_type: CallType
└── is_resolved: bool
```

### Statement Types

```
MStatement (base)
├── scope: MScope
├── postcondition: MExpr
└── is_unreachable: bool

Control Flow:
├── MIfStatement     (condition, then_scope)
├── MElseStatement   (body)
├── MForStatement    (loop_var, parameters, body, loop_type, ...)
├── MGotoStatement   (targets, goto_type, exits_loops)
└── MQuitStatement   (return_value, exits_for)

Subroutines:
├── MDoStatement     (targets, body)
└── MDoBlockStatement (body)

Data:
├── MSetStatement    (assignments)
├── MWriteStatement  (arguments)
├── MReadStatement   (targets)
└── MMergeStatement  (destination, source)

Variables:
├── MNewStatement    (variables, exclusive, except_list)
└── MKillStatement   (targets, exclusive, except_list)

Other:
├── MHangStatement   (duration)
├── MHaltStatement
├── MBreakStatement
├── MXecuteStatement (code_expressions)
├── MLockStatement   (targets, lock_type, timeout)
├── MViewStatement   (keyword, arguments)
├── MOpenStatement   (device_expr, parameters, timeout)
├── MCloseStatement  (device_expr)
├── MUseStatement    (device_expr, parameters)
└── MJobStatement    (call, parameters, timeout)
```

### Expression Types

```
MExpr (base)

Literals:
└── MLiteral (value, literal_type: STRING|INTEGER|DECIMAL)

Variables:
├── MVariable (name, subscripts)
├── MGlobal   (name, subscripts)
└── MNakedGlobal (subscripts)

Operators:
├── MBinaryOp (operator, left, right)
└── MUnaryOp  (operator, operand)

Functions:
├── MIntrinsicFunction (name, arguments)
└── MExtrinsicFunction (target: MCall, arguments: List[MActualParameter])

Special:
├── MPatternMatch   (subject, pattern, operator, compiled_regex)
├── MIndirection    (expression, indirection_type, subscripts)
├── MFormatControl  (control_type, expression)
├── MSpecialVariable (name)
└── MActualParameter (passing_mode, expression, variable_name)
```

## Key Concepts

### Source Tracking

Every ASG element tracks its source location:

```python
element.source_file   # Path to source file
element.line_number   # 1-indexed line number
element.column        # 1-indexed column
element.parent        # Parent ASG element
```

### Parent References

Parent references form a bidirectional tree:
- Access parent via `element.parent`
- Find enclosing scope via `statement.scope`
- Find enclosing routine via walking up `parent` chain

### Scopes

`MScope` is the container for statements. Scopes can be nested:
- Label body scope
- IF then_scope
- FOR body scope
- DO block body scope

Use `scope.walk_statements()` to recursively iterate all statements.

### Analysis Fields

Many ASG fields are populated by analysis passes:

| Field | Populated By | Description |
|-------|--------------|-------------|
| `MCall.target` | resolver | Resolved MLabel |
| `MCall.call_type` | resolver | Classification |
| `MLabel.callers` | resolver | Back-references |
| `MGotoStatement.goto_type` | goto_analysis | Classification |
| `MGotoStatement.exits_loops` | goto_analysis | Exited FOR loops |
| `MForStatement.loop_type` | for_analysis | Classification |
| `MForStatement.is_infinite` | for_analysis | Infinite detection |
| `MLabel.input_variables` | variables | Required inputs |
| `MLabel.output_variables` | variables | Modified outputs |
| `MLabel.signature` | variables | FunctionSignature |

## Documentation Index

| Document | Description |
|----------|-------------|
| [structural_elements.md](structural_elements.md) | MRoutine, MLabel, MScope, MCall |
| [statements.md](statements.md) | All statement types |
| [expressions.md](expressions.md) | All expression types |
| [enums.md](enums.md) | Classification enums |
| [type_helpers.md](type_helpers.md) | Type narrowing utilities |

## Source Code

- **Elements**: [`src/m2py/asg/elements.py`](../../src/m2py/asg/elements.py)
- **Statements**: [`src/m2py/asg/statements.py`](../../src/m2py/asg/statements.py)
- **Expressions**: [`src/m2py/asg/expressions.py`](../../src/m2py/asg/expressions.py)
- **Enums**: [`src/m2py/asg/enums.py`](../../src/m2py/asg/enums.py)
