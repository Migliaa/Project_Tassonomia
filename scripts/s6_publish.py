"""
S6 — pubblica su Langfuse i due Run del confronto, leggendo i `results.json`
prodotti dai worker. **Nessuna chiamata a un LLM: costo zero.**

Perche' separato dall'esecuzione
--------------------------------
I 100 task girano divisi in cinque processi, uno per chiave API. Se ogni processo
pubblicasse il proprio Run, nel dataset finirebbero dieci frammenti da dieci item
invece di due Run da cinquanta, e il confronto item-per-item nella pagina
Experiments — che e' il motivo per cui il dataset esiste — sarebbe illeggibile.
Quindi: i worker scrivono solo su disco, e qui si consolida.

Effetto collaterale utile: si puo' ripubblicare quante volte si vuole (per
aggiungere uno score, correggere un nome) senza rigiocare niente.

Cosa produce
------------
Due Run nel dataset `airline-50-baseline-vs-custom`, sugli stessi 50 item:
- "baseline - llm_agent" : l'agente di default di tau2-bench, senza i nostri
  cablaggi. E' il termine di paragone.
- "custom_agent - dopo S5" : il nostro agente.

Stesso motore per entrambi (gemini-3.5-flash-lite come agente e come simulatore),
stessi task, stessi score: le uniche variabili sono i cablaggi dell'agente.

Score pubblicati per ogni item: `reward`, `db_check`, `write_action_score`,
`unexpected_writes`, `wrong_argument_writes` (definiti in
`run_s5_round2_experiment.py`) piu' `failure_family`, qui in versione ristretta —
vedi il commento sotto.
"""

import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent
TAU2_ROOT = ROOT / "tau2-bench"
load_dotenv(TAU2_ROOT / ".env")

