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

AGGIUNTA 2026-09-01 (passo 0 della ripresa di S5): oltre a `reward` e
`db_check` il run pubblica ora tre score per-azione calcolati da
`scripts/action_metrics.py` - `write_action_score`, `unexpected_writes`,
`wrong_argument_writes`. Motivo: il reward binario aveva nascosto quasi tutto il
segnale del round2 (vedi DIARIO.md, "il reward binario stava nascondendo il
lavoro"), e senza queste tre non si distingue una regola che non morde da una che
morde nella direzione sbagliata. Costo zero: si calcolano dalla simulazione gia'
prodotta, nessuna chiamata a un LLM.

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
sys.path.insert(0, str(ROOT / "scripts"))

from langfuse import Evaluation, get_client  # noqa: E402

from tau2.data_model.simulation import Results, TextRunConfig  # noqa: E402
from tau2.runner.batch import run_domain  # noqa: E402
from tau2.runner.helpers import get_tasks  # noqa: E402

from action_metrics import (  # noqa: E402
    compute_action_metrics,
    get_domain_tool_types,
)

DATASET_NAME = "airline-s4-round2"
TASK_SET_NAME = "airline"
DOMAIN = "airline"

# Nome del Run dentro il dataset. Ogni iterazione del ciclo diagnosi-correzione-verifica
# e' un Run distinto sullo STESSO dataset: cosi' in Langfuse restano confrontabili fianco
# a fianco invece di disperdersi in dataset diversi. Cambiarlo a ogni lancio.
RUN_NAME = "S5 round3 - agente dopo il passo 1"
MODEL = "gemini/gemini-3.5-flash-lite"
PACING_SECONDS = 75
RETRY_BACKOFF_SECONDS = 75
# Safety net, NON un limite di lavoro. Alzato a 900s il 2026-09-01 dopo che la
# sonda sul task 44 e' stata troncata a 321s: il task era durato 134s nel round2,
# ma la latenza dell'API varia di un fattore 3 nella stessa giornata, quindi un
# timeout tarato sulla durata osservata taglia il task piu' lungo. Un run troncato
# costa comunque i suoi token e non risponde a niente: meglio largo.
PER_TASK_TIMEOUT = 900

# Se valorizzato, lancia solo questi task_id invece di tutto il dataset - per
# rilanciare gli item senza dato di un run precedente (es. falliti per quota)
# senza rispendere sui task gia' completati. Resta lo STESSO dataset: crea un
# secondo Run piu' piccolo, confrontabile nella UI con il primo. None = tutti.
TASK_IDS_FILTER = None

# Task gia' misurati con QUESTA versione dell'agente: invece di rigiocarli si
# riusa la simulazione salvata. Cosi' il Run del dataset resta completo a dieci
# item - che serve per il confronto visivo nella pagina Experiments - senza
# rispendere quota su un task il cui risultato conosciamo gia'.
# Ogni item riusato porta "reused_from" nel proprio output: non e' una misura
# nuova e non deve sembrarlo a chi legge il report.
REUSE_EXISTING = {
    # Round 3 completo del 2026-09-01: tutte e dieci le simulazioni sono gia' state
    # eseguite e salvate in locale. Elencate qui per poter ripubblicare il Run con il
    # nome corretto senza rigiocare nulla - il primo tentativo aveva ereditato il nome
    # della sonda (una sostituzione di stringa che non aveva fatto match), e un Run mal
    # nominato rende illeggibile il confronto nella pagina Experiments.
    # Il campo reused_from finisce nell'output di ogni item: chi legge vede che quel
    # risultato non e' stato prodotto da questa esecuzione.
    "0": "20260901_225634_airline_custom_agent_gemini-3.5-flash-lite_user_simulator_gemini-3.5-flash-lite",
    "7": "20260901_224145_airline_custom_agent_gemini-3.5-flash-lite_user_simulator_gemini-3.5-flash-lite",
    "18": "20260901_224410_airline_custom_agent_gemini-3.5-flash-lite_user_simulator_gemini-3.5-flash-lite",
    "23": "20260901_224635_airline_custom_agent_gemini-3.5-flash-lite_user_simulator_gemini-3.5-flash-lite",
    "33": "20260901_224905_airline_custom_agent_gemini-3.5-flash-lite_user_simulator_gemini-3.5-flash-lite",
    "37": "20260901_225147_airline_custom_agent_gemini-3.5-flash-lite_user_simulator_gemini-3.5-flash-lite",
    "39": "20260901_225407_airline_custom_agent_gemini-3.5-flash-lite_user_simulator_gemini-3.5-flash-lite",
    "41": "20260901_225806_airline_custom_agent_gemini-3.5-flash-lite_user_simulator_gemini-3.5-flash-lite",
    "42": "20260901_230040_airline_custom_agent_gemini-3.5-flash-lite_user_simulator_gemini-3.5-flash-lite",
    "44": "20260901_223046_airline_custom_agent_gemini-3.5-flash-lite_user_simulator_gemini-3.5-flash-lite",
}

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


_TASKS_CACHE = {}


def _task_definitions():
    """Definizioni dei task del dominio, caricate una volta sola: servono per il
    ground truth delle azioni, che le metriche per-azione confrontano con quello
    che l'agente ha davvero chiamato."""
    if not _TASKS_CACHE:
        for t in get_tasks(task_set_name=TASK_SET_NAME):
            _TASKS_CACHE[t.id] = t
    return _TASKS_CACHE


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


def load_saved_simulation(dir_name, task_id):
    """Rilegge una simulazione gia' salvata come oggetto pydantic, cosi' il resto
    del codice (transcript, reward_info) non distingue fra riusata e nuova."""
    path = TAU2_ROOT / "data" / "simulations" / dir_name / "results.json"
    results = Results.load(path)
    for sim in results.simulations:
        if sim.task_id == task_id:
            return sim
    return None


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
    reused_from = REUSE_EXISTING.get(task_id)
    if reused_from:
        print(f"Task {task_id}: riuso la simulazione {reused_from} (nessuna chiamata LLM)")
        sim = load_saved_simulation(reused_from, task_id)
    else:
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

    # Metriche per-azione (scripts/action_metrics.py): il reward binario da solo
    # non distingue una regola che non morde da una che morde troppo. Calcolate
    # qui e non solo a posteriori cosi' finiscono su Langfuse insieme al run.
    action_metrics = None
    if sim is not None:
        task = _task_definitions().get(task_id)
        if task is not None and task.evaluation_criteria is not None:
            golden = [a.model_dump() for a in (task.evaluation_criteria.actions or [])]
            action_metrics = compute_action_metrics(
                sim.model_dump(), golden, get_domain_tool_types(DOMAIN)
            )

    if not reused_from:
        time.sleep(PACING_SECONDS)
    return {
        "task_id": task_id,
        "reused_from": reused_from,
        "action_metrics": action_metrics,
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


def _metric(output, key):
    am = output.get("action_metrics") if isinstance(output, dict) else None
    return (am or {}).get(key)


def write_action_evaluator(*, input, output, expected_output, metadata, **kwargs):
    """Quante delle scritture attese sono state eseguite: 0.0-1.0 invece del
    binario. Distingue "non ha fatto niente" da "ne ha fatte due su tre"."""
    v = _metric(output, "write_action_score")
    if v is None:
        return []
    return Evaluation(name="write_action_score", value=float(v))


def unexpected_writes_evaluator(*, input, output, expected_output, metadata, **kwargs):
    """Sovra-esecuzione: scritture su prenotazioni che il ground truth non
    modifica mai. Un task puo' avere write_action_score 1.0 e fallire il DB check
    solo per queste (task 44, round2)."""
    v = _metric(output, "unexpected_writes")
    if v is None:
        return []
    detail = [
        s["name"]
        for s in (_metric(output, "spurious_writes_detail") or [])
        if s.get("new_target")
    ]
    return Evaluation(
        name="unexpected_writes",
        value=float(v),
        comment=", ".join(detail) or None,
    )


def wrong_argument_writes_evaluator(
    *, input, output, expected_output, metadata, **kwargs
):
    """Scritture sulla prenotazione giusta ma con un argomento sbagliato (tipico:
    il metodo di pagamento). Problema opposto alla sovra-esecuzione e con una
    correzione opposta, quindi conta separatamente."""
    spur = _metric(output, "spurious_writes")
    unex = _metric(output, "unexpected_writes")
    if spur is None or unex is None:
        return []
    return Evaluation(name="wrong_argument_writes", value=float(spur - unex))


# Triage dei fallimenti: etichetta categoriale pubblicata accanto al reward.
#
# Perche': il reward di tau2-bench e' binario e mette nello stesso mucchio tre cose
# molto diverse - l'agente ha sbagliato; l'agente ha fatto la cosa giusta ma il
# ground truth ne voleva un'altra; il simulatore-utente ha chiuso prima che l'agente
# potesse agire. Senza un'etichetta, chi apre la pagina Experiments legge dieci
# righe e vede solo "0.0" o "1.0", e un caso noto e spiegato sembra un errore
# dell'agente. Questa colonna dice a chi guarda *di che tipo* e' il fallimento.
#
# I valori sono pochi e stabili di proposito, cosi' la colonna resta filtrabile:
#   - "famiglia N - <titolo>"   : una delle famiglie della tassonomia S4
#   - "ground truth incoerente" : l'atteso del benchmark contraddice la policy del
#                                 dominio o non e' ricostruibile dalla conversazione
#   - "da diagnosticare"        : fallimento non ancora classificato. E' il default,
#                                 apposta: un fallimento senza etichetta non deve
#                                 poter passare per "gia' capito".
#   - "run non riuscito"        : nessun risultato (quota, rete). Non e' un
#                                 fallimento dell'agente e non va contato come tale.
#
# La classificazione e' la NOSTRA diagnosi alla data indicata, non un dato del
# benchmark: va riverificata quando cambia l'agente. Il task 23 e' l'esempio -
# fino al round2 era un fallimento correggibile, nel round3 e' diventato famiglia 4.
KNOWN_FAILURE_FAMILIES = {
    "7": (
        "ground truth incoerente",
        "L'atteso e' $1.628, che somma anche due prenotazioni cancellate durante "
        "la telefonata stessa, valorizzate al prezzo di prima delle modifiche. "
        "L'agente dichiara entrambe le letture di 'other' ($708 e $2.076) e nessuna "
        "coincide; anche il baseline llm_agent rispondeva $708. Non correggibile "
        "con una regola difendibile. Vedi docs/s5-correzioni.md.",
    ),
    "23": (
        "famiglia 4 - utente chiude nel turno della conferma",
        "Round3: la catena progettata ha funzionato per intero - l'agente comunica "
        "il limite di un solo metodo di pagamento, il cliente propone le tre "
        "prenotazioni separate, l'agente stende il piano corretto - e il "
        "simulatore risponde 'Yes, please proceed' chiudendo con ###STOP### nello "
        "stesso messaggio, prima dell'esecuzione. Famiglia dichiarata non "
        "correggibile in S4 leggendo orchestrator.py:836-843.",
    ),
    "39": (
        "ground truth incoerente",
        "Il ground truth chiede di cancellare MSJ4OA, che non soddisfa nessuna "
        "condizione di cancellazione della policy - ed e' indistinguibile da "
        "S61CZX (task 44), che lo stesso benchmark vieta di cancellare. La "
        "description del task contraddice il proprio elenco di azioni attese. "
        "Scelta la lettura fedele alla policy, che salva il 44. Vedi "
        "docs/s5-correzioni.md, 'Task 39 - dichiarato non correggibile'.",
    ),
}


def failure_family_evaluator(*, input, output, expected_output, metadata, **kwargs):
    """Etichetta categoriale sul tipo di fallimento. Nessuna etichetta sui task
    che passano: la colonna serve a leggere gli zeri, non a decorare gli uni."""
    if not isinstance(output, dict):
        return []
    reward = output.get("reward")
    if reward is None:
        return Evaluation(
            name="failure_family",
            value="run non riuscito",
            data_type="CATEGORICAL",
            comment=f"nessun risultato (termination_reason={output.get('termination_reason')})",
        )
    if float(reward) >= 1.0:
        return []
    family, why = KNOWN_FAILURE_FAMILIES.get(
        output.get("task_id"),
        (
            "da diagnosticare",
            "Fallimento non ancora classificato nella tassonomia. Va letto con le "
            "metriche per-azione (write_action_score, unexpected_writes, "
            "wrong_argument_writes) prima di concludere.",
        ),
    )
    return Evaluation(
        name="failure_family", value=family, data_type="CATEGORICAL", comment=why
    )


def main():
    dataset = lf.get_dataset(DATASET_NAME)
    prepare_dataset_items(dataset)
    dataset = lf.get_dataset(DATASET_NAME)  # ricarica con input/expected_output aggiornati

    items = dataset.items
    description = (
        "Round 3. custom_agent dopo il passo 1 di S5 (docs/s5-correzioni.md): "
        "clausola pagamenti riscritta per prenotazione, clausola di verifica "
        "della policy prima di ogni scrittura, clausola sulle parole di scopo "
        "rimossa. Stesso motore e stessi dieci task del round1 e del round2, "
        "quindi confrontabile item per item. Il task 44 riusa la simulazione "
        "gia' misurata della sonda 5 (campo reused_from nell'output): stessa "
        "versione dell'agente, non rigiocato per non sprecare quota."
    )
    if TASK_IDS_FILTER is not None:
        items = [it for it in items if it.input["task_id"] in TASK_IDS_FILTER]
        description += (
            f" Eseguito solo su {TASK_IDS_FILTER}, sullo stesso dataset "
            "(crea un Run in piu', non un dataset in piu')."
        )
        print(f"Rilancio solo {len(items)} item: {sorted(TASK_IDS_FILTER)}")

    run_kwargs = dict(
        name=RUN_NAME,
        description=description,
        task=my_task,
        evaluators=[
            reward_evaluator,
            db_check_evaluator,
            write_action_evaluator,
            unexpected_writes_evaluator,
            wrong_argument_writes_evaluator,
            failure_family_evaluator,
        ],
        max_concurrency=1,
        metadata={"sprint": "S5", "commit": "51946b6", "iterazione": "round3-sonda"},
    )
    if TASK_IDS_FILTER is not None:
        result = lf.run_experiment(data=items, **run_kwargs)
    else:
        result = dataset.run_experiment(**run_kwargs)
    print(result.format())


if __name__ == "__main__":
    main()
