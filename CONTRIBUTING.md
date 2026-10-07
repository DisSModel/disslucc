# Contributing to disslucc

Thank you for your interest in contributing to `disslucc`! We welcome contributions from research group members, students, and the broader open-source community.

`disslucc` is a raster-only, script-first port of the CLUE-like (continuous)
and CLUE-S-like (discrete) LUCC allocation algorithms, built on top of
[`dissmodel`](https://github.com/DisSModel/dissmodel). See
`docs/architecture.md` for what's faithful to the original LuccME
implementation and what was simplified, and `docs/decisions.md` for the
reasoning behind past design decisions.

---

## Contribution Workflow

We follow a **Trunk-Based Development** model: all active development targets the `main` branch through short-lived branches and Pull Requests.

### 1. Issues First
Before writing code or opening a pull request, make sure an issue tracks the task:
- Navigate to the **Issues** tab and click **New issue**.
- Choose the relevant template (**Feature Task**, **Bug Report**, **Documentation**, or **Onboarding**).
- Provide the required details. Relevant labels will be attached automatically.

### 2. Creating Your Branch

#### For Lab Members & Collaborators (Direct Access)
1. Open the assigned issue on GitHub.
2. In the right sidebar under **Development**, click **"Create a branch"**.
3. Use conventional prefixes: `feat/<issue-id>-short-desc`, `fix/<issue-id>-short-desc`, `docs/<issue-id>-short-desc`, or `chore/<issue-id>-short-desc`.
4. Pull and checkout the branch locally:
   ```bash
   git fetch origin
   git checkout <branch-name>
   ```

#### For External Contributors (Fork Workflow)

1. Fork the repository to your personal GitHub account.
2. Clone your fork locally:
   ```bash
   git clone https://github.com/<your-username>/disslucc.git
   cd disslucc
   ```
3. Create a descriptive feature branch targeting `main`:
   ```bash
   git checkout -b feat/my-improvement
   ```

---

### 3. Submitting a Pull Request (PR)

1. Verify that all tests pass locally:
   ```bash
   pytest tests/ -v
   ```
2. Push your branch to GitHub:
   - **Lab members:** `git push -u origin <branch-name>`
   - **External contributors:** `git push -u origin feat/my-improvement` (to your fork)
3. Open a Pull Request targeting `DisSModel/disslucc:main`.
4. Complete the checklist provided by the Pull Request template.
5. Ensure the PR description explicitly links the issue it resolves (e.g., `Closes #15`).
6. A maintainer will review your submission. Once approved, the changes will be integrated via **Squash and merge**, and the working branch will be automatically deleted.

---

## Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/DisSModel/disslucc.git
cd disslucc
```

### 2. Virtual Environment Setup

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Development Dependencies

```bash
pip install -e ".[examples,dev]"
```

### 4. Running the Test Suite

```bash
pytest tests/ -v
```

All tests should pass on a clean checkout. If your change makes a test fail
unexpectedly, treat it as a regression until proven otherwise.

---

## Coding Standards

- **PEP 8 Compliance:** Follow standard Python formatting conventions.
- **Type Annotations:** Provide type hints for public functions, methods, and class attributes -- checked with `mypy src/disslucc` (`mypy.ini` config lives in `pyproject.toml`; currently clean, keep it that way).
- **Docstrings:** Document new modules, classes, and functions using NumPy docstring style.

---

## Data and agreement with TerraME

- **Vendored input data** (`data/input/`) is real data from
  `disslucc-continuous`/`disslucc-discrete`, used by the examples and tests.
  Don't regenerate or "clean up" these files without checking the examples
  and the benchmark that read them.
- **Agreement with TerraME/LuccME** is checked in
  [LambdaGeo/disslucc-benchmark](https://github.com/LambdaGeo/disslucc-benchmark)
  (reference results from [luccme-goldens](https://github.com/LambdaGeo/luccme-goldens),
  generated in [terrame-docker](https://github.com/profsergiocosta/terrame-docker)).
  If your change can alter numerical results, run the benchmark against your branch
  and describe the outcome in the PR. Don't copy goldens into this repository.

## Documentation & Docstrings

Document new public functions, classes, and modules with NumPy-style
docstrings. Longer illustrative examples that depend on broader context
(an existing `RasterBackend`, `Environment`, or `ModelExecutor` instance)
belong in plain ` ```python ` fenced code blocks in `docs/` or
`examples/`, not as doctests -- this package does not currently run
`pytest --doctest-modules`.

---

## Troubleshooting: Accidentally Committed to `main`?

If you committed directly to your local `main` branch and your push was blocked by repository rules, migrate your changes to a feature branch without losing work:

```bash
# 1. Create a new branch preserving your unpushed commits
git branch feat/<issue-id>-my-task

# 2. Reset your local main back to the clean remote state
git reset --hard origin/main

# 3. Switch to your new branch and push
git checkout feat/<issue-id>-my-task
git push -u origin feat/<issue-id>-my-task
```

---

## License

By contributing to `disslucc`, you agree that your contributions will be licensed under the project's [MIT License](LICENSE).
