"""
Metriche per-azione, calcolate dai `results.json` locali - costo zero, nessuna
chiamata a un LLM, nessun consumo di quota.

PERCHE' ESISTE
--------------
Il reward di tau2-bench e' binario: 1.0 solo se il DB finale coincide con quello
atteso E tutte le informazioni richieste sono state comunicate; 0.0 in ogni altro
caso. Un agente che esegue due cancellazioni su tre e uno che non ne esegue
nessuna prendono lo stesso identico voto.

Nel round2 di S5 questo ha nascosto quasi tutto il segnale: il reward diceva
"1 task recuperato su 7", ma al livello delle azioni tre task su sei erano
migliorati molto (44: da 0 a 3 upgrade corretti; 39: da 0 a 2 cancellazioni su 3;
23: dal trasferire tutto al trovare la strada alternativa) e uno era *peggiorato*
(18: DB da 1.0 a 0.0). Con il solo reward non si distingue una regola che non
morde da una che morde nella direzione sbagliata - e sono due problemi che si
correggono in modo opposto.

COSA MISURA
-----------
- `action_score`      : frazione delle azioni del ground truth che l'agente ha
                        eseguito. Include le letture (get_*, search_*), quindi
                        e' generoso: serve come indicatore grossolano di quanto
                        della traiettoria attesa e' stato percorso.
- `write_action_score`: come sopra, ma solo sulle azioni che *modificano* il
                        database (book/cancel/update/send). E' la metrica che
                        conta davvero: il DB check dipende solo da queste.
- `spurious_writes`   : scritture che l'agente ha eseguito e che il ground truth
                        NON riconosce. Misura l'eccesso, non il difetto. Serve
                        perche' `write_action_score` puo' valere 1.0 mentre il
                        DB check fallisce.
- `unexpected_writes` : sottoinsieme delle precedenti in cui anche l'*oggetto*
                        e' inatteso (una prenotazione che il ground truth non
                        tocca mai), non solo gli argomenti. E' la sovra-esecuzione
                        vera: il caso del task 44, dove i tre upgrade attesi erano
                        tutti corretti ma l'agente aveva cancellato in piu' una
                        prenotazione che il ground truth vieta esplicitamente.
                        Senza questa distinzione una scrittura giusta con il
                        metodo di pagamento sbagliato (task 18, 33) verrebbe
                        contata come sovra-esecuzione, che e' il problema opposto
                        e si corregge in modo opposto.

Insieme, le tre metriche separano tre fallimenti che il reward confonde:
sotto-esecuzione (`write_action_score` < 1), sovra-esecuzione
(`unexpected_writes` > 0) e argomento sbagliato in un'azione altrimenti giusta
(`spurious_writes` > `unexpected_writes`).

MATCHING
--------
Nessun criterio inventato: si riusa `Action.compare_with_tool_call()`, lo stesso
metodo che `ActionEvaluator` usa per produrre `action_checks`. Una scrittura
dell'agente e' "spuria" se nessuna azione del ground truth le corrisponde secondo
quel confronto. La classificazione read/write viene da `get_tool_types()` sul
toolkit del dominio, non da una lista scritta a mano.

USO
---
    PYTHONIOENCODING=utf-8 PYTHONUTF8=1 .venv/Scripts/python.exe \
        ../scripts/action_metrics.py [--domain airline] [glob...]

lanciato da dentro `tau2-bench/`. Senza argomenti analizza tutti i
`data/simulations/*/results.json` e stampa una riga per simulazione.

Le stesse funzioni sono importate da `run_s5_round2_experiment.py`, che le
pubblica come score su Langfuse accanto a `reward` e `db_check`.
"""

import argparse
import glob
import json
import os
import sys
from pathlib import Path

TAU2_ROOT = Path(__file__).parent.parent / "tau2-bench"
if str(TAU2_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(TAU2_ROOT / "src"))

from tau2.data_model.tasks import Action  # noqa: E402
from tau2.environment.toolkit import ToolType, get_tool_types  # noqa: E402
from tau2.registry import registry  # noqa: E402

