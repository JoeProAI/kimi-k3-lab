from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from k3lab.core import grade_response, load_suite
from k3lab.openrouter import Completion, Pricing
from k3lab.runner import run_benchmark


ROOT = Path(__file__).resolve().parents[1]
SUITE = ROOT / "suites" / "k3-core-v1.jsonl"
FIXTURES = ROOT / "fixtures" / "offline-responses.json"


class CoreTests(unittest.TestCase):
    def test_suite_has_three_distinct_categories(self) -> None:
        tasks = load_suite(SUITE)
        self.assertEqual(3, len(tasks))
        self.assertEqual({"coding", "visual-debugging", "research-synthesis"}, {task.category for task in tasks})

    def test_offline_run_scores_fixtures_without_cost(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            receipt_path = run_benchmark(
                SUITE,
                "fixture/model",
                Path(directory),
                live=False,
                max_usd=0,
                fixtures_path=FIXTURES,
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(100.0, receipt["score"])
        self.assertEqual(0.0, receipt["actual_cost_usd"])
        self.assertEqual("offline-fixture", receipt["mode"])
        self.assertEqual(3, receipt["passed_tasks"])

    def test_live_run_requires_explicit_cap(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "positive --max-usd"):
                run_benchmark(SUITE, "moonshotai/kimi-k3", Path(directory), live=True, max_usd=0)

    def test_live_run_rejects_cap_below_suite_ceiling(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, "exceeds cap"):
                run_benchmark(SUITE, "moonshotai/kimi-k3", Path(directory), live=True, max_usd=0.01)

    def test_live_run_with_fake_client_records_actual_cost(self) -> None:
        fixtures = list(json.loads(FIXTURES.read_text(encoding="utf-8")).values())

        class FakeClient:
            def pricing(self, _model):
                return Pricing(0.0, 0.0)

            def complete(self, _model, _prompt, _max_tokens):
                response = fixtures.pop(0)
                return Completion(json.dumps(response), 10, 20, 0.001, "gen-test", "fixture-provider")

        with tempfile.TemporaryDirectory() as directory:
            receipt_path = run_benchmark(
                SUITE,
                "fixture/model",
                Path(directory),
                live=True,
                max_usd=0.15,
                client=FakeClient(),
            )
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        self.assertEqual(100.0, receipt["score"])
        self.assertEqual(0.003, receipt["actual_cost_usd"])
        self.assertEqual("live", receipt["mode"])

    def test_catalog_pricing_can_reject_task_before_inference(self) -> None:
        class ExpensiveClient:
            def pricing(self, _model):
                return Pricing(0.001, 0.001)

        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "catalog-priced ceiling"):
                run_benchmark(SUITE, "fixture/model", Path(directory), live=True, max_usd=0.15, client=ExpensiveClient())

    def test_invalid_json_scores_zero(self) -> None:
        task = load_suite(SUITE)[0]
        grade = grade_response(task, "not json")
        self.assertEqual(0.0, grade.score)
        self.assertIsNotNone(grade.parse_error)


if __name__ == "__main__":
    unittest.main()
