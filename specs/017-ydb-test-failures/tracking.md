# YDB Test Failure Resolution Tracking

**Baseline Date**: 2026-01-22
**Initial Status**: 147 failed, 336 passed, 1 skipped, 5 xfailed

## Summary by Category

| Category | Count | Status |
|----------|-------|--------|
| TRAMPOLINE Strategy Gaps | 10 | Not Started |
| LIM-015 Z-extensions | 12 | Not Started |
| Other Functional Gaps | 11 | Not Started |
| External Dependencies (merge) | 33 | Not Started |
| Codegen Bugs | 1 | Not Started |
| Behavioral Bugs | 75 | Not Started |
| **Total** | **147** | |

## Phase Progress

- [x] Phase 1: Setup (T001-T003)
- [ ] Phase 2: Foundational (T004-T008)
- [ ] Phase 3: US1 - TRAMPOLINE (T009-T016)
- [ ] Phase 4: US9 - Codegen Syntax (T017-T020)
- [ ] Phase 5: US2 - Sorts-After (T021-T025)
- [ ] Phase 6: US3 - LHS $PIECE (T026-T031)
- [ ] Phase 7: US10 - Expression Types (T032-T036)
- [ ] Phase 8: US8 - LIM-015 xfail (T037-T039)
- [ ] Phase 9: US4 - Arithmetic (T040-T044)
- [ ] Phase 10: US5 - Pattern Matching (T045-T050)
- [ ] Phase 11: US6 - FOR Loops (T051-T055)
- [ ] Phase 12: US7 - $ORDER/$QUERY (T056-T060)
- [ ] Phase 13: US11 - Merge Suite (T061-T067)
- [ ] Phase 14: Remaining Bugs (T068-T075)
- [ ] Phase 15: Polish (T076-T079)

## Detailed Test Mapping

### TRAMPOLINE Tests (10)
- v1call, v1nst3, v1ov, v1prgd, v1seq, vv2lcc1, vv2vnib, fifo, per02397, setpiece

### LIM-015 Z-extension Tests (12)
- From failure-analysis.md: ZSYSTEM (3), $ZTRAP (6), Z-functions (3)

### Merge Suite Tests (33)
- gbl2gbl, gbl2lcl, lcl2gbl, lcl2lcl, etc.

## Resolution Log

| Date | Phase | Tests Fixed | Notes |
|------|-------|-------------|-------|
| 2026-01-22 | Setup | - | Baseline established |
