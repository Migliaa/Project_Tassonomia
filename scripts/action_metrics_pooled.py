"""
Rianalisi per-azione, mettendo insieme le due esecuzioni indipendenti (s6 + s9).

PERCHE' ESISTE
--------------
Il reward binario su 50 task da' 50 osservazioni. Su un effetto atteso di 2-5
task ne abbiamo verificato il rumore: 5-8 task su 36 cambiano esito fra due
esecuzioni identiche a temperature=0 (vedi `confronto_ripetizioni.py`). Nessun
confronto binario a n=50 poteva rispondere con quella risoluzione.

Le metriche per-azione di `action_metrics.py` danno una osservazione continua
in [0,1] per task (`write_action_score`), non un bit. Mettendo insieme le due
esecuzioni si hanno fino a 100 coppie appaiate (baseline, custom) invece di 50,
e ogni coppia porta piu' informazione di un bit.

Il test e' un Wilcoxon signed-rank sulle differenze per-task (implementato qui
perche' scipy non e' installato nel venv), con approssimazione normale e
correzione per i pareggi - standard per n>20. Le coppie sono (task, esecuzione):
non sono tutte indipendenti in senso stretto (stesso task in due esecuzioni),
ma e' la stessa unita' di appaiamento gia' usata da McNemar altrove nel
progetto, solo con un punteggio continuo al posto del bit.

Uso, dalla radice del repo:
    PYTHONIOENCODING=utf-8 PYTHONUTF8=1 tau2-bench/.venv/Scripts/python.exe \
        scripts/action_metrics_pooled.py
"""

import glob
import json
import math
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tau2-bench" / "src"))

from action_metrics import analyze_results_file  # noqa: E402

from tau2.runner.helpers import get_tasks  # noqa: E402

TRIALS = [
    ("s6", "1a esecuzione"),
    ("s9", "2a esecuzione"),
]
AGENTI = {"baseline": "llm_agent", "custom v1": "custom_agent"}


def load(prefix: str, agent: str, tasks: dict) -> dict:
    out = {}
    for d in sorted(glob.glob(f"data/simulations/{prefix}_{agent}_t*")):
        fp = os.path.join(d, "results.json")
        if not os.path.exists(fp):
            continue
        rows = analyze_results_file(fp, "airline", tasks)
        if rows and rows[0].get("reward") is not None:
            out[rows[0]["task_id"]] = rows[0]
    return out


def wilcoxon_signed_rank(diffs: list) -> tuple:
    """Wilcoxon signed-rank, approssimazione normale con correzione ties.
    Ritorna (n_effettivo, statistic W, z, p a due code)."""
    nz = [d for d in diffs if d != 0]
    n = len(nz)
    if n == 0:
        return 0, 0.0, 0.0, 1.0
    ranks = _rankdata([abs(d) for d in nz])
    w_pos = sum(r for r, d in zip(ranks, nz) if d > 0)
    w_neg = sum(r for r, d in zip(ranks, nz) if d < 0)
    w = min(w_pos, w_neg)
    mean_w = n * (n + 1) / 4
    # correzione per i pareggi nei ranghi (tie correction)
    from collections import Counter
    tie_term = sum(t**3 - t for t in Counter(ranks).values())
    var_w = n * (n + 1) * (2 * n + 1) / 24 - tie_term / 48
    if var_w <= 0:
        return n, w, 0.0, 1.0
    z = (w - mean_w) / math.sqrt(var_w)
    p = 2 * (1 - _norm_cdf(abs(z)))
    return n, w, z, min(1.0, p)


def _rankdata(values: list) -> list:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg_rank = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = avg_rank
        i = j + 1
    return ranks


def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def mean(values) -> float:
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else 0.0


def cluster_bootstrap_micro(clusters: list, n_boot: int = 10000, seed: int = 20260904) -> tuple:
    """Bootstrap per cluster (task, esecuzione) sul tasso MICRO-medio di azioni
    di scrittura corrette (somma corrispondenze / somma azioni attese, non media
    dei rapporti per task). Serve perche' la media per-task pesa un task da due
    azioni quanto uno da dieci; il micro-tasso pesa le azioni, non i task, ed e'
    la grandezza su cui e' naturale fare inferenza quando l'unita' di interesse
    e' "quante azioni corrette", non "quanti task riusciti".

    Ricampiona i CLUSTER (non le singole azioni), quindi rispetta la
    correlazione fra le azioni dello stesso task - lo stesso motivo per cui si
    usa un bootstrap a blocchi invece di trattare ogni azione come indipendente.
    Ritorna (divario osservato, IC 95% percentile, p a due code)."""
    rng = random.Random(seed)
    n = len(clusters)

    def micro_diff(sample: list) -> float:
        nb_sum = mb_sum = nc_sum = mc_sum = 0
        for c in sample:
            nb_sum += c["nb"]
            mb_sum += c["mb"]
            nc_sum += c["nc"]
            mc_sum += c["mc"]
        rb = mb_sum / nb_sum if nb_sum else 0.0
        rc = mc_sum / nc_sum if nc_sum else 0.0
        return rc - rb

    osservato = micro_diff(clusters)
    boot = []
    for _ in range(n_boot):
        sample = [clusters[rng.randrange(n)] for _ in range(n)]
        boot.append(micro_diff(sample))
    boot.sort()
    lo = boot[int(0.025 * n_boot)]
    hi = boot[int(0.975 * n_boot) - 1]
    # p a due code: quota di ricampionamenti che cadono dall'altra parte dello
    # zero rispetto al segno osservato, raddoppiata (bootstrap percentile test)
    if osservato >= 0:
        oltre = sum(1 for x in boot if x <= 0)
    else:
        oltre = sum(1 for x in boot if x >= 0)
    p = min(1.0, 2 * oltre / n_boot)
    return osservato, (lo, hi), p


