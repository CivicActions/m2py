# Contract: Test Naming Conventions

This document defines the naming conventions for test files and functions in the spec-aligned test structure.

## File Naming

### Pattern

```
test_s{section}_{subsection}_{feature}.py
```

### Examples

| Spec Section | File Name |
|--------------|-----------|
| §7.1.2 Local Variable Name | `test_s7_1_2_variables.py` |
| §7.1.5 Intrinsic Functions | `test_s7_1_5_intrinsic_functions.py` |
| §8.2.18 SET Command | `test_s8_2_18_set.py` |
| §8.2.3 DO Command | `test_s8_2_03_do.py` |

### Rules

1. **Section numbers**: Use underscores to separate section levels (e.g., `s7_1_5` for §7.1.5)
2. **Leading zeros**: Use for single-digit command numbers (e.g., `s8_2_03` not `s8_2_3`)
3. **Feature suffix**: Use lowercase snake_case descriptor (e.g., `intrinsic_functions`, `set`, `do`)
4. **Extensions**: YDB Z-commands use `test_z{command}.py` in `extensions/ydb/` directory

## Test Function Naming

### Pattern

```python
def test_{feature}_{variant}_{detail}():
```

### Examples

| Test Purpose | Function Name |
|--------------|---------------|
| Basic SET parsing | `test_set_simple_assignment` |
| SET with postcondition | `test_set_with_postcondition` |
| SET multiple targets | `test_set_multiple_assignments` |
| $ASCII single char | `test_ascii_single_character` |
| $ASCII empty string | `test_ascii_empty_string_returns_negative_one` |
| FOR bounded loop | `test_for_bounded_increment` |
| FOR string list | `test_for_string_list_iteration` |

### Rules

1. **Feature first**: Start with the primary feature being tested (command name, function name, etc.)
2. **Variant second**: Describe the specific variation or form (e.g., `simple`, `with_postcondition`, `multiple`)
3. **Detail optional**: Add clarifying detail for edge cases (e.g., `returns_negative_one`)
4. **Snake_case**: Use lowercase with underscores throughout
5. **No redundant prefixes**: Avoid `test_parser_set_...` — the directory already indicates parser level

## Test Class Naming

### Pattern

```python
class Test{Feature}{Variant}:
```

### Examples

| Class Purpose | Class Name |
|---------------|------------|
| SET command parsing | `TestSetCommandParsing` |
| SET command ASG analysis | `TestSetCommandAnalysis` |
| $ASCII function | `TestAsciiFunctionParsing` |
| Pattern match operators | `TestPatternMatchOperators` |

### Rules

1. **PascalCase**: Standard Python class naming
2. **Feature-focused**: Name by the spec feature, not the test type
3. **One class per major variation**: Split by postconditions, indirection, etc. if large

## Docstring Requirements (FR-004)

Every test class and function SHOULD include a docstring referencing the spec section:

```python
class TestSetCommandParsing:
    """Tests for SET command parsing (§8.2.18).
    
    Verifies textX grammar correctly captures SET syntax variations
    including simple assignment, multiple targets, and postconditions.
    """

    def test_set_simple_assignment(self):
        """SET X=1 produces SetCommand with single assignment (§8.2.18.1)."""
        ...
```

## Migration Renaming Guide

When migrating existing tests, rename to align with conventions:

| Original Name | New Name |
|---------------|----------|
| `test_simple_set` | `test_set_simple_assignment` |
| `test_set_full_keyword` | `test_set_keyword_full_form` |
| `test_analyze_simple_literal` | `test_literal_integer_analysis` |
| `test_parse_set_command` | `test_set_command_parsing` |

## Shared Symbol Lists

These canonical lists prevent duplication across task descriptions:

### SSVN_LIST (Structured System Variables - §7.1.3)

**In-scope** (require stub tests):
- `^$JOB` - Job information
- `^$ROUTINE` - Routine information
- `^$GLOBAL` - Global directory
- `^$LOCK` - Lock information
- `^$DEVICE` - Device information
- `^$CHARACTER` - Character set information
- `^$SYSTEM` - System information
- `^$Z...` - Any implementation-defined SSVNs (YottaDB specific)

**Out-of-scope** (require skip-marked tests per FR-055):
- `^$LIBRARY` - Routine library management
- `^$EVENT` - Event processing

### INTRINSIC_FUNCTION_LIST (§7.1.5)

$ASCII, $CHAR, $DATA, $EXTRACT, $FIND, $FNUMBER, $GET, $JUSTIFY, $LENGTH, $NAME, $NEXT (deprecated—@pytest.mark.pre1995), $ORDER, $PIECE, $QLENGTH, $QSUBSCRIPT, $QUERY, $RANDOM, $REVERSE, $SELECT, $STACK, $TEXT, $TRANSLATE, $VIEW

### SPECIAL_VARIABLE_LIST (§7.1.7)

$DEVICE, $ECODE, $ESTACK, $ETRAP, $HOROLOG, $IO, $JOB, $KEY, $PRINCIPAL, $QUIT, $REFERENCE, $STACK, $STORAGE, $SYSTEM, $TEST, $TLEVEL, $TRESTART, $X, $Y

## Marker Integration

All test functions must have appropriate markers:

```python
@pytest.mark.parser
def test_set_simple_assignment(self):
    """§8.2.18: Basic SET parsing."""
    ...

@pytest.mark.asg
def test_set_variable_tracking(self):
    """§8.2.18: SET updates variable tracking in ASG."""
    ...

@pytest.mark.codegen
def test_set_executes_correctly(self):
    """§8.2.18: Generated Python SET assignment works."""
    ...
```
