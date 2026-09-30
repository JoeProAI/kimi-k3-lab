# Contributing

K3 Lab accepts task suites, deterministic graders, model adapter improvements, receipt tooling, and documentation fixes.

## Ground rules

* All model calls go through OpenRouter.
* Never commit credentials or add direct provider keys.
* Tests and CI must stay offline and free.
* A live path must require an explicit flag, a positive operator cap, and catalog pricing validation.
* New tasks must expose the full prompt, token bound, cost allocation, and deterministic checks.
* Hidden judge prompts and paid judge models are not accepted.
* Keep model claims tied to dated receipts using the same suite SHA256.
* Describe Kimi K3 as open-weight under the Kimi K3 License, not as OSI open source.

## Add a task

1. Append one self-contained JSON object to the current suite or propose a versioned new suite.
2. Add a matching offline fixture.
3. Add a test that proves the grader accepts the fixture and rejects a meaningful failure.
4. Run the full offline verification.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m k3lab run
```

## Pull requests

Explain who the change helps, what can fail, and which commands you ran. Never attach live secrets or private benchmark inputs.
