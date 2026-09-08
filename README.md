# Can prompt engineering alone improve an agent?

A study on [τ²-bench](https://github.com/sierra-research/tau2-bench) (airline domain), with the
model held fixed and **only the system prompt allowed to change** — no fine-tuning, no second
model, no extra tools.

Engine: `gemini-3.5-flash-lite` for both the agent and the simulated user, `temperature=0`,
all 50 airline tasks.

## Result

| | pass^1 | notes |
|---|---|---|
| default `llm_agent` (benchmark's own) | 68.0% | 34/50, single run |
| our agent, v6 | **80.5%** | average of 4 full trials (200 simulations) |

Per trial: 82% / 74% / 80% / 86%. Three of the four beat the baseline with McNemar
*p* = 0.039 / 0.508 / 0.031 / 0.004; in two of them the agent loses **no** task to the baseline.

Two things this result does **not** say, both documented rather than hidden:

- **Reliability did not improve.** Asked to succeed repeatedly on the same task, our agent is on
  par with the baseline, not better. On the 37 tasks where both have two runs, pass^2 is 67.6%
  for each.
- **One run would have been misleading.** The same agent, same tasks, `temperature=0`, scores
  anywhere from 74% to 86%. A single trial would have reported 86% in good faith.

## A defect found in the benchmark

The DB comparison hashes the database with `json.dumps(..., sort_keys=True)`, which sorts dict
keys but **not list elements**. Two bookings with identical payments listed in a different order
therefore hash differently and are judged different.

Verified on two runs of the same agent differing only in the order of two gift cards: one
passes, one fails. Because the ordering an LLM emits is unstable, this does not merely produce
false negatives — it injects variance into `pass^k`, the very metric the benchmark exists to
measure. Full write-up: [`docs/segnalazione-bug.md`](docs/segnalazione-bug.md).

## Method

Each version of the agent came from reading failing conversations turn by turn and grouping them
into failure families, not from guessing. Every change was **registered as a prediction before
running** — which specific tasks should flip, and which should not — so a correction can be told
apart from a lucky adjustment.

The most useful negative result: **adding rules made things worse.** Three consecutive versions
that added clauses lost ground. Past roughly twenty instructions, small models start violating
them silently. What worked was subtraction — removing a worked example that was teaching the
wrong behaviour, and replacing ten lines of case law with one principle.

## Layout

| path | |
|---|---|
| `patches/` | our changes to `tau2-bench`, which is gitignored as a third-party clone |
| `scripts/` | run workers, Langfuse publishing, statistics (McNemar, bootstrap, pass^k) |
| `docs/` | failure analysis, prompt design rationale, the benchmark bug report |
| `report/` | the write-up prepared for publication, with figures |
| `DIARIO.md` | full working diary, in Italian — including the wrong hypotheses |

## Reproducing a run

`tau2-bench/` is a third-party clone and is not committed. Clone it, apply the patches in
`patches/`, then:

```bash
PYTHONIOENCODING=utf-8 PYTHONUTF8=1 python scripts/s6_worker.py \
    --key-var GEMINI_API_KEY --agent custom_agent --tasks 0,1,2 --prefix myrun
```

Results land in `tau2-bench/data/simulations/<prefix>_<agent>_t<id>/results.json`.
`scripts/s6_publish.py <prefix>` pushes them to Langfuse for side-by-side comparison; it reads
from disk and makes no model calls.

---

Total API spend for the whole project: about $25.
