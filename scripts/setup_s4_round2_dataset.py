"""
Crea il dataset "airline-s4-round2" su Langfuse: i 10 task su cui rilanceremo
custom_agent DOPO averlo corretto in base alle famiglie di fallimento trovate
in S4.

Composizione, decisa con Andrea il 2026-08-31:
- 7 task falliti: il task 7 (gia' noto dai 10 di sviluppo) + i 6 nuovi falliti
  in questo giro (18, 23, 33, 37, 39, 44).
- 3 task passati, scelti come "canarini di regressione" - cioe' per accorgerci
  se la correzione rompe qualcosa che prima funzionava. Scelti apposta non a
  caso: 41 e 42 sono tra i piu' complessi del lotto (8 e 10 azioni valutate),
  quindi condividono il profilo dei task che falliscono - se la correzione
  introduce un problema simile, e' su questi due che e' piu' probabile
  vederlo. Il task 0 e' il piu' semplice dei 10 originali (un solo assert),
  incluso come controllo di sanita' a basso costo.

A differenza di scripts/setup_dataset_experiments.py, QUESTO script non
aggancia tracce esistenti: crea solo il Dataset e i suoi Item (l'elenco dei
task da rigiocare), senza chiamare l'agente. Costa zero token Gemini - sono
solo chiamate all'API di Langfuse. Il "prima" (i risultati che l'agente ha
gia' prodotto su questi 10 task) resta scritto nel diario/nella conversazione;
il "dopo" prodotto rilanciando l'agente corretto sara' il primo vero
Experiment Langfuse su questo dataset, fatto con dataset.run_experiment()
(il percorso nativo v4, visibile in UI - a differenza dell'endpoint deprecato
usato nello script precedente).
"""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / "tau2-bench" / ".env")

from langfuse import get_client

lf = get_client()

DATASET_NAME = "airline-s4-round2"

FAILED_TASKS = ["7", "18", "23", "33", "37", "39", "44"]
REGRESSION_CHECK_TASKS = ["0", "41", "42"]


def main():
    try:
        lf.api.datasets.get(dataset_name=DATASET_NAME)
    except Exception:
        lf.api.datasets.create(name=DATASET_NAME)
        print(f"dataset '{DATASET_NAME}' creato")

    existing = lf.api.dataset_items.list(dataset_name=DATASET_NAME).data
    item_ids = {
        i.input["task_id"]: i.id
        for i in existing
        if isinstance(i.input, dict) and "task_id" in i.input
    }

    for task_id in FAILED_TASKS + REGRESSION_CHECK_TASKS:
        if task_id in item_ids:
            print(f"item task {task_id}: {item_ids[task_id]} (gia' esisteva)")
            continue
        category = "fail" if task_id in FAILED_TASKS else "regression_check"
        item = lf.create_dataset_item(
            dataset_name=DATASET_NAME,
            input={"task_id": task_id},
            metadata={"category": category},
        )
        item_ids[task_id] = item.id
        print(f"item task {task_id} ({category}): {item.id}")

    print(f"\nDataset '{DATASET_NAME}': {len(item_ids)} item totali.")


if __name__ == "__main__":
    main()
