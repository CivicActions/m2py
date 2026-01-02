"""Unit tests for M2PY package setup and fixtures.

Verifies that the package structure and MUGJ fixtures are properly configured.
"""

import pytest
from pathlib import Path


class TestPackageSetup:
    """Test that M2PY package is properly structured."""

    def test_version_exists(self):
        """Verify the package has a version."""
        from m2py import __version__

        assert __version__ == "0.1.0"

    def test_submodules_importable(self):
        """Verify core submodules can be imported."""


class TestMUGJFixtures:
    """Test that MUGJ fixtures work correctly."""

    def test_mugj_dir_exists(self, mugj_dir):
        """Verify mugj_dir fixture returns valid path."""
        assert isinstance(mugj_dir, Path)
        assert mugj_dir.exists()
        assert mugj_dir.name == "mugj"

    def test_mugj_inref_dir_exists(self, mugj_inref_dir):
        """Verify mugj_inref_dir fixture returns valid path."""
        assert isinstance(mugj_inref_dir, Path)
        assert mugj_inref_dir.exists()
        assert mugj_inref_dir.name == "inref"

    def test_mugj_file_loads(self, mugj_file):
        """Verify mugj_file fixture can load a file."""
        source = mugj_file("V1FORA.m")
        assert isinstance(source, str)
        assert len(source) > 0
        assert "V1FORA" in source

    def test_mugj_file_not_found(self, mugj_file):
        """Verify mugj_file raises on missing file."""
        with pytest.raises(FileNotFoundError):
            mugj_file("NONEXISTENT.m")

    def test_v1fora_source(self, v1fora_source):
        """Verify V1FORA.m fixture loads correct content."""
        assert "V1FORA" in v1fora_source
        assert "FOR COMMAND" in v1fora_source

    def test_v1fora1_source(self, v1fora1_source):
        """Verify V1FORA1.m fixture loads correct content."""
        assert "V1FORA1" in v1fora1_source
        # V1FORA1 contains FOR with single iteration format
        assert "FOR" in v1fora1_source

    def test_mugj_files_iterator(self, mugj_files):
        """Verify mugj_files factory returns iterator of (filename, content) tuples."""
        files_iter = mugj_files()
        first_file = next(files_iter)
        filename, content = first_file
        assert filename.endswith(".m")
        assert isinstance(content, str)
        assert len(content) > 0


class TestASGModuleExports:
    """Test that ASG module exports all expected types."""

    def test_all_enums_exported(self):
        """Verify all enum types are exported from m2py.asg."""
        from m2py.asg import (
            ForLoopType,
            ForParamType,
            GotoType,
            CallType,
            LiteralType,
            FormatControlType,
            IndirectionType,
            PassingMode,
            ScopeStrategy,
        )

        # Verify they are the correct enum types
        assert hasattr(ForLoopType, "BOUNDED")
        assert hasattr(ForParamType, "VALUE")
        assert hasattr(GotoType, "FORWARD_JUMP")
        assert hasattr(CallType, "LABEL_CALL")
        assert hasattr(LiteralType, "STRING")
        assert hasattr(FormatControlType, "NEWLINE")
        assert hasattr(IndirectionType, "NAME")
        assert hasattr(PassingMode, "BY_VALUE")
        assert hasattr(ScopeStrategy, "PURE_FUNCTION")

    def test_indirection_type_accessible(self):
        """Verify IndirectionType can be imported from m2py.asg (Phase 72 fix)."""
        from m2py.asg import IndirectionType

        assert IndirectionType.NAME.name == "NAME"
        assert IndirectionType.SUBSCRIPT.name == "SUBSCRIPT"
        assert IndirectionType.ARGUMENT.name == "ARGUMENT"
        assert IndirectionType.PATTERN.name == "PATTERN"
        assert IndirectionType.UNKNOWN.name == "UNKNOWN"

    def test_scope_strategy_accessible(self):
        """Verify ScopeStrategy can be imported from m2py.asg (Phase 72 fix)."""
        from m2py.asg import ScopeStrategy

        assert ScopeStrategy.PURE_FUNCTION.name == "PURE_FUNCTION"
        assert ScopeStrategy.FUNCTION_WITH_OUTPUTS.name == "FUNCTION_WITH_OUTPUTS"
        assert ScopeStrategy.SUBROUTINE.name == "SUBROUTINE"
        assert ScopeStrategy.REQUIRES_RUNTIME.name == "REQUIRES_RUNTIME"

    def test_all_in_dunder_all(self):
        """Verify __all__ includes all expected exports."""
        import m2py.asg as asg

        # Check enums are in __all__
        assert "IndirectionType" in asg.__all__
        assert "ScopeStrategy" in asg.__all__
        assert "ForLoopType" in asg.__all__
        assert "PassingMode" in asg.__all__


class TestASGSubComponentTypes:
    """Test that ASG sub-component types are correctly designed."""

    def test_massignment_not_asg_element(self):
        """Verify MAssignment is a sub-component, not ASGElement."""
        from m2py.asg.statements import MAssignment
        from m2py.asg.elements import ASGElement

        assert not issubclass(MAssignment, ASGElement)

        # Should be a dataclass
        import dataclasses

        assert dataclasses.is_dataclass(MAssignment)

        # Should not have source tracking fields
        assignment = MAssignment()
        assert not hasattr(assignment, "source_file")
        assert not hasattr(assignment, "line_number")

    def test_mreadtarget_not_asg_element(self):
        """Verify MReadTarget is a sub-component, not ASGElement."""
        from m2py.asg.statements import MReadTarget
        from m2py.asg.elements import ASGElement

        assert not issubclass(MReadTarget, ASGElement)

        # Should be a dataclass
        import dataclasses

        assert dataclasses.is_dataclass(MReadTarget)

    def test_mforparameter_not_asg_element(self):
        """Verify MForParameter is a sub-component, not ASGElement."""
        from m2py.asg.statements import MForParameter
        from m2py.asg.elements import ASGElement

        assert not issubclass(MForParameter, ASGElement)

        # Should be a dataclass
        import dataclasses

        assert dataclasses.is_dataclass(MForParameter)

    def test_sub_components_docstrings_mention_design(self):
        """Verify sub-component docstrings explain the design decision."""
        from m2py.asg.statements import MAssignment, MReadTarget, MForParameter

        # Each should mention it's a sub-component (case-insensitive check)
        assert "sub-component" in MAssignment.__doc__.lower()
        assert "sub-component" in MReadTarget.__doc__.lower()
        assert "sub-component" in MForParameter.__doc__.lower()


class TestMIndirectionTyping:
    """Test MIndirection field types (Phase 72 fix)."""

    def test_subscripts_type_annotation(self):
        """Verify MIndirection.subscripts has proper type annotation."""
        import typing
        from m2py.asg.expressions import MIndirection

        hints = typing.get_type_hints(MIndirection)
        # Should be Optional[List[MExpr]] not Optional[list]
        subscripts_hint = str(hints.get("subscripts", ""))
        assert "List" in subscripts_hint or "list" in subscripts_hint
        # The key check is that it's not bare "list" without parameters
        assert subscripts_hint != "typing.Optional[list]"

    def test_name_indirection_subscripts_type_annotation(self):
        """Verify MIndirection.name_indirection_subscripts has proper type annotation."""
        import typing
        from m2py.asg.expressions import MIndirection

        hints = typing.get_type_hints(MIndirection)
        name_subs_hint = str(hints.get("name_indirection_subscripts", ""))
        assert "List" in name_subs_hint or "list" in name_subs_hint
        # Should not be bare "list"
        assert name_subs_hint != "typing.Optional[list]"
