# Feature Specification: Database Storage Backends for YottaDB and IRIS

**Feature Branch**: `025-database-backends`  
**Created**: 2026-02-19  
**Status**: Draft  
**Input**: User description: "Build and test complete GlobalStorageBackend implementations for YottaDB and IRIS using their SDKs (uv add yottadb intersystems-irispython). For development we will be using their docker images: https://hub.docker.com/r/yottadb/yottadb and https://hub.docker.com/r/intersystems/iris-community. For testing, we should use the same core set of globals/lock/etc tests. We already have several, but should fill in any gaps we discover as we go. We can use a pytest mark to identify, if they aren't all in one place. We should be able to run these tests against each backend database by specifing M2PY_GLOBAL_BACKEND together with other environment variables needed for connection parameters (defaulting to the docker defaults)."

## Clarifications

### Session 2026-02-19

- Q: When should backend database connections be established and terminated? → A: Lazy initialization on first global access, persistent until process exit
- Q: What timeout should be used when a LOCK command doesn't specify one? → A: Wait indefinitely (block forever until lock is acquired)
- Q: How should the system handle exceptions raised by YottaDB and IRIS SDKs? → A: Translate SDK exceptions to specific m2py exception types (ConnectionError, PermissionError, etc.)
- Q: Which IRIS namespace should be used when M2PY_IRIS_NAMESPACE is not specified? → A: USER namespace (IRIS default for interactive sessions)
- Q: How should the unified backend test suite be organized within the test directory? → A: tests/runtime/backend/ directory with reorganized existing tests

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Store and Retrieve MUMPS Globals in YottaDB (Priority: P1)

A developer running m2py-generated Python code needs global variables (^PATIENT, ^ORDER) to persist across program executions using YottaDB's native storage engine. They set `M2PY_GLOBAL_BACKEND=yottadb` and connection parameters, then execute their transpiled code. The globals are correctly stored in, and retrieved from, the YottaDB database.

**Why this priority**: YottaDB is the leading open-source MUMPS-compatible database and the primary target for production m2py deployments. Without persistent global storage in YottaDB, transpiled code cannot function as a true MUMPS runtime replacement.

**Independent Test**: Can be fully tested by setting `M2PY_GLOBAL_BACKEND=yottadb`, running transpiled Python code that sets globals (e.g., `^TEST(1)="value"`), stopping the process, then starting a new process that reads the same global and verifies the value persists.

**Acceptance Scenarios**:

1. **Given** YottaDB is running and `M2PY_GLOBAL_BACKEND=yottadb`, **When** transpiled code executes `SET ^PATIENT(123)="John Doe"`, **Then** the value is stored in YottaDB's native database format
2. **Given** a global was previously stored in YottaDB, **When** transpiled code executes `WRITE ^PATIENT(123)`, **Then** the correct value "John Doe" is retrieved from the database
3. **Given** YottaDB backend is configured, **When** transpiled code performs hierarchical subscript operations (e.g., `^DATA(1,2,3)="nested"`), **Then** the subscript hierarchy is preserved in YottaDB's tree structure
4. **Given** YottaDB backend is configured, **When** transpiled code executes `KILL ^PATIENT(123)`, **Then** the node is removed from YottaDB and subsequent reads return empty string

---

### User Story 2 - Store and Retrieve MUMPS Globals in IRIS (Priority: P1)

A developer running m2py-generated Python code in an InterSystems IRIS environment needs global variables to persist using IRIS's native storage engine. They set `M2PY_GLOBAL_BACKEND=iris` and connection parameters, then execute their transpiled code. The globals are correctly stored in, and retrieved from, the IRIS database.

**Why this priority**: IRIS is the commercial successor to Caché and widely deployed in healthcare and enterprise environments. Supporting IRIS enables m2py to integrate with existing MUMPS/Caché installations and leverage IRIS's advanced features.

**Independent Test**: Can be fully tested by setting `M2PY_GLOBAL_BACKEND=iris`, running transpiled Python code that sets globals, then verifying persistence across process restarts and cross-validation with IRIS's native MUMPS tools.

**Acceptance Scenarios**:

1. **Given** IRIS is running and `M2PY_GLOBAL_BACKEND=iris`, **When** transpiled code executes `SET ^PATIENT(123)="John Doe"`, **Then** the value is stored in IRIS's native database format
2. **Given** a global was previously stored in IRIS, **When** transpiled code executes `WRITE ^PATIENT(123)`, **Then** the correct value is retrieved from the database
3. **Given** IRIS backend is configured, **When** transpiled code uses IRIS-specific intrinsic functions (e.g., `$LISTBUILD`, `$ZCONVERT`), **Then** these functions execute correctly using IRIS's native implementations
4. **Given** an IRIS namespace is configured via connection parameters, **When** transpiled code accesses globals, **Then** globals are stored in and retrieved from the specified namespace

