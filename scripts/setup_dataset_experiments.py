"""
Crea il dataset "airline-dev-10" su Langfuse con i 10 task id 0-9, e collega
le tracce reali gia' esistenti (baseline e custom_agent) come due Experiment
separati - senza rilanciare nulla, i risultati esistono gia'.

Come si trova quale traccia va con quale task: ogni traccia ha un
session_id del tipo "task_9_sim_<uuid>" - il numero del task e' gia' scritto
li' dentro. Per distinguere baseline da custom_agent, PRIMA VERSIONE di
questo script usava l'orario (custom_agent = notte, baseline = mattina) -
sbagliato: l'ambiente e' stato sospeso mentre Andrea dormiva e l'orologio ha
fatto un salto, quindi alcune tracce vere del custom_agent sono finite
"nel futuro" rispetto al taglio a mezzanotte. Corretto usando un segnale che
non dipende dall'ora: ogni traccia contiene una chiamata figlia chiamata
"agent_response" (baseline, src/tau2/agent/llm_agent.py) oppure
"custom_agent_response" (il nostro agente, src/tau2/agent/custom_agent.py) -
il nome e' scritto nel codice, non cambia mai. Una traccia senza nessuna
delle due (fallita prima ancora che l'agente rispondesse una volta) non e'
un candidato valido per nessun esperimento e viene scartata.

Caso particolare, trovato SBAGLIATO nella prima versione di questo filtro:
non basta "la conversazione con agent_response piu' lunga". Il task 7 ha
sei tracce con agent_response=True (alcune da 20-27s, sembrano run completi)
ma **solo una ha un punteggio reward attaccato** - le altre sono conversazioni
partite bene e poi interrotte a meta' da un errore di quota, mai arrivate a
una valutazione finale di tau2. Il criterio giusto e' "ha un reward", non
"dura di piu'". Tra le tracce con un reward vero per lo stesso
(task, esperimento) - dovrebbe capitare raramente - tengo la piu' recente.

Nota sulla scelta tecnica: per l'aggancio uso POST /api/public/dataset-run-items,
segnato deprecato nella migrazione v3->v4 di Langfuse (sunset 16 nov 2026,
vedi anche docs/langfuse-produzione.md). E' una scelta consapevole: la via
v4 "nativa" (SDK experiment runner) richiederebbe rilanciare dal vivo tutti
i task per creare tracce nuove, cosa che vogliamo evitare visto che i
risultati esistono gia'. La scadenza di deprecazione (16 nov) e' comunque
ben oltre la chiusura di questo progetto (24 ott).
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "tau2-bench" / ".env")

from langfuse import get_client

lf = get_client()

HOST = os.environ.get("LANGFUSE_HOST") or os.environ.get("LANGFUSE_OTEL_HOST")
if not HOST.startswith("http"):
    HOST = f"https://{HOST}"
AUTH = (os.environ["LANGFUSE_PUBLIC_KEY"], os.environ["LANGFUSE_SECRET_KEY"])

DATASET_NAME = "airline-dev-10"
RUN_NAME_BY_CALL_NAME = {
    "agent_response": "baseline",
    "custom_agent_response": "custom_agent",
}


def inspect_trace(trace_id):
    """Per una traccia: chi l'ha prodotta (baseline/custom_agent/None) e se
    ha un reward - cioe' se tau2 e' arrivato a valutarla per intero, non solo
    se l'agente ha risposto almeno una volta."""
    children = lf.api.observations.get_many(
        trace_id=trace_id, limit=50, fields="core,basic"
    ).data
    names = {o.name for o in children}
    run_name = None
    for call_name, candidate_run_name in RUN_NAME_BY_CALL_NAME.items():
        if call_name in names:
            run_name = candidate_run_name
            break
    scores = lf.api.scores_v3.get_many_v3(trace_id=trace_id).data
    reward = next((s.value for s in scores if s.name == "reward"), None)
    return run_name, reward


def main():
    # 1) le 10 righe del registro - idempotente: se lo script viene rilanciato
    #    (es. dopo un crash come questo), non ricrea righe gia' presenti
    existing = lf.api.dataset_items.list(dataset_name=DATASET_NAME).data
    item_ids = {
        i.input["task_id"]: i.id
        for i in existing
        if isinstance(i.input, dict) and "task_id" in i.input
    }
    for task_id in range(10):
        task_id = str(task_id)
        if task_id in item_ids:
            print(f"item task {task_id}: {item_ids[task_id]} (gia' esisteva)")
            continue
        item = lf.create_dataset_item(
            dataset_name=DATASET_NAME, input={"task_id": task_id}
        )
        item_ids[task_id] = item.id
        print(f"item task {task_id}: {item.id}")

    # 2) tutte le tracce radice dei nostri run (poche decine, una pagina basta)
    obs = lf.api.observations.get_many(type="SPAN", limit=100, fields="core,basic")
    roots = [
        o
        for o in obs.data
        if o.is_root_observation and o.session_id and o.session_id.startswith("task_")
    ]

    by_task = {}
    scartate_no_run = 0
    scartate_no_reward = 0
    for o in roots:
        task_id = o.session_id.split("_")[1]
        run_name, reward = inspect_trace(o.trace_id)
        if run_name is None:
            scartate_no_run += 1
            continue
        if reward is None:
            scartate_no_reward += 1
            continue
        by_task.setdefault(task_id, {}).setdefault(run_name, []).append((o, reward))
    print(
        f"{scartate_no_run} tracce scartate: nessuna chiamata "
        f"agent_response/custom_agent_response dentro (fallite troppo presto)"
    )
    print(
        f"{scartate_no_reward} tracce scartate: l'agente ha risposto ma la "
        f"simulazione non e' arrivata a un reward finale (interrotta a meta')"
    )

    # 3) una traccia sola per (task, esperimento): quella con reward piu' recente
    selected = {}
    for task_id, runs in by_task.items():
        selected[task_id] = {}
        for run_name, candidates in runs.items():
            candidates.sort(key=lambda pair: pair[0].start_time, reverse=True)
            if len(candidates) > 1:
                print(
                    f"task {task_id} / {run_name}: {len(candidates)} tracce CON reward "
                    f"({[reward for _, reward in candidates]}), tengo la piu' recente"
                )
            o, reward = candidates[0]
            selected[task_id][run_name] = (o, reward)

    # 4) aggancio: ogni traccia scelta -> la riga giusta, sotto il nome giusto
    for task_id in sorted(selected, key=int):
        if task_id not in item_ids:
            print(f"task {task_id}: nessuna riga corrispondente nel dataset, salto")
            continue
        for run_name, (o, reward) in selected[task_id].items():
            resp = requests.post(
                f"{HOST}/api/public/dataset-run-items",
                auth=AUTH,
                json={
                    "datasetItemId": item_ids[task_id],
                    "traceId": o.trace_id,
                    "runName": run_name,
                },
            )
            status = "ok" if resp.status_code == 200 else f"ERRORE {resp.status_code}: {resp.text[:200]}"
            print(f"task {task_id} -> {run_name} (reward={reward}): {status}")


if __name__ == "__main__":
    main()