sys.path.insert(0, str(TAU2_ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from langfuse import Evaluation, get_client  # noqa: E402

import run_s5_round2_experiment as base  # noqa: E402
from s6_dataset import DATASET_NAME  # noqa: E402

TASK_IDS = [str(i) for i in range(50)]

# Etichette applicabili a QUALUNQUE agente, perche' sono proprieta' del task e non
# della traccia: in entrambi i casi il ground truth del benchmark e' incoerente, e
# nessun agente puo' soddisfarlo.
#
# Deliberatamente NON si riporta qui l'etichetta "famiglia 4" del task 23: quella
# era la diagnosi di una traccia specifica del custom_agent nel round3, non una
# proprieta' del task. Riusarla alla cieca su 100 esecuzioni nuove significherebbe
# etichettare fallimenti che non abbiamo guardato. Restano "da diagnosticare", che
# e' la verita'.
TASK_INTRINSIC_FAILURES = {
    "7": (
        "ground truth incoerente",
        "L'atteso ($1.628) somma anche prenotazioni cancellate durante la "
        "conversazione stessa, valorizzate al prezzo di prima delle modifiche. "
        "Nessun agente ci arriva con una lettura difendibile di 'other'. "
        "Vedi docs/s5-correzioni.md.",
    ),
    "39": (
        "ground truth incoerente",
        "Il ground truth chiede di cancellare MSJ4OA, che non soddisfa nessuna "
        "condizione di cancellazione della policy ed e' indistinguibile da "
        "S61CZX (task 44), che lo stesso benchmark vieta di cancellare. La "
        "description del task contraddice il proprio elenco di azioni attese.",
    ),
}


def failure_family_evaluator(*, input, output, expected_output, metadata, **kwargs):
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
    family, why = TASK_INTRINSIC_FAILURES.get(
        output.get("task_id"),
        (
            "da diagnosticare",
            "Fallimento non ancora classificato. Da leggere con le metriche "
            "per-azione prima di concludere.",
        ),
    )
    return Evaluation(
        name="failure_family", value=family, data_type="CATEGORICAL", comment=why
    )


# Etichette prodotte dal giudice per il run corrente. Popolata in `main()` prima
# di ogni Run, sullo stesso schema di `base.REUSE_EXISTING`: gli evaluator di
# Langfuse ricevono un item per volta e non sanno a quale run appartengono.
GIUDIZI: dict = {}


def judge_evaluator(*, input, output, expected_output, metadata, **kwargs):
    """Pubblica l'etichetta del giudice accanto a quella di riferimento.

    Perche' sta su Langfuse e non solo in un file: e' li' che si vede, riga per
    riga e sullo stesso item, cosa ha detto il classificatore automatico e cosa
    dice il reward. Una tabella in un report la si legge fidandosi; una colonna
    accanto agli altri score la si puo' ispezionare.
    """
    if not isinstance(output, dict):
        return []
    g = GIUDIZI.get(output.get("task_id"))
    if not g:
        return []
    prova = str(g.get("evidence") or "")[:300]
    nota = f"confidenza {g.get('confidence')} · prova citata: {prova}"
    if g.get("json_rotto"):
        nota += " · [output JSON non valido, etichetta recuperata dal testo]"
    return Evaluation(
        name="failure_family_judge",
        value=g.get("family", "?"),
        data_type="CATEGORICAL",
        comment=nota,
    )


RUNS = [
    (
        "s6",
        "llm_agent",
        "baseline - llm_agent",
        "L'agente di default di tau2-bench, senza nessuno dei nostri cablaggi: "
        "policy del dominio nel system prompt e nient'altro. E' il termine di "
        "paragone contro cui si misura il custom_agent. Motore "
        "gemini-3.5-flash-lite per agente e simulatore-utente, un'esecuzione per "
        "task (n=1: un delta di uno o due task non distingue il miglioramento "
        "dalla varianza).",
    ),
    (
        "s6",
        "custom_agent",
        "custom_agent v1 - le regole di S3 e S5",
        "Il nostro agente: system prompt in sezioni XML con riassunto della "
        "policy, limite di turni e gestione degli errori dei tool (S3), piu' le "
        "regole comportamentali nate dalla tassonomia dei fallimenti di S4 e "
        "corrette in S5 (docs/s5-correzioni.md). Stesso motore, stessi task e "
        "stesso n=1 del baseline: l'unica variabile sono i cablaggi.",
    ),
    (
        "s7",
        "custom_agent",
        "custom_agent v2 - pagamento e trasferimento",
        "La v1 con due sole clausole riscritte, entrambe sostituzioni e nessuna "
        "aggiunta. (1) Quando il cliente non indica un metodo di pagamento, "
        "l'agente propone quello con cui la prenotazione e' stata pagata invece "
        "di elencare il profilo e chiedere: chiedere portava il cliente fuori "
        "dalla sua stessa intenzione. (2) Il trasferimento a un umano passa da "
        "condizione a sequenza: prima si dichiara l'ostacolo e si aspetta la "
        "risposta, poi eventualmente si trasferisce. Stesso motore, stessi task, "
        "stesso n=1: l'unica variabile rispetto alla v1 sono queste due clausole.",
    ),
    (
        "s8",
        "custom_agent",
        "custom_agent v3 - solo trasferimento",
        "La v1 con la sola clausola del trasferimento riscritta, senza quella sul "
        "pagamento: doveva isolare la modifica che nella v2 sembrava aver "
        "funzionato. Ha invece falsificato l'attribuzione. Nella v3 i task 24 e 32 "
        "tornano a trasferire a un umano, pur essendo questa la versione che "
        "contiene la clausola sul trasferimento, mentre nella v2 - stessa clausola "
        "- non trasferivano. La differenza fra le due e' la clausola sui pagamenti, "
        "che col trasferimento non c'entra: quindi il comportamento non e' "
        "attribuibile alla clausola, ma alla perturbazione del prompt nel suo "
        "insieme. Con un'esecuzione per task le singole modifiche non sono "
        "separabili dal rumore.",
    ),
    (
        "s10",
        "custom_agent",
        "custom_agent v4 - ristrutturazione, non un'altra clausola",
        "Non una sostituzione di clausola come v2/v3: una ristrutturazione, "
        "motivata dalla scoperta che v1 impila ~21 vincoli nostri sopra i ~40 "
        "della policy del dominio, ben oltre la soglia (15-20) a cui i modelli "
        "senza reasoning nativo iniziano a violare regole in silenzio "
        "(Instruction Stacking Collapse, arXiv:2608.02639). Regole fuse invece "
        "che ripetute fino a 3 volte, precedenze esplicite quando due regole "
        "confliggono, ordine dei blocchi per primacy/recency, un modulo di "
        "verifica a 5 righe dentro il messaggio di conferma gia' imposto dalla "
        "policy invece di ragionamento libero, e due checkpoint leggeri (non "
        "regole a se') per far riattraversare al modello la regola pertinente "
        "prima e dopo il ragionamento su un'azione. Bozza in "
        "docs/v4-bozza-prompt.md. Stesso motore, stessi 50 task, stesso n=1 "
        "di questo primo giro: confronta con il Run 'baseline - llm_agent' "
        "sopra, non con v1/v2/v3.",
    ),
    (
        "s13",
        "custom_agent",
        "custom_agent v5 - conferma unica e disciplina di ricerca",
        "La v4 ristrutturata su tre diagnosi lette una traccia alla volta. "
        "(1) Una conferma sola per richiesta, poi tutte le azioni di fila: il "
        "modulo a 5 righe della v4 sembrava una ricevuta, e il cliente chiudeva "
        "la conversazione dopo aver detto si', lasciando l'azione mai eseguita "
        "(COMMUNICATE 1.0, DB 0.0). (2) Disciplina di ricerca: quando il cliente "
        "descrive invece di nominare - 'il piu' economico', 'un posto qualsiasi "
        "della West Coast' - enumerare i candidati e scegliere per confronto "
        "invece di fermarsi al primo valido. (3) Lo slot 'Allowed because' "
        "riscritto come verifica che puo' fallire, con un esempio di rifiuto. "
        "Stesso motore, stessi 50 task, n=1: il termine di paragone e' il Run "
        "'baseline - llm_agent'.",
    ),
    # v6: due trial dello STESSO agente. Servono a due cose diverse - il primo
    # dice se le due righe aggiunte valgono qualcosa, il secondo misura quanta
    # parte delle differenze fra le nostre versioni era varianza (con lo stesso
    # agente girato due volte avevamo gia' visto cambiare esito a 8 task su 36).
    (
        "s15",
        "custom_agent",
        "custom_agent v6 - trial 1",
        "La v5 piu' due righe, entrambe nate da fallimenti letti nel trial 1 "
        "della v5. (1) 'Un diritto non e' un'istruzione': l'agente emetteva un "
        "certificato mai chiesto (task 2) e aggiungeva bagagli a un cliente che "
        "diceva di non averne (task 8), giustificandoli con il diritto ad "
        "averli. Rimosso anche l'esempio sul bagaglio gratuito nel prompt, che "
        "innescava il secondo. (2) Il messaggio di conferma si apre dichiarando "
        "che nulla e' stato ancora fatto: la conferma unica della v5 "
        "concentrava tutto il rischio in un istante, e se il cliente chiudeva "
        "li' non veniva eseguita nessuna azione invece che solo l'ultima. "
        "Stesso motore e stessi 50 task: confronta con 'baseline - llm_agent'.",
    ),
    (
        "s16",
        "custom_agent",
        "custom_agent v6 - trial 2",
        "Seconda esecuzione della v6, identica alla prima in tutto: stesso "
        "prompt, stesso motore, stessi task. Non serve a migliorare il "
        "punteggio ma a misurarne la varianza - insieme al trial 1 da' il "
        "pass^2, cioe' la probabilita' che lo stesso task riesca DUE volte su "
        "due. E' la misura che manca al progetto: i confronti a n=1 fra le "
        "nostre versioni sono sempre stati dentro il rumore.",
    ),
]

# Etichetta di sprint per i metadata del Run, per prefisso. "s6" copre sia il
# baseline sia v1 (girati insieme nello stesso batch di 100).
SPRINT_PER_PREFISSO = {
    "s6": "S6",
    "s7": "S7",
    "s8": "S7",
    "s9": "S6-ripetizione",
    "s10": "S8-v4",
    "s13": "S8-v5",
    "s15": "S9-v6",
    "s16": "S9-v6",
}


def main() -> None:
    lf = get_client()
    dataset = lf.get_dataset(DATASET_NAME)
    items = list(dataset.items)
    print(f"dataset '{DATASET_NAME}': {len(items)} item")

    # Filtro da riga di comando: o il solo prefisso ("s6"), o prefisso e agente
    # ("s6:custom_agent") quando su uno stesso prefisso convivono due agenti.
    wanted = set(sys.argv[1:]) or None
    for prefix, agent, run_name, description in RUNS:
        if wanted and prefix not in wanted and f"{prefix}:{agent}" not in wanted:
            continue
        mapping, missing = {}, []
        for task_id in TASK_IDS:
            d = f"{prefix}_{agent}_t{task_id}"
            if (TAU2_ROOT / "data" / "simulations" / d / "results.json").exists():
                mapping[task_id] = d
            else:
                missing.append(task_id)
        if missing:
            print(f"[{run_name}] ATTENZIONE: mancano i results.json di {missing}")

        global GIUDIZI
        percorso = ROOT / "docs" / "giudice" / "esito-tutto.json"
        GIUDIZI = {}
        if percorso.exists() and prefix == "s6" and agent == "custom_agent":
            grezzo = json.loads(percorso.read_text(encoding="utf-8"))
            GIUDIZI = {k.split("/")[1]: v for k, v in grezzo.items()}
            print(f"[{run_name}] etichette del giudice caricate: {len(GIUDIZI)}")

        # Serve tutto dalla cache locale: my_task non fa nessuna chiamata LLM.
        base.REUSE_EXISTING = mapping

        result = lf.run_experiment(
            name=run_name,
            # Senza `run_name` l'SDK accoda al nome un timestamp ISO completo
            # ("... - 2026-09-05T00:05:20.746417Z"): nella pagina di confronto fra
            # Run i nomi diventano illeggibili, ed e' proprio la schermata che
            # serve al report. Passandolo esplicitamente il nome resta quello.
            run_name=run_name,
            description=description,
            data=items,
            task=base.my_task,
            evaluators=[
                base.reward_evaluator,
                base.db_check_evaluator,
                base.write_action_evaluator,
                base.unexpected_writes_evaluator,
                base.wrong_argument_writes_evaluator,
                failure_family_evaluator,
                judge_evaluator,
            ],
            max_concurrency=1,
            metadata={
                "sprint": SPRINT_PER_PREFISSO.get(prefix, prefix),
                "agent": agent,
                "modello": "gemini/gemini-3.5-flash-lite",
                "esecuzioni_per_task": 1,
            },
        )
        print(result.format())


if __name__ == "__main__":
    main()
