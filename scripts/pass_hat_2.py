"""
pass^2 sui 36 task presenti in entrambe le esecuzioni indipendenti (s6, s9).

E' la metrica ufficiale del benchmark (Yao et al., arXiv:2406.12045): la
probabilita' che un task riesca in TUTTE le k prove, non solo in almeno una.
Con k=2 e due sole esecuzioni per task il calcolo e' semplice: un task conta
se e solo se ha reward 1.0 in ENTRAMBE le esecuzioni.

Non e' una nuova infrastruttura: `pass_hat_k()` esiste gia' in
`tau2-bench/src/tau2/metrics/agent_metrics.py:113` per il caso generale (num
prove, k) via coefficiente binomiale; con num_trials=k=2 si riduce a "successo
in entrambe", quindi qui si conta a mano invece di importarla, per restare
leggibile senza il resto dell'infrastruttura di aggregazione di quel modulo.

Uso, dalla radice del repo:
    PYTHONIOENCODING=utf-8 PYTHONUTF8=1 tau2-bench/.venv/Scripts/python.exe \
        scripts/pass_hat_2.py
"""

import glob
import json
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent


def carica(prefisso: str, agente: str) -> dict:
    out = {}
    for d in glob.glob(f"data/simulations/{prefisso}_{agente}_t*"):
        fp = os.path.join(d, "results.json")
        if not os.path.exists(fp):
            continue
        s = (json.load(open(fp, encoding="utf-8")).get("simulations") or [{}])[0]
        r = (s.get("reward_info") or {}).get("reward")
        if r is not None:
            out[s["task_id"]] = r
    return out


def main() -> None:
    os.chdir(ROOT / "tau2-bench")

    b1, c1 = carica("s6", "llm_agent"), carica("s6", "custom_agent")
    b2, c2 = carica("s9", "llm_agent"), carica("s9", "custom_agent")
    comuni = sorted(set(b1) & set(c1) & set(b2) & set(c2), key=int)
    n = len(comuni)
    print(f"task con entrambe le esecuzioni per entrambi gli agenti: {n}\n")

    pass1_b = sum(1 for t in comuni if b1[t] == 1.0 or b2[t] == 1.0) / n
    pass1_c = sum(1 for t in comuni if c1[t] == 1.0 or c2[t] == 1.0) / n
    pass2_b = sum(1 for t in comuni if b1[t] == 1.0 and b2[t] == 1.0) / n
    pass2_c = sum(1 for t in comuni if c1[t] == 1.0 and c2[t] == 1.0) / n

    print(f"{'':<12}{'pass^1 (almeno 1/2)':>22}{'pass^2 (2/2, affidabilita)':>28}")
    print("-" * 62)
    print(f"{'baseline':<12}{pass1_b:>22.3f}{pass2_b:>28.3f}")
    print(f"{'custom v1':<12}{pass1_c:>22.3f}{pass2_c:>28.3f}")
    print(f"{'divario':<12}{pass1_c - pass1_b:>+22.3f}{pass2_c - pass2_b:>+28.3f}")

    print("\ntask che riescono SEMPRE (2/2) per ciascun agente:")
    sempre_b = [t for t in comuni if b1[t] == 1.0 and b2[t] == 1.0]
    sempre_c = [t for t in comuni if c1[t] == 1.0 and c2[t] == 1.0]
    print(f"  baseline  {len(sempre_b)}/{n}: {sempre_b}")
    print(f"  custom v1 {len(sempre_c)}/{n}: {sempre_c}")

    solo_c = sorted(set(sempre_c) - set(sempre_b), key=int)
    solo_b = sorted(set(sempre_b) - set(sempre_c), key=int)
    print(f"\naffidabili SOLO per custom v1 (mai per baseline): {solo_c}")
    print(f"affidabili SOLO per baseline (mai per custom v1): {solo_b}")


if __name__ == "__main__":
    main()
