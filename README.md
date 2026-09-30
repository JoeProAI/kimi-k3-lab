# Kimi K3 OpenWeights Lab

Know whether an agent model is worth your money before you rebuild your stack around it.

K3 Lab is an MIT licensed, provider neutral evaluation harness for long horizon agent work. It starts with Kimi K3, but every task and receipt works with any model available through OpenRouter.

Kimi K3 is open-weight under the custom Kimi K3 License. The model itself is not OSI licensed. This lab is open source under MIT.

## Who this helps

* Developers choosing a coding or research model for a real agent loop.
* Small teams that need cost and latency evidence, not a vendor leaderboard.
* Open model researchers who want reproducible task definitions and portable receipts.
* Operators who need a hard spend gate before a benchmark can call a paid model.

The design reduces asymmetric information between model vendors and users. Fixed public tasks, visible graders, and immutable receipts turn benchmark claims into evidence anyone can inspect or rerun. That follows the asymmetric information principle in the JoePro game theory canon: hidden policy should be inferred from observable actions, not marketing claims.

## What ships in v0.1

v0.1 is a smoke suite for adapter reliability, structured task compliance, receipts, and cost controls. It does not prove long horizon agent superiority. The next corpus milestone will execute real repository and browser tasks in isolated sandboxes.

* A fixed three lane corpus: coding repair, visual debugging, and cited research synthesis.
* Deterministic JSON graders with no judge model and no hidden scoring prompt.
* Offline fixture mode as the free default.
* OpenRouter only live inference using `moonshotai/kimi-k3` by default.
* Concurrency fixed at one.
* A declared per-task cost ceiling and required operator cap.
* Fail closed behavior when OpenRouter omits actual cost data.
* Versioned JSON receipts containing suite hash, raw response, checks, latency, usage, provider, and cost.
* Receipt comparison across K3 and any OpenRouter baseline.

## Quick start, free

```powershell
cd C:\Projects\AI_Projects\kimi-k3-lab
$env:PYTHONPATH = "src"
python -m k3lab list
python -m k3lab plan
python -m k3lab run
```

The default run uses committed fixtures, spends nothing, and writes a receipt under `runs/`.

Compare receipts:

```powershell
python -m k3lab compare runs\first.json runs\second.json
```

## Live run

Live inference is intentionally difficult to trigger accidentally. It requires all three controls:

1. `--live`
2. `OPENROUTER_API_KEY`
3. `--max-usd` at or above the suite ceiling

```powershell
$env:OPENROUTER_API_KEY = "your local secret"
python -m k3lab run --live --model moonshotai/kimi-k3 --max-usd 0.15
```

Do not put the key in source, commands saved to history, or committed env files. The harness reads `OPENROUTER_API_KEY` from the process environment.

## Why Daytona is optional

Daytona is useful for disposable tool and browser sandboxes. It cannot host Kimi K3 directly because K3 needs a multi-accelerator deployment, while Daytona sandboxes expose one GPU each. K3 inference stays behind OpenRouter. Daytona can later isolate generated code execution, with a labeled sandbox, short auto-stop, per-run cap, and guaranteed teardown.

No Daytona sandbox is created by this repository today.

## Corpus contract

Each JSONL task declares:

* A stable ID and category.
* The complete prompt.
* A bounded output token count.
* A conservative maximum cost allocation.
* Public deterministic checks.

A model cannot receive private hints or a hidden evaluator prompt. The suite SHA256 is embedded in every receipt, so two runs are comparable only when they used the same corpus bytes.

## Add a model

Pass any OpenRouter model slug:

```powershell
python -m k3lab run --live --model another-provider/model --max-usd 0.15
```

The model adapter remains provider neutral because the only network boundary is OpenRouter.

## Add a task

Append one JSON object to `suites/k3-core-v1.jsonl`, add an offline response fixture, and add or update a test. Keep tasks self-contained and scoreable without a paid judge model.

## Development

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
python -m k3lab run
```

No dependency installation is required for the current harness.