---

### User Story 3 - Unified Test Suite Validates All Backends (Priority: P1)

A developer maintaining m2py wants to ensure that all GlobalStorageBackend implementations (in-memory, YottaDB, IRIS) provide identical MUMPS semantics. They run a common test suite in tests/runtime/backend/ marked with `@pytest.mark.backend` against each backend by setting `M2PY_GLOBAL_BACKEND` to different values. All backends pass the same tests, proving semantic equivalence.

**Why this priority**: Without a unified test suite, backend implementations can drift apart in behavior, creating subtle bugs when switching backends. This is essential for ensuring correctness and builds confidence that production backends match the in-memory reference. Organizing tests in tests/runtime/backend/ keeps them close to runtime code.

**Independent Test**: Can be tested by running `uv run pytest -m backend` with `M2PY_GLOBAL_BACKEND=inmemory`, then re-running with `M2PY_GLOBAL_BACKEND=yottadb` and `M2PY_GLOBAL_BACKEND=iris`, verifying all tests pass in all configurations.

**Acceptance Scenarios**:

1. **Given** the backend test suite exists, **When** `M2PY_GLOBAL_BACKEND=inmemory` and tests are run, **Then** all backend tests pass
2. **Given** YottaDB backend is implemented, **When** `M2PY_GLOBAL_BACKEND=yottadb` and tests are run, **Then** all backend tests pass with identical assertions
3. **Given** IRIS backend is implemented, **When** `M2PY_GLOBAL_BACKEND=iris` and tests are run, **Then** all backend tests pass with identical assertions
4. **Given** backend tests cover core operations (set, get, kill, data, order, query, lock, transactions), **When** any backend is tested, **Then** all operations produce MUMPS-compliant results

---

### User Story 4 - Lock Operations Across Backends (Priority: P2)

A developer needs MUMPS LOCK semantics to coordinate concurrent processes accessing shared global data. Their transpiled code includes `LOCK ^RESOURCE(ID)` commands. When using YottaDB or IRIS backends, lock operations use the native database lock mechanisms; with in-memory backend, locks are process-local only.

**Why this priority**: Locks are essential for maintaining data consistency in multi-process MUMPS applications. Database-backed locks provide true inter-process synchronization, a critical capability for production deployments.

**Independent Test**: Can be tested by spawning two concurrent processes with the same backend configuration, having both attempt to lock the same global node, and verifying only one succeeds until the lock is released.

**Acceptance Scenarios**:

1. **Given** YottaDB backend is configured, **When** transpiled code executes `LOCK +^RESOURCE(123)`, **Then** YottaDB's native lock table is updated and other processes attempting the same lock are blocked
2. **Given** IRIS backend is configured, **When** transpiled code executes `LOCK +^RESOURCE(123)`, **Then** IRIS's native lock mechanism is used for inter-process coordination
3. **Given** a lock is held in YottaDB/IRIS, **When** transpiled code executes `LOCK -^RESOURCE(123)`, **Then** the lock is released in the database and becomes available to other processes
4. **Given** a lock timeout is specified, **When** a lock cannot be acquired within the timeout, **Then** the operation returns failure status without waiting indefinitely

---

### User Story 5 - Transaction Support Across Backends (Priority: P2)

A developer needs MUMPS transaction semantics (TSTART/TCOMMIT/TROLLBACK) for atomic global updates. Their transpiled code includes transaction commands. When using YottaDB or IRIS backends, transactions use the native database transaction mechanisms to ensure ACID properties.

**Why this priority**: Transactions are critical for maintaining database integrity in real-world applications, especially in healthcare/financial domains. Native database transactions provide durability and crash recovery.

**Independent Test**: Can be tested by starting a transaction, modifying globals, triggering a rollback, then verifying the globals are restored to their pre-transaction state.

**Acceptance Scenarios**:

1. **Given** YottaDB backend is configured, **When** transpiled code executes TSTART/TCOMMIT, **Then** YottaDB's native transaction mechanism ensures atomic commits
2. **Given** IRIS backend is configured, **When** transpiled code executes TSTART/TCOMMIT, **Then** IRIS's native transaction mechanism ensures atomic commits
3. **Given** a transaction is started, **When** TROLLBACK is executed, **Then** all global changes since TSTART are discarded in the backend database
4. **Given** nested transactions (TSTART within TSTART), **When** operations complete, **Then** the backend correctly handles nested transaction levels per MUMPS semantics

---

### User Story 6 - Connection Configuration via Environment (Priority: P2)

