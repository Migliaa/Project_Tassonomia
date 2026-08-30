# Langfuse in produzione — funzionalità professionali

**Data della ricerca: 2026-08-30.**

Questo documento raccoglie quello che la documentazione ufficiale di Langfuse (`langfuse.com/docs`)
dice sulle funzionalità "da produzione" della piattaforma, con un occhio specifico al progetto
`tassonomia`: SDK Python **v4** (architettura OpenTelemetry), LiteLLM come gateway agganciato via
callback `langfuse_otel`, e l'obiettivo di costruire una **tassonomia dei fallimenti** di un agente
su `tau2-bench`. Ogni affermazione ha il link alla pagina che la possiede. Dove la documentazione
non risponde, è scritto esplicitamente. Le parti dedotte sono marcate come tali.

> **Avvertenza generale sulla v4.** Buona parte del materiale su Langfuse in circolazione è
> pre-v4 e non vale più. Nella v4 il modello dati è *observations-first*: gli attributi di
> correlazione (`user_id`, `session_id`, `metadata`, `tags`) si propagano su **ogni observation**
> invece di vivere su un'entità trace separata, e il raggruppamento avviene sul trace ID nativo
> OTel
> ([upgrade path v3→v4](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v3-to-v4)).
> Ogni sezione qui sotto segnala dove la v4 diverge.

---

## Indice

