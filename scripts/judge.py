"""
Il giudice: classifica la famiglia di fallimento di una traccia, e si misura.

Cosa fa
-------
Legge una traccia dai `results.json` locali, ne costruisce la **vista ridotta**
(la stessa, identica, che ha ricevuto l'annotatore: vedi `build_judge_pack.py`) e
chiede a un modello di assegnarle una famiglia fra quelle definite in
`docs/giudice/famiglie.md`. Poi confronta le sue risposte con le etichette di
riferimento e stampa kappa di Cohen e matrice di confusione.

Tre scelte di disegno, e il perche'
-----------------------------------
**Il giudice deve citare.** Oltre all'etichetta gli si chiede il turno esatto che
la giustifica. Un classificatore obbligato a produrre la prova diventa
verificabile a colpo d'occhio e confabula molto meno; e quando sbaglia si vede
*su cosa* ha guardato.

**Il modello e' quello piccolo.** Il giudice gira su `gemini-3.5-flash-lite`,
mentre le etichette di riferimento vengono da un modello di frontiera. Non e'
validazione umana - e' dichiarato - ma misura una cosa che in produzione serve
davvero: *un modello economico riproduce la diagnosi di uno costoso?* E' la
domanda che ci si pone prima di mettere un classificatore su decine di migliaia
di tracce.

**Il prompt e' in inglese** anche se il progetto e' in italiano: le tracce sono
in inglese e il modello e' piccolo. Far cambiare lingua a un modello da poco tra
istruzioni e dati aggiunge un modo di sbagliare che non stiamo studiando.

Insiemi
-------
- `SVILUPPO`: tracce di cui ho gia' dichiarato la diagnosi in chat. Qui si itera
  sul prompt. Non e' una misura, quindi l'indipendenza non serve.
- `MISURA`: le sei voci di `etichette-riferimento.md`, con etichette congelate
  prima che questo file esistesse. **Si tocca una volta sola.**

Uso:
    ... judge.py --set sviluppo        # itera qui
    ... judge.py --set misura          # una volta sola
    ... judge.py --set misura --ripeti 2   # controllo di auto-coerenza
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tau2-bench" / "src"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / "tau2-bench" / ".env")

from build_judge_pack import compact  # noqa: E402

from action_metrics import get_domain_tool_types  # noqa: E402
from tau2.runner.helpers import get_tasks  # noqa: E402

MODELLO = "gemini/gemini-3.5-flash-lite"

# Insieme di sviluppo: la diagnosi l'ho gia' dichiarata in chat, quindi queste
# etichette non sono indipendenti. Vanno bene per iterare, non per misurare.
SVILUPPO = {
    ("s6", "7"): "F7", ("s6", "11"): "F1", ("s6", "14"): "F4", ("s6", "23"): "F4",
    ("s6", "24"): "F2", ("s6", "25"): "F1", ("s6", "29"): "F8", ("s6", "32"): "F2",
    ("s6", "33"): "F3", ("s6", "35"): "F5", ("s6", "39"): "F7",
}

# Insieme di misura: etichette congelate in docs/giudice/etichette-riferimento.md
# prima che questo script esistesse. Gli id anonimi vengono da mappa-privata.json.
MISURA = {
    ("s6", "5"): "F0", ("s6", "27"): "F0", ("s7", "8"): "F3",
    ("s8", "22"): "F6", ("s8", "34"): "F10", ("s8", "37"): "F2",
}

ISTRUZIONI = """You are classifying why a customer-service agent failed a benchmark task.

You will see a reduced view of one conversation: what the customer asked, the database
writes the benchmark expected, the writes the agent actually made, whether it transferred
to a human, the last two turns, and the final scores.

Assign EXACTLY ONE family from this list.

F0  No failure. The task succeeded: expected writes were performed and required
    information communicated. Both scores are 1.0.
F1  Confirmation trap. The agent asked for the explicit confirmation the policy requires;
    the customer approved AND ended the conversation in the same message, so the agent
    never got another turn and the write was never executed.