A developer deploying m2py code needs to configure database connection parameters without modifying code. They set environment variables (`M2PY_GLOBAL_BACKEND`, `M2PY_YDB_DIR`, `M2PY_IRIS_HOST`, `M2PY_IRIS_PORT`, etc.) and the runtime automatically connects to the appropriate backend with secure defaults.

**Why this priority**: Configuration via environment variables is standard practice for containerized/cloud deployments and enables the same transpiled code to work across development, staging, and production environments.

**Independent Test**: Can be tested by setting different environment variables and verifying the runtime connects to the correct backend without code changes.

**Acceptance Scenarios**:

1. **Given** `M2PY_GLOBAL_BACKEND=yottadb` and `M2PY_YDB_DIR=/path/to/db`, **When** runtime initializes, **Then** it connects to YottaDB using the specified database directory
2. **Given** `M2PY_GLOBAL_BACKEND=iris` with host/port/namespace variables, **When** runtime initializes, **Then** it connects to the specified IRIS instance
3. **Given** `M2PY_GLOBAL_BACKEND=iris` without M2PY_IRIS_NAMESPACE specified, **When** runtime initializes, **Then** it defaults to USER namespace
4. **Given** no backend environment variable is set, **When** runtime initializes, **Then** it defaults to in-memory backend for development/testing
5. **Given** Docker-based deployment with standard IRIS/YottaDB containers, **When** default connection parameters are used, **Then** the runtime connects successfully without additional configuration

---

### Edge Cases

- What happens when the database connection is lost mid-operation? The backend should raise a clear m2py ConnectionError that can be caught and handled at the application level, wrapping the original SDK exception.
- How does the system handle database connection timeouts? The backend should implement configurable timeout periods and fail gracefully with informative m2py TimeoutError messages.
- What happens when a database is read-only or has insufficient permissions? The backend should detect permission errors during initialization and raise m2py PermissionError with clear diagnostic information.
- How are database-specific limits (max key length, max value size, max subscript depth) handled? The backend should either enforce MUMPS standard limits or document database-specific limits clearly.
- What happens when attempting cross-namespace operations in IRIS? The backend should document namespace isolation semantics in quickstart.md and handle cross-namespace references per IRIS standards.
- How does concurrent access from multiple Python processes behave with each backend? Lock and transaction tests should validate correct multi-process behavior, with thread-safety tests validating concurrent access from multiple threads.
- What happens when a backend is not available (e.g., Docker container not running)? The runtime should provide a clear, actionable m2py BackendConnectionError directing the user to start the necessary services.
- What happens when LOCK operations don't specify a timeout? Locks wait indefinitely until acquired, matching standard MUMPS semantics.
- How are database-specific limits (max key length, max value size, max subscript depth) handled? Backends document database-specific limits in docs/limitations.md rather than enforcing MUMPS standard limits, allowing users to leverage native database capabilities.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST provide persistent global storage using YottaDB database
- **FR-002**: System MUST provide persistent global storage using IRIS database
- **FR-003**: System MUST support all global operations (get, set, kill, data, order, query, lock, unlock, transaction operations) in both YottaDB and IRIS backends
- **FR-004**: System MUST provide connection configuration via environment variables (M2PY_GLOBAL_BACKEND, M2PY_YDB_DIR, M2PY_IRIS_HOST, M2PY_IRIS_PORT, M2PY_IRIS_NAMESPACE, M2PY_IRIS_USERNAME, M2PY_IRIS_PASSWORD)
- **FR-005**: System MUST default to Docker-standard connection parameters when specific parameters are not provided
- **FR-006**: System MUST integrate with YottaDB using its official SDK
- **FR-007**: System MUST integrate with IRIS using its official SDK
- **FR-008**: System MUST maintain a unified test suite that validates all backend implementations with identical test cases, organized in tests/runtime/backend/ directory with reorganized existing backend tests
- **FR-009**: Backend tests MUST pass identically for inmemory, yottadb, and iris backends
- **FR-010**: System MUST preserve MUMPS global subscript hierarchy (arbitrary depth, string/numeric subscripts, collation order) in backend storage
- **FR-011**: System MUST track naked references per MUMPS semantics (handled by m2py codegen layer, not database backends)
- **FR-012**: System MUST implement $DATA intrinsic function correctly (returning 0/1/10/11) across all backends
- **FR-013**: System MUST implement $ORDER with forward/reverse direction across all backends
- **FR-014**: System MUST implement $QUERY for tree traversal across all backends
- **FR-015**: System MUST implement LOCK operations using native database lock mechanisms for YottaDB and IRIS
- **FR-016**: System MUST implement transaction operations (TSTART/TCOMMIT/TROLLBACK) using native database transactions for YottaDB and IRIS
- **FR-017**: System MUST handle transaction nesting levels correctly per MUMPS semantics
- **FR-018**: System MUST provide clear error messages when database connection fails
- **FR-019**: System MUST provide clear error messages when attempting to use a backend without required dependencies installed
- **FR-020**: System MUST document namespace isolation for IRIS backend
- **FR-021**: Backend implementations MUST handle concurrent access from multiple Python processes correctly
- **FR-022**: System MUST canonicalize subscripts (numeric vs string forms) consistently across backends per MUMPS collation rules
- **FR-023**: System MUST support global MERGE operations across backends
- **FR-024**: System MUST support global increment operations ($INCREMENT) across backends with proper atomicity
- **FR-025**: System MUST translate SDK-specific exceptions to consistent m2py exception types (BackendConnectionError, BackendPermissionError, BackendTimeoutError) while preserving original error details
- **FR-026**: System MUST support SSVN (Structured System Variable Node) operations (^$JOB, ^$LOCK, etc.) across all backends for system-wide state access

