# Python Notes

## Idioms

- Target the project's Python version (check `pyproject.toml`/`requires-python`). Type hints on all public functions; run mypy/pyright per project config.
- Modern hints: `list[str]`, `dict[str, int]`, `X | None` (3.10+); `from __future__ import annotations` on older versions.
- Data: `@dataclass(frozen=True, slots=True)` for value objects; pydantic models at I/O boundaries (API, config, files); `TypedDict` for typed dict shapes; `Enum`/`StrEnum` for closed sets.
- Protocols (`typing.Protocol`) for structural interfaces instead of ABCs when only a shape is needed.
- EAFP where natural (`try: d[k] except KeyError`), but `dict.get`/`in` when absence is normal.
- Context managers (`with`) for files, locks, connections, transactions; `contextlib.contextmanager` for custom ones.
- Comprehensions for simple transforms; plain loops once there are conditions + side effects. Generators for large/streamed data.
- `pathlib.Path` over `os.path` string munging.
- f-strings for formatting; but logging uses lazy args or structured fields: `log.info("user.created", extra={...})` / structlog.
- `enumerate`, `zip(strict=True)` (3.10+), `itertools`, `functools.cache` for pure functions.
- Money: `decimal.Decimal` or integer cents. Time: timezone-aware `datetime` in UTC (`datetime.now(UTC)`); never naive datetimes across boundaries.
- Package layout: `src/` layout, `__init__.py` minimal, no heavy work at import time.
- Entry points guarded by `if __name__ == "__main__":`.

## Errors

- Raise specific exceptions; define a project base exception; chain with `raise NewError(...) from e`.
- Never bare `except:`; avoid `except Exception:` except at top-level boundaries (and log with `log.exception`).
- Don't catch `BaseException`, `KeyboardInterrupt`, `SystemExit`, `asyncio.CancelledError` (re-raise if you must catch).

## Async

- Don't call blocking I/O in `async def` (use async clients or `asyncio.to_thread`).
- `asyncio.TaskGroup` (3.11+) for structured concurrency; keep references to created tasks.
- Timeouts: `asyncio.timeout()` (3.11+) / `wait_for`.

## Pitfalls

- Mutable default arguments: `def f(items=[])` → `def f(items: list | None = None)`.
- Late-binding closures in loops (`lambda: i`) — bind via default arg or `functools.partial`.
- `is` vs `==`: `is` only for `None`/singletons.
- Shadowing builtins (`list`, `id`, `type`, `input`).
- Integer vs float division (`/` always float; `//` floor).
- Circular imports from module-level cross-imports — restructure or import inside function as last resort.
- `pickle`, `yaml.load` (use `yaml.safe_load`), `eval`, `subprocess(..., shell=True)` with untrusted input are code execution.
- SQL via f-strings — always parameterized (`cursor.execute(sql, params)`, SQLAlchemy bound params).
- Global mutable state in modules (shared across requests/tests).
- `requests` without `timeout=` hangs forever.

## Tooling

- Ruff (lint + format) or project's Black/isort/flake8; mypy/pyright; pytest with fixtures and `parametrize`; `pytest -x -q` for quick runs.
- Dependencies pinned via lockfile (uv, poetry, pip-tools); virtual environments always.
- `pip-audit` for vulnerabilities.

## Sources

- PEP 8: https://peps.python.org/pep-0008/
- Python typing docs: https://docs.python.org/3/library/typing.html
- Ruff rules: https://docs.astral.sh/ruff/rules/
- asyncio TaskGroup: https://docs.python.org/3/library/asyncio-task.html#task-groups
