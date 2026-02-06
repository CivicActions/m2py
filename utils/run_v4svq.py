"""Run V4SVQ test suite to diagnose $QUIT failures."""

import sys
import types
from pathlib import Path

from m2py.codegen import generate_python
from m2py.runtime import MUMPSRuntime, run_with_goto_support

# Load all routines from mvts/inref
inref_dir = Path("tests/functional/mvts/inref")
routine_modules = {}
errors = {}
for mfile in sorted(inref_dir.glob("*.m")):
    name = mfile.stem
    try:
        source = mfile.read_text()
        code = generate_python(source)
        mod = types.ModuleType(name)
        sys.modules[name] = mod
        exec(compile(code, f"{name}.py", "exec"), mod.__dict__)
        routine_modules[name] = mod
    except Exception as e:
        errors[name] = str(e)

if "V4SVQ" in errors:
    print(f"TRANSPILE ERROR for V4SVQ: {errors['V4SVQ']}")
    sys.exit(1)

rt = MUMPSRuntime()
rt._capture_output = True
rt.clear()
mod = routine_modules.get("V4SVQ")
rt._current_routine = "V4SVQ"
rt._current_source_lines = getattr(mod, "_source_lines", [])
rt._current_label_lines = getattr(mod, "_label_lines", {})
entry = getattr(mod, "V4SVQ", None)
_scope = {}


def wrapped_func(_rt, _scope=_scope):
    return entry(_rt, _scope=_scope)


try:
    run_with_goto_support(wrapped_func, rt, _scope)
except Exception:
    import traceback

    traceback.print_exc()

output = rt.get_output()
print(output)
