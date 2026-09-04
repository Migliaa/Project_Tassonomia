"""
Costruisce il materiale per l'etichettatura umana del giudice.

Produce due file:
- `docs/giudice/da-etichettare.md` — le tracce ridotte, con id anonimi, da dare
  all'annotatore umano. Nessuna indicazione della versione dell'agente, del
  numero di task o dell'esito atteso: solo il dialogo, le azioni attese, quelle
  eseguite, e il dettaglio del reward.
- `docs/giudice/mappa-privata.json` — la corrispondenza id anonimo -> traccia
  reale. **Non va aperto prima di aver etichettato**, e non va commesso finche'
  l'etichettatura non e' chiusa.

Perche' gli id sono anonimi
---------------------------
Durante la diagnosi ho discusso in chat la causa di quattordici task. Su quelli
l'annotatore conosce gia' la mia risposta, quindi la sua etichetta non sarebbe
indipendente e l'accordo misurato sarebbe gonfiato. Il pacco separa percio' due
insiemi:

- **misura**: solo tracce di cui non ho mai dichiarato la causa. E' l'unico
  insieme su cui il kappa significa qualcosa.
- **sviluppo**: il resto, dove si itera sul prompt del giudice usando le mie
  etichette. Li' l'indipendenza non serve, perche' non e' una misura.

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

from tau2.data_model.tasks import Action  # noqa: E402
from tau2.runner.helpers import get_tasks  # noqa: E402

# Fallimenti la cui causa non e' mai stata dichiarata in chat: (prefisso, task).
MISURA_KO = [("s7", "8"), ("s7", "42"), ("s8", "22"), ("s8", "34"), ("s8", "37"), ("s8", "42")]
# Successi, per dare al giudice la possibilita' di sbagliare in eccesso.
MISURA_OK = [("s6", "2"), ("s6", "5"), ("s6", "13"), ("s6", "27"), ("s6", "43"), ("s6", "47")]

SEED = 20260903  # ordine mescolato ma riproducibile


def compact(sim: dict, task, tool_types: dict) -> str:
    out = []
    out.append("**Dialogo**\n")
    for m in sim.get("messages") or []:
        role = m.get("role")
        content = (m.get("content") or "").strip().replace("\n", " ")
        if role == "tool":
            out.append(f"- *(risposta dello strumento)* {content[:120]}…")
            continue
        etichetta = {"assistant": "AGENTE", "user": "CLIENTE"}.get(role, role)
        if content:
            out.append(f"- **{etichetta}**: {content[:700]}")
        for tc in m.get("tool_calls") or []:
            args = json.dumps(tc.get("arguments"), ensure_ascii=False)
            out.append(f"- **{etichetta} → CHIAMA** `{tc.get('name')}({args[:220]})`")

    golden = task.evaluation_criteria.actions or []
    out.append("\n**Azioni che il benchmark si aspetta** (solo quelle che scrivono nel database)\n")
    scritture_attese = [a for a in golden if tool_types.get(a.name) == "write"]
    if not scritture_attese:
        out.append("- nessuna")
    for a in scritture_attese:
        out.append(f"- `{a.name}({json.dumps(a.arguments, ensure_ascii=False)[:260]})`")

    out.append("\n**Azioni che l'agente ha eseguito** (idem)\n")
    fatte = [c for c in _agent_tool_calls(sim.get("messages") or [])
             if tool_types.get(c.get("name")) == "write"]
    if not fatte:
        out.append("- nessuna")
    for c in fatte:
        args = json.dumps(c.get("arguments"), ensure_ascii=False)
        out.append(f"- `{c.get('name')}({args[:260]})`")

    ri = sim.get("reward_info") or {}
    bd = ri.get("reward_breakdown") or {}
    out.append(
        f"\n**Esito della misura**: database `{bd.get('DB')}` · "
        f"comunicazione `{bd.get('COMMUNICATE')}`\n"
    )
    return "\n".join(out)


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
        "Per ogni voce scrivi **una sola etichetta** (`F0`–`F9`) nella riga *Etichetta*, e una riga",
        "di motivazione. La motivazione serve piu' dell'etichetta: quando piu' avanti il giudice",
        "dissentira', e' l'unico modo per capire se ha torto lui o se la definizione della famiglia",
        "e' ambigua.",
        "",
        "Le voci sono **mescolate e anonime**: non sai a quale task corrispondono, ne' quale",
        "versione dell'agente le ha prodotte, ne' quante sono riuscite. E' voluto.",
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
        testo.append("**Perché**: ")
        testo.append("")
        testo.append("---")
        testo.append("")

    out_dir = ROOT / "docs" / "giudice"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "da-etichettare.md").write_text("\n".join(testo), encoding="utf-8")
    (out_dir / "mappa-privata.json").write_text(
        json.dumps(mappa, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"scritte {len(voci)} voci in docs/giudice/da-etichettare.md")
    print("mappa in docs/giudice/mappa-privata.json (non aprirla prima di etichettare)")


if __name__ == "__main__":
    main()
