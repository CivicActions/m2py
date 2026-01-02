# Contract: Test Markers

This document defines the pytest marker conventions for the M2PY test suite.

## Marker Registration (conftest.py)

```python
# tests/conftest.py

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "parser: Tests at textX grammar/parser level")
    config.addinivalue_line("markers", "asg: Tests at ASG semantic analysis level")
    config.addinivalue_line("markers", "codegen: Tests at Python code generation level")
    config.addinivalue_line("markers", "stub: Placeholder test, expected to fail until implemented")
    config.addinivalue_line("markers", "slow: Long-running test, skipped by default")
    config.addinivalue_line("markers", "pre1995: Tests pre-1995 MUMPS syntax")
    config.addinivalue_line("markers", "ydb: YottaDB-specific extension test")
```

## Marker Usage Patterns

### Category Markers (Required)

Every test MUST have exactly one category marker:

```python
@pytest.mark.parser
def test_parse_set_command():
    """Parser-level test."""
    pass

@pytest.mark.asg
def test_set_command_variable_binding():
    """ASG-level test."""
    pass

@pytest.mark.codegen
def test_set_command_executes():
    """Codegen-level test."""
    pass
```

### Status Markers

#### Stub (Placeholder)

```python
@pytest.mark.stub
@pytest.mark.parser
@pytest.mark.xfail(reason="Not yet implemented: $ASCII function parsing")
def test_ascii_basic_parsing():
    """Test $ASCII parses single character."""
    pytest.fail("Stub - implement test")
```

#### Skip (Out of Scope)

```python
@pytest.mark.parser
@pytest.mark.skip(reason="Out of scope: VIEW command. See docs/limitations.md")
def test_view_command():
    """VIEW command not supported."""
    pass
```

### Extension Markers

```python
@pytest.mark.ydb
@pytest.mark.codegen
def test_zwrite_output():
    """YottaDB ZWRITE extension test."""
    pass
```

## Command-Line Usage

### Run by Category

```bash
# Run only parser tests
uv run pytest -m parser

# Run only implemented codegen tests
uv run pytest -m "codegen and not stub"

# Run all stubs (see what's pending)
uv run pytest -m stub --collect-only
```

### Run by Spec Section

```bash
# Run all §7 expression tests
uv run pytest tests/unit/*/s7_expressions/

# Run specific function tests
uv run pytest -k "ascii or char"
```

### Coverage Analysis

```bash
# Count implemented vs stub tests
uv run pytest -m "not stub" --collect-only | wc -l
uv run pytest -m stub --collect-only | wc -l
```

## Marker Validation

The `conftest.py` should validate markers:

```python
def pytest_collection_modifyitems(config, items):
    """Validate test markers."""
    category_markers = {'parser', 'asg', 'codegen'}
    
    for item in items:
        item_markers = {m.name for m in item.iter_markers()}
        has_category = bool(item_markers & category_markers)
        
        if not has_category:
            pytest.fail(f"Test {item.name} missing category marker (parser/asg/codegen)")
```

## Migration Compatibility

During migration, old tests without markers should be:
1. Run with warning (not failure)
2. Added to migration checklist
3. Given markers when moved to new structure
