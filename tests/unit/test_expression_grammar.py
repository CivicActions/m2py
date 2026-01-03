"""Tests for the expression grammar (expressions.tx).

Low-level tests that verify the textX expression grammar directly.
Tests literals, variables, operators, functions, and special constructs.

For semantic analysis of expressions, see test_semantic_analyzer.py.
"""

import pytest
from pathlib import Path
from textx import metamodel_from_file
from m2py.parser.textx_classes import get_expression_classes


@pytest.fixture
def expr_metamodel():
    """Load the expression grammar metamodel with custom classes.

    The custom classes (LocalVariable, GlobalVariable, etc.) ensure proper
    inheritance from ASG base classes (MVariable, MExpr). This is required
    for tests that use SemanticAnalyzer, which dispatches based on isinstance
    checks against these base classes.
    """
    grammar_path = (
        Path(__file__).parent.parent.parent
        / "src"
        / "m2py"
        / "grammar"
        / "expressions.tx"
    )
    return metamodel_from_file(
        str(grammar_path), classes=get_expression_classes(), skipws=True
    )


# TestNumericLiterals migrated to tests/unit/parser/s7_expressions/test_s7_1_4_literals.py

# TestStringLiterals migrated to tests/unit/parser/s7_expressions/test_s7_1_4_literals.py


# TestLocalVariables migrated to tests/unit/parser/s7_expressions/test_s7_1_2_variables.py


# TestGlobalVariables migrated to tests/unit/parser/s7_expressions/test_s7_1_2_variables.py


# TestExtendedGlobalReferences migrated to tests/unit/parser/s7_expressions/test_s7_1_2_variables.py


# TestBinaryOperators migrated to tests/unit/parser/s7_expressions/test_s7_2_operators.py

# TestUnaryOperators migrated to tests/unit/parser/s7_expressions/test_s7_2_operators.py

# TestChainedUnarySemantics migrated to tests/unit/parser/s7_expressions/test_s7_2_operators.py

# TestIntrinsicFunctions migrated to tests/unit/parser/s7_expressions/test_s7_1_5_intrinsic_functions.py

# TestCacheSpecificFunctions migrated to tests/unit/parser/s7_expressions/test_s7_1_5_intrinsic_functions.py

# TestZFunctionsAndISVs migrated to tests/unit/parser/extensions/ydb/test_zfunctions.py

# TestSpecialVariables migrated to tests/unit/parser/s7_expressions/test_s7_1_7_special_variables.py


# TestSelectFunction migrated to tests/unit/parser/s7_expressions/test_s7_1_5_intrinsic_functions.py

# TestIndirection migrated to tests/unit/parser/s7_expressions/test_s7_3_indirection.py

# TestExtrinsicFunctions migrated to tests/unit/parser/s7_expressions/test_s7_1_6_extrinsic_functions.py

# TestExternalFunctions migrated to tests/unit/parser/s7_expressions/test_s7_1_6_extrinsic_functions.py

# TestParentheses migrated to tests/unit/parser/s7_expressions/test_s7_2_operators.py

# TestComplexExpressions migrated to tests/unit/parser/s7_expressions/test_s7_2_operators.py

# NOTE: This entire file can be deleted once all migrations are verified working.
# All test classes have been migrated to their spec-aligned locations.
