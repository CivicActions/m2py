"""Shared fixtures for meta-level tests.

Imports fixtures from parser/conftest.py for tests that need grammar-level access.
"""

# Import command_metamodel fixture from parser conftest for edge case tests
from tests.unit.parser.conftest import command_metamodel

__all__ = ["command_metamodel"]
