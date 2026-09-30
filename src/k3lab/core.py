from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Task:
    id: str
    category: str
    title: str
    prompt: str
    max_output_tokens: int
    max_cost_usd: float
    checks: list[dict[str, Any]]


@dataclass(frozen=True)
class Grade:
    score: float
    passed: int
    total: int
    checks: list[dict[str, Any]]
    parse_error: str | None = None


def load_suite(path: Path) -> list[Task]:
    tasks: list[Task] = []
    seen: set[str] = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        raw = json.loads(line)
        task = Task(**raw)
        if task.id in seen:
            raise ValueError(f"duplicate task id at line {line_number}: {task.id}")
        if task.max_output_tokens <= 0 or task.max_cost_usd <= 0:
            raise ValueError(f"task limits must be positive: {task.id}")
        seen.add(task.id)
        tasks.append(task)
    if not tasks:
        raise ValueError("suite is empty")
    return tasks


def suite_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _value_at(data: Any, path: str) -> Any:
    value = data
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(path)
        value = value[part]
    return value


def _run_check(data: Any, check: dict[str, Any]) -> tuple[bool, str]:
    kind = check["type"]
    path = check["path"]
    expected = check["value"]
    try:
        actual = _value_at(data, path)
    except KeyError:
        return False, f"missing path: {path}"
    if kind == "contains":
        passed = str(expected).casefold() in str(actual).casefold()
    elif kind == "equals":
        passed = actual == expected
    elif kind == "min_items":
        passed = isinstance(actual, list) and len(actual) >= int(expected)
    elif kind == "all_items_have":
        passed = isinstance(actual, list) and bool(actual) and all(
            isinstance(item, dict) and all(key in item for key in expected) for item in actual
        )
    else:
        raise ValueError(f"unknown check type: {kind}")
    return passed, f"{kind} {path}"


def grade_response(task: Task, text: str) -> Grade:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        return Grade(score=0.0, passed=0, total=len(task.checks), checks=[], parse_error=str(error))
    results = []
    for check in task.checks:
        passed, label = _run_check(data, check)
        results.append({"passed": passed, "label": label})
    passed_count = sum(1 for result in results if result["passed"])
    total = len(results)
    return Grade(score=round(100 * passed_count / total, 2) if total else 100.0, passed=passed_count, total=total, checks=results)


def grade_dict(grade: Grade) -> dict[str, Any]:
    return asdict(grade)