1. [LLM-as-a-judge / evaluator automatici](#1-llm-as-a-judge--evaluator-automatici)
2. [Dataset ed experiment](#2-dataset-ed-experiment)
3. [Prompt management e versioning](#3-prompt-management-e-versioning)
4. [Scores — il modello completo](#4-scores--il-modello-completo)
5. [Sessions e users](#5-sessions-e-users)
6. [Dashboard, metriche aggregate, costi e token](#6-dashboard-metriche-aggregate-costi-e-token)
7. [Alerting](#7-alerting)
8. [Note specifiche per `tassonomia`](#8-note-specifiche-per-tassonomia)
9. [Cosa la documentazione non copre](#9-cosa-la-documentazione-non-copre)

---

## 1. LLM-as-a-judge / evaluator automatici

Questa è la sezione più importante per il progetto: è il meccanismo con cui si può far
classificare automaticamente ogni run di `tau2-bench` in una categoria di fallimento.

### 1.1 Il cambio architetturale che devi conoscere prima di tutto

**Gli evaluator trace-level sono deprecati.** Dal 13 febbraio 2026 Langfuse ha introdotto gli
evaluator **observation-level**, e la documentazione li indica come il target raccomandato per i
dati di produzione
([LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge),
[changelog observation-level evals](https://langfuse.com/changelog/2026-02-13-observation-level-evals)).

Tempistiche dichiarate nel changelog:

- **Langfuse Cloud**: gli evaluator trace-level esistenti continuano a funzionare fino al
  **16 novembre 2026**.
- **Self-hosted v4**: smettono di produrre risultati appena il server gira in modalità
  `events_only`.
- Prerequisito: SDK Python v3+ o JS/TS v4+ (quelli basati su OTel).

Motivazioni dichiarate: precisione (valuti solo l'operazione che conta, non l'intero workflow),
costo (filtrare riduce il volume di valutazioni) e performance — le valutazioni si completano
«in seconds, not minutes»
([changelog](https://langfuse.com/changelog/2026-02-13-observation-level-evals)).

> **Questo è il punto in cui quasi tutte le guide online sbagliano.** Se trovi un tutorial che ti
> fa creare un "evaluator sulle trace con sampling", stai leggendo materiale che scade a novembre
> 2026.

### 1.2 I pezzi mobili

La documentazione dei [concetti di evaluation](https://langfuse.com/docs/evaluation/core-concepts)
separa due oggetti che è facile confondere:

| Oggetto | Cosa definisce |
|---|---|
| **Evaluator** | *Come* si assegna un punteggio: modello giudice, prompt, tipo di score, categorie ammesse. Riutilizzabile su più rule. |
| **Evaluation rule** | *Su cosa* gira: target (observation live vs experiment), filtri, sampling rate, e il mapping dai tuoi dati alle variabili dell'evaluator. |

Un evaluator, sempre secondo la pagina dei concetti, può essere usato in tre modi: **batch** su
observation storiche già ingerite, **online** attaccato a una rule che valuta il traffico in
arrivo, e sulle run di **experiment**.

### 1.3 Configurazione passo per passo

Da [LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge):

1. **LLM connection.** Prima di tutto va configurata una connessione LLM nelle impostazioni di
   progetto: è il modello che fa da giudice.
2. **Nuovo evaluator.** Pagina *Evaluators* → "New evaluator". Si parte da un template
   precompilato oppure da zero. I template sono configurazioni prepopolate, poi personalizzabili.
3. **Modello.** O il default di progetto, o un modello dedicato a quell'evaluator.
4. **Judge prompt.** Le istruzioni di valutazione, con placeholder `{{variabile}}` — tipicamente
   `{{input}}`, `{{output}}`, `{{ground_truth}}`.
5. **Score type.** Tre opzioni:
   - *Numeric* — valori continui (es. helpfulness 0–1);
   - ***Categorical* — etichette discrete** tipo `correct`, `partially_correct`, `incorrect`;
   - *Boolean* — `true`/`false`.
6. **Variable mapping.** Ogni variabile del prompt viene mappata su una sorgente dati della
   observation: **input, output, metadata, tool calls**. Nel caso degli experiment si possono
   mappare anche `expected output` e i metadata dell'experiment.
7. **Test.** Si filtrano observation campione, se ne sceglie una, si lancia l'evaluator e si
   validano score e reasoning **prima** di metterlo in produzione.
8. **Rule.** Dopo aver salvato l'evaluator si crea la rule che decide quali observation lo
   attivano, con i filtri e l'eventuale **sampling rate**.

Nelle *Advanced settings* si possono configurare «score description and score reasoning fields to
give the model more detail about the structured output»
([stessa pagina](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)).

### 1.4 Selezione del target e filtri

I filtri sono **stackabili**: si combinano filtri sulla observation (type, name, metadata) con
filtri sulla trace (`userId`, `sessionId`, tags, version). Esempio dalla documentazione: «all LLM
generations in conversations tagged 'customer-support' for premium users»
([LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)).

Esiste un filtro **"Is Root Observation"** (`isRootObservation`, con logica booleana anche via API)
per colpire la observation radice logica invece delle operazioni intermedie dentro la trace.
Per `tassonomia` questo è probabilmente il filtro chiave: la root observation di un task
`tau2-bench` è l'unità che vuoi classificare.

### 1.5 Il risultato: uno score per observation per evaluator

Il flusso è: una observation in arrivo matcha i filtri della rule → la rule attiva gli evaluator
collegati → il modello giudice produce uno score strutturato con reasoning → lo score si attacca a
quella specifica observation, «one score per observation per evaluator»
([core concepts](https://langfuse.com/docs/evaluation/core-concepts)).

**Sì, uno score categorico è esattamente lo strumento per la tassonomia.** Il tipo *Categorical*
produce etichette discrete definite da te, e la documentazione nota che «the system allows multiple
matches when more than one category may apply» — quindi una singola trace può ricevere più
etichette di fallimento
([LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)).

Architettura conseguente, e utile: evaluator diversi possono girare **contemporaneamente su
operazioni diverse** della stessa trace. Un evaluator "tool call sbagliata" sulle observation di
tipo tool, un evaluator "policy violation" sulla generation finale.

### 1.6 Costo e sampling

Le leve di controllo costo documentate sono tre: (1) **sampling**, valutare solo una percentuale;
(2) targettizzare observation specifiche invece dell'intera trace; (3) scegliere modelli giudice
economici per valutazioni semplici
([LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge)).

### 1.7 Gestione via API

Evaluator e Evaluation Rules hanno **endpoint API stabili**, pensati per versionare in git la
configurazione degli evaluator e replicarla tra progetti
([LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge);
annuncio: [changelog API LLM-as-a-judge](https://langfuse.com/changelog/2026-04-15-llm-as-a-judge-api)).

### 1.8 Disponibilità

La pagina [pricing](https://langfuse.com/pricing) elenca «LLM-as-judge evaluators» come disponibile
su **tutti i piani** (Hobby, Core, Pro, Enterprise), senza limiti d'uso dichiarati nella tabella.
Non è quindi una feature a pagamento. *(Sulla disponibilità in self-hosting vedi §9: la pagina
overview non lo dichiara esplicitamente.)*

---

## 2. Dataset ed experiment

### 2.1 Dataset

Un dataset è una collezione curata di input e output attesi, definita come «a single source of
truth for your test data»
([datasets](https://langfuse.com/docs/evaluation/features/datasets)).

```python
langfuse.create_dataset(
    name="<dataset_name>",
    description="My first dataset",
    metadata={"author": "Alice", "date": "2022-01-01", "type": "benchmark"}
)

langfuse.create_dataset_item(
    dataset_name="<dataset_name>",
    input={"text": "hello world"},
    expected_output={"text": "hello world"},
    metadata={"model": "llama3"}
)
```

Punti rilevanti dalla stessa pagina:

- **Versioning automatico.** Ogni modifica (add, update, delete, archive) crea una nuova versione
  tracciata da timestamp. Si può recuperare uno stato storico e lanciarci un experiment sopra,
  «to ensure reproducibility»:

  ```python
  version_timestamp = datetime(2025, 12, 15, 6, 30, 0, tzinfo=timezone.utc)
  dataset_at_version = langfuse.get_dataset(name="my-dataset", version=version_timestamp)
  ```

- **Schema enforcement.** Si può definire uno JSON Schema di validazione per `input` e
  `expectedOutput`.
- **Media.** Immagini/audio/video via `LangfuseMedia`.
- **Costruzione dai dati di produzione.** Il workflow suggerito è estrarre come dataset item le
  trace di produzione andate male, farle annotare con l'expected output, e usarle come regression
  test contro versioni successive.

### 2.2 Experiment via SDK

Un experiment esegue la tua applicazione (il *task*) su ogni item del dataset e ne valuta l'output
([core concepts](https://langfuse.com/docs/evaluation/core-concepts)). Il vocabolario ufficiale è:
*Dataset* → *Dataset Item* → *Task* → *Experiment Run*.

```python
from langfuse import get_client
from langfuse.openai import OpenAI

langfuse = get_client()

def my_task(*, item, **kwargs):
    question = item.input
    response = OpenAI().chat.completions.create(
        model="gpt-4.1",
        messages=[{"role": "user", "content": question}]
    )
    return response.choices[0].message.content

dataset = langfuse.get_dataset("my-evaluation-dataset")
result = dataset.run_experiment(
    name="Production Model Test",
    description="Monthly evaluation of our production model",
    task=my_task
)
print(result.format())
```

([experiments via SDK](https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk))

> **Differenza v4.** Il vecchio pattern `item.run()` (v3 e precedenti) è sostituito da
> `dataset.run_experiment()`
> ([upgrade path v3→v4](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v3-to-v4)).
> Se leggi un tutorial con `item.run()`, è vecchio.

Gli evaluator si passano come funzioni Python — due livelli, per item e per run:

```python
from langfuse import Evaluation

def accuracy_evaluator(*, input, output, expected_output, metadata, **kwargs):
    if expected_output and expected_output.lower() in output.lower():
        return Evaluation(name="accuracy", value=1.0)
    return Evaluation(name="accuracy", value=0.0)

def average_accuracy(*, item_results, **kwargs):
    accuracies = [e.value for r in item_results for e in r.evaluations if e.name == "accuracy"]
    return Evaluation(name="avg_accuracy",
                      value=sum(accuracies) / len(accuracies) if accuracies else None)

result = dataset.run_experiment(
    name="Test",
    task=my_task,
    evaluators=[accuracy_evaluator],
    run_evaluators=[average_accuracy],
    max_concurrency=10,
    metadata={"model": "gpt-4", "version": "v1.2.0"}
)
```

Parametri di `run_experiment`: `name`, `description`, `task`, `evaluators`, `run_evaluators`,
`max_concurrency`, `metadata`
([experiments via SDK](https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk)).

### 2.3 Confronto tra run

La documentazione descrive due modalità di esecuzione — programmatica via SDK, e via UI usando
versioni di dataset e di prompt
([core concepts](https://langfuse.com/docs/evaluation/core-concepts)) — e una **compare view**
nella UI in cui si vedono input, output e score automatici affiancati, con la possibilità di
annotare a mano i risultati dell'experiment
([annotation](https://langfuse.com/docs/evaluation/evaluation-methods/annotation)).

Il regression testing di prompt e agent si fa quindi così: dataset versionato + più experiment run
con `metadata` che identifica la versione + confronto degli score aggregati nella compare view.

---

## 3. Prompt management e versioning

I prompt vivono in Langfuse invece che hardcodati nel codice. Due benefici dichiarati
([overview](https://langfuse.com/docs/prompt-management/overview)): il disaccoppiamento tra
«prompt iteration and code deployment», e il fatto che il sistema «adds no latency to your
application» perché l'SDK tiene una cache client-side.

Creazione (text e chat):

```python
from langfuse import get_client
langfuse = get_client()

langfuse.create_prompt(
    name="movie-critic",
    type="text",
    prompt="As a {{criticlevel}} movie critic, do you like {{movie}}?",
    labels=["production"]
)

langfuse.create_prompt(
    name="movie-critic-chat",
    type="chat",
    prompt=[
      {"role": "system", "content": "You are an {{criticlevel}} movie critic"},
      {"role": "user", "content": "Do you like {{movie}}?"},
    ],
    labels=["production"]
)
```

Fetch e compile a runtime:

```python
prompt = langfuse.get_prompt("movie-critic")            # di default: label "production"
compiled_prompt = prompt.compile(criticlevel="expert", movie="Dune 2")

prompt = langfuse.get_prompt(
    "movie-critic",
    label="production",       # oppure version=N
    cache_ttl_seconds=3600,
    fallback="default text"   # se il fetch fallisce
)
```

([get started](https://langfuse.com/docs/prompt-management/get-started))

**Label.** `production` è la versione scelta intenzionalmente per il live ed è il default del
fetch; `latest` è semplicemente l'ultima creata; si possono definire label custom per
staging/testing.

**Collegamento al tracing.** Il prompt si lega alla generation per poter poi analizzare le
performance per versione di prompt. La documentazione mostra:

```python
langfuse.generation(
    name="critique",
    prompt=compiled_prompt,
    langfuse_prompt=prompt,   # collega la versione del prompt alla trace
    model="gpt-4o"
)
```

> **Attenzione (dedotto, non verificato).** Lo snippet qui sopra usa `langfuse.generation(...)`,
> che è API pre-v4. Nella v4 `start_span()` / `start_generation()` sono consolidati in
> `start_observation(as_type="...")`
> ([upgrade path v3→v4](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v3-to-v4)).
> Il **concetto** del parametro `langfuse_prompt` è documentato; la **forma esatta della chiamata
> in v4** non l'ho verificata su una pagina che sia esplicitamente v4 — controllala nel
> [reference Python](https://python.reference.langfuse.com/langfuse) prima di usarla.

---

## 4. Scores — il modello completo

Lo score è «the universal data object for storing evaluation results»: ha `name`, `value` e
`dataType` ([core concepts](https://langfuse.com/docs/evaluation/core-concepts)).

### 4.1 Data type

Quattro, non tre — attenzione, la pagina LLM-as-a-judge ne elenca tre perché il giudice non emette
testo libero come score:

| Tipo | Valore |
|---|---|
| `NUMERIC` | float (accuracy, similarity, latenza normalizzata…) |
| `CATEGORICAL` | stringa da un insieme definito (`correct`, `partially correct`…) |
| `BOOLEAN` | binario (`0`/`1`) |
| `TEXT` | stringa 1–500 caratteri, per note e spiegazioni |

([scores via API/SDK](https://langfuse.com/docs/evaluation/evaluation-methods/scores-via-sdk),
[core concepts](https://langfuse.com/docs/evaluation/core-concepts))

### 4.2 Livelli di attacco

Uno score può attaccarsi a: **trace**, **observation**, **session**, **dataset run**
([core concepts](https://langfuse.com/docs/evaluation/core-concepts),
[scores via API/SDK](https://langfuse.com/docs/evaluation/evaluation-methods/scores-via-sdk)).

Nota di coerenza sulla v4: anche se il modello dati è observations-first, i **trace-level score
esistono ancora** — l'SDK v4 espone `score_trace()` / `score_current_trace()` accanto a `score()` /
`score_current_span()`. Quello che è deprecato è l'*evaluator* trace-level (§1.1), non lo *score*
trace-level.

### 4.3 Creazione

**SDK Python v4 — tre forme.**

```python
from langfuse import get_client
langfuse = get_client()

# 1. esplicita, con id noti
langfuse.create_score(
    name="correctness",
    value=0.9,
    trace_id="trace_id_here",
    observation_id="observation_id_here",   # opzionale
    data_type="NUMERIC",
    comment="Factually correct"
)

# 2. sull'oggetto span
with langfuse.start_as_current_observation(as_type="span", name="my-operation") as span:
    span.score(name="correctness", value=0.9, data_type="NUMERIC")
    span.score_trace(name="overall_quality", value=0.95, data_type="NUMERIC")

# 3. sul contesto corrente
with langfuse.start_as_current_observation(as_type="span", name="my-operation"):
    langfuse.score_current_span(name="correctness", value=0.9, data_type="NUMERIC")
    langfuse.score_current_trace(name="overall_quality", value=0.95, data_type="NUMERIC")

# session-level
langfuse.create_score(name="session_quality", value=0.85,
                      session_id="session_id_here", data_type="NUMERIC")
```

([scores via API/SDK](https://langfuse.com/docs/evaluation/evaluation-methods/scores-via-sdk))

**REST API.**

```bash
curl -X POST https://cloud.langfuse.com/api/public/scores \
  -u "pk-lf-...":"sk-lf-..." \
  -H "Content-Type: application/json" \
  -d '{"traceId":"trace_id_here","name":"accuracy",
       "value":"partially correct","dataType":"CATEGORICAL"}'
```

**Idempotenza.** Passando un `score_id`/`id` stabile si evitano duplicati: il match avviene su
`id`, `name` e timestamp a granularità giornaliera
([scores via API/SDK](https://langfuse.com/docs/evaluation/evaluation-methods/scores-via-sdk)).

**Score Config.** Un `configId` referenzia una configurazione che valida lo score contro vincoli
definiti (range numerici, opzioni categoriche ammesse). Serve a standardizzare i nomi e i valori
tra evaluator automatici e annotazione umana.

**UI / annotazione manuale.** Va creato **almeno uno Score Config prima di poter annotare dalla
UI**. Poi: aprire una Trace, Session o Observation → pulsante *Annotate* → scegliere i config da
applicare → inserire i valori → commento opzionale → i risultati compaiono nel tab *Scores*
([annotation](https://langfuse.com/docs/evaluation/evaluation-methods/annotation)).

**Annotation queue.** Workflow strutturato di review umana; utile per costruire una baseline umana
contro cui misurare gli evaluator automatici
([annotation](https://langfuse.com/docs/evaluation/evaluation-methods/annotation)).
Limiti per piano: Hobby 1 coda, Core 3, Pro/Enterprise illimitate
([pricing](https://langfuse.com/pricing)).

**Frontend.** `@langfuse/browser` per raccogliere feedback utente dal client: richiede solo la
public key e invia gli score subito via ingestion API.

### 4.4 Sintassi della filter search bar

La barra di ricerca unifica filtri, wildcard e full-text
([filter search bar](https://langfuse.com/docs/observability/features/filter-search-bar)):

```
level:ERROR type:TOOL environment:production latency:>2 name:*checkout*
```

I `field:value` sono in AND implicito.

| Costrutto | Esempio |
|---|---|
| Confronto numerico/datetime | `latency:>2`, `cost:>=0.01`, `startTime:>2026-06-01` |
| Contains / prefix / suffix | `name:*checkout*`, `name:checkout*`, `name:*checkout` |
| Match esatto | `name:=checkout` |
| Negazione | `-environment:production` |
| Any-of | `level:(ERROR OR WARNING)` |
| All-of (array) | `tags:(billing AND urgent)` |
| Metadata annidati | `metadata.region:eu` |
| Esistenza / null | `has:endTime` / `-has:endTime` |
| Full-text (id, name, input, output) | `refund failed`, `output:"refund failed"` |

**Score — dot notation:**

```
scores.accuracy:>0.8              # score numerico
scores.is_hallucination:false     # score boolean
scores.helpfulness:positive       # score categorico
scores."Answer Relevance":>=0.9   # nome con caratteri speciali → virgolette
```

La query viene serializzata nell'URL, quindi una vista filtrata è condivisibile come link — utile
per linkare "tutte le trace con `scores.failure_type:tool_misuse`" nel diario di progetto.

---

## 5. Sessions e users

### 5.1 Sessions

Le session **raggruppano più trace** e abilitano un «session replay» dell'intera interazione
([sessions](https://langfuse.com/docs/observability/features/sessions)). Il `session_id` accetta
«any US-ASCII character string less than 200 characters».

```python
from langfuse import observe, propagate_attributes

@observe()
def process_request():
    with propagate_attributes(session_id="your-session-id"):
        result = process_chat_message()
        return result
```

Nella UI: replay dell'interazione per debug, pubblicazione come link pubblico condivisibile,
bookmark, e **score a livello di session** per valutazioni human-in-the-loop.

### 5.2 Users

`userId` aggrega metriche per utente: si può segmentare per «overall token usage, number of traces,
and user feedback», e dal dettaglio del singolo utente vedere metriche aggregate o tutte le sue
trace e feedback ([users](https://langfuse.com/docs/observability/features/users)).

```python
from langfuse import observe, propagate_attributes

@observe()
def process_user_request(user_query):
    with propagate_attributes(user_id="user_12345"):
        return process_query(user_query)
```

> **Differenza v4, importante.** In v3 si usava `update_current_trace()`; in v4 è sostituito da
> **`propagate_attributes()`**, un context manager che applica gli attributi alla observation
> corrente **e a tutte le figlie** create nel suo scope. `update_trace()` è stato spezzato in
> `propagate_attributes()` + `set_current_trace_io()` + `set_current_trace_as_public()`
> ([upgrade path v3→v4](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v3-to-v4)).

**Quando usare cosa (in parte dedotto per il caso `tassonomia`):** `session_id` per raggruppare le
trace che appartengono alla stessa conversazione multi-turno — nel caso di `tau2-bench`, il singolo
task, che è esattamente una conversazione. `user_id` per segmentare per persona/tenant: in un
benchmark ha senso solo se lo si riusa come dimensione artificiale (es. dominio, variante di
agente). La documentazione non dà indicazioni specifiche per i benchmark.

### 5.3 Altre due differenze v4 da tenere a mente

- **Span filtering.** La v4 non esporta più tutti gli span OTel di default: filtra tenendo gli
  span creati da Langfuse, quelli con attributi `gen_ai.*`, e gli scope di instrumentation LLM noti
  (OpenInference, LangSmith, …). Si può forzare con `should_export_span=lambda span: True`.
- **Namespace API.** Gli endpoint v2 ad alte performance sono ora i default:
  `api.observations_v_2` → `api.observations`; i v1 legacy sono sotto `api.legacy.observations_v1`.
  Pydantic v2 è obbligatorio.

([upgrade path v3→v4](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v3-to-v4))

---

## 6. Dashboard, metriche aggregate, costi e token

### 6.1 Dashboard

Langfuse fornisce dashboard **built-in** curate — Latency, Cost (token usage e costi nel tempo),
Usage — più dashboard **custom** costruite su «a flexible, self-service analytics solution built on
a powerful query engine that supports multi-level aggregations»
([custom dashboards](https://langfuse.com/docs/metrics/features/custom-dashboards)).

Un **widget** si compone scegliendo:

- **data source**: traces, observations, evaluation scores;
- **metrica**: count, latency, cost, score, token usage;
- **dimensione di raggruppamento**: user, model, time, trace name, environment;
- **filtri**: metadata, timestamp, proprietà utente, parametri del modello, tag, range di score;
- **tipo di grafico**: line, bar, time series, pie.

Le dashboard supportano drag-and-drop, resize, aggiornamento in tempo reale, **export/import JSON**
(portabilità tra progetti), export CSV, copia/incolla di widget, e gestione via API, CLI e MCP
server. I filtri del widget hanno precedenza sui selettori della dashboard.
Il piano [pricing](https://langfuse.com/pricing) elenca le custom dashboard come disponibili su
tutti i piani.

### 6.2 Metrics API

Per estrarre gli stessi numeri programmaticamente:
`GET /api/public/v2/metrics` ([metrics API](https://langfuse.com/docs/metrics/features/metrics-api)).

Le **view** disponibili in v2 sono `observations`, `scores-numeric`, `scores-categorical`,
`scores-boolean`. La query JSON prende `view`, `metrics` (misure + aggregazione), `dimensions`,
`filters`, `fromTimestamp`/`toTimestamp`, `orderBy`, `config.row_limit` (default 100, max 1000).

Vincoli documentati: le dimensioni ad alta cardinalità (`id`, `traceId`, `userId`, `sessionId`)
**non** si possono usare per il raggruppamento; i dati provenienti da SDK vecchi possono avere fino
a 15 minuti di ritardo.

Il fatto che esistano view dedicate `scores-categorical` è la ragione per cui una tassonomia
costruita su score categorici è direttamente interrogabile e graficabile.

### 6.3 Come viene calcolato il costo — e perché su free tier è teorico

Da [token and cost tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking):

- Langfuse distingue valori **ingested** (arrivano dalla risposta dell'LLM tramite SDK/integrazione)
  da valori **inferred** (calcolati da Langfuse con model definition e tokenizer). Quando ci sono
  entrambi, «ingested values take priority over inferred ones».
- Per il costo inferito, il campo `model` della generation viene matchato **via regex** a una model
  definition che contiene i prezzi per usage type; Langfuse moltiplica prezzo × usage osservato.
- Il calcolo avviene **al momento dell'ingestion**, a condizione che (1) l'usage sia ingerito o
  inferito via tokenizzazione e (2) esista una model definition con i prezzi per quegli usage type.
- Si possono aggiungere model definition custom da *Project Settings > Models* o via Models API;
  le definizioni utente hanno priorità su quelle mantenute da Langfuse. Sono supportate fasce di
  prezzo (es. pricing high-context di Anthropic).
- **Trappola:** le chiavi di `usage_details` sono bucket **non sovrapposti**. `input` deve
  escludere i cached token, `output` deve escludere i reasoning token, altrimenti il costo viene
  doppio-contato.

> **Sul free tier (dedotto, ma con base documentale solida).** La documentazione descrive il costo
> come prodotto *prezzo di listino della model definition × token osservati*. Non esiste alcun
> collegamento alla fatturazione reale del provider. Ne segue che, se stai usando un modello su
> free tier (come `gemini-flash-lite` nel progetto), il costo mostrato in Langfuse è **il prezzo di
> listino teorico, non denaro effettivamente speso**. È comunque la metrica giusta per confrontare
> configurazioni di agente tra loro, purché il numero venga presentato come "costo che avresti
> pagato a listino". La documentazione **non** discute esplicitamente il caso free-tier.

---

## 7. Alerting

**Sì, Langfuse supporta l'alerting nativo.** Non è un buco da riempire con Grafana esterno.
([alerts](https://langfuse.com/docs/observability/features/alerts))

**Cosa si può monitorare.**
- *Data source*: observations, score numerici, score categorici, score boolean.
- *Metriche*: aggregazioni tipo average latency, count, p95 cost.
- *Filtri*: model name, tag, user ID, environment, valori boolean.

**Soglie.** Una soglia di **alert** (obbligatoria, severità `ALERT`) e una soglia di **warning**
opzionale che scatta prima (severità `WARNING`). La finestra di valutazione va da ore a settimane.

**Canali di notifica.** Tre:
- **Slack** — posta un messaggio in un canale;
- **Webhook** — HTTP POST con payload JSON firmato in HMAC;
- **GitHub Actions** — genera un evento `workflow_dispatch`.

**Gestione dei casi limite.** Configurabile il comportamento in assenza di dati (trattare come 0,
mantenere la severità precedente, mostrare stato `NO_DATA`, o notificare dopo un buco prolungato) e
la **rinotifica**, da 1 a 10.080 minuti finché la severità persiste.

**Limiti per piano** ([pricing](https://langfuse.com/pricing)): Hobby 2 alert, Core 20, Pro 50,
Enterprise 100.

**Nota di disponibilità:** la pagina documenta gli alert su Langfuse Cloud; **non dichiara** la
disponibilità in self-hosting.

Per `tassonomia`: un alert su score categorico (es. conteggio di `failure_type:policy_violation`
sopra una soglia in 24 ore) con canale webhook o GitHub Actions è fattibile con quanto documentato.

---

## 8. Note specifiche per `tassonomia`

### 8.1 LiteLLM → Langfuse via `langfuse_otel`

Configurazione documentata ([integrazione LiteLLM](https://langfuse.com/integrations/gateways/litellm)):

```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_OTEL_HOST="https://us.cloud.langfuse.com"
```

```yaml
# litellm_config.yaml
model_list:
  - model_name: gpt-5.1
    litellm_params:
      model: gpt-5.1
litellm_settings:
  callbacks: ["langfuse_otel"]
```

Endpoint regionali: US `us.cloud.langfuse.com`, EU `cloud.langfuse.com`, Giappone
`jp.cloud.langfuse.com`, HIPAA `hipaa.cloud.langfuse.com`. La pagina rimanda a un'integrazione
LiteLLM SDK "legacy" separata ma **non spiega le differenze** tra il callback `langfuse_otel` e il
vecchio `"langfuse"`.

### 8.2 Come impostare la tassonomia dei fallimenti — implicazioni

Dedotto dalle fonti sopra, non è una ricetta della documentazione:

1. **Valuta observation, non trace.** L'evaluator trace-level è deprecato. Usa il filtro
   *Is Root Observation* per colpire la root del task `tau2-bench`, oppure filtri su `name`/`type`
   per colpire le tool call.
2. **Uno score `CATEGORICAL` con Score Config condiviso.** Definisci il config una volta (es.
   `failure_type` con l'elenco chiuso delle categorie) e riusalo sia per l'evaluator LLM sia per
   l'annotazione manuale: così le due sorgenti sono confrontabili e filtrabili con la stessa query
   `scores.failure_type:...`.
3. **Più evaluator componibili invece di uno monolitico.** L'architettura observation-level permette
   evaluator diversi su operazioni diverse della stessa trace; e uno score categorico ammette
   match multipli.
4. **Baseline umana prima.** Testa l'evaluator su observation campione dalla UI (step 7 di §1.3),
   e usa un'annotation queue per costruire il ground truth contro cui misurare l'accordo del
   giudice.
5. **Batch sulle trace già raccolte.** L'evaluator può girare in batch su observation storiche —
   utile perché i run S1/S2 sono già in Langfuse.
6. **Versiona gli evaluator via API.** Gli endpoint Evaluators/Evaluation Rules sono stabili: la
   definizione della tassonomia può stare in git nel repo invece che solo nella UI.

---

## 9. Cosa la documentazione non copre

Domande rimaste senza risposta nelle fonti primarie consultate:

1. **Batch evaluation su observation storiche — dettagli operativi.** La pagina core-concepts la
   menziona («Langfuse v4 preview toggle enables LLM-as-a-Judge for batch evaluation») ma non ho
   trovato una pagina che spieghi limiti, dimensione massima del batch, costi, o se il toggle di
   preview sia ancora tale ad agosto 2026.
2. **Forma esatta v4 del linking prompt↔trace.** Lo snippet documentato usa `langfuse.generation()`,
   API pre-v4. La forma con `start_observation(as_type="generation")` non è mostrata nella pagina
   prompt management.
3. **Disponibilità di LLM-as-a-judge e alerting in self-hosting.** La pagina overview non dichiara
   la disponibilità self-hosted degli evaluator; la pagina alerts documenta i limiti Cloud e tace
   sul self-hosting. Il pricing copre solo i piani Cloud.
4. **Free tier e costo teorico.** Nessuna pagina discute il caso in cui il modello sia gratuito e il
   costo mostrato sia puramente nominale. La conclusione di §6.3 è mia, dedotta dal meccanismo di
   calcolo documentato.
5. **Libreria di evaluator predefiniti.** La pagina LLM-as-a-Judge parla di «templates» che
   prepopolano la configurazione, ma la pagina overview non elenca un catalogo gestito (tipo RAGAS,
   hallucination, toxicity). Non so quali template esistano davvero senza guardare la UI.
6. **Differenze `langfuse_otel` vs callback `"langfuse"` legacy.** Menzionate ma non spiegate.
7. **Come modellare un benchmark.** Nessuna guida su come mappare i concetti session/user su un
   benchmark agentico anziché su un'app con utenti reali.
8. **Semantica precisa del trace ID in v4.** Ho verificato il modello observations-first e la
   propagazione degli attributi; la formulazione "non esiste più un'entità trace separata" è
   coerente con quanto letto ma non l'ho trovata come frase esplicita in una pagina di
   documentazione — gli score trace-level e `score_current_trace()` continuano a esistere.