_TOOL_TYPES_CACHE: dict[str, dict[str, str]] = {}


def get_domain_tool_types(domain: str) -> dict[str, str]:
    """Mappa nome tool -> "read"/"write"/... per un dominio, dal toolkit reale.

    Stessa procedura di `evaluator.py:156-168`. In cache: costruire l'ambiente
    carica il db, e ci serve una volta sola per dominio.
    """
    if domain in _TOOL_TYPES_CACHE:
        return _TOOL_TYPES_CACHE[domain]
    types: dict[str, str] = {}
    env = registry.get_env_constructor(domain)()
    for toolkit in (env.tools, env.user_tools):
        if toolkit is not None:
            for name, tt in get_tool_types(toolkit).items():
                types[name] = tt.value if isinstance(tt, ToolType) else str(tt)
    _TOOL_TYPES_CACHE[domain] = types
    return types


def _agent_tool_calls(messages: list[dict]) -> list[dict]:
    """Le tool call fatte dall'agente. Esclude quelle dell'utente simulato:
    il ground truth valuta l'agente, e in airline l'utente non ha tool di
    scrittura, ma la distinzione va fatta comunque per non contarle altrove."""
    calls = []
    for m in messages or []:
        if m.get("role") != "assistant":
            continue
        for tc in m.get("tool_calls") or []:
            calls.append(tc)
    return calls


def compute_action_metrics(
    simulation: dict, golden_actions: list[dict], tool_types: dict[str, str]
) -> dict:
    """Calcola le tre metriche per una singola simulazione.

    `simulation` e `golden_actions` sono i dizionari grezzi letti dal JSON
    (results.json e le `evaluation_criteria.actions` del task), non oggetti
    pydantic: cosi' la funzione resta usabile anche solo con i file salvati.
    """
    actions = [Action(**a) for a in golden_actions]
    checks = (simulation.get("reward_info") or {}).get("action_checks") or []
    # `action_checks` e' gia' allineato posizionalmente a `golden_actions`
    # (evaluator_action.py:_check_actions itera sulle golden in ordine), quindi
    # se c'e' lo si riusa invece di rifare il match.
    if len(checks) == len(actions):
        matches = [bool(c.get("action_match")) for c in checks]
    else:
        matches = []
        calls = _agent_tool_calls(simulation.get("messages") or [])
        for a in actions:
            matches.append(any(_matches(a, tc) for tc in calls))

    is_write = [tool_types.get(a.name) == "write" for a in actions]

    n_all = len(actions)
    n_write = sum(is_write)
    action_score = (sum(matches) / n_all) if n_all else None
    write_action_score = (
        sum(m for m, w in zip(matches, is_write) if w) / n_write if n_write else None
    )

    # Scritture in eccesso: chiamate write dell'agente che nessuna azione attesa
    # riconosce. Le azioni attese qui sono TUTTE, non solo le write, perche' il
    # confronto e' per nome+argomenti e non c'e' rischio di falsi accoppiamenti.
    #
    # Vanno distinti due casi che il solo conteggio confonderebbe, ed e' proprio
    # la distinzione che serve per capire se una regola non morde o morde troppo:
    #   - stesso oggetto, argomenti sbagliati -> l'agente ha fatto la cosa
    #     giusta sulla prenotazione giusta, sbagliando un parametro (tipico:
    #     il metodo di pagamento). Non e' sovra-esecuzione.
    #   - oggetto che il ground truth non tocca mai -> azione davvero in piu'.
    #     Questa e' sovra-esecuzione, e conta separatamente.
    # Solo le SCRITTURE attese: che il ground truth *legga* una prenotazione non
    # autorizza a modificarla. Nel task 44 `S61CZX` compare tra le letture attese
    # e la nl_assertion dice esplicitamente di non cancellarla - includendo le
    # letture qui, la cancellazione di troppo passerebbe inosservata.
    gt_targets = {
        _target(a.name, a.arguments) for a, w in zip(actions, is_write) if w
    }
    spurious = []
    for tc in _agent_tool_calls(simulation.get("messages") or []):
        if tool_types.get(tc.get("name")) != "write":
            continue
        if any(_matches(a, tc) for a in actions):
            continue
        target = _target(tc.get("name"), tc.get("arguments") or {})
        spurious.append(
            {
                "name": tc.get("name"),
                "arguments": tc.get("arguments"),
                "new_target": target not in gt_targets,
            }
        )

    return {
        "action_score": action_score,
        "write_action_score": write_action_score,
        "n_actions": n_all,
        "n_write_actions": n_write,
        "spurious_writes": len(spurious),
        "unexpected_writes": sum(1 for s in spurious if s["new_target"]),
        "spurious_writes_detail": spurious,
    }


