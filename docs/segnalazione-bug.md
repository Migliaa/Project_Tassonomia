# Segnalazione a sierra-research/tau2-bench

Testo definitivo, pronto da incollare. Apri:
<https://github.com/sierra-research/tau2-bench/issues/new>

---

## Titolo

```
DB comparison via get_dict_hash is order-sensitive on lists: financially identical payment_history orderings flip the verdict (airline; root cause behind #325)
```

## Corpo

```markdown
`Environment.get_db_hash()` (`src/tau2/environment/toolkit.py:244`) fingerprints the DB with:

```python
def get_dict_hash(obj: dict) -> str:
    hash_string = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(hash_string.encode()).hexdigest()
```

`sort_keys=True` sorts dict keys but never list elements. `environment.py:267` compares this
hash between the gold and the predicted environment to decide `db_match`, and that is the
entire `DB` component of the reward. So for any field that is a **list**, the order the agent
happens to emit becomes part of the pass/fail criterion — `payment_history` in particular.

## Minimal reproduction: same agent, same task, two runs

The clearest evidence is a pair of runs of the *same* agent on airline task 14, at
`temperature=0`. Both runs produced the same cancellation and the same booking. The only
difference in the entire `book_reservation` call is the order of two gift cards inside
`payment_methods`:

| run | `payment_methods` | DB check |
|---|---|---|
| A | `[{gift_card_8020792, 198}, {gift_card_6136092, 129}]` | **pass** |
| B | `[{gift_card_6136092, 129}, {gift_card_8020792, 198}]` | **fail** |

Same cards, same amounts, same total, same reservation. Only the list order differs, and the
verdict flips. The failing run scores `reward_breakdown = {"DB": 0.0, "COMMUNICATE": 1.0}`.

## The two end states are equivalent by the project's own definition

On the full final DB state, `DeepDiff(gold_db, agent_db)` returns *only* those two
`payment_history` entries as reordered, and `DeepDiff(gold_db, agent_db, ignore_order=True)`
returns `{}`. `docs/evaluation.md` states: *"Any agent trajectory that produces an equivalent
end state passes"* — these two end states are equivalent.

Nothing in the task `instructions` or in `policy.md` specifies an ordering for
`payment_history`, and the user is never told about card ordering. I also checked the user's
profile in `db.json` for a canonical order the gold might be following: there isn't one. The
profile lists `gift_card_8020792` before `certificate_3765853`, the opposite of the gold
action's order, so there is no encoded ordering rule to preserve.

## Why this matters beyond a single false negative

The ordering an LLM emits is not stable across runs. So the defect does not merely fail some
correct solutions — it **injects variance into `pass^k`**. A genuinely solved task becomes a
coin flip, which inflates apparent model non-determinism and makes multi-trial reliability
metrics noisier than the agent under test actually is. In our own four-trial run of one agent,
task 14 passed 1 time out of 4 with materially identical actions.

## Suggested scope for a fix (not a blanket `ignore_order`)

`ignore_order=True` across the whole DB would be wrong: in the retail domain
`payment_history[0]` is indexed positionally by several tools (apparently as the original
payment method for refund routing), so order is load-bearing there.

The fix should be scoped to fields that are genuinely unordered sets in a given domain.
`payment_history` in **airline** qualifies: it is written atomically in one transaction with a
fixed `created_at` and no per-entry sequence number, so there is no ordering information to
preserve between entries. Options: sort by `payment_id` before hashing, or keep an
evaluator-level allowlist of order-insensitive fields per domain. Happy to open a PR if a
maintainer confirms the intended scope.

## Relation to #325

This looks like the root cause behind #325 (retail, `modify_pending_order_items`), which
observed an order-sensitivity symptom but listed it as one of three unconfirmed hypotheses.
`get_dict_hash` (`src/tau2/utils/utils.py:39-45`) would produce the same symptom there. This
report is airline-only, pins the mechanism, and includes a proof that the two DB states are
otherwise equivalent — so it is not a duplicate, but the missing mechanism for #325.

## Context

Found while building a failure taxonomy for a custom agent evaluated on all 50 airline tasks
across four trials. Two tasks (14 and 23) failed for this reason alone, both with DB states
identical modulo list order.
```

---

## Nota interna (non fa parte della issue)

Verificato nel codice, non dedotto, su tutti e tre gli anelli della catena:
`utils.py` (la funzione), `toolkit.py:244` (dove viene applicata al database),
`environment.py:267` (dove il confronto decide l'esito). Più la prova diretta: due liste con
le stesse voci in ordine diverso danno impronte diverse, mentre due dizionari con le chiavi in
ordine diverso danno la stessa.

Le due esecuzioni citate sono reali: `s15_custom_agent_t14` (passata) e `s16_custom_agent_t14`
(fallita).
