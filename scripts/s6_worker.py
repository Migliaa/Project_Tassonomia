"""
S6 — worker di un blocco di task, legato a UNA chiave API.

Perche' esiste
--------------
Il tier gratuito Gemini limita a 500 richieste al giorno **per progetto**. I 100
task di S6 (50 con `llm_agent` come baseline, 50 con il nostro `custom_agent`) ne
consumano circa 1.600, quindi non stanno in una chiave sola. La soluzione e'
dividerli in blocchi e dare a ogni blocco la chiave di un progetto Google diverso.

Ogni blocco gira in un **processo separato**, e questo risolve due problemi in un
colpo solo:
- la chiave: `load_dotenv` usa `override=False`, quindi basta impostare
  `GEMINI_API_KEY` nell'ambiente del processo prima di importare tau2 e vince
  quella, senza modificare una riga del codice di terzi;
- il rate limit: il limitatore RPM in `llm_utils.generate()` (vedi
  `patches/tau2-infra.patch`) e' per-processo, quindi ogni blocco si autolimita
  sui propri 13 richieste/minuto senza sapere degli altri. E' esattamente il
  comportamento voluto, perche' anche le quote sono per progetto.

La chiave non passa mai dalla riga di comando: il worker riceve il **nome** della
variabile (`--key-var GEMINI_API_KEY_1`) e legge il valore dal `.env`. Cosi' non
finisce nella lista dei processi ne' nei log.

Un task per volta, un file per task
-----------------------------------
`save_to` viene valorizzato per singolo task (`s6_<agente>_t<id>`), non per
blocco: se il processo muore a meta' si perde un task, non venti. Ed e' quello
che rende gratuita la ripresa — al riavvio il worker salta i task che hanno gia'
un `results.json` con un reward valido.

Uso
---
    .venv/Scripts/python.exe ../scripts/s6_worker.py \\
        --key-var GEMINI_API_KEY_1 --agent custom_agent --tasks 0,1,2
"""

import argparse
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
TAU2_ROOT = ROOT / "tau2-bench"

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--key-var", required=True, help="nome della variabile nel .env")
parser.add_argument("--agent", required=True, choices=["llm_agent", "custom_agent"])
parser.add_argument("--tasks", required=True, help="task_id separati da virgola")
parser.add_argument("--model", default="gemini/gemini-3.5-flash-lite")
parser.add_argument("--timeout", type=int, default=900)
parser.add_argument("--retry-wait", type=int, default=90)
# Prefisso della cartella di salvataggio. Serve a tenere separate le versioni
# dell'agente: S6 ha usato "s6", la v2 delle clausole usa "s7". Default "s6" per
# non invalidare la ripresa dei run gia' su disco.
parser.add_argument("--prefix", default="s6")
args = parser.parse_args()

# La chiave va messa in ambiente PRIMA di importare tau2/litellm.
load_dotenv(TAU2_ROOT / ".env")
key = os.environ.get(args.key_var, "").strip()
if not key:
    sys.exit(f"ERRORE: {args.key_var} non valorizzata nel .env")
os.environ["GEMINI_API_KEY"] = key

sys.path.insert(0, str(TAU2_ROOT / "src"))

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.runner.batch import run_domain  # noqa: E402

SIM_DIR = TAU2_ROOT / "data" / "simulations"


def already_done(save_to: str) -> bool:
    """Un task e' fatto se esiste il suo results.json con un reward valorizzato.
    E' cio' che rende la ripresa gratuita dopo un'interruzione per quota."""
    path = SIM_DIR / save_to / "results.json"
    if not path.exists():
        return False
    try:
        import json

        data = json.load(open(path, encoding="utf-8"))
        sims = data.get("simulations") or []
        return bool(sims) and (sims[0].get("reward_info") or {}).get("reward") is not None
    except Exception:
        return False


def discard_incomplete(save_to: str) -> bool:
    """Rimuove una cartella di simulazione senza reward.

    Serve perche' `run_domain` non e' pensato per girare senza un terminale: se
    trova un `results.json` gia' presente chiede a schermo "Do you want to resume
    the run? (y/n)", e in un processo senza stdin quella domanda diventa un
    EOFError. E' cosi' che in S7 una caduta di rete ha fatto perdere cinque task
    invece di zero: il primo tentativo moriva per la rete lasciando la cartella a
    meta', e il secondo non falliva per la rete ma per quella domanda.

    Si cancella solo quando `already_done()` ha gia' detto di no, cioe' quando il
    reward manca: non c'e' nulla da salvare in quel file, solo un dialogo troncato.
    """
    import shutil

    path = SIM_DIR / save_to
    if not path.exists():
        return False
    shutil.rmtree(path, ignore_errors=True)
    return True


def run_task(task_id: str, save_to: str):
    config = TextRunConfig(
        domain="airline",
        task_set_name="airline",
        agent=args.agent,
        llm_agent=args.model,
        user="user_simulator",
        llm_user=args.model,
        task_ids=[task_id],
        num_trials=1,
        # Regola di progetto: max_retries 1. Quel parametro rigioca il TASK
        # INTERO, non la singola chiamata; alzarlo contro un rate limit
        # moltiplica i token sprecati. I 429 li assorbe LiteLLM piu' il
        # limitatore RPM nostro.
        max_retries=1,
        max_concurrency=1,
        timeout=args.timeout,
        save_to=save_to,
    )
    results = run_domain(config)
    sims = results.simulations or []
    return sims[0] if sims else None


def main() -> None:
    task_ids = [t.strip() for t in args.tasks.split(",") if t.strip()]
    label = f"[{args.key_var} · {args.agent}]"
    print(f"{label} {len(task_ids)} task da eseguire: {task_ids}", flush=True)

    ok, skipped, failed = 0, 0, []
    for i, task_id in enumerate(task_ids, 1):
        save_to = f"{args.prefix}_{args.agent}_t{task_id}"
        if already_done(save_to):
            skipped += 1
            print(f"{label} ({i}/{len(task_ids)}) task {task_id}: gia' fatto, salto", flush=True)
            continue

        sim = None
        for attempt in (1, 2):
            try:
                if discard_incomplete(save_to):
                    print(f"{label} task {task_id}: scarto una simulazione incompleta", flush=True)
                sim = run_task(task_id, save_to)
            except Exception as e:
                print(f"{label} task {task_id} tentativo {attempt}: eccezione {type(e).__name__}: {e}", flush=True)
                sim = None
            if sim is not None and sim.reward_info is not None:
                break
            if attempt == 1:
                print(f"{label} task {task_id}: nessun risultato, attendo {args.retry_wait}s", flush=True)
                time.sleep(args.retry_wait)

        if sim is not None and sim.reward_info is not None:
            ok += 1
            print(f"{label} ({i}/{len(task_ids)}) task {task_id}: reward {sim.reward_info.reward}", flush=True)
        else:
            failed.append(task_id)
            print(f"{label} ({i}/{len(task_ids)}) task {task_id}: FALLITO senza risultato", flush=True)

    print(f"{label} FINE — completati {ok}, saltati {skipped}, falliti {len(failed)} {failed}", flush=True)


if __name__ == "__main__":
    main()
