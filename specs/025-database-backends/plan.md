# Implementation Plan: Database Storage Backends for YottaDB and IRIS

**Branch**: `025-database-backends` | **Date**: 2026-02-19 | **Spec**: [spec.md](spec.md)  
**Input**: Feature specification from `/workspaces/m2py/specs/025-database-backends/spec.md`

## Summary

Implement production-ready GlobalStorageBackend implementations for YottaDB and IRIS databases using their official Python SDKs. This enables m2py-generated code to persist MUMPS globals in real database backends, replacing the in-memory-only implementation. The unified test suite validates semantic equivalence across all three backends (inmemory, yottadb, iris), ensuring correct MUMPS behavior for globals, locks, and transactions. Environment-based configuration allows developers to switch backends via `M2PY_GLOBAL_BACKEND` without code changes.

**Technical Approach**: Wrap native YottaDB Python API and IRIS Native SDK for Python, translating their APIs to match the existing GlobalStorageBackend protocol. Use lazy connection initialization, SDK-to-m2py exception translation, and Docker containers for development/testing. Reorganize existing global/lock/transaction tests into `tests/runtime/backend/` with pytest marks for selective backend execution.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: yottadb (YottaDB Python wrapper), intersystems-irispython (IRIS Native SDK)  
**Storage**: YottaDB persistent storage, IRIS persistent storage (both via Docker for dev/test)  
**Testing**: pytest with pytest-order, backend parameterization via M2PY_GLOBAL_BACKEND environment variable  
**Target Platform**: Linux servers (production), Docker containers (development)  
**Project Type**: Single project with runtime library extension  
**Performance Goals**: 95th percentile latency <10ms for typical global operations (≤3 subscript levels, ≤1KB values) on local database  
**Constraints**: Must maintain 100% semantic equivalence with in-memory backend, no breaking changes to GlobalStorageBackend protocol  
**Scale/Scope**: 26 functional requirements, ~100+ existing tests to reorganize, 2 new backend classes, unified test suite with 3 backend configurations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### ✅ Pass: Semantic Correctness First
- Backend implementations must produce identical MUMPS behavior to InMemoryGlobalStorage
- YottaDB is reference implementation for validation
- All edge cases (collation, naked refs, transactions) map to database-native semantics

### ✅ Pass: YDB as Reference Implementation
- YottaDB backend is P1 priority
- IRIS backend validated against YDB behavior for common operations
- Test suite uses YDB as ground truth

### ✅ Pass: Strict Layer Separation  
- Backend implementations are pure adapters (no parsing/analysis logic)
- All subscript canonicalization delegated to existing SubscriptCanonicalizer
- Exception translation keeps SDK errors accessible via `__cause__`

### ✅ Pass: Explicit Over Implicit
- Connection lifecycle explicitly documented (lazy init on first use)
- Lock timeout semantics explicit (None = wait indefinitely)
- Exception types explicit (ConnectionError, PermissionError, TimeoutError)
- Namespace defaults explicit (IRIS USER namespace when unspecified)

### ✅ Pass: Foundational Correctness
- GlobalStorageBackend protocol already validated through InMemory implementation
- No protocol changes needed - pure implementation work
- Test reorganization validates existing test quality before adding backends

### ✅ Pass: Cross-Cutting Semantics
- Collation order preserved across backends
- Naked reference tracking works identically  
- $DATA semantics (0/1/10/11) maintained
- Transaction nesting levels consistent

**No violations - proceed to Phase 0**

## Project Structure

### Documentation (this feature)

```text
specs/025-database-backends/
├── plan.md              # This file (implementation plan)
├── research.md          # Phase 0: SDK research, best practices, integration patterns
├── data-model.md        # Phase 1: Backend connection model, exception hierarchy
├── quickstart.md        # Phase 1: Developer guide for using backends
├── contracts/           # Phase 1: Backend API contracts (empty - protocol already defined)
│   └── backend-protocol.md  # Reference to existing GlobalStorageBackend
└── checklists/
    └── requirements.md  # Spec validation checklist (already exists)
```

### Source Code (repository root)

```text
src/m2py/runtime/
├── __init__.py          # [EXISTING] Runtime exports, get_global_storage() factory
├── globals.py           # [EXISTING] GlobalStorageBackend protocol, InMemoryGlobalStorage
├── yottadb_backend.py   # [NEW] YottaDBGlobalStorage implementation
├── iris_backend.py      # [NEW] IRISGlobalStorage implementation
├── exceptions.py        # [EXISTING] MRuntimeError base class
└── backend_exceptions.py # [NEW] Backend-specific exceptions (ConnectionError, etc.)

tests/runtime/backend/   # [NEW DIRECTORY] Unified backend test suite
├── conftest.py          # [NEW] Pytest fixtures for backend selection via M2PY_GLOBAL_BACKEND
├── test_basic_operations.py    # [REORGANIZED] get, set, kill, data
├── test_order_query.py         # [REORGANIZED] $ORDER, $QUERY traversal
├── test_subscript_canonicalization.py  # [REORGANIZED] Numeric/string collation
├── test_naked_references.py    # [REORGANIZED] Naked indicator tracking
├── test_merge_operations.py    # [REORGANIZED] MERGE command
├── test_increment.py           # [REORGANIZED] $INCREMENT atomicity
├── test_locks.py               # [REORGANIZED] LOCK/UNLOCK operations
├── test_transactions.py        # [REORGANIZED] TSTART/TCOMMIT/TROLLBACK
├── test_extended_globals.py    # [REORGANIZED] Namespace/environment references
├── test_connection_lifecycle.py # [NEW] Lazy init, persistence, cleanup
├── test_exception_translation.py # [NEW] SDK exception mapping
└── test_cross_validation.py    # [NEW] Data written by m2py readable by native MUMPS

tests/unit/runtime/
├── test_global_storage.py  # [EXISTING] Keep as-is for factory/configuration tests
└── [other existing tests]  # [UNCHANGED]

Dockerfile.yottadb          # [NEW] YDB container for testing (project root)
utils/
├── ydb.sh                   # [NEW] Run commands inside YDB container (auto-builds image)
├── iris.sh                  # [NEW] Run commands with IRIS container (auto-starts, exports env)
├── run_mumps_ydb.py         # [RENAMED from ydb.py] Run MUMPS through YottaDB via Docker
├── run_mumps_iris.py        # [RENAMED from iris.py] Run MUMPS through IRIS via Docker
└── validate.py              # [EXISTING] Compare m2py output against YDB/IRIS
```

