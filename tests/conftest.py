"""Pytest configuration and fixtures for M2PY tests.

Provides fixtures for loading MUGJ test files and validating parser behavior.
"""

from pathlib import Path

import pytest


# Constants for MUGJ test suite location
MUGJ_BASE = Path(__file__).parent / "functional" / "mugj"
MUGJ_INREF = MUGJ_BASE / "inref"
MUGJ_OUTREF = MUGJ_BASE / "outref"
MUGJ_U_INREF = MUGJ_BASE / "u_inref"


@pytest.fixture
def mugj_dir() -> Path:
    """Return the path to the MUGJ test suite directory.
    
    Returns:
        Path to tests/functional/mugj/
    """
    return MUGJ_BASE


@pytest.fixture
def mugj_inref_dir() -> Path:
    """Return the path to the MUGJ inref directory containing .m files.
    
    Returns:
        Path to tests/functional/mugj/inref/
    """
    return MUGJ_INREF


@pytest.fixture
def mugj_file() -> callable:
    """Factory fixture to load a specific MUGJ .m file by name.
    
    Returns:
        A callable that takes a filename and returns the file content.
        
    Usage:
        def test_parse_v1fora(mugj_file):
            source = mugj_file("V1FORA.m")
            # ... parse and validate
    """
    def _load_mugj_file(filename: str) -> str:
        """Load a MUGJ file by name.
        
        Args:
            filename: Name of the .m file (e.g., "V1FORA.m")
            
        Returns:
            The content of the file as a string.
            
        Raises:
            FileNotFoundError: If the file does not exist.
        """
        file_path = MUGJ_INREF / filename
        if not file_path.exists():
            raise FileNotFoundError(f"MUGJ file not found: {file_path}")
        return file_path.read_text(encoding="utf-8")
    
    return _load_mugj_file


@pytest.fixture
def mugj_files() -> callable:
    """Factory fixture to get an iterator over all MUGJ .m files.
    
    Returns:
        A callable that returns an iterator of (filename, content) tuples.
        
    Usage:
        def test_parse_all(mugj_files):
            for filename, source in mugj_files():
                # ... parse and validate
    """
    def _iter_mugj_files():
        for path in sorted(MUGJ_INREF.glob("*.m")):
            yield path.name, path.read_text(encoding="utf-8")
    return _iter_mugj_files


@pytest.fixture
def v1fora_source(mugj_file) -> str:
    """Load V1FORA.m source - the primary FOR command test file.
    
    This is the validation target for User Story 1 (FOR classification).
    
    Returns:
        Content of V1FORA.m
    """
    return mugj_file("V1FORA.m")


@pytest.fixture
def v1fora1_source(mugj_file) -> str:
    """Load V1FORA1.m source - FOR command test cases part 1.
    
    Returns:
        Content of V1FORA1.m  
    """
    return mugj_file("V1FORA1.m")


@pytest.fixture
def v1fora2_source(mugj_file) -> str:
    """Load V1FORA2.m source - FOR command test cases part 2.
    
    Returns:
        Content of V1FORA2.m
    """
    return mugj_file("V1FORA2.m")
