"""
Ripopola su Langfuse i Run dei round precedenti, rileggendo i `results.json`
locali invece di rigiocare le simulazioni: **costo zero, nessuna chiamata LLM,
nessun consumo di quota.**

PERCHE'
-------
I Run del round1 e del round2 sono nati prima del passo 0 di S5, quindi in
Langfuse hanno solo `reward` (e il round2 anche `db_check`). Le metriche
per-azione - `write_action_score`, `unexpected_writes`, `wrong_argument_writes` -
e l'etichetta `failure_family` esistono solo dal round3 in avanti, il che rende
impossibile il confronto visivo fianco a fianco nella pagina Experiments: e'
proprio quel confronto il materiale che serve al report.

Le simulazioni pero' ci sono tutte, salvate in `tau2-bench/data/simulations/`.
Ripubblicarle come Run nuovi, con lo stesso set di score del round3, ricostruisce
la progressione completa senza spendere niente.

COSA PRODUCE
------------
Due Run nuovi nel dataset `airline-s4-round2`, accanto a quello del round3:
- "S5 round1 - agente prima delle correzioni": il custom_agent uscito da S3,
  cioe' lo stato su cui e' stata costruita la tassonomia di S4.
- "S5 round2 - agente dopo la prima stesura delle correzioni": la prima
  implementazione di S5, quella che aveva dato 4/10.

Ogni item porta `reused_from` con la cartella di provenienza: sono misure vere,
gia' fatte, non rigiocate qui - e chi legge il report deve poterlo vedere.

I Run originali del round2 restano dove sono: sono il documento storico di come
sono stati prodotti (compresi i due parziali per quota). Questi nuovi non li
sostituiscono, li rendono confrontabili.

USO
---
    cd tau2-bench && PYTHONIOENCODING=utf-8 PYTHONUTF8=1 \\
        .venv/Scripts/python.exe ../scripts/backfill_langfuse_runs.py
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
TAU2_ROOT = ROOT / "tau2-bench"
load_dotenv(TAU2_ROOT / ".env")

sys.path.insert(0, str(TAU2_ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from langfuse import get_client  # noqa: E402

import run_s5_round2_experiment as base  # noqa: E402

SUF = "_airline_custom_agent_gemini-3.5-flash-lite_user_simulator_gemini-3.5-flash-lite"

# Cartelle di `tau2-bench/data/simulations/` per ciascun round.
# Round1 = custom_agent di S3, prima di qualunque correzione S5 (e' lo stato su
# cui e' stata costruita la tassonomia di S4).
ROUND1 = {
    "0": "20260830_234429",
    "7": "20260831_000345",
    "18": "20260831_125156",
    "23": "20260831_123627",
    "33": "20260831_121236",
    "37": "20260831_124310",
    "39": "20260831_123304",
    "41": "20260831_123950",
    "42": "20260831_123442",
    "44": "20260831_115327",
}

# Round2 = prima stesura delle correzioni S5 (commit 1a40172), quella da 4/10.
ROUND2 = {
    "0": "20260901_022257",
    "7": "20260901_170406",
    "18": "20260901_165542",
    "23": "20260901_170941",
    "33": "20260901_171224",
    "37": "20260901_023157",
    "39": "20260901_023004",
    "41": "20260901_022119",
    "42": "20260901_021757",
    "44": "20260901_171651",
}

RUNS = [
    (
        "S5 round1 - agente prima delle correzioni",
        ROUND1,
        "1a40172^",
        "round1",
        "custom_agent come uscito da S3, prima di qualunque correzione di S5. "
        "E' lo stato dell'agente su cui e' stata costruita la tassonomia dei "
        "fallimenti di S4. Ripubblicato dai results.json locali (campo "
        "reused_from su ogni item): misure vere gia' eseguite, non rigiocate.",
    ),
    (
        "S5 round2 - agente dopo la prima stesura delle correzioni",
        ROUND2,
        "1a40172",
        "round2",
        "custom_agent dopo la prima implementazione di S5: POLICY_HIGHLIGHTS in "
        "inglese col quarto punto riparato, OUTPUT_CONVENTIONS, e cinque "
        "clausole in HANDLING_CUSTOMER_REQUESTS. E' il run che aveva dato 4/10 "
        "e in cui due fallimenti erano causati dalle regole stesse. "
        "Ripubblicato dai results.json locali (campo reused_from su ogni item).",
    ),
]


def main() -> None:
    lf = get_client()
    dataset = lf.get_dataset(base.DATASET_NAME)
    items = list(dataset.items)

    for name, mapping, commit, iterazione, description in RUNS:
        missing = [
            t for t, d in mapping.items()
            if not (TAU2_ROOT / "data" / "simulations" / (d + SUF) / "results.json").exists()
        ]
        if missing:
            print(f"[{name}] SALTATO: mancano i results.json per {missing}")
            continue

        # Il task viene servito interamente dalla cache locale: nessun LLM.
        base.REUSE_EXISTING = {t: d + SUF for t, d in mapping.items()}

        result = lf.run_experiment(
            name=name,
            description=description,
            data=items,
            task=base.my_task,
            evaluators=[
                base.reward_evaluator,
                base.db_check_evaluator,
                base.write_action_evaluator,
                base.unexpected_writes_evaluator,
                base.wrong_argument_writes_evaluator,
                base.failure_family_evaluator,
            ],
            max_concurrency=1,
            metadata={
                "sprint": "S5",
                "commit": commit,
                "iterazione": iterazione,
                "ripubblicato_da_locale": True,
            },
        )
        print(result.format())


if __name__ == "__main__":
    main()
