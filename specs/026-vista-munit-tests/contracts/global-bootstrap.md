# Module Contract: global_bootstrap (SUPERSEDED)

> **This contract has been superseded by [zwr.md](zwr.md).**
>
> The original `GlobalBootstrap` class design was replaced by standalone ZWR
> functions in `src/m2py/runtime/zwr.py` during tasks.md restructuring.
> See [zwr.md](zwr.md) for the current contract.
>
> Key changes:
> - ZWR parsing/import/export lives in **m2py** (`src/m2py/runtime/zwr.py`), not vista-test
> - Standalone functions (`parse_zwr_line`, `import_zwr`, `export_zwr`) replace the `GlobalBootstrap` class
> - CLI integration via `m2py globals import/export`
> - Vista-test fixtures call `import_zwr()` to load cached ZWR data
