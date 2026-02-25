# Module Contract: M-Unit Data Models

**Module**: `vista_test.munit.models`  
**Location**: `vista-test/src/vista_test/munit/models.py`  
**Used by**: All M-Unit modules (parser, baseline, adapter)

## Public Interface

All data classes from `data-model.md` live here:

```python
from dataclasses import dataclass, field
from typing import Literal
import json
from pathlib import Path


@dataclass
class FailureDetail:
    entry_tag: str
    routine: str
    test_name: str
    message: str
    kind: Literal["failure", "error"]
    expected: str | None = None
    actual: str | None = None


@dataclass
class MUnitResult:
    routine: str
    package: str
    total_tests: int = 0
    failures: int = 0
    errors: int = 0
    entry_tags: int = 0
    routines_ran: int = 0
    status: Literal["pass", "fail", "error", "timeout", "skip"] = "skip"
    failure_details: list[FailureDetail] = field(default_factory=list)
    raw_output: str = ""
    duration_seconds: float | None = None
    error_message: str | None = None

    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> "MUnitResult": ...


@dataclass
class PackageBaseline:
    package_name: str
    test_list_path: str
    routines: dict[str, MUnitResult] = field(default_factory=dict)


@dataclass
class BaselineData:
    version: str = "1.0"
    captured_at: str = ""
    docker_image: str = ""  # e.g., "worldvista/osehravista"
    packages: dict[str, PackageBaseline] = field(default_factory=dict)

    def to_json(self, path: Path) -> None:
        """Serialize to JSON file."""
        ...

    @classmethod
    def from_json(cls, path: Path) -> "BaselineData":
        """Deserialize from JSON file."""
        ...


@dataclass
class TestRoutineConfig:
    routine_name: str
    package_name: str
    invocation: str
    source_path: str
    tier: int = 1
    dependencies: list[str] = field(default_factory=list)
```

## Serialization Contract

- All models round-trip through JSON: `obj → to_dict() → json.dumps → json.loads → from_dict() → obj`
- `BaselineData.to_json() / from_json()` handles file I/O
- JSON keys use snake_case matching Python field names
- `None` values serialized as JSON `null`

## Dependencies

- Standard library only (`dataclasses`, `json`, `pathlib`)
- No external imports
