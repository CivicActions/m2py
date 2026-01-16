# Quickstart: Extended Operators, Commands & Completion

**Feature**: Spec 011 - Extended Operators, Commands & Completion
**Date**: 2026-01-15

## Setup

```bash
# Ensure you're on the feature branch
git checkout 011-operators-commands-completion

# Install dependencies
uv sync

# Run existing tests to verify baseline
uv run pytest tests/unit/codegen/ -v
```

## Key Files to Modify

### Operators (expressions.py)

```python
# src/m2py/codegen/expressions.py

def _generate_binary_op(op: MBinaryOp, ctx: "GeneratorContext") -> str:
    """Add cases for new operators."""
    # ... existing operators ...
    
    elif op.operator == "&":
        # Logical AND: both operands must be truthy
        return f"int(m_truth({left}) and m_truth({right}))"
    
    elif op.operator == "!":
        # Logical OR: either operand truthy
        return f"int(m_truth({left}) or m_truth({right}))"
    
    elif op.operator == "[":
        # Contains: right is substring of left
        return f"int(str({right}) in str({left}))"
    
    elif op.operator == "]":
        # Follows: left sorts after right
        return f"int(str({left}) > str({right}))"
    
    elif op.operator == "]]":
        # Sorts after (strictly): left > right and left not empty
        return f"int(str({left}) != '' and str({left}) > str({right}))"
    
    elif op.operator == "?":
        # Pattern match: use compiled regex
        # Note: right is pattern string or expression
        return f"int(m_pattern_match(str({left}), {right}))"

def _generate_unary_op(op: MUnaryOp, ctx: "GeneratorContext") -> str:
    """Fix NOT operator to return int."""
    # ...
    elif op.operator == "'":
        # Logical NOT - must return 0 or 1, not True/False
        return f"int(not m_truth({operand}))"
```

### Format Controls (statements.py)

```python
# src/m2py/codegen/statements.py

def _generate_write(stmt: MWriteStatement, ctx: "GeneratorContext") -> None:
    """Handle format controls in WRITE arguments."""
    for arg in stmt.arguments:
        if isinstance(arg, MExpr):
            expr = generate_expr(arg, ctx)
            ctx.emitter.line(f"_rt.write({expr})")
        elif isinstance(arg, MFormatControl):
            if arg.control_type == FormatControlType.NEWLINE:
                ctx.emitter.line('_rt.write("\\n")')
            elif arg.control_type == FormatControlType.FORMFEED:
                ctx.emitter.line('_rt.write("\\f")')
            elif arg.control_type == FormatControlType.CHARCODE:
                char_expr = generate_expr(arg.argument, ctx)
                ctx.emitter.line(f"_rt.write(chr(int({char_expr})))")
            elif arg.control_type == FormatControlType.TAB:
                col_expr = generate_expr(arg.argument, ctx)
                ctx.emitter.line(f"_rt.write_tab(int({col_expr}))")
```

### Postconditions (statements.py)

```python
# src/m2py/codegen/statements.py

def generate_statement(stmt: "MStatement", ctx: "GeneratorContext") -> None:
    """Wrap statement in conditional if postcondition present."""
    if stmt.postcondition is not None:
        cond_expr = generate_expr(stmt.postcondition, ctx)
        ctx.emitter.line(f"if m_truth({cond_expr}):")
        ctx.emitter.indent()
        _dispatch_statement(stmt, ctx)
        ctx.emitter.dedent()
    else:
        _dispatch_statement(stmt, ctx)
```

### Special Variables (expressions.py)

```python
# src/m2py/codegen/expressions.py

def _generate_special_variable(var: MSpecialVariable, ctx: "GeneratorContext") -> str:
    name = var.name.upper()
    
    if name in ("TEST", "T"):
        return "int(_test)"
    elif name in ("HOROLOG", "H"):
        return "_rt.horolog()"
    elif name in ("JOB", "J"):
        return "_rt.job()"
    elif name == "IO":
        return "_rt.io()"
    elif name == "X":
        return "_rt.x()"
    elif name == "Y":
        return "_rt.y()"
    elif name in ("STORAGE", "S"):
        return "2147483647"  # Large value for Python
    elif name in ("STACK", "ST"):
        return "_rt.stack_level()"
    elif name in ("QUIT", "Q"):
        return "_rt.quit_flag()"
    else:
        raise NotImplementedError(f"Special variable ${var.name} not supported")
```

## Testing

### Run a specific test

```bash
# Test operators
uv run pytest tests/unit/codegen/s7_expressions/test_s7_2_operators.py -v

# Test format controls
uv run pytest tests/unit/codegen/s8_commands/test_s8_2_25_write.py -v
```

### Validate against YDB

```bash
# Single expression
uv run python utils/validate.py --code 'TEST W 1&1 Q'

# Debug mode (shows AST and generated Python)
uv run python utils/validate.py --debug --code 'TEST W 1&1 Q'
```

### Quick validation loop

```bash
# Check logical AND
echo -e 'TEST\n W 1&1,!\n Q' | docker run --rm -i ydb

# Check format control
echo -e 'TEST\n W "A",!,"B",!\n Q' | docker run --rm -i ydb

# Check pattern match
echo -e 'TEST\n W "ABC"?1A.A,!\n Q' | docker run --rm -i ydb
```

## Implementation Checklist

### Phase 1: Operators (P1)
- [ ] Fix NOT (`'`) to return 0/1
- [ ] Add AND (`&`)
- [ ] Add OR (`!`)
- [ ] Add negated comparisons (`'=`, `'<`, `'>`)

### Phase 2: Format Controls (P1)
- [ ] Handle MFormatControl in _generate_write()
- [ ] NEWLINE (`!`)
- [ ] FORMFEED (`#`)
- [ ] CHARCODE (`*n`)
- [ ] TAB (`?n`) with column tracking

### Phase 3: Postconditions (P1)
- [ ] Check postcondition in generate_statement()
- [ ] Wrap in conditional when present

### Phase 4: String Operators (P2)
- [ ] Contains (`[`)
- [ ] Follows (`]`)
- [ ] Sorts after (`]]`)

### Phase 5: Pattern Match (P2)
- [ ] Import pattern compiler
- [ ] Handle pattern match operator (`?`)

### Phase 6: Special Variables (P2)
- [ ] $HOROLOG
- [ ] $JOB
- [ ] $IO
- [ ] $X, $Y
- [ ] $STORAGE
- [ ] $STACK
- [ ] $QUIT

### Phase 7: Commands (P2-P3)
- [ ] Multiple SET assignments
- [ ] NEW command (selective)
- [ ] KILL command (exclusive)
- [ ] MERGE command
- [ ] HANG command
- [ ] HALT command
- [ ] READ command
