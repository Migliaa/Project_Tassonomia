"""
S5 round2: rilancia custom_agent (con le tre correzioni di S5, vedi
docs/s5-correzioni.md) sui 10 task del dataset Langfuse "airline-s4-round2",
come vero Experiment nativo v4 (dataset.run_experiment()) - non con
l'endpoint deprecato usato per airline-dev-10 in setup_dataset_experiments.py.

Per ogni dataset item il task esegue dal vivo tau2 tramite run_domain() su un
TextRunConfig per un solo task_id, num_trials=1 - stessa configurazione
validata nei run S4 (run_s4_batch.sh): agent=custom_agent, motore
gemini/gemini-3.5-flash-lite sia per agente che utente, max_retries=1 a
livello tau2 (quel parametro rigioca il task intero, non la singola
chiamata). save_to non viene fissato: resta la convenzione automatica gia'
usata in tutti i run precedenti (data/simulations/<timestamp>_...), cosi' il
file locale prodotto resta quello autorevole da rileggere per il confronto
pre/dopo.

Verificato leggendo il codice della SDK (langfuse/_client/client.py,
_process_experiment_item): dataset.run_experiment() apre gia' uno span radice
("experiment-item-run") e ne annida uno figlio ("experiment-item-task") prima
di chiamare il nostro task; il nuovo span aperto da run_single_task
(tau2.utils.langfuse_tracing.simulation_trace, gia' patchato in S2) eredita
quindi lo stesso trace_id come ulteriore figlio - niente trace separate, e il
dataset run item viene linkato correttamente da dataset_run_items.create()
usando quel trace_id/observation_id, senza bisogno di codice nostro in piu'.

CORREZIONE 2026-09-01, dopo il secondo tentativo: Andrea ha fatto notare che
in passato i dataset item collegati in Langfuse non mostravano nulla di
rilevante nella sezione Datasets - bisognava sempre saltare a Tracing per
vedere il dialogo. Motivo: Dataset Item e Trace sono entita' diverse nel
modello dati di Langfuse, e il mio primo `output` conteneva solo
{task_id, reward, termination_reason} - non il contenuto della conversazione.
Corretto qui aggiungendo:
- `prepare_dataset_items()`: arricchisce ogni item con lo scenario del task
  (purpose + policy rilevante, da Task.description) come input e il ground
  truth (Task.evaluation_criteria, gia' testuale via il suo __str__) come
  expected_output - upsert idempotente via create_dataset_item(id=...),
  nessuna chiamata a un LLM, costo zero.
- `my_task` ora ritorna anche un `transcript` leggibile (ogni turno
  UTENTE/AGENTE/TOOL) e il dettaglio dei check (DB, azioni, comunicazione),
  cosi' la colonna Output del Dataset Run mostra il dialogo e il verdetto
  senza dover aprire la trace.
Da qui in avanti questo e' lo standard per ogni run collegato a un dataset,
compresi i futuri batch piu' grandi.

Resilienza aggiunta dopo aver osservato due limiti di quota Gemini diversi
nello stesso giorno (uno giornaliero, uno RPM=15): un item che fallisce con
nessun risultato (reward_info assente, es. rate limit) ora aspetta
RETRY_BACKOFF_SECONDS e riprova UNA sola volta a livello di script - non
un rilancio cieco dell'intero esperimento, ma l'automazione della regola di
progetto "dopo un fallimento da rate limit si aspetta". Se fallisce di nuovo,
l'item resta a reward=None/0.0 e va rilanciato in un secondo momento.

Pacing: 75s di pausa dopo ogni task completato (alzato da 65s dopo aver
osservato un 429 anche con 65s), max_concurrency=1 per esecuzione
sequenziale.
"""

import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
TAU2_ROOT = ROOT / "tau2-bench"
load_dotenv(TAU2_ROOT / ".env")

import sys

sys.path.insert(0, str(TAU2_ROOT / "src"))

from langfuse import Evaluation, get_client  # noqa: E402

from tau2.data_model.simulation import TextRunConfig  # noqa: E402
from tau2.runner.batch import run_domain  # noqa: E402
from tau2.runner.helpers import get_tasks  # noqa: E402

DATASET_NAME = "airline-s4-round2"
TASK_SET_NAME = "airline"
MODEL = "gemini/gemini-3.5-flash-lite"
PACING_SECONDS = 75
RETRY_BACKOFF_SECONDS = 75
PER_TASK_TIMEOUT = 300  # safety net: nessun run S4 precedente si e' avvicinato

# Se valorizzato, lancia solo questi task_id invece di tutto il dataset - per
# rilanciare gli item senza dato di un run precedente (es. falliti per quota)
# senza rispendere sui task gia' completati. Resta lo STESSO dataset: crea un
# secondo Run piu' piccolo, confrontabile nella UI con il primo. None = tutti.
TASK_IDS_FILTER = ["44", "33", "23", "7"]

lf = get_client()


def prepare_dataset_items(dataset):
    """Arricchisce gli item gia' esistenti con scenario (input) e ground
    truth (expected_output), letti dalle definizioni locali dei task -
    nessuna chiamata a un LLM. Upsert via id: non crea duplicati."""
    task_ids = [item.input["task_id"] for item in dataset.items]
    tasks_by_id = {
        t.id: t for t in get_tasks(task_set_name=TASK_SET_NAME, task_ids=task_ids)
    }
    for item in dataset.items:
        task_id = item.input["task_id"]
        task = tasks_by_id.get(task_id)
        if task is None:
            continue
        scenario = str(task.description) if task.description else None
        expected = str(task.evaluation_criteria) if task.evaluation_criteria else None
        lf.create_dataset_item(
            dataset_name=DATASET_NAME,
            id=item.id,
            input={"task_id": task_id, "scenario": scenario},
            expected_output=expected,
            metadata=item.metadata,
        )


