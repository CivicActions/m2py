# Tasks: MUMPS Semantic Graph Parser

**Input**: Design documents from `/specs/001-textx-semantic-graph/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/parser-api.md ✅

**Tests**: Tests are included as they are fundamental to the MUGJ validation approach defined in the specification (Constitution Principle II: Test-Driven Validation).

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create project structure per plan.md: src/m2py/{grammar,asg,parser,analysis,cli}/, tests/{unit,integration}/
- [X] T002 Add textX dependency (4.0+) to pyproject.toml
- [X] T003 [P] Create src/m2py/__init__.py with version and public API exports
- [X] T004 [P] Create src/m2py/grammar/__init__.py (empty placeholder)
- [X] T005 [P] Create src/m2py/asg/__init__.py with ASG element exports
- [X] T006 [P] Create src/m2py/parser/__init__.py with MUMPSParser export
- [X] T007 [P] Create src/m2py/analysis/__init__.py with analysis function exports
- [X] T008 [P] Create tests/unit/__init__.py (empty placeholder)
- [X] T009 [P] Create tests/integration/__init__.py (empty placeholder)
- [X] T010 Create pytest fixture for MUGJ file loading in tests/conftest.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### ASG Base Classes (from data-model.md)

- [X] T011 Implement ASGElement base dataclass with source tracking in src/m2py/asg/elements.py
- [X] T012 [P] Implement enumerations (ForLoopType, ForParamType, GotoType, CallType, LiteralType) in src/m2py/asg/enums.py
- [X] T013 [P] Implement MExpr base and literal types (MLiteral, MVariable, MGlobal, MNakedGlobal) in src/m2py/asg/expressions.py
- [X] T014 [P] Implement MBinaryOp, MUnaryOp, MIntrinsicFunction, MExtrinsicFunction in src/m2py/asg/expressions.py
- [X] T015 [P] Implement MPatternMatch, MIndirection, MSpecialVariable in src/m2py/asg/expressions.py
- [X] T016 Implement MStatement base, MScope container, MSetStatement in src/m2py/asg/statements.py
- [X] T017 [P] Implement MWriteStatement, MReadStatement, MQuitStatement, MHaltStatement in src/m2py/asg/statements.py
- [X] T018 [P] Implement MNewStatement, MKillStatement, MHangStatement in src/m2py/asg/statements.py
- [X] T019 [P] Implement MXecuteStatement, MLockStatement, MMergeStatement, MViewStatement in src/m2py/asg/statements.py
- [X] T020 Implement MRoutine, MLabel with back-reference support in src/m2py/asg/elements.py
- [X] T021 Implement MCall with resolution tracking in src/m2py/asg/elements.py

### Parser Foundation (from contracts/parser-api.md)

- [X] T022 Implement MUMPSSyntaxError exception class in src/m2py/parser/exceptions.py
- [X] T023 Create minimal textX grammar skeleton in src/m2py/grammar/mumps.tx (routine, label, comment rules)
- [X] T024 Implement MUMPSParser.__init__() with grammar loading in src/m2py/parser/parser.py
- [X] T025 Implement MUMPSParser.parse() stub returning MRoutine in src/m2py/parser/parser.py
- [X] T026 Implement MUMPSParser.parse_file() with file reading in src/m2py/parser/parser.py
- [X] T027 Write unit test for MUMPSParser initialization in tests/unit/test_parser.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - Parse and Analyze Simple MUMPS Routines (Priority: P1) 🎯 MVP

**Goal**: Parse MUMPS routines with SET, WRITE, IF, and simple bounded FOR constructs

**Independent Test**: Parse V1FORA.m and verify ASG contains correct labels, statements, and FOR loop classification

### Tests for User Story 1

- [X] T028 [P] [US1] Unit test for SET statement parsing in tests/unit/test_grammar.py
- [X] T029 [P] [US1] Unit test for WRITE statement parsing in tests/unit/test_grammar.py
- [X] T030 [P] [US1] Unit test for bounded FOR parsing in tests/unit/test_grammar.py
- [X] T031 [P] [US1] Unit test for simple IF parsing in tests/unit/test_grammar.py
- [X] T032 [US1] Integration test: parse V1FORA.m in tests/integration/test_mugj.py

### Grammar Implementation for User Story 1

Note: Grammar tasks T033-T040 were addressed through an alternative approach. The textX grammar captures line structure, and command parsing is done in the classifier layer. This allows incremental development while still passing MUGJ tests.

- [X] T033 [US1] Add SET command grammar rule (S|SET target=expr, assignments) in src/m2py/grammar/mumps.tx
- [X] T034 [P] [US1] Add WRITE command grammar rule (W|WRITE arguments) in src/m2py/grammar/mumps.tx
- [X] T034a [P] [US1] Add READ command grammar rule (R|READ arguments with timeout) per FR-002 in src/m2py/grammar/mumps.tx
- [X] T035 [P] [US1] Add QUIT command grammar rule (Q|QUIT return_value?) in src/m2py/grammar/mumps.tx
- [X] T036 [US1] Add expression grammar (literals, local variables, subscripted variables per FR-013, globals ^NAME per FR-014, all operators per FR-005: +,-,*,/,\,#,**,=,<,>,',&,!,_,[,],]],?, unary +/-, strict L-to-R eval per FR-050) in src/m2py/grammar/mumps.tx
- [X] T037 [US1] Add simple IF command grammar rule (I|IF condition?) in src/m2py/grammar/mumps.tx
- [X] T038 [US1] Add bounded FOR command grammar rule (F|FOR var=start:step:end) in src/m2py/grammar/mumps.tx
- [X] T039 [US1] Add postcondition grammar rule (: condition) in src/m2py/grammar/mumps.tx
- [X] T040 [US1] Add line structure grammar (label, commands, dot blocks) in src/m2py/grammar/mumps.tx

Note: Commands are captured as raw text in the line's "rest" attribute. Command parsing is done in the analysis layer using regex patterns. This approach is simpler and more robust for MVP.

### Statement ASG Mapping for User Story 1

Note: These tasks are REQUIRED per spec acceptance scenarios. The spec explicitly requires:
- "ASG contains statement nodes with correct variable references and literal values" (US1-AC1)
- "ASG contains a FOR node... with start/step/end values and body statements as children" (US1-AC2)

Current status: FOR classification works at line level, statement parsing functions implemented for all core statement types.

- [X] T041 [US1] Implement parse_set_statement() for MSetStatement in src/m2py/analysis/command_parser.py
- [X] T042 [P] [US1] Implement parse_write_statement() and parse_quit_statement() in src/m2py/analysis/command_parser.py
- [X] T043 [US1] Implement parse_if_statement() for MIfStatement with scope in src/m2py/analysis/command_parser.py
- [X] T044 [US1] Implement parse_for_statement() function for MForStatement with MForParameter capture in src/m2py/analysis/command_parser.py
- [X] T045 [US1] Wire parse_for_statement() into parser.classify_patterns() to build MForStatement ASG nodes in src/m2py/parser/parser.py

### Basic FOR Classification for User Story 1

- [X] T046 [US1] Implement classify_for_loops() for BOUNDED type in src/m2py/analysis/command_parser.py
- [X] T047 [US1] Add MUMPSParser.classify_patterns() method calling classifier in src/m2py/parser/parser.py
- [X] T048 [US1] Verify V1FORA.m FOR loops classified as BOUNDED in tests/integration/test_mugj.py

**Checkpoint**: User Story 1 complete - V1FORA.m parses with bounded FOR classification

---

## Phase 4: User Story 2 - Handle Complex FOR Loop Patterns (Priority: P2)

**Goal**: Correctly model FOR loops with multiple forparameters (string lists, mixed patterns, nested loops)

**Independent Test**: Parse V1FORB and V1FORC series files and verify all 5 FOR loop types are correctly classified

### Tests for User Story 2

- [X] T049 [P] [US2] Unit test for string-list FOR (F I="A","B","C") in tests/unit/test_grammar.py
- [X] T050 [P] [US2] Unit test for open-ended FOR (F I=1:1) in tests/unit/test_grammar.py
- [X] T051 [P] [US2] Unit test for mixed FOR (F I="A",1:1:3) in tests/unit/test_grammar.py
- [X] T052 [P] [US2] Unit test for argumentless FOR (F) in tests/unit/test_grammar.py
- [X] T053 [US2] Integration test: parse V1FORB.m with multiple forparameters in tests/integration/test_mugj.py
- [X] T054 [US2] Integration test: parse V1FORC.m with all FOR types in tests/integration/test_mugj.py

### Grammar Extensions for User Story 2

Note: Grammar tasks T055-T058 are addressed via the classifier layer. The textX grammar captures line content as raw text, and the classifier in src/m2py/analysis/command_parser.py handles all FOR patterns.

- [X] T055 [US2] Extend FOR grammar for string-list forparameter (value list) in src/m2py/grammar/mumps.tx
- [X] T056 [US2] Extend FOR grammar for open-ended forparameter (start:step without end) in src/m2py/grammar/mumps.tx
- [X] T057 [US2] Extend FOR grammar for argumentless FOR (no var or params) in src/m2py/grammar/mumps.tx
- [X] T058 [US2] Extend FOR grammar for nested FOR body scope in src/m2py/grammar/mumps.tx

### FOR Classification Complete for User Story 2

Note: T063 is REQUIRED per spec acceptance scenario US2-AC4:
- "ASG contains a FOR node classified as 'open-ended' with the QUIT condition linked as a loop exit point"

- [X] T059 [US2] Extend classify_for_loops() for OPEN_ENDED type in src/m2py/analysis/command_parser.py
- [X] T060 [P] [US2] Extend classify_for_loops() for STRING_LIST type in src/m2py/analysis/command_parser.py
- [X] T061 [P] [US2] Extend classify_for_loops() for MIXED type in src/m2py/analysis/command_parser.py
- [X] T062 [P] [US2] Extend classify_for_loops() for ARGUMENTLESS type in src/m2py/analysis/command_parser.py
- [X] T063 [US2] Identify internal QUIT as loop exit points in parse_for_statement() in src/m2py/analysis/command_parser.py
- [X] T064 [US2] Verify V1FORC series FOR loops have correct types in tests/integration/test_mugj.py

**Checkpoint**: User Story 2 complete - All 5 FOR loop types correctly classified

---

## Phase 5: User Story 3 - Handle GOTO Across Control Boundaries (Priority: P2)

**Goal**: Fully classify GOTO statements by target, control structures exited, and jump direction

**Independent Test**: Parse V1GO1, V1GO2, V1FORC2 and verify all GOTO types classified with exit information

### Tests for User Story 3

- [X] T065 [P] [US3] Unit test for GOTO to local label in tests/unit/test_classifier.py
- [X] T066 [P] [US3] Unit test for GOTO to label+offset in tests/unit/test_classifier.py
- [X] T067 [P] [US3] Unit test for GOTO to external routine (label^routine) in tests/unit/test_classifier.py
- [X] T068 [US3] Integration test: parse V1GO1.m with simple GOTOs in tests/integration/test_mugj.py
- [X] T069 [US3] Integration test: parse V1GO2.m with offset GOTOs in tests/integration/test_mugj.py
- [X] T070 [US3] Integration test: parse V1FORC2.m with nested FOR+GOTO in tests/integration/test_mugj.py

### Grammar Extensions for User Story 3

- [X] T071 [US3] Add GOTO command grammar rule (G|GOTO targets with postconditions) in src/m2py/analysis/command_parser.py
- [X] T072 [US3] Add label reference grammar (name, name+offset, name^routine) in src/m2py/analysis/command_parser.py
- [X] T073 [US3] Implement MGotoStatement ASG element with target list in src/m2py/asg/statements.py (already existed)

### Reference Resolution for User Story 3

- [X] T074 [US3] Implement resolve_references() scanning for MCall objects in src/m2py/analysis/resolver.py
- [X] T075 [US3] Implement label lookup by name in resolve_references() in src/m2py/analysis/resolver.py
- [X] T076 [US3] Populate MCall.target with resolved MLabel in src/m2py/analysis/resolver.py
- [X] T077 [US3] Populate MLabel.callers and MLabel.goto_sources back-references in src/m2py/analysis/resolver.py
- [X] T078 [US3] Add MUMPSParser.resolve_references() method in src/m2py/parser/parser.py
- [X] T079 [US3] Verify V1GO1 GOTO targets resolved in tests/integration/test_mugj.py

### GOTO Classification for User Story 3

- [X] T080 [US3] Implement classify_gotos() for FORWARD_JUMP detection in src/m2py/analysis/goto_analysis.py
- [X] T081 [P] [US3] Extend classify_gotos() for BACKWARD_JUMP detection in src/m2py/analysis/goto_analysis.py
- [X] T082 [P] [US3] Extend classify_gotos() for LOOP_EXIT detection (single FOR) in src/m2py/analysis/goto_analysis.py
- [X] T083 [US3] Extend classify_gotos() for MULTI_LOOP_EXIT detection (nested FORs) in src/m2py/analysis/goto_analysis.py
- [X] T084 [P] [US3] Extend classify_gotos() for CROSS_LABEL detection in src/m2py/analysis/goto_analysis.py
- [X] T085 [P] [US3] Extend classify_gotos() for EXTERNAL detection (^routine) in src/m2py/analysis/goto_analysis.py
- [X] T086 [US3] Populate exits_loops list with enclosing MForStatements in src/m2py/analysis/command_parser.py
- [X] T087 [US3] Verify V1FORC2 GOTO exits nested loops correctly in tests/integration/test_mugj.py

**Checkpoint**: User Story 3 complete - All 6 GOTO types classified with loop exit info ✅

---

## Phase 6: User Story 4 - Variable Scope and Data Flow Analysis (Priority: P3)

**Goal**: Track variable usage across scopes, identify inputs/outputs, respect NEW boundaries

**Independent Test**: Parse a routine with NEW and subroutine calls, verify input/output variable sets

### Tests for User Story 4

- [X] T088 [P] [US4] Unit test for NEW command parsing in tests/unit/test_classifier.py
- [X] T089 [P] [US4] Unit test for exclusive NEW (N (X)) in tests/unit/test_classifier.py
- [X] T090 [P] [US4] Unit test for DO command parsing in tests/unit/test_classifier.py
- [X] T091 [US4] Integration test: parse V1DO1.m with DO commands in tests/integration/test_mugj.py
- [X] T092 [US4] Integration test: parse V1DO2.m with subroutine calls in tests/integration/test_mugj.py

### Grammar Extensions for User Story 4

- [X] T093 [US4] Add parse_new_statement() function in src/m2py/analysis/command_parser.py
- [X] T094 [US4] Add parse_do_statement() function in src/m2py/analysis/command_parser.py
- [X] T095 [US4] Add extract_new_from_line() helper in src/m2py/analysis/command_parser.py
- [X] T096 [US4] Add extract_do_from_line() helper in src/m2py/analysis/command_parser.py
- [X] T097 [US4] Handle argumentless DO in parse_do_statement()

### Variable Analysis for User Story 4

- [X] T098 [US4] Implement analyze_variables() collecting variable reads in src/m2py/analysis/variables.py
- [X] T099 [US4] Extend analyze_variables() collecting variable writes in src/m2py/analysis/variables.py
- [X] T100 [US4] Extend analyze_variables() respecting NEW boundaries in src/m2py/analysis/variables.py
- [X] T101 [US4] Compute input_variables (read before first write) in src/m2py/analysis/variables.py
- [X] T102 [US4] Compute output_variables (written and visible to caller) in src/m2py/analysis/variables.py
- [X] T103 [US4] Implement get_def_use_chains() per FR-051 in src/m2py/analysis/variables.py
- [X] T104 [US4] Implement compute_transitive_inputs() for call chain variable propagation per FR-042 in src/m2py/analysis/variables.py
- [X] T105 [US4] Add MUMPSParser.analyze_variables() method in src/m2py/parser/parser.py
- [X] T106 [US4] Implement detect_unreachable_code() after unconditional GOTO/QUIT per FR-053 in src/m2py/analysis/command_parser.py
- [X] T107 [US4] Verify variable analysis with NEW in tests/integration/test_mugj.py

**Checkpoint**: User Story 4 complete - Variable inputs/outputs computed correctly

---

## Phase 7: Full textX Grammar Refactoring (Architecture Alignment)

**Goal**: Replace regex-based Python parsing with proper textX grammar rules per FR-001 and research.md decisions

**Rationale**: The initial implementation used textX only for line capture, with regex-based parsing in Python. This phase aligned the implementation with the architectural intent by building proper textX grammars.

**Benefits**:
1. **Spec compliance** - FR-001 requires "textX grammar definition" for parsing
2. **Error quality** - textX provides precise line/column in error messages
3. **Source positions** - Automatic _tx_position tracking via textX
4. **Custom classes** - Direct ASG node instantiation from grammar
5. **Maintainability** - Declarative grammar vs. regex parsing functions
6. **RREL** - Label reference resolution via textX's Reference Resolving Expression Language

**Risk Assessment**: All 226 existing tests provide regression safety. Refactor incrementally.

### Phase 7a: Grammar Foundation - Expressions

- [X] T108 Create expression grammar file src/m2py/grammar/expressions.tx with base types
- [X] T109 Add numeric literal grammar (INT, FLOAT, negative numbers) in expressions.tx
- [X] T110 Add string literal grammar (quoted strings with escapes) in expressions.tx
- [X] T111 Add local variable grammar (NAME, subscripted NAME(subscripts)) in expressions.tx
- [X] T112 Add global variable grammar (^NAME, ^NAME(subscripts)) in expressions.tx
- [X] T113 Add naked global grammar (^(subscripts)) in expressions.tx
- [X] T114 Add binary operators grammar (+,-,*,/,\,#,**,=,<,>,',&,!,_,[,],]],?) with L-to-R precedence
- [X] T115 Add unary operators grammar (+,-,') in expressions.tx
- [X] T116 Add parenthesized expression grammar in expressions.tx
- [X] T117 Unit tests for expression parsing (literals, variables, operators) in tests/unit/test_expression_grammar.py

### Phase 7b: Grammar Foundation - Commands

- [X] T118 Add command postcondition grammar (:condition) in commands.tx
- [X] T119 Add argument postcondition grammar (:condition on each arg) in commands.tx
- [X] T120 Add SET command grammar (S|SET assignments with postconditions) in commands.tx
- [X] T121 Add WRITE command grammar (W|WRITE arguments with postconditions) in commands.tx
- [X] T122 Add READ command grammar (R|READ targets with timeout) in commands.tx
- [X] T123 Add QUIT command grammar (Q|QUIT return_value?) in commands.tx
- [X] T124 Add IF command grammar (I|IF condition?) in commands.tx
- [X] T125 Add ELSE command grammar (E|ELSE) in commands.tx
- [X] T126 Add FOR command grammar (F|FOR var=forparams body) with all 5 forparam types in commands.tx
- [X] T127 Add GOTO command grammar (G|GOTO targets with postconditions) in commands.tx
- [X] T128 Add DO command grammar (D|DO targets with postconditions) in commands.tx
- [X] T129 Add NEW command grammar (N|NEW vars, exclusive NEW) in commands.tx
- [X] T130 Add KILL command grammar (K|KILL vars) in commands.tx
- [X] T131 Add remaining commands (BREAK, HALT, HANG, LOCK, MERGE, VIEW, JOB, OPEN, CLOSE, USE, XECUTE) in commands.tx
- [X] T132 Unit tests for command parsing in tests/unit/test_command_grammar.py

### Phase 7c: Special Constructs Grammar

- [X] T133 Add intrinsic function grammar ($fn(args)) for all functions per FR-003 in expressions.tx
- [X] T134 Add special variable grammar ($TEST, $HOROLOG, etc.) per FR-004 in expressions.tx
- [X] T135 Add pattern match grammar (expr?pattern) in expressions.tx
- [X] T136 Add indirection grammar (@expr) for name/subscript/argument indirection in expressions.tx
- [X] T137 Add extrinsic function grammar ($$func^routine(args)) per FR-018 in expressions.tx
- [X] T138 Add extrinsic variable grammar ($$VAR) per FR-019 in expressions.tx
- [X] T139 Unit tests for special constructs in tests/unit/test_special_constructs.py

### Phase 7d: Line/Label Structure

- [X] T140 Refactor line content parsing - created line.tx grammar with LineContent as root
- [X] T141 Add dotted block scope via line.tx LineContent rule (leading whitespace handled)
- [X] T142 Add comment handling (;text) via LineComment rule in line.tx per FR-012
- [X] T143 Handle whitespace sensitivity - line.tx uses skipws=False, explicit /[ \t]*/ matches
- [X] T144 Unit tests for line structure in tests/unit/test_command_parser.py (TestParseLineContent)

### Phase 7e: Custom Class Integration (N/A - Superseded by Semantic Analyzer)

**Status**: N/A - The SemanticAnalyzer approach (Phase 9) superseded direct textX custom class registration. The two-layer CST → SemanticAnalyzer → ASG architecture provides better control over computed fields and semantic analysis.

- [N/A] T145 Register MLiteral, MVariable, MGlobal, MNakedGlobal as textX custom classes
- [N/A] T146 Register MBinaryOp, MUnaryOp as textX custom classes with operator field
- [N/A] T147 Register MSetStatement, MWriteStatement, MReadStatement, MQuitStatement as textX custom classes
- [N/A] T148 Register MIfStatement, MElseStatement, MForStatement as textX custom classes
- [N/A] T149 Register MGotoStatement, MDoStatement, MDoBlockStatement as textX custom classes
- [N/A] T150 Register MNewStatement, MKillStatement as textX custom classes
- [N/A] T151 Register MIntrinsicFunction, MExtrinsicFunction, MSpecialVariable as textX custom classes
- [N/A] T152 Register MPatternMatch, MIndirection as textX custom classes
- [N/A] T153 Implement object processors for computed fields (loop_type, goto_type) if needed
- [N/A] T154 Unit tests verifying custom class instantiation from grammar

### Phase 7f: Parser Refactoring

- [X] T155 Update MUMPSParser to use line.tx grammar via _build_label (loads line_metamodel)
- [X] T156 Enhance _build_label() to parse line content with textX (stores _parsed_commands)
- [X] T157 Remove regex-based parse_*() functions (completed - command_parser.py now uses textX grammar exclusively)
- [X] T158 Update classify_patterns() to work with textX-generated commands (uses extract_for_commands, classify_for_from_textx, parse_for_command_to_asg)
- [X] T159 Update resolve_references() to use textX RREL if applicable (N/A - resolve_references works on ASG nodes; RREL is for textX model references, not needed here)
- [X] T160 Update analyze_variables() to work with textX-generated ASG (already works - operates on ASG nodes; 23 tests passing)
- [X] T161 Verify all existing tests still pass (425 tests passing)
- [X] T162 Integration test: parse all MUGJ files with new grammar (375/376 parsed, 1 empty file skipped)

### Phase 7g: Error Handling Enhancement (N/A - Already Implemented)

**Status**: N/A - Error handling already implemented in parser.py (line 277). textX provides line/column info, and MUMPSSyntaxError wraps TextXSyntaxError. All 376 MUGJ files parse successfully.

- [N/A] T163 Verify textX provides line/column in MUMPSSyntaxError per SC-007
- [N/A] T164 Map textX TextXSyntaxError to MUMPSSyntaxError with full context
- [N/A] T165 Add tests for error message quality (line, column, message)

**Checkpoint**: Grammar refactoring complete - textX grammar replaces regex parsing

---

## Phase 8: Complete ASG Population (Architecture Alignment)

**Goal**: Build fully populated ASG with statements in label bodies, proper expression ASG nodes, and textX custom class integration

**Rationale**: The current implementation parses successfully and classifies patterns, but:
1. `MLabel.body.statements` lists remain empty - parsed commands stored in `_parsed_commands` but not converted to ASG
2. Expressions captured as strings (`_expr_to_string`) rather than full ASG expression trees
3. textX custom classes not registered - manual conversion from textX objects to ASG objects
4. Continuation lines not associated with their parent labels

**Benefits**:
1. `label.body.walk_statements()` returns actual statement objects for traversal
2. Full expression ASG enables semantic analysis without string parsing
3. Custom class registration eliminates manual conversion step
4. Complete ASG ready for code generation phase

### Phase 8a: Statement ASG Population

**Purpose**: Convert `_parsed_commands` into actual `MStatement` objects in `label.body.statements`

- [X] T193 [P8a] Create `_build_statements_from_parsed()` function in src/m2py/parser/parser.py to convert textX commands to ASG
- [X] T194 [P8a] Implement SetCommand → MSetStatement conversion with MAssignment objects
- [X] T195 [P8a] Implement WriteCommand → MWriteStatement conversion with argument list
- [X] T196 [P8a] Implement ReadCommand → MReadStatement conversion with targets and timeouts
- [X] T197 [P8a] Implement QuitCommand → MQuitStatement conversion with return value
- [X] T198 [P8a] Implement IfCommand → MIfStatement conversion with condition expression
- [X] T199 [P8a] Implement ElseCommand → MElseStatement conversion
- [X] T200 [P8a] Implement ForCommand → MForStatement conversion (reuse parse_for_command_to_asg)
- [X] T201 [P8a] Implement GotoCommand → MGotoStatement conversion with MCall targets
- [X] T202 [P8a] Implement DoCommand → MDoStatement conversion with MCall targets and arguments
- [X] T203 [P8a] Implement NewCommand → MNewStatement conversion with variable list
- [X] T204 [P8a] Implement KillCommand → MKillStatement conversion
- [X] T205 [P8a] Implement remaining commands (HANG, HALT, BREAK, LOCK, MERGE, VIEW, XECUTE, JOB, OPEN, CLOSE, USE)
- [X] T206 [P8a] Call `_build_statements_from_parsed()` in `_build_label()` to populate `label.body.statements`
- [X] T207 [P8a] Unit tests verifying `label.body.statements` contains MStatement objects in tests/unit/test_parser.py
- [X] T208 [P8a] Integration test: verify V1FORA.m labels have populated statement bodies

### Phase 8b: Expression ASG Construction

**Purpose**: Replace `_expr_to_string()` with full expression ASG tree construction

- [X] T209 [P8b] Create `_build_expression_asg()` function in src/m2py/analysis/command_parser.py
- [X] T210 [P8b] Convert NumericLiteral → MLiteral with proper LiteralType
- [X] T211 [P8b] Convert StringLiteral → MLiteral with LiteralType.STRING
- [X] T212 [P8b] Convert LocalVariable → MVariable with name and subscripts
- [X] T213 [P8b] Convert GlobalVariable → MGlobal with name and subscripts
- [X] T214 [P8b] Convert NakedGlobal → MNakedGlobal with subscripts
- [X] T215 [P8b] Convert BinaryOp expressions → MBinaryOp with left/right/operator
- [X] T216 [P8b] Convert UnaryOp expressions → MUnaryOp with operand/operator
- [X] T217 [P8b] Convert ParenExpr → recursive expression handling
- [X] T218 [P8b] Convert IntrinsicFunction → MIntrinsicFunction with name and arguments
- [X] T219 [P8b] Convert ExtrinsicFunction → MExtrinsicFunction with label, routine, arguments
- [X] T220 [P8b] Convert SpecialVariable → MSpecialVariable with name
- [X] T221 [P8b] Convert Indirection → MIndirection with expression and subscripts
- [X] T222 [P8b] Update statement converters to use `_build_expression_asg()` instead of `_expr_to_string()`
- [X] T223 [P8b] Unit tests verifying expression ASG structure in tests/unit/test_command_parser.py
- [X] T224 [P8b] Unit tests for complex nested expressions (binary ops, function calls)

### Phase 8c: Continuation Line Handling

**Purpose**: Associate continuation lines (tab/space/dot prefix) with their parent label's body

- [X] T225 [P8c] Track current_label when building routine in `_build_routine()`
- [X] T226 [P8c] Parse ContLine content and add statements to current label's body
- [X] T227 [P8c] Handle dotted block scope (`. S X=1`) - create nested MScope if needed
- [X] T228 [P8c] Unit tests for continuation line statement association
- [X] T229 [P8c] Integration test: V1FORA.m continuation lines included in label bodies

### Phase 8d: Remaining Phase 8 Tasks (Reserved)

**Note**: Phase 8d originally planned textX custom class integration. That work has been moved to Phase 9 for comprehensive implementation with semantic analyzer integration.

- [X] T230 [P8d] Reserved - see Phase 9
- [X] T231 [P8d] Reserved - see Phase 9
- [X] T232 [P8d] Reserved - see Phase 9
- [X] T233 [P8d] Reserved - see Phase 9
- [X] T234 [P8d] Reserved - see Phase 9
- [X] T235 [P8d] Reserved - see Phase 9
- [X] T236 [P8d] Reserved - see Phase 9

### Phase 8e: Variable Analysis Update

**Purpose**: Update variable analysis to work with expression ASG instead of strings

- [X] T237 [P8e] Refactor `_extract_expression_variables()` to traverse MExpr ASG nodes
- [X] T238 [P8e] Handle MVariable, MGlobal nodes for variable extraction
- [X] T239 [P8e] Handle MBinaryOp, MUnaryOp recursively for nested variable references
- [X] T240 [P8e] Handle MIntrinsicFunction arguments for variable extraction
- [X] T241 [P8e] Handle MIndirection flagging for requires_runtime_eval
- [X] T242 [P8e] Update `_extract_statement_variables()` to use new expression traversal
- [X] T243 [P8e] Verify variable analysis tests still pass with expression ASG
- [X] T244 [P8e] Integration test: V1NX1 variable analysis with full expression ASG

### Phase 8f: Validation & Regression Testing

**Purpose**: Ensure complete ASG population doesn't break existing functionality

- [X] T245 [P8f] Run all 425 existing tests - verify none regress (454 passed, 1 skipped)
- [X] T246 [P8f] Add tests for `walk_statements()` returning non-empty iterators
- [X] T247 [P8f] Add tests for expression ASG parent-child relationships
- [X] T248 [P8f] Verify resolver works with fully populated statement bodies
- [X] T249 [P8f] Verify GOTO classification works with new ASG structure
- [X] T250 [P8f] Integration test: parse all MUGJ files and verify statement counts > 0 for non-empty labels
- [X] T251 [P8f] Coverage report: command_parser.py=75%, converters.py=68%, parser.py=84%, overall=75%

**Checkpoint**: Complete ASG population - statements, expressions, and custom classes integrated

---

## Phase 9: textX Custom Class + Semantic Analyzer Integration ✅ COMPLETE

**Goal**: Complete the two-layer CST → Semantic Analyzer → ASG architecture

**Status**: ✅ All Phase 9 tasks complete. The semantic analyzer is now the primary path for command conversion.
Old `converters.py` module was deleted. All 501 tests pass.

### Phase 9a: Complete Custom Class Registration ✅

**Purpose**: Register all expression custom classes with textX metamodel

- [X] T252 [P9a] Add custom classes import to command_parser.py from textx_classes.py
- [X] T253 [P9a] Update `_get_command_metamodel()` to pass `classes=[...]` parameter with expression classes
- [X] T254 [P9a] Update `_get_line_metamodel()` to pass `classes=[...]` parameter
- [X] T255 [P9a] Verify NumericLiteral, StringLiteral instantiate as MLiteral subclasses
- [X] T256 [P9a] Verify LocalVariable instantiates as MVariable
- [X] T257 [P9a] Verify GlobalVariable instantiates as MGlobal
- [X] T258 [P9a] Verify SpecialVariable instantiates as MSpecialVariable
- [X] T259 [P9a] Verify IntrinsicFunction instantiates as MIntrinsicFunction
- [X] T260 [P9a] Unit test: parse "1" returns NumericLiteral (is-a MLiteral) in tests/unit/test_textx_classes.py

### Phase 9b: Grammar Fixes for Custom Class Compatibility ✅

**Purpose**: Ensure grammar rules match custom class constructors

- [X] T261 [P9b] Verify expressions.tx rule names match class names (NumericLiteral, StringLiteral, etc.)
- [X] T262 [P9b] Verify grammar attribute names match __init__ parameters (name, value, subscripts, args)
- [X] T263 [P9b] Fix SpecialVariable vs IntrinsicFunction ordering in PrimaryExpr (SpecialVariable first)
- [X] T264 [P9b] Fix Expr rule to capture binary operations: `left=UnaryExpr (ops+=BinaryOp right+=UnaryExpr)*`
- [X] T265 [P9b] Verify ParenExpr unwrapping works with custom classes
- [X] T266 [P9b] Unit test: parse "$TEST" returns SpecialVariable (not IntrinsicFunction) in tests/unit/test_textx_classes.py
- [X] T267 [P9b] Unit test: parse "1+2" captures binary op structure in tests/unit/test_textx_classes.py

### Phase 9c: Complete Semantic Analyzer ✅

**Purpose**: Finish semantic analyzer to transform CST → clean ASG

- [X] T268 [P9c] Implement `_analyze_Routine()` for MRoutine nodes
- [X] T269 [P9c] Implement `_analyze_Label()` for MLabel nodes with scope tracking
- [X] T270 [P9c] Implement `_analyze_Statement()` dispatcher for all statement types
- [X] T271 [P9c] Complete `_analyze_Expr()` binary operation chain building
- [X] T272 [P9c] Implement `_analyze_ForCommand()` building MForStatement with parameters
- [X] T273 [P9c] Implement `_analyze_SetCommand()` building MSetStatement with assignments
- [X] T274 [P9c] Implement `_analyze_WriteCommand()` building MWriteStatement
- [X] T275 [P9c] Implement `_analyze_GotoCommand()` building MGotoStatement with MCall targets
- [X] T276 [P9c] Implement `_analyze_DoCommand()` building MDoStatement with MCall targets
- [X] T277 [P9c] Implement `_analyze_NewCommand()` building MNewStatement
- [X] T278 [P9c] Add variable tracking during expression analysis
- [X] T279 [P9c] Add scope management (push/pop) for label and FOR bodies
- [X] T280 [P9c] Unit tests for semantic analyzer in tests/unit/test_semantic_analyzer.py

### Phase 9d: Converters Removed ✅

**Status**: ✅ OBSOLETE - `src/m2py/parser/converters.py` (829 lines) was deleted.
All command conversion now goes through `analyze_command()` in `semantic_analyzer.py`.

- [X] T281 [P9d] ~~Update `_convert_expr()`~~ → DELETED with converters.py
- [X] T282 [P9d] ~~Update `_convert_full_expr()`~~ → DELETED with converters.py
- [X] T283 [P9d] ~~Update `_convert_for_param()`~~ → Handled by semantic analyzer
- [X] T284 [P9d] ~~Update `parse_for_statement()`~~ → Uses command_parser.py utilities
- [X] T285 [P9d] ~~Update `parse_set_statement()`~~ → Uses command_parser.py utilities
- [X] T286 [P9d] ~~Update `parse_write_statement()`~~ → Uses command_parser.py utilities
- [X] T287 [P9d] ~~Update `parse_goto_statement()`~~ → Uses command_parser.py utilities
- [X] T288 [P9d] Unit tests now use semantic analyzer in tests/unit/test_converters.py

### Phase 9e: Update Tests for ASG Objects

**Purpose**: Fix failing tests that assert against string values instead of ASG objects

**Note**: The root cause was `_expr_to_string()` not handling the new grammar structure with `left`/`ops`/`right`.
Fixed by updating `_expr_to_string()` to properly traverse the new Expr structure. All 12 tests now pass.

- [X] T289 [P9e] Fix test_parse_bounded_for: Fixed via `_expr_to_string()` update
- [X] T290 [P9e] Fix test_parse_open_ended_for: Fixed via `_expr_to_string()` update
- [X] T291 [P9e] Fix test_parse_mixed_for: Fixed via `_expr_to_string()` update
- [X] T292 [P9e] Fix test_parse_for_decimal_step: Fixed via `_expr_to_string()` update
- [X] T293 [P9e] Fix test_parse_for_negative_values: Fixed via `_expr_to_string()` update
- [X] T294 [P9e] Fix test_parse_for_multiple_ranges: Fixed via `_expr_to_string()` update
- [X] T295 [P9e] Fix test_parse_simple_set: Fixed via `_expr_to_string()` update
- [X] T296 [P9e] Fix test_parse_write_tab: Fixed via `_expr_to_string()` update
- [X] T297 [P9e] Fix test_parse_goto_label_offset: Fixed via `_expr_to_string()` update
- [X] T298 [P9e] Fix test_bounded_for_asg (test_command_parser.py): Fixed via `_expr_to_string()` update
- [X] T299 [P9e] Fix test_classify_patterns_mforstatement_has_parameters (test_parser.py): Fixed via `_expr_to_string()` update
- [X] T300 [P9e] Fix test_classify_patterns_mforstatement_multiple_params (test_parser.py): Fixed via `_expr_to_string()` update

### Phase 9f: Add Helper Functions for Test Assertions

**Purpose**: Create utilities for easier ASG value assertions

**Status**: N/A - Existing APIs work correctly. These helpers can be added in code generation phase if needed.

- [N/A] T301 [P9f] Create `get_literal_value(expr)` helper: extracts value from MLiteral or returns string
- [N/A] T302 [P9f] Create `assert_literal_equals(expr, expected)` helper for test assertions
- [N/A] T303 [P9f] Update test docstrings to document MLiteral vs string value expectations
- [N/A] T304 [P9f] Add type hints to MForParameter for start/step/end/value as Optional[MExpr]

### Phase 9g: Integration Testing and Validation

**Purpose**: Validate the complete CST → Semantic Analyzer → ASG pipeline

- [X] T305 [P9g] Run all 456 tests - verify all pass (0 failures) - 475 passed, 1 skipped
- [X] T306 [P9g] Integration test: parse V1FORA.m and verify MForParameter fields are MExpr - Added test_v1fora1_for_parameter_fields_are_mexpr
- [X] T307 [P9g] Integration test: parse V1GO1.m and verify GOTO targets parse correctly - Added test_v1go1_goto_targets_parse_correctly
- [X] T308 [P9g] Integration test: verify expression parent relationships are set correctly - Added test_expression_parent_relationships
- [X] T309 [P9g] Performance test: ensure parse time hasn't regressed significantly - Added test_parse_performance_acceptable
- [X] T310 [P9g] Add test for binary operation chain: "1+2*3" produces correct structure - Added test_binary_operation_chain_in_for_expr
- [X] T311 [P9g] Add test for nested function call: "$P($G(X),",",1)" produces correct ASG - Added test_nested_function_call_parsing

### Phase 9h: Documentation and Cleanup

**Purpose**: Update documentation and remove deprecated code

- [X] T312 [P9h] Update quickstart.md with new architecture diagram - Added Architecture Overview section
- [X] T313 [P9h] Add docstrings to semantic_analyzer.py explaining the two-layer approach - Already documented
 - [X] T314 [P9h] Remove deprecated/unused analysis APIs or mark with deprecation warnings - Pruned unused SET/QUIT/IF extraction functions (kept stubbed for compatibility)
- [X] T315 [P9h] Update data-model.md to show MLiteral/MVariable inheritance from custom classes - Added Two-Layer Architecture section
- [X] T316 [P9h] Add inline comments in textx_classes.py explaining textX constructor requirements - Already documented

**Checkpoint**: Phase 9 complete - CST → Semantic Analyzer → ASG architecture fully implemented

---

## Phase 10: User Story 5 - Parse Special MUMPS Features (Priority: P3) ✅ COMPLETE

**Goal**: Verify special MUMPS features work with refactored textX grammar

**Note**: Most grammar work now done in Phase 7. This phase validates integration.

### Tests for User Story 5

- [X] T317 [P] [US5] Unit test for pattern match expression (X?1A.N) in tests/unit/test_grammar.py
- [X] T318 [P] [US5] Unit test for $PIECE intrinsic function in tests/unit/test_grammar.py
- [X] T319 [P] [US5] Unit test for $SELECT intrinsic function in tests/unit/test_grammar.py
- [X] T320 [P] [US5] Unit test for $TEST special variable in tests/unit/test_grammar.py
- [X] T321 [P] [US5] Unit test for indirection (@variable) in tests/unit/test_grammar.py
- [X] T322 [US5] Integration test: parse V1PAT.m with patterns in tests/integration/test_mugj.py
- [X] T323 [US5] Integration test: parse V1FN* files with functions in tests/integration/test_mugj.py

### Validation for User Story 5

- [X] T324 [US5] Verify MPatternMatch nodes have correct pattern structure (parsed as MBinaryOp with '?' operator)
- [X] T325 [US5] Verify MIntrinsicFunction nodes have all arguments
- [X] T326 [US5] Verify MExtrinsicFunction nodes link to routine references
- [X] T327 [US5] Verify MIndirection nodes flag requires_runtime_eval
- [X] T328 [US5] Verify MSpecialVariable nodes identify $TEST references

**Checkpoint**: User Story 5 complete - All special MUMPS features represented in ASG

---

## Phase 11: Polish & Cross-Cutting Concerns ✅ COMPLETE

**Purpose**: Full MUGJ validation, performance, and cleanup

### Full MUGJ Validation (SC-001)

- [X] T329 Add MUGJ parse loop test for all ~280 files in tests/integration/test_mugj.py
- [X] T330 Create list of files failing parse for triage in tests/integration/test_mugj.py
- [X] T331 Fix failing MUGJ files iteratively until 100% parse rate
- [X] T332 Verify SC-001: 100% MUGJ parse rate in tests/integration/test_mugj.py

### Performance Validation (SC-005)

- [X] T333 Add benchmark test for 500-line routine parse time in tests/unit/test_parser.py
- [X] T334 Verify SC-005: parse time <2s for 500 lines
- [X] T335 Profile and optimize grammar if needed (not needed - performance acceptable)

### Error Handling (SC-007)

- [X] T336 Verify MUMPSSyntaxError includes line/column in tests/unit/test_parser.py
- [X] T337 Add source position propagation to all ASG elements (via ASGElement base class)

### Serialization & Debugging

- [X] T338 Implement to_dict() serialization for ASG per data-model.md in src/m2py/asg/elements.py
- [X] T339 Add ASG JSON dump for debugging in src/m2py/parser/parser.py

### Documentation

- [X] T340 [P] Update README.md with parser usage examples
- [X] T341 [P] Add inline docstrings to all public API methods (already documented)
- [X] T342 Run quickstart.md validation steps to ensure setup works

**Checkpoint**: Phase 11 complete - Full MUGJ validation, performance, and documentation

---

## Phase 12: Code Generation Readiness ✅ COMPLETE

**Purpose**: Address ASG structure issues discovered during MUGJ validation to prepare for Python code generation.

**Context**: During Phase 11 validation, we discovered that control flow bodies (FOR, IF, ELSE, DO) were not being properly populated. Commands following control flow statements on the same line were siblings in the parent scope rather than children in the control flow body. This phase fixes those structural issues.

### 12a: Control Flow Body Population (CRITICAL)

- [X] T343 [US6] Implement FOR body population - commands following FOR on same line go in body
- [X] T344 [US6] Implement IF then_scope population - commands following IF on same line
- [X] T345 [US6] Implement ELSE body population - commands following ELSE on same line
- [X] T346 [US6] Implement DO block body population - dot-indented lines go in body
- [X] T347 [US6] Add unit tests for FOR body population
- [X] T348 [US6] Add unit tests for IF/ELSE body population
- [X] T349 [US6] Add unit tests for DO block body population
- [X] T350 [US6] Integration test: V1FORA1.m FOR bodies populated correctly
- [X] T351 [US6] Integration test: V1IE1.m IF bodies populated correctly
- [X] T352 [US6] Integration test: V1DO1.m DO block bodies populated correctly

### 12b: Nested Control Flow (HIGH)

- [X] T353 [US6] Handle nested FOR loops - inner FOR is in outer FOR body
- [X] T354 [US6] Handle FOR with nested IF - IF is in FOR body
- [X] T355 [US6] Handle IF with nested FOR - FOR is in IF body
- [X] T356 [US6] Integration test: V1FORC2.m nested FOR structure correct

### 12c: Command Association (MEDIUM)

- [X] T357 [US6] Verify postconditions are on correct statements
- [X] T358 [US6] Add test for postcondition association
- [X] T359 [US6] Verify indirection produces MIndirection nodes
- [X] T360 [US6] Add test for indirection expression structure

### 12d: Pattern Match Complete (MEDIUM)

- [X] T361 [US6] Verify pattern match captures all pattern segments
- [X] T362 [US6] Add test for complex pattern match ASG structure
- [X] T363 [US6] Verify pattern alternation (!) captured

### 12e: Full MUGJ Validation (VALIDATION)

- [X] T364 [US6] Run all V1FOR* tests and verify FOR bodies populated
- [X] T365 [US6] Run all V1IE* tests and verify IF/ELSE bodies populated
- [X] T366 [US6] Run all V1DO* tests and verify DO bodies populated
- [X] T367 [US6] Run all V1PAT* tests and verify pattern structures
- [X] T368 [US6] Run all V1IND* tests and verify indirection structures (covered in V1PCA.m)
- [X] T369 [US6] Create MUGJ validation report with pass/fail for each file

**Checkpoint**: Phase 12 complete - ASG structure ready for code generation (576 tests passing)

---

## Phase 13: ASG Refinement Based on MUGJ Validation ✅ COMPLETE

**Purpose**: Fix semantic representation issues discovered during systematic MUGJ validation to ensure Python code generation readiness.

**Context**: After Phase 12, we systematically validated all 376 MUGJ test files. All files parse successfully (100% parse rate), and all identified semantic representation issues have been resolved.

**Validation Results**: ✅ 376/376 files parse | ✅ All 7 issue categories resolved | ✅ 33 tasks complete

### 13a: External Routine Call Representation (HIGH PRIORITY) ✅ COMPLETE

**Issue**: External calls like `D ^ROUTINE` incorrectly set `MCall.name=None` instead of `""` (empty string for entry point). Affects 183 files (~49% of test suite).

- [X] T370 [US6] Fix MCall.name for external routine calls to use "" instead of None
- [X] T371 [US6] Update extract_do_from_line() to set name="" for ^ROUTINE syntax in src/m2py/analysis/command_parser.py
- [X] T372 [US6] Update extract_goto_from_line() similarly in src/m2py/analysis/command_parser.py
- [X] T373 [US6] Add validation test to ensure external calls have name="" not None in tests/unit/test_parser.py
- [X] T374 [US6] Verify all 183 affected files now have correct MCall.name in tests/integration/test_mugj.py

### 13b: Multi-Command Line Validation (MEDIUM PRIORITY) ✅ COMPLETE

**Issue**: Verify Phase 12 work is complete - multi-command lines with postconditions handled correctly.

- [X] T395 [US6] Validate multi-command lines parse correctly (SET X=1 DO L IF Y QUIT)
- [X] T396 [US6] Verify postconditions associated with correct commands (SET:X Y=1 WRITE:Y !)
- [X] T397 [US6] Test nested control flow (FOR with IF with DO) in tests/unit/test_parser.py
- [X] T398 [US6] Ensure statement order preserved in ASG

### 13c: Function Call vs Command Ambiguity (MEDIUM PRIORITY) ✅ COMPLETE

**Issue**: Verify parser correctly distinguishes intrinsic functions (in expressions) from commands.

- [X] T375 [US6] Analyze V1FC.m, V1FC1.m, V1FC2.m for function call patterns
- [X] T376 [US6] Verify MIntrinsicFunction captured correctly in expression context
- [X] T377 [US6] Verify extrinsic function $$LABEL^ROUTINE syntax captured
- [X] T378 [US6] Document any function/command ambiguity issues found

### 13d: Pattern Match Validation (MEDIUM PRIORITY) ✅ COMPLETE

**Issue**: Validate pattern match ASG structure for Python code generation readiness.

- [X] T379 [US6] Read V1PAT1.m source and examine pattern syntax variations
- [X] T380 [US6] Parse V1PAT1.m and validate MPatternMatch structure in ASG
- [X] T381 [US6] Verify pattern atoms captured (A=alpha, N=numeric, E=everything, P=punctuation)
- [X] T382 [US6] Verify pattern counts captured (1N, 3A, 1.2N range syntax)
- [X] T383 [US6] Document pattern match ASG structure for code generation

### 13e: Special Variable Handling (MEDIUM PRIORITY) ✅ COMPLETE

**Issue**: Validate special variables like $HOROLOG, $STORAGE, $IO are properly captured.

- [X] T384 [US6] Read V1SVH.m and V1SVS.m for special variable usage patterns
- [X] T385 [US6] Validate MSpecialVariable ASG structure
- [X] T386 [US6] Check special variable subscripts handled ($IO(device))
- [X] T387 [US6] Document all special variables found in MUGJ test suite
- [X] T388 [US6] Create mapping of MUMPS special vars to Python equivalents

### 13f: Indirection Completeness (LOW PRIORITY) ✅ COMPLETE

**Issue**: Validate all forms of indirection operator @ are properly captured.

- [X] T389 [US6] Survey all V1ID*.m files (IDARG, IDDO, IDGO, IDNM) for indirection patterns
- [X] T390 [US6] Validate MIndirection captured in argument position (DO LABEL(@X))
- [X] T391 [US6] Validate MIndirection captured in name position (SET @X=1)
- [X] T392 [US6] Validate MIndirection captured in pattern position (IF X?@PAT)
- [X] T393 [US6] Validate command/GOTO indirection (DO @LABEL, GOTO @DEST)
- [X] T394 [US6] Document which indirection forms are fully supported

### 13g: Numeric Literal Edge Cases (LOW PRIORITY) ✅ COMPLETE

**Issue**: Validate numeric literal parsing for MUMPS-specific rules.

- [X] T399 [US6] Validate numeric literal parsing in V1NUM*.m files
- [X] T400 [US6] Check scientific notation handling (1E2, 1.5E-3)
- [X] T401 [US6] Verify sign handling (unary + and -)
- [X] T402 [US6] Document numeric edge cases for Python generation

**Checkpoint**: Phase 13 complete - ASG semantically accurate, Python code generation ready

---

## Phase 14: MUGJ Validation Round 2 - Command Grammar Fixes ✅ COMPLETE

**Purpose**: Fix command parsing issues discovered during systematic MUGJ file-by-file validation (Checklist 1: INSTRUCT.m - V0.m).

**Context**: Phase 13 validated 376/376 files parse, but detailed file-by-file review revealed commands being silently dropped when grammar doesn't match. Parsing "succeeds" but statements are missing from ASG.

**Discovery Date**: 2025-12-20 (Checklist 1 of 54)
**Completion Date**: 2025-12-20

### 14a: READ Command Format Control ✅ COMPLETE

**Issue**: READ command grammar fails when format controls (`!`, `?n`, `#`) or prompts appear without a following target variable.

**Root Cause**: `ReadArg` grammar required `target=ReadTarget` but MUMPS allows format-only arguments.

**Solution**: Restructured `ReadArg` in `src/m2py/grammar/commands.tx` to allow format-only, prompt-only, or target with optional timeout as separate alternatives.

- [X] T403 [US6] Fix ReadArg grammar to make target optional - format/prompt can stand alone
- [X] T404 [US6] Fix Tab handling in ReadFormat - Tab correctly uses `?` + Expr
- [X] T405 [US6] Add unit tests for READ format control variations in tests/unit/test_grammar.py (TestReadFormatControlGrammar class, 6 tests)
- [X] T406 [US6] Verify MAIN.m line 4 parses correctly with READ and QUIT statements

### 14b: OPEN Command Device Parameters ✅ COMPLETE

**Issue**: OPEN command grammar fails when device parameters are present.

**Root Cause**: OpenCommand grammar only accepted simple expression, not timeout or parameter syntax.

**Solution**: Added `OpenArg` rule with support for `:timeout`, `:(params)`, and `:(params):timeout` syntax in `src/m2py/grammar/commands.tx`.

- [X] T407 [US6] Extend OpenCommand grammar to support `:timeout` syntax
- [X] T408 [US6] Extend OpenCommand grammar to support `:(param:param:...)` syntax
- [X] T409 [US6] Add unit tests for OPEN device parameters in tests/unit/test_grammar.py (TestOpenDeviceParametersGrammar class, 5 tests)
- [X] T410 [US6] Verify RESTORE.m OPEN statement captured in ASG

### 14c: Continuation Line Association ✅ COMPLETE

**Issue**: Continuation lines 5-7 in MAIN.m weren't being parsed due to expression grammar issues.

**Root Cause**: Two issues discovered during debugging:
1. `'[` (not-contains) operator missing from BinaryOp regex in `src/m2py/grammar/expressions.tx`
2. DO with indirection (`D @VAR` or `D @(expr)`) not supported in DoTarget grammar

**Solution**: 
- Added `'\[` to BinaryOp regex pattern
- Added `DoIndirect` rule for DO command indirection support

- [X] T411 [US6] Debug continuation line parsing for MAIN.m - traced textX parse output
- [X] T412 [US6] Fixed 'not contains' operator `'[` in expressions.tx
- [X] T413 [US6] Added DoIndirect rule for DO @VAR and DO @(expr) in commands.tx

### 14d: Validation Script Attribute Errors ✅ COMPLETE

**Issue**: utils/validate_asg.py had attribute name mismatches.

- [X] T414 [US6] Fix validate_asg.py formal_params → formal_list
- [X] T415 [US6] Fix validate_asg.py MCall.label → MCall.name

**Checkpoint**: Phase 14 complete - 602 tests passing, MAIN.m and RESTORE.m fully parse

### 14d: Validation Script Attribute Errors (FIXED)

**Issue**: utils/validate_asg.py had attribute name mismatches causing crashes:
- `formal_params` should be `formal_list`
- `label` attribute on MCall should be `name`

**Status**: ✅ Fixed during this validation session

- [X] T414 [US6] Fix validate_asg.py formal_params → formal_list
- [X] T415 [US6] Fix validate_asg.py MCall.label → MCall.name

**Checkpoint**: Phase 14 addresses command parsing gaps for code generation readiness

---

## Phase 15: MUGJ Validation Checklist - INSTRUCT to V0 ✅ COMPLETE

**Purpose**: Capture remaining ASG correctness gaps found while validating INSTRUCT.m, MAIN.m, OVERVIEW.m, PROC.m, RESTORE.m, V.m, and V0.m for code generation readiness.

**Completion Date**: 2025-12-20

### 15a: Commands After IF Are Silently Dropped (CRITICAL) ✅ FIXED

**Issue**: Commands following IF on the same line are completely missing from ASG, not just misplaced. This loses control flow logic entirely.

**Evidence**:
- INSTRUCT.m line 31: `I IO="PRINTER" W #` → MIf captured, but `W #` **dropped**
- RESTORE.m line 8: `I %TP="" G DONE` → MIf captured, but `G DONE` **dropped**
- RESTORE.m line 18: `I %TP="END ROUTINES" Q` → MIf captured, but `Q` **dropped**

**Root Cause Analysis**: Investigation revealed the ASG WAS actually capturing IF body contents correctly. The issue was the validate_asg.py display tool wasn't showing nested then_scope contents.

**Resolution**: Updated validate_asg.py to recursively display nested control flow bodies.

- [X] T416 [US6] Verified IF same-line command capture already working correctly
- [X] T417 [US6] Updated validate_asg.py to show nested then_scope contents
- [X] T418 [US6] Verified INSTRUCT.m line 31 `W #` captured in IF body
- [X] T419 [US6] Verified RESTORE.m line 8 `G DONE` captured in IF body
- [X] T420 [US6] Verified RESTORE.m line 18 `Q` captured in IF body

### 15b: Commands After KILL Are Dropped ✅ FIXED

**Issue**: Line 26 in RESTORE.m is `K  Q` (KILL then QUIT), but ASG only shows MKill.

**Root Cause**: KILL grammar `WS?` consumed all whitespace, treating `Q` as kill target instead of QUIT command.

**Resolution**: Fixed KillCommand grammar in commands.tx to require single space before arguments: `' ' (exclusive=ExclusiveKill | vars+=KillTarget[/,/])?`

- [X] T421 [US6] Fixed multi-command line parsing when KILL is first command
- [X] T422 [US6] Verified RESTORE.m DONE label has MKill (no targets) and MQuit

### 15c: DO Indirection Target Empty ✅ FIXED

**Issue**: MAIN.m line 6 `D @($P($T(tab+ans),";",2))` shows as `MDo → CALL() body=0stmts` with empty target.

**Root Cause**: `_analyze_DoCommand` in semantic_analyzer.py only checked `target.label`, not `target.indirect`.

**Resolution**: 
1. Added handling for `target.indirect` in `_analyze_DoCommand`
2. Added `indirection` field to MCall dataclass

- [X] T423 [US6] Fixed DO indirection - now captures MIndirection as call.indirection
- [X] T424 [US6] Added test coverage for `D @(expr)` producing proper MCall with indirection

### 15d: Kill-All Semantics ✅ FIXED

**Issue**: RESTORE.m line 26 `K  Q` - the `K` with no arguments should kill all locals, but shows `MKill → LocalVar(Q)`.

**Resolution**: Same fix as 15b - grammar now correctly separates KILL (no args) from QUIT command.

- [X] T425 [US6] Verified KILL without arguments produces MKillStatement with empty targets list

**Checkpoint**: Phase 15 complete - INSTRUCT.m, MAIN.m, OVERVIEW.m, PROC.m, RESTORE.m, V.m, V0.m all validated

### Phase 15e: READ Command Full Argument Capture ✅ FIXED

**Purpose**: Address additional issues found during re-validation of INSTRUCT.m to V0.m.

- [X] T426 [MAIN.m] Fix `READ` command parsing to capture prompts and format controls (e.g., `R !,?10,"Prompt",ans,!`).

**Root Cause**: `_analyze_ReadCommand` in semantic_analyzer.py only captured `target` arguments, skipping format controls and prompts.

**Resolution**: Updated `_analyze_ReadCommand` to also capture:
- Format controls (!, #, ?n) via `arg.format`
- Prompts ("string") via `arg.prompt`

- [X] T427 [RESTORE.m] Validate `XECUTE` and `Z-commands` - XECUTE correctly captures code as string literals. Z-commands (ZREMOVE, ZINSERT, ZSAVE) are implementation-specific and only appear inside XECUTE strings, which is correct behavior for static transpilation.

**Checkpoint**: Phase 15e complete - READ arguments fully captured (602 tests passing)

---

### Phase 15f: Leading Decimal Number Fix ✅ FIXED

**Purpose**: Fix parsing of MUMPS numbers that start with a decimal point (e.g., `.5`, `.00E3`).

- [X] T428 [V1AC2.m] Fix NUMBER regex in expressions.tx to allow leading decimal point.

**Issue Found During Validation**: V1AC2.m label 13 only had 1 statement instead of 3. The continuation line `S ITEM="I-13  ",VCOMP=$A(.00E3),VCORR=48 D EXAMINER` was failing to parse.

**Root Cause**: NUMBER regex `/[0-9]+(\.[0-9]+)?([Ee][+-]?[0-9]+)?/` required at least one digit before the decimal point.

**Resolution**: Updated NUMBER regex to `/([0-9]+\.?[0-9]*|\.[0-9]+)([Ee][+-]?[0-9]+)?/` which allows:
- Standard integers and decimals: `5`, `5.`, `5.5`, `5.5E3`
- Leading decimal without integer part: `.5`, `.00`, `.00E3`

**Checkpoint**: Phase 15f complete - Leading decimal numbers parse correctly (602 tests passing)

---

## Phase 16: MUGJ Validation Checklist - V000006 to V1AC2 ✅ COMPLETE

**Purpose**: Capture ASG correctness gaps found while validating V000006.m through V1AC2.m (Checklist 2/54).

**Findings**:
- ~~Argumentless DO blocks are not associated with their dot-indented bodies; V1AC.m `if unix do` loses the inline SET/XECUTE block (statements become top-level instead of inside the DO scope).~~ **FIXED**
- WRITE format controls (`!`, `#`, etc.) remain as textX `Newline`/`Form` tokens rather than ASG expressions. This is cosmetic - the tokens contain usable `val` attributes for code generation.

- [X] T429 Fix argumentless DO block handling so dot-indented bodies attach to the DO inside nested control flow. Fixed `_structure_do_blocks()` to search for argumentless DO in nested scopes (then_scope, else_scope, body). V1AC.m now correctly has SET/XECUTE in the DO body inside the IF.
- [N/A] T430 WRITE format controls: NOT A BLOCKER. The textX `Newline`/`FormFeed`/`Tab` objects contain `val` attribute with the format character, usable for code generation. Converting to ASG types would be cosmetic consistency only.
- [X] T431 Add regression coverage for V1AC.m in `tests/integration/test_mugj.py` to assert DO block scoping is correct.

---

## Phase 17: MUGJ Validation Checklist - V1BOA to V1BOA6

**Purpose**: Capture ASG correctness gaps found while validating V1BOA.m through V1BOA6.m (Checklist 3/54).

**Findings**:
- DO calls were unresolved in validation output because `utils/validate_asg.py` only invoked `parse_file` and skipped `resolve_references()`, leaving `MCall.target`/`call_type` unset and `MLabel.callers` empty (blocks call-chain based variable analysis for codegen).

- [X] T432 [VALIDATION] Run reference resolution inside `utils/validate_asg.py` (call `parser.resolve_references` after `parse_file`) so local DO/GOTO targets populate `MCall.target`, `call_type`, and `MLabel.callers` in validation dumps.
- [X] T433 [VALIDATION] Add regression check that V1BOA1 EXAMINER DO calls report `is_resolved=True` and `call_type=LABEL_CALL` (unit test `tests/unit/test_resolver_call_types.py`).

---

## Phase 18: MUGJ Validation Checklist - V1BOB to V1BOB5A

**Purpose**: Capture ASG correctness gaps found while validating V1BOB.m through V1BOB5A.m (Checklist 4/54).

**Findings**:
- V1BOB10.m tested the `']` (not follows) operator which was missing from the expression grammar, causing lines containing this operator to fail parsing silently. This resulted in only 23 statements captured instead of 125.

- [X] T434 [BUG FIX] Add missing `']` (not follows) operator to BinaryOp grammar in `src/m2py/grammar/expressions.tx`. Changed pattern from `'\[|]]|>\[|\[|\]` to `'\[|'\]|]]|\[|\]` to include the `'\]` operator.
- [X] T435 [VALIDATION] Verify V1BOB10.m parses correctly with 125 statements after grammar fix (was 23 before fix).

---

## Phase 19: MUGJ Validation Checklist - V1BOC1 to V1CALL1 ✅ COMPLETE

**Purpose**: Capture ASG correctness gaps found while validating V1BOC1.m through V1CALL1.m (Checklist 6/54).

**Completion Date**: 2024-12-20

**Findings**:
- V1BOC1.m, V1BOC2.m, V1BOC3.m, V1BR1.m, V1CALL.m parse correctly with expected labels/statements
- ~~V1BR.m line 37 completely missing from ASG due to IF multi-condition parsing failure~~ **FIXED**
- ~~V1CALL1.m has SET after QUIT parsed as VIEW due to command boundary ambiguity~~ **FIXED**

### 19a: IF Command Grammar - Multiple Conditions ✅ FIXED

**Issue**: IF command grammar doesn't support comma-separated conditions.

**Root Cause**: `IfCommand` grammar only accepts single `condition=Expr`, but MUMPS allows comma-separated conditions acting as AND.

**Solution**: Changed IfCommand grammar to `conditions+=Expr[/,/]` and updated MIfStatement to have both `condition` (single) and `conditions` (list) for backwards compatibility.

**Reference**: mumps-reference/1977__a108035.md states "IF with n arguments is equivalent in execution to n IFs, each with one argument."

- [X] T436 [BUG FIX] Change IfCommand grammar from `condition=Expr` to `conditions+=Expr[/,/]` in `src/m2py/grammar/commands.tx`
- [X] T437 [BUG FIX] Update `_analyze_IfCommand` in `src/m2py/analysis/semantic_analyzer.py` to handle list of conditions
- [X] T438 [VALIDATION] Verify V1BR.m line 37 parses with FOR, IF (with 2 conditions), SET, BREAK, SET commands
- [X] T439 [TEST] Add unit test for IF with multiple comma-separated conditions (`tests/unit/test_if_comma_conditions.py`)

### 19b: QUIT Value vs Next Command Ambiguity ✅ FIXED

**Issue**: `Q S X=1` fails because QUIT tries to parse `S X=1` as return value.

**Root Cause**: QuitCommand grammar `(WS value=Expr)?` greedily matches any expression after whitespace, but MUMPS uses context to distinguish `Q X` (QUIT with value X) from `Q  S X=1` (QUIT then SET).

**Solution**: Added `CommandWithArg` rule for negative lookahead in QuitCommand. The pattern `!CommandWithArg` prevents QUIT from matching command keywords followed by argument patterns.

- [X] T440 [BUG FIX] Add negative lookahead `!CommandWithArg` in QuitCommand to prevent matching command keywords as return value
- [X] T441 [VALIDATION] Verify V1CALL1.m line 3 parses as SET, QUIT, SET (not SET, QUIT, VIEW)
- [X] T442 [TEST] Add unit test for QUIT followed by SET on same line (`tests/unit/test_quit_then_command.py`)

**Checkpoint**: Phase 19 complete - all 7 files in checklist 6/54 now parse correctly (619 tests passing)

---

## Phase 20: MUGJ Validation Checklist - V1BOC1 to V1CALL1 (Revisit)

**Purpose**: New gaps found while re-validating checklist 6/54 (V1BOC1.m through V1CALL1.m) for ASG completeness and call capture.

**Findings**:
- V1BOC1.m and V1BOC2.m: labels 145-149 and 155-159 only capture the leading `W` statements; the `S` assignments and `D EXAMINER` calls on subsequent lines are dropped, so the test bodies are missing.
- V1CALL.m: DO call lists are dropped when followed by trailing commands on the same label (e.g., label 172 `DO 1^V1CALL1,2^V1CALL1,IF^V1CALL1` is missing entirely; labels 178-185 likewise lose their DO targets, leaving only the final `D EXAMINER`).
- V1CALL.m: DO call targets that remain are marked `CallType.UNRESOLVED` even when the routine is known (e.g., `D V1CALL1+7-11+12^V1CALL1`).

- [X] T443 [BUG] **VERIFIED FIXED 2025-12-24** Preserve all commands after numeric labels in V1BOC1/2 (labels 145-149, 155-159): ensure `_structure_lines`/command parsing emits the `S`/`D EXAMINER` statements that follow the initial `W` line. Add regression coverage in `tests/integration/test_mugj.py` for these labels.
- [X] T444 [BUG] **VERIFIED FIXED 2025-12-24** Capture DO call lists before trailing commands (V1CALL label 172, 178-185): fix DO parsing to emit the full target list (`MCall` entries) even when another command follows on the same line/label.
- [X] T445 [VALIDATION] **VERIFIED 2025-12-24** Add integration assertions for V1CALL.m to check DO targets: label 172 should contain a DO statement with three targets (1^V1CALL1, 2^V1CALL1, IF^V1CALL1) plus the trailing `D EXAMINER`; labels 178-185 should each retain their label+offset DO calls.
- [X] T446 [BUG] Set correct `call_type`/resolution for DO label+offset ^routine calls (e.g., `V1CALL1+7-11+12^V1CALL1` should classify as `ROUTINE_CALL` with `offset` captured, not `UNRESOLVED`). **Fixed**: Created `OffsetExpr` grammar rules that exclude `GlobalVariable` to prevent `^routine` from being consumed as a global variable. Updated semantic analyzer to handle chained binary operators with +/- that textX misparsed as unary operators.

---

## Phase 21: MUGJ Validation Checklist - V1BOC1 to V1CALL1

**Purpose**: Systematic validation of MUGJ test files V1BOC1 through V1CALL1.

- [X] T447 [VALIDATION] V1BOC1.m - Label test
- [X] T448 [VALIDATION] V1BOC2.m - Label test
- [X] T449 [VALIDATION] V1BOC3.m - Label test
- [X] T450 [VALIDATION] V1BR.m - Label test
- [X] T451 [VALIDATION] V1BR1.m - Label test
- [X] T452 [VALIDATION] V1CALL.m - Label test (Confirmed BUG T446)
- [X] T453 [VALIDATION] V1CALL1.m - Label test

---

## Phase 22: MUGJ Validation Checklist - V1CMT to V1DLB ✅ COMPLETE

**Purpose**: Validate V1CMT.m through V1DLB.m (Checklist 7/54).

**Validation Date**: 2024-12-20

**Initial Concerns (Investigated and Resolved)**:
- ~~`K (vars)` treated as empty-target `MKillStatement`~~ **NOT A BUG**: Verified V1DGA label 198 correctly produces `exclusive=True` with `except_list=['PASS','FAIL','X','Y','Z','V1A','V1B']`.
- ~~Argumentless `K` indistinguishable from no-op~~ **NOT A BUG**: Verified V1DGA label 199 produces `exclusive=False, targets=[]` which IS distinguishable from Selective Kill (`targets` non-empty) and Exclusive Kill (`exclusive=True`).

**KILL Command Semantics (Already Correct)**:
The three KILL forms per MUMPS spec (1977__a108037.md) are correctly modeled:
1. **Kill All** (`K`): `exclusive=False, targets=[]` - detectable via `len(targets)==0 and not exclusive`
2. **Selective Kill** (`K X,Y`): `exclusive=False, targets=[X,Y]` - non-empty targets
3. **Exclusive Kill** (`K (X,Y)`): `exclusive=True, except_list=['X','Y']` - preserves exception list

**Files Validated**:
- [X] V1CMT.m - Comment tests (7 labels, 16 statements)
- [X] V1DGA.m - $DATA/KILL global tests (13 labels, 107 statements, label 198 exclusive KILL verified, label 199 kill-all verified)
- [X] V1DGB.m - Driver file (3 labels, 4 statements)
- [X] V1DGB1.m - $DATA/KILL global tests (10 labels, 88 statements)
- [X] V1DGB2.m - $DATA/KILL global tests (9 labels, 83 statements)
- [X] V1DLA.m - $DATA/KILL local tests (12 labels, 114 statements, labels 218/824/217 kill forms verified)
- [X] V1DLB.m - Driver file (3 labels, 4 statements)

- [X] T454 [VALIDATED] Exclusive KILL (`K (vars)`) already correctly captured with `exclusive=True` and `except_list` populated.
- [X] T455 [VALIDATED] Argumentless KILL already distinguishable: `len(targets)==0 and not exclusive` means Kill All.
- [X] T456 [VALIDATION] All 7 files in checklist 7/54 parse correctly with expected labels and statements.

---

## Phase 23: MUGJ Validation Checklist - V1DLB1 to V1DO3 ✅ COMPLETE

**Purpose**: Validate V1DLB1.m through V1DO3.m (Checklist 8/54).

**Validation Date**: 2024-12-20
**Revalidation**: 2025-12-20 via `uv run python utils/validate_asg.py` on V1DLB1–V1DO3 — no discrepancies found.

**Files Validated**:
- [X] T457 [VALIDATION] V1DLB1.m - $DATA/KILL local variables -2- (10 labels, 90 statements)
- [X] T458 [VALIDATION] V1DLB2.m - $DATA/KILL local variables -3- (9 labels, 90 statements)
- [X] T459 [VALIDATION] V1DLC.m - $DATA/KILL local variables -4- exclusive KILL (9 labels, 87 statements)
- [X] T460 [VALIDATION] V1DO.m - DO command driver (4 labels, 6 statements)
- [X] T461 [VALIDATION] V1DO1.m - DO command (% labels) (37 labels, 122 statements)
- [X] T462 [VALIDATION] V1DO2.m - DO command (alpha/numeric labels) (37 labels, 166 statements)
- [X] T463 [VALIDATION] V1DO3.m - DO command (label+offset) (25 labels, 131 statements)

**Key Features Validated**:
1. **$DATA intrinsic function**: Correctly captured in expressions
2. **KILL commands**: All three forms (kill-all, selective, exclusive) correctly captured per T454-T455
3. **DO label calls**: All label names (%, alpha, numeric, reserved words, mixed) correctly resolved
4. **DO routine calls**: External routine calls (^V1DO1, ^VREPORT) captured as ROUTINE_CALL
5. **DO label+offset**: `D 012+01.99999` captured with call_type=OFFSET_CALL and offset expression
6. **DO argument list**: `D %,%0A1B2C3,DO,012` captured with multiple MCall targets
7. **Label back-references**: Caller tracking working (e.g., EXAMINER has 10-21 callers)
8. **Postconditions**: `W:$Y>55 #` correctly captured with condition expression

**Notes for Code Generation**:
- Label names like `%`, `DO`, `IF`, `012` need Python name sanitization
- Label+offset calls require runtime line-number computation (rarely used, can defer)
- Naked global tracking needed for `^V1A(2)-^(3)` pattern (known issue)

---

## Bugs Found During Validation

### BUG-001: Multiple Exclusive KILL Groups Not Parsed (Found in V1DLC.m) ✅ FIXED

**Severity**: Medium  
**Files Affected**: V1DLC.m labels 232, 235

**Description**: The grammar `KillCommand` only handled ONE exclusive group OR multiple selective targets, but NOT:
- Multiple exclusive groups: `K (X,Y,Z),(X,W)` - keeps intersection of both lists (only X)
- Mixed exclusive+selective: `K (X,W),Z` - exclusive kill, then also kill Z

**Fix Applied**:
- [x] T464 [BUG] Updated grammar to allow `killarglist` with mixed exclusive and selective arguments
  - Changed `KillCommand` to use `args+=KillArgument[/,/]`
  - New `KillArgument` rule supports both exclusive groups and selective targets
- [x] T465 [BUG] Updated MKillStatement with `except_groups: List[List[str]]` field
  - `except_groups` stores raw groups
  - `except_list` stores computed intersection
- [x] T466 [BUG] Added tests for multiple exclusive KILL patterns
  - `test_multiple_exclusive_groups`: K (X,Y,Z),(X,W)
  - `test_mixed_exclusive_selective`: K (X,W),Z

**Verification**:
- V1DLC.m label 232: `K (X,Y,Z),(X,W)` → `except_groups=[['X','Y','Z'],['X','W']], except_list=['X']` ✅
- V1DLC.m label 235: `K (X,W),Z` → `except_groups=[['X','W']], targets=[Z]` ✅

---

## Phase 24: MUGJ Validation Checklist - V1FNF2 to V1FORA1 ✅ COMPLETE

**Purpose**: Validate V1FNF2.m through V1FORA1.m (Checklist 10/54).

**Validation Date**: 2025-12-20

**Initial Concern (Investigated and Resolved)**:
- ~~V1FORA1.m drops all GOTO commands~~ **NOT A BUG**: Investigation revealed that `MGotoStatement` nodes ARE correctly captured in the ASG. The apparent issue was that `utils/validate_asg.py` wasn't displaying nested `then_scope` content when IF statements appear inside FOR bodies. The ASG structure is correct: `F J=4:0:5 S I=I+1 S VCOMP=VCOMP_J I I=4 G G3401` properly produces `MForStatement.body -> [MSetStatement, MSetStatement, MIfStatement] -> MIfStatement.then_scope -> [MGotoStatement]`.

**Fix Applied**:
- [X] T476 [FIX] Updated `utils/validate_asg.py` to display `then_scope` for IF statements nested inside FOR bodies, so validation output shows the complete nesting structure.

**Verification**:
- All three GOTO targets in V1FORA1.m (`G3401`, `G3402`, `G3403`) are correctly resolved
- `walk_statements()` correctly traverses nested scopes and finds all MGotoStatement nodes
- 621 tests passing

- [X] T467 [VALIDATION] V1FNF2.m - $FIND function tests (11 labels, 93 statements)
- [X] T468 [VALIDATION] V1FNF3.m - $FIND function tests with 3rd arg (9 labels, 79 statements)
- [X] T469 [VALIDATION] V1FNL.m - $LENGTH function tests (15 labels, 133 statements)
- [X] T470 [VALIDATION] V1FNP1.m - $PIECE function tests (13 labels, 97 statements)
- [X] T471 [VALIDATION] V1FNP2.m - $PIECE function tests (13 labels, 99 statements)
- [X] T472 [VALIDATION] V1FORA.m - FOR command driver (3 labels, 4 statements)
- [X] T473 [VALIDATION] V1FORA1.m - FOR command tests (13 labels, 108 statements, nested GOTO correctly captured)

---

## Phase 25: MUGJ Validation Checklist - V1FORA2 to V1GO1

**Purpose**: Validate V1FORA2.m through V1GO1.m (Checklist 11/54).

**Validation Date**: 2025-12-20

### Validation Results

- [X] T474 [VALIDATION] V1FORA2.m - FOR command tests (18 labels, 82 statements) - ✅ Nested FOR/QUIT/GOTO captured
- [X] T475 [VALIDATION] V1FORB.m - FOR command tests (13 labels, 101 statements) - ✅ Loop var subscripts and complex parameters captured
- [X] T476 [VALIDATION] V1FORC.m - FOR command driver (3 labels, 5 statements) - ✅ Correct
- [X] T477 [VALIDATION] V1FORC1.m - FOR command tests (12 labels, 73 statements) - ✅ Chained unary and complex expressions captured
- [X] T478 [VALIDATION] V1FORC2.m - FOR command tests (18 labels, 68 statements) - ✅ GOTO/DO target postconditions captured
- [X] T479 [VALIDATION] V1GO.m - GOTO command driver (3 labels, 4 statements) - ✅ Correct
- [X] T480 [VALIDATION] V1GO1.m - GOTO command tests (33 labels, 146 statements) - ✅ Correct

### Summary of Files

| File | Labels | Statements | Issues |
|------|--------|------------|--------|
| V1FORA2.m | 18 | 82 | ✅ 5-level nesting, QUIT/GOTO in FOR scopes captured |
| V1FORB.m | 13 | 101 | ✅ Loop var subscripts and complex parameters captured |
| V1FORC.m | 3 | 5 | ✅ Simple driver file, correct |
| V1FORC1.m | 12 | 73 | ✅ Chained unary and complex expressions captured |
| V1FORC2.m | 18 | 68 | ✅ GOTO/DO target postconditions captured |
| V1GO.m | 3 | 4 | ✅ Correct |
| V1GO1.m | 33 | 146 | ✅ Correct |
| V1GO.m | 3 | 4 | ✅ Simple driver file, correct |
| V1GO1.m | 33 | 146 | ✅ All 30 GOTO tests correctly captured |

---

### BUG-002: Chained Unary Operators Not Supported ❌ OPEN

**Severity**: High  
**Files Affected**: V1FORC1.m (line 366), potentially many others

**Description**: The expression grammar only allows a single optional unary operator before a primary expression. MUMPS allows multiple chained unary operators like `--X`, `''X`, `+-X`.

**Current Grammar** (expressions.tx line 15-17):
```textx
UnaryExpr:
    operator=UnaryOp? operand=PrimaryExpr
;
```

**Failing Cases**:
```mumps
F I='0:+"000001.20E-.8ABDEF0":--"82E-1FOR" S VCOMP=VCOMP_I_" "
;      ^^                    ^^
;    single OK              double FAILS
```

**Test Results**:
- `S X=-1` → `['SetCommand']` ✅
- `S X=--1` → `[]` ❌
- `S X=''1` → `[]` ❌
- `S X=+-1` → `[]` ❌

**Fix Required**:
- [X] T481 [BUG] **VERIFIED FIXED 2025-12-24** Update UnaryExpr grammar to allow chained unary operators:
  ```textx
  UnaryExpr:
      operators*=UnaryOp operand=PrimaryExpr
  ;
  ```
- [X] T482 [BUG] **VERIFIED FIXED 2025-12-24** Update MUnaryOp ASG class to support multiple operators or nested structure
- [X] T483 [BUG] **VERIFIED FIXED 2025-12-24** Add tests for chained unary operator expressions

---

### BUG-003: Subscripted Loop Variables in FOR Not Supported ❌ OPEN

**Severity**: High  
**Files Affected**: V1FORB.m (lines 31, 33, 35), V1FORC1.m (line 369)

**Description**: The FOR command grammar only allows simple variable names as loop variables. MUMPS allows subscripted variables as loop variables.

**Current Grammar** (commands.tx line 156-157):
```textx
ForCommand:
    /[Ff][Oo][Rr]|[Ff]/ (WS var=VARNAME '=' params+=ForParam[/,/])?
;
```

**Failing Cases**:
```mumps
F J(1,2,3)=1:1:3 S VCOMP=VCOMP_J(1,2,3)_" "
F J(I)=1:1:3 S I=I+2,VCOMP=VCOMP_J(I)_" "
F A(A+B+C,$A(A),D_E)=1:1:3 S A=A+1 S VCOMP=VCOMP_A_" "
F A(^(1,^V1A(1)))=^(2,3):^V1B(4):^(5) S VCOMP=VCOMP_^(1)
```

**Test Results**:
- `F A=1:1:3 S X=1` → `['ForCommand', 'SetCommand']` ✅
- `F A(1)=1:1:3 S X=1` → `[]` ❌
- `F A(B)=1:1:3 S X=1` → `[]` ❌

**Fix Required**:
- [X] T484 [BUG] **VERIFIED FIXED 2025-12-24** Update ForCommand grammar to use LocalVariable instead of VARNAME:
  ```textx
  ForCommand:
      /[Ff][Oo][Rr]|[Ff]/ (WS var=LocalVariable '=' params+=ForParam[/,/])?
  ;
  ```
- [X] T485 [BUG] **VERIFIED FIXED 2025-12-24** Update MForStatement and parsing to handle subscripted loop variables
- [X] T486 [BUG] **VERIFIED FIXED 2025-12-24** Add tests for subscripted FOR loop variables

---

### BUG-004: GOTO/DO Argument Postcondition Grammar Incorrect ❌ OPEN

**Severity**: High  
**Files Affected**: V1FORC2.m (multiple lines), V1FORA2.m (multiple lines)

**Description**: The GOTO and DO target grammar places postcondition BEFORE the label, but in MUMPS the argument postcondition comes AFTER the target. `G ABC:X=1` means "GOTO ABC if X=1".

**Current Grammar** (commands.tx line 173-175):
```textx
GotoTarget:
    postcond=Postcondition? label=LabelRef   ; WRONG ORDER
;
```

**Correct Semantics**:
```mumps
G G379:X=1    ; GOTO G379 if X=1  (arg postcondition AFTER target)
G:X=1 G379    ; GOTO G379 if X=1  (command postcondition AFTER keyword)
```

**Test Results**:
- `G ABC` → `['GotoCommand']` ✅
- `G:X=1 ABC` → `['GotoCommand']` ✅ (command postcondition)
- `G ABC:X=1` → `[]` ❌ (argument postcondition)

**Fix Required**:
- [X] T487 [BUG] **VERIFIED FIXED 2025-12-24** Fix GotoTarget grammar to place postcondition AFTER label:
  ```textx
  GotoTarget:
      label=LabelRef postcond=Postcondition?
  ;
  ```
- [X] T488 [BUG] **VERIFIED FIXED 2025-12-24** Fix DoTarget grammar similarly
- [X] T489 [BUG] **VERIFIED FIXED 2025-12-24** Add tests for argument postconditions on GOTO/DO

---

### BUG-005: Loop Variable Subscripts Not Converted to ASG ✅ FIXED

**Severity**: High  
**Files Affected**: [tests/functional/mugj/inref/V1FORB.m#L26-L34](tests/functional/mugj/inref/V1FORB.m#L26-L34)

**Description**: Subscripted loop variables inside FOR commands are parsed, but their subscript expressions remain as raw textX nodes instead of ASG expressions. Example: `F A(A+B+C,$A(A),D_E)=1:1:3 ...` leaves the subscripts as `<textx:expressions.Expr>` and `IntrinsicFunction` without conversion, preventing variable analysis and code generation from traversing the loop variable structure.

**Fix Applied**:
- [X] T490 [BUG] Added `_convert_loop_var_subscripts()` to SemanticAnalyzer to recursively convert subscript expressions to ASG nodes.
- [X] T491 [BUG] Updated `_analyze_ForCommand()` in semantic_analyzer.py to use the new helper.
- [X] T492 [BUG] Added `_convert_loop_var_to_asg()` and `_convert_subscripts_to_asg()` in command_parser.py for the `parse_for_command_to_asg` path.

**Verification**:
- V1FORB.m label 360 cases now produce proper ASG subscripts:
  - `J(1,2,3)` → NumericLiteral subscripts ✅
  - `J(I)` → LocalVariable subscript ✅
  - `A(A+B+C,$A(A),D_E)` → MBinaryOp, IntrinsicFunction, MBinaryOp subscripts ✅

---

### Notes for Code Generation

**V1FORA2.m**:
- Tests 5-level nested FOR loops (345) - important for Python nesting limits
- Tests GOTO in FOR scope (346) - classic FOR exit pattern

---

## Phase 26: MUGJ Validation Checklist - V1GO2 to V1IDARG3

**Purpose**: Validate V1GO2.m through V1IDARG3.m (Checklist 12/54).

**Validation Date**: 2025-12-21

### Validation Results

- [X] T493 [VALIDATION] V1GO2.m - GOTO label+offset variants (31 labels, 136 statements) - ❌ missing GOTO nodes with global offsets
- [X] T494 [VALIDATION] V1GVN.m - Global variable name acceptance (11 labels, 90 statements) - ✅ correct
- [X] T495 [VALIDATION] V1HANG.m - HANG command tests (20 labels, 144 statements) - ❌ STOP label dropped
- [X] T496 [VALIDATION] V1IDARG.m - Indirection driver (6 labels, 10 statements) - ✅ correct
- [X] T497 [VALIDATION] V1IDARG1.m - IF argument indirection (13 labels, 104 statements) - ✅ correct
- [X] T498 [VALIDATION] V1IDARG2.m - KILL argument indirection (13 labels, 92 statements) - ❌ indirect KILL targets missing
- [X] T499 [VALIDATION] V1IDARG3.m - SET argument indirection (13 labels, 62 statements) - ❌ trailing DO dropped in label 440

### Summary of Files

| File | Labels | Statements | Issues |
|------|--------|------------|--------|
| V1GO2.m | 31 | 140 | ✅ (fixed BUG-006) |
| V1GVN.m | 11 | 90 | ✅ |
| V1HANG.m | 20 | 147 | ✅ (fixed BUG-007) |
| V1IDARG.m | 6 | 10 | ✅ |
| V1IDARG1.m | 13 | 104 | ✅ |
| V1IDARG2.m | 13 | 109 | ✅ (fixed BUG-008) |
| V1IDARG3.m | 13 | 77 | ✅ (fixed BUG-009) |

---

### BUG-006: GOTO Offsets with Global Expressions Dropped ✅ FIXED

**Severity**: High  
**Files Affected**: V1GO2.m labels 389, 392, STAR

**Description**: `G STAR+^V1A`, `G HAL9000+^V1A(2)-ZORAC`, and `GOTO 389+^V1A-A(^V1A)` were not producing `MGotoStatement` nodes. The entire command (and subsequent SET on the same line) was dropped when the offset expression contains globals or subscripts.

**Fix Applied**:
- [X] T500 [BUG] Made offset optional in LabelRef when followed by routine (`('+' offset=OffsetExpr?)`) in commands.tx
- [X] T501 [BUG] Added `SubscriptedGlobal` rule in expressions.tx to allow `^VAR(...)` in offset expressions (disambiguates from routine names)
- [X] T502 [BUG] Verified all GOTO patterns now parse: `G STAR+^V1A`, `G HAL9000+^V1A(2)-ZORAC`, etc.

---

### BUG-007: STOP Label Body Dropped in V1HANG.m ✅ FIXED

**Severity**: High  
**Files Affected**: V1HANG.m label STOP

**Description**: Label `STOP` had zero statements in the ASG. Source line `S H=$$^difftime($H,H) W "<  EXPECTED:",TM,?55,"MEASURED:",H Q` was not parsed into `MSetStatement`/`MWriteStatement`/`MQuitStatement`.

**Fix Applied**:
- [X] T503 [BUG] Made label optional in ExtrinsicFunction grammar (`'$$' label=VARNAME?`) to support `$$^routine(args)` pattern
- [X] T504 [BUG] STOP label now correctly parses 3 statements: SET, WRITE, QUIT

---

### BUG-008: Indirected KILL Targets Missing ✅ FIXED

**Severity**: High  
**Files Affected**: V1IDARG2.m labels 426, 427, 428, 430

**Description**: KILL commands with argument-level or name-level indirection were not represented:
- `K @%1`, `K @%2`, `K @^V1A(1)` (426) were absent
- `K @%1,@%2,@(%1_","_%2),@^V1A(1)` (427) reduced to selective kills only
- `K @B` (428) captured as `K A` (loses indirection and subscripts)
- `K @Z,Z` (430) only partially represented

**Fix Applied**:
- [X] T505 [BUG] Added `Indirection` to KillTarget rule in commands.tx: `KillTarget: GlobalVariable | Indirection | LocalVariable`
- [X] T506 [BUG] All KILL patterns with indirection now parse correctly

---

### BUG-009: Trailing DO Dropped After Multi-SET Line ✅ FIXED

**Severity**: Medium  
**Files Affected**: V1IDARG3.m label 440

**Description**: Line `S @A,VCOMP=A(2)_" "_C(10),VCORR="  9.88 SET" D EXAMINER` was parsed as two `MSetStatement` nodes but the trailing `D EXAMINER` was missing. Multi-command lines that mix comma-separated SET arguments with a following DO were truncated.

**Fix Applied**:
- [X] T507 [BUG] Added `SetArgument` and `SetIndirection` rules to allow standalone `@VAR` indirection in SET command arguments
- [X] T508 [BUG] SET command now parses `@A` as argument-level indirection, followed by regular assignments, followed by DO command
- Tests QUIT in FOR scope (347) - both with and without postcondition
- Tests XECUTE in FOR scope (348) - runtime code execution
- Tests open-ended FOR with GOTO exit (350-353) - requires while-break pattern

**V1FORB.m**:
- Tests list-of-forparameter (355) - `F I=1,3,4,5.5,-1,"ABC"` needs special handling
- Tests subscripted loop variables (360) - complex case for Python
- Tests `$D(I)` as forparameter (361) - function calls in parameters

**V1FORC1.m**:
- Tests complex expression forparameters (364-367) - including unary ops, functions
- Tests global variables in forparameters (368-369)
- Tests FOR...QUIT...FOR combinations (370-372)

**V1FORC2.m**:
- Tests complex FOR+GOTO combinations (373-379)
- Tests `label^routine` GOTO targets with postconditions
- Most challenging FOR/GOTO combinations in test suite

**V1GO1.m**:
- Tests all label name formats: %, alpha, numeric, mixed
- Tests labels that match reserved words: SET, QUIT, IF, DO
- All 30 GOTOs correctly resolved to target labels

---

## Phase 27: MUGJ Validation - Indirection in DO/GOTO Commands (Checklist 13)

**Purpose**: Document and track issues discovered during validation of V1IDARG4-V1IDGO files.

**Files Validated**: V1IDARG4.m, V1IDARG5.m, V1IDDO.m, V1IDDO1.m, V1IDDOA.m, V1IDDOB.m, V1IDGO.m

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1IDARG4.m | 12 | 74 | ✅ Complete | Multi-level indirection (@@, @@@) in WRITE - all captured |
| V1IDARG5.m | 12 | 74 | ✅ Complete | XECUTE with indirection, postconditions on XECUTE captured |
| V1IDDO.m | 3 | 5 | ✅ Complete | Simple driver file |
| V1IDDO1.m | 13 | 37 | ✅ Complete | Target labels for indirection tests |
| V1IDDOA.m | 27 | 100 | ✅ Complete | Complex indirect DO with offsets - now captured |
| V1IDDOB.m | 27 | 105 | ✅ Complete | Double indirection DO (@@var^@routine) - now captured |
| V1IDGO.m | 3 | 4 | ✅ Complete | Simple driver file |

### BUG-010: Complex Indirect DO Statements Not Fully Captured ✅ RESOLVED

**Severity**: High  
**Files Affected**: V1IDDOA.m (lines 18, 29, 42), V1IDDOB.m (lines 7, 12-13, 38, 44, 47)

**RESOLUTION** (2024-01-21):

Enhanced the grammar and semantic analyzer to fully capture complex indirect DO and GOTO patterns:

1. **Grammar Changes** (`src/m2py/grammar/commands.tx`):
   - Added `IndirectChain` rule for nested indirection (`@@VAR`, `@@@VAR`)
   - Enhanced `DoIndirect` with `labelIndirect`, `routineIndirect`, and `offset` support
   - Enhanced `LabelRef` with `routineIndirect` option for indirect routine names
   - Added `GotoIndirect` rule mirroring DoIndirect for GOTO command

2. **ASG Changes** (`src/m2py/asg/elements.py`):
   - Added to MCall: `routine_indirection`, `label_is_indirect`, `routine_is_indirect`, `indirection_levels`

3. **Semantic Analyzer Changes** (`src/m2py/analysis/semantic_analyzer.py`):
   - Added `_analyze_indirect_chain()` to walk nested indirection and count levels
   - Updated `_analyze_DoCommand()` to handle new grammar structure
   - Updated `_analyze_GotoCommand()` to handle new grammar structure

4. **Test Patterns Now Parsing Correctly**:
   - `D @A`, `D @A+5`, `D @@A` - basic indirect with offset
   - `D @A^ROUTINE`, `D @A^@C`, `D @@A^@C` - indirect with routine
   - `D LABEL^@C`, `D LABEL^@@C` - static label with indirect routine
   - `D V1IDDO+-5+@^V1IDDO1^@@C` - complex offset with nested indirect routine
   - `D @A^@C,V1IDDO+-5+@^V1IDDO1^@@C` - multiple complex targets
   - `G @C`, `G @A^@C`, `G @@B+1^V1IDGO1` - GOTO indirect patterns

All 633 tests pass. V1IDGOA.m and V1IDGO.m parse successfully.

**Original Description**: DO commands with complex indirection patterns were not fully captured in the ASG:

1. **Double indirection in label+routine**: `D @@A^@C` (V1IDDOB line 7)
   - Should parse the @@A (double indirection) for label and @C for routine
   
2. **Indirection with offset expressions**: `DO @A+00002+(2+3)-04` (V1IDDOA line 18)
   - Indirect label with arithmetic offset expression
   
3. **Multiple complex DO targets on one line**: `D @@A+A(2),@^V1A` (V1IDDOA line 29)
   - Double indirection with subscripted offset + global indirection
   
4. **Very complex patterns**: `D @A^@C,V1IDDO+-5+@^V1IDDO1^@@C` (V1IDDOA line 42)
   - Mix of indirect label, indirect routine, negative offsets, nested indirection

**Current Behavior**: Parser captures `D EXAMINER` calls but drops the complex indirect DO statements on the same or preceding lines.

**Workaround**: None - these patterns require runtime XECUTE-like handling anyway.

**Why Additional Parsing IS Helpful** (even for runtime-evaluated patterns):

Even though the final target cannot be resolved statically, parsing the **structure** of these patterns enables:

1. **Typed Runtime Dispatch**: Instead of treating `D @@A^@C` as opaque text, we can generate:
   ```python
   # Current (unparsed): falls back to generic XECUTE-like handler
   runtime.do_indirect("@@A^@C")  # No structure
   
   # With parsing: structured runtime call
   runtime.do_indirect(
       label_indirection=Indirect(Indirect(var='A')),  # @@A
       routine_indirection=Indirect(var='C'),           # ^@C
       offset=None
   )
   ```

2. **Offset Expression Evaluation**: For `DO @A+5` we need to:
   - Evaluate `@A` at runtime to get label name
   - Add 5 to get the actual line offset
   - Having `offset=NumericLiteral(5)` in the ASG makes this explicit

3. **Error Handling**: Knowing the structure allows better error messages:
   - "Cannot resolve routine from @C" vs "Invalid DO target"

4. **Analysis Flags**: We can set `requires_runtime_eval` specifically for:
   - `routine_is_indirect: bool` - Need to resolve routine name at runtime
   - `label_is_indirect: bool` - Need to resolve label name at runtime
   - `has_nested_indirection: bool` - @@var patterns need special handling

5. **Optimization Opportunities**: Some cases like `D ^@A` where A is set to a constant 
   string on the previous line could be constant-folded in a future optimization pass.

**Grammar Enhancement Needed**:

Current `DoIndirect` only handles: `@VAR` or `@(expr)`

Should handle the full pattern: `@expr (+offset)? (^routine)?` where routine can also be `@expr`

```textx
// Enhanced DO indirection to support full label reference structure
DoIndirect:
    labelIndirect=IndirectExpr 
    ('+' offset=OffsetExpr?)?  // Optional offset after indirect label
    ('^' (routineIndirect=IndirectExpr | routine=VARNAME))?  // Optional routine
    args=FunctionArgs?
;

// Indirection can be nested: @@VAR means @(@VAR)
IndirectExpr:
    '@' (
        nested=IndirectExpr |           // Recursive for @@, @@@
        '(' expr=Expr ')' |             // Parenthesized
        var=LocalVariable |             // Simple variable
        global=GlobalVariable           // ^VAR indirection
    )
;
```

**Tasks** (All completed 2024-01-21):
- [X] T509 [BUG] Investigate DO command parsing for indirect label+offset patterns
- [X] T510 [BUG] Add grammar support for `@@var` double indirection in DO targets
- [X] T511 [BUG] Add grammar support for `@var^@routine` in DO targets
- [X] T512 [BUG] Add unit tests for complex indirect DO patterns (utils/test_indirect_do.py)
- [X] T513 [ENH] Add `routine_is_indirect` and `label_is_indirect` flags to MCall
- [X] T514 [ENH] Add `IndirectChain` grammar rule (renamed from IndirectExpr) for nested indirection
- [X] T515 [ENH] Extend DoIndirect grammar to support offset and routine components
- [X] T516 [ENH] Add GotoIndirect grammar for GOTO command parity with DO

### Observations for Code Generation

1. **Multi-level indirection** (@@, @@@) - Requires runtime string evaluation, cannot resolve statically
2. **Indirection in routine names** (`D ^@A`, `D @A^@routine`) - Dynamic dispatch at runtime
3. **Format controls in WRITE** (!?3, #) - Need to map to Python print formatting
4. **XECUTE with indirection** - Already flagged as `requires_runtime_eval`
5. **Implicit fall-through** - V1IDGO.m has no QUIT at end, relies on fall-through between labels

---

## Phase 28: MUGJ Validation Checklist - V1IDGO1 to V1IDNM3

**Purpose**: Validate indirection-heavy GOTO and name-level indirection tests (Checklist 14/54).

**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1IDGO1.m | 11 | 44 | ✅ Complete | Complex GOTO indirection/postconditions captured |
| V1IDGOA.m | 30 | 106 | ✅ Complete | Indirect GOTO targets and offsets retained |
| V1IDGOB.m | 28 | 109 | ✅ Complete | Nested indirect GOTOs with postconditions captured |
| V1IDNM.m | 4 | 6 | ✅ Complete | Driver DO calls preserved |
| V1IDNM1.m | 12 | 64 | ✅ Complete | FOR loops with indirect loop vars/params captured |
| V1IDNM2.m | 15 | 89 | ✅ Complete | SET/KILL with name-level indirection captured |
| V1IDNM3.m | 14 | 77 | ✅ Complete | $DATA/$NEXT with multi-level indirection preserved |

### Findings

- All commands and expressions in this batch are present in the ASG; no dropped statements or labels observed.
- Indirection metadata (`label_is_indirect`, `routine_is_indirect`, `indirection_levels`) is populated for indirect DO/GOTO targets, matching the runtime patterns needed for code generation.
- $DATA/$NEXT intrinsic calls with indirect arguments (V1IDNM3) are represented in the statement expressions, preserving nested indirection structure for later evaluation.

---

## Phase 29: MUGJ Validation Checklist - V1IE to V1JST

**Purpose**: Validate IF/ELSE/$TEST and I/O control tests (Checklist 15/54).

**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1IE.m | 3 | 4 | ✅ Complete | Simple driver with external DO calls |
| V1IE1.m | 12 | 85 | ✅ Complete | IF/ELSE/$TEST tests; all captured correctly |
| V1IE2.m | 8 | 94 | ✅ Complete | Argumentless IF, $TEST usage captured |
| V1IO.m | 2 | 70 | ✅ Complete | READ/GOTO now captured after T517/T518 fixes |
| V1IO1.m | 10 | 50 | ✅ Complete | I/O tests with SET/WRITE/DO |
| V1IO2.m | 16 | 68 | ✅ Complete | FOR with string-list parameters captured |
| V1JST.m | 4 | 7 | ✅ Complete | Simple driver with external DO calls |

### Issues Fixed

#### Issue T517: READ command grammar fails with adjacent format controls ✅ FIXED

**Fix Applied**: Modified `ReadCommand` grammar to use `args*=ReadArg` with optional comma `/,/?` in each `ReadArg`, matching the pattern used by `WriteCommand`. Added `ReadArgValue` wrapper to properly dispatch to `ReadFormat`, `StringLiteral`, or `ReadTargetWithTimeout`.

#### Issue T518: OPEN command grammar fails with empty params and timeout (`::`) ✅ FIXED

**Fix Applied**: Extended `OpenArg` grammar to add a `':' ':' timeout=Expr` alternative that matches the double-colon syntax for "empty params with timeout".

### Tasks Completed

- [X] T517 [BUG] Fix READ command grammar to allow adjacent format controls without commas (R !!,"text")
- [X] T518 [BUG] Fix OPEN command grammar to allow empty params with timeout (OPEN X::10)

### Detailed File Validations

#### V1IE.m (IF/ELSE driver)
- 3 labels: V1IE, V1IE1, V1IE2
- Simple structure: WRITE and DO calls to external routines
- All statements captured correctly

#### V1IE1.m (IF/ELSE/$TEST tests - Part 1)
- 12 labels testing IF conditions, ELSE behavior, $TEST special variable
- Complex line: `I 1 S VCOMP=VCOMP_" " S:0 VCOMP=VCOMP_" " I  S VCOMP=VCOMP_"//"_$TEST`
  - Multiple SET with postconditions on same line
  - Argumentless IF (`I `)
  - $TEST special variable references
- All IF/ELSE pairs properly nested in ASG
- Label call resolution working (EXAMINER called 12 times, all resolved)

#### V1IE2.m (IF/ELSE/$TEST tests - Part 2)
- 8 labels with complex $TEST evaluations
- Features: argumentless IF, IF with comma-separated conditions
- Line 73: `K A I $D(A),A S VCOMP=...` - KILL followed by IF with $DATA
- All control flow structures preserved correctly

#### V1IO.m (I/O Control driver) - **HAS ISSUES**
- 2 labels: V1IO, END
- **Line 8 missing**: READ with format controls (`R !!,"WHEN..."`)
- **Line 10 missing**: READ + GOTO combination
- Lines with simple OPEN, USE, CLOSE correctly captured
- I/O statements (MOpenStatement, MUseStatement, MCloseStatement) present

#### V1IO1.m (I/O Control tests - Part 1)
- 10 labels testing $JOB, $IO, $X, $Y after I/O operations
- All SET/WRITE/DO statements captured
- No I/O commands in this file (tests results set by V1IO.m)

#### V1IO2.m (I/O Control tests - Part 2)
- 16 labels testing I/O effects
- **Notable**: Label 554 has FOR with 17-element string list parameter
  - `F I=532,533,534,5380,5381,5390,5391,5400,5401,5411,5412,5413,551,5521,5520,5522,553 S ...`
  - Correctly captured as MForStatement with 17 parameters

#### V1JST.m ($JUSTIFY/$SELECT/$TEXT driver)
- 4 labels: V1JST, V1JST1, V1JST2, V1JST3
- Simple driver structure calling external routines
- All statements captured correctly

### Observations for Code Generation

1. **Argumentless IF (`I ` or `IF `)** - Uses prior $TEST value; code generation must track $TEST state
2. **$TEST special variable** - Must be maintained across IF/ELSE executions
3. **I/O commands** - OPEN/USE/CLOSE need Python equivalents (file handles or context managers)
4. **$X, $Y, $IO, $JOB** - Special variables tracking cursor position and device; need runtime support
5. **READ with timeout** - `R VAR:timeout` - Needs timed input implementation

---

## Phase 30: MUGJ Validation Checklist - V1JST1 to V1MAX

**Purpose**: Validate $JUSTIFY/$SELECT/$TEXT functions and label/variable naming tests (Checklist 16/54).

**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1JST1.m | 21 | 98 | ✅ Complete | $JUSTIFY(expr,int) tests with FOR loop |
| V1JST2.m | 17 | 92 | ✅ Complete | $JUSTIFY(num,int,int) 3-arg tests |
| V1JST3.m | 22 | 90 | ✅ Complete | $SELECT and $TEXT tests; Z1,Z2,Z4 comment labels |
| V1LL1.m | 20 | 85 | ✅ Complete | Labelless first line now captured in preamble label |
| V1LL2.m | 28 | 104 | ✅ Complete | All label formats captured correctly |
| V1LVN.m | 11 | 104 | ✅ Complete | Local variable naming tests (subscripted) |
| V1MAX.m | 3 | 5 | ✅ Complete | Simple driver calling external V1MAX1/V1MAX2 |

### Issues Fixed

#### Issue T519: Labelless first line not captured in V1LL1.m ✅ FIXED

**Problem**: V1LL1.m has a labelless first line:
```mumps
	S VCOMP="LABEL LESS";;;
V1LL1	;YS-TS,V1LL,VALIDATION VERSION 7.1;31-AUG-1987;LINE LABELS -1-
```

The first line starts with whitespace (no label) and contains `S VCOMP="LABEL LESS"`. This statement was **not captured** in the ASG.

**Fix Applied**: Modified `_build_routine()` in `src/m2py/parser/parser.py` to create a synthetic "preamble" label with an empty name (`''`) for any `ContLine` that appears before the first named label. The preamble label is inserted at the beginning of the routine's labels list.

### Tasks

- [X] T519 [BUG] Support labelless first lines in MUMPS files (V1LL1.m line 1 now captured)

### Detailed File Validations

#### V1JST1.m ($JUSTIFY 2-arg tests)
- 21 labels testing `$JUSTIFY(expr1, intexpr2)` - right-padding strings
- I-555 through I-571: Various expr1 types (string, number, binary ops, globals)
- One FOR loop at label 566: `F I=1:1:255 S VCORR=VCORR_" "`
- All $J intrinsic function calls captured correctly
- EXAMINER subroutine resolved with 22 callers

#### V1JST2.m ($JUSTIFY 3-arg tests)
- 17 labels testing `$JUSTIFY(numexpr1, intexpr2, intexpr3)` - decimal formatting
- I-572 through I-585: Rounding, sign handling, decimal places
- Uses naked global references in I-585: `^V1A(2,2)`, `^(2,2,2)`, etc.
- All naked global usage preserved in ASG expressions

#### V1JST3.m ($SELECT and $TEXT tests)
- 22 labels including utility labels Z1, Z2, Z4 for $TEXT testing
- $SELECT tests (I-586 through I-592): Short-circuit evaluation, $TEST interaction
- $TEXT tests (I-593 through I-600): Line reference, +intexpr, indirection
- IF/ELSE pairs captured correctly for $TEST validation
- Comment-only labels (Z1, Z2, Z4) correctly captured with 0 statements

#### V1LL1.m (Line Labels test - Part 1)
- 20 labels: 1 preamble (empty name) + 19 named labels
- Labels like `%`, `%A`, `%ABZWQ`, `%01`, `%000000`, `%234EFGH` all captured
- Preamble label contains `S VCOMP="LABEL LESS"` from line 1
- Test I-609 "the first line is labelless" now correctly captured

#### V1LL2.m (Line Labels test - Part 2)
- 28 labels including single-letter (A), pure numeric (3, 00, 123), mixed (A1B2C3)
- All variations of valid MUMPS labels captured correctly
- EXAMINER subroutine resolved with 21 callers

#### V1LVN.m (Local Variable Names)
- 11 labels testing local variable naming rules
- Tests `%`, `%ABCDEF`, `%1234` and regular names with subscripts
- I-618: 8 levels of subscript depth `ABCDEFGH(1,2,3,4,5,6,7,8)` - captured correctly
- All subscripted variable assignments preserved in MSetStatement

#### V1MAX.m (Maximum Range Driver)
- 3 labels: V1MAX (empty), V1MAX1, V1MAX2
- Simple driver that calls external routines `^V1MAX1` and `^V1MAX2`
- External routine calls marked as `is_resolved=False` (expected)

### Observations for Code Generation

1. **$JUSTIFY intrinsic** - Needs right-padding and decimal rounding implementation
2. **$SELECT intrinsic** - Short-circuit evaluation (only evaluate until true found)
3. **$TEXT intrinsic** - Requires runtime access to source file text (or precompiled text table)
4. **Preamble labels** - Empty-name label for labelless first lines; code gen should execute before main entry
5. **% prefix labels/variables** - Valid in MUMPS, need escaping or renaming for Python
6. **Naked global references** - Must track last-used global context at runtime

---

## Phase 31: MUGJ Validation Checklist - V1MAX1 to V1NR

**Purpose**: Validate maximum range and LOCK/OPEN/NAKED reference driver files (Checklist 17/54).

**Validation Date**: 2025-12-21 (Re-validated)

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1MAX1.m | 9 | 69 | ✅ Complete | Large literal/string range tests, FOR loops, complex expressions |
| V1MAX2.m | 7 | 43 | ✅ Complete | Deep subscript (15 levels) and 9-digit subscript tests |
| V1MJA.m | 3 | 11 | ✅ Complete | Driver with postconditioned WRITE and external DO calls |
| V1MJA1.m | 16 | 133 | ✅ Complete | LOCK variations including indirection `L @A` now captured |
| V1MJA2.m | 14 | 107 | ✅ Complete | OPEN/CLOSE/USE statements, IF/ELSE, pattern matching |
| V1MJB.m | 20 | 127 | ✅ Complete | Extensive LOCK variations with timeouts and targets |
| V1NR.m | 3 | 4 | ✅ Complete | Naked reference driver, external routine calls |

### Re-Validation Findings (2025-12-21)

Previous issues (T520-T522) have been resolved. Current validation confirms:

1. ✅ **LOCK command variations** - All standard forms work correctly:
   - Simple lock: `L ^V1A(1,2)`
   - Parenthesized list with timeout: `L (^V1A,^V1B):1`
   - Postconditioned lock: `L:1=0.1 ^V1A(2,2)`
   - Lock with timeout: `L ^V1A(2):1`
   - Lock on local variables: `L A(1,1)`
   - Argumentless unlock: `L`
   - Lock operators: `+` and `-`

2. ⚠️ **NEW ISSUE - LOCK with indirection not captured**:
   - File: V1MJA1.m, line 55, label 635
   - Source: `S A="^V1A" L @A K ^V1F`
   - The `L @A` (LOCK with name indirection) is silently skipped
   - Root cause: `LockTarget` grammar rule uses `VarRef` which is `GlobalVariable | LocalVariable`
   - Indirection `@expr` is not part of `VarRef`, so the parse fails and command is dropped

3. ✅ **I/O commands** - OPEN, CLOSE, USE, READ all captured correctly with:
   - Device expressions
   - Timeouts
   - Postconditions
   - Argument lists

4. ✅ **Special variables** - `$Y`, `$JOB`, `$IO`, `$TEST`, `$D` all captured in expressions

5. ✅ **Pattern matching** - Expressions like `$JOB?1N.N` properly captured as pattern match operations

### Tasks

- [x] T520 [BUG] Handle `K  L  Q` tails as Kill + unlock-only Lock (no targets) + Quit in command parsing.
  - **Root cause**: LockCommand grammar used `WS?` which was greedy and consumed the next command keyword as a lock target.
  - **Fix**: Changed LockCommand grammar to require single space before targets like KillCommand: `(' ' lockop=LockOp? (locklist=LockList | targets+=LockTarget[/,/]))?`
  - **Result**: Now correctly parses "double-space = argumentless command" pattern. 642 tests pass.
- [x] T521 [BUG] Preserve multi-command lines with K/LOCK/K in V1MJA1 (label 632/635).
  - **Fixed by T520**: Grammar fix allows proper command separation.
- [x] T522 [BUG] Fix empty labels 632/634/635 in V1MJB.
  - **Fixed by T520**: Grammar fix plus semantic analyzer update to handle parenthesized lock lists (`locklist`).
  - **Added**: `_analyze_LockCommand` now processes `cmd.locklist` for parenthesized lock targets like `L (^A,^B):1`.
- [x] T523 [US5] Add indirection support to LOCK command grammar
  - **File**: V1MJA1.m, label 635, line 55: `L @A`
  - **Root cause**: `LockTarget` used `VarRef` which doesn't include `Indirection`
  - **Fix**: Extended grammar to support indirection in lock targets:
    - Added `LockListItem` rule: `indirect=IndirectChain | target=VarRef`
    - Updated `LockTarget` rule: `postcond? (indirect | target) (':' timeout)?`
    - Added `_analyze_lock_item()` and `_analyze_lock_target()` helper methods
    - Reused existing `_analyze_indirect_chain()` for consistent handling
  - **Result**: Lock indirection now captured with semantic structure:
    - `is_indirect: True` flag for code generation
    - `indirection`: The expression to dereference at runtime
    - `indirection_levels`: Supports nested indirection (@@A)
  - **Impact**: V1MJA1 label 635 now has 10 statements (was 7), all commands captured

---

## Phase 32: MUGJ Validation Checklist - V1NR1 to V1NUM

**Purpose**: Validate nesting/label/naked-reference tests (Checklist 18/54) ahead of codegen.

**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1NR1.m | 6 | 63 | ✅ Complete | Naked reference sequencing; EXAMINER backref resolved |
| V1NR2.m | 7 | 52 | ✅ Complete | Naked reference with KILL variations and data checks |
| V1NST1.m | 68 | 198 | ✅ Complete | Deep FOR/DO nesting (14 levels), external DO/GOTO links |
| V1NST2.m | 47 | 129 | ✅ Complete | Indirection-heavy DO chain; name/argument indirection captured |
| V1NST3.m | 52 | 136 | ✅ Complete | Mixed GOTO nesting across routines; FOR/QUIT exits captured |
| V1NSTE.m | 46 | 98 | ✅ Complete | External GOTO/DO ladder, nested FOR with postconditioned QUIT |
| V1NUM.m | 5 | 9 | ✅ Complete | Numeric literal driver calling ^V1NUM* routines |

### Observations for Code Generation

1. DO indirection (V1NST2 label 657) is captured as `MDo` with `indirection`; runtime will need to execute the comma-separated target list contained in the dereferenced string.
2. Deep nested FOR/QUIT structures (V1NST1/V1NST3) are represented as nested `MForStatement` bodies with postconditioned `MQuit`—codegen should preserve early-exit semantics.
3. External GOTO/DO chains (V1NSTE/V1NST3) resolve to `MCall` with `routine` set, confirming cross-routine linkage is available for future call graph analysis.

---

## Phase 33: MUGJ Validation Checklist - V1NUM1 to V1NX2

**Purpose**: Validate numeric literal edge cases and $NEXT traversal routines (Checklist 19/54).

**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1NUM1.m | 6 | 102 | ✅ Complete | Numeric literal tests - leading zeros; format controls as MFormatControl |
| V1NUM2.m | 5 | 80 | ✅ Complete | Numeric literal tests - trailing zeros, multiple minus signs |
| V1NUM3.m | 4 | 85 | ✅ Complete | Numeric literal tests - scientific notation |
| V1NUM4.m | 4 | 109 | ✅ Complete | String-to-numeric head extraction with unary +/- |
| V1NX.m | 3 | 4 | ✅ Complete | $NEXT driver - external routine calls |
| V1NX1.m | 8 | 73 | ✅ Complete | $NEXT tests; naked global SET targets fixed (T526) |
| V1NX2.m | 16 | 62 | ✅ Complete | $NEXT with GOTO patterns; label targets resolved |

### Tasks

- [x] T524 [BUG] Convert Write formatting tokens (Newl, Form, Tab, Backspace, etc.) to ASG expressions during `_analyze_WriteCommand` / `_build_expression_asg`.
   - **Fix Applied**: Added `MFormatControl` ASG class and `FormatControlType` enum in `src/m2py/asg/`. Added handler methods `_analyze_Newline`, `_analyze_FormFeed`, `_analyze_Tab`, `_analyze_CharCode` in `semantic_analyzer.py`.
   - **Result**: All format controls (!, #, ?n, *n) now converted to proper `MFormatControl` ASG objects with `FormatControlType` classification. 669 tests passing.
- [x] T525 [BUG] Normalize postconditioned Write control arguments (e.g., `W:$Y>55 #`) into concrete ASG literals instead of textX control nodes.
   - **Fix Applied**: Same fix as T524 - the analyze dispatch now routes all FormatControl textX types to dedicated handlers that create `MFormatControl` ASG nodes.
   - **Result**: Postconditioned writes like `W:$Y>55 #` now produce `MFormatControl(control_type=FORMFEED)` with proper postcondition expression.

### Outstanding Issues

- [X] T526 [BUG] Naked globals (`^(...)`) fail to parse as SET targets - grammar issue
   - **Root Cause**: `SingleTarget` rule in `commands.tx` allows `GlobalVariable | LocalVariable | Indirection` but does NOT include `NakedGlobal`. When parser encounters `S ^(1)=1`, it fails to match and silently drops the entire SET statement.
   - **Affected Files**: V1NX1.m line 37: `S ^V1(1)=1,^V1(200)=200,^(30,30)=3030,^(3,3)=33` - only first 2 assignments parsed
   - **Fix Applied**: 
     1. Added `NakedGlobal` to `SingleTarget` rule in `src/m2py/grammar/commands.tx` (placed before GlobalVariable due to ambiguous `^` prefix)
     2. Added `NakedGlobal` handling in `convert_to_variable()` in `src/m2py/analysis/command_parser.py`
     3. Added 6 unit tests for grammar and analysis levels
   - **Result**: SET statements with naked global targets now parse correctly with all assignments captured

### Observations for Code Generation

1. **MFormatControl** - New ASG type representing I/O format controls:
   - `control_type`: `FormatControlType.NEWLINE` (!), `FORMFEED` (#), `TAB` (?n), `CHARCODE` (*n)
   - `expression`: For TAB and CHARCODE, contains the column/character code expression
2. **$NEXT function** - V1NX1/V1NX2 test traversal with $NEXT($N) intrinsic; properly captured as MIntrinsicFunction
3. **Naked global references in expressions** - Used extensively in V1NX1/V1NX2 for testing; properly captured as MNakedGlobal in expressions like `$N(^(1))`
4. **Naked global references as SET targets** - ⚠️ **BUG**: Not currently parsed - see T526
5. **Numeric literal canonicalization** - V1NUM1-4 test leading/trailing zero removal and scientific notation; literal values captured with original precision
6. **Unary operators on strings** - V1NUM4 tests numeric interpretation (`+"123ABC"` → 123); captured as MUnaryOp with StringLiteral operand
7. **$Y special variable** - Used in EXAMINER postconditions (`W:$Y>55 #`); properly captured as SpecialVariable

---

## Phase 34: MUGJ Validation Checklist - V1OV to V1PC1

**Purpose**: Validate overlay GOTO, pattern matching, and post-conditional drivers (Checklist 20/54).
**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1OV.m | 23 | 101 | ✅ Complete | All GOTO targets resolved; offsets captured |
| V1OV1.m | 20 | 68 | ✅ Complete | EXAMINER backrefs resolved; offset GOTOs captured |
| V1PAT.m | 3 | 5 | ✅ Complete | Driver only (WRITE + DO) |
| V1PAT1.m | 10 | 72 | ✅ Complete | Pattern atom and count loops captured; MPatternMatch with subject/pattern |
| V1PAT2.m | 12 | 75 | ✅ Complete | Complex patterns with multipliers, indirection, negation |
| V1PC.m | 3 | 4 | ✅ Complete | Driver only (WRITE + DO) |
| V1PC1.m | 39 | 122 | ⚠️ Minor | Postconditioned GOTOs good; $TEXT function arg parsing issue |

### Findings

1. **Pattern Match Parsing (V1PAT1, V1PAT2)**: `MPatternMatch` correctly captures:
   - `subject`: The expression being matched
   - `pattern`: The pattern string (e.g., "1C", "5N", ".A.P")
   - `pattern_indirect`: For `?@X` indirect patterns
   - `operator`: `?` or `'?` (not match)

2. **V1OV GOTO Offsets**: All label+offset references (`G XYZ+0^V1OV1`) captured correctly with:
   - `MCall.offset` as `NumericLiteral` or `MBinaryOp`
   - Complex offset expressions (e.g., `G 691+A/9-11/19^V1OV`) preserved as expression trees

3. **V1PC1 $TEXT Function Issue**: Line `G:$T(V1PC1+300)="" ...` parses `$T(V1PC1+300)` incorrectly:
   - Expected: `$TEXT` with label reference argument `V1PC1+300`
   - Actual: `$T` with `LocalVariable(name='V1PC1')` - the `+300` offset is dropped
   - The `$TEXT` function expects a `labelref` argument (label+offset^routine), not an expression

4. **V1OV Multi-target GOTOs**: Lines like `G ^V1OV1,^V1OV1` correctly capture multiple MCall targets

5. **V1PC1 Postconditioned GOTOs**: Both command-level (`G:cond target`) and target-level (`G target:cond`) postconditions captured

### Tasks

- [X] T527 [CODEGEN NOTE] **VERIFIED 2025-12-24** - $TEXT parsing works correctly at ASG level.
  - `$T(LABEL+5)` parses as `IntrinsicFunction(name='T', args=[MBinaryOp(left=LocalVariable('LABEL'), op='+', right=NumericLiteral(5))])`
  - This is semantically correct for the ASG - the structure is captured.
  - **Code generation responsibility**: The codegen phase must recognize `$TEXT`/`$T` function calls and interpret the argument as a label reference (first identifier is label name, `+n` is offset), not as a variable expression.
  - This is documented in `docs/codegen/mumps_gotchas.md` under "$TEXT Function".

- [X] T528 [RESOLVED] V1PAT2 pattern parsing issues - previously noted bugs now passing (75 statements captured)

### Observations for Code Generation

1. **MPatternMatch** semantics:
   - Returns 1 (true) or 0 (false) in MUMPS
   - Pattern codes: C (control), N (numeric), P (punctuation), A (alpha), L (lower), U (upper), E (everything)
   - Multipliers: `0`, `1-9`, `.` (zero or more), `n.m` (range)
   - Python will need a pattern matcher implementation or regex translation

2. **Label+Offset References**:
   - `G label+n^routine` jumps to n lines after label
   - Python code gen must compute actual target or use a label registry

3. **$TEXT Function**:
   - Returns source text of line at label+offset
   - Rarely used in production code but important for meta-programming
   - May need stub implementation returning empty string

4. **GOTO Lists with Postconditions**:
   - `G target1:cond1,target2:cond2` - each target has own postcondition
   - Python: `if cond1: goto target1; elif cond2: goto target2`

---

## Phase 35: MUGJ Validation Checklist - V1PCA to V1PRGD2

**Purpose**: Validate postcondition-heavy drivers and preliminary GOTO/DO/QUIT behavior (Checklist 21/54).
**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1PCA.m | 29 | 152 | ⚠️ Issues | GOTO target postconditions/offsets dropped |
| V1PCB.m | 26 | 143 | ⚠️ Issues | DO target postconditions/offsets dropped |
| V1PO.m | 8 | 62 | ⚠️ Needs spot-check | Operator-precedence expressions not yet inspected in ASG |
| V1PRFOR.m | 5 | 35 | ✅ | FOR params captured; classification not reviewed here |
| V1PRGD.m | 11 | 77 | ⚠️ Minor | Statements after QUIT not marked unreachable |
| V1PRGD1.m | 2 | 12 | ⚠️ Minor | Statements after QUIT not marked unreachable |
| V1PRGD2.m | 1 | 2 | ⚠️ Minor | Implicit QUIT missing (label ends with fallthrough) |

### Findings

1. **GOTO target postconditions and offsets lost (V1PCA)**
   - Examples: [tests/functional/mugj/inref/V1PCA.m#L44-L48], [tests/functional/mugj/inref/V1PCA.m#L50-L66]
   - MCalls created from GOTO lists do not retain target-level postconditions (`:expr`) or label offsets (`+n`). External targets (label^routine) are flattened into names without per-target metadata, preventing correct branching order.
2. **DO target postconditions and offsets lost (V1PCB)**
   - Examples: [tests/functional/mugj/inref/V1PCB.m#L11-L20], [tests/functional/mugj/inref/V1PCB.m#L22-L35], [tests/functional/mugj/inref/V1PCB.m#L39-L71]
   - DO lists collapse into a single MDoStatement without preserving per-target postconditions or offsets (`+n`). Offset DO calls (`BYTE+2`, `OS+2^V1PC1`, etc.) are emitted as plain CALL(BYTE) / CALL(^V1PC1OS) with no offset data.
3. **Unreachable code after QUIT not flagged (V1PRGD/V1PRGD1)**
   - Examples: [tests/functional/mugj/inref/V1PRGD.m#L34-L37], [tests/functional/mugj/inref/V1PRGD1.m#L3-L6]
   - Statements following explicit QUIT remain in bodies with no `is_unreachable` tagging, making downstream control-flow analysis/codegen harder.
4. **Implicit QUIT missing for fallthrough labels (V1PRGD2)**
   - Example: [tests/functional/mugj/inref/V1PRGD2.m#L1-L4]
   - Routine ends with SET/WRITE and comment; ASG stops without a terminating MQuitStatement, so callers cannot tell the label exits.

### Tasks

- [X] T529 [FALSE POSITIVE] GOTO target postconditions and offsets ARE captured correctly.
  - **Verified**: `MCall.offset` and `MCall.postcondition` are populated for GOTO targets.
  - The validate_asg.py compact display just wasn't showing these fields.
  - Test: V1PCA label 838 shows BUG+2 with postcondition MBinaryOp and TABLE+1 with postcondition IntrinsicFunction.
- [X] T530 [FALSE POSITIVE] DO target postconditions and offsets ARE captured correctly.
  - **Verified**: `MCall.offset` and `MCall.postcondition` are populated for DO targets.
  - Test: V1PCB label 843 shows BYTE+2:$D(A) and BYTE+1:'$D(A) with proper offsets and postconditions.
- [X] T531 [BUG] **VERIFIED FIXED 2025-12-24** Mark statements after unconditional QUIT as unreachable.
  - During semantic analysis, flag statements after QUIT/QUIT-return as `is_unreachable=True` for accurate CFG/codegen.
  - The `detect_unreachable_code()` function exists but is never called/integrated into the ASG.
  - Need to add post-processing pass to mark statements in label bodies.
- [X] T532 [ENHANCEMENT] **VERIFIED IMPLEMENTED 2025-12-24** Add `has_explicit_exit` flag to MLabel.
  - Instead of synthesizing implicit QUIT, track whether label ends with explicit exit (QUIT/GOTO/HALT).
  - This is informational for code generation; MUMPS semantics already imply fallthrough returns.

---

## Phase 36: MUGJ Validation Checklist - V1PRGD3 to V1READA1

**Purpose**: Validate preliminary GOTO/DO/QUIT label tests and READ command drivers (Checklist 22/54).
**Validation Date**: 2025-12-21

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1PRGD3.m | 3 | 9 | ⚠️ Minor | Statements after unconditional GOTO remain reachable (extends unreachable-code issue)
| V1PRIE.m | 4 | 36 | ✅ | IF/ELSE chains captured; nested ELSE blocks preserved
| V1PRSET.m | 7 | 36 | ✅ | SET/KILL/WRITE sequences captured; format controls normalized
| V1RANDA.m | 24 | 66 | ✅ | $RANDOM loop tests captured; DO EXT/FIND targets resolved
| V1RANDB.m | 14 | 70 | ✅ | $RANDOM gap/frequency tests captured; nested DO/QUIT preserved
| V1READA.m | 3 | 5 | ✅ | Driver DO calls to ^V1READA1/^V1READA2 resolved
| V1READA1.m | 11 | 72 | ⚠️ Issues | READ arguments still contain raw textX format nodes (Newl/Tab) instead of ASG expressions

### Findings

1. **READ arguments not normalized to ASG (V1READA1 labels 749-756)**
    - `MReadStatement.arguments` contain `textx:commands.Newl`/`Tab` objects rather than `MFormatControl`/expression nodes.
    - Root cause: `_analyze_ReadCommand` passes textX command nodes through without routing to `_build_expression_asg` or format-control handlers.
    - Impact: Codegen cannot interpret READ format controls, timeouts, or prompts consistently.

2. **Unreachable code after unconditional GOTO not flagged (V1PRGD3 line 4)**
    - Line `S VCOMP=VCOMP_3 G B` is followed by additional SET/QUIT statements that remain marked reachable.
    - Existing unreachable detection (T531) covers QUIT-only; needs extension to unconditional transfers like GOTO.

### Tasks

- [X] T533 [BUG] Normalize READ arguments to ASG format controls/expressions.
  - **Root Cause**: `_analyze_ReadCommand` checked for format control class names (`Newline`, `FormFeed`, `Tab`) but appended raw textX nodes directly instead of calling `self.analyze()` to convert them to `MFormatControl` ASG nodes.
  - **Fix Applied**: Changed line 537-538 in `semantic_analyzer.py` to call `self.analyze(arg_value, stmt)` for format controls, routing through `_analyze_Newline`/`_analyze_FormFeed`/`_analyze_Tab`/`_analyze_CharCode` handlers.
  - **Test Added**: `test_read_format_controls_as_asg_nodes` in `tests/unit/test_grammar.py` verifies READ format controls are proper `MFormatControl` ASG nodes.
  - **Result**: 709 tests passing.

- [X] T534 [FALSE POSITIVE] Unreachable code after unconditional GOTO IS already detected.
  - **Verified**: V1PRGD3.m statements [4] and [5] after unconditional GOTO are already marked `is_unreachable=True`.
  - The existing unreachable code detection in `detect_unreachable_code()` handles both QUIT and GOTO transfers correctly.

---

## Phase 37: MUGJ Validation Checklist - V1READA2 to V1SEQ1

**Purpose**: Validate READ timeout/indirection behaviors and execution-sequence routines (Checklist 23/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1READA2.m | 7 | 62 | ⚠️ Issues | `*lvn` reads parsed as plain variables; char-read intent lost |
| V1READB.m | 3 | 4 | ✅ | Driver DOs to ^V1READB1/^V1READB2 captured |
| V1READB1.m | 6 | 71 | ⚠️ Issues | READ timeouts (`:0`, `:-1`, `:100`, `:10`) dropped; char-read semantics not captured |
| V1READB2.m | 12 | 81 | ⚠️ Issues | READ timeouts (`:100`) discarded; read-level indirection kept as raw targets |
| V1RN.m | 8 | 52 | ✅ | Routine-name DO lists captured (single and multi-target DO) |
| V1SEQ.m | 29 | 134 | ✅ | Execution sequence flows (DO/GOTO/XECUTE) captured and resolved |
| V1SEQ1.m | 10 | 22 | ✅ | Helper labels and cross-routine DO/GOTO captured |

### Findings

1. **READ timeouts are dropped (V1READB1, V1READB2)**
    - `ReadTargetWithTimeout` nodes append only the target; the `timeout` expression is ignored so `$TEST` behavior for time-limited reads is lost. Seen in [tests/functional/mugj/inref/V1READB1.m#L9-L39](tests/functional/mugj/inref/V1READB1.m#L9-L39) and [tests/functional/mugj/inref/V1READB2.m#L46-L56](tests/functional/mugj/inref/V1READB2.m#L46-L56).
    - Root cause: `_analyze_ReadCommand` appends the analyzed `target` but never stores `timeout` from `ReadTargetWithTimeout` ([src/m2py/analysis/semantic_analyzer.py#L526-L536](src/m2py/analysis/semantic_analyzer.py#L526-L536)).

2. **Char READ (`*lvn`) semantics lost (V1READA2, V1READB1)**
    - `*` arguments are emitted as plain `MVariable` entries in `MReadStatement.arguments`, so codegen cannot distinguish char-by-char reads from line reads (affects tests 757-758, 760/763/765). Examples in [tests/functional/mugj/inref/V1READA2.m#L11-L44](tests/functional/mugj/inref/V1READA2.m#L11-L44) and [tests/functional/mugj/inref/V1READB1.m#L9-L30](tests/functional/mugj/inref/V1READB1.m#L9-L30).
    - Root cause: `_analyze_ReadCommand` unwraps `CharRead` into `LocalVariable` with no flag or distinct ASG node ([src/m2py/analysis/semantic_analyzer.py#L526-L536](src/m2py/analysis/semantic_analyzer.py#L526-L536)).

### Tasks

- [x] T535 [BUG] Preserve READ timeouts from `ReadTargetWithTimeout`.
   - Store the analyzed `timeout` expression alongside the target (new field on `MReadArgument`/`MReadTarget` or structured tuple) so `$TEST` and blocking behavior are preserved for `:0`, `:-1`, `:10`, `:100` cases.
   - Update semantic analyzer and any ASG classes needed; add regression tests covering V1READB1 and V1READB2 timeout scenarios.

- [x] T536 [BUG] Represent char-read (`*lvn`) distinctly in ASG.
   - Introduce an ASG wrapper or flag so char reads are not flattened into normal variable targets.
   - Ensure semantic analyzer preserves the distinction and add tests for single-character reads in V1READA2/V1READB1.

---

## Phase 38: MUGJ Validation Checklist - V1SET to V1UO2A

**Purpose**: Validate SET command variations, special variables ($HOROLOG, $STORAGE), and unary operator tests (Checklist 24/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1SET.m | 10 | 120 | ⚠️ Issues | Multi-assignment `(A,B,C)=1` stored as list target, not expanded |
| V1SVH.m | 7 | 37 | ✅ | Pattern match and $HOROLOG captured correctly |
| V1SVS.m | 6 | 51 | ✅ | $STORAGE tests and argumentless KILL captured |
| V1UO.m | 11 | 20 | ✅ | Simple driver pattern with external routine calls |
| V1UO1A.m | 6 | 65 | ⚠️ Issues | $H abbreviation misclassified as IntrinsicFunction |
| V1UO1B.m | 6 | 111 | ✅ | Unary plus tests captured |
| V1UO2A.m | 6 | 65 | ⚠️ Issues | $T abbreviation misclassified as IntrinsicFunction |

### Findings

1. **Multi-assignment SET stores target as list instead of expanding (V1SET labels 785, 786)**
   - `S (A,B,C,D,E,F,^V1,^V1A)=1` creates a single `MAssignment` with `target` as a list of 8 variables.
   - Per data-model.md, each `MAssignment` should have a single target; the semantic analyzer should expand this into 8 separate assignments with the same value.
   - Impact: Code generation must handle list targets specially or risk incorrect semantics.
   - Root cause: `_analyze_SetCommand` in `semantic_analyzer.py` lines 467-468 stores `ParenTargets.targets` as a list in `MAssignment.target` instead of expanding.

2. **Special variable abbreviations misclassified as IntrinsicFunction**
   - `$H` (abbreviation of `$HOROLOG`) → `IntrinsicFunction` ❌ (should be `SpecialVariable`)
   - `$S` (abbreviation of `$STORAGE` or `$SELECT`) → `IntrinsicFunction` ❌
   - `$T` (abbreviation of `$TEST`) → `IntrinsicFunction` ❌
   - Full names work correctly: `$HOROLOG`, `$TEST`, `$Y` → `SpecialVariable` ✅
   - Root cause: The parser or textX grammar doesn't recognize single-letter abbreviations as special variables.
   - Impact: Code generation may call non-existent functions instead of accessing special variable values.

3. **Naked globals correctly tracked**
   - `^(2)` (naked global) → `NakedGlobal` with `requires_runtime_tracking=True` ✅
   - Subscripts captured correctly.

4. **Pattern match correctly captured**
   - `$HOROLOG?1N.N` → `MPatternMatch` with `subject=SpecialVariable(HOROLOG)`, `pattern="1N.N"` ✅

### Tasks

- [x] T537 [BUG] Expand multi-assignment SET `(A,B,C)=value` into separate MAssignment objects. ✅
   - Modified `_analyze_SetCommand` in `semantic_analyzer.py` to iterate over `ParenTargets.targets` and create one `MAssignment` per target, all with the same value expression.
   - Added tests: `test_set_parenthesized_multi_target_expansion`, `test_set_parenthesized_with_globals`, `test_set_parenthesized_mixed_with_regular`.
   - Location: [src/m2py/analysis/semantic_analyzer.py#L466-L497](src/m2py/analysis/semantic_analyzer.py#L466-L497)

- [x] T538 [BUG] Recognize abbreviated special variables ($H, $S, $T, $J, $I, etc.) as SpecialVariable. ✅
   - Updated `SVARNAME` regex in `expressions.tx` to include abbreviations: D, H, I, J, K, P, Q, R, S, T, X, Y, EC, ES, ET, ST, SY, ZL.
   - Reordered grammar: `IntrinsicFunction` (with required args) → `SpecialVariable` → `IntrinsicFunctionNoArgs` (catch-all for $ZVersion etc.).
   - Added `IntrinsicFunctionNoArgs` textX class for unknown $ items like `$ZVersion`.
   - Added tests: `test_abbreviated_horolog`, `test_abbreviated_storage`, `test_abbreviated_test`, `test_abbreviated_job`, `test_abbreviated_io`, `test_abbreviated_device`, `test_select_function_still_works`.
   - Location: [src/m2py/grammar/expressions.tx#L281-L286](src/m2py/grammar/expressions.tx#L281-L286)

### Code Generation Considerations (Documented)

1. **Naked globals require runtime context tracking** - The ASG correctly identifies them but code generation needs to track the "last referenced global" across statements.

2. **MUMPS numeric coercion rules** - Unary operators `+` and `-` follow specific string-to-number rules that must be replicated in Python runtime.

---

## Phase 39: MUGJ Validation Checklist - V1WR to V4444 ✅ COMPLETE

**Purpose**: Validate WRITE command character output and XECUTE nested command execution (Checklist 26/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V1WR.m | 4 | 28 | ✅ | All character output tests parsed correctly |
| V1XECA.m | 2 | 2 | ✅ | Simple driver for XECUTE test suites |
| V1XECA1.m | 14 | 90 | ✅ | XECUTE single/multi argument, postconditions, indirection |
| V1XECA2.m | 14 | 90 | ✅ | XECUTE with GOTO, FOR, DO, QUIT, nested XECUTE |
| V1XECAE.m | 3 | 5 | ✅ | External routine called by V1XECA2 tests |
| V1XECB.m | 17 | 74 | ✅ | XECUTE 2-level nesting with all control flow commands |
| V4444.m | 1 | 2 | ✅ | Simple external routine with 4-digit label name |

### Findings

**ALL FILES PARSE 100% CORRECTLY** ✅

1. **V1WR.m - WRITE character output (802-804, END)**
   - All alphabetic (upper/lower), digit, and punctuation tests captured correctly
   - WRITE arguments properly structured for both abbreviated `W` and full `WRITE` keywords
   - Postconditions not present in this file (visual test file)
   - ASG captures: 28 statements (27 WRITE, 1 SET, 1 DO, 1 QUIT, 1 KILL)

2. **V1XECA.m - Simple XECUTE driver**
   - Minimal driver that calls two external test routines
   - Labels: V1XECA1, V1XECA2
   - Each label does a WRITE followed by external routine call (`D ^V1XECA1`, `D ^V1XECA2`)
   - All external references marked `is_resolved=False` (correct behavior)

3. **V1XECA1.m - XECUTE basic tests (805-809)**
   - **Single argument XECUTE**: `X "S VCOMP=1"` → `MXecuteStatement` with 1 string argument ✅
   - **Argument list**: `X "S A=2","SET VCOMP=A"` → 2 string arguments ✅
   - **Expression arguments**: `X X_",VCOMP=A_0"` → concatenation operator captured ✅
   - **Postconditions on arguments**: `X:P=1 "S VCOMP=""#""":P=0,"S P=2":P=1` → multiple arguments with postconditions ✅
   - **Indirection in postconditions**: `X:@Q=3 R_":P="_(10\3_" ")` → indirection and operators parsed ✅
   - **Postcondition on command**: `XECUTE:P=1 "S VCOMP=""A"""` → command-level postcondition ✅
   - External labels (A, B, C, D, E) for subroutine tests all captured

4. **V1XECA2.m - XECUTE with control flow (810-815)**
   - **Argument indirection**: `X @X` where `X="Y"` → indirection captured ✅
   - **GOTO in XECUTE**: `X "G B","S VCOMP=VCOMP_7"` → GOTO command string literal ✅
   - **External GOTO**: `X "S VCOMP=VCOMP_10 G ^V1XECAE"` → external jump captured ✅
   - **FOR in XECUTE**: `X "F I=1:1:3 S VCOMP=VCOMP_I"` → FOR loop string ✅
   - **DO in XECUTE**: `X "D A","S VCOMP=VCOMP_5"` → DO command string ✅
   - **QUIT in XECUTE**: `X "S VCOMP=8 Q S VCOMP=VCOMP_""ERROR""` → QUIT string ✅
   - **Nested XECUTE (2-level)**: `X "X ""S A=1""","S VCOMP=A"` → nested double-quote escaping ✅
   - **Nested XECUTE (3-level)**: `X "X ""X """"S A=2"""""",""S VCOMP=A"""` → triple-level nesting ✅
   - All subroutine labels (A, B, C, D, E) resolved correctly to internal labels

5. **V1XECAE.m - External routine for V1XECA2**
   - Three labels: V1XECAE, EXTERN, 13
   - Label "13" is numeric (validates numeric label support) ✅
   - Simple SET/QUIT pairs for each label
   - Called by V1XECA2 tests with patterns: `G ^V1XECAE`, `D EXTERN^V1XECAE`, `D 13^V1XECAE`

6. **V1XECB.m - XECUTE 2-level nesting (816-821)**
   - **Nested DO**: `X "S VCOMP=1 X ""S VCOMP=VCOMP_2 D F S VCOMP=VCOMP_4"" S VCOMP=VCOMP_5"` ✅
   - **Nested GOTO**: `X "S VCOMP=7 X ""S VCOMP=VCOMP_8 G G""..."` → GOTO to label G ✅
   - **Nested QUIT**: `X "S VCOMP=12 X ""S VCOMP=VCOMP_13 Q S VCOMP=..."""` ✅
   - **Nested FOR with DO**: `X "S V=V_6 X ""F I=7:1:9 D H Q:I>7"" S V=V_9"` ✅
   - **Nested FOR with GOTO**: `X "S V=V_11 X ""F I=12:1:14 G I Q:I>12"" S V=V_13"` ✅
   - **KILL self-reference**: `A="S VCOMP=$D(A) K A S VCOMP=VCOMP_$D(A)"` X A → KILL of XECUTE source var ✅
   - **SET self-reference**: `A="S A=$J(1,10) S VCOMP=A"` X A → SET of XECUTE source var ✅
   - Postconditions on nested XECUTE: `X:0 "S V=V_"" ERROR """:1` → compound postconditions ✅
   - Helper labels (F, G, H, I, J, K, L, M) all resolved correctly

7. **V4444.m - 4-digit label name**
   - Label "V4444" validates that 4+ digit labels work (not just 1-3)
   - Simple SET and QUIT
   - Called by V1RN.m with pattern: `D ^V4444`

### ASG Structure Validation

All files show **perfect ASG capture**:

✅ **Labels**: All label names captured correctly (including numeric "13" and 4-digit "V4444")
✅ **Commands**: SET, WRITE, XECUTE, DO, QUIT, KILL all captured
✅ **Expressions**: String literals (with nested quotes), concatenation operators, indirection, intrinsic functions ($D, $J, $Y)
✅ **Postconditions**: Both command-level and argument-level postconditions preserved
✅ **Control flow**: IF/ELSE, FOR loops within XECUTE strings (captured as literal strings, which is correct)
✅ **String escaping**: Nested double-quotes properly captured (e.g., `""""S A=2""""` in 3-level XECUTE)
✅ **External references**: DO ^routine and label^routine patterns captured with `is_resolved=False`
✅ **Label resolution**: All internal DO/GOTO targets resolved to correct `MLabel` objects with populated `callers` lists

### Code Generation Considerations

**Key insights for Python code generation phase**:

1. **XECUTE requires runtime evaluation** - The ASG correctly marks `MXecuteStatement` with `requires_runtime_eval=True`. The string arguments contain MUMPS code that must be parsed and executed at runtime. This cannot be statically translated.

2. **Nested XECUTE depth tracking** - The string literal nesting (double-quotes within double-quotes) shows the complexity of 2-3 level XECUTE nesting. Code generation must:
   - Parse the XECUTE string at runtime
   - Handle escaped quotes correctly (`""` → `"`)
   - Maintain execution context across nesting levels

3. **Variable scope in XECUTE** - Tests 820-821 show XECUTE can modify or KILL its own source variable. Python code generation must ensure:
   - XECUTE string evaluation has access to the current variable scope
   - Changes to variables persist after XECUTE completes
   - KILL of the XECUTE source variable works correctly

4. **Control flow in XECUTE strings** - GOTO, FOR, DO, QUIT commands within XECUTE strings affect the calling context:
   - `X "G label"` → must jump to `label` in the current routine
   - `X "Q"` → must return from the current subroutine
   - `X "D subroutine"` → must call local or external subroutine
   - These require maintaining a unified control flow context

5. **Postconditions on XECUTE** - Both `X:condition` and `X arg1:cond1,arg2:cond2` patterns must be evaluated:
   - Command postcondition (`X:P=1`) prevents entire XECUTE if false
   - Argument postconditions (`X "code1":cond1,"code2":cond2`) skip individual arguments selectively

6. **External GOTO via XECUTE** - `X "G ^routine"` must support routine overlay (loading and jumping to external routine). This is a challenging feature that may require special runtime handling.

7. **WRITE character output** - V1WR shows every ASCII character output. Code generation must preserve exact character output semantics (no Unicode normalization issues).

### No Issues Found ✅

**All 7 files parse correctly with complete ASG structure**. No bugs, missing features, or semantic gaps identified. The XECUTE implementation correctly:
- Captures all argument patterns (single, multiple, expressions, indirection)
- Preserves postconditions at both command and argument levels
- Marks statements for runtime evaluation
- Maintains proper label resolution for control flow targets

**This validates that the textX grammar and semantic analyzer handle the most complex MUMPS features correctly.**

---

## Phase 40: MUGJ Validation Checklist - V7777777 to VABCDEF ✅ COMPLETE

**Purpose**: Validate label-name length handling (2–7 chars/digits) and end-of-label exit behavior (Checklist 27/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| V7777777.m | 1 | 2 | ✅ | 7-digit label with SET+QUIT captured |
| VA.m | 1 | 2 | ✅ | 2-char label captured |
| VAB.m | 1 | 2 | ✅ | 3-char label captured |
| VABC.m | 1 | 1 | ✅ | No explicit QUIT; `has_explicit_exit=False` correctly identifies this |
| VABCD.m | 1 | 2 | ✅ | 5-char label captured |
| VABCDE.m | 1 | 2 | ✅ | 6-char label captured |
| VABCDEF.m | 1 | 2 | ✅ | 7-char label captured |

### Findings

1. **Implicit QUIT correctly handled via `has_explicit_exit` property (VABC)** ✅
    - Source ends with `S VCOMP=VCOMP_"VABC "` and no `Q`. The ASG correctly captures only `MSetStatement`.
    - The existing `MLabel.has_explicit_exit` property returns `False` for this label, enabling code generation to handle implicit returns.
    - **This is correct behavior**: The ASG accurately represents the source, and Python's implicit return semantics match MUMPS.
    - MUGJ tests V1DO1.m, V1PRGD.m, V1PRGD2.m explicitly document `;IMPLICIT QUIT` as intentional.

### Tasks

- [x] T539 [NOT A BUG] Implicit QUIT handling is already correct.
   - `MLabel.has_explicit_exit` property (in `src/m2py/asg/elements.py`) correctly identifies labels without explicit exits.
   - Python code generation can use this property to emit explicit `return` statements if needed.
   - No synthetic `MQuitStatement` nodes should be added - the ASG must accurately reflect source code structure.
   - Verified: VABC.m has `has_explicit_exit=False`, VA.m has `has_explicit_exit=True`.

---

## Phase 41: MUGJ Validation Checklist - VABCDEFG to VV1DOC10

**Purpose**: Validate long-label drivers and the Part-I documentation/report routines (Checklist 28/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VABCDEFG.m | 1 | 2 | ✅ | 8-character label; simple SET+QUIT for name-length test |
| VABCDEFH.m | 1 | 2 | ✅ | 8-character label; simple SET+QUIT for name-length test |
| VREPORT.m | 9 | 102 | ✅ | Report writer; page-break checks via $Y and TAB/FORMFEED captured |
| VV1.m | 63 | 126 | ✅ | Part-I driver; DO ^V1* external calls resolved as routine targets |
| VV1DOC.m | 80 | 82 | ✅ | DOC driver; CRT/PRINTER routing via MGoto START; bulk DO ^VV1DOC* calls |
| VV1DOC1.m | 2 | 4 | ✅ | Documentation text emitter; FOR loop walks $TEXT; quits on empty line |
| VV1DOC10.m | 2 | 4 | ✅ | Documentation text emitter; same $TEXT loop pattern as VV1DOC1 |

### Findings

- **No new issues**: ASG aligns with source for all files. External DO/GOTO references remain unresolved by design for cross-routine calls.
- **Codegen notes**: VREPORT relies on format controls (TAB, FORMFEED) and chained ELSE blocks for report rows; VV1/VV1DOC are driver routines dominated by DO ^routine calls, so runtime must handle external routine loading.

---

## Phase 42: MUGJ Validation Checklist - VV1DOC11 to VV1DOC17

**Purpose**: Validate Part-I documentation emitters driven by $TEXT loops (Checklist 29/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VV1DOC11.m | 2 | 4 | ✅ | QUIT postcondition correctly captured; validate_asg display issue |
| VV1DOC12.m | 2 | 4 | ✅ | Same pattern as VV1DOC11 |
| VV1DOC13.m | 2 | 4 | ✅ | Same pattern as VV1DOC11 |
| VV1DOC14.m | 2 | 4 | ✅ | Same pattern as VV1DOC11 |
| VV1DOC15.m | 2 | 4 | ✅ | Same pattern as VV1DOC11 |
| VV1DOC16.m | 2 | 4 | ✅ | Same pattern as VV1DOC11 |
| VV1DOC17.m | 2 | 4 | ✅ | Same pattern as VV1DOC11 |

### Findings

1. **QUIT postcondition IS correctly captured** ✅
    - Source pattern: `F I=1:1 S A=$T(TEX+I) Q:A=""  W !,$P(A," ;",2,99)` (e.g., [tests/functional/mugj/inref/VV1DOC11.m#L5](tests/functional/mugj/inref/VV1DOC11.m#L5)).
    - ASG correctly captures `MQuitStatement.postcondition = MBinaryOp(operator='=', left=LocalVariable('A'), right=StringLiteral(''))`.
    - **This was a false positive** - the `validate_asg.py` compact display wasn't showing the postcondition field for statements inside FOR bodies.

2. **$TEXT content not preserved for documentation routines** (informational)
    - Labels like `TEX` consist solely of comment lines whose text is retrieved via `$TEXT`. The ASG drops these lines entirely (label has zero statements).
    - **This is correct ASG behavior** - comments are not executable statements.
    - **For code generation**: The `$TEXT` intrinsic function requires access to raw source lines at runtime. This is a runtime concern, not an ASG parsing concern.
    - **Recommendation**: Code generation should provide a `$TEXT` implementation that reads from the original source file or a source-line cache, not from the ASG.

### Tasks

- [X] T540 [FALSE POSITIVE] QUIT postconditions ARE correctly captured.
   - **Verified**: `MQuitStatement.postcondition` contains `MBinaryOp(operator='=', left=LocalVariable('A'), right=StringLiteral(''))` for `Q:A=""`.
   - The `validate_asg.py` display issue was cosmetic (not showing postconditions for nested statements).

- [X] T541 [NOT A BUG] $TEXT source access is a runtime concern.
   - The ASG correctly represents parsed structure; it is not responsible for preserving comment text.
   - Code generation phase should implement `$TEXT` by reading the original source file or providing a source cache.
   - No changes needed to ASG or parser.

---

## Phase 43: VistA Codebase Support Enhancements

**Purpose**: Enhance ASG with features needed for transpiling the VistA-M codebase (33,951 files).

**Analysis Summary** (from VistA-M codebase scan):
| Feature | VistA Usage | MUGJ Usage | Priority |
|---------|-------------|------------|----------|
| Indirection (@) | 86,145 | ~500 | 🔴 Critical |
| Pattern Match (?) | 24,478 | ~200 | 🔴 Critical |
| XECUTE | 24,417 | 109 | 🔴 Critical |
| $TEXT | 12,792 | 184 | ✅ Done |
| LOCK | 7,245 | ~50 | 🟡 High |
| $Z* variables | 1,557 | 0 | 🟠 Medium |
| $ECODE/$ETRAP | 1,300+ | 0 | 🟠 Medium |
| Transactions | 201 | 0 | 🟢 Low |
| $STACK(,MCODE) | 43 | 0 | 🟢 Low |

### Phase 43a: $TEXT Cross-Routine Support

**Goal**: Enable $TEXT(label^routine) to access other routine's source lines.

- [X] T542 Add IndirectionType enum to src/m2py/asg/enums.py (NAME, SUBSCRIPT, ARGUMENT, PATTERN)
- [X] T543 Add indirection_type field to MIndirection in src/m2py/asg/expressions.py
- [X] T544 Add tests for IndirectionType classification in tests/unit/test_expressions.py
- [X] T545 [P] Add can_resolve_statically and resolved_name fields to MIndirection

### Phase 43b: Pattern Match Enhancement

**Goal**: Pre-compile MUMPS patterns to Python regex for efficient code generation.

- [X] T546 Create pattern_compiler.py module in src/m2py/analysis/
- [X] T547 Implement compile_pattern_to_regex() function supporting standard pattern codes (A, N, E, P, L, U, C)
- [X] T548 Add compiled_regex field to MPatternMatch in src/m2py/asg/expressions.py
- [X] T549 Integrate pattern compilation into semantic analyzer
- [X] T550 Add comprehensive tests for pattern compilation in tests/unit/test_pattern_compiler.py

### Phase 43c: XECUTE Static Analysis

**Goal**: Identify constant XECUTE strings for potential pre-compilation.

- [X] T551 Add is_constant and constant_value fields to MXecuteStatement in src/m2py/asg/statements.py
- [X] T552 Implement XECUTE constant detection in semantic analyzer
- [X] T553 Add tests for XECUTE constant detection in tests/unit/test_semantic_analyzer.py

### Phase 43d: Indirection Classification

**Goal**: Classify indirection types to enable targeted code generation strategies.

- [X] T554 Implement indirection type classification in semantic analyzer
- [X] T555 Attempt static resolution for constant indirection (e.g., @"VARNAME")
- [X] T556 Add tests for indirection classification in tests/unit/test_semantic_analyzer.py

### Phase 43 Implementation Notes (2025-12-22)

**Files Modified:**
- `src/m2py/asg/enums.py` - Added `IndirectionType` enum (NAME, SUBSCRIPT, ARGUMENT, PATTERN, UNKNOWN)
- `src/m2py/asg/expressions.py` - Updated `MIndirection.indirection_type` to use enum; added `compiled_regex` to `MPatternMatch`
- `src/m2py/asg/statements.py` - Added `is_constant` and `constant_values` fields to `MXecuteStatement`
- `src/m2py/analysis/semantic_analyzer.py` - Integrated pattern compilation, XECUTE constant detection, indirection classification
- `src/m2py/analysis/pattern_compiler.py` - **New module** for MUMPS pattern to Python regex compilation

**New Test Files:**
- `tests/unit/test_pattern_compiler.py` - 26 tests for pattern compilation

**Pattern Compiler Features:**
- All standard pattern codes: A (alpha), C (control), E (everything), L (lowercase), N (numeric), P (punctuation), U (uppercase)
- Multi-letter patcodes (e.g., `AN` for alphanumeric = union of A and N)
- Repeat counts: exact (`3N`), range (`2.4N`), at-least (`1.N`), at-most (`.3N`), indefinite (`.N`)
- String literals with escaped quotes
- Alternation patterns

**Test Results:**
- 693 unit tests pass (added 35 new tests)
- 81 MUGJ integration tests pass

---

## Phase 44: MUGJ Validation Checklist - VV1DOC18 to VV1DOC23

**Purpose**: Validate Part-I documentation emitters VV1DOC18–VV1DOC23 (Checklist 30/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VV1DOC18.m | 2 | 4 | ✅ | IF IO="PRINTER" guard, WRITE, bounded FOR over $TEXT, QUIT postcondition captured |
| VV1DOC19.m | 2 | 4 | ✅ | Same documentation emitter pattern; A=$TEXT(TEX+I) SET captured |
| VV1DOC2.m | 2 | 4 | ✅ | Same pattern; QUIT postcondition `A=""` present in ASG |
| VV1DOC20.m | 2 | 4 | ✅ | Same pattern; FOR body SET/QUIT/WRITE captured |
| VV1DOC21.m | 2 | 4 | ✅ | Same pattern; TEX label contains only comments (no statements) |
| VV1DOC22.m | 2 | 4 | ✅ | Same pattern; bounded FOR parameter start=1 step=1 |
| VV1DOC23.m | 2 | 4 | ✅ | Same pattern; WRITE arguments include line break and $PIECE expression |

### Findings

- QUIT postconditions (`Q:A=""`) inside the FOR bodies are correctly captured as `MQuitStatement.postcondition` binary comparisons.
- FOR loops are classified as bounded with start=1, step=1; body statements include the SET of `A=$TEXT(TEX+I)` and the trailing WRITE arguments (`!` and `$PIECE`).
- TEX labels intentionally contain only comment lines; ASG omits them, which is expected for $TEXT-driven emitters. $TEXT runtime access remains a codegen/runtime concern, not an ASG issue.

### Tasks

- [x] T557 [Validation] VV1DOC18–VV1DOC23 ASG verified; no parser changes required.

---

## Phase 45: MUGJ Validation Checklist - VV1DOC24 to VV1DOC29

**Purpose**: Validate Part-I documentation emitters VV1DOC24–VV1DOC29 (Checklist 31/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VV1DOC24.m | 2 | 4 | ✅ | IF IO="PRINTER" guard, WRITE, bounded FOR over $TEXT, QUIT postcondition captured |
| VV1DOC25.m | 2 | 4 | ✅ | Same documentation emitter pattern; A=$TEXT(TEX+I) SET captured |
| VV1DOC26.m | 2 | 4 | ✅ | Same pattern; QUIT postcondition `A=""` present in ASG |
| VV1DOC27.m | 2 | 4 | ✅ | Same pattern; FOR body SET/QUIT/WRITE captured |
| VV1DOC28.m | 2 | 4 | ✅ | Same pattern; TEX label contains only comments (no statements) |
| VV1DOC29.m | 2 | 4 | ✅ | Same pattern; bounded FOR parameter start=1 step=1 |

### Findings

- All files follow identical structure to VV1DOC18-23 series
- QUIT postconditions (`Q:A=""`) inside the FOR bodies are correctly captured as `MQuitStatement.postcondition` binary comparisons
- FOR loops are classified as bounded with start=1, step=1; body statements include the SET of `A=$TEXT(TEX+I)` and the trailing WRITE arguments
- TEX labels intentionally contain only comment lines documenting test cases; ASG omits them (expected behavior)
- These files document binary operator validation tests (string identity, not-identical, contains, etc.)

### Tasks

- [x] T558 [Validation] VV1DOC24–VV1DOC29 ASG verified; no parser changes required.

---

## Phase 46: MUGJ Validation Checklist - VV1DOC30 to VV1DOC36

**Purpose**: Validate Part-I documentation emitters VV1DOC30–VV1DOC36 (Checklist 32/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VV1DOC30.m | 2 | 4 | ✅ | IF IO="PRINTER" guard, WRITE, bounded FOR over $TEXT, QUIT postcondition captured |
| VV1DOC31.m | 2 | 4 | ✅ | Same documentation emitter pattern; A=$TEXT(TEX+I) SET captured |
| VV1DOC32.m | 2 | 4 | ✅ | Same pattern; QUIT postcondition `A=""` present in ASG |
| VV1DOC33.m | 2 | 4 | ✅ | Same pattern; FOR body SET/QUIT/WRITE captured |
| VV1DOC34.m | 2 | 4 | ✅ | Same pattern; TEX label contains only comments (no statements) |
| VV1DOC35.m | 2 | 4 | ✅ | Same pattern; bounded FOR parameter start=1 step=1 |
| VV1DOC36.m | 2 | 4 | ✅ | Same pattern; WRITE arguments include line break and $PIECE expression |

### Findings

- All files follow identical structure to VV1DOC18-29 series
- QUIT postconditions (`Q:A=""`) inside the FOR bodies are correctly captured as `MQuitStatement.postcondition` binary comparisons
- FOR loops are classified as bounded with start=1, step=1; body statements include the SET of `A=$TEXT(TEX+I)` and the trailing WRITE arguments
- TEX labels intentionally contain only comment lines; ASG omits them (expected behavior)
- Special format characters (`#`, `!`) in WRITE arguments are captured correctly
- Intrinsic functions `$TEXT()` and `$PIECE()` are properly identified as `MIntrinsicFunction` nodes
- These files document binary operator validation tests:
  - VV1DOC30: String identity operator (`=`) with numeric/string literals
  - VV1DOC31: Continuation of string identity tests, plus not-identical operator (`'=`)
  - VV1DOC32: String not-identical (`'=`) and contains operator (`[`)
  - VV1DOC33: Contains operator (`[`) and not-contains operator (`'[`)
  - VV1DOC34: Not-contains (`'[`) and follows operator (`]`)
  - VV1DOC35: Follows operator (`]`) and not-follows operator (`']`)
  - VV1DOC36: Not-follows operator (`']`) continuation

### Python Code Generation Readiness

✅ **All aspects ready:**
- Expression trees properly structured (not just strings)
- Intrinsic functions like `$TEXT()` and `$PIECE()` clearly identified with full argument lists
- Variable references tracked (I, A, IO)
- Control structures translatable to Python if/for/break patterns
- Special format characters (`#` for form feed, `!` for newline) captured in WRITE arguments
- Postconditions properly modeled as conditional expressions

### Tasks

- [x] T559 [Validation] VV1DOC30–VV1DOC36 ASG verified; no parser changes required.

---

## Phase 47: MUGJ Validation Checklist - VV2 to VV2DOC1

**Purpose**: Validate Part-II drivers and command-space/documentation helpers (Checklist 39/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VV2.m | 23 | 49 | ✅ | Part-II driver; writes headers, K ^VREPORT then DO ^VV2* routines; external DO targets unresolved by design |
| VV2CS.m | 12 | 68 | ⚠️ | Command-space tests; second FOR (`F I=9:1:15 ...`) not emitted; DO postconditions dropped |
| VV2DOC.m | 15 | 17 | ✅ | DOC driver; CRT/PRINTER routes via MGoto START; VV2DOC10 body carries WRITE/IF/KILL |

### Findings

1. **~~Missing second FOR in VV2CS II-5~~**: ✅ FIXED - Both `MForStatement` nodes now captured. Root cause: `CommandWithArg` lookahead didn't recognize commands with postconditions (e.g., `D:1`).
2. **~~DO postconditions dropped~~**: ✅ FIXED - Command postconditions and argument postconditions now captured correctly.

### Root Cause & Fix

The `CommandWithArg` negative lookahead in [commands.tx](../../src/m2py/grammar/commands.tx) was designed to distinguish `Q X` (QUIT with return value) from `Q S X=1` (QUIT followed by SET). However, it only recognized commands followed by space or keyword prefixes, not commands with postconditions (`:` suffix like `D:1`).

**Fix**: Extended each command pattern in `CommandWithArg` to include postcondition detection:
- Before: `/[Dd][Oo][ \t]|[Dd][ \t]+[A-Za-z%^@]/`
- After:  `/[Dd][Oo][ \t:]|[Dd][ \t]+[A-Za-z%^@]/ | /[Dd]:/`

### Tasks

- [x] T560 [Validation] VV2/VV2DOC drivers validated; no parser changes required.
- [x] T561 [Bug] Emit multiple FOR statements on a single line so VV2CS II-5 retains the second loop (`F I=9:1:15 ...`). **FIXED** via CommandWithArg grammar update.
- [x] T562 [Bug] Capture DO postconditions for `DO:1 A:I>0` (both command-level and argument-level) in VV2CS II-5. **FIXED** via CommandWithArg grammar update.
- [x] T563 [Test] Added `test_vv2cs_multi_for_with_postconditions` to validate the fix ([tests/integration/test_mugj.py](../../tests/integration/test_mugj.py)).

---

## Phase 48: MUGJ Validation Checklist - VV2FN1 to VV2LCF1

**Purpose**: Validate Part-II extended function and lower-case command/function coverage (Checklist 41/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VV2FN1.m | 17 | 83 | ⚠️ | Missing `K ^VV` and `K ^(2)` commands in label 70; only WRITE/SET/WRITE captured |
| VV2FN2.m | 17 | 80 | ✅ | $LENGTH/$TEXT cases captured; T95 label intentionally comment-only |
| VV2LCC1.m | 19 | 89 | ✅ | Lower-case DO/GOTO/HANG variants captured; goto sources resolved |
| VV2LCC2.m | 13 | 98 | ✅ | Lower-case IF/ELSE/SET/KILL/XECUTE captured with postconditions |
| VV2LCF1.m | 21 | 99 | ✅ | Lower-case intrinsic functions ($ASCII/$NEXT/$ORDER) captured; KILL ABC array cases modeled |

### Findings

- VV2FN1 label 70 line `K ^VV S ^VV(1)=0,^(1,2)=0 K ^(2) ...` was dropping both KILL commands. Root cause: `KillTarget` rule in commands.tx didn't include `NakedGlobal`. After fix, all 6 commands on that line (K, S, K, S, S, D) parse correctly.
- Remaining files structurally match source; postconditions and intrinsic functions captured; empty TEX/T95 labels (comment-only) are acceptable for $TEXT use.

### Root Cause & Fix

The `KillTarget` rule in [commands.tx](../../src/m2py/grammar/commands.tx) only listed `GlobalVariable | Indirection | LocalVariable`. Naked globals (`^(subscripts)`) were not recognized.

**Fix**: Added `NakedGlobal` before `GlobalVariable` in the `KillTarget` rule (order matters since both start with `^`):
```
KillTarget:
    NakedGlobal | GlobalVariable | Indirection | LocalVariable
;
```

### Tasks

- [x] T564 [Validation] VV2FN1–VV2LCF1 ASG reviewed; noted missing KILL handling in VV2FN1.
- [x] T565 [Bug] Fix KILL parsing for global + naked-global forms (`K ^NAME`, `K ^(subscripts)`) when interleaved with SET on the same line (VV2FN1 label 70). **FIXED** via KillTarget grammar update in commands.tx.
- [x] T566 [Test] Add regression covering VV2FN1 label 70 to assert both KILL statements are emitted. Added `test_vv2fn1_naked_global_kill` in tests/integration/test_mugj.py.

---

## Phase 49: MUGJ Validation Checklist - VV2LCF2 to VV2PAT2

**Purpose**: Validate Part-II lower-case intrinsic/special variables, left-hand `$PIECE`, $NEXT/$ORDER, and pattern matching files (Checklist 42/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VV2LCF2.m | 21 | 93 | ✅ | Lower-case intrinsic and special variables captured; EXAMINER calls resolved |
| VV2LHP1.m | 16 | 114 | ✅ | Left-hand $PIECE lines now parsed correctly with SET/DO statements |
| VV2LHP2.m | 15 | 110 | ✅ | Left-hand $PIECE and trailing DO EXAMINER now captured correctly |
| VV2NO.m | 7 | 101 | ✅ | $NEXT/$ORDER sequences captured including nested FOR/QUIT exits |
| VV2NR.m | 7 | 48 | ✅ | Naked reference effects preserved across KILL/$DATA cases |
| VV2PAT1.m | 10 | 59 | ✅ | Pattern operator combinations captured; FOR on II-154 present |
| VV2PAT2.m | 10 | 71 | ✅ | Indirection and lower-case pattern codes captured with loop counts |

### Findings

- ~~SET + DO are not built for left-hand `$PIECE` assignment lines on a single line in [tests/functional/mugj/inref/VV2LHP1.m](tests/functional/mugj/inref/VV2LHP1.m#L6-L71); ASG emits only the header WRITE for labels 96–108. `$P(...)=` targets should surface as `MSetStatement` (with `MSetTarget`) followed by the `MDoStatement` to EXAMINER.~~ **FIXED:** Added `IntrinsicFunction` to `SingleTarget` in commands.tx grammar.
- ~~[tests/functional/mugj/inref/VV2LHP2.m](tests/functional/mugj/inref/VV2LHP2.m#L60-L63) label 118 omits the trailing `DO EXAMINER`; statements stop at the SET.~~ **FIXED:** Same grammar fix resolved this issue.

### Tasks

- [x] T567 [Bug] Emit `MSetStatement` and `MDoStatement` for left-hand `$PIECE` assignment lines so VV2LHP1 labels 96–108 are fully represented (commands.tx + parser conversion). **FIXED:** Added `IntrinsicFunction` to `SingleTarget` rule in commands.tx. VV2LHP1 now captures 114 statements (up from 46). Added 3 unit tests in test_command_analysis.py.
- [x] T568 [Bug] Ensure trailing `DO EXAMINER` is retained after multi-assignment lines in VV2LHP2 label 118 (textX line parsing → statement build). **FIXED:** Same grammar change resolved this issue. VV2LHP2 now captures 110 statements (up from 67).

## Phase 50: MUGJ Validation Checklist - VV2LCF2 to VV2PAT2 (Re-validation) ✅ COMPLETE

**Purpose**: Address issues found during detailed re-validation of VV2LCF2 and VV2LHP2.

### Findings

- **VV2LCF2.m**: Labels 53 and 54 were missing the last line containing `$select` / `$s`. ✅ FIXED
- **VV2LHP2.m**: Label 119 was missing a statement. ✅ FIXED

### Root Cause: $SELECT Function Parsing

The `$SELECT` function uses special `condition:value` pair syntax that wasn't supported by the `FunctionArgs` grammar rule. The `:` in `$SELECT` is a separator between condition and value, NOT an operator.

**Syntax**: `$S[ELECT](tvexpr:expr, tvexpr:expr, ...)`

### Tasks

- [x] T569 [Bug] Fix `$select` / `$s` parsing in `VV2LCF2.m`. **FIXED:** Added `SelectFunction`, `SelectFunctionArgs`, and `SelectArg` grammar rules to `expressions.tx`. Updated `PrimaryExpr` and `OffsetPrimaryExpr` to include `SelectFunction` before `IntrinsicFunction`. Added `SelectFunction` class to `textx_classes.py`. Labels 53 and 54 now have 5 statements each (was 4).
- [x] T570 [Bug] `$TEST` / `$T` parsing. **RESOLVED:** No separate issue - `$TEST` is a special variable (not a function), already parsed correctly. The missing statements were due to `$SELECT` on the same lines.
- [x] T571 [Bug] `FOR` loop parsing in `VV2LHP2.m` Label 119. **RESOLVED:** Same root cause as T569. Label 119 now has 13 statements (was 12).
- [x] T572 [Test] Added `TestSelectFunction` class with 12 test cases to `test_expression_grammar.py` covering all abbreviation forms and complex expressions.

---

## Phase 51: MUGJ Validation Checklist 42 - VV2LCF2 to VV2PAT2 (Final Re-validation) ✅ COMPLETE

**Purpose**: Final re-validation of 7 files in Checklist 42/54 with detailed ASG review.
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VV2LCF2.m | 21 | 97 | ⚠️ | Mixed-case `$TEst` fails; label 67 missing statements |
| VV2LHP1.m | 16 | 114 | ✅ | Left-hand $PIECE (`$P(glvn,expr)=value`); naked global references in SET targets |
| VV2LHP2.m | 15 | 110 | ✅ | Left-hand $PIECE with postconditions, indirection, control characters |
| VV2NO.m | 7 | 101 | ✅ | $NEXT and $ORDER functions; FOR loops with QUIT conditions |
| VV2NR.m | 7 | 48 | ✅ | Naked global references; effect on KILL, $DATA; interpretation sequence |
| VV2PAT1.m | 10 | 59 | ✅ | Pattern match operator (`?`); repcount patterns (.0A, 1.N, etc.); multi-patatom |
| VV2PAT2.m | 10 | 73 | ⚠️ | Indirect pattern (`?@`) NOT parsed - known limitation |

### ASG Correctness Validation

✅ **All Files Parse Successfully**: 100% parse rate (376/376 MUGJ files)

✅ **Labels Captured Correctly**: All 21 labels in VV2LCF2, 16 in VV2LHP1, 15 in VV2LHP2, etc.

✅ **Commands Captured**:
- SET, WRITE, KILL, DO, IF, FOR, QUIT all correctly represented
- Postconditions on commands (`W:$Y>55 #`) captured
- Multiple commands on one line properly separated

✅ **Expressions Captured**:
- Pattern matches (`X?1.3N`) captured as `MPatternMatch` with pattern string, subject, and compiled_regex
- Left-hand $PIECE (`$P(X,"^")="D"`) captured with target as `IntrinsicFunction`
- Naked globals (`^(subscripts)`) captured as `NakedGlobal` with `requires_runtime_tracking=True`
- $NEXT/$ORDER captured as `IntrinsicFunction` with function name preserved

✅ **Special Variables**: `$JOB`, `$HOROLOG`, `$TEST`, etc. captured as `SpecialVariable` (uppercase versions)

### Known Issues / Limitations

1. **Indirect Pattern Match (`?@`) NOT SUPPORTED**: Lines using `?@(pattern)` syntax (VV2PAT2 lines 7, 12-13) fail to parse entirely. The SET command is silently dropped. This affects:
   - VV2PAT2 label 155: `S VCOMP="ABC123#$!"?@(".4AN2.N1.99999999PN")...` - MISSING
   - VV2PAT2 label 156: `S VCOMP="MUMPS"?@(...)` - MISSING
   - **Impact**: Pattern match tests with indirect patterns will fail at runtime

2. **Lowercase Special Variables Misclassified**: When special variables use lowercase names (`$x`, `$y`, `$io`, `$job`, `$horolog`, `$storage`, `$test`), they are captured as `IntrinsicFunctionNoArgs` instead of `SpecialVariable`. Uppercase versions (`$X`, `$JOB`, etc.) are correctly captured as `SpecialVariable`.
   - **Impact**: Code generation must normalize function names and treat these as special variables
   - **Files Affected**: VV2LCF2 uses lowercase special variables in tests 57-68

3. **Mixed-Case Special Variables FAIL TO PARSE**: Special variables with mixed case like `$Test`, `$TEst`, `$HoroloG` cause the entire line to fail parsing. Only fully uppercase (`$TEST`) or fully lowercase (`$test`) are recognized.
   - **Impact**: VV2LCF2 label 67 line `S VCOMP=VCOMP_$TEST_$test_$TEst` fails completely
   - VV2LCF2 label 67 shows 3 statements but should have 7+ (missing SET/IF/SET/IF sequence)
   - VV2LCF2 label 68 also affected by `$T_$t` patterns

4. **~~FOR + QUIT postcondition + Left-hand $PIECE fails to parse~~** ✅ FIXED: Added `$` to CommandWithArg SET pattern (`[Ss][ \t]+[A-Za-z%^($]`) in commands.tx. The issue was the negative lookahead `!CommandWithArg` in QuitCommand didn't recognize SET with left-hand $PIECE because `$` wasn't in the character class. Now correctly parses VV2LHP2 line 73.

### Python Code Generation Readiness

✅ **Ready for Code Generation**:
- Expression trees properly structured (not strings)
- Operator precedence captured through expression tree nesting
- Label references resolved with `is_resolved=True`
- FOR loops have classified types and body scopes
- Control flow translatable to Python

⚠️ **Requires Runtime Support**:
- Naked globals need runtime tracking of last global reference
- Left-hand $PIECE needs special runtime implementation
- Pattern matches need MUMPS-compatible regex conversion

### Tasks

- [x] T573 [Validation] Re-validate VV2LCF2 to VV2PAT2 with detailed ASG inspection
- [x] T574 [Documentation] Document indirect pattern match (`?@`) as known parser limitation
- [X] T575 [Bug] **VERIFIED FIXED 2025-12-24** Fix lowercase special variable classification (`$x` should be `SpecialVariable` not `IntrinsicFunctionNoArgs`)
- [X] T576 [Enhancement] **VERIFIED FIXED 2025-12-24** Add indirect pattern match (`?@(expr)`) support to expression grammar
- [X] T577 [Bug] **VERIFIED FIXED 2025-12-24** Fix mixed-case special variable parsing (`$Test`, `$TEst`, `$HoroloG` fail to parse entirely)
- [x] T578 [Bug] FOR + QUIT postcondition + SET (left-hand $P) fails to parse entire line - FIXED by adding `$` to CommandWithArg SET pattern in commands.tx

---

## Phase 52: MUGJ Validation Checklist 43 - VV2PAT3 to VV2VNIC

**Purpose**: Validate pattern-operator edge cases, READ with counts/timeouts, string subscripts, and variable-name indirection (Checklist 43/54).
**Validation Date**: 2025-12-22 (Round 2 re-validation)

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VV2PAT3.m | 8 | 88 | ✅ | Pattern code tables (n/u/l/a/e) captured; 16 FOR loops, 16 DO EXAMINER calls resolved |
| VV2READ.m | 11 | 60 | ⚠️ | **READ count syntax (`X#3`) NOT PARSED** - only 2 of 8 READ commands captured |
| VV2SS1.m | 9 | 70 | ✅ | FOR with postconditioned QUIT; $ORDER iteration; long subscripts captured |
| VV2SS2.m | 8 | 57 | ✅ | Naked globals; scientific notation subscripts; 31-subscript limits captured |
| VV2VNIA.m | 13 | 96 | ✅ | All name indirection patterns `@X@(subs)` correctly captured |
| VV2VNIB.m | 10 | 103 | ✅ | Complex DO/GOTO with name indirection postconditions captured |
| VV2VNIC.m | 6 | 63 | ✅ | Name indirection in expressions, KILL, multi-assign, XECUTE captured |

### Critical Issue Found: READ Count Syntax Not Parsed

**VV2READ.m Analysis**: The file tests READ with count syntax per MUMPS spec 8.2.17:
- `R X#3` - read up to 3 characters
- `R X#10:60` - read up to 10 chars with 60 second timeout

**Test Results**:
```
'read X#3': 0 commands parsed
'r X#10': 0 commands parsed
'R X#10:60': 0 commands parsed
'R @A': 1 command parsed (indirection works)
```

**Root Cause**: The `ReadTarget` rule in `commands.tx` only accepts:
- `CharRead | GlobalVariable | LocalVariable | Indirection`

It does NOT handle the readcount syntax `glvn # intexpr` where `#` specifies max characters.

**Impact**: 6 of 8 READ commands in VV2READ.m are silently dropped:
- Labels 140, 141, 143, 144, 145, 146 show 5 statements each, but should have 6 (missing READ)
- Only labels 142 and 147 (using `@A` indirection) correctly capture the READ

**MUMPS Spec Reference** (1995__a108040.md):
> When the form of the argument is `glvn # intexpr [ timeout ]`, let n be the value of intexpr. The input message is a string whose length is at most n characters.

### Previous Findings (Resolved)

The name indirection grammar fix from the previous validation remains in place and working correctly.

### Tasks

- [x] T579 [Bug] Fix statement emission for VV2VNIA labels 122–126/129 where SET sequences with nested variable-name indirection and trailing `D EXAMINER` are dropped. **RESOLVED** - Grammar now supports `@X@(subs)` patterns.
- [x] T580 [Bug] Restore XECUTE + trailing `D EXAMINER` in VV2VNIB label 135. **RESOLVED** - Same grammar fix applied.
- [X] T581 [Bug] **VERIFIED FIXED 2025-12-24** Add READ count syntax (`glvn#intexpr`) support to ReadTarget grammar rule in `src/m2py/grammar/commands.tx`. Must handle:
  - `R X#3` - variable with count
  - `R X#10:60` - variable with count and timeout
  - `R @A` where `A="X#10"` - indirection containing count (may require runtime)
  - Update `ReadTargetWithTimeout` to include optional `#count` before timeout

---

## Phase 53: MUGJ Validation Checklist 44 - VVE to VVEDOC2

**Purpose**: Validate Part-III instruction drivers and documentation files (Checklist 44/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VVE.m | 2 | 6 | ✅ | FOR with $T(TEX+I), $P; D ^VVE1/VVE2; K ^VREPORT; TEX label (comments only) |
| VVE1.m | 2 | 2 | ✅ | Same FOR pattern as VVE.m; TEX label for documentation text |
| VVE2.m | 2 | 3 | ✅ | FOR pattern + W ! (newline); TEX label for validation sequence docs |
| VVEDIV.m | 6 | 47 | ✅ | Division-by-zero tests: 1/0, 0/0, 4/$L(""); numeric labels (1,2,3,4) |
| VVEDOC.m | 13 | 15 | ✅ | Driver routine; S IO="CRT" G START pattern; D ^VVEDOC1-8; IF/KILL |
| VVEDOC1.m | 2 | 4 | ✅ | IF IO="PRINTER" W #; FOR $T pattern; documentation driver |

---

## Phase 60: VistA-M Codebase Validation

**Purpose**: Validate the M2PY parser against the full VistA-M codebase (~34,000 files) to achieve 100% parsing coverage.

**Evaluation Date**: 2025-12-23
**Codebase**: `/Users/owen.barton/workspace/m2py/VistA-M/Packages/` (139 packages)
**Total Files**: 33,951 MUMPS routines

### Evaluation Results Summary

| Metric | Value | Notes |
|--------|-------|-------|
| **Parse Success Rate** | **99.98%** | 33,944 of 33,951 files |
| Parse Failures | 7 | All UnicodeDecodeError (encoding issues) |
| Files with Computed GOTOs | 1,025 | Dynamic GOTO targets requiring runtime |
| Files with GOTO inside FOR | 778 | Complex control flow |
| Files with Multiple XECUTE (>3) | 1,223 | Heavy dynamic execution |
| Files with Deeply Nested FOR (>3) | 58 | Deep loop nesting |

### Phase 60a: File Encoding Support ✅ PRIORITY: HIGH

**Issue**: 7 files fail with UnicodeDecodeError - contain Latin-1 or other non-UTF-8 characters.

| File | Error Byte | Position | Package |
|------|------------|----------|---------|
| DVBCQAN2.m | 0xba | 9374 | Automated Information Collection System |
| DVBCQWR2.m | 0xba | 9174 | Automated Information Collection System |
| YTSFTND.m | 0xf6 | 27 | Unknown |
| RMPR4P23.m | 0xa7 | 1696 | Unknown |
| RMPR9P23.m | 0xa7 | 1750 | Unknown |
| RMPRP23.m | 0xa7 | 1693 | Unknown |
| TIULC.m | 0xf7 | 1601 | Text Integration Utilities |

**Root Cause**: These files contain special characters (°, ö, §, ÷) encoded in Latin-1/CP1252.

**Tasks**:
- [X] T600 [BUG] Add encoding fallback to `parse_file()` in `src/m2py/parser/parser.py`
  - Try UTF-8 first, then Latin-1/CP1252 fallback
  - Implementation: Added try/except around read_text() with Latin-1 fallback
- [X] T601 [TEST] Add unit tests for Latin-1 file parsing in `tests/unit/test_parser.py`
  - Added: test_parse_file_utf8_encoding, test_parse_file_latin1_fallback, test_parse_file_latin1_preserves_content
- [X] T602 [VALIDATION] Verify all 7 VistA files parse after encoding fix
  - All 7 files now parse successfully (DVBCQAN2, DVBCQWR2, YTSFTND, RMPR4P23, RMPR9P23, RMPRP23, TIULC)

### Phase 60b: Unknown Intrinsic Functions ✅ PRIORITY: MEDIUM

**Issue**: 6 function names flagged as unknown during evaluation.

| Function | Count | Analysis | Action |
|----------|-------|----------|--------|
| `$I` | 7 | Standard `$INCREMENT` abbreviation per Caché | Already parsed via FUNCNAME |
| `$LI` | 2 | Standard `$LIST` abbreviation per Caché | Already parsed via FUNCNAME |
| `$EREF` | 1 | Extended reference (implementation-specific) | Already parsed via FUNCNAME |
| `$INCREMENT` | 1 | Standard function (full name) | Already supported |
| `$NAMESPACE` | 1 | Caché-specific namespace accessor | Already parsed via FUNCNAME |
| `$LISTGET` | 1 | Standard `$LG` function (full name) | Already supported |

**Resolution**: The grammar's `FUNCNAME` pattern `/[A-Za-z][A-Za-z0-9]*/` already accepts all these
Caché-specific functions. They parse as `IntrinsicFunction` or `IntrinsicFunctionNoArgs` nodes.
No grammar changes required - these are correctly handled at the syntax level.

**Tasks**:
- [X] T603 [ANALYSIS] Verified grammar already handles `$I`, `$LI`, `$INCREMENT`, `$LISTGET` via FUNCNAME
- [X] T604 [ANALYSIS] Verified grammar already handles `$EREF`, `$NAMESPACE` via IntrinsicFunctionNoArgs
- [X] T605 [DOC] Documented Caché-specific functions in test suite comments
- [X] T606 [TEST] Added tests for Caché functions in `tests/unit/test_expression_grammar.py::TestCacheSpecificFunctions`
  - test_li_list_abbreviation, test_listget_function, test_increment_function
  - test_namespace_special_var, test_eref_special_var

### Phase 60c: Complex Control Flow Patterns 🔍 PRIORITY: LOW (Runtime)

**Issue**: Deep analysis identified patterns requiring runtime support.

| Pattern | Files Affected | Code Generation Strategy |
|---------|----------------|--------------------------|
| Computed GOTOs | 1,025 | `MCall.label_is_indirect=True` → runtime dispatch |
| GOTO inside FOR | 778 | Standard FOR-exit pattern → `break` in Python |
| Multiple XECUTE (>3) | 1,223 | `requires_runtime_eval=True` → runtime interpreter |
| Nested FOR (>3 levels) | 58 | Direct translation (Python supports deep nesting) |
| Argumentless FOR | Many | `while True` + explicit break conditions |

**Tasks**:
- [X] T607 [ANALYSIS] Computed GOTOs already flagged via `MCall.label_is_indirect` - no parser change needed
- [X] T608 [ANALYSIS] GOTO inside FOR already captured - control flow analysis handles loop exits
- [X] T609 [ANALYSIS] XECUTE statements marked `requires_runtime_eval=True` - no parser change needed
- [X] T610 [VALIDATION] Confirm 58 deep-nested FOR files parse correctly (random sample validated)

### Phase 60d: Top Complex Files for Manual Validation

**Purpose**: Identify files to validate with `utils/validate_asg.py` for ASG correctness.

The deep analysis script identified these as highest-priority for manual review:

| Rank | File | Issues | Validation Command |
|------|------|--------|-------------------|
| 1 | DIVR.m | Computed GOTOs, 11 XECUTE, 7 argumentless FOR | `uv run python utils/validate_asg.py VistA-M/.../DIVR.m` |
| 2 | DENTDC.m | 12 unresolved GOTOs, computed GOTOs, 5 XECUTE | `uv run python utils/validate_asg.py VistA-M/.../DENTDC.m` |
| 3 | XQ1.m | 8 unresolved GOTOs, computed GOTOs, 4 XECUTE | `uv run python utils/validate_asg.py VistA-M/.../XQ1.m` |
| 4 | ORCONV1.m | 24 unresolved GOTOs, computed GOTOs | `uv run python utils/validate_asg.py VistA-M/.../ORCONV1.m` |
| 5 | DGPTFM.m | 12 unresolved GOTOs, computed GOTOs, 2 GOTO-in-FOR | `uv run python utils/validate_asg.py VistA-M/.../DGPTFM.m` |

**Tasks**:
- [ ] T611 [VALIDATION] Manually validate DIVR.m with validate_asg.py - verify all statements captured
- [ ] T612 [VALIDATION] Manually validate DENTDC.m - focus on computed GOTO representation
- [ ] T613 [VALIDATION] Manually validate XQ1.m - verify unresolved GOTO handling
- [ ] T614 [VALIDATION] Manually validate ORCONV1.m - largest unresolved GOTO count
- [ ] T615 [VALIDATION] Manually validate DGPTFM.m - GOTO-in-FOR control flow

### Phase 60e: Statement Type Coverage

**Verified**: All major MUMPS statement types are captured across VistA-M.

| Statement Type | VistA-M Count | Status |
|----------------|---------------|--------|
| MSetStatement | 991,362 | ✅ Fully supported |
| MQuitStatement | 466,476 | ✅ Fully supported |
| MDoStatement | 378,027 | ✅ Fully supported |
| MIfStatement | 340,710 | ✅ Fully supported |
| MWriteStatement | 193,727 | ✅ Fully supported |
| MKillStatement | 132,166 | ✅ Fully supported |
| MNewStatement | 106,874 | ✅ Fully supported |
| MGotoStatement | 105,681 | ✅ Fully supported |
| MForStatement | 105,108 | ✅ Fully supported |
| MXecuteStatement | 19,099 | ✅ Fully supported |
| MElseStatement | 15,509 | ✅ Fully supported |
| MLockStatement | 7,835 | ✅ Fully supported |
| MReadStatement | 7,303 | ✅ Fully supported |
| MUseStatement | 4,291 | ✅ Fully supported |
| MMergeStatement | 4,184 | ✅ Fully supported |
| MHangStatement | 2,662 | ✅ Fully supported |
| MViewStatement | 251 | ✅ Fully supported |
| MCloseStatement | 140 | ✅ Fully supported |
| MOpenStatement | 118 | ✅ Fully supported |
| MBreakStatement | 100 | ✅ Fully supported |

### Phase 60f: Intrinsic Function Coverage

**Verified**: Top 15 intrinsic functions by usage in VistA-M.

| Function | VistA-M Count | Status |
|----------|---------------|--------|
| $P ($PIECE) | 23,699 | ✅ Fully supported |
| $O ($ORDER) | 20,423 | ✅ Fully supported |
| $D ($DATA) | 20,335 | ✅ Fully supported |
| $G ($GET) | 19,961 | ✅ Fully supported |
| $E ($EXTRACT) | 17,606 | ✅ Fully supported |
| $S ($SELECT) | 15,420 | ✅ Fully supported |
| $L ($LENGTH) | 8,188 | ✅ Fully supported |
| $T ($TEXT) | 7,908 | ✅ Fully supported |
| $A ($ASCII) | 5,478 | ✅ Fully supported |
| $C ($CHAR) | 4,019 | ✅ Fully supported |
| $J ($JUSTIFY) | 3,552 | ✅ Fully supported |
| $TR ($TRANSLATE) | 2,104 | ✅ Fully supported |
| $NA ($NAME) | 1,109 | ✅ Fully supported |
| $F ($FIND) | 629 | ✅ Fully supported |
| $Q ($QUERY) | 534 | ✅ Fully supported |

### Phase 60g: Special Variable Coverage

**Verified**: Special variables used in VistA-M.

| Variable | VistA-M Count | Status | Notes |
|----------|---------------|--------|-------|
| $J ($JOB) | 11,688 | ✅ Supported | Process ID |
| $T ($TEST) | 3,741 | ✅ Supported | Last IF/READ result |
| $Y | 3,250 | ✅ Supported | Vertical position |
| $H ($HOROLOG) | 1,244 | ✅ Supported | Date/time |
| $X | 1,227 | ✅ Supported | Horizontal position |
| $I ($IO) | 84 | ✅ Supported | Current device |
| $JOB | 43 | ✅ Supported | Full name |
| $Q ($QUIT) | 42 | ✅ Supported | QUIT level |
| $P ($PRINCIPAL) | 41 | ✅ Supported | Principal device |
| $ECODE | 17 | ✅ Supported | Error codes |
| $IO | 16 | ✅ Supported | Full name |
| $PRINCIPAL | 14 | ✅ Supported | Full name |
| $TEST | 8 | ✅ Supported | Full name |
| $ESTACK | 7 | ✅ Supported | Error stack depth |

---

## Phase 60 Completion Summary ✅

**Final Result**: **100% parsing success across all 33,951 VistA-M files**

**Changes Made**:
1. **Encoding Fallback** (T600-T602): Added UTF-8 → Latin-1 fallback in `parse_file()` 
   - File: [src/m2py/parser/parser.py](src/m2py/parser/parser.py)
   - All 7 previously failing files now parse correctly
   
2. **Caché Function Tests** (T603-T606): Verified grammar already handles Caché-specific functions
   - `$LI`, `$LISTGET`, `$INCREMENT`, `$NAMESPACE`, `$EREF` all parse correctly
   - Added documentation tests in [tests/unit/test_expression_grammar.py](tests/unit/test_expression_grammar.py)

**Test Coverage Added**:
- 3 encoding fallback tests in `test_parser.py::TestMUMPSParserParseFile`
- 5 Caché function tests in `test_expression_grammar.py::TestCacheSpecificFunctions`

---

| VVEDOC2.m | 2 | 4 | ✅ | Same pattern as VVEDOC1; Part-III content documentation |

### Bug Fix Applied

**T582 [Bug Fix] Binary expressions in function arguments were being dropped**

**Root Cause**: The `_unwrap_expr()` function in `textx_classes.py` checked for `.ops` attribute to detect binary operations, but the actual textX grammar uses `.tail` (containing `BinaryOpTail` list).

**Symptom**: `$T(TEX+I)` was incorrectly parsed as `$T(TEX)` - the `+I` offset was lost.

**Fix Applied**: Updated `_unwrap_expr()` to check for both `.tail` and `.ops` attributes, and also fixed the unary operator detection to check for `operators` (plural) list in addition to `operator` (singular).

**Files Modified**: `src/m2py/parser/textx_classes.py` lines 36-73

**Verification**: 
- `$T(TEX+I)` now correctly produces `MBinaryOp(TEX + I)` as argument
- `$P(A," ;",2,99)` correctly captures all 4 arguments
- All 727 unit tests pass

### Detailed Analysis

#### VVE.m, VVE1.m, VVE2.m
These files use a common pattern for displaying documentation text from embedded comments:
```mumps
F I=1:1 S A=$T(TEX+I) Q:A=""  W !,$P(A," ;",2,99)
```

This pattern:
1. Open-ended FOR loop (`I=1:1` with no end)
2. Uses `$TEXT(label+offset)` to get source line text
3. Postconditioned QUIT when empty line found
4. Extracts text after ` ;` using $PIECE

**ASG correctly captures**:
- FOR with open-ended MForParameter (start=1, step=1, end=None)
- SET with MBinaryOp as $T argument (TEX + I)
- QUIT with MBinaryOp postcondition (A = "")
- WRITE with FormatControl (!) and $P intrinsic

#### VVEDIV.m
Tests division by zero error conditions. Numeric labels (1,2,3,4) for test entry points.

**Key expressions captured**:
- `W 1/0` → MBinaryOp(1 / 0)
- `W 0/0` → MBinaryOp(0 / 0)  
- `W 4/$L("")` → MBinaryOp(4 / $L(""))
- `S A=2345979/0000E2+3` → Complex expression with scientific notation

#### VVEDOC.m
Driver routine with branching entry points and external routine calls.

**Control flow captured**:
- `S IO="CRT" G START` → SET followed by resolved GOTO
- `D ^VVEDOCn` → DO external routine (8 calls)
- `I IO="PRINTER" W #` → IF with condition and form-feed output
- `K IO,I,A` → KILL with 3 local variables

**GOTO resolution verified**: Both CRT and PRINTER labels correctly resolve GOTO START.

### Python Code Generation Readiness

All files in this batch are **ready for code generation**:

1. **FOR with $TEXT**: The `$TEXT(label+offset)` pattern requires runtime support for source introspection. The ASG correctly captures the structure - code generation needs to implement `$TEXT` to return source lines.

2. **Expression trees**: Binary operations are properly structured with operator, left, and right - no string parsing needed.

3. **External routine calls**: `D ^ROUTINE` correctly captured as MCall with routine name. Resolution deferred (external).

4. **GOTO resolution**: Local label jumps correctly resolved with back-references.

### Tasks

- [x] T582 [Bug Fix] Update `_unwrap_expr()` in textx_classes.py to check for `.tail` attribute (not just `.ops`) for binary operation detection
- [x] T583 [Test] Add regression tests for binary expressions in function arguments (`test_binary_expression_in_function_arg`, `test_complex_expression_in_function_arg`) in `tests/unit/test_semantic_analyzer.py`

---

## Phase 54: MUGJ Validation Checklist 46 - VVEFORB to VVELINB

**Purpose**: Validate FOR edge cases, KILL semantics, and line-reference error handling (Checklist 46/54).  
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VVEFORB.m | 7 | 66 | ✅ | FOR with KILL postcondition; XECUTE loop body; double QUIT captured |
| VVEFORC.m | 7 | 67 | ✅ | Negative step FOR patterns; DO KILL helper; XECUTE classification ok |
| VVEFORD.m | 7 | 61 | ✅ | Open-ended FOR forms; KILL postcondition in loop body captured |
| VVEKILL.m | 6 | 65 | ✅ | Plain `K` now has `is_kill_all=True` property |
| VVELIMN.m | 5 | 58 | ✅ | Plain `K` now has `is_kill_all=True` property |
| VVELIMS.m | 5 | 70 | ✅ | Plain `K` now has `is_kill_all=True` property |
| VVELINA.m | 7 | 59 | ✅ | DO/GOTO offsets are correctly captured; bounds checking is runtime concern per MUMPS spec |
| VVELINB.m | 6 | 59 | ✅ | Indirect DO/GOTO captured as unresolved; external label spellings remain unresolved |

### Findings

**T584 Analysis (Out-of-range offsets)**: After reviewing the MUMPS spec, line reference errors are **runtime errors**, not parse-time errors. The VVE test files are specifically designed to trigger these runtime errors. Since we cannot know routine size during static analysis (especially for external routines like `D LINE+999^VVELINA`), the ASG correctly captures the offset as-is with `CallType.OFFSET_CALL`. **No fix needed** - this is working as intended.
**T585 Analysis (Kill-all semantics)**: Plain `K` (no arguments) was represented as `MKillStatement` with empty `targets` and `exclusive=False`, which technically distinguishes it but was not explicit. Also, variable analysis did not handle `MKillStatement` at all. **Fix applied**: 1) Added `is_kill_all` computed property to `MKillStatement` that returns `True` when `targets` is empty and `exclusive=False`. 2) Added `MKillStatement` handling in `_extract_statement_variables()` in `variables.py`. 3) Added unit tests for `is_kill_all` property.

### Tasks

- [x] T584 [Not a Bug] Investigated - out-of-range line offsets are runtime errors per MUMPS spec, not static analysis concerns. No fix needed.
- [x] T585 [Enhancement] Added `is_kill_all` property to `MKillStatement` and updated variable analysis to handle KILL statements. Added unit tests.

---

## Phase 55: MUGJ Validation Checklist 47 - VVELINN to VVERAND

**Purpose**: Validate line reference error handling (internal/external), naked global semantics, pattern match validation, and $RANDOM error conditions (Checklist 47/54).  
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VVELINN.m | 7 | 61 | ✅ | Internal line refs with negative offsets; `DO LR+-1`, `G @B+A` |
| VVELINXA.m | 7 | 59 | ✅ | External line refs with large offsets; indirect labels with decimal offset |
| VVELINXB.m | 6 | 59 | ✅ | External calls to nonexistent labels; subscripted indirection |
| VVELINXN.m | 7 | 61 | ✅ | External calls with negative offsets; `G @B+A^VVELINN` |
| VVENAK.m | 6 | 66 | ✅ | Naked global `^(2)` with `requires_runtime_tracking=True`; `$D`, `$O` with naked |
| VVEPAT.m | 6 | 57 | ✅ | Pattern match `?` operator; MPatternMatch correctly captures subject/pattern/regex |
| VVERAND.m | 6 | 47 | ✅ | `$RANDOM`/`$R` intrinsic with various invalid arguments |

### Findings

All 7 files parse correctly and produce complete, accurate ASG representations. These VVE* files are specifically designed to trigger **runtime errors** (negative line offsets, undefined naked indicator, invalid pattern repcounts, $RANDOM arguments < 1), which correctly cannot be detected at parse time.

**Key semantic structures validated**:

1. **Line offset calls**: `DO LR+-1` correctly produces MCall with `offset=MUnaryOp('-', 1)` and `call_type=OFFSET_CALL`. Internal labels are resolved; external remain unresolved.

2. **Indirect calls with offset**: `G @B+A` produces MCall with `indirection=LocalVariable('B')`, `offset=LocalVariable('A')`, and `call_type=INDIRECT_CALL`. Complex subscripted indirection like `@B(2,1)+A` also works.

3. **Naked globals**: `^(2)` produces NakedGlobal with `subscripts=[2]` and `requires_runtime_tracking=True`. The naked indicator state is a runtime concern.

4. **Pattern matches**: `123?2.1N` produces MPatternMatch with `subject=123`, `pattern='2.1N'`, and `compiled_regex='[0-9]{2,1}'`. Invalid repcounts (upper < lower) are runtime errors.

5. **Intrinsic functions**: `$RANDOM(0)`, `$R(-1)`, `$R(A)` all correctly captured with proper argument expressions. Argument validation is runtime.

### Python Code Generation Notes

- **Line offsets**: Code gen needs runtime line-number resolution from labels. Consider a `_get_line_by_offset(label, offset)` helper.
- **Naked globals**: Need to track "naked indicator" state variable that stores last non-naked global reference.
- **Pattern validation**: Invalid pattern repcounts should raise runtime error. The `compiled_regex` field provides Python regex equivalent.
- **$RANDOM**: Python's `random.randint(0, arg-1)` with argument validation for < 1.

### Tasks

No new tasks - all semantic structures are correctly captured.

---

## Phase 56: MUGJ Validation Checklist 48 - VVEREAD to VVINST10

**Purpose**: Validate READ command error handling, $SELECT error conditions, $TEXT error conditions, undefined variable errors, and instruction documentation files (Checklist 48/54).  
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VVEREAD.m | 6 | 57 | ✅ | Fixed-length READ syntax now supported |
| VVESEL.m | 6 | 48 | ✅ | $SELECT with all-false conditions; correctly captured |
| VVESTAT.m | 9 | 60 | ✅ | Validation report utility; complex FOR, IF/ELSE, DO calls |
| VVETEXT.m | 6 | 48 | ✅ | $TEXT with negative line offsets; indirection @A+B |
| VVEUNDF.m | 6 | 57 | ✅ | Undefined variable errors; subscripted undefined |
| VVINST1.m | 2 | 4 | ✅ | Instruction file 1; mostly comments |
| VVINST10.m | 2 | 4 | ✅ | Instruction file 10; mostly comments |

### Issues Found and Resolved

#### Issue #1: READ Command Missing Fixed-Length Syntax (`#length`) ✅ FIXED

**Description**: The READ command grammar doesn't support the fixed-length syntax `READ var#length` or `READ var#length:timeout`.

**Affected Files**: VVEREAD.m (and potentially any MUMPS code using fixed-length reads)

**Missing Statements**: 4 statements in VVEREAD.m fail to parse:
- Line 16: `K A READ A#-1` → KILL captured, READ with `A#-1` not parsed (0 commands)
- Line 29: `S A=99 R A#-999999999` → SET captured, READ with `A#-999999999` not parsed
- Line 42: `S A=123,B=0 R A#B` → SET captured, READ with `A#B` not parsed
- Line 55: `K B S A=-3 R B#A:10` → KILL+SET captured, READ with `B#A:10` not parsed

**Root Cause**: `ReadTarget` rule in `commands.tx` only supports:
```textx
ReadTarget:
    CharRead | GlobalVariable | LocalVariable | Indirection
;
```

Missing support for fixed-length read: `var#intexpr` and `var#intexpr:timeout`

**MUMPS Spec Reference**: ANSI/MDC X11.1 Section I-3.6.14 (READ command):
> "When the form of the argument is lvn # intexpr [timeout], let n be the value of intexpr."

**Required Grammar Change**: Add `FixedLengthRead` rule:
```textx
ReadTarget:
    CharRead | FixedLengthRead | GlobalVariable | LocalVariable | Indirection
;

FixedLengthRead:
    var=(GlobalVariable | LocalVariable | Indirection) '#' length=Expr
;
```

**Impact**: Low - only affects error-handling tests. Most production code doesn't use fixed-length reads.

### Key Semantic Structures Validated

1. **$SELECT with all-false conditions**: `$SELECT(0:"text")` correctly produces `SelectFunction` with `arguments=[(0, "text")]`. Runtime should raise error when no condition is true.

2. **$TEXT with negative offsets**: `$TEXT(+-1)`, `$T(+-999999999)`, `$T(TEXT+2-3)` all correctly capture the offset expression tree. `$T(@A+B)` captures indirection correctly.

3. **Undefined variable subscript**: `B(A)` where A is undefined produces correct `LocalVariable` with subscript. Runtime error detection is correct.

4. **Complex FOR with 12 value parameters**: `F %I=31,%Y#4=0+28,31,30,31,30,31,31,30,31,30,31` correctly produces 12 `MForParameter` objects with proper expression trees for month-day calculations.

5. **$PIECE and $EXTRACT**: String manipulation functions correctly captured with all arguments.

6. **IF/ELSE chains**: Proper scope nesting with condition expressions.

7. **DO call resolution**: All internal labels (`%DATE`, `%TIME`, `DISPF`, `DISPL`, `TOTAL`, `SET`, `DISP1`) correctly resolved with back-references.

### Python Code Generation Notes

- **Fixed-length READ**: Needs runtime support for `input()[:length]` with proper timeout handling.
- **$SELECT all-false**: Should raise `MUMPSError` at runtime, not parse time.
- **$TEXT negative offset**: Should raise `MUMPSError` at runtime.
- **Undefined variables**: Python will raise `KeyError` or similar, may need wrapper.

### Tasks

- [X] T586 [US1] Add `FixedLengthRead` grammar rule to support `READ var#length` syntax
- [X] T587 [US1] Update `_analyze_ReadCommand` in semantic_analyzer.py to handle fixed-length reads
- [X] T588 [US1] Add unit test for fixed-length READ parsing
- [X] T589 [US1] Re-validate VVEREAD.m after grammar fix

**Checkpoint**: Phase 56 complete - READ#length grammar support added. All 7 files now fully validated.

---

## Phase 57: MUGJ Validation Checklist 52 - VVINST9 to VVOVER14

**Purpose**: Validate instruction and overview documentation emitters (Checklist 52/54).
**Validation Date**: 2025-12-22

### Validation Summary

| File | Labels | Statements | Status | Notes |
|------|--------|------------|--------|-------|
| VVINST9.m | 2 | 4 | ✅ | IF IO="PRINTER" guard; standalone WRITE; bounded FOR with SET/QUIT postcondition/WRITE; QUIT terminator |
| VVOVER1.m | 2 | 3 | ✅ | Documentation emitter pattern (WRITE guarded by IF, bounded FOR over $TEXT, QUIT) |
| VVOVER10.m | 2 | 3 | ✅ | Same pattern; $TEXT(TEX+I) offset and $PIECE arguments captured |
| VVOVER11.m | 2 | 3 | ✅ | Same pattern; FOR body SET/QUIT/WRITE captured |
| VVOVER12.m | 2 | 3 | ✅ | Same pattern; intrinsic functions preserved |
| VVOVER13.m | 2 | 3 | ✅ | Same pattern; TEX label comment-only (no statements) |
| VVOVER14.m | 2 | 3 | ✅ | Same pattern; QUIT postcondition modeled |

### Findings

- All seven routines share the documentation emitter structure: optional printer IF/WRITE header, standalone newline WRITE (VVINST9), bounded FOR `I=1:1` with SET `$TEXT(TEX+I)`, QUIT postcondition `A=""`, trailing WRITE with `$PIECE` extraction, and final QUIT.
- FOR loops classified as bounded with start=1 and step=1; loop bodies include SET, postconditioned QUIT, and WRITE statements.
- TEX labels contain only comments for $TEXT retrieval; absence of statements is expected.
- No additional parser or analysis changes required; ASG already captures intrinsic functions (`$TEXT`, `$PIECE`) and format controls (`#`, `!`).

### Python Code Generation Readiness

- Control flow (IF guard, bounded FOR, QUIT) maps directly to Python; WRITE commands include format controls for form feed/newline.
- `$TEXT` offsets and `$PIECE` argument lists are fully preserved for runtime implementations; label resolution complete.

### Tasks

- [x] T590 [Validation] VVINST9–VVOVER14 ASG verified; no parser changes required.

**Checkpoint**: Phase 57 complete - All VVINST/VVOVER files validated.

---

## Phase 58: Enhanced Variable Scoping for Clean Python Function Generation

**Purpose**: Implement comprehensive variable scoping analysis that enables Python code generation with normal function arguments and return values, instead of runtime `get_local()`/`set_local()` patterns.

**Background**: MUMPS has unique variable scoping semantics:
- All local variables are implicitly visible to called subroutines (unless NEWed)
- The NEW command creates a scope boundary that shadows variables
- Parameter passing with formal parameters performs an implicit NEW
- Call-by-reference (`.X`) creates aliasing between caller and callee variables
- Labels can be called with arguments that bind to formal parameters

**Goal**: Analyze variable flow to enable generating Python functions like:
```python
def CALC(X, Y):           # From formal_list + input_variables
    Z = X + Y
    return Z              # From output_variables + QUIT value
```

Instead of:
```python
def CALC():
    X = get_local("X")
    Y = get_local("Y") 
    Z = X + Y
    set_local("Z", Z)
```

**Reference**: See `mumps-reference/MDC__a108014.md` (Parameter Passing), `mumps-reference/MDC__a108042.md` (NEW Command), `mumps-reference/MDC__a108026.md` (DO Command).

---

### Phase 58a: Formal Parameter Integration

**Purpose**: Treat formal parameters as implicit NEW - they create local scope for those names

- [X] T591 [P58a] Update `_analyze_label()` in variables.py to treat `formal_list` names as implicitly NEWed
- [X] T592 [P58a] Add `formal_params: Set[str]` field to `ScopeVariables` dataclass
- [X] T593 [P58a] Exclude formal parameters from `input_variables` (they ARE the inputs, not external reads)
- [X] T594 [P58a] Unit test: label with formal params - verify they don't appear in input_variables
- [X] T595 [P58a] Unit test: label reading caller's variable before formal param shadows it

### Phase 58b: Call-by-Reference Analysis

**Purpose**: Track which actual parameters are passed by reference (`.X`) vs by value

- [X] T596 [P58b] Add `PassingMode` enum to enums.py: `BY_VALUE`, `BY_REFERENCE`, `OMITTED`
- [X] T597 [P58b] Add `passing_mode: PassingMode` field to MCall argument representation
- [X] T598 [P58b] Update DO command parsing in semantic_analyzer.py to detect `.actualname` syntax
- [X] T599 [P58b] Update extrinsic function parsing to detect call-by-reference arguments
- [X] T600 [P58b] Add `is_byref: bool` property to MCall arguments
- [X] T601 [P58b] Unit test: `D CALC(.X,.Y)` - verify arguments marked as BY_REFERENCE
- [X] T602 [P58b] Unit test: `D CALC(X+1,Y)` - verify arguments marked as BY_VALUE
- [X] T603 [P58b] Unit test: `D CALC(,X)` - verify first arg OMITTED, second BY_VALUE

### Phase 58c: Actual-to-Formal Parameter Binding

**Purpose**: Link actual parameters at call sites to formal parameters at target labels

- [X] T604 [P58c] Create `ParameterBinding` dataclass: `formal_name`, `actual_expr`, `passing_mode`, `caller_var_name`
- [X] T605 [P58c] Add `parameter_bindings: List[ParameterBinding]` field to MCall
- [X] T606 [P58c] Implement `bind_parameters()` function in variables.py
- [X] T607 [P58c] Call `bind_parameters()` during `resolve_references()` pass (deferred - called on demand)
- [X] T608 [P58c] Validate actual count ≤ formal count per MUMPS spec (excess actuals = error)
- [X] T609 [P58c] Handle omitted parameters (empty DATA-CELL in MUMPS)
- [X] T610 [P58c] Unit test: `D CALC(A,B)` calling `CALC(X,Y)` - verify bindings X←A, Y←B
- [X] T611 [P58c] Unit test: `D CALC(A)` calling `CALC(X,Y)` - verify X←A, Y←omitted

### Phase 58d: Alias Tracking for By-Reference Parameters

**Purpose**: Track when modifications to formal params affect caller's actual variables

- [X] T612 [P58d] Create `AliasSet` class to track variable aliasing relationships
- [X] T613 [P58d] Populate alias sets when call-by-reference binds formal to actual
- [X] T614 [P58d] Add `aliased_variables: Dict[str, Set[str]]` to ScopeVariables
- [X] T615 [P58d] Update `output_variables` computation to include aliased writes
- [X] T616 [P58d] Flag labels that modify by-ref parameters as having "caller side effects"
- [X] T617 [P58d] Unit test: `.X` passed to formal `A`, `S A=1` - verify X in caller's outputs
- [X] T618 [P58d] Unit test: nested call chains with by-ref propagation (via transitive output test)

### Phase 58e: Function Signature Computation

**Purpose**: Compute clean Python function signatures for each label

- [X] T619 [P58e] Create `FunctionSignature` dataclass in variables.py:
  - `label_name: str`
  - `formal_params: List[str]` (from MLabel.formal_list)
  - `required_inputs: Set[str]` (caller must provide, not in formal_list)
  - `optional_inputs: Set[str]` (can be provided via globals or caller scope)
  - `return_value: Optional[str]` (from QUIT expr analysis)
  - `byref_outputs: Set[str]` (modified by-ref params)
  - `side_effect_outputs: Set[str]` (other visible modifications)
  - `requires_runtime_scope: bool` (indirection defeats analysis)
- [X] T620 [P58e] Implement `compute_function_signature()` for single label
- [X] T621 [P58e] Add `signature: Optional[FunctionSignature]` field to MLabel
- [X] T622 [P58e] Implement `compute_all_signatures()` for routine
- [X] T623 [P58e] Add `MUMPSParser.compute_signatures(routine)` public API
- [X] T624 [P58e] Unit test: simple label `CALC(X,Y)` with `S Z=X+Y Q Z` - verify signature
- [X] T625 [P58e] Unit test: label with no formal params reading external vars
- [X] T626 [P58e] Unit test: label with indirection - verify `requires_runtime_scope=True`

### Phase 58f: QUIT Value Analysis

**Purpose**: Analyze QUIT statements to determine return values

- [X] T627 [P58f] Add `return_expression: Optional[MExpr]` tracking to label analysis
- [X] T628 [P58f] Collect all QUIT statements in label and check for return values
- [X] T629 [P58f] Detect inconsistent returns (some QUIT with value, some without)
- [X] T630 [P58f] Add `has_value_quit: bool` and `has_void_quit: bool` to MLabel
- [X] T631 [P58f] Classify label as: extrinsic function (all QUITs have value), subroutine (no values), mixed
- [X] T632 [P58f] Unit test: `Q X+Y` - verify return expression captured
- [X] T633 [P58f] Unit test: mixed QUIT with/without value - flag as mixed
- [X] T634 [P58f] Unit test: `$$FUNC()` extrinsic requiring return value

### Phase 58g: Transitive Signature Propagation

**Purpose**: Propagate input/output requirements through call chains

- [X] T635 [P58g] Extend `compute_transitive_inputs()` to use FunctionSignature
- [X] T636 [P58g] Implement `compute_transitive_outputs()` for by-ref chains
- [X] T637 [P58g] Handle recursive calls (fixed-point iteration)
- [X] T638 [P58g] Handle mutual recursion between labels
- [X] T639 [P58g] Add `transitive_inputs: Set[str]` and `transitive_outputs: Set[str]` to signature
- [X] T640 [P58g] Unit test: A calls B calls C - verify transitive input propagation
- [X] T641 [P58g] Unit test: A calls B with by-ref, B modifies - verify A's outputs include it

### Phase 58h: Enable Analysis Pass by Default

**Purpose**: Run variable analysis automatically and integrate with parser flow

- [X] T642 [P58h] Add `analyze_variables=True` parameter to `parse()` and `parse_file()`
- [X] T643 [P58h] Call `analyze_variables()` after `resolve_references()` in default flow
- [X] T644 [P58h] Update `validate_asg.py` to show populated variable sets
- [X] T645 [P58h] Add `compute_signatures=True` parameter for signature analysis
- [X] T646 [P58h] Update integration tests to verify variable analysis runs
- [X] T647 [P58h] Verify all 376 MUGJ files parse with variable analysis without error

### Phase 58i: Scope Determination Classification

**Purpose**: Classify each label for code generation strategy

- [X] T648 [P58i] Create `ScopeStrategy` enum:
  - `PURE_FUNCTION` - No side effects, can be Python function with args/return
  - `FUNCTION_WITH_OUTPUTS` - Has return value + by-ref outputs
  - `SUBROUTINE` - No return value, may have side effects
  - `REQUIRES_RUNTIME` - Indirection/XECUTE defeats static analysis
- [X] T649 [P58i] Implement `classify_scope_strategy()` using FunctionSignature
- [X] T650 [P58i] Add `scope_strategy: ScopeStrategy` to MLabel
- [X] T651 [P58i] Unit test: pure function classification
- [X] T652 [P58i] Unit test: subroutine with side effects classification
- [X] T653 [P58i] Unit test: runtime-required classification (has @indirection)

### Phase 58j: Unit Tests - Edge Cases

**Purpose**: Comprehensive unit tests for complex scoping scenarios

- [X] T654 [P58j] Unit test: NEW (exclusive) - `N (X)` news all except X
- [X] T655 [P58j] Unit test: argumentless DO block scope isolation
- [X] T656 [P58j] Unit test: KILL effects on variable visibility
- [X] T657 [P58j] Unit test: nested NEW at different scope levels
- [X] T658 [P58j] Unit test: variable used before and after NEW
- [X] T659 [P58j] Unit test: same variable name in multiple labels (no conflict)
- [X] T660 [P58j] Unit test: global (^VAR) excluded from local variable analysis
- [X] T661 [P58j] Unit test: special variables ($HOROLOG etc) excluded from analysis
- [X] T662 [P58j] Unit test: subscripted variable X(I) - both X and I tracked

### Phase 58k: Integration Tests - MUGJ Validation

**Purpose**: Validate variable analysis against real MUMPS test files

- [X] T663 [P58k] Integration test: V1DO1.m - verify call parameter bindings
- [X] T664 [P58k] Integration test: V1DO2.m - verify formal parameter handling
- [X] T665 [P58k] Integration test: V1NX1.m - verify NEW command scoping
- [X] T666 [P58k] Integration test: V1NX2.m - verify exclusive NEW handling
- [X] T667 [P58k] Integration test: V1XRF1.m - verify extrinsic function signatures
- [X] T668 [P58k] Integration test: V1XRF2.m - verify by-reference parameter tracking
- [X] T669 [P58k] Integration test: Routine with 10+ labels - verify all signatures computed

### Phase 58l: Documentation - Code Generation Usage

**Purpose**: Document how to use variable analysis for Python code generation

- [X] T670 [P58l] Create `docs/variable-scoping-analysis.md` with:
  - Overview of MUMPS scoping semantics
  - API reference for analysis functions
  - FunctionSignature field descriptions
  - ScopeStrategy usage guide
- [X] T671 [P58l] Add section to `docs/asg-codegen-notes.md`:
  - Variable analysis fields on MLabel
  - FunctionSignature access patterns
  - Code generation decision tree based on ScopeStrategy
- [X] T672 [P58l] Add code examples for each ScopeStrategy:
  - PURE_FUNCTION → `def func(args) -> return_value`
  - FUNCTION_WITH_OUTPUTS → `def func(args) -> Tuple[return, modified_refs]`
  - SUBROUTINE → `def sub(args) -> None` with side effect docs
  - REQUIRES_RUNTIME → `def sub() with runtime.get_local/set_local`
- [X] T673 [P58l] Document limitations:
  - XECUTE defeats static analysis
  - Indirect references require runtime
  - KILL all/exclusive NEW limitations
- [X] T674 [P58l] Add migration guide: converting from runtime scope to static signatures (N/A - no existing users)

### Phase 58m: Formal Specification Alignment

**Purpose**: Verify implementation matches MUMPS specification exactly

- [X] T675 [P58m] Review MDC__a108014.md (Parameter passing) - verify all steps implemented
- [X] T676 [P58m] Review MDC__a108042.md (NEW) - verify all four NEW forms handled
- [X] T677 [P58m] Review MDC__a108026.md (DO) - verify call semantics match
- [X] T678 [P58m] Review MDC__a107010.md (PROCESS-STACK) - verify scope model correct
- [X] T679 [P58m] Add spec reference comments in variables.py for each behavior

**Checkpoint**: Phase 58 complete - Full variable scoping analysis enables clean Python function generation

---

## Phase 59: Variable Analysis Optimization and Performance

**Purpose**: Ensure variable analysis performs well on large routines

### Performance Tasks

- [x] T680 [P59] Profile variable analysis on largest MUGJ files
  - Created `utils/profile_variable_analysis.py` for profiling
  - MUGJ: 376 files, 18,811 lines, analyzed in ~10s total
  - VistA-M (50 largest): 26,728 lines, analyzed in ~8s
  - Analysis time: <10ms even for largest files (parsing dominates at 97%+)
  - Max analysis for 694-line file: 627ms total (well under 2s target)
- [x] T681 [P59] Cache transitive closure computations
  - SKIPPED: Profiling shows analysis is already very fast (<10ms)
  - Transitive closure computation is not a bottleneck
- [x] T682 [P59] Optimize fixed-point iteration for recursive call chains
  - SKIPPED: Current fixed-point iteration is already efficient
  - 100-iteration limit prevents infinite loops; typical runs converge in 2-3
- [x] T683 [P59] Add incremental analysis (only recompute changed labels)
  - Added `RoutineAnalysisCache` class in variables.py
  - Supports `invalidate_label()` for single-label updates
  - Rebuilds call graph and recomputes only affected labels + callers
  - Added 2 tests in TestRoutineAnalysisCache
- [x] T684 [P59] Performance test: 500-line routine analyzes in <2 seconds per SC-005
  - Added `test_analysis_performance_500_lines` in test_variables.py
  - Generates 575-line synthetic routine with 25 labels
  - Verifies full analysis completes in <2 seconds
  - Actual: ~330ms for 575-line routine (well under target)

**Checkpoint**: Phase 59 complete - Variable analysis meets performance requirements

---

## Phase 60: Code Quality Analysis & Cleanup

**Purpose**: Systematically analyze codebase for duplicates, unused code, DRY violations, inconsistencies, and test coverage gaps. Each analysis task should create sub-tasks for any improvements identified.

**Approach**: 
- Each analysis task records findings in a dedicated section below
- Improvement tasks are added as they are discovered (prefix CQ-xxx)
- Focus on code reduction and quality improvements, not new features
- Use test coverage to identify both gaps AND dead code

---

### Phase 60a: Test Coverage Analysis

**Purpose**: Use pytest-cov to identify coverage gaps and unused code

- [X] T685 [P60a] Run full test coverage: `uv run pytest --cov=m2py --cov-report=html --cov-report=term-missing`
  - **Overall coverage: 81%** (895 tests passed, 2 skipped)
  - HTML report saved to htmlcov_phase60/
  - Files below 80% coverage requiring analysis:
    - command_parser.py: 71% (170 uncovered statements)
    - for_analysis.py: 72% (13 uncovered statements)
    - exceptions.py: 67% (11 uncovered statements - MUMPSSemanticError unused)
    - semantic_analyzer.py: 78% (134 uncovered statements)
    - resolver.py: 78% (11 uncovered statements)
  - Created CQ-001 through CQ-008 for findings

- [X] T686 [P60a] Analyze coverage for src/m2py/parser/parser.py
  - Coverage: 88% (27 uncovered statements)
  - Uncovered: error handling paths, encoding fallback edge cases
  - Finding: Code is valid - represents edge cases that are hard to test
  - No CQ tasks - coverage is acceptable

- [X] T687 [P60a] Analyze coverage for src/m2py/parser/textx_classes.py
  - Coverage: 92% (7 uncovered statements)
  - Uncovered: edge cases in _unwrap_expr for rare expression patterns
  - Finding: Code is valid - represents rare parsing scenarios
  - No CQ tasks - coverage is good

- [X] T688 [P60a] Analyze coverage for src/m2py/parser/exceptions.py
  - Coverage: 67% (11 uncovered statements)
  - Uncovered: MUMPSSemanticError class (lines 79-91) - NEVER RAISED
  - Uncovered: column indicator in MUMPSSyntaxError (lines 52-55) - rarely used
  - Finding: MUMPSSemanticError is dead code → CQ-001

- [X] T689 [P60a] Analyze coverage for src/m2py/analysis/command_parser.py
  - Coverage: 71% (170 uncovered statements)
  - Major uncovered blocks:
    - Lines 851-916: Old grammar handling paths
    - Lines 937-972: _reconstruct_expr() function → CQ-002
    - Lines 1202-1256: Edge cases in command parsing
  - Finding: _reconstruct_expr is dead code, old grammar paths never hit

- [X] T690 [P60a] Analyze coverage for src/m2py/analysis/semantic_analyzer.py
  - Coverage: 78% (134 uncovered statements)
  - Major uncovered blocks:
    - Lines 311-358: Old grammar backwards compatibility → CQ-003
    - Lines 621-630: Legacy format/prompt handling → CQ-003
    - Lines 1193-1206, 1315-1375: Edge case command handling
  - Finding: Old grammar paths are dead code

- [X] T691 [P60a] Analyze coverage for src/m2py/analysis/resolver.py
  - Coverage: 78% (11 uncovered statements)
  - Uncovered: error handling paths (lines 135-137, 184-187, 209-212)
  - Finding: Valid code for edge cases, not dead code
  - No CQ tasks - coverage is acceptable for error handlers

- [X] T692 [P60a] Analyze coverage for src/m2py/analysis/goto_analysis.py
  - Coverage: 80% (14 uncovered statements)
  - Uncovered: rare GOTO classification scenarios
  - Finding: Valid code for edge cases
  - No CQ tasks - coverage is acceptable

- [X] T693 [P60a] Analyze coverage for src/m2py/analysis/for_analysis.py
  - Coverage: 72% (13 uncovered statements)
  - Uncovered: _check_var_in_indirection and some nested scope handling
  - Finding: Valid code for complex patterns, no overlap with command_parser.py
  - No CQ tasks - coverage is acceptable

- [X] T694 [P60a] Analyze coverage for src/m2py/analysis/variables.py
  - Coverage: 84% (59 uncovered statements)
  - Uncovered: RoutineAnalysisCache methods, some edge cases
  - Finding: Valid code - incremental analysis cache added recently
  - No CQ tasks - coverage is good

- [X] T695 [P60a] Analyze coverage for src/m2py/analysis/pattern_compiler.py
  - Coverage: 82% (24 uncovered statements)
  - Uncovered: rare pattern compilation edge cases
  - Finding: Valid code for complex pattern matching
  - No CQ tasks - coverage is acceptable

- [X] T696 [P60a] Analyze coverage for src/m2py/asg/*.py (elements, expressions, statements, enums)
  - elements.py: 94% (6 uncovered)
  - expressions.py: 97% (1 uncovered)
  - statements.py: 98% (2 uncovered)
  - enums.py: 100%
  - Finding: Excellent coverage, minimal uncovered code
  - No CQ tasks - ASG module is well-tested

**Checkpoint**: Coverage analysis complete - dead code and test gaps identified

---

### Phase 60b: Source File Individual Analysis

**Purpose**: Read each source file for DRY violations, unused code, inconsistencies

#### Parser Module

- [X] T697 [P60b] Analyze src/m2py/parser/parser.py (846 lines)
  - Well-structured, single responsibility (file→ASG orchestration)
  - No dead methods found
  - Some debug comments could be cleaned up (e.g., line 62)
  - No CQ tasks - code is clean

- [X] T698 [P60b] Analyze src/m2py/parser/textx_classes.py (332 lines)
  - Custom classes properly inherit from ASG classes
  - _unwrap_expr() has some complex logic but is necessary
  - No unused classes found (all used by grammar)
  - No CQ tasks - design is correct

- [X] T699 [P60b] Analyze src/m2py/parser/exceptions.py (91 lines)
  - MUMPSSemanticError is NEVER RAISED → CQ-001 (already logged)
  - MUMPSSyntaxError is used and well-designed
  - No other issues

#### Analysis Module

- [X] T700 [P60b] Analyze src/m2py/analysis/command_parser.py (1479 lines)
  - Largest file - well-organized with clear sections
  - _reconstruct_expr() is dead code → CQ-002 (already logged)
  - Some extract_*_from_line_textx functions (lines 1193-1259) appear unused
  - Created CQ-009: Review extract_*_from_line_textx function usage

- [X] T701 [P60b] Analyze src/m2py/analysis/semantic_analyzer.py (1447 lines)
  - Second largest file - complex but necessary
  - Old grammar handling code is dead → CQ-003 (already logged)
  - analyze_command() is the main entry point, well-designed
  - Some _analyze_*Command methods have similar patterns but variation is justified

- [X] T702 [P60b] Analyze src/m2py/analysis/resolver.py (214 lines)
  - Clean, focused module
  - No duplicate logic found
  - No CQ tasks

- [X] T703 [P60b] Analyze src/m2py/analysis/goto_analysis.py (253 lines)
  - Clean separation from resolver.py (resolver links refs, goto_analysis classifies)
  - No duplicate logic found
  - No CQ tasks

- [X] T704 [P60b] Analyze src/m2py/analysis/for_analysis.py (141 lines)
  - Operates on ASG (post-parsing), not on text
  - Complementary to command_parser.py FOR handling
  - No overlap or duplication
  - No CQ tasks

- [X] T705 [P60b] Analyze src/m2py/analysis/variables.py (975 lines)
  - Complex but necessary for variable scoping
  - RoutineAnalysisCache is recent addition, well-designed
  - No obvious duplication
  - No CQ tasks

- [X] T706 [P60b] Analyze src/m2py/analysis/pattern_compiler.py (351 lines)
  - Focused on MUMPS pattern → regex conversion
  - Clean, well-documented
  - No CQ tasks

#### ASG Module

- [X] T707 [P60b] Analyze src/m2py/asg/elements.py (295 lines)
  - MRoutine, MLabel, MScope, MCall classes
  - Well-designed with proper back-reference support
  - No unused classes
  - No CQ tasks

- [X] T708 [P60b] Analyze src/m2py/asg/expressions.py (274 lines)
  - All expression types used (MLiteral, MVariable, MBinaryOp, etc.)
  - MPatternMatch.compiled_regex is useful for code generation
  - No unused expression classes
  - No CQ tasks

- [X] T709 [P60b] Analyze src/m2py/asg/statements.py (464 lines)
  - All statement classes used by semantic_analyzer.py
  - Some have similar patterns (postcondition handling) but justified
  - is_kill_all property recently added, good design
  - No CQ tasks

- [X] T710 [P60b] Analyze src/m2py/asg/enums.py (163 lines)
  - All enum values used:
    - ForLoopType: all 5 types used in classification
    - GotoType: all types used in goto_analysis
    - CallType: all types used in resolver
    - PassingMode: used in variable analysis
    - ScopeStrategy: used in function signature computation
  - No unused enum values
  - No CQ tasks

#### Grammar Files

- [X] T711 [P60b] Analyze src/m2py/grammar/mumps.tx (60 lines)
  - Root grammar for routine structure
  - Clean, minimal - captures labels and line content
  - No unused rules
  - No CQ tasks

- [X] T712 [P60b] Analyze src/m2py/grammar/line.tx (23 lines)
  - Imports commands.tx, provides LineContent root
  - No overlap with mumps.tx - they're separate parse contexts
  - No CQ tasks

- [X] T713 [P60b] Analyze src/m2py/grammar/commands.tx (509 lines)
  - Comprehensive command grammar
  - All command rules used by semantic_analyzer.py
  - No CQ tasks

- [X] T714 [P60b] Analyze src/m2py/grammar/expressions.tx (355 lines)
  - Expression grammar imported by commands.tx
  - All rules used
  - No CQ tasks

#### Init/Export Files

- [X] T715 [P60b] Analyze all __init__.py files for unused exports
  - src/m2py/__init__.py: Exports MUMPSSemanticError (unused) → CQ-007
  - src/m2py/parser/__init__.py: Same issue
  - src/m2py/analysis/__init__.py: All exports used
  - src/m2py/asg/__init__.py: All exports used

**Checkpoint**: Individual source file analysis complete

---

### Phase 60c: Cross-File Duplicate Analysis

**Purpose**: Compare files likely to have duplicate code

- [X] T716 [P60c] Compare command_parser.py vs semantic_analyzer.py
  - command_parser.py: Text parsing → textX models
  - semantic_analyzer.py: textX models → ASG nodes
  - These are COMPLEMENTARY, not duplicative
  - command_parser does: parse_line_content, parse_for_command_to_asg
  - semantic_analyzer does: analyze_command (textX cmd → ASG)
  - No consolidation needed - they serve different pipeline stages

- [X] T717 [P60c] Compare for_analysis.py vs command_parser.py FOR handling
  - command_parser.py: Parses FOR syntax, classifies loop type
  - for_analysis.py: Post-parsing ASG analysis (var modification, internal QUIT)
  - COMPLEMENTARY, not duplicative - different pipeline stages
  - No consolidation needed

- [X] T718 [P60c] Compare resolver.py vs goto_analysis.py
  - resolver.py: Links MCall.target to MLabel, populates back-refs
  - goto_analysis.py: Classifies resolved GOTOs (forward/backward/loop-exit)
  - COMPLEMENTARY - resolver runs first, then goto_analysis
  - No consolidation needed

- [X] T719 [P60c] Compare textx_classes.py vs asg/*.py
  - textX custom classes inherit from ASG classes (correct design)
  - NumericLiteral(MLiteral), LocalVariable(MVariable), etc.
  - _unwrap_expr() is unique to textX layer
  - No duplicate method implementations found
  - Design is intentional - two-layer architecture

- [X] T720 [P60c] Search for duplicate regex patterns across all files
  - Only one regex compilation found in command_parser.py line 1006
  - Pattern: `r'^([A-Za-z%][A-Za-z0-9]*|[A-Za-z%])='`
  - No duplicate patterns found
  - No CQ tasks

- [X] T721 [P60c] Search for duplicate string literals across all files
  - Command names: Each command handler uses its own name - not duplicated
  - Error messages: Unique per error type
  - No significant duplication found
  - No CQ tasks

**Checkpoint**: Cross-file duplicate analysis complete

---

### Phase 60d: Test File Analysis

**Purpose**: Analyze test files for quality issues

#### Individual Test File Analysis

- [X] T722 [P60d] Analyze tests/unit/test_grammar.py (913 lines, 85 tests)
  - Purpose: Grammar acceptance tests via MUMPSParser.parse()
  - Well-organized by command type
  - Clear docstrings explain scope
  - No duplicates with other files

- [X] T723 [P60d] Analyze tests/unit/test_command_grammar.py (793 lines, 107 tests)
  - Purpose: Low-level textX command grammar tests
  - Tests grammar rules directly without semantic analysis
  - No overlap with test_grammar.py (different layers)
  - No CQ tasks

- [X] T724 [P60d] Analyze tests/unit/test_expression_grammar.py (681 lines, 83 tests)
  - Purpose: Expression grammar tests
  - Complements test_command_grammar.py
  - No duplication
  - No CQ tasks

- [X] T725 [P60d] Analyze tests/unit/test_parser.py (854 lines, 56 tests)
  - Purpose: MUMPSParser class API tests
  - Tests parse(), parse_file(), classify_patterns()
  - Clear separation from grammar tests
  - No CQ tasks

- [X] T726 [P60d] Analyze tests/unit/test_textx_classes.py (232 lines, 14 tests)
  - Purpose: Custom textX class tests
  - Tests _unwrap_expr(), expression classes
  - No overlap with grammar tests
  - No CQ tasks

- [X] T727 [P60d] Analyze tests/unit/test_semantic_analyzer.py (802 lines, 56 tests)
  - Purpose: SemanticAnalyzer and analyze_expression tests
  - Complements test_command_analysis.py
  - No duplication
  - No CQ tasks

- [X] T728 [P60d] Analyze tests/unit/test_command_analysis.py (542 lines, 44 tests)
  - Purpose: analyze_command() tests
  - Tests textX→ASG transformation
  - Clear docstring explains relationship to test_command_grammar.py
  - No CQ tasks

- [X] T729 [P60d] Analyze tests/unit/test_command_parser.py (464 lines, 53 tests)
  - Purpose: command_parser.py function tests
  - Tests parse_line_content, parse_commands_from_line
  - No overlap with test_command_analysis.py
  - No CQ tasks

- [X] T730 [P60d] Analyze tests/unit/test_classifier.py (1111 lines, 92 tests)
  - Purpose: FOR loop classification tests
  - Tests ForLoopType classification
  - Includes extract function tests
  - No CQ tasks

- [X] T731 [P60d] Analyze tests/unit/test_resolver.py and test_resolver_call_types.py
  - test_resolver.py (217 lines): Synthetic test data
  - test_resolver_call_types.py (38 lines): MUGJ regression tests
  - Potential merge candidate → CQ-006 (already logged)
  - Could consolidate into single file

- [X] T732 [P60d] Analyze tests/unit/test_goto_for_analysis.py (449 lines, 17 tests)
  - Purpose: GOTO + FOR interaction tests
  - Tests classify_gotos, GotoType values
  - No overlap with test_classifier.py (different focus)
  - No CQ tasks

- [X] T733 [P60d] Analyze tests/unit/test_variables.py (1213 lines, 61 tests)
  - Purpose: Variable analysis tests
  - Tests analyze_variables, ScopeVariables, FunctionSignature
  - Comprehensive coverage
  - No CQ tasks

- [X] T734 [P60d] Analyze tests/unit/test_pattern_compiler.py (231 lines, 26 tests)
  - Purpose: Pattern→regex compilation tests
  - Tests compile_pattern_to_regex
  - No CQ tasks

- [X] T735 [P60d] Analyze remaining unit test files:
  - test_external_calls.py (78 lines): External routine call tests
  - test_if_comma_conditions.py (86 lines): IF comma-separated condition tests
  - test_io_commands.py (154 lines): READ/WRITE/OPEN/CLOSE tests
  - test_quit_then_command.py (112 lines): QUIT followed by command tests
  - test_setup.py (72 lines): Project setup verification tests
  - test_special_constructs.py (249 lines): Indirection, pattern, etc.
  - test_unreachable_code.py (438 lines): Unreachable code detection tests
  - All have clear purposes, no duplication
  - No CQ tasks

- [X] T736 [P60d] Analyze tests/integration/test_mugj.py
  - Purpose: MUGJ test file validation
  - Tests parsing of real MUMPS files
  - Well-organized
  - No CQ tasks

#### Cross-Test File Analysis

- [X] T737 [P60d] Compare all test files for duplicate test fixtures
  - conftest.py provides shared fixtures (mugj_dir, mugj_inref_dir)
  - test_command_grammar.py has module-scoped command_metamodel fixture
  - No duplicate fixtures across files
  - No CQ tasks

- [X] T738 [P60d] Compare all test files for duplicate helper functions
  - analyze_first_command() in test_command_analysis.py is unique
  - _create_test_routine() in test_resolver.py is unique
  - No duplicate helpers found
  - No CQ tasks

- [X] T739 [P60d] Analyze test file naming and organization
  - Consistent naming: test_*.py
  - Clear separation by layer/component
  - Each file has docstring explaining scope and relationships
  - Organization is good
  - No CQ tasks

**Checkpoint**: Test file analysis complete

---

### Phase 60e: Utils Folder Analysis

**Purpose**: Analyze utils folder for cleanup opportunities

- [X] T740 [P60e] Analyze each file in utils/:

  **Debug Scripts (DELETE - CQ-004):**
  - debug_line31.py (59 lines): One-off debugging for VV2CS.m line 31 parsing issue
  - debug_line31b.py (36 lines): Continuation of above debugging

  **One-off Investigation Scripts (REVIEW - CQ-005):**
  - check_indirect_do.py (80 lines): Test script for indirect DO parsing
  - check_indirect_pattern.py (43 lines): Test script for indirect pattern match
  - check_issues.py (111 lines): Check ASG issues during validation (ad-hoc)
  - check_vv2cs.py (54 lines): Debug VV2CS.m label 5 parsing (one-off)

  **Useful Validation Scripts (KEEP):**
  - validate_asg.py (550 lines): Deep MUGJ validation with ASG display - valuable tool
  - batch_validate_mugj.py (116 lines): Batch validation for MUGJ files - useful
  - batch_validate_categories.py (215 lines): Category-based MUGJ validation
  - validate_all_remaining.py (193 lines): Complete validation of all MUGJ files
  - validate_external_calls.py (94 lines): Validate external call handling
  - verify_real_io.py (83 lines): Verify I/O command handling

  **VistA Analysis Scripts (KEEP):**
  - analyze_vista_deep.py (399 lines): Deep analysis for VistA-M validation
  - evaluate_vista.py (578 lines): Parser evaluation against VistA-M codebase

  **Other Utilities (KEEP):**
  - generate_validation_checklists.py (251 lines): Generate validation checklists
  - profile_variable_analysis.py (197 lines): Performance profiling utility
  - find_io_in_version2.py (42 lines): Find I/O commands in version 2 files

- [X] T741 [P60e] Check for duplicate utility code across utils files
  - validate_asg.py and batch_validate_mugj.py have related but different purposes
  - No significant duplicates found
  - No CQ tasks

- [X] T742 [P60e] Determine which utils are one-off debugging vs permanent tools
  - debug_line31.py, debug_line31b.py: TEMPORARY - should be removed (CQ-004)
  - check_*.py files: ONE-OFF INVESTIGATIONS - consider removal (CQ-005)
  - All other files: PERMANENT TOOLS - keep

**Checkpoint**: Utils analysis complete

---

### Phase 60f: Documentation & Configuration Consistency

**Purpose**: Check for consistency in docs and config

- [X] T743 [P60f] Review pyproject.toml for unused dependencies
  - Dependencies: textX>=4.0 (required - used extensively)
  - Dev dependencies: pytest>=7.0, pytest-cov>=4.0 (required - test framework)
  - All dependencies are actively used
  - No CQ tasks needed

- [X] T744 [P60f] Review spec files for outdated information
  - plan.md line 114: References MUMPSSemanticError (unused) → CQ-008
  - quickstart.md line 73: References MUMPSSemanticError (unused) → CQ-008
  - spec.md: Accurate to current implementation
  - data-model.md: Accurate to current ASG structure
  - No other discrepancies found

- [X] T745 [P60f] Review contracts/parser-api.md against actual API
  - parse() method: Documented, exists ✓
  - parse_file() method: Documented, exists ✓
  - resolve_references() method: Documented, exists ✓
  - classify_patterns() method: Documented, exists ✓
  - analyze_variables() method: Documented, exists ✓
  - All documented methods exist in implementation
  - No undocumented public methods
  - No CQ tasks needed

**Checkpoint**: Documentation consistency check complete

---

### Phase 60g: Improvement Task Execution

**Purpose**: Execute improvement tasks identified in previous phases

Note: This section will be populated with CQ-xxx tasks discovered during analysis.

#### Identified Improvements (add CQ-xxx tasks here as discovered)

##### Dead Code Removal

- [X] CQ-001 [REMOVE] Delete `MUMPSSemanticError` class from exceptions.py
  - DONE: Removed class definition (lines 58-91)
  - DONE: Removed from exports in parser/__init__.py and m2py/__init__.py
  - Saved ~35 lines of dead code

- [X] CQ-002 [REMOVE] Delete `_reconstruct_expr()` function from command_parser.py
  - DONE: Removed function (lines 937-972)
  - DONE: Removed fallback call from _expr_to_string (lines 918-921)
  - Saved ~40 lines of dead code

- [X] CQ-003 [REMOVE] Delete old grammar backwards compatibility code in semantic_analyzer.py
  - DONE: Removed "OLD GRAMMAR" handling for ops/right structure (lines 311-358)
  - Saved ~50 lines of dead code

##### Utils Cleanup

- [X] CQ-004 [CLEANUP] Remove debug_line31.py and debug_line31b.py from utils/
  - DONE: Removed debug_line31.py (59 lines)
  - DONE: Removed debug_line31b.py (36 lines)
  - Saved ~95 lines of debug scripts

- [X] CQ-005 [CLEANUP] Review check_*.py utils for removal candidates
  - DONE: Removed check_indirect_do.py (80 lines)
  - DONE: Removed check_indirect_pattern.py (43 lines)
  - DONE: Removed check_issues.py (111 lines)
  - DONE: Removed check_vv2cs.py (54 lines)
  - Saved ~288 lines of one-off scripts

##### Test Organization

- [ ] CQ-006 [MERGE] Consider merging test_resolver.py and test_resolver_call_types.py
  - test_resolver.py: 217 lines, uses synthetic test data
  - test_resolver_call_types.py: 38 lines, uses MUGJ files
  - DECISION: Keep separate - they test different approaches (synthetic vs real data)
  - No action needed

##### Documentation Consistency

- [X] CQ-007 [CLEANUP] Update __all__ exports to remove MUMPSSemanticError
  - DONE as part of CQ-001

- [X] CQ-008 [CLEANUP] Review spec documentation for accuracy
  - DONE: Updated plan.md line 114
  - DONE: Updated quickstart.md line 73

##### Potential Dead Code (Needs Verification)

- [X] CQ-009 [REVIEW] Review extract_*_from_line_textx function usage
  - VERIFIED: Functions ARE used - exported in __init__.py and imported in tests
  - Used by: tests/integration/test_mugj.py, and exposed in public API
  - No action needed - these are valid public API functions

**Checkpoint**: Phase 60 complete - Codebase analyzed and cleaned up

**Summary of improvements:**
- Dead code removed: ~125 lines from source files
- Debug/one-off scripts removed: ~383 lines from utils/
- Documentation updated to match current implementation
- Tests still pass: 895 passed, 2 skipped

---

## Test Coverage Gap Analysis

**Overall Coverage: 82%** (after CQ improvements)

### Coverage by Category

| Category | Coverage | Assessment |
|----------|----------|------------|
| ASG Core (asg/*) | 94-100% | ✓ Excellent |
| Parser API | 88-97% | ✓ Good |
| Analysis | 72-84% | Needs review |

### Detailed Gap Analysis

#### 1. for_analysis.py (72% coverage) - LOW PRIORITY

**Uncovered lines 80-84, 94-96, 103-104, 109, 133, 135-136:**
- `_check_var_modified_in_scope()`: Nested else_scope/body recursion paths
- `_check_quit_in_scope()`: Recursion into IF/ELSE scopes

**Assessment**: These are recursive helper functions that handle nested scopes. The main paths ARE tested. The uncovered code is for deeply nested structures (IF inside FOR inside IF). **Not critical** - edge cases that don't affect correctness.

#### 2. resolver.py (78% coverage) - LOW PRIORITY

**Uncovered lines 135-137, 184-187, 209-212:**
- Line 135-137: Handling indirected calls (already tested in other files)
- Lines 184-187, 209-212: `get_unresolved_calls()` and `get_external_calls()` utility functions

**Assessment**: These are helper/utility functions. The core `resolve_call()` function IS tested. The utilities are simple iteration - **low risk**.

#### 3. command_parser.py (74% coverage) - MIXED

**Uncovered - Edge Cases (LOW PRIORITY):**
- Lines 422-440: StringLiteral fallback in `convert_to_literal()`
- Lines 458-465, 480-481, 492-493: Edge cases in `convert_to_variable()` for subscripts
- Lines 851-916: Complex expression reconstruction for rare patterns

**Uncovered - Potentially Important (MEDIUM PRIORITY):**
- Lines 999-1004, 1021-1035: `classify_for_loop_textx()` error branches
- Lines 1161-1176, 1188-1196, 1208-1215: `extract_*_from_line_textx()` error paths

**Assessment**: Most uncovered code is error handling/fallback paths that are hard to trigger. The main parsing logic IS tested. The extract functions are used by integration tests. **Medium priority** - could add negative tests for error paths.

#### 4. semantic_analyzer.py (81% coverage) - MIXED

**Uncovered - Legacy/Fallback (LOW PRIORITY):**
- Lines 570-579: Legacy format/prompt attribute handling (old grammar)
- Lines 601-602: Old grammar IF condition handling

**Uncovered - Edge Cases (LOW PRIORITY):**
- Lines 692-695: Error handling in FOR analysis
- Lines 903-907: Edge cases in command analysis fallback

**Uncovered - I/O Commands (MEDIUM PRIORITY):**
- Lines 1142-1155: MERGE command destination/source handling
- Lines 1264-1277: VIEW command argument handling
- Lines 1287-1295, 1299-1302: USE command parameters
- Lines 1312-1324: LOCK command timeout/offset handling

**Assessment**: I/O command analysis is less tested than core commands. These are complex MUMPS I/O operations that ARE parsed correctly (MUGJ tests pass), but detailed ASG field population has gaps.

#### 5. variables.py (84% coverage) - MEDIUM PRIORITY

**Uncovered - RoutineAnalysisCache (MEDIUM PRIORITY):**
- Lines 195-230: Incremental analysis logic in `analyze()`
- Lines 239-285: Cache invalidation and rebuild paths
- Lines 889-895: Cache getter methods

**Assessment**: The `RoutineAnalysisCache` class was added for performance but its incremental analysis paths aren't fully tested. The main `analyze_variables()` function IS fully tested.

#### 6. parser.py (88% coverage) - LOW PRIORITY

**Uncovered lines 129-130, 133-146:**
- `_find_last_argumentless_do()`: Nested DO block discovery
- Lines 253-254: Error case for orphan dot-statements

**Assessment**: These handle edge cases in DO block structuring. Normal paths ARE tested.

### Recommendations

#### HIGH PRIORITY (Should Add Tests):
None - all critical parsing and analysis paths are covered.

#### MEDIUM PRIORITY (Would Improve Confidence):
1. **RoutineAnalysisCache incremental analysis** - Lines 195-285 in variables.py
   - Add test for cache invalidation and incremental recompute
   - ~2 tests needed
   - ✅ DONE: Added 6 tests in test_coverage_gaps.py::TestRoutineAnalysisCacheIncremental

2. **I/O Command ASG field population** - Lines 1142-1324 in semantic_analyzer.py
   - MERGE, VIEW, USE, LOCK command detailed testing
   - ~4 tests needed (one per command type)
   - ✅ DONE: Added 8 tests (MERGE: 3, VIEW: 3, LOCK: 5)

3. **extract_*_from_line_textx error paths** - command_parser.py
   - Add tests for malformed input handling
   - ~2 tests needed
   - ✅ DONE: Added 10 tests in test_coverage_gaps.py::TestExtractFunctionErrorPaths

4. **FOR analysis nested scope recursion** - for_analysis.py
   - Add tests for then_scope/else_scope/body recursion
   - ✅ DONE: Added 7 tests in test_coverage_gaps.py::TestForAnalysisNestedScopes

#### LOW PRIORITY (Edge Cases):
- Nested scope recursion in for_analysis.py - ✅ COVERED
- Expression reconstruction fallbacks in command_parser.py
- DO block structuring edge cases in parser.py

### Conclusion

**No critical test gaps exist.** The 85% coverage reflects:
1. Dead code removed (was dragging down coverage)
2. Error handling paths (hard to trigger, low risk)
3. I/O command edge cases (parsing works, ASG details less tested)
4. Cache optimization code (now well-tested)

The MUGJ test suite (376 real MUMPS files) provides excellent integration coverage. The uncovered code is primarily:
- Fallback/error paths that handle malformed input
- Complex I/O command edge cases

**Phase 60g Update**: Added 34 new targeted tests in test_coverage_gaps.py:
- 7 FOR analysis nested scope tests
- 8 I/O command tests (MERGE, VIEW, LOCK)
- 10 extract function error path tests
- 6 RoutineAnalysisCache incremental tests + 3 additional cache tests

Coverage improved from 82% to 85%.

---

## Phase 61: Comprehensive Code Quality Review

**Purpose**: Systematic review of all source and test files to identify quality issues including inconsistent naming, poor organization, structural problems, duplication, and unused code. Focus on improvements that reduce codebase size or improve quality without adding complexity.

**Methodology**: 
- Each analysis task reads the specified file(s) thoroughly
- Check against spec documentation for consistency (data-model.md, parser-api.md, plan.md)
- Create specific improvement tasks (CQ-xxx) for any issues found
- Prioritize removals and simplifications over additions

**Quality Criteria**:
1. **Naming**: Consistent with data-model.md terminology, clear purpose
2. **Organization**: Logical grouping, appropriate file boundaries
3. **Structure**: Clean abstractions, minimal nesting, single responsibility
4. **Duplication**: DRY violations, copy-paste code
5. **Unused**: Dead code, unused imports, obsolete functions
6. **Consistency**: API patterns, error handling, docstring style

---

### Phase 61a: Source Code Analysis - ASG Module

- [X] CQ-100 [P] Analyze `src/m2py/asg/__init__.py` (41 lines): ✓ Clean exports, well organized. Missing: MActualParameter not exported (used in variables.py). See FIX-001.

- [X] CQ-101 [P] Analyze `src/m2py/asg/elements.py` (295 lines): ✓ Clean. Minor: data-model.md shows `parent_scope` on MScope but implementation has `parent`. See FIX-002.

- [X] CQ-102 [P] Analyze `src/m2py/asg/enums.py` (163 lines): ✓ Clean. All enums have docstrings and clear purpose.

- [X] CQ-103 [P] Analyze `src/m2py/asg/expressions.py` (274 lines): ✓ Clean. MActualParameter class defined but not exported in __init__.py. See FIX-001.

- [X] CQ-104 [P] Analyze `src/m2py/asg/statements.py` (464 lines): ✓ Clean. Consistent field naming patterns.

---

### Phase 61b: Source Code Analysis - Parser Module

- [X] CQ-105 [P] Analyze `src/m2py/parser/__init__.py` (11 lines): ✓ Clean. Exports match parser-api.md contract.

- [X] CQ-106 [P] Analyze `src/m2py/parser/exceptions.py` (55 lines): ✓ Clean. MUMPSSyntaxError matches parser-api.md contract. Consistent error formatting.

- [X] CQ-107 Analyze `src/m2py/parser/parser.py` (846 lines): Large file analyzed. Issues found:
  - parser-api.md defines `classify_patterns(routine)` but implementation has `classify_patterns(source, filename)` with different signature. See FIX-003.
  - Dead code: commented print statement at line 63. See FIX-004.
  - Duplicate analysis call: `analyze_variables` called twice in `parse_file()` when `compute_signatures=True`. See FIX-005.

- [X] CQ-108 Analyze `src/m2py/parser/textx_classes.py` (332 lines): ✓ Clean. Proper inheritance from ASG classes. No redundant wrapper classes.

---

### Phase 61c: Source Code Analysis - Grammar Files

- [X] CQ-109 [P] Analyze `src/m2py/grammar/mumps.tx` (60 lines): ✓ Clean. Clear rule naming, good comments.

- [X] CQ-110 [P] Analyze `src/m2py/grammar/line.tx` (23 lines): ✓ Clean. Simple and well-organized.

- [X] CQ-111 [P] Analyze `src/m2py/grammar/commands.tx` (509 lines): Large grammar file analyzed. Issues found:
  - CommandWithArg lookahead pattern (lines 285-322) is complex and hard to maintain - many similar regex patterns could potentially be simplified. See FIX-006.
  - Duplicate `return stmt` at end of `_analyze_lock_target` in semantic_analyzer.py (copy-paste error from reviewing grammar). Not a grammar issue.

- [X] CQ-112 [P] Analyze `src/m2py/grammar/expressions.tx` (355 lines): ✓ Clean. Good operator precedence documentation. No unused rules found.

---

### Phase 61d: Source Code Analysis - Analysis Module (Large Files)

- [X] CQ-113 Analyze `src/m2py/analysis/__init__.py` (160 lines): Issues found:
  - Duplicate exports: Both `classify_for_loop` and `classify_for_loop_textx` exported (aliases). See FIX-007.
  - Similar aliases for all extract_* functions (6 pairs). Consider removing non-textx aliases if unused. See FIX-007.
  - Both `parse_*_statement` and `parse_*_command` functions exported for same commands. See FIX-008.

- [X] CQ-114 Analyze `src/m2py/analysis/command_parser.py` (1438 lines): Largest analysis file. Issues found:
  - `parse_*_statement` functions are thin wrappers around `parse_*_command` - possible consolidation. See FIX-008.
  - `_expr_to_string` function (lines 768-920) is 150+ lines with many elif branches - could use dispatch pattern. See FIX-009.
  - Duplicate pattern in `parse_for_command` and `parse_for_command_to_asg` - similar FOR param handling. See FIX-010.

- [X] CQ-115 Analyze `src/m2py/analysis/semantic_analyzer.py` (1396 lines): Second largest. Issues found:
  - Duplicate `return stmt` at line 1127 after completed `_analyze_lock_target` method - dead code. See FIX-011.
  - Handler methods follow consistent `_analyze_*Command` pattern - good.
  - `_analyze_indirect_chain` repeated logic for extracting var/global/expr. See FIX-012.

- [X] CQ-116 Analyze `src/m2py/analysis/variables.py` (975 lines): ✓ Clean. Good class organization. Well-documented MDC references.

- [X] CQ-117 Analyze `src/m2py/analysis/pattern_compiler.py` (351 lines): ✓ Clean. Well-organized pattern handling.

- [X] CQ-118 Analyze `src/m2py/analysis/goto_analysis.py` (253 lines): ✓ Clean. Good GOTO classification alignment with enums.py.

- [X] CQ-119 Analyze `src/m2py/analysis/resolver.py` (214 lines): ✓ Clean. Matches parser-api.md contract.

- [X] CQ-120 Analyze `src/m2py/analysis/for_analysis.py` (141 lines): ✓ Clean. Good organization.

---

### Phase 61e: Cross-File Duplication Analysis

- [X] CQ-121 Compare `command_parser.py` and `semantic_analyzer.py`: Issues found:
  - Both handle textX model → ASG conversion but via different approaches (parse_* vs analyze_*). 
  - semantic_analyzer.py uses `_expr_to_string` equivalent logic inline in some places.
  - Overall: Intentional separation (command_parser for string→command, semantic_analyzer for CST→ASG). See FIX-013 for potential unification.

- [X] CQ-122 Compare `resolver.py`, `goto_analysis.py`, and `for_analysis.py`: Issues found:
  - All three use `label.body.walk_statements()` traversal - this is appropriate.
  - `_classify_gotos_in_scope` and `_analyze_fors_in_scope` have similar scope-walking patterns. See FIX-014.

- [X] CQ-123 Compare ASG statement/expression handlers across `semantic_analyzer.py`: Issues found:
  - Handler methods follow consistent pattern `_analyze_*Command` returning M*Statement.
  - Common boilerplate: postcondition handling, parent setting. Could use base method. See FIX-015.

- [X] CQ-124 Compare textX custom classes in `textx_classes.py` with ASG base classes: ✓ Clean.
  - All custom classes properly inherit from ASG base.
  - No duplicate field definitions found.
  - Constructor patterns are consistent.

---

### Phase 61f: Test File Analysis - Unit Tests (Large Files)

- [X] CQ-130 Analyze `tests/unit/test_variables.py` (1403 lines): ✓ Well organized.
  - Clean test class organization: TestScopeVariables, TestVariableInfo, TestExtractExpressionVariables, TestExtractStatementVariables, TestAnalyzeVariables, TestGetDefUseChains
  - Good fixture usage and helper patterns
  - No duplication found - each class tests distinct functionality
  - Tests are already well-parameterized where appropriate

- [X] CQ-131 Analyze `tests/unit/test_classifier.py` (1111 lines): ✓ Well organized.
  - Excellent organization by classification type: TestClassifyForLoop, TestExtractForFromLine, TestParseForStatement, TestQuitDetection
  - Clear docstrings explain purpose and relationship to other test files
  - Note: This file tests the "content-only" API; command-prefixed API tests are in test_command_parser.py (this is documented)

- [X] CQ-132 Analyze `tests/unit/test_grammar.py` (912 lines): ✓ Well organized.
  - Grammar acceptance tests only (parse success, not ASG verification)
  - Organized by command type and phase (T028-T031, T049-T052, etc.)
  - Good documentation about relationship to test_command_analysis.py and test_parser.py
  - No overlap - clear purpose separation

- [X] CQ-133 Analyze `tests/unit/test_parser.py` (853 lines): ✓ Well organized.
  - Clean organization: TestMUMPSParserInit, TestMUMPSParserParse, TestMUMPSParserParseFile, TestMUMPSParserMUGJ, TestMUMPSParserGrammarIntegration, TestMUMPSParserClassifyPatterns
  - Good encoding tests (UTF-8, Latin-1 fallback)
  - Clear docstrings explaining relationship to test_grammar.py

- [X] CQ-134 Analyze `tests/unit/test_semantic_analyzer.py` (802 lines): ✓ Well organized.
  - Clean organization: TestAnalyzeExpression, TestUnwrapExpression, TestPatternMatchASG, TestIntrinsicFunctionASG
  - Good docstrings with test ticket references (T324, T325, T527, T582, etc.)
  - Command analysis split to test_command_analysis.py (documented)

- [X] CQ-135 Analyze `tests/unit/test_command_grammar.py` (792 lines): ✓ Well organized.
  - Grammar-level tests for command parsing
  - Organized by command type
  - No overlap with test_grammar.py (different granularity)

- [X] CQ-136 Analyze `tests/unit/test_expression_grammar.py` (681 lines): ✓ Well organized.
  - Expression parsing tests organized by expression type
  - Good operator precedence coverage
  - No duplicate expression tests found

- [X] CQ-137 Analyze `tests/unit/test_goto_for_analysis.py` (629 lines): ✓ Well organized.
  - Combined tests for goto_analysis.py and for_analysis.py
  - Clear organization by analysis type
  - No duplicate control flow tests

---

### Phase 61g: Test File Analysis - Unit Tests (Medium Files)

- [X] CQ-140 [P] Analyze `tests/unit/test_command_parser.py` (546 lines): ✓ Well organized.
  - Tests parse_*_command functions (textX grammar → ASG)
  - Clear distinction from test_command_analysis.py (documented in header)
  - Good class organization by command type

- [X] CQ-141 [P] Analyze `tests/unit/test_command_analysis.py` (541 lines): ✓ Well organized.
  - Tests analyze_command() semantic analysis
  - Clear distinction from test_command_parser.py (parse vs analyze)
  - Good regression test coverage (T526, T537, T567 fixes)

- [X] CQ-142 [P] Analyze `tests/unit/test_unreachable_code.py` (438 lines): ✓ Well organized.
  - Tests T531 (is_unreachable marking) and T532 (has_explicit_exit)
  - Good scope coverage (IF, FOR, DO blocks)
  - Multiple labels tested independently

- [X] CQ-143 [P] Analyze `tests/unit/test_io_commands.py` (330 lines): ✓ Well organized.
  - I/O command test coverage
  - Organized by command type (READ, WRITE, OPEN, CLOSE, USE)

- [X] CQ-144 [P] Analyze `tests/unit/test_special_constructs.py` (249 lines): ✓ Appropriate.
  - Tests for special MUMPS constructs that don't fit elsewhere
  - Content is specific enough to warrant separate file

- [X] CQ-145 [P] Analyze `tests/unit/test_textx_classes.py` (232 lines): ✓ Well organized.
  - Tests textx_classes.py custom class behavior
  - Good alignment with source module

- [X] CQ-146 [P] Analyze `tests/unit/test_pattern_compiler.py` (231 lines): ✓ Well organized.
  - Pattern compilation tests organized logically
  - Good coverage of pattern syntax

- [X] CQ-147 [P] Analyze `tests/unit/test_resolver.py` (217 lines): ✓ Well organized.
  - Resolver tests aligned with resolver.py
  - Good reference resolution coverage

---

### Phase 61h: Test File Analysis - Unit Tests (Small Files)

- [X] CQ-150 [P] Analyze `tests/unit/test_quit_then_command.py` (112 lines): ✓ Appropriate.
  - Tests specific issue #2 (QUIT followed by command)
  - Includes regression test for V1CALL1.m line 3
  - Small focused file is appropriate for this edge case

- [X] CQ-151 [P] Analyze `tests/unit/test_if_comma_conditions.py` (86 lines): ✓ Appropriate.
  - Tests specific issue #1 (IF with comma-separated conditions)
  - Includes regression test for V1BR.m line 37
  - Small focused file is appropriate for this edge case

- [X] CQ-152 [P] Analyze `tests/unit/test_external_calls.py` (78 lines): ✓ Appropriate.
  - Tests T373 (external routine call representation)
  - Focused on D ^ROUTINE / G ^ROUTINE syntax
  - No overlap with resolver tests (different concern)

- [X] CQ-153 [P] Analyze `tests/unit/test_setup.py` (72 lines): ✓ Still needed.
  - Tests package setup and fixture configuration
  - Verifies MUGJ fixtures work correctly
  - Good smoke tests for package structure

- [X] CQ-154 [P] Analyze `tests/unit/test_resolver_call_types.py` (38 lines): Issues found.
  - Very small file (38 lines, 2 tests)
  - Tests call_type population during reference resolution
  - **Recommendation**: Merge into test_resolver.py. See FIX-016.

---

### Phase 61i: Integration Test Analysis

- [X] CQ-160 Analyze `tests/integration/test_mugj.py` (1828 lines): ✓ Well organized.
  - Excellent organization by MUGJ file/series: TestV1FORARoutine, TestMUGJFileIterator, TestV1FORA1ForClassification, TestV1FORBForPatterns, TestV1FORCSeriesForPatterns, TestQuitExitPointDetection
  - Tests are true integration tests (parsing real MUGJ files)
  - Good use of fixtures for MUGJ file loading
  - No obvious duplication or parameterization opportunities

- [X] CQ-161 Analyze `tests/conftest.py` (117 lines): ✓ Well organized.
  - Clean fixture organization
  - MUGJ_BASE, MUGJ_INREF, MUGJ_OUTREF, MUGJ_U_INREF constants
  - Factory fixtures (mugj_file, mugj_files) are well-designed
  - Convenience fixtures (v1fora_source, v1fora1_source, v1fora2_source) are appropriate

---

### Phase 61j: Test-Source Alignment Analysis

- [X] CQ-170 Compare test file names with source files: ✓ Mostly aligned.
  - `test_parser.py` → `parser.py` ✓
  - `test_resolver.py` → `resolver.py` ✓
  - `test_variables.py` → `variables.py` ✓
  - `test_pattern_compiler.py` → `pattern_compiler.py` ✓
  - `test_textx_classes.py` → `textx_classes.py` ✓
  - `test_semantic_analyzer.py` → `semantic_analyzer.py` ✓
  - `test_goto_for_analysis.py` → `goto_analysis.py` + `for_analysis.py` (combined, OK)
  - `test_classifier.py` → Tests functions exported from analysis/__init__.py (classify_for_loop, etc.) - naming could be clearer. See FIX-017.
  - `test_command_parser.py` → `command_parser.py` (parse_* functions) ✓
  - `test_command_analysis.py` → `semantic_analyzer.py` (analyze_command function) - naming inconsistent. See FIX-018.

- [X] CQ-171 Check for untested source modules: ✓ All covered.
  - All source modules have corresponding test coverage
  - No gaps identified
  - Note: Some modules covered by integration tests (test_mugj.py) rather than dedicated unit tests

---

### Phase 61k: Documentation Consistency Analysis

- [X] CQ-180 Verify source code aligns with data-model.md: Issues found.
  - MScope: data-model.md shows `parent_scope` but implementation has `parent`. See FIX-002.
  - MActualParameter: Defined in expressions.py but not exported in asg/__init__.py. See FIX-001.
  - Most other classes align well with documentation.

- [X] CQ-181 Verify parser implementation aligns with parser-api.md: Issues found.
  - `classify_patterns()`: parser-api.md defines `classify_patterns(routine)` but implementation has `classify_patterns(source, filename=None)`. See FIX-003.
  - `parse_file()`: Documented correctly.
  - `resolve_references()`: Documented correctly.

- [X] CQ-182 Verify analysis passes align with plan.md architecture: ✓ Aligned.
  - Multi-pass structure (Parse → Analyze → Generate) matches documented design
  - Analysis passes (variables, goto, for) align with plan

- [X] CQ-183 Check docstring consistency: ✓ Consistent.
  - All modules use Google-style docstrings consistently
  - Args/Returns sections present where appropriate
  - Example docstrings included in public API functions

---

### Phase 61l: Final Consolidation

- [X] CQ-190 Review all CQ-xxx improvement tasks created: Complete - see Phase 62 below.
  - 18 FIX tasks identified (FIX-001 through FIX-018)
  - Prioritized by impact: High (removes dead code), Medium (naming), Low (cosmetic)

- [X] CQ-191 Execute high-priority improvements: ✓ Complete.
  - FIX-001, FIX-002, FIX-003, FIX-004, FIX-011, FIX-016 executed
  - Priority 3-4 items deferred (higher risk, lower impact)

- [X] CQ-192 Verify test suite still passes after improvements: ✓ 929 passed.

- [X] CQ-193 Update documentation if needed: ✓ data-model.md and parser-api.md updated.

---

## Phase 62: Execute Code Quality Fixes

**Purpose**: Execute the fixes identified in Phase 61. Prioritized by impact (removes code/complexity) and risk (test coverage).

**Status**: ✓ Phase 62 COMPLETE. Priorities 1-5 all addressed. Remaining items deferred (high risk or no change needed).

### Priority 1: Dead Code Removal (High Impact, Low Risk)

- [X] FIX-004: Remove dead commented print statement at line 63 in `parser.py` ✓
- [X] FIX-011: Remove duplicate `return stmt` at line 1127 in `semantic_analyzer.py` ✓

### Priority 2: API/Documentation Alignment (Medium Impact, Medium Risk)

- [X] FIX-001: Export `MActualParameter` from `asg/__init__.py` (used in variables.py) ✓
- [X] FIX-002: Update data-model.md to document `parent` field on MScope ✓
- [X] FIX-003: Update parser-api.md to document actual `classify_patterns(source, filename)` signature ✓

### Priority 3: Potential Duplication Reduction (Medium Impact, Higher Risk) - INVESTIGATED

- [X] FIX-005: Simplified `parse_file()` to use `if compute_signatures or analyze_variables:` pattern matching `parse()` ✓
- [X] FIX-007: Aliases are intentional - both used in tests for backward compatibility (no change needed) ✓
- [X] FIX-008: Wrappers are intentional - provide content-only API for ease of testing (no change needed) ✓

### Priority 4: Code Structure Improvements (Lower Impact, Higher Risk) - COMPLETED

- [X] FIX-009: Applied dispatch pattern for `_expr_to_string` - extracted 12 handler functions + dispatch table ✓
- [X] FIX-010: Consolidated FOR param handling with `_build_for_parameters()` and `_extract_loop_var()` helpers ✓
- [X] FIX-015: Added `_analyze_postcondition()` helper - reduced boilerplate in 15+ command handlers ✓
- [ ] FIX-006: Evaluate simplifying CommandWithArg lookahead pattern in commands.tx - DEFERRED (grammar changes high risk)
- [ ] FIX-012: Consider extracting common logic from `_analyze_indirect_chain` - DEFERRED (only 30 lines, low impact)
- [ ] FIX-013: Evaluate unification between command_parser.py and semantic_analyzer.py - DEFERRED (major restructuring)
- [ ] FIX-014: Consider extracting scope-walking pattern - NO CHANGE NEEDED ("for label in routine.labels" is idiomatic Python)

### Priority 5: Test File Organization (Low Impact, Low Risk)

- [X] FIX-016: Merge `test_resolver_call_types.py` (38 lines) into `test_resolver.py` ✓
- [ ] FIX-017: Consider renaming `test_classifier.py` to `test_for_classification.py` for clarity - DEFERRED (naming is clear enough)
- [ ] FIX-018: Consider renaming `test_command_analysis.py` to `test_analyze_command.py` for clarity - DEFERRED (naming is clear enough)

---

## Phase 63: Ruff Linter & Formatter Issues

**Discovered via**: `uv run ruff check src/` and `uv run ruff format --check src/`

**Status**: ✅ COMPLETE - All 929 tests pass

### RUFF-1: Unused Imports (F401) - Auto-fixable

Run: `uv run ruff check src/ --fix` to auto-fix these 20 issues.

- [X] RUFF-1a: `command_parser.py:11` - Remove unused `typing.Union` ✓
- [X] RUFF-1b: `command_parser.py:24` - Remove unused `MNakedGlobal` ✓
- [X] RUFF-1c: `for_analysis.py:12-13` - Remove unused `List`, `Set`, `Optional`, `MLabel` ✓
- [X] RUFF-1d: `resolver.py:13` - Remove unused `typing.Optional` ✓
- [X] RUFF-1e: `semantic_analyzer.py:23-53` - Remove unused `Union`, `MNakedGlobal`, `MSpecialVariable`, `MRoutine`, `MLabel`, `MScope` ✓
- [X] RUFF-1f: `variables.py:46-48` - Remove unused `Enum`, `auto`, `MScope` ✓
- [X] RUFF-1g: `variables.py:719` - Remove unused `MIndirection` ✓
- [X] RUFF-1h: `asg/elements.py:16` - Remove unused `MForStatement`, `MDoBlockStatement` ✓
- [X] RUFF-1i: `parser/parser.py:843` - Fixed: Now imports `FunctionSignature` for use in type annotation ✓

### RUFF-2: Undefined Names (F821) - Requires Manual Fix

These are actual bugs where classes are referenced but not imported:

- [X] RUFF-2a: `semantic_analyzer.py:1127` - `MOpenStatement` undefined - added to top-level imports ✓
- [X] RUFF-2b: `semantic_analyzer.py:1157` - `MCloseStatement` undefined - added to top-level imports ✓
- [X] RUFF-2c: `semantic_analyzer.py:1173` - `MUseStatement` undefined - added to top-level imports ✓
- [X] RUFF-2d: `semantic_analyzer.py:1189` - `MJobStatement` undefined - added to top-level imports ✓
- [X] RUFF-2e: `semantic_analyzer.py:1224` - `MViewStatement` undefined - added to top-level imports ✓
- [X] RUFF-2f: `parser/parser.py:823` - `FunctionSignature` undefined - added import to top-level ✓

### RUFF-3: Unused Local Variables (F841) - Review Required

These assigned-but-unused variables may indicate incomplete implementations:

- [X] RUFF-3a: `command_parser.py:1301` - `is_exclusive` removed (was dead code) ✓
- [X] RUFF-3b: `goto_analysis.py:181` - `source_line` renamed to `_source_line` (reserved for future use) ✓
- [X] RUFF-3c: `pattern_compiler.py:181` - `start` removed (was unused) ✓
- [X] RUFF-3d: `variables.py:658` - `callee_outputs` removed (was unused in transitive inputs calc) ✓
- [X] RUFF-3e: `variables.py:962` - `callee_outputs` removed (was unused in transitive outputs calc) ✓

### RUFF-4: Code Formatting - Auto-fixable

Run: `uv run ruff format src/` to auto-fix formatting in 16 files.

- [X] RUFF-4: Formatted 49 files across src/, tests/, utils/ ✓

### RUFF-5: Additional Test/Util Fixes

- [X] RUFF-5a: `test_grammar.py` - Fixed 5x E712 (use `is True`/`is False` instead of `==`) ✓
- [X] RUFF-5b: `test_classifier.py:623` - Removed return type annotation for locally-imported class ✓
- [X] RUFF-5c: `test_command_parser.py:534` - Prefixed unused `result` with underscore ✓
- [X] RUFF-5d: `test_parser.py:483` - Removed unused `routine` variable ✓
- [X] RUFF-5e: `test_mugj.py:1792` - Prefixed unused `has_exclusive_new` with underscore ✓
- [X] RUFF-5f: `batch_validate_categories.py:82-83` - Renamed `l` to `line` (E741 ambiguous name) ✓
- [X] RUFF-5g: `profile_variable_analysis.py:182` - Renamed `l` to `lines` (E741 ambiguous name) ✓
- [X] RUFF-5h: `validate_asg.py:420` - Renamed `l` to `line` (E741 ambiguous name) ✓

**Checkpoint**: Phase 63 complete - All ruff linter and formatter issues resolved

---

## Phase 64: Pyright Type Checking

**Goal**: Add comprehensive type annotations to the codebase to catch bugs early and improve IDE support.

**Current State**: 104 errors across 10 files (discovered via `uv run pyright src/`)

**Error Distribution by File**:
| File | Errors | Primary Issues |
|------|--------|----------------|
| `parser/parser.py` | 31 | Missing `body`, `_line_rest`, `_parsed_*` attributes on dataclasses |
| `analysis/variables.py` | 26 | Missing `name`, `args` attributes on base `MExpr` type |
| `analysis/for_analysis.py` | 23 | Missing `then_scope`, `else_scope`, `body` on `MStatement` |
| `asg/elements.py` | 9 | Dict/list type mismatches, missing `body`/`then_scope`/`else_scope` |
| `analysis/goto_analysis.py` | 6 | Missing `then_scope`, `else_scope`, `body` on `MStatement` |
| `analysis/command_parser.py` | 5 | `str` assigned where `MExpr` expected |
| Others | 4 | Scattered type mismatches |

**Error Distribution by Type**:
| Error Type | Count | Root Cause |
|------------|-------|------------|
| `reportAttributeAccessIssue` | 96 | Missing attributes on base types; need Union types or Protocol |
| `reportArgumentType` | 6 | Wrong type passed to function/constructor |
| `reportAssignmentType` | 2 | `None` assigned to non-Optional field |

### Phase 64a: Configure Pyright

**Purpose**: Set up pyright configuration for gradual adoption

- [X] T680 [P64a] Create `pyrightconfig.json` with initial settings:
  - `"typeCheckingMode": "basic"` (start lenient, increase later)
  - `"include": ["src"]`
  - `"exclude": ["tests", "utils"]` (initially)
  - `"reportMissingTypeStubs": false`
  - `"reportUnknownMemberType": false` (textX classes)
- [X] T681 [P64a] Add pyright to pre-commit hooks for CI enforcement
- [X] T682 [P64a] Add `py.typed` marker file to `src/m2py/` for PEP 561 compliance

### Phase 64b: Core ASG Type Fixes

**Purpose**: Fix type definitions in the foundational ASG module

- [X] T683 [P64b] `asg/expressions.py`: Fix `MFormatControl.control_type` - make Optional or set default
- [X] T684 [P64b] `asg/statements.py:106`: Fix `MReadTarget.variable` - make `Optional[MExpr]` or remove default
- [X] T685 [P64b] `asg/statements.py`: Add type alias `StatementWithBody = Union[MForStatement, MDoStatement, MDoBlockStatement]`
- [X] T686 [P64b] `asg/statements.py`: Add type alias `StatementWithScopes = Union[MIfStatement, MElseStatement]`
- [X] T687 [P64b] `asg/elements.py:61-81`: Fix `to_dict()` method - use `dict[str, Any]` return type
- [X] T688 [P64b] `asg/elements.py`: Add helper method or Protocol for statements with body/scopes

### Phase 64c: Statement Type Narrowing Helpers

**Purpose**: Create utilities to help pyright understand statement type narrowing

- [X] T689 [P64c] Create `asg/type_helpers.py` with:
  ```python
  from typing import TypeGuard
  
  def has_body(stmt: MStatement) -> TypeGuard[MForStatement | MDoStatement | MDoBlockStatement]:
      return hasattr(stmt, 'body') and stmt.body is not None
  
  def has_scopes(stmt: MStatement) -> TypeGuard[MIfStatement | MElseStatement]:
      return hasattr(stmt, 'then_scope')
  ```
- [X] T690 [P64c] Update `analysis/for_analysis.py` to use type guards (23 errors)
- [X] T691 [P64c] Update `analysis/goto_analysis.py` to use type guards (6 errors)
- [X] T692 [P64c] Update `parser/parser.py` statement handling to use type guards

### Phase 64d: MExpr Hierarchy Improvements

**Purpose**: Fix type issues with MExpr subclass attribute access

- [X] T693 [P64d] `asg/expressions.py`: Add abstract `name` property to MExpr or document it's only on subclasses
- [X] T694 [P64d] `analysis/variables.py:481-482`: Add type narrowing for `isinstance(expr, (MVariable, MGlobal))`
- [X] T695 [P64d] `analysis/variables.py:594`: Add type narrowing for function argument access
- [X] T696 [P64d] `analysis/for_analysis.py:50`: Fix `loop_var` type to be `str | MVariable` (not MExpr)

### Phase 64e: MForStatement.loop_var Type Fix

**Purpose**: Fix the loop_var field type that causes 1 error

- [X] T697 [P64e] Review MForStatement.loop_var type - should it be `str | MVariable` or `MExpr`?
- [X] T698 [P64e] Update `asg/statements.py` with correct loop_var type
- [X] T699 [P64e] Update all callers to handle the correct type

### Phase 64f: Fix String-to-MExpr Assignment Issues

**Purpose**: Fix 5 errors where `str` is assigned instead of `MExpr`

- [X] T700 [P64f] `command_parser.py:543`: Fix MForParameter value - convert str to MExpr or use different approach
- [X] T701 [P64f] `command_parser.py:622,625`: Fix MQuitStatement postcondition/return_value assignment
- [X] T702 [P64f] `command_parser.py:649`: Fix MIfStatement.conditions - should be `list[MExpr]` not `list[str]`
- [X] T703 [P64f] `command_parser.py:706`: Fix MGotoStatement.postcondition assignment
- [X] T704 [P64f] Review if these functions should return ASG nodes or strings (API decision)

### Phase 64g: Parser Internal Attribute Types

**Purpose**: Fix 10+ errors about private attributes on MLabel

- [X] T705 [P64g] `parser/parser.py`: Add private attributes to MLabel or use separate tracking dict:
  - `_line_rest: Optional[str]`
  - `_parsed_content: Optional[Any]`
  - `_parsed_commands: Optional[list]`
- [X] T706 [P64g] `parser/parser.py:618`: Add `_dot_level` to MStatement or use external tracking
- [X] T707 [P64g] Consider moving parsing state to a separate ParserContext class

### Phase 64h: Semantic Analyzer Type Fixes

**Purpose**: Fix remaining 1 error in semantic_analyzer.py

- [X] T708 [P64h] `semantic_analyzer.py:641`: Fix condition type - should be `list[MExpr]` not `MExpr | None`

### Phase 64i: textx_classes Type Fixes

**Purpose**: Fix 1 error in textx integration

- [X] T709 [P64i] `textx_classes.py:259`: Fix None assignment to str parameter

### Phase 64j: Add Type Stubs for textX

**Purpose**: Improve type checking for textX integration (optional - SKIPPED)

- [X] T710 [P64j] Create `stubs/textx/__init__.pyi` with basic type stubs - SKIPPED (not needed with basic mode)
- [X] T711 [P64j] Add `stubPath` to pyrightconfig.json - SKIPPED (not needed with basic mode)

### Phase 64k: Enable Stricter Type Checking

**Purpose**: Progressively increase type strictness

- [X] T712 [P64k] Fix all remaining errors with `"typeCheckingMode": "basic"` - DONE (0 errors)
- [ ] T713 [P64k] Upgrade to `"typeCheckingMode": "standard"` and fix new errors
- [ ] T714 [P64k] Add type annotations to public API functions
- [ ] T715 [P64k] Consider `"typeCheckingMode": "strict"` for core modules only

### Phase 64l: Test Type Annotations (Optional)

**Purpose**: Add types to test helpers (lower priority)

- [ ] T716 [P64l] Add return type annotations to test fixture functions
- [ ] T717 [P64l] Add types to helper functions in test files
- [ ] T718 [P64l] Add types to utility scripts in utils/

### Phase 64m: CI Integration

**Purpose**: Ensure type checking runs in CI

- [X] T719 [P64m] Add pyright to pre-commit hooks (local CI enforcement)
- [ ] T720 [P64m] Set up type coverage reporting
- [ ] T721 [P64m] Add badge for type coverage to README

**Checkpoint**: Phase 64 core complete - All 104 pyright errors fixed, 929 tests passing

---

## Summary: Type Error Categories and Solutions

### 1. Missing Attributes on Base Types (96 errors) - FIXED
**Pattern**: `Cannot access attribute "body" for class "MStatement"`
**Solution**: Created `asg/type_helpers.py` with TypeGuard functions and helper accessors

### 2. str vs MExpr Mismatch (6 errors) - FIXED
**Pattern**: `Argument of type "str" cannot be assigned to parameter "value" of type "MExpr"`
**Solution**: Used `_expr_to_asg_literal()` to wrap strings in MLiteral nodes

### 3. Optional vs Required Fields (2 errors) - FIXED
**Pattern**: `Type "None" is not assignable to declared type "MExpr"`
**Solution**: Changed field types to `Optional[T]` (MFormatControl.control_type, MReadTarget.variable)

---

## Phase 65: Comprehensive Documentation

**Purpose**: Create detailed, high-level documentation to guide future development and Python code generation. Documentation should cover architecture, ASG structures, analysis logic, and MUMPS-to-ASG mappings with concrete examples.

**CRITICAL Guidelines for Documentation Authors**:
- Always run `uv run python utils/validate_asg.py <file.m>` to inspect actual ASG output before documenting
- Cross-reference `mumps-reference/` for MUMPS language semantics (see `mumps-reference/README.md` for index)
- Cross-reference `textX-reference/` for textX grammar and parsing concepts
- Test actual parser behavior with: `uv run python -c "from m2py import MUMPSParser; ..."`
- Keep documentation detailed oriented but concise; do not duplicate code-level docstrings; reference specific files/functions for implementation details - if needed, expand or correct code level docstrings
- Use specs/ to understand design decisions and rationale, as well as as a source of implementation notes that may be relevant for understanding why certain choices were made and how they could be used. Bear in mind that specs/ (especially tasks.md and checklists) may contain outdated information; always verify against the current codebase.

---

### Section A: Architecture & Overview Documentation

- [X] T6501 Create `docs/README.md`: Documentation index with links to all docs, quick start, and navigation guide.

- [X] T6502 Create `docs/architecture.md`: High-level system architecture document.
  - Include data flow diagram: `MUMPS Source → textX Parser → CST → Semantic Analyzer → ASG → Analysis Passes`
  - Document the two-layer architecture (textX custom classes inheriting from ASG classes)
  - Explain why textX is used and alternatives considered (reference `specs/001-textx-semantic-graph/research.md`)
  - Directory structure explanation: `grammar/`, `asg/`, `parser/`, `analysis/`
  - Reference: `src/m2py/parser/parser.py` (MUMPSParser class), `src/m2py/parser/textx_classes.py`

- [X] T6503 Create `docs/grammar_overview.md`: Document the textX grammar structure.
  - Explain the multi-file grammar organization: `mumps.tx`, `line.tx`, `commands.tx`, `expressions.tx`
  - Document grammar rule naming conventions and how they map to ASG classes
  - Explain whitespace handling (`skipws=False`) and line structure parsing
  - Reference: `src/m2py/grammar/*.tx`, `textX-reference/grammar.md`

---

### Section B: ASG Reference Documentation

- [X] T6504 Create `docs/asg/index.md`: ASG overview and class hierarchy diagram.
  - Document ASGElement base class and common fields (source_file, line_number, column, parent)
  - Show inheritance hierarchy for all ASG node types
  - Reference: `src/m2py/asg/elements.py`

- [X] T6505 Create `docs/asg/structural_elements.md`: Document MRoutine, MLabel, MScope, MCall.
  - **MRoutine**: `name`, `labels`, `source_lines` (for $TEXT support), analysis flags (`has_unstructured_goto`, `requires_runtime_eval`)
  - **MLabel**: `name`, `formal_list`, `body`, back-references (`callers`, `goto_sources`), variable analysis fields (`variables_read`, `variables_written`, `variables_newed`, `input_variables`, `output_variables`), `signature` (FunctionSignature)
  - **MScope**: `statements`, `parent_scope`, `walk_statements()` method for recursive traversal
  - **MCall**: `name`, `offset`, `routine`, `arguments`, `target` (resolved MLabel), `call_type`, `is_resolved`, indirection fields
  - Include code generation implications for each field
  - Reference: `src/m2py/asg/elements.py`

- [X] T6506 Create `docs/asg/statements.md`: Document all MStatement subclasses.
  - **Base MStatement**: `scope`, `postcondition`, `is_unreachable`, `_dot_level`
  - **MSetStatement**: `assignments` (list of MAssignment with target/value/postcondition)
  - **MWriteStatement** / **MReadStatement**: `arguments` list, MReadTarget (with `is_char_read`, `timeout`, `fixed_length`)
  - **MIfStatement**: `condition`/`conditions` (comma-separated), `then_scope` - explain $TEST side effects
  - **MElseStatement**: `body` - explain dependence on $TEST
  - **MForStatement**: Full field documentation including analysis flags:
    - `loop_var`, `loop_var_indirect`, `parameters` (list of MForParameter)
    - `loop_type` (ForLoopType enum), `is_infinite`, `has_internal_quit`, `has_internal_goto`, `goto_exits_loop`, `exit_points`, `loop_var_modified_in_body`
  - **MGotoStatement**: `targets`, `goto_type` (GotoType enum), `exits_loops`, `is_loop_continue`
  - **MDoStatement**: `targets`, `body` (for argumentless DO blocks)
  - **MDoBlockStatement**: `body` - for dot-indented blocks
  - **MQuitStatement**: `return_value`, `exits_for`, `exits_do_block`
  - **MNewStatement**: `variables`, `exclusive`, `except_list` - explain 4 NEW forms
  - **MKillStatement**: `targets`, `exclusive`, `except_list`, `except_groups`, `is_kill_all`
  - **MMergeStatement**: `destination`, `source`
  - **MHangStatement**: `duration`
  - **MHaltStatement** / **MBreakStatement**: (no additional fields)
  - **MXecuteStatement**: `code_expressions`, `requires_runtime_eval`, `is_constant`, `constant_values`
  - **MLockStatement**: `targets`, `lock_type` (+/-/none), `timeout`
  - **MViewStatement**: `keyword`, `arguments`
  - **MOpenStatement** / **MCloseStatement** / **MUseStatement**: `device_expr`, `parameters`, `timeout`
  - **MJobStatement**: `call`, `parameters`, `timeout`
  - Reference: `src/m2py/asg/statements.py`

- [X] T6507 Create `docs/asg/expressions.md`: Document all MExpr subclasses.
  - **Base MExpr**: `result_type` (may be computed during analysis)
  - **MLiteral**: `value`, `literal_type` (LiteralType enum: STRING/INTEGER/DECIMAL), `raw_value`
  - **MVariable**: `name`, `subscripts` - local variable with optional array subscripts
  - **MGlobal**: `name`, `subscripts` - persistent global variable (^NAME)
  - **MNakedGlobal**: `subscripts`, `requires_runtime_tracking` - naked reference ^(subscripts)
  - **MBinaryOp**: `operator`, `left`, `right` - document all MUMPS operators (+,-,*,/,\,#,**,=,<,>,],]],[,&,!,_,?)
  - **MUnaryOp**: `operator`, `operand` - unary +, -, ' (NOT)
  - **MIntrinsicFunction**: `name`, `arguments` - document common functions ($EXTRACT, $PIECE, $LENGTH, $ORDER, etc.)
  - **MExtrinsicFunction**: `target` (MCall), `arguments` - user-defined $$FUNC^ROUTINE
  - **MPatternMatch**: `subject`, `pattern`, `pattern_indirect`, `operator` (?/'?), `compiled_regex`
  - **MIndirection**: `expression`, `indirection_type` (IndirectionType enum), `subscripts`, `name_indirection_subscripts`, `can_resolve_statically`, `resolved_value`
  - **MFormatControl**: `control_type` (FormatControlType enum: NEWLINE/FORMFEED/TAB/CHARCODE), `expression`
  - **MSpecialVariable**: `name` - document common SVs ($TEST, $HOROLOG, $IO, $JOB, $X, $Y, etc.)
  - **MActualParameter**: `passing_mode` (PassingMode: BY_VALUE/BY_REFERENCE/OMITTED), `expression`, `variable_name`
  - Reference: `src/m2py/asg/expressions.py`

- [X] T6508 Create `docs/asg/enums.md`: Document all ASG enumerations with code generation guidance.
  - **ForLoopType**: BOUNDED, OPEN_ENDED, STRING_LIST, MIXED, ARGUMENTLESS - Python mapping strategies
  - **ForParamType**: VALUE, RANGE, OPEN_RANGE - how each maps to Python iteration
  - **GotoType**: FORWARD_JUMP, BACKWARD_JUMP, LOOP_EXIT, MULTI_LOOP_EXIT, CROSS_LABEL, EXTERNAL, UNRESOLVED - control flow translation strategies
  - **CallType**: LABEL_CALL, OFFSET_CALL, ROUTINE_CALL, INDIRECT_CALL, UNRESOLVED - function call generation
  - **LiteralType**: STRING, INTEGER, DECIMAL - Python literal generation
  - **FormatControlType**: NEWLINE, FORMFEED, TAB, CHARCODE - I/O translation
  - **IndirectionType**: NAME, SUBSCRIPT, ARGUMENT, PATTERN, UNKNOWN - runtime vs static handling
  - **PassingMode**: BY_VALUE, BY_REFERENCE, OMITTED - Python function signature mapping
  - **ScopeStrategy**: PURE_FUNCTION, FUNCTION_WITH_OUTPUTS, SUBROUTINE, REQUIRES_RUNTIME - code gen approach
  - Reference: `src/m2py/asg/enums.py`

- [X] T6509 Create `docs/asg/type_helpers.md`: Document type narrowing utilities.
  - TypeGuard functions: `has_body`, `has_then_scope`, `has_else_scope`
  - Accessor functions: `get_body_scope`, `get_then_scope`, `get_else_scope`
  - When and why to use these (pyright type safety in analysis code)
  - Reference: `src/m2py/asg/type_helpers.py`

---

### Section C: Analysis Passes Documentation

- [X] T6510 Create `docs/analysis/index.md`: Analysis pipeline overview.
  - Required order: `parse` → `resolve_references` → `classify_gotos` → `analyze_for_loops` → `analyze_variables`
  - What each pass populates on the ASG
  - Example usage code with MUMPSParser
  - Reference: `src/m2py/parser/parser.py`, `src/m2py/analysis/__init__.py`

- [X] T6511 Create `docs/analysis/semantic_analyzer.md`: CST to ASG transformation.
  - Role of SemanticScope and ScopeVariableInfo during analysis
  - How textX wrapper nodes are unwrapped to semantic equivalents
  - Command parsing flow: raw line text → textX command parser → `analyze_command()` → MStatement
  - Expression analysis: `analyze_expression()` for building proper expression trees
  - Pattern compilation: `compile_pattern_to_regex()` for ?pattern operators
  - Reference: `src/m2py/analysis/semantic_analyzer.py`, `src/m2py/analysis/command_parser.py`

- [X] T6512 Create `docs/analysis/resolver.md`: Reference resolution pass.
  - How MCall.target is populated with resolved MLabel
  - How MLabel.callers and MLabel.goto_sources back-references are built
  - External call handling (label^routine marked as external, not resolved)
  - Unresolved call handling (indirect calls, computed targets)
  - Functions: `resolve_references()`, `get_unresolved_calls()`, `get_external_calls()`
  - Reference: `src/m2py/analysis/resolver.py`

- [X] T6513 Create `docs/analysis/goto_analysis.md`: GOTO classification pass.
  - Algorithm for classifying each MGotoStatement by GotoType
  - How enclosing FOR loops are tracked for LOOP_EXIT detection
  - Forward vs backward jump detection based on label position
  - Multi-loop exit detection and `exits_loops` population
  - Functions: `classify_gotos()`, `get_loop_exiting_gotos()`, `get_gotos_by_type()`
  - Reference: `src/m2py/analysis/goto_analysis.py`

- [X] T6514 Create `docs/analysis/for_analysis.md`: FOR loop analysis pass.
  - How `loop_type` is classified (BOUNDED, OPEN_ENDED, ARGUMENTLESS, etc.)
  - `is_infinite` detection: step=0, ARGUMENTLESS
  - `has_internal_quit` detection: QUIT directly in FOR body (not nested FOR)
  - `has_internal_goto` detection: GOTO to label outside loop
  - `loop_var_modified_in_body` detection: SET of loop variable inside body
  - Functions: `analyze_for_loops()`, `_check_var_modified_in_scope()`, `_check_quit_in_scope()`
  - Reference: `src/m2py/analysis/for_analysis.py`

- [X] T6515 Create `docs/analysis/variable_analysis.md`: Variable scope analysis pass.
  - MUMPS scoping semantics overview (implicit visibility, NEW boundaries, formal params)
  - Per-label analysis: `variables_read`, `variables_written`, `variables_newed`
  - Input/output variable computation: `input_variables`, `output_variables`
  - Call-by-reference tracking: ParameterBinding, MActualParameter.passing_mode
  - FunctionSignature computation: formal_params, required_inputs, byref_outputs, scope_strategy
  - Transitive analysis: `compute_transitive_inputs()` for call chain propagation
  - RoutineAnalysisCache for incremental updates
  - Reference: `src/m2py/analysis/variables.py`, MDC 8.1.7 (parameter passing), MDC 8.1.42 (NEW)

- [X] T6516 Create `docs/analysis/pattern_compiler.md`: MUMPS pattern to regex compilation.
  - Pattern codes: A, C, E, L, N, P, U and their regex equivalents
  - Pattern syntax: counts (n, .n, n., n.m), alternation, literal strings
  - Indirect patterns (?@X) and runtime handling
  - `compile_pattern_to_regex()` function and PatternCompileError
  - Reference: `src/m2py/analysis/pattern_compiler.py`

---

### Section D: MUMPS-to-ASG Mapping Examples

- [X] T6517 Create `docs/examples/index.md`: Examples overview and how to generate ASG output.
  - Using `utils/validate_asg.py` for inspection
  - Using `from m2py.parser import dump_asg_json` for JSON output
  - Test file locations: `tests/functional/mugj/inref/`

- [X] T6518 Create `docs/examples/basic_commands.md`: SET, WRITE, READ examples.
  - SET single: `S X=1` → MSetStatement with one MAssignment
  - SET multiple: `S A=1,B=2` → MSetStatement with multiple MAssignment
  - SET with postcondition: `S:X X=1` → MAssignment.postcondition
  - WRITE formats: `W "text",!,?10,*65` → MWriteStatement with MLiteral, MFormatControl
  - READ with timeout: `R X:10` → MReadTarget with timeout
  - Include actual ASG output from parser

- [X] T6519 Create `docs/examples/control_flow.md`: IF, ELSE, FOR, GOTO examples.
  - IF simple: `I X=1 W "yes"` → MIfStatement with condition and then_scope
  - IF comma conditions: `I X=1,Y=2` → MIfStatement.conditions list (AND semantics)
  - ELSE: `E W "no"` → MElseStatement (depends on $TEST)
  - FOR bounded: `F I=1:1:10 W I` → MForStatement with loop_type=BOUNDED
  - FOR open-ended: `F I=1:1 Q:I>10 W I` → loop_type=OPEN_ENDED, has_internal_quit=True
  - FOR argumentless: `F  R X Q:X=""` → loop_type=ARGUMENTLESS, is_infinite=True
  - FOR string-list: `F I="A","B","C"` → loop_type=STRING_LIST
  - GOTO with postcondition: `G:X LABEL` → MGotoStatement with postcondition
  - Include actual ASG output from MUGJ test files

- [X] T6520 Create `docs/examples/subroutines.md`: DO, QUIT, parameter passing examples.
  - DO simple: `D LABEL` → MDoStatement with single MCall
  - DO with args: `D CALC(A,B)` → MCall.arguments with MActualParameter
  - DO by-reference: `D SWAP(.X,.Y)` → MActualParameter with passing_mode=BY_REFERENCE
  - DO external: `D LABEL^ROUTINE` → MCall with routine field, call_type=ROUTINE_CALL
  - DO block (argumentless): `D` followed by dot lines → MDoBlockStatement
  - QUIT with value: `Q X+1` → MQuitStatement.return_value
  - NEW selective: `N X,Y` → MNewStatement.variables
  - NEW exclusive: `N (X,Y)` → MNewStatement.exclusive=True, except_list

- [X] T6521 Create `docs/examples/expressions.md`: Variables, operators, functions examples.
  - Local variable: `X` → MVariable with name
  - Subscripted: `A(1,2)` → MVariable with subscripts
  - Global: `^GLOBAL(1)` → MGlobal
  - Naked global: `^(2)` → MNakedGlobal
  - Binary ops: `A+B*C` → MBinaryOp tree (strict L-to-R, no precedence)
  - Unary ops: `-X`, `'Y` → MUnaryOp
  - Intrinsic function: `$P(X,"^",2)` → MIntrinsicFunction (name="P", $PIECE)
  - Extrinsic function: `$$CALC^MATH(X)` → MExtrinsicFunction with MCall target
  - Pattern match: `X?1N.A` → MPatternMatch with compiled_regex
  - Special variable: `$H` → MSpecialVariable (name="H", $HOROLOG)

- [X] T6522 Create `docs/examples/indirection.md`: @ operator examples.
  - Name indirection: `@X` where X contains variable name → MIndirection
  - Subscript indirection: `Y(@I)` → subscript is MIndirection
  - Argument indirection: `D @CMD` → MCall with indirection
  - Pattern indirection: `X?@PAT` → MPatternMatch.pattern_indirect
  - Multi-level: `@@A` → indirection_levels field
  - Show `requires_runtime_eval` flag and code generation implications

- [X] T6523 Create `docs/examples/advanced_patterns.md`: Complex FOR/GOTO patterns.
  - Nested FOR with QUIT: which loop does QUIT exit?
  - GOTO exiting multiple loops: MULTI_LOOP_EXIT classification
  - Loop variable modification: `loop_var_modified_in_body` flag
  - Forward vs backward jumps: how goto_type is determined
  - Cross-reference with MUGJ test files: V1FORC.m, V1FORC2.m, V1GO.m

---

### Section E: Code Generation Guide

- [X] T6524 Create `docs/codegen/index.md`: Code generation strategy overview.
  - Philosophy: semantic-preserving translation, not line-by-line
  - Using analysis flags to determine generation strategy
  - When runtime support is required vs pure Python generation
  - Reference existing notes: `specs/001-textx-semantic-graph/asg-codegen-notes.md`

- [X] T6525 Create `docs/codegen/for_loops.md`: FOR loop translation strategies.
  - BOUNDED → Python `for i in range(start, end+1, step)` (adjust for direction)
  - OPEN_ENDED → Python `while True:` with explicit break
  - ARGUMENTLESS → Python `while True:` with explicit break
  - STRING_LIST → Python `for i in [val1, val2, ...]`
  - MIXED → combination strategy
  - `has_internal_quit` → generate `break` statement
  - `has_internal_goto` with LOOP_EXIT → exception or state machine
  - `loop_var_modified_in_body` → cannot use simple range(), need while loop

- [X] T6526 Create `docs/codegen/goto_handling.md`: GOTO translation strategies.
  - FORWARD_JUMP → may map to if/elif chain
  - BACKWARD_JUMP → creates loop structure
  - LOOP_EXIT → `break` with possible state flag
  - MULTI_LOOP_EXIT → exception-based exit or state machine
  - CROSS_LABEL → function call + return flag
  - EXTERNAL → external function call
  - Structured vs unstructured goto detection (`has_unstructured_goto` flag)

- [X] T6527 Create `docs/codegen/variable_scoping.md`: Variable and function signature generation.
  - Using `input_variables` for function arguments
  - Using `output_variables` for return values or by-ref modifications
  - `scope_strategy` classification:
    - PURE_FUNCTION → clean Python function with return
    - FUNCTION_WITH_OUTPUTS → return tuple or dataclass
    - SUBROUTINE → Python function returning None
    - REQUIRES_RUNTIME → use runtime.get_local()/set_local()
  - NEW command → Python scope handling (nested functions or context managers)
  - Call-by-reference → mutable container or return modified value

- [X] T6528 Create `docs/codegen/operators.md`: Operator translation.
  - MUMPS strict left-to-right vs Python precedence - need explicit parentheses
  - Arithmetic: +, -, *, /, \ (integer div), # (modulo), ** (power)
  - String: _ (concatenation) → Python +
  - Comparison: =, <, >, ], ]] (sorts after), [ (contains)
  - Logical: &, !, ' → Python and, or, not
  - Pattern: ? → compiled regex match

- [X] T6529 Create `docs/codegen/functions.md`: Intrinsic function translation.
  - Document Python equivalents for common MUMPS functions:
    - $EXTRACT → string slicing
    - $PIECE → str.split() with indexing
    - $LENGTH → len() or count occurrences
    - $ORDER → dict/tree traversal
    - $DATA → check variable existence
    - $GET → dict.get() with default
    - $FIND → str.find()
    - $TRANSLATE → str.translate()
    - $SELECT → conditional expression or if/elif
    - $HOROLOG → datetime handling
    - $RANDOM → random.randint()
  - Functions requiring runtime support

- [X] T6530 Create `docs/codegen/runtime_requirements.md`: When runtime support is needed.
  - Indirection that cannot be statically resolved
  - XECUTE command
  - Naked global references
  - External routine calls (cross-routine)
  - $TEXT function (needs source_lines)
  - Dynamic array subscripting
  - Error handling ($ECODE, $ETRAP)

---

### Section F: Integration & Maintenance

- [X] T6531 Update root `README.md`: Add documentation links and quick reference.
  - Link to `docs/README.md`
  - Update "Getting Started" section
  - Add documentation contribution guidelines

- [X] T6532 [P] Review and update docstrings in `src/m2py/asg/elements.py`.
  - Ensure all fields documented with types and purpose
  - Add code generation guidance where relevant
  - Cross-reference to documentation files

- [X] T6533 [P] Review and update docstrings in `src/m2py/asg/statements.py`.
  - Ensure all statement types fully documented
  - Include MUMPS syntax examples in docstrings
  - Document analysis flags and when they're populated

- [X] T6534 [P] Review and update docstrings in `src/m2py/asg/expressions.py`.
  - Ensure all expression types fully documented
  - Include MUMPS syntax examples
  - Document code generation implications

- [X] T6535 [P] Review and update docstrings in `src/m2py/asg/enums.py`.
  - Ensure all enum values have clear descriptions
  - Include code generation strategy hints

- [X] T6536 [P] Review and update docstrings in `src/m2py/analysis/semantic_analyzer.py`.
  - Document analyze_command() with examples
  - Document analyze_expression() with examples
  - Explain CST → ASG transformation process

- [X] T6537 [P] Review and update docstrings in `src/m2py/analysis/variables.py`.
  - Document FunctionSignature fields
  - Document ScopeVariables and ParameterBinding
  - Explain transitive analysis algorithm

- [X] T6538 Create `docs/testing.md`: How to test and validate parser output.
  - Using pytest: `uv run pytest`
  - Using validate_asg.py: `uv run python utils/validate_asg.py <file>`
  - MUGJ test suite structure and purpose
  - Adding new test cases
  - Coverage reporting


---

## Phase 66: Enhanced Loop Variable Modification Detection

Analysis of 33,951 VistA files revealed gaps in `loop_var_modified_in_body` detection.
The current implementation only detects SET commands. Real-world code uses additional
patterns to modify loop variables.

**Status**: ✅ Phase 66a COMPLETE, ✅ Phase 66b COMPLETE

### Phase 66a: Detect READ/KILL Modifications (Low Priority) - COMPLETE

These patterns are rare (3 READ cases, few real KILL cases in VistA).

- [X] T6601 [P66a] Add MReadStatement detection to `_check_var_modified_in_scope`
  - Check if loop variable appears as MReadTarget.variable
  - ~10 lines of code
  - Test: `F I=1:1 R I Q:I=0` should set loop_var_modified_in_body=True

- [X] T6602 [P66a] Add MKillStatement detection to `_check_var_modified_in_scope`
  - Check if loop variable appears in kill targets
  - Handle both selective kill and K-all patterns
  - Test: `F D="+"... K D Q` should set loop_var_modified_in_body=True

### Phase 66b: Detect Pass-by-Reference Modifications (Medium Priority) - COMPLETE

This is the most significant gap - 11 real cases in VistA using iterator patterns.
Requires grammar extension for `.VAR` syntax.

- [X] T6610 [P66b] Add pass-by-reference detection to `analyze_for_loops`
  - Implementation complete in `for_analysis.py`
  - Scan FOR body for DO statements with loop var passed by reference
  - Check MActualParameter.passing_mode == BY_REFERENCE
  - If loop var is passed by-ref, set loop_var_modified_in_body=True (conservative)

- [X] T6612 [P66b] Add `.VAR` syntax to grammar for by-reference parameters
  - Modified `FunctionArgs` in `expressions.tx` to support `.VAR` prefix
  - Created `FunctionArg` rule: `byref=ByRefArg | expr=Expr?`
  - Created `ByRefArg` rule: `'.' var=LocalVariable`
  - Parse `D BLANK(.I)` as by-ref, `D BLANK(I)` as by-val
  - Grammar: `FunctionArgs: '(' args+=FunctionArg[','] ')'`

- [X] T6613 [P66b] Update semantic analyzer to create MActualParameter nodes
  - Added `_analyze_function_arg()` helper to create MActualParameter
  - Added `_analyze_function_args()` to process FunctionArgs
  - Create MActualParameter with PassingMode.BY_REFERENCE for `.VAR`
  - Create MActualParameter with PassingMode.BY_VALUE for expressions
  - Create MActualParameter with PassingMode.OMITTED for empty positions
  - Updated all three DO/JOB command argument processing locations

- [X] T6611 [P66b] Enable and fix pass-by-reference loop var pattern tests
  - Removed `pytest.skip` from 3 by-ref test cases
  - Test: `F I=1:1:30 D BLANK(.I)` sets loop_var_modified_in_body=True ✓
  - Test: `F I=1:1:10 D WORK(.X)` (other var) sets loop_var_modified_in_body=False ✓
  - Test: `F NEXT=1:1 D PTNEXT(.NEXT) Q:NEXT=0` sets loop_var_modified_in_body=True ✓

- [X] T6614 [P66b] Fix ExtrinsicFunction to preserve by-ref argument info
  - MUMPS spec 8.1.7: extrinsic functions also support `.actualname` call-by-reference
  - Added `_unwrap_function_args_with_passing_mode()` helper in textx_classes.py
  - Updated `ExtrinsicFunction` class to use new helper instead of `_unwrap_function_args()`
  - `$$CALC(.A,B,.C)` now correctly creates MActualParameter with PassingMode.BY_REFERENCE
  - Updated variables.py `_extract_expression_variables()` to handle MActualParameter
  - Exported `PassingMode` enum from `m2py.asg`
  - Added `test_extrinsic_with_byref_args` unit test in test_semantic_analyzer.py

---

## Phase 67: Complete Interprocedural By-Reference Analysis

**Purpose**: Enable precise by-ref tracking across call chains for optimal Python code generation.

**Background**: The infrastructure for interprocedural by-ref analysis is 95% complete:
- `FunctionSignature.byref_outputs` field exists but is never populated
- `ParameterBinding` dataclass correctly tracks `PassingMode` and `caller_var_name`  
- `bind_parameters()` creates bindings from MCall + MLabel
- `compute_transitive_outputs()` is fully implemented but gets empty `byref_outputs`

**Value for Python Code Generation**:
1. **Pure function detection**: If no `byref_outputs` and no `side_effect_outputs`, generate clean `def f() -> T`
2. **Minimal return values**: Only return by-ref params that are actually modified
3. **Accurate function signatures**: Know exactly which args are read-only vs modified
4. **FOR loop optimization**: Only set `loop_var_modified_in_body=True` when callee actually modifies it
5. **Documentation generation**: Accurate docstrings describing parameter behavior

**Dependencies**: None - existing infrastructure is sufficient

**Status**: Complete

---

### Phase 67a: Populate byref_outputs in Function Signatures

**Purpose**: Detect which formal parameters are written to within a label

- [X] T6701 [P67a] Add byref_outputs population to `compute_function_signature()`
  - File: `src/m2py/analysis/variables.py`
  - In `compute_function_signature()`, after getting `scope_vars`:
    ```python
    # Detect formal params that are written (potential by-ref outputs)
    for formal_param in label.formal_list or []:
        if formal_param in scope_vars.writes:
            sig.byref_outputs.add(formal_param)
    ```
  - ~5 lines of code

- [X] T6702 [P67a] Unit test: formal param written → in byref_outputs
  - File: `tests/unit/test_variables.py`
  - Test case:
    ```mumps
    SWAP(X,Y)
        N T
        S T=X,X=Y,Y=T
        Q
    ```
  - Verify: `signature.byref_outputs == {"X", "Y"}`

- [X] T6703 [P67a] Unit test: formal param only read → NOT in byref_outputs
  - File: `tests/unit/test_variables.py`
  - Test case:
    ```mumps
    ADD(A,B)
        N R
        S R=A+B
        Q R
    ```
  - Verify: `signature.byref_outputs == set()` (A, B only read, not written)

- [X] T6704 [P67a] Unit test: formal param conditionally written
  - File: `tests/unit/test_variables.py`
  - Test case:
    ```mumps
    MAYBE(X)
        I X<0 S X=0
        Q
    ```
  - Verify: `signature.byref_outputs == {"X"}` (conservative - written in any path)

---

### Phase 67b: Verify Transitive Output Propagation

**Purpose**: Ensure `compute_transitive_outputs()` works correctly with populated byref_outputs

- [X] T6710 [P67b] Unit test: direct by-ref modification propagates
  - File: `tests/unit/test_variables.py`
  - Test case:
    ```mumps
    MAIN   D WORKER(.X)
           Q
    WORKER(A)
           S A=A+1
           Q
    ```
  - Verify: After transitive analysis, MAIN's `transitive_outputs` includes `X`

- [X] T6711 [P67b] Unit test: nested call chain with by-ref
  - File: `tests/unit/test_variables.py`
  - Test case:
    ```mumps
    OUTER  D MIDDLE(.X)
           Q
    MIDDLE(A)
           D INNER(.A)
           Q
    INNER(B)
           S B=B*2
           Q
    ```
  - Verify: OUTER's `transitive_outputs` includes `X` (via MIDDLE→INNER chain)

- [X] T6712 [P67b] Unit test: by-ref param NOT modified → NOT in transitive outputs
  - File: `tests/unit/test_variables.py`
  - Test case:
    ```mumps
    CALLER D READER(.X)
           Q
    READER(A)
           W A   ; Only reads A, doesn't write
           Q
    ```
  - Verify: CALLER's `transitive_outputs` does NOT include `X`

- [X] T6713 [P67b] Integration test with real MUGJ file
  - File: `tests/integration/test_mugj.py`
  - Find or create MUGJ test with by-ref call chain
  - Verify transitive analysis produces expected results

---

### Phase 67c: Reorder Analysis Passes

**Purpose**: Run variable analysis before FOR analysis so signatures are available

- [X] T6720 [P67c] Update analysis order in `MUMPSParser.parse()`
  - File: `src/m2py/parser/parser.py`
  - Current order: `resolve → classify_gotos → analyze_for_loops → analyze_variables`
  - New order: `resolve → analyze_variables → classify_gotos → analyze_for_loops`
  - Rationale: FOR analysis needs callee signatures to check byref_outputs

- [X] T6721 [P67c] Update analysis order in `MUMPSParser.parse_file()`
  - File: `src/m2py/parser/parser.py`
  - Same reordering as parse()

- [X] T6722 [P67c] Verify no circular dependencies
  - Confirm: variable analysis doesn't depend on GOTO/FOR analysis
  - Confirm: GOTO analysis doesn't depend on FOR analysis
  - Run full test suite to verify

- [X] T6723 [P67c] Update `docs/analysis/index.md` with new order
  - Document: `parse → resolve → analyze_variables → classify_gotos → analyze_for_loops`
  - Explain: Why this order enables signature-aware FOR analysis

---

### Phase 67d: Use Signatures in FOR Loop Analysis

**Purpose**: Replace conservative by-ref check with signature-aware check

- [X] T6730 [P67d] Create `_get_callee_signature()` helper in for_analysis.py
  - File: `src/m2py/analysis/for_analysis.py`
  - Helper to look up callee's FunctionSignature from routine
  - Handle unresolved calls (return None)

- [X] T6731 [P67d] Update `_check_var_passed_byref_in_scope()` to use signatures
  - File: `src/m2py/analysis/for_analysis.py`
  - Current: Returns True if var passed by-ref to ANY call (conservative)
  - New: Only return True if callee's `byref_outputs` includes the formal param
  - Fallback: If signature unavailable (external call), use conservative approach

- [X] T6732 [P67d] Unit test: by-ref to callee that doesn't modify → False
  - File: `tests/unit/test_goto_for_analysis.py`
  - Test case:
    ```mumps
    LOOP   F I=1:1:10 D READER(.I)
           Q
    READER(A)
           W A
           Q
    ```
  - Current (conservative): `loop_var_modified_in_body=True`
  - New (signature-aware): `loop_var_modified_in_body=False`

- [X] T6733 [P67d] Unit test: by-ref to callee that modifies → True
  - File: `tests/unit/test_goto_for_analysis.py`
  - Test case:
    ```mumps
    LOOP   F I=1:1:10 D INCR(.I)
           Q
    INCR(A)
           S A=A+1
           Q
    ```
  - Verify: `loop_var_modified_in_body=True` (correct detection)

- [X] T6734 [P67d] Unit test: by-ref to external routine → conservative True
  - File: `tests/unit/test_goto_for_analysis.py`
  - Test case:
    ```mumps
    LOOP   F I=1:1:10 D UNKNOWN^EXTERNAL(.I)
           Q
    ```
  - Verify: `loop_var_modified_in_body=True` (fallback to conservative)

---

### Phase 67e: Update ScopeStrategy Classification

**Purpose**: Leverage populated byref_outputs for better function classification

- [X] T6740 [P67e] Verify classify_scope_strategy() uses byref_outputs correctly
  - File: `src/m2py/analysis/variables.py`
  - Already checks `sig.byref_outputs` - now it will have real data
  - FUNCTION_WITH_OUTPUTS: has return + byref_outputs
  - PURE_FUNCTION: has return, no byref_outputs, no side_effect_outputs

- [X] T6741 [P67e] Unit test: pure function classification
  - File: `tests/unit/test_variables.py`
  - Test case:
    ```mumps
    ADD(A,B)
        N R
        S R=A+B
        Q R
    ```
  - Verify: `scope_strategy == ScopeStrategy.PURE_FUNCTION`

- [X] T6742 [P67e] Unit test: function with outputs classification
  - File: `tests/unit/test_variables.py`
  - Test case:
    ```mumps
    CALC(A,B)
        S A=A+B
        Q A
    ```
  - Verify: `scope_strategy == ScopeStrategy.FUNCTION_WITH_OUTPUTS`
  - Verify: `byref_outputs == {"A"}`

---

### Phase 67f: Documentation Updates

**Purpose**: Update all documentation to reflect new analysis capabilities

- [X] T6750 [P67f] Update `docs/analysis/variable_analysis.md`
  - Document how `byref_outputs` is computed
  - Add examples showing formal params written → in byref_outputs
  - Document transitive_outputs propagation through by-ref chains

- [X] T6751 [P67f] Update `docs/analysis/for_analysis.md`
  - Document signature-aware by-ref detection
  - Explain fallback to conservative approach for external calls
  - Update examples showing precise vs conservative detection

- [X] T6752 [P67f] Update `docs/analysis/index.md`
  - Update analysis pass order diagram
  - Explain why variable analysis must precede FOR analysis
  - Document dependencies between analysis passes

- [X] T6753 [P67f] Update `docs/codegen/variable_scoping.md`
  - Document how `byref_outputs` enables better Python generation
  - Add examples: minimal return values, pure function detection
  - Update decision tree to show byref_outputs usage

- [X] T6754 [P67f] Update `docs/asg/index.md` FunctionSignature section
  - Document `byref_outputs` field (now populated)
  - Document `transitive_outputs` field behavior
  - Add cross-reference to variable_analysis.md

- [X] T6755 [P67f] Update docstrings in `src/m2py/analysis/variables.py`
  - `compute_function_signature()`: Document byref_outputs computation
  - `compute_transitive_outputs()`: Document integration with byref_outputs
  - `FunctionSignature`: Update field descriptions

---

### Phase 67g: Final Validation

**Purpose**: Ensure all changes work together correctly

- [X] T6760 [P67g] Run full test suite and verify no regressions
  - `uv run pytest` - all tests must pass
  - Check for any test failures related to analysis ordering

- [X] T6761 [P67g] Run pyright and verify no new type errors
  - `uv run pyright src/`
  - Fix any type issues introduced by changes

- [X] T6762 [P67g] Validate with VistA sample files
  - Run `utils/validate_asg.py` on several VistA files
  - Verify byref_outputs is populated correctly
  - Verify transitive_outputs shows expected propagation

- [X] T6763 [P67g] Performance check
  - Run `utils/profile_variable_analysis.py` on large files
  - Ensure no significant performance regression from analysis reordering

**Checkpoint**: Phase 67 complete - Full interprocedural by-ref analysis enabled
---

## Phase 68: ASG Implementation Gaps Cleanup

**Purpose**: Address implementation gaps identified during documentation accuracy review - fields/enums that are defined in ASG but never populated or used.

**Background**: During a comprehensive documentation vs. source code review, 5 implementation gaps were identified:
1. `GotoType.CROSS_LABEL` - Enum value defined but never assigned
2. `MForStatement.goto_exits_loop` - Field defined but never set (redundant with existing analysis)
3. `MGotoStatement.is_loop_continue` - Field defined but never set
4. `MRoutine.requires_runtime_eval` - Field defined but never populated (high value for codegen)
5. `MRoutine.global_refs` - Field defined but never populated

**Value for Code Generation**: Proper population of these fields enables more accurate Python code generation, better optimization decisions, and cleaner function signatures.

---

### Phase 68a: Remove Redundant Field

- [X] T6801 [P68a] Remove `MForStatement.goto_exits_loop` field
  - File: `src/m2py/asg/statements.py`
  - This field is redundant - `analyze_for_loops()` already populates `goto_entry_points` and `exit_point_stmts` on labels/scopes
  - Action: Delete the field definition and any references
  - Update tests if any reference this field

- [X] T6802 [P68a] Update documentation referencing goto_exits_loop
  - File: `docs/asg/structural_elements.md`, `docs/codegen/goto_handling.md`
  - Remove mentions of the deleted field
  - Clarify that GOTO-exiting-FOR is tracked via `label.exit_point_stmts`

---

### Phase 68b: Add is_cross_label Flag to MGotoStatement

- [X] T6810 [P68b] Add `is_cross_label: bool` field to `MGotoStatement` and set it in `classify_gotos()`
  - Files: `src/m2py/asg/statements.py`, `src/m2py/analysis/goto_analysis.py`
  - Added `is_cross_label: bool = False` as an orthogonal flag to track whether GOTO crosses label boundaries
  - This separates direction (FORWARD_JUMP/BACKWARD_JUMP) from scope (same-label vs cross-label)
  - Deprecated `GotoType.CROSS_LABEL` enum value - use `is_cross_label` flag instead
  - Now codegen can use both direction AND scope info (e.g., `LOOP_EXIT` + `is_cross_label=True`)

- [X] T6811 [P68b] Add unit tests for is_cross_label detection
  - File: `tests/unit/test_goto_for_analysis.py`
  - Test cases:
    1. GOTO to different label → `FORWARD_JUMP` + `is_cross_label=True`
    2. GOTO within same label → `FORWARD_JUMP` + `is_cross_label=False`
  - Verify: `goto.goto_type == GotoType.FORWARD_JUMP and goto.is_cross_label == True`

- [X] T6812 [P68b] Update documentation for is_cross_label
  - Files: `docs/asg/enums.md`, `docs/asg/statements.md`, `docs/analysis/goto_analysis.md`
  - Document `is_cross_label` as orthogonal to `goto_type`
  - Show code gen strategies for different combinations

---

### Phase 68c: Implement MGotoStatement.is_loop_continue

- [X] T6820 [P68c] Implement `is_loop_continue` detection in `classify_gotos()`
  - File: `src/m2py/analysis/goto_analysis.py`
  - Detect GOTO that jumps back to the start of an enclosing FOR loop (continue semantics)
  - Pattern: GOTO target is the label containing the FOR, and GOTO is inside the FOR body
  - Set: `goto.is_loop_continue = True`

- [X] T6821 [P68c] Add unit tests for is_loop_continue
  - File: `tests/unit/test_goto_for_analysis.py`
  - Test cases:
    1. GOTO back to label containing FOR from inside FOR body → is_loop_continue=True
    2. GOTO forward past FOR loop → is_loop_continue=False
    3. GOTO back but not to loop start → is_loop_continue=False

- [X] T6822 [P68c] Update documentation for is_loop_continue
  - File: `docs/asg/statements.md`, `docs/codegen/goto_handling.md`
  - Document the is_loop_continue field and when it's set
  - Explain how codegen can use this to generate Python `continue` statements

---

### Phase 68d: Implement MRoutine.requires_runtime_eval

- [X] T6830 [P68d] Implement `requires_runtime_eval` rollup in variable analysis
  - File: `src/m2py/analysis/variables.py`
  - After computing all label signatures, check if ANY label has `signature.requires_runtime_eval`
  - Set: `routine.requires_runtime_eval = any(label.signature.requires_runtime_eval for label in routine.labels if label.signature)`

- [X] T6831 [P68d] Add unit tests for requires_runtime_eval
  - File: `tests/unit/test_variables.py`
  - Test cases:
    1. Routine with no indirection → requires_runtime_eval=False
    2. Routine with @VAR indirection in one label → requires_runtime_eval=True
    3. Routine with XECUTE in one label → requires_runtime_eval=True

- [X] T6832 [P68d] Update documentation for requires_runtime_eval
  - File: `docs/asg/structural_elements.md`, `docs/codegen/index.md`
  - Document the requires_runtime_eval field and its source
  - Explain how codegen uses this for optimization decisions

---

### Phase 68e: Implement MRoutine.global_refs

- [X] T6840 [P68e] Populate `global_refs` during resolver pass
  - File: `src/m2py/analysis/resolver.py`
  - During `resolve_references()`, collect all MGlobal and MNakedGlobal nodes
  - Populate: `routine.global_refs = {global.name for global in all_globals}`
  - This enables fast lookup of which globals a routine accesses

- [X] T6841 [P68e] Add unit tests for global_refs population
  - File: `tests/unit/test_resolver.py`
  - Test cases:
    1. Routine with no globals → global_refs=set()
    2. Routine with ^GLOBAL → global_refs={"GLOBAL"}
    3. Routine with multiple globals ^A, ^B → global_refs={"A", "B"}
    4. Routine with naked global ^(x) → handled appropriately (may be empty set or special marker)

- [X] T6842 [P68e] Update documentation for global_refs
  - File: `docs/asg/structural_elements.md`
  - Document the global_refs field
  - Explain how it's populated and what it's used for

---

### Phase 68f: Final Validation

- [X] T6850 [P68f] Run full test suite and verify no regressions
  - `uv run pytest` - all tests must pass

- [X] T6851 [P68f] Run pyright and verify no new type errors
  - `uv run pyright src/`

- [ ] T6852 [P68f] Update integration tests to verify new fields
  - Add assertions in existing MUGJ tests for new field population

**Checkpoint**: Phase 68 complete - All ASG implementation gaps resolved

## Phase 69: Grammar and Parser Consistency Review

### Findings from Review

This phase documents findings from a consistency, correctness, and completion review of the grammar (.tx) and parser (.py) files.

#### Issue 1: Outdated Comment in parser.py `__init__`
**File:** [src/m2py/parser/parser.py#L395-L402](src/m2py/parser/parser.py#L395-L402)  
**Status:** Minor - Comment Cleanup  
**Finding:** The comment `# Custom classes will be registered here as ASG types are implemented` is outdated.  
**Analysis:** The architecture intentionally uses a two-phase approach:
1. `mumps.tx` parses routine structure (labels, lines) without custom classes
2. `parse_commands_from_line()` in `command_parser.py` uses custom classes for command/expression parsing

This is correct behavior, not a bug. The comment is simply outdated and misleading.  
**Solution:** Update comment to describe the current two-phase parsing architecture.

#### Issue 2: textX Line/Column Info Not Extracted in Error Handling
**File:** [src/m2py/parser/parser.py#L450-L456](src/m2py/parser/parser.py#L450-L456)  
**Status:** Improvement - Error Reporting  
**Finding:** When catching textX exceptions, line/column info from `TextXSyntaxError` is not extracted.  
**Analysis:** Verified that `TextXSyntaxError` has `line` and `col` attributes, but the current code only uses `str(e)`. The structured `MUMPSSyntaxError.line` and `.column` attributes remain `None`.  
**Solution:** Extract line/column from textX exceptions when available and pass to `MUMPSSyntaxError`.

#### Issue 3: Outdated "Placeholder" Comment in `_build_routine`
**File:** [src/m2py/parser/parser.py#L516-L520](src/m2py/parser/parser.py#L516-L520)  
**Status:** Minor - Comment Cleanup  
**Finding:** Comment says "This is a placeholder that will be expanded..."  
**Analysis:** The method is fully implemented and handles LabelLine, ContLine, and preamble labels. The "placeholder" phrasing implies incomplete work.  
**Solution:** Reframe to describe current behavior without "placeholder" terminology.

#### Issue 4: Change-Centric Wording in textx_classes.py
**File:** [src/m2py/parser/textx_classes.py#L285](src/m2py/parser/textx_classes.py#L285), [#L298](src/m2py/parser/textx_classes.py#L298)  
**Status:** Minor - Comment Cleanup  
**Finding:** Comments reference "T538 fix" which is change-centric rather than describing current behavior.  
**Analysis:** T538 references appear in docstrings for `IntrinsicFunction` and `IntrinsicFunctionNoArgs`. These should state the current grammar rule requirements.  
**Solution:** Reframe comments to state current behavior (e.g., "IntrinsicFunction requires parenthesized arguments" rather than "T538 fix").

#### Issue 5: "New Approach" Wording in _build_label
**File:** [src/m2py/parser/parser.py#L648-L649](src/m2py/parser/parser.py#L648-L649)  
**Status:** Minor - Comment Cleanup  
**Finding:** Comment says "Parse line content using textX grammar (new approach)"  
**Analysis:** Implies a transition rather than describing current behavior.  
**Solution:** Remove "new approach" phrasing.

#### Non-Issue: `]]` Operator in BinaryOp Regex
**File:** [src/m2py/grammar/expressions.tx#L50-L55](src/m2py/grammar/expressions.tx#L50-L55)  
**Status:** Correct - No Change Needed  
**Finding:** Initially appeared that `]]` might be incorrectly included as a binary operator.  
**Analysis:** Per MUMPS 1995 ANSI standard (see [mumps-reference/1995__a902027.md](mumps-reference/1995__a902027.md)), `]]` is the "sorts after" operator added in the 1995 standard. The grammar is correct.

#### Non-Issue: Empty `classes=[]` in MUMPSParser
**File:** [src/m2py/parser/parser.py#L398-L402](src/m2py/parser/parser.py#L398-L402)  
**Status:** Correct - No Change Needed  
**Finding:** Custom classes are not registered with the main metamodel.  
**Analysis:** This is intentional. The two-phase architecture uses `mumps.tx` for structure parsing only; command parsing with custom classes happens in `command_parser.py`. All 56 parser tests pass, confirming the architecture works correctly.

### Tasks

- [X] **1.1** Update comment in `MUMPSParser.__init__` to describe two-phase parsing architecture
- [X] **1.2** Extract line/column from textX exceptions in error handler
- [X] **1.3** Update `_build_routine` docstring to remove "placeholder" phrasing
- [X] **1.4** Reframe "T538 fix" comments in textx_classes.py to describe current behavior
- [X] **1.5** Remove "new approach" phrasing from `_build_label` comment
---

## Phase 70: Additional Grammar Comment Cleanup

### Findings from Review

This phase addresses additional findings from a consistency and correctness review, focusing on orphan dot-lines and change-centric comments in grammar files.

#### Issue 1: Orphan Dot-Lines Handling
**File:** [src/m2py/parser/parser.py#L252-L264](src/m2py/parser/parser.py#L252-L264)  
**Status:** No Change Needed - Spec-Compliant Behavior  
**Finding:** `_structure_do_blocks` treats dot-lines with no owning DO as an "error case" but keeps the statements un-nested without surfacing an error.  
**Analysis:** Per MUMPS ANSI standard 1995 section 6.3 (Routine Execution): "Lines which have a LEVEL greater than the current execution level are **ignored**, i.e., not executed." Orphan dot-lines are valid MUMPS syntax that simply does not execute at runtime - they are not malformed input requiring a parse error. The current behavior correctly preserves the source structure.  
**Solution:** The comment at line 262 ("No DO found - this is an error case, but keep statements") could be clarified to note this matches MUMPS spec behavior. However, the logic itself is correct and no code change is required.

#### Issue 2: "Enhanced to" Wording in commands.tx GotoIndirect
**File:** [src/m2py/grammar/commands.tx#L214-L215](src/m2py/grammar/commands.tx#L214-L215)  
**Status:** Minor - Comment Cleanup  
**Finding:** Comment says "GOTO indirection: Enhanced to support full label reference structure"  
**Analysis:** "Enhanced to" is change-centric language referencing a prior state. Should describe current behavior.  
**Solution:** Reframe to "GOTO indirection: Supports full label reference structure including nested indirection, offset, and routine components"

#### Issue 3: "Enhanced to" Wording in commands.tx DoIndirect
**File:** [src/m2py/grammar/commands.tx#L238-L240](src/m2py/grammar/commands.tx#L238-L240)  
**Status:** Minor - Comment Cleanup  
**Finding:** Comment says "DO indirection: Enhanced to support full label reference structure"  
**Analysis:** Same issue as GotoIndirect - change-centric rather than descriptive.  
**Solution:** Reframe to "DO indirection: Supports full label reference structure with nested indirection (@@, @@@), offset, routine, and arguments"

#### Issue 4: "(T538 fix...)" Wording in expressions.tx
**File:** [src/m2py/grammar/expressions.tx#L131](src/m2py/grammar/expressions.tx#L131)  
**Status:** Minor - Comment Cleanup  
**Finding:** Comment says "(T538 fix for abbreviated special variables)"  
**Analysis:** T538 task reference is change-centric. The comment should explain WHY the ordering matters, not reference a task number.  
**Solution:** Reframe to "Ordering ensures abbreviated special variables like $S/$H/$T parse correctly before IntrinsicFunctionNoArgs catch-all"

#### Issue 5: "(T538 fix)" in OffsetPrimaryExpr
**File:** [src/m2py/grammar/expressions.tx#L181](src/m2py/grammar/expressions.tx#L181)  
**Status:** Minor - Comment Cleanup  
**Finding:** Comment says "Ordering for $ items same as PrimaryExpr (T538 fix)"  
**Analysis:** Same issue - task reference should be removed.  
**Solution:** Reframe to "Ordering for $ items same as PrimaryExpr to ensure correct parsing of abbreviated special variables"

### Tasks

- [X] **2.1** Clarify comment in `_structure_do_blocks` at line 262 to note MUMPS spec behavior (optional improvement)
- [X] **2.2** Update GotoIndirect comment in commands.tx to remove "Enhanced to" phrasing
- [X] **2.3** Update DoIndirect comment in commands.tx to remove "Enhanced to" phrasing
- [X] **2.4** Update PrimaryExpr comment in expressions.tx to remove "(T538 fix...)" reference
- [X] **2.5** Update OffsetPrimaryExpr comment in expressions.tx to remove "(T538 fix)" reference

---

## Phase 71: Parser File Encoding Consistency

### Findings from Review

This phase addresses an encoding inconsistency discovered during a grammar and parser consistency review.

#### Issue 1: `classify_patterns_from_file` Lacks Latin-1 Fallback
**File:** [src/m2py/parser/parser.py#L781](src/m2py/parser/parser.py#L781)  
**Status:** Bug Fix Needed  
**Finding:** `classify_patterns_from_file` uses only UTF-8 encoding, while `parse_file` (lines 499-505) has a UTF-8-to-Latin-1 fallback for legacy VistA files.  
**Analysis:** Some VistA MUMPS files contain Latin-1/CP1252 encoded characters (°, ö, §, ÷) that fail to decode as UTF-8. `parse_file` correctly handles this with a try/except fallback, but `classify_patterns_from_file` does not have this fallback and will raise `UnicodeDecodeError` on these files.  
**Solution:** Apply the same encoding fallback pattern from `parse_file` to `classify_patterns_from_file`.

### Tasks

- [X] **3.1** Add UTF-8 to Latin-1 encoding fallback to `classify_patterns_from_file`
  - File: `src/m2py/parser/parser.py`
  - Match the pattern used in `parse_file` (lines 499-505)

- [X] **3.2** Add test for Latin-1 encoded file handling in classify_patterns_from_file
  - File: `tests/unit/test_parser.py`
  - Create test that verifies both methods handle Latin-1 files consistently

**Checkpoint**: Phase 71 complete - Parser file encoding is consistent across all file-loading methods

---

## Phase 72: ASG Module Consistency Review

### Findings from Review

This phase addresses consistency, completeness, and clarity issues in the ASG module files discovered during a code review.

#### Finding 1: `IndirectionType` and `ScopeStrategy` Not Exported from `m2py.asg`
**Files:** [src/m2py/asg/__init__.py](src/m2py/asg/__init__.py), [src/m2py/asg/enums.py](src/m2py/asg/enums.py#L119-L175)  
**Status:** Fix Needed - Export Inconsistency  
**Finding:** `IndirectionType` and `ScopeStrategy` enums are defined in `enums.py` but not re-exported from `m2py.asg.__init__.py`. All other enums (`ForLoopType`, `ForParamType`, `GotoType`, `CallType`, `LiteralType`, `FormatControlType`, `PassingMode`) are exported.  
**Analysis:** Verified with `from m2py.asg import IndirectionType` - fails with `ImportError`. These enums are used internally (`expressions.py` imports `IndirectionType`, `variables.py` imports `ScopeStrategy`) but external code must use `from m2py.asg.enums import ...`. For API consistency, all public enums should be re-exported from the package `__init__.py`.  
**Solution:** Add `IndirectionType` and `ScopeStrategy` to the imports and `__all__` in `src/m2py/asg/__init__.py`.

#### Finding 2: `MAssignment`, `MReadTarget`, `MForParameter` Are Not ASGElements
**Files:** [src/m2py/asg/statements.py#L51-L62](src/m2py/asg/statements.py#L51-L62), [#L92-L116](src/m2py/asg/statements.py#L92-L116), [#L181-L195](src/m2py/asg/statements.py#L181-L195)  
**Status:** Not an Issue - Intentional Design  
**Finding:** `MAssignment`, `MReadTarget`, and `MForParameter` are plain `@dataclass` types that do not inherit from `ASGElement`, so they lack source tracking (`source_file`, `line_number`, `column`) and parent references.  
**Analysis:** These types are sub-components of statements, not standalone ASG nodes:
- `MAssignment` is a target=value pair within `MSetStatement.assignments`
- `MReadTarget` is a read target within `MReadStatement.arguments`
- `MForParameter` is a loop parameter within `MForStatement.parameters`

They inherit source position from their containing statement (which has source tracking). Making them `ASGElement` subclasses would add ~40 bytes per instance for unused fields and complicate serialization. The current design is intentional and correct for MUMPS semantics where these are syntactic sub-parts of commands, not addressable entities.  
**Solution:** No code change needed. Add clarifying docstrings to document this design decision.

#### Finding 3: `MIndirection.subscripts` Uses Untyped `Optional[list]`
**File:** [src/m2py/asg/expressions.py#L209-L214](src/m2py/asg/expressions.py#L209-L214)  
**Status:** Fix Needed - Type Annotation Improvement  
**Finding:** `MIndirection.subscripts` and `name_indirection_subscripts` are typed as `Optional[list]` instead of `Optional[List[MExpr]]` like other subscript fields in the ASG (e.g., `MVariable.subscripts`, `MGlobal.subscripts`).  
**Analysis:** The textX custom class in `textx_classes.py:Indirection` populates these with properly unwrapped `MExpr` objects via `_unwrap_subscripts()`. The loose typing is inconsistent with the rest of the ASG and hinders static analysis tools. The runtime behavior is correct; only the type annotations need updating.  
**Solution:** Change type annotations to `Optional[List["MExpr"]]` for consistency and type safety.

#### Finding 4: `has_else_scope`/`get_else_scope` Helpers for Non-Existent Attribute
**File:** [src/m2py/asg/type_helpers.py#L64-L130](src/m2py/asg/type_helpers.py#L64-L130)  
**Status:** Not an Issue - Intentional Future-Proofing  
**Finding:** `has_else_scope()` and `get_else_scope()` helpers are documented as "currently always False/None" because no ASG statement type defines an `else_scope` attribute.  
**Analysis:** In MUMPS, IF and ELSE are independent commands per spec (MDC 8.2.4): "If the value of $Test is 0, execution continues normally at the next command." ELSE checks `$TEST` rather than being structurally linked to IF. The ASG correctly models this:
- `MIfStatement` has `then_scope` (commands on same line after IF)
- `MElseStatement` has `body` (commands on same line after ELSE)

The `else_scope` helpers exist for completeness in code that walks all nested scopes (used in `for_analysis.py`, `goto_analysis.py`, `elements.py`). They ensure if a future ASG type adds `else_scope`, the walking code handles it. This is intentional future-proofing, not dead code.  
**Solution:** No code change needed. The existing documentation already explains this is for future extensibility.

### Tasks

- [X] **1.1** Add `IndirectionType` and `ScopeStrategy` to exports in `src/m2py/asg/__init__.py`
  - Add to imports from `m2py.asg.enums`
  - Add to `__all__` list

- [X] **1.2** Fix type annotations for `MIndirection` subscript fields
  - File: `src/m2py/asg/expressions.py`
  - Change `subscripts: Optional[list]` to `subscripts: Optional[List["MExpr"]]`
  - Change `name_indirection_subscripts: Optional[list]` to `name_indirection_subscripts: Optional[List[List["MExpr"]]]`

- [X] **1.3** Add clarifying docstring to `MAssignment`, `MReadTarget`, `MForParameter`
  - File: `src/m2py/asg/statements.py`
  - Document that these are sub-components of statements and inherit source tracking from their containing statement

- [X] **1.4** Update documentation in `docs/asg/`
  - Updated `enums.md` (already had IndirectionType and ScopeStrategy documented)
  - Updated `statements.md` to add sub-component notes for MAssignment, MReadTarget, MForParameter
  - Updated `expressions.md` to fix MIndirection subscripts type documentation

- [X] **1.5** Add tests for Phase 72 changes
  - File: `tests/unit/test_setup.py`
  - Added `TestASGModuleExports` class testing all enum exports including IndirectionType and ScopeStrategy
  - Added `TestASGSubComponentTypes` class verifying MAssignment, MReadTarget, MForParameter design
  - Added `TestMIndirectionTyping` class verifying proper type annotations

**Checkpoint**: Phase 72 complete - ASG module has consistent exports, typing, and documentation