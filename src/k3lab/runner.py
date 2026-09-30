from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .core import grade_dict, grade_response, load_suite, suite_hash
from .openrouter import OpenRouterClient


def planned_ceiling(tasks: list[Any]) -> float:
    return round(sum(task.max_cost_usd for task in tasks), 6)


def run_benchmark(
    suite_path: Path,
    model: str,
    output_dir: Path,
    live: bool,
    max_usd: float,
    fixtures_path: Path | None = None,
    client: OpenRouterClient | None = None,
) -> Path:
    tasks = load_suite(suite_path)
    ceiling = planned_ceiling(tasks)
    if live and max_usd <= 0:
        raise ValueError("live runs require a positive --max-usd")
    if live and ceiling > max_usd:
        raise ValueError(f"suite ceiling ${ceiling:.4f} exceeds cap ${max_usd:.4f}")
    fixtures = json.loads(fixtures_path.read_text(encoding="utf-8")) if fixtures_path else {}
    if not live and not fixtures:
        raise ValueError("offline runs require fixtures")
    if live and client is None:
        client = OpenRouterClient(os.environ.get("OPENROUTER_API_KEY", ""))
    if live:
        pricing = client.pricing(model)
        for task in tasks:
            conservative_prompt_tokens = len(task.prompt.encode("utf-8")) // 3 + 256
            projected = conservative_prompt_tokens * pricing.prompt_per_token + task.max_output_tokens * pricing.completion_per_token
            if projected > task.max_cost_usd:
                raise RuntimeError(
                    f"catalog-priced ceiling ${projected:.6f} exceeds task allocation ${task.max_cost_usd:.6f}: {task.id}"
                )

    started = datetime.now(timezone.utc).isoformat()
    results: list[dict[str, Any]] = []
    spent = 0.0
    for task in tasks:
        if live and spent + task.max_cost_usd > max_usd:
            raise RuntimeError(f"cost guard stopped before {task.id}")
        begin = time.perf_counter()
        if live:
            completion = client.complete(model, task.prompt, task.max_output_tokens)
            text = completion.text
            usage = {
                "prompt_tokens": completion.prompt_tokens,
                "completion_tokens": completion.completion_tokens,
                "cost_usd": completion.cost_usd,
                "generation_id": completion.generation_id,
                "provider": completion.provider,
            }
        else:
            if task.id not in fixtures:
                raise ValueError(f"missing fixture for task: {task.id}")
            text = json.dumps(fixtures[task.id], ensure_ascii=False)
            usage = {"prompt_tokens": 0, "completion_tokens": 0, "cost_usd": 0.0, "generation_id": None, "provider": "fixture"}
        spent = round(spent + float(usage["cost_usd"]), 8)
        if live and spent > max_usd:
            raise RuntimeError(f"reported cost ${spent:.6f} exceeded cap ${max_usd:.6f}")
        grade = grade_response(task, text)
        results.append({
            "task_id": task.id,
            "category": task.category,
            "title": task.title,
            "latency_ms": round((time.perf_counter() - begin) * 1000, 2),
            "usage": usage,
            "grade": grade_dict(grade),
            "response": text,
        })

    score = round(sum(result["grade"]["score"] for result in results) / len(results), 2)
    receipt = {
        "schema_version": 1,
        "run_id": str(uuid.uuid4()),
        "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "mode": "live" if live else "offline-fixture",
        "model": model,
        "suite": suite_path.name,
        "suite_sha256": suite_hash(suite_path),
        "declared_cost_ceiling_usd": ceiling,
        "operator_cap_usd": max_usd if live else 0.0,
        "actual_cost_usd": spent,
        "score": score,
        "passed_tasks": sum(1 for result in results if result["grade"]["score"] == 100.0),
        "task_count": len(results),
        "results": results,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{receipt['run_id']}.json"
    output_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def compare_receipts(paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        receipt = json.loads(path.read_text(encoding="utf-8"))
        rows.append({
            "model": receipt["model"],
            "score": receipt["score"],
            "cost_usd": receipt["actual_cost_usd"],
            "passed": f"{receipt['passed_tasks']}/{receipt['task_count']}",
            "receipt": str(path),
        })
    return sorted(rows, key=lambda row: (-row["score"], row["cost_usd"]))
