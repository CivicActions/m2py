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
        import m2py.grammar
        import m2py.asg
        import m2py.parser
        import m2py.analysis
        import m2py.cli


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