F2  Premature transfer. The agent transferred to a human while something it could still
    serve was left open: an unserved request, or an alternative it never proposed.
    NOTE: transferring is often CORRECT. It is only a failure if a servable part was left.
F3  Wrong argument. The right action on the right object, but with a wrong parameter -
    typically the payment method. The call succeeded; the resulting database differs.
F4  Unrecognised equivalence. The writes performed are substantially equivalent to those
    expected - same effects, same amounts - but differ in order or in form, and the
    database comparison, which is a hash, does not match. Not an agent error.
F5  Wrong selection. The agent acted on the wrong object: a different flight, a different
    reservation. Right operation, wrong target.
F6  Partial execution. The agent performed some of the expected writes and stopped, with
    nothing preventing it from continuing.
F7  Incoherent ground truth. The task is unsolvable: the expected actions contradict the
    domain policy, or the task description contradicts its own expected actions.
F8  Simulator exit. The simulated user ended the conversation for its own reason
    (###OUT-OF-SCOPE###, ###TRANSFER###), cutting off a path that was progressing.
F10 Undue execution. The agent performed a write the benchmark does not expect AT ALL:
    the task required refusing, or not touching that reservation, and the agent acted.
    Distinct from F3: there the action was due and a parameter was wrong; here the action
    should not have happened.
F9  Undeterminable. Not enough in the trace to decide, or the mechanism fits none of the
    above. Use it without hesitation: a forced label is worse than an abstention.

WHAT THIS VIEW CANNOT SHOW YOU. The view does not include the task description or the
domain policy. F7 can therefore almost never be established from it: do not choose F7
unless the contradiction is visible inside the view itself. When the failure looks like it
needs information you were not given, answer F9.

RULE FOR AMBIGUOUS CASES. Choose the PROXIMATE CAUSE of the database mismatch: the first
thing that went wrong, without which the final database would have matched. If several
families seem to apply, pick the one furthest UPSTREAM in the conversation.

Answer with JSON only, no other text:
{"family": "F<n>", "evidence": "<the exact sentence or tool call from the view that
justifies your choice, copied verbatim>", "confidence": "high"|"medium"|"low"}
"""


def chiedi(vista: str) -> dict:
    from litellm import completion

    r = completion(
        model=MODELLO,
        messages=[
            {"role": "system", "content": ISTRUZIONI},
            {"role": "user", "content": vista},
        ],
        temperature=0.0,
    )
    testo = (r.choices[0].message.content or "").strip()
    costo = getattr(r, "_hidden_params", {}).get("response_cost") or 0.0
    if testo.startswith("```"):
        testo = testo.split("```")[1]
        testo = testo[4:] if testo.startswith("json") else testo
    try:
        d = json.loads(testo)
    except json.JSONDecodeError:
        # Lettura indulgente. Chiedere una citazione *alla lettera* e chiedere JSON
        # sono due istruzioni giuste che collidono: la citazione contiene virgolette,
        # e il JSON si rompe. Succede su una traccia su undici. La correzione non e'
        # rinunciare alla citazione - che e' cio' che rende il giudice verificabile -
        # ma non far dipendere l'ETICHETTA dalla citazione: l'etichetta e' il dato,
        # la prova e' un ausilio. Si estrae la prima con una regex e si tiene il
        # resto come testo grezzo.
        m = re.search(r'"family"\s*:\s*"(F\d+)"', testo)
        d = {
            "family": m.group(1) if m else "PARSE_ERROR",
            "evidence": testo[:300],
            "confidence": "low",
            "json_rotto": True,
        }
    d["costo"] = costo
    return d


def kappa_cohen(a: list, b: list) -> float:
    """Kappa di Cohen: accordo osservato, scontato di quello atteso per caso.

    Serve al posto dell'accuratezza perche' con classi sbilanciate un
    classificatore degenere - che risponde sempre la famiglia piu' comune -
    ottiene una percentuale alta ed e' inutile. Kappa 0 = come tirare i dadi.
    """
    n = len(a)
    if n == 0:
        return float("nan")
    osservato = sum(1 for x, y in zip(a, b) if x == y) / n
    ca, cb = Counter(a), Counter(b)
    atteso = sum((ca[k] / n) * (cb[k] / n) for k in set(a) | set(b))
    if atteso >= 1.0:
        return float("nan")
    return (osservato - atteso) / (1 - atteso)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--set", dest="insieme",
                   choices=["sviluppo", "misura", "tutto"], required=True)
    p.add_argument("--prefisso", default="s6", help="con --set tutto: quale run")
    p.add_argument("--agente", default="custom_agent", help="con --set tutto")
    p.add_argument("--ripeti", type=int, default=1, help="giri, per l'auto-coerenza")
    args = p.parse_args()

    if args.insieme == "tutto":
        # Etichetta l'intero run, per avere su Langfuse una colonna piena: e' il
        # senso di S5b, automatizzare il lavoro diagnostico fatto a mano. Le voci
        # dell'insieme di MISURA vengono saltate di proposito: quello si esegue
        # una volta sola e deliberatamente, non come effetto collaterale.
        import glob as _glob
        riferimento = {}
        for d in sorted(_glob.glob(
                f"{ROOT}/tau2-bench/data/simulations/{args.prefisso}_{args.agente}_t*")):
            t = d.split("_t")[-1]
            if (args.prefisso, t) in MISURA:
                continue
            riferimento[(args.prefisso, t)] = SVILUPPO.get((args.prefisso, t), "(nessuna)")
    else:
        riferimento = SVILUPPO if args.insieme == "sviluppo" else MISURA
    os.chdir(ROOT / "tau2-bench")
    tasks = {t.id: t for t in get_tasks(task_set_name="airline")}
    tool_types = get_domain_tool_types("airline")

    giri, costo = [], 0.0
    for giro in range(args.ripeti):
        risposte = {}
        for (prefisso, task_id), atteso in riferimento.items():
            agente = args.agente if args.insieme == "tutto" else "custom_agent"
            path = f"data/simulations/{prefisso}_{agente}_t{task_id}/results.json"
            if prefisso == "s6" and not os.path.exists(path):
                path = f"data/simulations/s6_custom_agent_t{task_id}/results.json"
            sim = json.load(open(path, encoding="utf-8"))["simulations"][0]
            vista = compact(sim, tasks[task_id], tool_types)
            r = chiedi(vista)
            costo += r.pop("costo", 0.0)
            risposte[(prefisso, task_id)] = r
            marchio = "ok " if r["family"] == atteso else "NO "
            if giro == 0:
                print(f"  [{marchio}] {prefisso}/{task_id}: giudice={r['family']:<4} "
                      f"riferimento={atteso:<4} ({r.get('confidence')})")
                print(f"        prova: {str(r.get('evidence'))[:150]}")
        giri.append(risposte)

    chiavi = list(riferimento)
    att = [riferimento[k] for k in chiavi]
    got = [giri[0][k]["family"] for k in chiavi]

    accordo = sum(1 for x, y in zip(att, got) if x == y)
    print(f"\ninsieme '{args.insieme}': {accordo}/{len(chiavi)} coincidono")
    print(f"kappa di Cohen: {kappa_cohen(att, got):.3f}   (0 = caso, 1 = accordo perfetto)")
    print(f"costo: ${costo:.4f}")

    print("\nmatrice di confusione (riga = riferimento, colonna = giudice):")
    fam = sorted(set(att) | set(got))
    print("        " + "".join(f"{f:>6}" for f in fam))
    for r in sorted(set(att)):
        riga = [sum(1 for x, y in zip(att, got) if x == r and y == c) for c in fam]
        print(f"  {r:>5} " + "".join(f"{v:>6}" for v in riga))

    if args.ripeti > 1:
        stabili = sum(1 for k in chiavi if len({g[k]["family"] for g in giri}) == 1)
        print(f"\nauto-coerenza su {args.ripeti} giri: {stabili}/{len(chiavi)} invariati")

    out = ROOT / "docs" / "giudice" / f"esito-{args.insieme}.json"
    out.write_text(json.dumps(
        {f"{k[0]}/{k[1]}": {"riferimento": riferimento[k], **giri[0][k]} for k in chiavi},
        indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nesito in {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
