# Operator Codegen API Contract

**Spec 011**: Extended Operators, Commands & Completion

## Binary Operator Translation

All binary operators go through `_generate_binary_op()` in `codegen/expressions.py`.

### Operator Mapping

| MUMPS | Python Pattern | Notes |
|-------|---------------|-------|
| `+` | `(m_num(L) + m_num(R))` | Numeric addition |
| `-` | `(m_num(L) - m_num(R))` | Numeric subtraction |
| `*` | `(m_num(L) * m_num(R))` | Multiplication |
| `/` | `(m_num(L) / m_num(R))` | Division |
| `\` | `(int(m_num(L) // m_num(R)))` | Integer division |
| `#` | `(m_num(L) % m_num(R))` | Modulo |
| `=` | `m_compare(L, "=", R)` | Equality |
| `<` | `m_compare(L, "<", R)` | Less than |
| `>` | `m_compare(L, ">", R)` | Greater than |
| `_` | `(str(L) + str(R))` | String concatenation |
| `&` | `int(m_truth(L) and m_truth(R))` | **Spec 011** Logical AND |
| `!` | `int(m_truth(L) or m_truth(R))` | **Spec 011** Logical OR |
| `[` | `int(str(R) in str(L))` | **Spec 011** Contains |
| `]` | `int(str(L) > str(R))` | **Spec 011** Follows |
| `]]` | `int(str(L) != "" and str(L) > str(R))` | **Spec 011** Sorts after |
| `?` | `int(m_pattern_match(str(L), R))` | **Spec 011** Pattern match |

### Negated Comparison Operators

Negated comparisons are parsed as unary NOT applied to comparison:

| MUMPS | ASG Structure | Python Pattern |
|-------|---------------|----------------|
| `'=` | `MUnaryOp('', MBinaryOp('=', L, R))` | `int(not m_compare(L, "=", R))` |
| `'<` | `MUnaryOp('', MBinaryOp('<', L, R))` | `int(not m_compare(L, "<", R))` |
| `'>` | `MUnaryOp('', MBinaryOp('>', L, R))` | `int(not m_compare(L, ">", R))` |

## Unary Operator Translation

| MUMPS | Python Pattern | Notes |
|-------|---------------|-------|
| `-` | `(-m_num(operand))` | Numeric negation |
| `+` | `(+m_num(operand))` | Numeric coercion |
| `'` | `int(not m_truth(operand))` | **Spec 011 FIX** Logical NOT |

**Critical**: NOT must return `0` or `1`, never Python `True`/`False`.

## Helper Function Contracts

### m_truth(value) -> bool
Convert MUMPS value to Python boolean.
- Empty string → `False`
- `"0"`, `0`, `0.0`, `"0.0"` → `False`
- All other values → `True`

### m_num(value) -> float
Convert MUMPS value to Python number.
- Extracts leading numeric portion
- `"3.14abc"` → `3.14`
- `""` → `0`

### m_compare(a, op, b) -> int
Compare values with MUMPS semantics.
- Returns `1` (true) or `0` (false)
- Handles numeric vs string comparison appropriately

### m_pattern_match(string, pattern) -> int (NEW)
Match string against MUMPS pattern.
- Uses `compile_pattern_to_regex()` to convert pattern
- Returns `1` if match, `0` otherwise
- Pattern may be literal string or runtime expression