def main() -> None:
    os.chdir(ROOT / "tau2-bench")
    tasks = {t.id: t for t in get_tasks(task_set_name="airline")}

    coppie_write = []   # (write_action_score custom - baseline), per (task, trial)
    coppie_unexp = []   # unexpected_writes custom - baseline
    cluster_micro = []  # conteggi grezzi per il bootstrap a blocchi
    per_trial = {}

    for prefix, label in TRIALS:
        b = load(prefix, AGENTI["baseline"], tasks)
        c = load(prefix, AGENTI["custom v1"], tasks)
        ids = sorted(set(b) & set(c), key=int)
        per_trial[label] = (b, c, ids)
        for t in ids:
            wb, wc = b[t]["write_action_score"], c[t]["write_action_score"]
            if wb is not None and wc is not None:
                coppie_write.append((prefix, t, wb, wc))
            coppie_unexp.append((prefix, t, b[t]["unexpected_writes"], c[t]["unexpected_writes"]))
            nw = b[t]["n_write_actions"]  # stesso task -> stesse azioni attese
            if nw:
                cluster_micro.append({
                    "prefix": prefix, "task": t, "nb": nw, "nc": nw,
                    "mb": round(wb * nw) if wb is not None else 0,
                    "mc": round(wc * nw) if wc is not None else 0,
                })

    print(f"coppie (task, esecuzione) disponibili per write_action_score: {len(coppie_write)}\n")

    print(f"{'esecuzione':<16}{'n task':>8}{'baseline':>12}{'custom v1':>12}{'divario':>10}")
    print("-" * 58)
    for label, (b, c, ids) in per_trial.items():
        mb = mean(b[t]["write_action_score"] for t in ids)
        mc = mean(c[t]["write_action_score"] for t in ids)
        print(f"{label:<16}{len(ids):>8}{mb:>12.3f}{mc:>12.3f}{mc - mb:>+10.3f}")

    mb_pool = mean(wb for _, _, wb, _ in coppie_write)
    mc_pool = mean(wc for _, _, _, wc in coppie_write)
    print("-" * 58)
    print(f"{'pooled':<16}{len(coppie_write):>8}{mb_pool:>12.3f}{mc_pool:>12.3f}{mc_pool - mb_pool:>+10.3f}")

    diffs = [wc - wb for _, _, wb, wc in coppie_write]
    n, w, z, p = wilcoxon_signed_rank(diffs)
    verdetto = "significativo" if p < 0.05 else "NON significativo"
    print(f"\nWilcoxon signed-rank su write_action_score (custom - baseline), "
          f"pooled su {len(TRIALS)} esecuzioni:")
    print(f"  n coppie non nulle = {n}, W = {w:.1f}, z = {z:.3f}, p = {p:.4f} a due code -> {verdetto}")

    diffs_unexp = [uc - ub for _, _, ub, uc in coppie_unexp]
    n2, w2, z2, p2 = wilcoxon_signed_rank(diffs_unexp)
    mu_b = mean(ub for _, _, ub, _ in coppie_unexp)
    mu_c = mean(uc for _, _, _, uc in coppie_unexp)
    print(f"\nscritture inattese (unexpected_writes) per task, pooled:")
    print(f"  baseline {mu_b:.3f}  custom v1 {mu_c:.3f}  divario {mu_c - mu_b:+.3f}")
    if n2:
        verdetto2 = "significativo" if p2 < 0.05 else "NON significativo"
        print(f"  Wilcoxon: n={n2}, z={z2:.3f}, p={p2:.4f} a due code -> {verdetto2}")
    else:
        print("  nessuna coppia con differenza non nulla (troppo poche scritture inattese per un test)")

    tot_nb = sum(cl["nb"] for cl in cluster_micro)
    tot_mb = sum(cl["mb"] for cl in cluster_micro)
    tot_nc = sum(cl["nc"] for cl in cluster_micro)
    tot_mc = sum(cl["mc"] for cl in cluster_micro)
    print(f"\nMICRO-tasso (azioni corrette / azioni attese, pesato per azione non per task):")
    print(f"  baseline  {tot_mb}/{tot_nb} = {tot_mb/tot_nb:.3f}")
    print(f"  custom v1 {tot_mc}/{tot_nc} = {tot_mc/tot_nc:.3f}")
    print(f"  cluster (task, esecuzione) usati nel bootstrap: {len(cluster_micro)}")

    diff, (lo, hi), p3 = cluster_bootstrap_micro(cluster_micro)
    verdetto3 = "significativo" if p3 < 0.05 else "NON significativo"
    print(f"\nBootstrap a blocchi (10000 ricampionamenti, blocco = task-esecuzione):")
    print(f"  divario osservato {diff:+.3f}, IC 95% [{lo:+.3f}, {hi:+.3f}], p={p3:.4f} -> {verdetto3}")


if __name__ == "__main__":
    main()