### Key Entities

- **GlobalStorageBackend**: Persistent storage mechanism for MUMPS globals. Maintains hierarchical key-value data with correct MUMPS collation semantics. Provides inter-process coordination via locks and transactions. Three implementations: in-memory (for testing), YottaDB (open-source production), and IRIS (commercial production).

- **Connection Configuration**: Set of parameters defining how to connect to a backend database. Includes database type selection, location/network parameters, authentication credentials, and namespace selection. Sourced from environment variables to support deployment flexibility. Database connections are established lazily on first global access and persist until process exit.

- **Global Reference**: Hierarchical key-value structure consisting of global name (e.g., "PATIENT") and subscript tuple (e.g., ("123", "NAME")). Supports arbitrary subscript depth, mixed numeric/string subscripts, and MUMPS-standard collation order (numeric before string).

- **Lock Coordination**: Mechanism for synchronizing concurrent access to shared global data across processes. Uses database-native lock tables for YottaDB and IRIS to provide true inter-process synchronization. Supports lock timeouts and multiple lock modes. When no timeout is specified, locks wait indefinitely until acquired.

- **Transaction Boundary**: Atomic unit of global updates with ACID properties. Allows multiple global modifications to commit or rollback as a single operation. Supports nested transactions per MUMPS semantics.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Developers can switch between in-memory, YottaDB, and IRIS backends by changing a single environment variable, with all backends producing identical functional behavior
- **SC-002**: Global data persists across application restarts when using YottaDB or IRIS backends, enabling long-running production deployments
- **SC-003**: Concurrent processes can safely coordinate access to shared globals using locks, with blocked processes resuming when locks are released
- **SC-004**: Transaction rollback restores globals to their exact pre-transaction state, ensuring data consistency after errors
- **SC-005**: Developers receive clear, actionable error messages when database connection fails, with SDK exceptions translated to specific m2py exception types (ConnectionError, PermissionError, TimeoutError) indicating exactly what configuration is missing or incorrect
- **SC-006**: Global read/write operations complete with 95th percentile latency under 10ms for typical workloads (≤3 subscript levels, ≤1KB values) on local database
- **SC-007**: MUMPS global subscript collation order is preserved identically across all backends, ensuring $ORDER traversal produces consistent results
- **SC-008**: Data written through m2py can be read by native MUMPS processes in the same database, proving full interoperability
- **SC-009**: Developers can configure all backends for both local Docker development and remote production deployments using environment variables only

## Assumptions

- **Development Environment**: Developers have Docker available for running YottaDB and IRIS containers during development and testing
- **Database Management**: YottaDB and IRIS databases are externally managed; m2py is responsible only for connecting to and using existing database instances, not for installation, configuration, or administration
- **Connection Security**: For production deployments, secure connection practices (TLS, credential management, network isolation) are handled at the infrastructure level, outside m2py's scope
- **Default Configuration**: Docker-standard connection parameters match the defaults used by official yottadb/yottadb and intersystems/iris-community container images
- **SDK Availability**: Official Python SDKs are available and maintained by YottaDB and InterSystems; m2py depends on these SDKs rather than implementing low-level database protocols
- **Backward Compatibility**: The existing GlobalStorageBackend protocol defined in m2py is sufficient for both YottaDB and IRIS; no breaking changes to the protocol are needed
- **Performance Expectations**: Local database operations (same host) complete in single-digit milliseconds; network-based operations may be slower depending on deployment architecture
- **Namespace Conventions**: IRIS namespace configuration follows InterSystems conventions; YottaDB uses a single global namespace without isolation. When M2PY_IRIS_NAMESPACE is not specified, the USER namespace is used as default.
