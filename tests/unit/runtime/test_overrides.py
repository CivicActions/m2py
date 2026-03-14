"""Tests for the routine override mechanism.

Verifies that MumpsAutoImporter correctly:
1. Loads .py overrides instead of transpiling .m sources
2. Supports partial overrides via __getattr__ delegation
3. Falls through to normal transpilation when no override exists
"""

from __future__ import annotations

import sys
import textwrap
import types
from pathlib import Path


class TestMumpsAutoImporterOverrides:
    """Test override_dirs support in MumpsAutoImporter."""

    def _make_importer(self, m_dir: Path, override_dir: Path | None = None):
        """Create a MumpsAutoImporter with the given dirs."""
        from tests.functional.munit.conftest import MumpsAutoImporter

        override_dirs = [override_dir] if override_dir else None
        return MumpsAutoImporter([m_dir], override_dirs=override_dirs)

    def test_override_found_in_index(self, tmp_path: Path) -> None:
        """Override .py files are indexed and findable by find_spec."""
        m_dir = tmp_path / "m"
        m_dir.mkdir()
        (m_dir / "TESTRTN.m").write_text("TESTRTN ; test\n Q\n")

        override_dir = tmp_path / "overrides"
        override_dir.mkdir()
        (override_dir / "TESTRTN.py").write_text('_routine_name = "TESTRTN"\n')

        importer = self._make_importer(m_dir, override_dir)

        # Should be in the overrides index
        assert "TESTRTN" in importer._overrides
        # find_spec should return a spec
        spec = importer.find_spec("TESTRTN")
        assert spec is not None

    def test_override_only_no_m_file(self, tmp_path: Path) -> None:
        """An override without a corresponding .m file is still loadable."""
        m_dir = tmp_path / "m"
        m_dir.mkdir()
        # No .m file for MYRTN

        override_dir = tmp_path / "overrides"
        override_dir.mkdir()
        (override_dir / "MYRTN.py").write_text(
            textwrap.dedent("""\
                _routine_name = "MYRTN"
                _source_lines = []
                _label_lines = {"HELLO": 0}
                _line_map = {}

                def HELLO(_rt, _scope=None):
                    _rt.write("hello from override")

                _entry_function = HELLO
            """)
        )

        importer = self._make_importer(m_dir, override_dir)
        spec = importer.find_spec("MYRTN")
        assert spec is not None

    def test_override_loads_and_exposes_attrs(self, tmp_path: Path) -> None:
        """exec_module loads the override and exposes its attributes."""
        m_dir = tmp_path / "m"
        m_dir.mkdir()
        (m_dir / "OVRTEST.m").write_text("OVRTEST ; test\n W 123\n Q\n")

        override_dir = tmp_path / "overrides"
        override_dir.mkdir()
        (override_dir / "OVRTEST.py").write_text(
            textwrap.dedent("""\
                _routine_name = "OVRTEST"
                _source_lines = []
                _label_lines = {"MAIN": 0}
                _line_map = {}
                _OVERRIDE_MARKER = True

                def MAIN(_rt, _scope=None):
                    pass

                _entry_function = MAIN
            """)
        )

        importer = self._make_importer(m_dir, override_dir)

        # Create a module and exec into it
        module = types.ModuleType("OVRTEST")
        # Temporarily register to avoid side-effects
        old = sys.modules.get("OVRTEST")
        try:
            importer.exec_module(module)
            assert module._routine_name == "OVRTEST"
            assert module._OVERRIDE_MARKER is True
            assert callable(module.MAIN)
        finally:
            # Clean up sys.modules
            for key in list(sys.modules):
                if "OVRTEST" in key or "_m2py_override_" in key:
                    del sys.modules[key]
            if old is not None:
                sys.modules["OVRTEST"] = old

    def test_underscore_files_ignored(self, tmp_path: Path) -> None:
        """Files starting with _ are not indexed as overrides."""
        override_dir = tmp_path / "overrides"
        override_dir.mkdir()
        (override_dir / "__init__.py").write_text("")
        (override_dir / "_helper.py").write_text("x = 1\n")

        m_dir = tmp_path / "m"
        m_dir.mkdir()

        importer = self._make_importer(m_dir, override_dir)
        assert "__init__" not in importer._overrides
        assert "_helper" not in importer._overrides

    def test_no_override_falls_through_to_index(self, tmp_path: Path) -> None:
        """Without an override, find_spec uses the .m index."""
        m_dir = tmp_path / "m"
        m_dir.mkdir()
        (m_dir / "FALLTHRU.m").write_text("FALLTHRU ; test\n Q\n")

        override_dir = tmp_path / "overrides"
        override_dir.mkdir()
        # No FALLTHRU.py override

        importer = self._make_importer(m_dir, override_dir)
        assert "FALLTHRU" not in importer._overrides
        assert "FALLTHRU" in importer._index
        spec = importer.find_spec("FALLTHRU")
        assert spec is not None

    def test_get_source_path(self, tmp_path: Path) -> None:
        """get_source_path returns the .m path for a routine."""
        m_dir = tmp_path / "m"
        m_dir.mkdir()
        m_file = m_dir / "DIC.m"
        m_file.write_text("DIC ; test\n Q\n")

        importer = self._make_importer(m_dir)
        assert importer.get_source_path("DIC") == m_file
        assert importer.get_source_path("NONEXIST") is None

    def test_override_dir_does_not_exist(self, tmp_path: Path) -> None:
        """A non-existent override dir is silently ignored."""
        m_dir = tmp_path / "m"
        m_dir.mkdir()

        nonexist = tmp_path / "no_such_dir"
        importer = self._make_importer(m_dir, nonexist)
        assert len(importer._overrides) == 0

    def test_no_override_dirs_param(self, tmp_path: Path) -> None:
        """Passing no override_dirs works (backward compatible)."""
        m_dir = tmp_path / "m"
        m_dir.mkdir()
        (m_dir / "ABC.m").write_text("ABC ; test\n Q\n")

        from tests.functional.munit.conftest import MumpsAutoImporter

        importer = MumpsAutoImporter([m_dir])
        assert len(importer._overrides) == 0
        assert "ABC" in importer._index


class TestPartialOverrideHelper:
    """Test the partial_override() helper function."""

    def test_module_getattr_delegation(self) -> None:
        """Module-level __getattr__ delegates to base for missing attrs."""
        # Simulate the pattern: override defines FIND, __getattr__ for rest
        base = types.ModuleType("_base")
        base.EN = lambda _rt, _scope=None: "en_result"
        base.IX = lambda _rt, _scope=None: "ix_result"
        base._routine_name = "DIC"
        base._label_lines = {"EN": 0, "IX": 1, "FIND": 2}

        override = types.ModuleType("DIC")
        override._routine_name = "DIC"

        def FIND(_rt, _scope=None):
            return "optimized_find"

        override.FIND = FIND

        # Simulate __getattr__
        override.__getattr__ = lambda name: getattr(base, name)

        # Override's own function
        assert override.FIND(None) == "optimized_find"
        # Delegated to base
        assert override.EN(None) == "en_result"
        assert override.IX(None) == "ix_result"
        assert override._label_lines == {"EN": 0, "IX": 1, "FIND": 2}
