---
name: Onboarding / Good First Issue
about: Well-scoped task suitable for new students joining the team
title: "[ONBOARDING] "
labels: good first issue, documentation
assignees: ""
---

### Task Description
<!-- Describe the specific, small-scope task to be completed. -->

### Relevant Files
- `path/to/file`
- `tests/`

### Step-by-Step Guidance
1. Checkout a branch from latest `main`.
2. Follow the setup in `README.md` (`pip install -e ".[examples,dev]"`) and
   activate the virtual environment.
3. Make the specified adjustments.
4. Run `pytest tests/ -v` -- expect `19 passed, 2 xfailed` unmodified,
   unless your task changes that on purpose.
5. Run `mypy src/disslucc` and fix any new warnings it reports.

### Expected Deliverable
- A pull request with clean commits following the repository conventions
  (see `CONTRIBUTING.md`).
