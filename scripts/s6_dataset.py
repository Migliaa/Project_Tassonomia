"""
S6 — crea (o aggiorna) il dataset Langfuse pulito con tutti e 50 i task airline.

Nessuna chiamata a un LLM: legge le definizioni locali dei task. Idempotente —
`create_dataset_item` con un `id` esplicito fa upsert, quindi si puo' rilanciare
senza creare duplicati.

Ogni item porta:
- `input`    : task_id + lo scenario (purpose, policy rilevante, note) dal
               `Task.description`, cosi' chi apre l'item capisce cosa doveva
               succedere senza aprire il codice del benchmark;
- `expected_output` : il ground truth (`Task.evaluation_criteria`: azioni attese,
               informazioni da comunicare, asserzioni in linguaggio naturale);
- `metadata` : `task_id` e `sprint`.

Il dataset e' uno solo per tutti e 100 i run: **50 item, due Run** (baseline
`llm_agent` e `custom_agent`). E' cosi' che la pagina Experiments di Langfuse
mette due esecuzioni a confronto item per item - due dataset separati non
sarebbero confrontabili.
"""

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
TAU2_ROOT = ROOT / "tau2-bench"
load_dotenv(TAU2_ROOT / ".env")
sys.path.insert(0, str(TAU2_ROOT / "src"))

from langfuse import get_client  # noqa: E402

from tau2.runner.helpers import get_tasks  # noqa: E402

DATASET_NAME = "airline-50-baseline-vs-custom"
TASK_SET_NAME = "airline"

DESCRIPTION = (
    "I 50 task del dominio airline di tau2-bench. Un item per task, con lo "
    "scenario come input e il ground truth come expected_output. Ospita due Run "
    "confrontabili item per item: 'baseline llm_agent' (agente di default, senza "
    "i nostri cablaggi) e 'custom_agent' (l'agente costruito in S3 e corretto in "
    "S5). Stesso motore per entrambi: gemini-3.5-flash-lite come agente e come "
    "simulatore-utente."
)


def main() -> None:
    lf = get_client()
    lf.create_dataset(name=DATASET_NAME, description=DESCRIPTION)

    tasks = get_tasks(task_set_name=TASK_SET_NAME)
    print(f"task trovati nel set '{TASK_SET_NAME}': {len(tasks)}")

    for task in tasks:
        scenario = str(task.description) if task.description else None
        expected = (
            str(task.evaluation_criteria) if task.evaluation_criteria else None
        )
        lf.create_dataset_item(
            dataset_name=DATASET_NAME,
            # id esplicito e stabile: rende l'operazione un upsert, quindi lo
            # script si puo' rilanciare senza sporcare il dataset.
            id=f"airline-{task.id}",
            input={"task_id": task.id, "scenario": scenario},
            expected_output=expected,
            metadata={"task_id": task.id, "sprint": "S6"},
        )

    lf.flush()
    dataset = lf.get_dataset(DATASET_NAME)
    print(f"dataset '{DATASET_NAME}': {len(dataset.items)} item")


if __name__ == "__main__":
    main()
