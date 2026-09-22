---
name: Feature / Task Request
about: Propose a new component, strategy, or task (Demand/Potential/Allocation, executor, validation)
title: "[FEAT] "
labels: enhancement
assignees: ""
---

### Objective
<!-- What problem does this solve, or what new capability does it introduce?
(e.g., a new Potential/Allocation strategy, a new validation scenario,
raster performance work) -->

### Technical Specifications & Context
<!-- Implementation details: affected modules under src/disslucc/
(components/demand, potential, allocation; executors/; validation/),
mathematical formulas, expected inputs/outputs, or references to the
original LuccME components this ports/extends. -->

### Acceptance Criteria (Definition of Done)
- [ ] Implementation completed in the target module
- [ ] Unit test(s) covering standard and edge cases added to `tests/`
- [ ] If it touches Lab1/Lab15, `pytest tests/ -v` still reports the same
      validation numbers (or the change is intentional and documented in
      `docs/validation.md`)
- [ ] Documentation or usage example provided (if public API changed)
- [ ] Pull request passes CI checks and is reviewed
