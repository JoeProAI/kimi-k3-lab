from __future__ import annotations

import io
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from k3lab.openrouter import OpenRouterClient


class FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class OpenRouterTests(unittest.TestCase):
    def test_reads_catalog_pricing(self) -> None:
        def opener(_request, timeout):
            self.assertEqual(30, timeout)
            return FakeResponse({"data": [{
                "id": "fixture/model",
                "pricing": {"prompt": "0.000001", "completion": "0.000005"},
            }]})

        pricing = OpenRouterClient("test-key", opener=opener).pricing("fixture/model")
        self.assertEqual(0.000001, pricing.prompt_per_token)
        self.assertEqual(0.000005, pricing.completion_per_token)

    def test_parses_costed_completion(self) -> None:
        def opener(_request, timeout):
            self.assertEqual(300, timeout)
            return FakeResponse({
                "id": "gen-test",
                "provider": "fixture-provider",
                "choices": [{"message": {"content": "{\"ok\": true}"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "cost": 0.001},
            })

        result = OpenRouterClient("test-key", opener=opener).complete("fixture/model", "prompt", 64)
        self.assertEqual("{\"ok\": true}", result.text)
        self.assertEqual(0.001, result.cost_usd)
        self.assertEqual("fixture-provider", result.provider)

    def test_refuses_unpriced_completion(self) -> None:
        def opener(_request, timeout):
            return FakeResponse({"choices": [{"message": {"content": "{}"}}], "usage": {}})

        with self.assertRaisesRegex(RuntimeError, "usage.cost"):
            OpenRouterClient("test-key", opener=opener).complete("fixture/model", "prompt", 64)


if __name__ == "__main__":
    unittest.main()