def build_transcript(messages):
    """Dialogo leggibile turno per turno, per la colonna Output del Dataset
    Run - cosi' si legge la conversazione senza aprire la trace."""
    lines = []
    for m in messages or []:
        role = getattr(m, "role", None)
        content = getattr(m, "content", None)
        tool_calls = getattr(m, "tool_calls", None) or []
        if role == "system":
            continue
        elif role == "user":
            if content:
                lines.append(f"UTENTE: {content}")
            for tc in tool_calls:
                lines.append(f"UTENTE -> tool {tc.name}({tc.arguments})")
        elif role == "assistant":
            if content:
                lines.append(f"AGENTE: {content}")
            for tc in tool_calls:
                lines.append(f"AGENTE -> tool {tc.name}({tc.arguments})")
        elif role == "tool":
            prefix = "TOOL[ERRORE]" if getattr(m, "error", False) else "TOOL"
            lines.append(f"{prefix} <- {content}")
        else:
            lines.append(f"{role}: {content}")
    return "\n".join(lines)


def run_once(task_id):
    config = TextRunConfig(
        agent="custom_agent",
        llm_agent=MODEL,
        user="user_simulator",
        llm_user=MODEL,
        task_ids=[task_id],
        num_trials=1,
        max_retries=1,
        timeout=PER_TASK_TIMEOUT,
    )
    results = run_domain(config)
    return results.simulations[0] if results.simulations else None


def my_task(*, item, **kwargs):
    task_id = item.input["task_id"]
    sim = run_once(task_id)
    if sim is None or sim.reward_info is None:
        time.sleep(RETRY_BACKOFF_SECONDS)
        sim = run_once(task_id)

    reward = None
    reward_breakdown = None
    termination_reason = None
    db_check = None
    action_checks_summary = None
    communicate_checks = None
    transcript = None

    if sim is not None:
        termination_reason = str(sim.termination_reason)
        transcript = build_transcript(sim.messages)
        ri = sim.reward_info
        if ri is not None:
            reward = ri.reward
            if ri.reward_breakdown:
                reward_breakdown = {
                    (k.value if hasattr(k, "value") else str(k)): v
                    for k, v in ri.reward_breakdown.items()
                }
            if ri.db_check is not None:
                db_check = {
                    "passed": ri.db_check.db_match,
                    "reward": ri.db_check.db_reward,
                }
            if ri.action_checks:
                correct = sum(1 for c in ri.action_checks if c.action_match)
                action_checks_summary = f"{correct}/{len(ri.action_checks)} azioni corrette"
            if ri.communicate_checks:
                communicate_checks = [
                    {"info": c.info, "met": c.met} for c in ri.communicate_checks
                ]

    time.sleep(PACING_SECONDS)
    return {
        "task_id": task_id,
        "reward": reward,
        "reward_breakdown": reward_breakdown,
        "termination_reason": termination_reason,
        "db_check": db_check,
        "action_checks_summary": action_checks_summary,
        "communicate_checks": communicate_checks,
        "transcript": transcript,
    }


def reward_evaluator(*, input, output, expected_output, metadata, **kwargs):
    # Un reward None (quota/errore infra) va registrato come fallimento esplicito,
    # non omesso: altrimenti la media aggregata di Langfuse si calcola solo sugli
    # item riusciti e sembra un successo anche quando 9 item su 10 non hanno girato
    # (successo il 2026-08-31: "Average Scores: reward: 1.000" su 1 item completato).
    reward = output.get("reward") if isinstance(output, dict) else None
    if reward is None:
        return Evaluation(
            name="reward",
            value=0.0,
            comment=f"nessun risultato (termination_reason={output.get('termination_reason') if isinstance(output, dict) else None})",
        )
    return Evaluation(name="reward", value=float(reward))


def db_check_evaluator(*, input, output, expected_output, metadata, **kwargs):
    db_check = output.get("db_check") if isinstance(output, dict) else None
    if db_check is None:
        return []
    return Evaluation(name="db_check", value=1.0 if db_check["passed"] else 0.0)


def main():
    dataset = lf.get_dataset(DATASET_NAME)
    prepare_dataset_items(dataset)
    dataset = lf.get_dataset(DATASET_NAME)  # ricarica con input/expected_output aggiornati

    items = dataset.items
    description = (
        "custom_agent con le tre modifiche S5 (docs/s5-correzioni.md), "
        "stesso motore e stessi 10 task del round1 (S4)."
    )
    if TASK_IDS_FILTER is not None:
        items = [it for it in items if it.input["task_id"] in TASK_IDS_FILTER]
        description += (
            f" Rilancio parziale di {TASK_IDS_FILTER}: item senza dato "
            "(quota) nel run precedente sullo stesso dataset."
        )
        print(f"Rilancio solo {len(items)} item: {sorted(TASK_IDS_FILTER)}")

    run_kwargs = dict(
        name="S5 correzioni comportamentali",
        description=description,
        task=my_task,
        evaluators=[reward_evaluator, db_check_evaluator],
        max_concurrency=1,
        metadata={"sprint": "S5", "commit": "1a40172"},
    )
    if TASK_IDS_FILTER is not None:
        result = lf.run_experiment(data=items, **run_kwargs)
    else:
        result = dataset.run_experiment(**run_kwargs)
    print(result.format())


if __name__ == "__main__":
    main()
