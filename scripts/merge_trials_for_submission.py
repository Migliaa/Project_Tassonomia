# -*- coding: utf-8 -*-
"""Unisce i 4x50 file results.json per-task dei trial v6 (s15-s18) in un unico
Results.json per dominio, nel formato nativo atteso da `tau2 submit prepare`.

Ogni cartella data/simulations/{prefisso}_custom_agent_t{N} contiene un
Results con un solo task e una sola simulazione (retry singoli per task, dopo
le interruzioni per quota giornaliera raccontate in DIARIO.md). Qui si
concatenano tasks/simulations dei 50 task per ognuno dei 4 trial in un solo
file (`tau2 submit prepare` rifiuta piu' file per lo stesso dominio: "Domain
airline appears multiple times").

I 200 run coprono piu' commit del repository a monte (il clone locale
veniva aggiornato fra un retry e l'altro): agent_info/user_info/
environment_info sono verificati identici su tutti e 200, `info.git_commit`
no. Quel campo e' obbligatorio e vale per l'intero file, quindi si sceglie
il commit piu' frequente (pluralita', non maggioranza assoluta) e la
distribuzione completa va dichiarata nella submission — vedi DIARIO.md,
voce "2026-09-09 - Due correzioni prima della submission".

Uso, dalla radice del repo:
    PYTHONIOENCODING=utf-8 PYTHONUTF8=1 tau2-bench/.venv/Scripts/python.exe \
        scripts/merge_trials_for_submission.py
"""
import collections
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
TAU2_ROOT = ROOT / "tau2-bench"
sys.path.insert(0, str(TAU2_ROOT / "src"))

from tau2.data_model.simulation import Results  # noqa: E402

OUT_DIR = TAU2_ROOT / "data" / "submission_merged"
OUT_DIR.mkdir(parents=True, exist_ok=True)

all_tasks_by_id: dict[str, object] = {}
all_sims = []
all_infos = []

for trial_idx, prefix in enumerate(["s15", "s16", "s17", "s18"]):
    task_dirs = sorted(
        (TAU2_ROOT / "data" / "simulations").glob(f"{prefix}_custom_agent_t*"),
        key=lambda p: int(p.name.rsplit("_t", 1)[1]),
    )
    if len(task_dirs) != 50:
        raise SystemExit(f"{prefix}: attese 50 cartelle, trovate {len(task_dirs)}")

    seen_here = set()
    for d in task_dirs:
        r = Results.load(d / "results.json")
        if len(r.tasks) != 1 or len(r.simulations) != 1:
            raise SystemExit(f"{d}: attesi 1 task e 1 simulazione, trovati "
                              f"{len(r.tasks)} e {len(r.simulations)}")
        task = r.tasks[0]
        sim = r.simulations[0]
        sim.trial = trial_idx
        all_tasks_by_id.setdefault(task.id, task)
        all_sims.append(sim)
        all_infos.append(r.info)
        seen_here.add(task.id)

    if len(seen_here) != 50:
        raise SystemExit(f"{prefix}: task_id duplicati o mancanti: {sorted(seen_here)}")

if len(all_tasks_by_id) != 50:
    raise SystemExit(f"task_id non coerenti fra trial: {sorted(all_tasks_by_id)}")
if len(all_sims) != 200:
    raise SystemExit(f"attese 200 simulazioni, trovate {len(all_sims)}")

commit_counts = collections.Counter(info.git_commit for info in all_infos)
plurality_commit, plurality_n = commit_counts.most_common(1)[0]
print("distribuzione commit sui 200 run:", dict(commit_counts))
print(f"-> git_commit dichiarato: {plurality_commit} ({plurality_n}/200, pluralita' non maggioranza)")

base_info = all_infos[0].model_copy(update={"git_commit": plurality_commit, "num_trials": 4})
merged = Results(info=base_info, tasks=list(all_tasks_by_id.values()), simulations=all_sims)
out_path = OUT_DIR / "airline_results.json"
merged.save(out_path, format="json")
print(f"airline: {len(all_tasks_by_id)} task x 4 trial = {len(all_sims)} simulazioni -> {out_path}")
