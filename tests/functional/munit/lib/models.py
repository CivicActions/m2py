"""M-Unit data models for baseline capture and test result parsing."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class FailureDetail:
    """One failure or error within a routine execution."""

    entry_tag: str
    routine: str
    test_name: str
    message: str
    kind: Literal["failure", "error"]
    expected: str | None = None
    actual: str | None = None


@dataclass
class MUnitResult:
    """Parsed result of a single M-Unit test routine execution."""

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

    def to_dict(self) -> dict:
        """Serialize to a JSON-compatible dictionary."""
        d = asdict(self)
        return d

    @classmethod
    def from_dict(cls, data: dict) -> MUnitResult:
        """Deserialize from a dictionary."""
        details = [FailureDetail(**fd) for fd in data.pop("failure_details", [])]
        return cls(failure_details=details, **data)


@dataclass
class PackageBaseline:
    """Baseline results for one VistA package's M-Unit tests."""

    package_name: str
    test_list_path: str
    routines: dict[str, MUnitResult] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "package_name": self.package_name,
            "test_list_path": self.test_list_path,
            "routines": {name: r.to_dict() for name, r in self.routines.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> PackageBaseline:
        routines_raw = data.pop("routines", {})
        pkg = cls(**data)
        pkg.routines = {
            name: MUnitResult.from_dict(r) for name, r in routines_raw.items()
        }
        return pkg


@dataclass
class BaselineData:
    """Complete baseline for all M-Unit test routines from a VistA Docker instance."""

    version: str = "1.0"
    captured_at: str = ""
    docker_image: str = ""
    packages: dict[str, PackageBaseline] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "captured_at": self.captured_at,
            "docker_image": self.docker_image,
            "packages": {name: p.to_dict() for name, p in self.packages.items()},
        }

    def to_json(self, path: Path) -> None:
        """Serialize to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
            f.write("\n")

    @classmethod
    def from_dict(cls, data: dict) -> BaselineData:
        packages_raw = data.pop("packages", {})
        baseline = cls(**data)
        baseline.packages = {
            name: PackageBaseline.from_dict(p) for name, p in packages_raw.items()
        }
        return baseline

    @classmethod
    def from_json(cls, path: Path) -> BaselineData:
        """Deserialize from JSON file."""
        with open(path) as f:
            return cls.from_dict(json.load(f))


@dataclass
class TestRoutineConfig:
    """Configuration for running one M-Unit test routine."""

    __test__ = False  # Prevent pytest from trying to collect this dataclass

    routine_name: str
    package_name: str
    invocation: str
    source_path: str
    tier: int = 1
    dependencies: list[str] = field(default_factory=list)
