# K3 Lab agent rules

- Keep the harness provider neutral. Model calls go through OpenRouter only.
- Never add a direct provider key or endpoint.
- Live runs require `--live`, `OPENROUTER_API_KEY`, and an explicit positive `--max-usd` that covers the suite ceiling.
- Default execution is offline fixture mode and must remain free.
- Keep concurrency at one until measured receipts justify another policy.
- Every scored run writes a versioned JSON receipt with suite hash, model ID, latency, usage, cost, raw response, and check results.
- Daytona is optional isolation for task execution. It is not a Kimi K3 inference host.
- Do not provision Daytona or call paid inference during tests.
- Kimi K3 is open-weight under the Kimi K3 License. Do not describe the model license as OSI open source.
- Run `python -m unittest discover -s tests -v` before completion.