def _target(name: str, arguments: dict) -> tuple:
    """Identita' dell'oggetto su cui una scrittura agisce.

    `reservation_id` per gli update/cancel; per `book_reservation`, che crea una
    prenotazione nuova e quindi non ha ancora un id, si usa `user_id`. Serve solo
    a distinguere "ha agito su qualcosa che il ground truth non tocca mai" da
    "ha agito sulla cosa giusta con argomenti sbagliati", non a fare matching.
    """
    for key in ("reservation_id", "user_id"):
        if key in (arguments or {}):
            return (key, arguments[key])
    return (name, json.dumps(arguments, sort_keys=True))


def _matches(action: Action, tool_call: dict) -> bool:
    """`Action.compare_with_tool_call` su una tool call in forma di dizionario."""

    class _TC:  # shim minimale: il metodo usa solo .name e .arguments
        name = tool_call.get("name")
        arguments = tool_call.get("arguments") or {}

    return action.compare_with_tool_call(_TC())


def analyze_results_file(path: str, domain: str, tasks_by_id: dict) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    tool_types = get_domain_tool_types(domain)
    rows = []
    for sim in data.get("simulations", []):
        task_id = sim.get("task_id")
        task = tasks_by_id.get(task_id)
        if task is None:
            continue
        golden = [a.model_dump() for a in (task.evaluation_criteria.actions or [])]
        m = compute_action_metrics(sim, golden, tool_types)
        ri = sim.get("reward_info") or {}
        m.update(
            {
                "task_id": task_id,
                "reward": ri.get("reward"),
                "reward_breakdown": ri.get("reward_breakdown"),
                "dir": os.path.basename(os.path.dirname(path)),
            }
        )
        rows.append(m)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--domain", default="airline")
    parser.add_argument("--task-set", default="airline")
    parser.add_argument(
        "patterns",
        nargs="*",
        default=["data/simulations/*/results.json"],
        help="glob dei results.json da analizzare",
    )
    args = parser.parse_args()

    from tau2.runner.helpers import get_tasks

    paths = []
    for p in args.patterns:
        paths.extend(sorted(glob.glob(p)))
    if not paths:
        print("nessun results.json trovato")
        return

    tasks_by_id = {t.id: t for t in get_tasks(task_set_name=args.task_set)}

    header = (
        f"{'task':>5} {'reward':>6} {'DB':>4} {'COMM':>5} "
        f"{'act':>6} {'write':>6} {'spur':>4} {'unex':>4}  dir"
    )
    print(header)
    print("-" * len(header))
    for path in paths:
        for r in analyze_results_file(path, args.domain, tasks_by_id):
            bd = r.get("reward_breakdown") or {}

            def fmt(v):
                return "-" if v is None else f"{v:.2f}"

            print(
                f"{r['task_id']:>5} {fmt(r['reward']):>6} {fmt(bd.get('DB')):>4} "
                f"{fmt(bd.get('COMMUNICATE')):>5} {fmt(r['action_score']):>6} "
                f"{fmt(r['write_action_score']):>6} {r['spurious_writes']:>4} "
                f"{r['unexpected_writes']:>4}  "
                f"{r['dir'][:15]}"
            )


if __name__ == "__main__":
    main()
