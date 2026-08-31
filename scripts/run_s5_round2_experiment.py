"""
S5 round2: rilancia custom_agent (con le tre correzioni di S5, vedi
docs/s5-correzioni.md) sui 10 task del dataset Langfuse "airline-s4-round2",
come vero Experiment nativo v4 (dataset.run_experiment()) - non con
l'endpoint deprecato usato per airline-dev-10 in setup_dataset_experiments.py.

Per ogni dataset item il task esegue dal vivo tau2 tramite run_domain() su un
TextRunConfig per un solo task_id, num_trials=1 - stessa configurazione
validata nei run S4 (run_s4_batch.sh): agent=custom_agent, motore
gemini/gemini-3.5-flash-lite sia per agente che utente, max_retries=1 (quel
parametro rigioca il task intero, non la singola chiamata - i 429 li assorbe
gia' il retry interno di LiteLLM; dopo un fallimento da rate limit si aspetta,
non si rilancia). save_to non viene fissato: resta la convenzione automatica
gia' usata in tutti i run precedenti (data/simulations/<timestamp>_...), cosi'
il file locale prodotto e' quello autorevole da rileggere per il confronto
pre/dopo, e la reward passata come Evaluation qui serve solo a rendere il
punteggio visibile nella UI di Langfuse accanto alla traccia.

Verificato leggendo il codice della SDK (langfuse/_client/client.py,
_process_experiment_item): dataset.run_experiment() apre gia' uno span radice
("experiment-item-run") e ne annida uno figlio ("experiment-item-task") prima
di chiamare il nostro task; il nuovo span aperto da run_single_task
(tau2.utils.langfuse_tracing.simulation_trace, gia' patchato in S2) eredita
quindi lo stesso trace_id come ulteriore figlio - niente trace separate, e il
dataset run item viene linkato correttamente da dataset_run_items.create()
usando quel trace_id/observation_id, senza bisogno di codice nostro in piu'.

Pacing: 65s di pausa dopo ogni task, stesso valore usato in run_s4_batch.sh
per restare sotto la quota RPM di Gemini Flash Lite (gia' esaurita una volta
in questo progetto). max_concurrency=1 forza l'esecuzione sequenziale.
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

DATASET_NAME = "airline-s4-round2"
MODEL = "gemini/gemini-3.5-flash-lite"
PACING_SECONDS = 65
PER_TASK_TIMEOUT = 300  # safety net: nessun run S4 precedente si e' avvicinato

lf = get_client()


def my_task(*, item, **kwargs):
    task_id = item.input["task_id"]
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
    sim = results.simulations[0] if results.simulations else None
    reward = None
    termination_reason = None
    if sim is not None:
        reward = sim.reward_info.reward if sim.reward_info else None
        termination_reason = str(sim.termination_reason)
    time.sleep(PACING_SECONDS)
    return {
        "task_id": task_id,
        "reward": reward,
        "termination_reason": termination_reason,
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


def main():
    dataset = lf.get_dataset(DATASET_NAME)
    result = dataset.run_experiment(
        name="S5 correzioni comportamentali",
        description=(
            "custom_agent con le tre modifiche S5 (docs/s5-correzioni.md), "
            "stesso motore e stessi 10 task del round1 (S4)."
        ),
        task=my_task,
        evaluators=[reward_evaluator],
        max_concurrency=1,
        metadata={"sprint": "S5", "commit": "1a40172"},
    )
    print(result.format())


if __name__ == "__main__":
    main()
