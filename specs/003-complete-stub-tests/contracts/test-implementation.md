# Contract: Test Implementation Standards

**Feature**: 003-complete-stub-tests  
**Date**: January 4, 2026

## Test Naming

Tests follow the pattern established in spec 002:

```
test_{layer}_{section}_{feature}_{case}
```

Examples:
- `test_parser_s7_1_5_intrinsic_functions_ascii`
- `test_asg_s8_2_05_for_bounded_loop_classification`

## Test Structure

### Parser Tests

```python
@pytest.mark.parser
class TestFeatureParser:
    """Parser-level tests for [feature] (§X.X.X)."""

    def test_basic_case(self, parser_or_metamodel_fixture):
        """[Feature] basic form parses correctly (§X.X.X)."""
        # Arrange
        code = "MUMPS code here"
        
        # Act
        result = parse(code)
        
        # Assert
        assert result is not None
        assert result.attribute == expected_value
```

### ASG Tests

```python
@pytest.mark.asg
class TestFeatureASG:
    """ASG-level tests for [feature] (§X.X.X)."""

    def test_semantic_property(self):
        """[Feature] [property] is correctly analyzed (§X.X.X)."""
        # Arrange
        code = "ROUTINE^LABEL\n CODE"
        
        # Act
        routine = parse_and_analyze(code)
        stmt = routine.labels[0].lines[0].statements[0]
        
        # Assert
        assert isinstance(stmt, MExpectedStatement)
        assert stmt.semantic_property == expected_value
```

## Assertion Patterns

### Parser Assertions

- Check `result is not None` (parsing succeeded)
- Check attribute values match source
- Check nested structures are present
- Do NOT check ASG-level semantics in parser tests

### ASG Assertions

- Check statement types: `isinstance(stmt, MStatementType)`
- Check enum classifications: `stmt.loop_type == ForLoopType.BOUNDED`
- Check expression structure: `stmt.condition.operator == "="` 
- Check semantic flags: `stmt.requires_runtime_eval == True`

## Marker Usage

| Marker | Usage |
|--------|-------|
| `@pytest.mark.parser` | Parser-level tests |
| `@pytest.mark.asg` | ASG/semantic analysis tests |
| `@pytest.mark.stub` | Test needs implementation (remove when done) |
| `@pytest.mark.xfail` | Test expected to fail (remove when implemented) |
| `@pytest.mark.skip` | Intentionally out of scope |

## Converting Stubs to Implemented Tests

Before (stub):
```python
@pytest.mark.stub
@pytest.mark.xfail(reason="Not yet implemented: feature X")
def test_feature_x(self):
    """Feature X works correctly (§X.X.X)."""
    pytest.fail("Stub - implement test")
```

After (implemented):
```python
def test_feature_x(self):
    """Feature X works correctly (§X.X.X)."""
    # Actual test implementation
    code = "SET X=1"
    result = analyze_first_command(code)
    assert isinstance(result, MSetStatement)
    assert result.targets[0].name == "X"
```

## Success Verification

After implementing a batch, verify:

```bash
# Run specific batch tests
uv run pytest tests/unit/path/to/file.py -v

# Check no xfails remain in file
uv run pytest tests/unit/path/to/file.py -v 2>&1 | grep -c XFAIL
# Should output: 0

# Update coverage matrix
uv run python utils/audit_tests.py --output docs/coverage-matrix.md
```