**Structure Decision**: Single project with runtime extension. New backend implementations are added as sibling modules to `globals.py`. Existing global/lock/transaction tests are reorganized from `tests/unit/runtime/`, `tests/integration/`, and various `tests/unit/codegen/` files into the new `tests/runtime/backend/` directory. This consolidation creates a focused test suite that can be executed against any backend via environment configuration.

For development and testing:
- **YottaDB**: `Dockerfile.yottadb` + `utils/ydb.sh` — runs commands inside a YDB Docker container with the workspace mounted. The `yottadb` Python SDK requires `libyottadb.so` which is only available inside the container.
- **IRIS**: `utils/iris.sh` — auto-starts the IRIS Docker container and exports connection env vars. The `intersystems-irispython` SDK connects over TCP, so commands run locally.

## Complexity Tracking

None. All constitution principles validated - no violations require justification.

---

## Phase 0: Research & Discovery

**Output**: `research.md` (SDK exploration, best practices, integration patterns)

**Next Steps**: 
1. Generate research.md with detailed SDK API mappings
2. Document YottaDB Python wrapper API → GlobalStorageBackend protocol mapping
3. Document IRIS Native SDK API → GlobalStorageBackend protocol mapping
4. Research Docker container configuration for both databases
5. Identify SDK-specific edge cases and limitations

Run Phase 0 research generation separately to populate research.md.

## Phase 1: Design & Contracts

**Prerequisites**: research.md complete

**Outputs**:
- `data-model.md`: Backend connection models, exception hierarchy
- `quickstart.md`: Developer guide for using backends
- `contracts/backend-protocol.md`: Reference to existing GlobalStorageBackend

**Next Steps**:
1. Define YottaDBGlobalStorage class architecture
2. Define IRISGlobalStorage class architecture  
3. Define backend exception hierarchy (ConnectionError, PermissionError, TimeoutError)
4. Document connection lifecycle patterns
5. Document test fixture strategy for backend selection
6. Update agent context with new technologies

Run Phase 1 design generation separately to populate design artifacts.

## Phase 2: Implementation Tasks

**Prerequisites**: Phase 1 design complete

**Output**: `tasks.md` (generated by `/speckit.tasks` command)

This phase is triggered separately via `/speckit.tasks` after design is finalized.

---

## Completion Status

### ✅ Phase 0: Research & Discovery (COMPLETE)

**Artifacts Generated**:
- [research.md](research.md) - Comprehensive SDK API mappings, Docker configuration, best practices, technology decisions

**Key Findings**:
- YottaDB Python wrapper maps cleanly to GlobalStorageBackend protocol
- IRIS Native SDK provides comprehensive MUMPS database functionality
- Both SDKs support all 25+ protocol methods with semantic equivalence
- Transaction handling requires adapter for YottaDB (callback model vs explicit)
- Docker-based testing strategy defined for both backends

### ✅ Phase 1: Design & Contracts (COMPLETE)

**Artifacts Generated**:
- [data-model.md](data-model.md) - Backend class architecture, exception hierarchy, connection models
- [quickstart.md](quickstart.md) - Developer guide with examples, configuration reference, troubleshooting
- [contracts/backend-protocol.md](contracts/backend-protocol.md) - Protocol reference and semantic guarantees

**Key Decisions**:
- Lazy connection initialization (defer until first use)
- Thread-safety via threading.Lock
- Environment-based configuration (12-factor app principle)
- Exception translation layer (SDK → m2py types)
- Unified test suite with pytest marks for backend selection

**Agent Context Updated**:
- ✅ Added YottaDB and IRIS technologies to `.github/agents/copilot-instructions.md`
- ✅ Technologies: yottadb (YottaDB Python wrapper), intersystems-irispython (IRIS Native SDK)
- ✅ Databases: YottaDB persistent storage, IRIS persistent storage (both via Docker)

### 🚧 Phase 2: Implementation Tasks (PENDING)

**Next Command**: `/speckit.tasks` - Generate detailed task breakdown for implementation

**Expected Tasks**:
1. Implement YottaDBGlobalStorage class (src/m2py/runtime/yottadb_backend.py)
2. Implement IRISGlobalStorage class (src/m2py/runtime/iris_backend.py)
3. Create backend exception classes (src/m2py/runtime/backend_exceptions.py)
4. Update get_global_storage() factory (src/m2py/runtime/__init__.py)
5. Reorganize tests into tests/runtime/backend/ directory
6. Create backend test fixtures (tests/runtime/backend/conftest.py)
7. Create Docker configuration (`Dockerfile.yottadb` + `utils/ydb.sh`, `utils/iris.sh`)
8. Write cross-validation tests (test_cross_validation.py)
9. Update CI/CD for multi-backend testing
10. Documentation updates (README.md, architecture.md)

---

**Plan Status**: ✅ COMPLETE (Phases 0 and 1)  
**Ready For**: Phase 2 task generation via `/speckit.tasks`
