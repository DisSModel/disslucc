"""
Lazy re-exports (PEP 562), not eager imports, on purpose: eagerly
importing .continuous/.discrete here means `python -m
disslucc.executors.continuous ...` (the CLI entry point, see that
module's `__main__` block) imports `disslucc.executors.continuous` as
a side effect of importing the *package* first, then runpy imports the
same module again to execute it as `__main__` -- Python then warns
`RuntimeWarning: 'disslucc.executors.continuous' found in sys.modules
after import of package 'disslucc.executors', but prior to execution
...; this may result in unpredictable behaviour`. Harmless in
practice here (no top-level side effects run twice), but avoidable:
`from disslucc.executors import LuccContinuousExecutor` still works
identically -- it just resolves through __getattr__ below instead of
a name already bound at package-import time.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .base import LuccExecutorBase as LuccExecutorBase
    from .continuous import LuccContinuousExecutor as LuccContinuousExecutor
    from .discrete import LuccDiscreteExecutor as LuccDiscreteExecutor

__all__ = ["LuccContinuousExecutor", "LuccDiscreteExecutor", "LuccExecutorBase"]


def __getattr__(name: str):
    if name == "LuccExecutorBase":
        from .base import LuccExecutorBase
        return LuccExecutorBase
    if name == "LuccContinuousExecutor":
        from .continuous import LuccContinuousExecutor
        return LuccContinuousExecutor
    if name == "LuccDiscreteExecutor":
        from .discrete import LuccDiscreteExecutor
        return LuccDiscreteExecutor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
