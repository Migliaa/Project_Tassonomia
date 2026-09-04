"""
Costruisce il materiale per l'etichettatura umana del giudice.

Produce due file:
- `docs/giudice/da-etichettare.md` — le tracce ridotte, con id anonimi, da dare
  all'annotatore umano.
- `docs/giudice/mappa-privata.json` — la corrispondenza id anonimo -> traccia
  reale. **Non va aperto prima di aver etichettato.**

Due scelte di disegno, entrambe pensate per non gonfiare il risultato
-------------------------------------------------------------------
**Gli id sono anonimi e le voci mescolate.** Durante la diagnosi ho dichiarato in
chat la causa di quattordici task: su quelli l'annotatore conoscerebbe gia' la
mia risposta, la sua etichetta non sarebbe indipendente e l'accordo misurato
sarebbe gonfiato. Nel set di misura entrano percio' solo tracce di cui non ho mai
detto niente. Il resto resta disponibile come set di sviluppo, dove si itera sul
prompt del giudice usando le mie etichette: li' l'indipendenza non serve, perche'
non e' una misura.

**La vista e' ridotta, ed e' la stessa che ricevera' il giudice.** Se l'umano
leggesse il dialogo intero e il giudice un estratto, il disaccordo misurato non
sarebbe fra due giudizi ma fra due livelli di informazione, e il kappa non
direbbe piu' niente. La riduzione contiene solo fatti — mai una sintesi
interpretata — perche' riassumere il dialogo a parole mie inietterebbe la mia
diagnosi dentro l'input, che e' esattamente cio' che stiamo tenendo fuori.

Uso:
    PYTHONIOENCODING=utf-8 PYTHONUTF8=1 tau2-bench/.venv/Scripts/python.exe \
        scripts/build_judge_pack.py
"""

import json
import os
import random
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tau2-bench" / "src"))

from action_metrics import _agent_tool_calls, get_domain_tool_types  # noqa: E402

from tau2.runner.helpers import get_tasks  # noqa: E402

# Fallimenti la cui causa non e' mai stata dichiarata in chat: (prefisso, task).
MISURA_KO = [("s7", "8"), ("s8", "22"), ("s8", "34"), ("s8", "37")]
# Successi: un classificatore a cui mostri solo fallimenti sembra bravissimo
# finche' non gli dai un caso sano e lui ci trova un problema comunque.
MISURA_OK = [("s6", "5"), ("s6", "27")]

SEED = 20260903  # ordine mescolato ma riproducibile

NL = "\n"


def compact(sim: dict, task, tool_types: dict) -> str:
    """La vista ridotta di una traccia — la stessa che ricevera' il giudice."""
    msgs = sim.get("messages") or []
    out = []

    prima = next(
        (m.get("content") for m in msgs
         if m.get("role") == "user" and (m.get("content") or "").strip()),
        "",
    )
    out.append("**Cosa chiede il cliente**")
    out.append("")
    out.append("> " + (prima or "").strip().replace("\n", " "))
    out.append("")

    golden = [a for a in (task.evaluation_criteria.actions or [])
              if tool_types.get(a.name) == "write"]
    out.append("**Scritture attese dal benchmark**")
    out.append("")
    out.extend(
        [f"- `{a.name}({json.dumps(a.arguments, ensure_ascii=False)[:900]})`" for a in golden]
        or ["- nessuna"]
    )

    fatte = [c for c in _agent_tool_calls(msgs) if tool_types.get(c.get("name")) == "write"]
    out.append("")
    out.append("**Scritture eseguite dall'agente**")
    out.append("")
    out.extend(
        [f"- `{c.get('name')}({json.dumps(c.get('arguments'), ensure_ascii=False)[:900]})`"
         for c in fatte]
        or ["- nessuna"]
    )

    trasferito = any(c.get("name") == "transfer_to_human_agents" for c in _agent_tool_calls(msgs))
    out.append("")
    out.append(f"**Ha trasferito a un operatore umano**: {'si' if trasferito else 'no'}  ")
    out.append(f"**Turni totali**: {len(msgs)}")
    out.append("")

    out.append("**Come e' finita** (ultimi due turni, testuali)")
    out.append("")
    ultimi = [m for m in msgs
              if m.get("role") in ("assistant", "user") and (m.get("content") or "").strip()][-2:]
    for m in ultimi:
        chi = "AGENTE" if m.get("role") == "assistant" else "CLIENTE"
        testo = (m.get("content") or "").strip().replace("\n", " ")
        out.append(f"- **{chi}**: {testo[:600]}")

    bd = (sim.get("reward_info") or {}).get("reward_breakdown") or {}
    out.append("")
    out.append(f"**Esito**: database `{bd.get('DB')}` · comunicazione `{bd.get('COMMUNICATE')}`")
    out.append("")
    return NL.join(out)


def main() -> None:
    os.chdir(ROOT / "tau2-bench")
    tasks = {t.id: t for t in get_tasks(task_set_name="airline")}
    tool_types = get_domain_tool_types("airline")

    voci = MISURA_KO + MISURA_OK
    random.Random(SEED).shuffle(voci)

    testo = [
        "# Tracce da etichettare — set di misura",
        "",
        "Leggi `famiglie.md` **prima** di cominciare, e tienilo aperto accanto.",
        "",
        "Per ogni voce scrivi **una sola etichetta** (`F0`–`F9`) e una riga di motivazione.",
        "La motivazione serve piu' dell'etichetta: quando il giudice dissentira', e' l'unico",
        "modo per capire se ha torto lui o se la definizione della famiglia e' ambigua — e nel",
        "secondo caso si corregge la definizione, non il tuo giudizio.",
        "",
        "Le voci sono **mescolate e anonime**: non sai a quale task corrispondano, ne' quale",
        "versione dell'agente le abbia prodotte, ne' quante siano riuscite. E' voluto.",
        "",
        "Quello che leggi qui e' **esattamente** cio' che ricevera' il giudice: stessa vista,",
        "stessi fatti, nessuna sintesi interpretata. Cosi' il disaccordo misura il giudizio e",
        "non l'accesso all'informazione.",
        "",
        "> Se una traccia non ti convince, `F9`. Un'etichetta forzata sporca la misura piu' di",
        "> un'astensione.",
        "",
        "---",
        "",
    ]
    mappa = {}
    for i, (prefisso, task_id) in enumerate(voci, 1):
        anon = f"T{i:02d}"
        mappa[anon] = {"prefisso": prefisso, "task_id": task_id}
        path = f"data/simulations/{prefisso}_custom_agent_t{task_id}/results.json"
        sim = json.load(open(path, encoding="utf-8"))["simulations"][0]
        testo.append(f"## {anon}")
        testo.append("")
        testo.append(compact(sim, tasks[task_id], tool_types))
        testo.append("**Etichetta**: `___`")
        testo.append("")
        testo.append("**Perche'**: ")
        testo.append("")
        testo.append("---")
        testo.append("")

    out_dir = ROOT / "docs" / "giudice"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "da-etichettare.md").write_text(NL.join(testo), encoding="utf-8")
    (out_dir / "mappa-privata.json").write_text(
        json.dumps(mappa, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"scritte {len(voci)} voci in docs/giudice/da-etichettare.md")
    print("mappa in docs/giudice/mappa-privata.json (non aprirla prima di etichettare)")


if __name__ == "__main__":
    main()
