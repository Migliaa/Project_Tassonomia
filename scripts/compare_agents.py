"""
Confronto a tre vie fra le versioni dell'agente, dai `results.json` locali.

Costo zero: nessuna chiamata LLM, nessun consumo di quota. Legge le cartelle
`data/simulations/<prefisso>_<agente>_t<id>` prodotte da `s6_worker.py` e mette
in colonna baseline, custom v1 e custom v2 sugli stessi 50 task.

Oltre al reward stampa le metriche per-azione di `action_metrics.py` (che sono
il motivo per cui in S5 abbiamo capito che un round apparentemente fallito era
invece un progresso) e il test esatto di McNemar per ogni coppia, perche' con
n=1 per task una differenza di uno o due task non e' distinguibile dalla
varianza e va detto accanto al numero, non in nota.

Uso, dalla radice del repo:
    PYTHONIOENCODING=utf-8 PYTHONUTF8=1 tau2-bench/.venv/Scripts/python.exe \
        scripts/compare_agents.py
"""

import glob
import json
import os
import sys
from math import comb
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tau2-bench" / "src"))

from action_metrics import analyze_results_file  # noqa: E402

from tau2.runner.helpers import get_tasks  # noqa: E402

# I dieci task che abbiamo guardato durante la diagnosi. Serve a separare il
# guadagno "sui casi studiati" da quello sui task mai visti: e' li' che si vede
# se le regole generalizzano o se abbiamo solo imparato a memoria.
DEV_SET = {"0", "7", "18", "23", "33", "37", "39", "41", "42", "44"}

VERSIONS = [
    ("s6", "llm_agent", "baseline"),
    ("s6", "custom_agent", "custom v1"),
    ("s7", "custom_agent", "custom v2"),
]


def load(prefix: str, agent: str, tasks: dict) -> dict:
    out = {}
    for d in sorted(glob.glob(f"data/simulations/{prefix}_{agent}_t*")):
        fp = os.path.join(d, "results.json")
        if not os.path.exists(fp):
            continue
        rows = analyze_results_file(fp, "airline", tasks)
        if rows:
            out[rows[0]["task_id"]] = rows[0]
    return out


def mcnemar(a: dict, b: dict, ids: list) -> tuple:
    """Test esatto di McNemar: e' il test corretto per esiti binari appaiati.
    Conta solo le coppie discordanti - i task su cui i due agenti differiscono."""
    win = [t for t in ids if b[t]["reward"] > a[t]["reward"]]
    lose = [t for t in ids if b[t]["reward"] < a[t]["reward"]]
    n, k = len(win) + len(lose), len(win)
    if n == 0:
        return win, lose, 1.0
    p_one = sum(comb(n, i) for i in range(k, n + 1)) / 2**n
    return win, lose, min(1.0, 2 * p_one)


def mean(values) -> float:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else 0.0


def main() -> None:
    os.chdir(ROOT / "tau2-bench")
    tasks = {t.id: t for t in get_tasks(task_set_name="airline")}

    data, labels = {}, []
    for prefix, agent, label in VERSIONS:
        d = load(prefix, agent, tasks)
        if not d:
            print(f"({label}: nessun risultato su disco, salto)")
            continue
        data[label] = d
        labels.append(label)

    ids = sorted(set.intersection(*[set(data[l]) for l in labels]), key=int)
    print(f"task confrontabili su tutte le versioni: {len(ids)}\n")

    head = f"{'':<12}" + "".join(f"{l:>12}" for l in labels)
    print(head)
    print("-" * len(head))
    rows = [
        ("reward", lambda d: sum(1 for t in ids if d[t]["reward"] == 1.0), "{:>10}/50"),
        ("db_check", lambda d: mean(( (d[t].get('reward_breakdown') or {}).get('DB') for t in ids)), "{:>12.2f}"),
        ("write score", lambda d: mean((d[t]["write_action_score"] for t in ids)), "{:>12.2f}"),
        ("scrit. inattese", lambda d: mean((d[t]["unexpected_writes"] for t in ids)), "{:>12.2f}"),
        ("arg. sbagliati", lambda d: mean(
            (d[t]["spurious_writes"] - d[t]["unexpected_writes"] for t in ids)), "{:>12.2f}"),
    ]
    for name, fn, fmt in rows:
        print(f"{name:<12}" + "".join(fmt.format(fn(data[l])) for l in labels))

    print("\nset di sviluppo (10 task gia' guardati) contro i 40 mai visti:")
    for l in labels:
        d = data[l]
        dev = sum(1 for t in ids if t in DEV_SET and d[t]["reward"] == 1.0)
        oth = sum(1 for t in ids if t not in DEV_SET and d[t]["reward"] == 1.0)
        n_dev = sum(1 for t in ids if t in DEV_SET)
        print(f"   {l:<12} sviluppo {dev}/{n_dev}   mai visti {oth}/{len(ids) - n_dev}")

    print("\nconfronti appaiati (test esatto di McNemar):")
    for i, a in enumerate(labels):
        for b in labels[i + 1:]:
            win, lose, p = mcnemar(data[a], data[b], ids)
            verdetto = "significativo" if p < 0.05 else "NON significativo"
            print(f"   {a} -> {b}: recuperati {sorted(win, key=int)}, persi {sorted(lose, key=int)}")
            print(f"      {len(win)+len(lose)} coppie discordanti, p={p:.4f} a due code -> {verdetto}")

    cost = 0.0
    for prefix, agent, _ in VERSIONS:
        for d in glob.glob(f"data/simulations/{prefix}_{agent}_t*"):
            fp = os.path.join(d, "results.json")
            if not os.path.exists(fp):
                continue
            sims = json.load(open(fp, encoding="utf-8")).get("simulations") or []
            if sims:
                cost += (sims[0].get("agent_cost") or 0) + (sims[0].get("user_cost") or 0)
    print(f"\ncosto complessivo delle simulazioni lette: ${cost:.3f}")


if __name__ == "__main__":
    main()
