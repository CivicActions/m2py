#!/usr/bin/env python
"""Test a single MUGJ routine for debugging."""

import sys
import types
import traceback
from pathlib import Path

from m2py.codegen import generate_python
from m2py.codegen.names import translate_name
from m2py.runtime import MUMPSRuntime

INREF_DIR = Path("YDBTest/mugj/inref")


def load_routine(name: str) -> types.ModuleType | None:
    """Load and transpile a routine."""
    path = INREF_DIR / f"{name}.m"
    if not path.exists():
        print(f"{name}: FILE NOT FOUND")
        return None

    try:
        code = generate_python(path.read_text())
        python_name = translate_name(name)
        module = types.ModuleType(python_name)
        sys.modules[python_name] = module
        exec(code, module.__dict__)
        print(f"Loaded {name} as {python_name}")
        return module
    except Exception as e:
        print(f"{name}: TRANSPILE ERROR - {type(e).__name__}: {e}")
        return None


def test_routine_with_deps(name: str, deps: list[str]) -> None:
    """Test a routine with its dependencies loaded."""
    modules = {}

    # Load dependencies first
    for dep in deps:
        module = load_routine(dep)
        if module:
            modules[dep] = module

    # Load main routine
    main_module = load_routine(name)
    if not main_module:
        return
    modules[name] = main_module

    # Execute
    runtime = MUMPSRuntime()
    runtime._capture_output = True
    runtime.clear()
    _scope = {}

    python_name = translate_name(name)
    entry = getattr(main_module, python_name, None)
    if not entry:
        print(f"{name}: No entry point '{python_name}' found")
        return

    print(f"\nExecuting {name}...")
    try:
        entry(runtime, _scope=_scope)
        print("SUCCESS")
        output = runtime.get_output()
        print(f"Output ({len(output)} chars):")
        print(output[:1000] if len(output) > 1000 else output)
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python utils/test_mugj_routine.py ROUTINE_NAME [DEP1 DEP2 ...]")
        sys.exit(1)

    routine = sys.argv[1]
    deps = sys.argv[2:] if len(sys.argv) > 2 else []
    test_routine_with_deps(routine, deps)
