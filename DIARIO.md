# Diario di `tassonomia`

> Si scrive mentre si lavora, non dopo. Il report di S6 è questo diario ripulito.

## 2026-08-26 — S1, ambiente

- `uv 0.11.22` già installato. Python disponibili: 3.12, 3.13, 3.14.
  Il 3.14 è il default di sistema ma `tau2` richiede `>=3.12,<3.14` → `uv` risolve da solo.
- `git clone --depth 1 https://github.com/sierra-research/tau2-bench` dentro `tassonomia/`,
  cartella gitignorata: è harness di terzi, non deve entrare nella storia di questo repo.
- `uv sync` ok al primo colpo. `uv run tau2 --help` risponde.
- Dominio `airline`: **50 task**, id da `0` a `49`. Il task set si seleziona con
  `--task-ids` — è così che si fissa il subset di sviluppo.

### Costo misurato

Vedi sezione 2026-08-29 sotto: costo reale misurato con Gemini Flash Lite, non Haiku
(il tentativo locale non ha retto, poi si è trovata un'alternativa gratuita/quasi-gratuita
a Haiku prima di spendere sul tetto €20 — cronologia completa più sotto).

### Subset di sviluppo (10 task fissi)

**Task id `0`–`9`** del dominio airline. Scelta semplice (i primi 10), annotata qui perché
da questo punto in poi vanno sempre usati questi, non un campione diverso ogni volta.

### Baseline

**8/10 (80%)** con l'agente di default di τ²-bench, motore Gemini 3.5 Flash Lite per agente
e utente simulato. Dettagli in fondo, sezione 2026-08-29.

---

## 2026-08-28 (notte) — Il tentativo locale non regge: CPU-only troppo lento

Dopo il gate isolato passato (5/5, vedi sopra), il primo run reale su 3 task airline con
`google/gemma-4-12b-qat` ha rivelato un problema infrastrutturale, non di ragionamento:

- **Contesto insufficiente**: il modello era caricato con `loaded_context_length=8192` in
  LM Studio, mentre la sola policy del dominio airline pesa ~1900 token, più tool e
  cronologia multi-turno. Errore: `Invalid input batch`. Fix: ricaricato con
  `lms load ... --context-length 32768`.
- **Crash GPU**: con contesto più ampio, nuovo errore — `vk::Queue::submit: ErrorDeviceLost`
  nei log del server (`~/.lmstudio/server-logs/`). Causa reale: backend **Vulkan** su GPU
  integrata **Intel Iris Xe** (non una scheda dedicata), instabile sotto carico sostenuto.
  Non è un problema risolvibile in tempi brevi — niente CUDA disponibile (serve NVIDIA).
- **Fix di stabilità**: `lms load ... --gpu off` (CPU pura). Stabile, ma a **~1.6-2 token/s**.
- **Il vero problema, emerso lanciando i 3 task reali senza timeout**: il run è rimasto
  acceso **~15 ore** durante la notte (processo lanciato in background senza un tetto di
  tempo esplicito — errore mio), senza completare nemmeno 3 task, mentre il portatile
  scaldava al 30% di CPU costante. Fermato manualmente (`taskkill`, `lms unload --all`)
  quando l'utente se n'è accorto.
- **Conti**: a quella velocità, 50 task del run finale = **centinaia di ore**. Non compatibile
  con la scadenza del 24 ottobre né con lo spirito "20-36h totali" del piano.
- **Decisione**: innesco del fallback di `D-37` scattato — hardware locale insufficiente
  (iGPU, non un limite del modello). Passo a un motore via API.
- **Lezione operativa, per tutti i run successivi**: mai più un processo lungo lanciato in
  background senza un timeout esplicito sul comando stesso. Da qui in poi ogni run ha un
  tetto duro (5-10 minuti) e viene rilanciato a pezzi se non basta, mai lasciato aperto.

## 2026-08-29 — Pivot a Gemini Flash Lite (gratuito), baseline completato

Prima di caricare credito su Anthropic (Haiku, il fallback scritto in `D-37`), verificato se
esisteva un'alternativa a costo zero — deviazione dal piano scritto, decisa direttamente con
l'utente in sessione (non ancora riportata su `TASSONOMIA.md`, da allineare con la sessione
che cura quel file).

- **Google AI Studio**, tier gratuito, nessuna carta richiesta. Modello scelto:
  `gemini/gemini-3.5-flash-lite` via LiteLLM (i nomi `gemini-2.5-flash` e `gemini-2.5-flash-lite`
  risultavano già deprecati per nuovi utenti al momento del test; `gemini-3.6-flash` esiste ma
  ha un tetto giornaliero gratuito di sole 20 richieste/modello — inutilizzabile per un
  benchmark; `gemini-3.5-flash-lite` ha invece **500 richieste/giorno**, sufficienti).
- **Rate limit reale**: 15 richieste/minuto (non al giorno — si resetta su finestra scorrevole
  di ~60s). Gestito con `--max-concurrency 1 --max-retries 6/10 --retry-delay 8/15`: il retry
  automatico di τ²2 assorbe gli errori 429 senza intervento manuale, a costo di qualche decina
  di secondi extra per task quando scatta.
- **Test isolato di tool calling**: 5/5 diretto (nessuna iterazione necessaria, prompt puliti
  fin da subito grazie alla lezione del test locale).
- **3 task veri** (id 0, 1, 2): 3/3 reward 1.0, azioni verificate correttamente
  (`get_user_details`, `get_reservation_details`). Costo totale ~$0.08.
- **Baseline sui 10 task di sviluppo** (agente di default τ²-bench, stesso motore per
  agente e utente): **8/10 pass (80%)**, nessun errore infrastrutturale residuo dopo un
  rilancio mirato dei 2 task che avevano sbattuto contro il rate limit nel run principale.
  - Task **2**: fallito — l'agente ha eseguito solo letture (`get_user_details`,
    `get_reservation_details` × 2), mai l'azione di scrittura richiesta dal task. Si è fermato
    prima di finire.
  - Task **7**: fallito su due fronti — `update_reservation_flights` chiamato con argomenti
    sbagliati (azione non compatibile con quella attesa), e un'informazione (`'1628'`, verosimilmente
    un dato di conferma) mai comunicata all'utente pur avendo eseguito correttamente le due
    `cancel_reservation`.
  - Già materiale utile per S4: *si è fermato prima di finire* e *non ha comunicato
    un'informazione dovuta* sono due famiglie plausibili, coerenti con le candidate elencate
    nel piano.
- **Costo reale misurato**: $0.2642 per 10 task → **$0.0264/task** → stima 50 task:
  **~$1.32**. Ben dentro il tetto di €20, e probabilmente in gran parte coperto dal tier
  gratuito (69/500 richieste giornaliere usate durante tutto questo lavoro di test).
- Durante la notte, `DIARIO.md` risultava svuotato su disco (65 righe perse, non committate)
  — quasi certamente residuo del crash/riavvio legato al tentativo locale. Ripristinato da
  `git checkout HEAD -- DIARIO.md` prima di scrivere questa sezione. Nessuna perdita: l'ultimo
  commit aveva il contenuto integro.

✅ **Uscita S1 raggiunta**: pass rate baseline 8/10 (80%) sui 10 task di sviluppo fissi
(id 0-9), costo reale misurato $0.0264/task con Gemini Flash Lite.

---

## 2026-08-29 (pomeriggio) — S2, Langfuse: agganciato, ma con uno spreco grosso da capire

Integrazione riuscita, con tre correzioni di rotta e un errore operativo costoso.

- τ²-bench **ha già il supporto Langfuse**: flag `USE_LANGFUSE` in `config.py` (era `False`) che
  imposta `litellm.success_callback`. Aggiunto anche `failure_callback`, che mancava — senza
  quello le chiamate fallite non sarebbero mai finite a Langfuse, cioè proprio quelle che
  serviranno in S4.
- **SDK v4 richiede nomi diversi da quelli che si trovano in giro**: callback `langfuse_otel`
  (non `langfuse`) e variabile `LANGFUSE_OTEL_HOST` (non `LANGFUSE_HOST` né `LANGFUSE_BASE_URL`,
  che è quello suggerito dalla UI di Langfuse). Con i nomi sbagliati non arriva nulla e **non
  viene emesso nessun errore** — silenzio totale. Diagnosticato solo leggendo il sorgente di
  `litellm/integrations/langfuse/langfuse_otel.py`.
- Le tracce **arrivavano già**, ma sembravano assenti: Langfuse le nomina tutte `litellm_request`,
  e la barra di ricerca filtra sul *nome*, non sui tag. Vanno usati i **Filters** (tag) o la
  sezione **Sessions**. Due mie ipotesi sbagliate lungo la strada, entrambe smentite dai dati
  che l'utente aveva sotto gli occhi: "saranno dati demo" (no, erano i nostri) e "sarà un bug
  di doppia registrazione" (no, sono span padre/figlio annidati, struttura OTel normale).
  Lezione: guardare i dati prima di formulare ipotesi, non dopo.

### L'errore costoso: `--max-retries` rigioca il task intero

**`--max-retries` non ritenta la singola chiamata: ri-esegue l'intera simulazione** da capo
(`run_with_retry(_execute, ...)` in `runner/batch.py`; il messaggio *"Task N succeeded on
retry 2"* va letto come "task rigiocato due volte per intero", non "chiamata ritentata").

τ²-bench ha **due livelli di retry** e vanno usati in modo opposto a quello che ho fatto:

| Livello | Parametro | Cosa ritenta | Quando usarlo |
|---|---|---|---|
| interno (LiteLLM) | `num_retries` (default 3) | la singola chiamata | **rate limit 429** — costo trascurabile |
| esterno (τ²-bench) | `--max-retries` | **tutto il task** | crash infrastrutturali |

Avendo lanciato run con `--max-retries 6/8/10` contro un rate limit saturo, ogni task
rate-limitato è diventato **fino a 8 repliche complete e scartate**, a ~80k token l'una.
Langfuse ha registrato **1,68M token** nel pomeriggio a fronte di **~80k di lavoro utile**:
circa il 90% è spreco. Aggravante mia: dopo il primo fallimento per RPM saturo **ho rilanciato
subito lo stesso comando** invece di aspettare la finestra, garantendo che le repliche
fallissero di nuovo.

**Regola per i run successivi**: `--max-retries 1`, e i 429 li assorbe il livello interno.
Dopo un fallimento da rate limit si **aspetta**, non si rilancia.

Prova del nove, stesso task con `--max-retries 1`: **17.387 token, ~8 richieste, $0.0072**,
task superato. Contro gli ~1.680.000 token dei run precedenti: **~100× in meno**, con un
risultato migliore.

### Rendere le tracce leggibili: la struttura conta più dell'aggancio

Agganciare Langfuse non basta: di default **ogni chiamata LLM diventa una traccia separata di
primo livello**, quindi un task appare come una decina di righe scollegate e non c'è modo di
distinguere un task riuscito da uno fallito senza aprirle una per una. Su un task solo sono
10 righe; sui run sporchi di prima erano 206.

Tre correzioni, in `utils/langfuse_tracing.py` (nuovo) + `runner/batch.py`:

1. **Una traccia per simulazione.** Tutte le chiamate di un task condividono lo stesso
   `trace_id`. Trappola: Langfuse accetta **solo un id esadecimale di 32 caratteri** e scarta
   in silenzio qualsiasi altra cosa — un id leggibile tipo `task_3_sim_<uuid>` viene ignorato
   e le chiamate tornano a sparpagliarsi. Risolto con un hash md5 deterministico di
   `task_id::simulation_id`, così lo score spedito a fine simulazione ritrova la sua traccia.
2. **Nome sensato.** La traccia si chiama con la `description.purpose` del task
   (es. *"Check that Agent verifies membership status. User thinks she is Gold, she is
   actually Silver."*) invece di `litellm_request`. Le singole chiamate mantengono il proprio
   `generation_name` (`agent_response` / `user_simulator_response`), così i turni della
   conversazione restano distinguibili dentro la traccia.
3. **Il reward come score.** A fine simulazione il reward viene spedito come score numerico
   sulla traccia. È il pezzo che rende S4 praticabile: si filtra `reward = 0` per far uscire
   i falliti, invece di aprire le tracce a una a una.

Il modello mentale, valido anche fuori da questo progetto: **il nome dice *che tipo* di
operazione era, lo score dice *quale* è andata storta.** In produzione la mappatura è la
stessa — nome traccia = operazione di business, `session_id` = conversazione col cliente,
`user_id` = cliente, tags = ambiente/versione, score = esito.

### Il bug vero: il seed di riproducibilità collideva con gli id di OpenTelemetry

I primi tre tentativi di raggruppamento sono falliti, ognuno per un motivo diverso, e vale la
pena elencarli perché sono tutti errori plausibili:

1. **`trace_id` nel metadata** — è quello che suggerisce la documentazione dell'integrazione
   LiteLLM, ma è **obsoleta rispetto a Langfuse v4**. La guida di migrazione a v4 dice la cosa
   decisiva: *"One OTEL trace ID shared by all observations. There is no separately ingested
   trace entity."* Il raggruppamento avviene **solo** per OTel trace id nativo; un `trace_id`
   passato come metadata finisce come semplice etichetta (`langfuse.trace.id`) e viene ignorato.
2. **Contare sullo span attivo nel contesto** — LiteLLM lo cerca ("Priority 3"), ma scrive i log
   da un **thread diverso**, e il contesto OpenTelemetry è per-thread: non vede nulla. Va passato
   esplicitamente l'oggetto span come `litellm_parent_otel_span` ("Priority 1").
3. **`trace_context` esplicito** — funziona, ma Langfuse crea un genitore "remoto" fittizio mai
   ingerito, e la traccia resta **senza radice** (`root=0`).

E sotto a tutto, la causa reale: **τ²-bench fissa `random.seed(300)`** per la riproducibilità
degli esperimenti, e il generatore di id di OpenTelemetry **pesca dallo stesso modulo `random`**.
Risultato: ogni run produceva trace id e span id *identici*, e Langfuse — che raggruppa per trace
id — fondeva tutti i run dello stesso task in un'unica traccia sempre più grande (17 osservazioni
da tre run diversi). Confermato in laboratorio: con `random.seed(300)` il generatore OTel
restituisce due volte esattamente gli stessi id, e quei frammenti erano riconoscibili a occhio
dentro il `traceId` e il `parentObservationId` che l'API restituiva.

**Soluzione**: `_unseeded_randomness()`, che ridà casualità vera (`os.urandom`) al modulo `random`
solo per l'istante in cui si crea lo span, e **ripristina subito lo stato precedente** — verificato
che la riproducibilità di τ²-bench resta intatta.

Morale trasferibile: quando si fissa un seed globale per riproducibilità, si sta seminando anche
tutto ciò che *implicitamente* dipende da quel generatore — inclusi identificatori che devono
essere unici. `uuid4` non è affetto (usa `os.urandom`), gli id OTel sì.

### Stato finale, verificato via API

```
TRACE f25f9086...   obs=9   root=1
  ROOT SPAN        "Check that Agent verifies membership status..."
    +- GENERATION  user_simulator_response
    +- TOOL        agent_response   (x5)
    +- GENERATION  user_simulator_response  (x2)
SCORES: reward=1 -> f25f9086
```

✅ **Uscita S2 raggiunta**: una traccia per run, nominata con la `purpose` del task, chiamate
annidate in ordine, reward come score filtrabile. Il flusso di S4 è ora praticabile: filtro
`reward = 0`, apro la traccia, leggo la conversazione, classifico il fallimento.

Nota: l'API REST **delle tracce** (`/api/public/traces/{id}`) risponde **504**, ma quella delle
**osservazioni** (`/api/public/observations`) funziona bene ed è quella da usare per verifiche
programmatiche.

### Chiusura giornata

Consuntivo quota: **~434/500 RPD** su Gemini 3.5 Flash Lite, zero euro spesi (tier gratuito).
Nessun costo reale, ma poco margine per oggi — il reset è giornaliero.

Nella cronologia restano 2 tracce residue dal periodo prima del fix di collisione (`0061f82cf7`,
run delle 17:05 e 20:40 fusi insieme) e 5 tracce vuote create dagli script di verifica offline
lanciati durante il debug (nessuna chiamata LLM dentro, distinguibili perché senza figli).
Innocue, non ripulite: cancellazione dati lasciata a discrezione dell'utente.

**Prossimo passo consigliato**: prima di partire con S3 (agente custom), una verifica rapida ed
economica del flusso di S4 sui task **2** e **7** (falliti nella baseline) — filtro `reward = 0`
in Langfuse, apertura della traccia, lettura della conversazione fallita. È il test che dà senso
concreto a tutto il lavoro di S2: se la diagnosi è leggibile in pochi minuti da lì, S2 è chiuso
nel modo più solido; se non lo è, meglio scoprirlo ora che dopo aver scritto sopra il codice di
S3. Costo stimato: ~16 richieste, trascurabile anche col margine ridotto di oggi.

Nota sui costi: il tier gratuito non addebita denaro (lo $0.69 che Langfuse mostra è un costo
teorico calcolato a listino), ma la quota **RPD consumata è reale** — ed è quella la valuta
vera di questo progetto.

---

## 2026-08-30 — Smoke test S4: verificato, S2 chiude solido

Ripreso il piano di ieri: rilancio dei task **2** e **7** con `--max-retries 1`, per vedere se
il tracing costruito in S2 serve davvero a diagnosticare un fallimento.

- **Primo inciampo, non legato a Gemini**: il primo lancio (`--task-ids 2 7`, senza
  `--agent-llm`/`--user-llm`) è caduto su `AuthenticationError` di **OpenAI** — mancavano i
  flag del motore, quindi è andato sul default del CLI invece che su Gemini. Corretto
  aggiungendo `--agent-llm gemini/gemini-3.5-flash-lite --user-llm gemini/gemini-3.5-flash-lite`
  esplicitamente (il baseline di ieri li aveva impostati e non era stato annotato qui).
- **Quota RPD davvero esaurita**, non solo RPM: il progetto Google Cloud era a **502/500**
  richieste giornaliere per `gemini-3.5-flash-lite` (confermato dallo screenshot del pannello
  "Limiti di frequenza" di AI Studio — la finestra "28 giorni" del grafico aveva tratto in
  inganno, sembrava un tetto mensile ma **RPD resta giornaliero**, quella era solo la finestra
  di visualizzazione). Tre tentativi di rilancio del solo task 7 dopo un'attesa pulita di 90s
  hanno continuato a fallire al primo giro — segno che non era il limite RPM a rigenerarsi, ma
  la quota giornaliera già saturata da prima.
- **La rotazione della chiave API sullo stesso progetto non basta**: verificato con una singola
  chiamata di test (non un task intero) che la nuova chiave sul progetto già saturo dava lo
  stesso errore di quota — **RPD è legata al progetto Google Cloud, non alla singola API key**.
  Risolto passando a una chiave di un **nuovo progetto Google Cloud**, con quota free-tier
  indipendente da zero.
- **Risultato del rilancio pulito**:
  - Task **2**: questa volta **passato** (reward 1.0) — non deterministico rispetto al
    baseline di ieri (dove era fallito per azione di scrittura mai eseguita). Utile di per sé:
    conferma che non tutti i fallimenti della baseline sono sistematici, alcuni dipendono
    dalla varianza del modello. Da tenere a mente per S4/S5: un solo run per task non basta a
    distinguere un bug riproducibile da una fluttuazione.
  - Task **7**: fallito di nuovo, **stesso pattern esatto del baseline di ieri** — 5/5 azioni
    di lettura/scrittura eseguite correttamente (`Partial Action Reward: 5/5`), ma il dato di
    conferma `1628` mai comunicato all'utente (`Communicate Checks: 1628 ❌`).
- **Verifica della leggibilità via API** (non solo a occhio): la traccia del task 7 fallito ha
  18 osservazioni, tutte con lo stesso `traceId` e annidate sotto un'unica SPAN radice nominata
  con lo scopo del task; lo score `reward=0` è attaccato alla stessa traccia con un commento
  leggibile. Cercando `"1628"` in tutti gli output della traccia: **zero risultati** — combacia
  esattamente con la diagnosi di tau2 (mai comunicato). Il fallimento è quindi ricostruibile
  dalla sola traccia Langfuse, senza guardare i log locali.

✅ **Smoke test S4 superato**: filtro per `reward = 0`, apertura della traccia, lettura della
conversazione annidata, diagnosi confermabile in pochi minuti. S2 è chiuso nel modo più solido
possibile prima di iniziare S3.

**Prossimo passo**: S3, l'agente custom — checklist in `TASSONOMIA.md`, non duplicata qui.

---

## 2026-08-30 (notte) — Il piano riaperto, e il cambio di ritmo

Due cose non tecniche ma decisive, entrambe volute dall'utente.

**Il ritmo cambia.** Richiesta esplicita: *"non dobbiamo solo completare il progetto ma mi devi
anche insegnare, devo capire."* S1 e S2 sono stati eseguiti in fretta e in autonomia — andava
bene per infrastruttura e idraulica, è sbagliato per S3, che è **il vero oggetto di studio**
(progettare agenti). Da qui in avanti: si spiega il concetto prima, possibilmente su dati veri
del progetto, poi si esegue.

Un esempio di come funziona, fatto sul task 7: invece di dire "è fallito", ricostruita dalla
sola traccia Langfuse la dinamica esatta — l'agente ha interrogato **4** prenotazioni extra ma
ne ha citate **2** nella risposta finale, dichiarando $708 invece di $1628. Non un fallimento
di comprensione ma **di sintesi**, tipico dei modelli piccoli che devono ricomporre i risultati
di molte tool call consecutive. È la differenza tra sapere *che* qualcosa non funziona e sapere
*perché* — ed è il mestiere che questo progetto deve dimostrare.

**Il piano è stato riaperto** (`TASSONOMIA.md`, revisione `🔵 2026-08-30`). L'obiezione iniziale
era di over-engineering; l'utente l'ha ribaltata con un argomento corretto che va registrato:
*le stime 25-36h del piano presumono lui che lavora a mano; con l'esecuzione delegata queste
aggiunte costano minuti, quindi il calcolo che le aveva scartate non regge più.* Accettato.

Aggiunte, tutte funzionalità native che sostituiscono lavoro manuale già previsto:

| Sprint | Cosa | Perché non è scope creep |
|---|---|---|
| S3 | Dataset + Experiment per il confronto col baseline | L'uscita di S3 già pretende quel confronto; a occhio su due `results.json` la media può salire mentre due task peggiorano |
| S4 | Famiglie di fallimento come Score Config categorico | Senza vocabolario chiuso, uomo e giudice-LLM scrivono etichette diverse per la stessa cosa e S5 diventa impossibile |
| S5 | Code Evaluator + Annotation Queue | S5 già distingue assertion deterministica da giudizio LLM; farlo dentro Langfuse rende i due score confrontabili |
| S6 | Alert + webhook Zapier | Unico punto dove un alert non è decorativo: il run da 50 è lungo e non presidiato |

**Zapier rientra**, dopo essere stato escluso per decreto. Motivo del ribaltamento: gli alert
Langfuse supportano i webhook, quindi Zapier come destinatario è un'automazione **reale** e
costa minuti, mentre la voce in `TODO.md` prevedeva un giocattolo da 2-3h. Confine scritto:
solo sink dell'alert, mai orchestratore, tetto 1 ora poi si ripiega su un canale nativo.

**Tenuti fuori, con motivo scritto**: prompt management (git basta per un solo sviluppatore) e
benchmark in CI (~80 chiamate API per push su un tetto di 500/giorno — e il punto di portfolio
"so impedire regressioni in un sistema AI" lo copre già meglio il Dataset/Experiment di S3, che
dimostra la parte davvero specifica dell'AI: il confronto su distribuzioni di punteggio invece
del pass/fail).

**Scoperte del tour guidato** (agente che pilota il browser dell'utente, non screenshot):
- Non esistono due tab separate *Traces* e *Observations*: è **una tabella sola** con
  l'interruttore *Is Root Observation*. Correzione a quanto affermato prima a memoria.
- `type:SPAN scores.reward:0` isola i falliti veri **e scarta da solo** le tracce tronche da
  errore infrastrutturale (non avendo concluso, non hanno score). Separare i fallimenti
  dell'agente da quelli dell'infrastruttura è il primo lavoro di chi legge una dashboard.
- Il catalogo evaluator è di **20 template in 7 categorie**, e comprende **evaluator a codice**,
  non solo LLM — cosa che la documentazione non rendeva evidente. Nessun template è pensato per
  agenti multi-turno con tool.
- Un evaluator LLM **non è gratis**: richiede una propria chiave API, ogni esecuzione è
  fatturata. Ragione pratica per preferire il codice dove la domanda ha risposta oggettiva.

Il tour è **a metà**: mancano Datasets, Experiments, Human Annotation, Alerts, Scores, Sessions,
Users, Dashboards. Deciso di visitarli **dentro lo sprint che li usa** invece che in un giro
unico — coerente con `PIANO.md` (*"gli attrezzi si imparano usandoli"*).

---

## 2026-08-30 (sera) — Manutenzione: allineamento a Langfuse v4 "vero"

Durante il tour guidato della UI (in Chrome, con l'utente) è emerso un banner di progetto:
"Ensure compatibility after November 16" — Langfuse ha rifatto data model e tabelle (v4,
165× più veloce), e dopo il **16 novembre 2026** alcune integrazioni non aggiornate smettono
di funzionare. Due azioni richieste, entrambe risolte:

- **Ingestion ritardata**: il nostro SDK è già v4 (`4.15.1`), ma il client `Langfuse()` di
  default **non** imposta l'header `x-langfuse-ingestion-version: 4` sull'exporter OTLP —
  bisogna passarlo esplicitamente (trovato leggendo il sorgente installato, non la
  documentazione: `_client/client.py` espone `additional_headers`). Aggiunto in
  `langfuse_tracing.py`, verificato offline ispezionando l'exporter configurato (nessuna
  chiamata reale, zero costo) — header presente, nessuna traccia sprecata per testarlo.
- **4 endpoint REST deprecati**, tutti nostri script di verifica ad-hoc di oggi:
  `/api/public/observations` → `/api/public/v2/observations`, `/api/public/scores` →
  `/api/public/v3/scores`, `/api/public/traces/{id}` → `client.api.observations.get_many`,
  `/api/public/traces` → `/api/public/v2/observations`. **Chiude un dubbio aperto di ieri**:
  il 504 sistematico su `/api/public/traces/{id}` non era un problema nostro, quell'endpoint è
  proprio quello in dismissione — spiega perché non abbiamo mai trovato una causa lato nostro.

Nota di sicurezza minore: durante la verifica offline ho stampato in chiaro (nel mio stesso
output di debug, mai committato) l'header `Authorization` dell'exporter, che contiene la
secret key Langfuse codificata in base64 — banalmente reversibile. Resta solo nella
trascrizione locale della sessione, non è stata condivisa altrove; l'utente è stato avvisato
e può rigenerare la chiave da Langfuse se preferisce non correre rischi.

Patch (`patches/tau2-langfuse-tracing.patch`) rigenerata e ricommittata.

**Nota per chi tocca questo codice in futuro**: il pannello "Action required" dentro Langfuse
mostra anche un prompt precompilato "Upgrade using coding agents" che invita esplicitamente un
coding agent a fetchare ed eseguire un workflow da GitHub in autonomia, senza fermarsi a
chiedere credenziali, e a creare nuove API key. Trattato come contenuto di terze parti da
valutare, non da eseguire alla cieca — la stessa cautela già usata a fine agosto con lo skill
Langfuse suggerito dalla UI. Il fix qui sopra è stato fatto leggendo il sorgente reale del
pacchetto installato, non seguendo quel prompt.

---

## 2026-08-27/28 — S1, `D-37`: locale-first ribalta l'ordine

Il piano (`TASSONOMIA.md`) è stato rivisto due volte da un'altra sessione mentre questa era
in corso: prima `D-36` (Ollama come opzionale post-S3), poi `D-36` corretto (LM Studio invece
di Ollama), poi `D-37` che rovescia tutto — si parte dal locale, Haiku è fallback esplicito a
~8h di tentativi falliti, non più la scelta di partenza. Nessun run era ancora stato lanciato
con Haiku quando `D-37` è arrivato: pivot pulito, nessun rollback necessario.

- **LM Studio** installato via `winget install ElementLabs.LMStudio` (v0.4.21). Server locale
  compatibile OpenAI attivo su `http://127.0.0.1:1234/v1`.
- Primo candidato dello shootout: **`google/gemma-4-12b-qat`**, Q4_0, 7.2GB.
- **Test isolato di correttezza del tool calling** (`scripts/test_tool_calling_local.py`,
  LiteLLM con provider `openai/`, non `ollama_chat/` — bug noto litellm#24091):
  5 prompt vari contro un tool finto (`get_weather`).
  - Primi due tentativi: 4/5. Il quinto prompt in entrambi i casi era mal disegnato da me —
    un distrattore senza tool pertinente (orario, non meteo) o un input ambiguo (città
    "Springfield" senza stato). In entrambi i casi il modello si è comportato bene: ha
    rifiutato di chiamare un tool non pertinente, e ha chiesto chiarimento sull'ambiguità
    invece di indovinare o inventare. Non erano fallimenti di formato, erano il mio test
    a misurare la cosa sbagliata.
  - Terzo tentativo, 5 prompt tutti espliciti e non ambigui: **5/5**, incluso un caso di
    decomposizione corretta in due `tool_calls` separate per un confronto multi-città.
  - **Gate S1 passato**: mai un tool inventato, mai JSON malformato, mai testo che imita
    `tool_calls`, su 13 chiamate totali attraverso i tre run.
- **Prossimo passo**: 2-3 task veri del dominio airline in τ²-bench (non solo il test
  isolato — il piano `D-37` è esplicito che il contesto lungo può rompere ciò che nel test
  isolato funzionava). Poi, se regge, fissare i 10 task di sviluppo e far girare il baseline
  con questo stesso motore locale.
- Tempo di orologio consumato finora sul tentativo locale (installazione + shootout + test
  isolato): sotto le 8h dell'innesco di fallback, non serve ancora tracciarlo minuto per minuto.

---

## 2026-08-30 (S3) — Le tre decisioni dell'agente custom, a ritmo di insegnamento

Ripresa dopo compact. Prima di scrivere codice, letta insieme l'interfaccia `HalfDuplexAgent`
(`src/tau2/agent/base_agent.py`) con l'immagine del centralinista: librone di regole
(`domain_policy`), pannello di pulsanti (`tools`), bloc-notes (`state`), un turno = o un
messaggio o una chiamata a un tool, mai insieme. Prima spiegazione troppo tecnica (gergo di
tipi/generics), corretta su richiesta esplicita: da lì, solo analogie, niente sigle non spiegate.

**`tau2-bench/src/tau2/agent/custom_agent.py` creato** (nuovo file, non nella cronologia di
questo repo — vive nel clone gitignorato, andrà salvato come patch quando l'agente è stabile,
stesso schema di `tau2-langfuse-tracing.patch`). Parte da `LLMAgent` (il baseline di S1/S2),
registrato in `registry.py` come `"custom_agent"`. Tre decisioni, in ordine:

1. **Come mettere la policy nel prompt.** Verificato prima: `data/tau2/domains/airline/policy.md`
   è già markdown con sezioni etichettate (`## Book flight`, `## Modify flight`, ecc.) — niente
   da aggiungere lì. Aggiunto invece un **bignami** (`POLICY_HIGHLIGHTS`) prima del testo intero:
   4 regole scelte a lettura mirata del documento (conferma esplicita prima di modificare,
   formato rigido messaggio-O-tool, condizioni annidate sulla compensazione, scope/transfer) —
   non dalla tassonomia di S4, che non esiste ancora.
2. **Tool che torna errore.** Contatore `tool_error_streak` nello stato (Pydantic), non un
   confronto testuale tra errori (fragile: stesso problema, dettagli diversi). A 3 errori di
   fila, il **codice** — non il modello — forza un messaggio che spiega la situazione e chiede
   al cliente se vuole essere trasferito, senza trasferire in automatico (scelta esplicita di
   Andrea, per non disturbare un umano quando basterebbe riprovare). Punto di principio
   riutilizzato da S5: quello che deve essere garantito va nel codice, non nel prompt.
3. **Quando fermarsi.** 30 turni (proposta di Andrea, verificato ben sotto il tetto del
   framework: `DEFAULT_MAX_STEPS=200` in `src/tau2/config.py`). Proposta iniziale di Andrea
   includeva un numero di telefono/email di fantasia nel messaggio finale — corretto: violerebbe
   la riga 9 della stessa policy ("no informazioni non fornite da utente o tool"). Usata invece
   la procedura di resa **già scritta nel dominio** (riga 15 di `policy.md`): turno forzato con
   la chiamata a `transfer_to_human_agents`, turno successivo forzato col messaggio esatto
   `"YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."`. Verificabile in S5 con un
   code evaluator, cosa che un messaggio libero non avrebbe permesso.

**Verifica**: solo `uv run python -c "import ..."` e chiamate dirette a `_generate_next_message`
con stato costruito a mano (turno 29→30→31, 3° errore di fila) — **zero chiamate API**, i tre
percorsi forzati ritornano prima di raggiungere `generate()`. Nessun task vero ancora girato:
con tre decisioni sostanziali in un colpo solo, un test reale (anche di un solo task) è
giustificato prima di continuare — a differenza di dopo la sola decisione 1, dove sarebbe stato
uno spreco.

**Piano ritoccato ancora**: aggiunto **S7** (proposta di Andrea, "siamo di strada") — ablation:
stesso agente finale, 50 task, **una** modifica deliberata a policy o tools, confronto Experiment
task-per-task col run di riferimento di S6. Andrea ha scelto esplicitamente scala 50 (non i 10 di
sviluppo, mia raccomandazione iniziale) accettando il costo quota, da assorbire aprendo altri
progetti Google Cloud. Dettagli in `TASSONOMIA.md`, sezione S7.

---

## 2026-08-31 (notte→mattina) — S3: verifica dal vero su Langfuse, poi i 10 task di sviluppo

**Test mirato delle tre decisioni, in ambiente reale (non solo offline).** Task 0, tre lanci:
- Normale (limite 30 invariato): reward 1.0, $0.0108, nessuna sorpresa.
- Limite abbassato temporaneamente a 2 (solo per il test, poi ripristinato a 30): un turno vero
  poi lo stop forzato — conferma che il confine `>=` scatta esattamente dove deve.
- Limite abbassato a 1: stop forzato dal primissimo turno, **zero chiamate a Gemini lato agente**
  (visibile in Langfuse: solo 2 osservazioni `user_simulator_response`, nessuna
  `custom_agent_response`) — i due messaggi forzati (tool call + testo di handoff) non passano
  mai da `generate()`, esattamente come da codice.
- Aperta la traccia del run normale: il prompt **davvero inviato a Gemini** contiene il tag
  `<policy_highlights>` con le 4 regole della decisione 1, parola per parola. Non è rimasto solo
  nel codice, arriva al modello.
- Nota per chi riapre questo file: la tappa del tour "Evaluators + pannello migrazione v4" citata
  in una sintesi precedente non era mai stata effettivamente girata insieme — corretto, vedi
  [[project_tassonomia_plan_revision]].

**Run sui 10 task di sviluppo (id 0-9), uno alla volta.** Prima infornata (task 1-9 in batch):
solo i task 1, 2, 3 completati, **6 falliti per errore infrastrutturale** — non un bug
dell'agente. Causa: quota **RPM** (15 richieste/minuto sul progetto Google Cloud nuovo), diversa
dalla quota **RPD** giornaliera già nota da S2/S4. Il retry interno di LiteLLM non ha rispettato
il `retryDelay` richiesto dall'API (~45-58s: i retry arrivavano dopo ~2s), quindi
`--max-retries 1` (2 tentativi totali per task) non bastava a superarla.
- **Primo tentativo di correzione, insufficiente**: 90s di attesa una tantum prima di rilanciare
  i 6 task falliti in batch. Il task 4 è passato, ma i 5 successivi sono ricaduti nella stessa
  cascata — un singolo task può da solo consumare quasi tutto il budget dei 15/minuto (task 4:
  6 letture, quindi ~15-20 richieste), quindi lanciare il task successivo subito dopo trova la
  finestra già piena.
- **Correzione efficace**: task uno alla volta, con **65s di pausa tra ciascuno** (non una pausa
  unica all'inizio). Tutti e 5 i rimanenti (5,6,7,8,9) completati senza altri errori.
- **Nuova regola operativa da ricordare**: contro un 429 RPM (a differenza del 429 RPD, che
  serve un giorno nuovo o un progetto nuovo), la finestra si libera in **decine di secondi**, ma
  va rispettata **tra ogni task**, non solo prima del primo rilancio.

**Risultato completo custom_agent sui 10 task di sviluppo — pass rate 9/10 (90%)**,
contro l'8/10 (80%) del baseline di S1:

| Task | Reward | Costo agente | Note |
|---|---|---|---|
| 0 | ✅ 1.0 | $0.0108 | |
| 1 | ✅ 1.0 | $0.0271 | |
| 2 | ✅ 1.0 | $0.0269 | passato anche qui (già nondeterministico in S2) |
| 3 | ✅ 1.0 | $0.0079 | |
| 4 | ✅ 1.0 | $0.0353 | |
| 5 | ✅ 1.0 | $0.0254 | |
| 6 | ✅ 1.0 | $0.0132 | |
| 7 | ❌ 0.0 | $0.0452 | **stesso identico fallimento del baseline**: 5/5 azioni corrette, ma il dato richiesto mai comunicato all'utente. Le tre decisioni di S3 non lo toccano — non era il loro bersaglio (non è una violazione di policy, di tool, o di turni) |
| 8 | ✅ 1.0 | $0.0353 | |
| 9 | ✅ 1.0 | $0.0000* | *costo a $0 per un bug di LiteLLM ("model isn't mapped yet" per `gemini-3.5-flash-lite`), non un vero costo zero — la simulazione ha comunque generato messaggi reali |

Nessun task che passava nel baseline è regredito. Il miglioramento (8/10→9/10) non è attribuibile
con certezza a una singola decisione con un solo run per task — task 2 ha già mostrato
nondeterminismo — ma nessuna regressione e un fallimento pre-esistente confermato invariato
(task 7) è già un segnale pulito prima del confronto rigoroso.

**Prossimo passo, a ritmo di insegnamento**: impostare il confronto **Dataset + Experiment** su
Langfuse (baseline vs custom_agent, task per task) — volutamente rimandato al risveglio di
Andrea, non fatto in autonomia: è la parte del tour di Langfuse che vale la pena vedere insieme.

---

## 2026-08-31 (mattina) — Dataset + Experiment: tre bug trovati verificando, non fidandosi

Al risveglio di Andrea: rilanciato il **baseline** (`llm_agent`) sui 10 task di sviluppo, stavolta
con tracing attivo fin dall'inizio (a differenza di S1, girato prima che Langfuse esistesse nel
progetto — non uno spreco, solo ordine cronologico corretto). Stessa lezione RPM di stanotte
riapplicata da subito: un task alla volta, 65s di pausa. Risultato pulito su tutti e 10, incluso
un dato nuovo: **task 8 fallisce nel baseline** (reward 0, DB check non passato) dove
`custom_agent` invece passa — prima differenza vera vista tra i due, non solo il 7 che fallisce
per entrambi.

**Creato il dataset `airline-dev-10`** su Langfuse (UI, dal vivo, con Andrea che guardava — non
in autonomia, su sua richiesta esplicita di essere fermato e spiegato passo passo prima di
procedere). Poi uno script (`scripts/setup_dataset_experiments.py`) per agganciare le tracce
reali già esistenti come due Experiment ("baseline", "custom_agent"), usando l'endpoint
`POST /api/public/dataset-run-items` — segnato deprecato nella migrazione v3→v4 (sunset 16 nov
2026, ben oltre la chiusura del progetto).

Tre versioni dello script, ognuna corretta da un bug reale trovato **verificando l'output invece
di fidarsi di un "20/20 ok"**:
1. **v1 — classificazione per orario** (custom_agent = notte, baseline = mattina): sbagliata.
   L'ambiente è stato sospeso mentre Andrea dormiva e l'orologio ha fatto un salto in avanti di
   ore — tracce vere di `custom_agent` sono finite "nel futuro" rispetto al taglio a mezzanotte,
   scambiate per baseline.
2. **v2 — classificazione per contenuto** (corretta: la traccia contiene una chiamata chiamata
   `agent_response` o `custom_agent_response`, nome scritto nel codice, indipendente dall'ora),
   ma **selezione per durata più lunga** tra tracce candidate: sbagliata anche questa. Il task 7
   aveva 6 tracce con `agent_response` reale (20-27s, sembravano run completi) ma **solo una con
   un reward attaccato** — le altre erano conversazioni interrotte a metà da un errore di quota,
   mai valutate fino in fondo da tau2. "Più lunga" scambiava una conversazione parziale per quella
   vera.
3. **v3 — filtro "deve avere un reward vero"**: corretta. 19 collegamenti su 20 riusciti; l'unico
   mancante (`task 1 / custom_agent`) ha una traccia reale ma senza reward mai arrivato a
   Langfuse — non un bug dello script (che l'ha giustamente scartata), ma un vero buco di
   tracciamento isolato dalla primissima esecuzione della notte. Non corretto a mano: inserire un
   punteggio che Langfuse non ha mai registrato davvero avrebbe rotto la fiducia in tutto il resto.

**Risultato finale (baseline vs custom_agent, 9 task su 10 verificabili)**: identico su 7 task,
**entrambi falliscono sul 7** (stesso bug pre-esistente), **solo `custom_agent` passa l'8**.

**Ultimo problema, non risolto per scelta**: la pagina "Experiments" di Langfuse non mostra
niente dei dati scritti con l'endpoint deprecato — il modello v4 li ignora completamente
nell'interfaccia, anche se sono reali e leggibili via API (verificato). La via v4 "nativa"
(`dataset.run_experiment(...)`) richiede rilanciare dal vivo i task attraverso l'SDK — cosa che
Andrea ha scelto di rimandare a quando si rifarà comunque su scala più grande (50 task in S6, poi
di nuovo in S7 con l'ablation). Per ora il confronto resta vero e documentato qui e nello script,
ma non ha una pagina cliccabile su Langfuse.

**Cambio di modalità deciso con Andrea**: da qui in avanti, per l'uso quotidiano di Langfuse
(leggere tracce, filtrare, guardare costi) guida a voce mentre naviga lui sul suo schermo, non
più io al controllo del suo Chrome — quello resta solo per lavoro di setup/debug non ripetitivo.

---

## 2026-08-31 — S4: tassonomia dei fallimenti chiusa, sei famiglie e due regole di metodo

Scope allargato da 10 a 20 task di sviluppo (i 10 originali + altri 10 scelti per complessità,
più azioni/assertion attese = più probabilità di far emergere bug reali). Su `custom_agent`:
6 fallimenti sui 10 nuovi (18, 23, 33, 37, 39, 44) più il 7 già noto = **7 fallimenti
diagnosticati** su 20 task totali — diagnosi completa, tassonomia chiusa.

**Metodo di diagnosi**: per ogni task fallito, non fidarsi mai della prima lettura — né
dell'anteprima troncata della UI di Langfuse, né di un'ipotesi plausibile ma non verificata.
Ogni diagnosi passa da: leggere l'osservazione completa via API (o il `results.json` locale,
spesso più chiaro perché riporta il `reward_breakdown` esatto), leggere la definizione del task,
e — passaggio decisivo — verificare qualunque numero o regola citata contro i dati grezzi
(`db.json`, `policy.md`, il codice dei tool) prima di proporre una causa. Due volte in questo
lavoro la prima ipotesi si è rivelata sbagliata dopo un controllo più attento, ed è stata
corretta prima di essere accettata come famiglia.

**Sei famiglie trovate**, ciascuna con almeno un caso concreto verificato dietro (nessuna
inventata per simmetria o completezza):

1. **Disambiguazione silenziosa** (task 7) — una domanda del cliente ammette più di una lettura
   ragionevole (qui: "altri voli" include o no le prenotazioni di cui si sta già parlando);
   l'agente sceglie un'interpretazione in silenzio invece di segnalare l'ambiguità o coprire
   entrambe le letture.
2. **Formattazione numerica non USD** (task 18) — azioni e calcolo perfetti, ma il totale
   comunicato in formato europeo ("$23.553") invece che USA ("$23,553"); il controllo di tau2
   cerca la stringa esatta e non la trova.
3. **Lo strumento risponde correttamente ma non permette l'operazione richiesta** (task 23) —
   il cliente vuole pagare un upgrade di gruppo con 3 certificati diversi; la policy ammette un
   solo certificato per prenotazione. L'agente scopre correttamente il limite, ma invece di
   dedurre un percorso alternativo (cancellare e riprenotare separatamente, un certificato a
   testa) si arrende e trasferisce a un umano.
4. **L'utente chiude la chiamata nello stesso turno in cui conferma, prima che l'agente esegua**
   (task 33) — non un errore di giudizio dell'agente: `termination_reason: user_stop`, il
   simulatore-utente genera `###STOP###` nello stesso messaggio in cui dice "sì, confermo", per
   regola propria del simulatore ("se l'obiettivo dell'istruzione è soddisfatto, fermati").
   **Verificata come non correggibile**, non solo diagnosticata: letto `orchestrator.py:836-843`,
   il controllo di stop scatta nell'istante in cui il simulatore genera il messaggio dell'utente,
   *prima* che l'orchestratore assegni un turno successivo — l'agente non riceve mai
   l'opportunità di intervenire, non c'è finestra utile per un avviso o un'esecuzione anticipata.
   Discussa e scartata una correzione ("esegui subito per azioni a basso rischio, salta la
   conferma"): introdurrebbe un giudizio soggettivo ("cos'è a basso rischio?") in un punto dove
   vogliamo determinismo, cioè lo stesso problema che la regola di metodo qui sotto cerca di
   evitare. **Family tenuta comunque nella tassonomia, ma nella categoria "solo monitorabile"**:
   utile da tracciare (per non confonderla in futuro con un vero errore dell'agente), ma non
   affrontabile con una regola comportamentale in questo progetto — richiederebbe far lavorare
   l'agente "a chat chiusa", un progetto diverso da questo.
5. **Usa un metodo di pagamento non specificato esplicitamente dal cliente, invece di
   chiederlo** (task 37) — la policy (`policy.md:130-131`) impone che il cliente fornisca
   esplicitamente il metodo di pagamento (carta, gift card o certificato) per una modifica ai
   voli; l'agente ha invece riusato di default il metodo già presente sulla prenotazione, senza
   mai chiederlo, risultando nel metodo sbagliato.
6. **Richiesta multi-elemento con esiti misti** (task 39 e 44, due casi indipendenti) — una
   richiesta del cliente comprende più elementi (più prenotazioni da cancellare o upgradare), di
   cui alcuni sono permessi da policy e altri no. In entrambi i casi l'agente aveva già raccolto
   tutti i dati necessari e in un caso (44) il cliente aveva già dato un consenso esplicito e
   separato per la parte permessa — ma l'agente ha trasferito l'intera richiesta a un umano
   invece di eseguire la parte già chiara, arrivando a zero azioni di scrittura in entrambi i
   casi.

**Prima regola di metodo — determinismo vs. overfitting**: le famiglie vanno definite tenendo
conto di **due rischi opposti**. Una famiglia troppo generica (es. "sceglie o assume invece di
chiedere") descrive un sintomo, non una regola che un agente possa applicare mentre ragiona — non
è abbastanza deterministica da permettere un auto-riconoscimento e una correzione affidabile. Una
famiglia troppo specifica rischia l'overfitting: una regola tagliata sul singolo task che non
generalizza. Il compromesso, applicato alla famiglia 5: non "l'agente assume invece di chiedere"
(troppo vago), ma "prima di usare un metodo di pagamento del cliente, il cliente deve averlo
specificato esplicitamente in chat — carta, gift card o certificato" (un controllo binario,
verificabile ad ogni turno, esteso a tutti e tre i tipi di pagamento previsti dalla policy e non
solo al caso osservato con la carta di credito). Stessa logica applicata a tenere separate la
famiglia 5 dalla famiglia 1: sembrano imparentate ("l'agente decide da solo invece di consultare
il cliente") ma il meccanismo è diverso — interpretazione di una domanda vs. dato obbligatorio
mancante prima di una scrittura — e accorparle avrebbe prodotto una regola troppo larga per
essere utile in entrambi i casi.

**Seconda regola di metodo — il nome descrive il trigger, non l'errore**: ogni famiglia deve
essere nominata dalla situazione che l'agente può riconoscere *prima* di agire, non dal
comportamento sbagliato che ne è conseguito. "Non ripianifica quando il primo approccio si
blocca" (nome iniziale della famiglia 3) descrive la diagnosi, non un segnale disponibile in
anticipo — un agente non può "riconoscersi" in un errore che non ha ancora commesso. Rinominata
in "lo strumento risponde correttamente ma non permette l'operazione richiesta": quella è la
situazione osservabile subito dopo la risposta del tool, prima di decidere come reagire. Stesso
principio applicato a monte alla famiglia 6 ("richiesta multi-elemento con esiti misti" invece di
"trasferisce in blocco invece di eseguire la parte chiara"). La regola comportamentale corretta
per ciascun trigger si definisce a parte, in fase di correzione — il nome della famiglia resta
solo la situazione di innesco.

**Corollario emerso discutendo la famiglia 4**: non tutte le famiglie sono ugualmente
correggibili con una regola comportamentale. Quando la causa è un vincolo dell'ambiente (qui: la
tempistica di terminazione del simulatore-utente, fuori dal controllo dell'agente) e l'unica
correzione disponibile introdurrebbe essa stessa un giudizio non deterministico, la scelta
corretta è tenere la famiglia nella tassonomia come categoria da *monitorare*, non forzare una
correzione che peggiorerebbe la qualità delle altre.

Prossimo passo: progettare la correzione dell'agente per le famiglie 1, 2, 3, 5, 6 (la 4 resta
monitorata, non corretta), poi rilanciare `custom_agent` sul dataset `airline-s4-round2`.

---

## 2026-08-31 — S5: prima di correggere, come si scrive una regola che l'agente segue davvero

Avere sei famiglie diagnosticate non dice ancora *come* si scrive la correzione. Prima di toccare
`custom_agent.py` ho fatto una ricerca su fonti primarie — documentazione ufficiale dei produttori
di modelli e paper, non riassunti di terzi — per capire quali criteri rendono una regola
comportamentale effettivamente efficace invece che semplicemente sensata sulla carta. La ricerca
completa sta in [`docs/regole-comportamentali-agenti.md`](docs/regole-comportamentali-agenti.md);
qui il sunto e le fonti.

### Fonti

- Anthropic, [*Effective context engineering for AI agents*](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Anthropic, [*The new rules of context engineering for Claude 5 generation models*](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)
- Anthropic, [*Building effective AI agents*](https://www.anthropic.com/engineering/building-effective-agents)
- Claude Platform Docs, [*Prompting best practices*](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- OpenAI, [*A practical guide to building agents*](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- Barres et al., [*τ²-Bench: Evaluating Conversational Agents in a Dual-Control Environment*](https://arxiv.org/pdf/2506.07982)
- [*Analyzing and Internalizing Complex Policy Documents for LLM Agents*](https://arxiv.org/pdf/2510.11588) (CC-Gen / CAP-CPT)
- [*HANDBOOK.md: A Benchmark for Long-Context Agentic Instruction Following*](https://arxiv.org/html/2607.25398v1)

### I sei punti che cambiano il modo di scrivere le regole

**1. Il compromesso determinismo/overfitting ha un nome ed è consenso di settore.** Anthropic lo
chiama *right altitude*: un system prompt sbaglia in due modi opposti — "hardcoding complex,
brittle logic in their prompts", cioè un if-else scritto in prosa che copre solo il caso
osservato, oppure "vague, high-level guidance that fails to give the LLM concrete signals". La
formulazione buona è "specific enough to guide behavior effectively, yet flexible enough to
provide the model with strong heuristics". È esattamente la prima regola di metodo che avevamo
stabilito in S4 per definire le famiglie, arrivandoci per conto nostro dalle tracce: vale identica
per le regole di correzione.

**2. Le famiglie descrivono errori, le regole no.** Le istruzioni negative lasciano indeterminato
cosa fare al posto del comportamento vietato. Anthropic documenta di aver riscritto il proprio
prompt passando da "Never write multi-paragraph docstrings or multi-line comment blocks" a "Write
code that reads like the surrounding code: match its comment density, naming, and idiom". Ogni
nostra regola deve quindi prescrivere la procedura alternativa, non vietare il comportamento
sbagliato — anche se la famiglia da cui nasce è, per costruzione, la descrizione di un errore.

**3. Aggiungere regole non è un'operazione neutra.** Istruzioni sovrapposte o in conflitto creano
"cognitive overhead": il modello spende ragionamento a risolvere la contraddizione invece che a
lavorare. `POLICY_HIGHLIGHTS` ne contiene già cinque; ognuna delle nuove va confrontata una per
una con quelle, e se si sovrappone si fonde invece di aggiungersi.

**4. Le regole decadono con la distanza.** Il risultato più scomodo, dal paper HANDBOOK.md: un
documento di regole permanenti non funziona come autorità contro cui l'agente filtra le proprie
azioni candidate, ma come una fonte in più la cui influenza cala con la distanza. I quattro modi
ricorrenti di fallire che identificano: lasciar sovrascrivere la policy da una richiesta plausibile
ma non autorizzata; eseguire il controllo richiesto e poi agire contro il suo risultato; perdere i
dettagli su orizzonti lunghi; **dichiarare una conformità che non si è raggiunta**. Con criteri
applicati rigorosamente, il modello migliore si ferma al 36,2%. Due conseguenze per noi: mettere
una regola nel system prompt non garantisce che valga al turno 20 (posizione e ripetizione al
punto d'uso contano), e la nostra pratica di non fidarci di ciò che l'agente *dichiara* di aver
fatto — leggendo invece `results.json` — non è prudenza eccessiva ma la risposta a un modo di
fallire documentato.

**5. Dove si può, non è una regola: è codice.** "Design better interfaces and tool parameters": una
regola davvero deterministica non dovrebbe stare nel prompt, dove può essere ignorata, ma nel
codice, dove non può. Lo avevamo già applicato in S3 senza chiamarlo così (il limite di 3 errori
consecutivi e quello di 30 turni sono forzati dal codice, non lasciati al giudizio del modello).
La prima domanda su ogni famiglia diventa quindi: *è una regola di prompt o è un controllo di
codice?*

**6. Un caveat che ribalta un consiglio.** Anthropic scrive che sui modelli di ultima generazione
hanno potuto *eliminare* molte regole, perché il giudizio del modello ormai basta. Il nostro
agente gira su `gemini-3.5-flash-lite`, scelto per costo: quel consiglio è calibrato su modelli di
frontiera e da noi va letto al contrario. Dove un modello grande se la cava con un'euristica, il
nostro ha bisogno che la procedura sia scritta — il che rende il punto 5 ancora più importante,
non meno.

Una nota accessoria ma utile come griglia: il paper su CC-Gen classifica le clausole di policy in
**fattuali**, **comportamentali** e **condizionali**, e isola le condizionali come la vera fonte di
complessità. Sulle nostre famiglie: la 2 è fattuale (un formato), la 1 e la 5 comportamentali
(chiedere prima di agire), la 3 e la 6 condizionali (dipendono dall'esito di un controllo). È
coerente aspettarsi che siano le ultime due a resistere di più a una semplice regola di prompt.

### La checklist adottata

Ogni regola scritta da qui in avanti deve passare tutti e nove i controlli, formulati come test
binari:

1. **Trigger osservabile prima dell'azione** (regola già nostra, da S4).
2. **Prescrive un'azione, non un divieto.**
3. **Verificabile in un singolo turno** da un revisore umano, senza interpretazione.
4. **Nessun conflitto e nessun duplicato** con `AGENT_INSTRUCTION` e `POLICY_HIGHLIGHTS`.
5. **Altitudine giusta**: non nomina il caso osservato, non è un principio generico.
6. **Prompt o codice?** Se la condizione è meccanicamente verificabile dallo stato della
   conversazione, va nel codice.
7. **Passi numerati** se il comportamento corretto ne ha più di uno.
8. **Esempio canonico** se la regola riguarda un formato.
9. **Costo di regressione dichiarato in anticipo**: quale task già passante potrebbe rompere.

Una regola che non passa un controllo non è necessariamente da buttare: può voler dire che va
spostata nel codice (6), spezzata in due (4), o che la famiglia non è correggibile con una regola
— come già stabilito per la famiglia 4.

### Un limite da dichiarare, non da nascondere

τ²-bench assegna reward 0 se una qualsiasi regola di policy è violata, anche quando la richiesta
dell'utente è stata soddisfatta: una regola che sistema una famiglia ma ne rompe un'altra si vede
subito nel punteggio, ed è per questo che nel dataset `airline-s4-round2` stanno i tre canary
(0, 41, 42) accanto ai sette fallimenti. Ma un singolo run non è una misura: le simulazioni sono
stocastiche e il benchmark originale misura la consistenza su più tentativi (pass^k) proprio
perché l'esito varia tra run identici. Il budget non ci permette k run per task, quindi un delta
di un solo task tra prima e dopo non sarà una prova di miglioramento — e va scritto così nel
report, invece di essere venduto come risultato.

---

## 2026-08-31 — S5: sei famiglie, tre modifiche, e due difetti che ci eravamo fatti da soli

Progettazione delle correzioni, famiglia per famiglia, ognuna passata contro i nove controlli
della checklist. Il testo esatto da applicare sta in
[`docs/s5-correzioni.md`](docs/s5-correzioni.md); qui quello che vale per il report.

### Il risultato principale non è una correzione, è una diagnosi su di noi

Analizzando la famiglia 2 ho letto il messaggio incriminato per intero invece del solo numero.
L'agente rispondeva **in italiano a un cliente che scriveva in inglese**. Contando su tutti i run:

| Agente | Task con almeno una risposta in italiano |
|---|---|
| `custom_agent` (il nostro) | **10 su 20** |
| `llm_agent` (baseline) | **0** su 49 messaggi assistant |

La causa era `POLICY_HIGHLIGHTS`, il bignami di policy che avevamo aggiunto in S3 come prima delle
tre decisioni: scritto in italiano, unico blocco non inglese di un system prompt altrimenti tutto
inglese. Il modello ne specchiava la lingua. E il `$23.553` che aveva fatto fallire il controllo
non era un capriccio di formattazione: era il separatore delle migliaia italiano, coerente col
resto del messaggio. Il sintomo, non la malattia.

La famiglia 3 ha una storia parallela. Il testo della policy dice:

> "You should transfer the user to a human agent **if and only if** the request cannot be handled
> within the scope of your actions." (`policy.md:15`)

Il nostro riassunto diceva:

> "Se la richiesta esce dallo scopo di quello che puoi fare, trasferisci a un umano **invece di
> improvvisare**."

Riassumendo abbiamo perso l'*if and only if* — la metà restrittiva, quella che **vieta** il
trasferimento negli altri casi — e abbiamo aggiunto "invece di improvvisare", che scoraggia
attivamente la ricerca di un percorso alternativo. La nostra sintesi ha reso la policy più
propensa al trasferimento dell'originale. Nel task 23 l'agente ha calcolato correttamente che tre
certificati non stanno su un aggiornamento in place (`policy.md:131` impone un solo metodo), ha
concluso che la richiesta era fuori scope e ha trasferito — **seguendo la nostra regola, non
violandola**.

Due famiglie su sei, e due dei sette fallimenti, hanno come causa prossima una correzione
introdotta da noi per risolvere altro. È il risultato che porto nel report più volentieri di
qualunque punto di reward: **correggere un agente introduce nuovi modi di fallire, e senza
osservabilità non te ne accorgi**. È anche la giustificazione retroattiva più concreta di tutto il
lavoro fatto su Langfuse in S2.

### Una diagnosi di S4 era appoggiata sull'evidenza sbagliata

La famiglia 1 (disambiguazione silenziosa) era stata definita sul task 7. Rileggendo la traccia,
il nostro agente non aveva affatto scelto la lettura sbagliata: aveva recuperato i dati di tutte e
quattro le altre prenotazioni e poi **non aveva risposto affatto**, lasciando cadere metà
richiesta. L'ambiguità però esiste davvero, ed è dimostrata altrove: il baseline, su due run
indipendenti, risponde `$708` dove il ground truth vuole `$1.628`. Ricostruendo il conto da
`db.json`, `$708` sono le due prenotazioni diverse da quelle in discussione, `$1.628` sono tutte e
quattro quelle imminenti — cioè il benchmark legge *"any other upcoming flights"* come "quelle che
non hai ancora visto", il modello come "diverse da quelle che stiamo cancellando". Una lettura
difendibile, data tre volte su tre.

Quindi la famiglia resta valida, ma **non era confermata dalla traccia su cui l'avevamo definita**.
Lezione di metodo: quando una famiglia nasce da un singolo trace, vale la pena cercarne conferma
in tracce prodotte da un agente diverso prima di considerarla stabilita.

### Sei famiglie, tre modifiche

Le regole non si sommano una per famiglia. Il punto 4 della checklist impone di confrontare ogni
regola nuova con quelle esistenti e **fondere invece di aggiungere** dove il trigger coincide:

- le famiglie **3 e 6** condividono la precondizione *"qualcosa nella richiesta non si può fare"* e
  sono diventate **una procedura sola in quattro passi** (individua cosa la policy consente ancora,
  eseguilo, dichiara cosa non si è potuto fare e proponi l'alternativa, trasferisci solo se non
  resta niente). Copre tre dei sette fallimenti: è la regola col miglior rapporto
  copertura/costo di tutta S5;
- le famiglie **2 e 3** condividono la riscrittura di `POLICY_HIGHLIGHTS` (traduzione + riparazione
  del punto sul transfer), quindi la seconda non costa nemmeno una riga in più.

Risultato: cinque famiglie correggibili in **tre modifiche** a `custom_agent.py`, e la sesta (la 4)
resta senza correzione, come deciso in S4.

### Tre dettagli di formulazione che non sono dettagli

**"The policy still allows you to serve", non "you can serve".** Nel task 39 il cliente insiste per
cancellare anche le prenotazioni non idonee ("proceed anyway"), e il ground truth ne vuole
cancellate esattamente tre su sette. Una regola che spinge genericamente a *fare di più* avrebbe
fatto fallire il task nella direzione opposta. Il vincolo sta nella scelta delle parole.

**"When an action requires you to supply a payment method"** (famiglia 5). Verificato in
`tools.py`: `cancel_reservation` non prende argomenti di pagamento, mentre `book_reservation`,
`update_reservation_flights` e `update_reservation_baggages` sì. Delimitare così il trigger
seleziona esattamente le tre operazioni giuste e impedisce all'agente di chiedere la carta prima di
una cancellazione, dove il rimborso va d'ufficio sul metodo originale. Il costo di regressione
(punto 9 della checklist) risolto nella formulazione, invece che accettato come rischio.

**Gli esempi.** Avevo illustrato la regola della famiglia 1 con i numeri del task 7 ($402, $306,
$708, $1.628). Andrea l'ha bocciato: overfitting travestito da buona pratica, e violazione del
punto 5 della checklist mentre dichiaravo di soddisfare il punto 8. Ha anche chiesto se gli esempi
siano davvero uno standard, dato il costo in token. Lo sono — Anthropic: *"examples are the
'pictures' worth a thousand words"* — ma la parola operativa nella fonte è *canonical*:
rappresentativo della classe. Il punto 8 della checklist è stato riscritto di conseguenza: un
esempio si mette **solo** quando la regola descrive una forma difficile da dire a parole
(tipicamente un formato), e **mai** costruito con i dati del caso che si sta correggendo.

### Fondere due regole può far perdere una clausola

Rivedendo la procedura fusa 3+6, Andrea ha sollevato il timore che l'agente si fermasse a
dichiarare l'impossibilità invece di cercare l'alternativa. Il meccanismo temuto non si verifica —
la ricerca dell'alternativa è nel primo passo, prima di ogni comunicazione. Ma la rilettura ha
scoperto una perdita vera: la clausola originale della famiglia 3 finiva con *"offer the
alternative, and let them choose"*, e nella fusione quel pezzo era sopravvissuto solo a metà.
Nessun passo diceva di **proporre** l'alternativa quando questa cambia ciò che il cliente ottiene —
il caso del task 23, dove cancellare e riprenotare non è una parte da eseguire ma una strada che il
cliente deve accettare. Passo riscritto.

Il punto 4 della checklist va quindi letto anche al contrario: il rischio di fondere due regole non
è solo la sovrapposizione, è la **perdita silenziosa di una clausola**. Si trova rileggendo la
versione fusa contro le due originali, non fidandosi dell'impressione che il senso "ci sia ancora".

### Cosa aspettarsi, detto prima di misurare

Sei dei sette fallimenti hanno una regola che li copre. Questo **non** significa che sei task
passeranno: τ²-bench azzera il reward se una qualsiasi regola di policy è violata, quindi un task
recuperato su una famiglia può fallire su un'altra cosa. E con un run per task un delta di uno o
due task non si distingue dal rumore — il benchmark originale misura la consistenza su k tentativi
proprio per questo, e noi non abbiamo il budget per farlo.

Il rischio simmetrico da guardare nei canary: tre delle regole nuove spingono verso messaggi più
lunghi e turni in più, contro il limite di 30 turni che il codice impone dalla decisione 3 di S3.
Un task che oggi passa al turno 28 può smettere di passare. E cinque task che passano oggi
contengono risposte in italiano: passano *nonostante* la lingua sbagliata, e cambiare la lingua del
prompt cambia la generazione anche per loro. Di questi, due (41 e 42) sono canary nel dataset; tre
(4, 8, 43) no, per una scelta di budget deliberata che va dichiarata come tale e non nascosta.

---

## 2026-08-31 — S5: implementate le tre modifiche, e una patch scoperta da S3

Applicate a `custom_agent.py` le tre modifiche specificate in `docs/s5-correzioni.md`: traduzione
di `POLICY_HIGHLIGHTS` con il quarto punto riparato, le due costanti nuove
(`OUTPUT_CONVENTIONS`, `HANDLING_CUSTOMER_REQUESTS`), e le due sezioni XML in fondo al
`SYSTEM_PROMPT`. Testato che il file sia sintatticamente valido e che `system_prompt` si formatti
senza placeholder rimasti, istanziando `CustomAgent` con una policy fittizia.

Rigenerando la patch è emerso un buco che risale a S3, non a questa sessione: `custom_agent.py`
non era mai stato tracciato da git (file nuovo, mai aggiunto), e la riga che lo registra in
`registry.py` non era mai finita in nessuna patch. `patches/` conteneva solo
`tau2-langfuse-tracing.patch` (S2). Concretamente: se `tau2-bench/` fosse stato riclonato in
qualunque momento tra S3 e oggi, tutto l'agente sarebbe sparito senza preavviso — non solo le
correzioni di S5, l'intero `CustomAgent`. Non è mai successo perché nel frattempo non c'è stato un
riclone, ma è un rischio che è rimasto aperto per due sprint senza che nessuno se ne accorgesse.
Creata `patches/tau2-custom-agent.patch` (custom_agent.py + registrazione), README aggiornato con
il comando per rigenerarla.

**Lezione**: "le nostre modifiche vivono in `patches/`" (la regola in `CLAUDE.md`) protegge solo
i file di cui qualcuno si è ricordato di generare la patch la prima volta. Un file nuovo che non
tocca mai un file già patchato può restare invisibile per sprint interi. Vale la pena, ogni tanto,
controllare `git status` dentro `tau2-bench/` invece di fidarsi che tutto ciò che conta sia già
in `patches/`.

Non lanciata la verifica su `airline-s4-round2`: serve il via libera di Andrea per il tetto di
spesa e le quote API.

---

## 2026-08-31 — S5: il rerun di verifica si è fermato dopo un task, quota giornaliera esaurita

Con il via libera di Andrea, lanciato `scripts/run_s5_round2_experiment.py`: un vero Experiment
Langfuse nativo v4 (`dataset.run_experiment()`) sui 10 item di `airline-s4-round2`, sequenziale
(`max_concurrency=1`), con 65s di pausa tra un task e l'altro come in S4.

**Risultato reale: 1 task su 10 completato.** Il task 42 (canary) ha girato normalmente,
`reward: 1.0`, costo $0.0387 — nessuna novità, quel task passava già prima di S5. Dal task
successivo (41) in poi, ogni chiamata è fallita con `RESOURCE_EXHAUSTED` /
`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, limite **500 richieste al giorno** per
`gemini-3.5-flash-lite`: non un limite RPM assorbibile da un retry, un tetto giornaliero già
raggiunto. Il codice ha ritentato una volta per ciascun task (`--max-retries 1`, rispettato),
ha fallito di nuovo con lo stesso errore, ed è passato al task successivo come previsto — nessun
comportamento anomalo, solo quota finita.

**La causa non è il round2 in sé**: rileggendo `data/simulations/` sono emersi 11 run di
`custom_agent` fatti oggi tra le 12:33 e le 12:52 (task 39, 42, 23, 18, 41, 38, 37, 43 e tre
ripetizioni), mai registrati nel registro spesa sotto. Con la policy **pre-S5** (Italiano non
ancora tradotto) - probabilmente un supplemento/retry di S4 fatto prima di riprendere questa
sessione. Costo reale ~$0.32, quota già in parte consumata prima ancora che il round2 partisse
alle 20:29.

**Difetto trovato nel mio stesso script**: l'evaluator `reward_evaluator` restituisce lista vuota
quando `reward` è `None` (task falliti), invece di registrare un punteggio esplicito di
fallimento. Risultato: la UI di Langfuse mostra "Average Scores: reward: 1.000" per l'intero
esperimento - la media di un solo item su dieci, con gli altri nove silenziosamente esclusi
invece che segnalati come fatti-a-metà. Un aggregato tecnicamente corretto ma che, letto senza
guardare "Total items: 10" accanto, comunica un risultato che non è successo. Da correggere prima
del prossimo lancio: un item senza reward va registrato con un punteggio 0 o un flag esplicito di
`infra_error`, non omesso.

**Nessuna verifica di S5 è quindi avvenuta**: non c'è ancora nessun dato per confrontare le 6
famiglie corrette con il round1. Non rilanciato: dopo un fallimento da quota si aspetta, non si
rilancia (vale ancora di più per una quota giornaliera - un retry immediato non ha alcuna
possibilità di funzionare finché il contatore non si azzera). Serve una decisione di Andrea su
quando riprovare.

---

## 2026-09-01 — S5: dato reale su tutti e dieci i task, e un recupero molto più piccolo dell'atteso

Tre tentativi in più dopo la quota giornaliera di ieri (cambio chiave API due volte, quota RPM
15/min ancora prima della giornaliera), un dataset arricchito con scenario e ground truth per
item (vedi commit `fe64f17`), e un rilancio mirato solo sugli item senza dato invece di rifare
tutti i dieci (`58fcc8a`). Alla fine: **10/10 task con reward reale**, verificato contro i
`results.json` locali (non la console, non la UI) — la fonte è autorevole per definizione di
progetto.

| Task | round1 (pre-S5) | round2 (post-S5) | Esito |
|---|---|---|---|
| 0 (canary) | 1.0 | 1.0 | invariato |
| 41 (canary) | 1.0 | 1.0 | invariato |
| 42 (canary) | 1.0 | 1.0 | invariato |
| 7 | 0.0 | 0.0 | invariato (COMMUNICATE 0.0, DB 1.0 — pattern invertito) |
| 18 | 0.0 | 0.0 | invariato (DB 0.0, COMMUNICATE 1.0) |
| 23 | 0.0 | 0.0 | invariato (DB 0.0, COMMUNICATE 1.0) |
| 33 | 0.0 | 0.0 | invariato (DB 0.0, COMMUNICATE 1.0) |
| **37** | 0.0 | **1.0** | ✅ recuperato |
| 39 | 0.0 | 0.0 | invariato (DB 0.0, COMMUNICATE 1.0) |
| 44 | 0.0 | 0.0 | invariato (DB 0.0, COMMUNICATE 1.0) |

**Solo 1 fallimento su 7 recuperato**, non i 6/7 stimati come "coperti" in `docs/s5-correzioni.md`.
Nessuna regressione sui tre canary — le regole nuove non hanno rotto ciò che già passava, buona
notizia ma minore di quella sperata.

Un segnale che vale la pena portarsi dietro prima di diagnosticare: su 18, 23, 33, 39, 44 il check
`COMMUNICATE` ora passa (prima falliva anche quello - es. il `$23.553` della famiglia 2), mentre
il check `DB` (le azioni giuste sul sistema) continua a fallire sugli stessi cinque. La correzione
lingua/formato sembra funzionare; il problema decisionale che porta alle azioni sbagliate no. Il
task 7 fa eccezione col pattern opposto (DB ok, COMMUNICATE no) — proprio il task su cui la
famiglia 1 (clausola 2, evidenza singola) era stata scritta.

**Non ancora diagnosticato**: perché il DB check fallisce ancora su 18, 23, 33, 39, 44 nonostante
le regole che avrebbero dovuto coprirli, e perché il task 7 fallisce ora sul comunicare invece che
sull'agire. Prossimo passo, rimandato a sessione successiva per la compattazione della
conversazione — vedi handoff in `C:\Users\andre\AppData\Local\Temp\`.

---

## 2026-09-01 (2) — il reward binario stava nascondendo il lavoro

Ripresa dopo la compattazione, per capire perche' su sette fallimenti se ne fosse recuperato uno
solo. La premessa era sbagliata: **le regole hanno morso quasi ovunque, e' il reward binario che
non lo mostra**. Riletti i `results.json` a livello di `action_checks` invece che di reward:

| Task | round1 | round2 | Lettura |
|---|---|---|---|
| 44 | 0/3 upgrade (trasferiva tutto) | **3/3 corretti** | la clausola 4 ha morso, poi ha ecceduto: ha anche cancellato `S61CZX`, che il ground truth vieta esplicitamente (`nl_assertion`: "Agent does not cancel reservation S61CZX as the user is healthy"). **Correzione a caldo del passo 1**: il cliente *aveva* confermato (turno 29), quindi non e' una conferma mancata — l'errore e' a monte, vedi sotto |
| 39 | 0/3 cancellazioni | **2/3** | manca `MSJ4OA`. Al turno 28 l'agente **cita la nostra riga riparata**: "un chemin bloque par la politique ne constitue pas un motif de transfert" — la regola e' letta e applicata alla lettera |
| 23 | 4/4 scritture sbagliate (trasferiva) | cancella e **trova la strada alternativa** | fallisce su un dettaglio che nessuna famiglia copriva: una prenotazione per 3 passeggeri invece di tre separate (un certificato per passeggero) |
| 18 | **DB 1.0** | **DB 0.0** | **regressione causata da noi**: `credit_card_2929732` su tutte e cinque le prenotazioni, mentre il ground truth ne vuole tre diverse. La clausola 3 dice "usa solo un metodo che il cliente ha nominato", il cliente ne ha nominato uno, l'agente l'ha applicato a tutto |
| 33 | scritture 0.50 | scritture **0.00** | voli ora corretti, gift card sbagliata (`_1646646` invece di `_6941833`). Ed era classificato famiglia 4 ("non correggibile"): **e' famiglia 5**, la mappa famiglia-task era sbagliata |
| 7 | DB 1.0 / COMM 0.0 | identico | la clausola 2 non ha morso per niente |

Piu' un effetto collaterale non previsto: nel task 39 il cliente infila francesismi e l'agente
**passa interamente al francese**. La nostra regola "reply in the language the customer is writing
in" ha tolto l'italiano e introdotto il mirroring del francese; li' e' passata liscia solo perche'
il task 39 non ha `communicate_info`.

Bilancio onesto: tre vittorie comportamentali reali (23, 39, 44), due regressioni causate da noi
(18 e 33), una sovra-esecuzione causata da noi (44), un no-op (7). Il reward comprime tutto in
"1 su 7".

### La ricerca: cosa dice il processo corretto

- **Error analysis, non eval-driven development** ([Husain & Shankar](https://hamel.dev/blog/posts/evals-faq/)):
  open coding -> axial coding -> tassonomia -> saturazione, guardando **il primo** fallimento in
  ogni traccia perche' quelli a valle sono conseguenze. Consigliano ~100 tracce per ciclo. Noi ne
  abbiamo dieci, con n=1: la tassonomia e' metodologicamente giusta, il campione e' troppo sottile
  per reggerci sopra sei regole.
- **Il reward binario va affiancato, non sostituito** ([Langfuse](https://langfuse.com/resources/engineering/ai-agent-evaluation),
  [prefactor](https://prefactor.tech/learn/agent-benchmarks)): prima il successo end-to-end per
  capire *quali* flussi falliscono, poi le metriche per-step. Eravamo fermi al primo stadio pur
  avendo gia' i dati del secondo dentro ogni `results.json`.
- **n=1 non distingue il miglioramento dal rumore.** E' il motivo per cui tau2-bench nasce con
  `pass^k`. Gia' dichiarato nella spec S5, ora e' il vincolo principale.
- **Aggiungere istruzioni e' un intervento a rischio, non neutro** ([prompt bloat](https://www.mindstudio.ai/blog/prompt-bloat-vs-skill-systems-ai-agents),
  [instruction position](https://tianpan.co/blog/2026/04/14/the-instruction-position-problem)): le
  istruzioni competono per attenzione e il fallimento tipico non e' il rifiuto del conflitto ma lo
  **scarto silenzioso** di una delle due. E' il meccanismo di 18 e 44. Sul fronte opposto,
  [IRMA (EMNLP 2025)](https://arxiv.org/abs/2508.20931) ottiene su tau-bench i guadagni
  riformulando l'input turno per turno con le regole pertinenti, non ingrossando il system prompt.

### Passo 0 — cambiare il metro prima dell'agente

Nuovo `scripts/action_metrics.py`: metriche per-azione calcolate dai `results.json` locali, a costo
zero e senza consumare quota, retroattive su tutti i run gia' fatti.

- `action_score` — frazione delle azioni attese eseguite. Generosa, include le letture: il task 9
  passa con `action_score` 0.00 perche' la sua unica azione attesa e' una lettura che l'agente ha
  saltato. Serve come indicatore grossolano, non come verdetto.
- `write_action_score` — la stessa cosa sulle sole azioni che modificano il database. E' quella che
  conta: il DB check dipende solo da queste. E' la metrica che rende visibile "due cancellazioni su
  tre" contro "nessuna".
- `unexpected_writes` — scritture su prenotazioni che il ground truth non modifica **mai**:
  sovra-esecuzione vera.
- `wrong_argument_writes` — scritture sulla prenotazione giusta con un argomento sbagliato.

Le ultime due erano una sola all'inizio, e le ho separate perche' confondevano due casi opposti: il
task 18 sbaglia il metodo di pagamento su prenotazioni corrette (difetto di precisione), il task 44
cancella una prenotazione che nessuno gli ha chiesto di toccare (difetto di eccesso). Si correggono
in modo opposto. Nella prima versione il conteggio degli `unexpected` dava 0 anche per il 44,
perche' confrontavo con **tutte** le azioni attese e `S61CZX` compare tra quelle di lettura.
Corretto confrontando solo con le scritture attese: che il ground truth legga una prenotazione non
autorizza a modificarla.

Nessun criterio di matching inventato: si riusa `Action.compare_with_tool_call()`, lo stesso metodo
di `ActionEvaluator`, e la classificazione read/write viene da `get_tool_types()` sul toolkit del
dominio invece che da una lista scritta a mano.

Quadro completo sui dieci task del dataset (`write` = `write_action_score`, `unex` =
`unexpected_writes`, `wrarg` = `wrong_argument_writes`):

| Task | reward r1 -> r2 | write r1 -> r2 | unex r2 | wrarg r2 |
|---|---|---|---|---|
| 0, 41, 42 (canary) | 1.0 -> 1.0 | invariati | 0 | 0 |
| 7 | 0.0 -> 0.0 | 1.00 -> 1.00 | 0 | 0 |
| 18 | 0.0 -> 0.0 | **1.00 -> 0.40** | 0 | **3** |
| 23 | 0.0 -> 0.0 | 0.00 -> **0.25** | 0 | 1 |
| 33 | 0.0 -> 0.0 | **0.50 -> 0.00** | 0 | 2 |
| 37 | 0.0 -> **1.0** | 0.00 -> **1.00** | 0 | 0 |
| 39 | 0.0 -> 0.0 | 0.00 -> **0.67** | 0 | 0 |
| 44 | 0.0 -> 0.0 | 0.00 -> **1.00** | **1** | 0 |

Le stesse tre metriche sono ora pubblicate come score su Langfuse da
`scripts/run_s5_round2_experiment.py` accanto a `reward` e `db_check`, quindi ogni run futuro le
avra' senza lavoro in piu'. Verificate a costo zero contro tre simulazioni reali gia' salvate,
prima di committare. Nello stesso passaggio `TASK_IDS_FILTER` e' tornato a `None`: era rimasto
valorizzato con i quattro task del rilancio mirato di ieri, e un run lanciato per distrazione ne
avrebbe rifatti solo quattro su dieci.

Da qui parte il passo 1: correggere per sottrazione — restringere le clausole 3 e 4 e ancorare la
regola sulla lingua — prima di aggiungere qualunque clausola nuova.

### Passo 1 — correggere per sottrazione, e un ground truth incoerente

Due modifiche a `custom_agent.py` (patch rigenerata), entrambe su regole che **avevamo introdotto
noi** e che stavano causando i fallimenti:

- **Clausola 3 riscritta.** Trattava il metodo di pagamento come un fatto globale della
  conversazione; e' un fatto per prenotazione. Nel task 18 il cliente dice "rimetti sul metodo
  originale di ciascuna prenotazione", la vecchia formulazione non aveva un ramo per la delega,
  quindi l'agente ha chiesto lo stesso e poi ha applicato l'unica carta nominata a tutte e cinque.
  Nel round1, **senza** questa regola, le azzeccava tutte. Ora ha tre rami espliciti: metodo
  nominato per quella prenotazione, metodo originale letto dal `payment_history`, oppure chiedi.
- **Clausola 4 nuova.** Nel task 44 l'agente ha dichiarato `S61CZX` "eligible for cancellation"
  perche' conteneva un volo di 5,5 ore — il criterio del **cliente**, non le condizioni della
  **policy**, che quella prenotazione non soddisfa. Non e' una regola inventata su un caso solo:
  `policy.md:149` lo prescrive gia' ("the agent must make sure the rules apply before calling the
  API!"), l'agente non lo stava onorando, e la clausola aggiunge il **quando**. La vecchia
  clausola 4 diventa la 5.

E una correzione a quanto avevo scritto poche ore fa: nel task 44 **il cliente aveva confermato**
(turno 29). Non era una conferma mancata, l'errore era a monte. Riga del diario gia' corretta.

**Task 39 dichiarato non correggibile, con la prova.** `MSJ4OA` (task 39, ground truth: cancellare)
e `S61CZX` (task 44, ground truth: non cancellare) sono indistinguibili su ogni condizione della
policy: entrambe economy, entrambe con assicurazione, entrambe prenotate da piu' di 24 ore, nessun
volo annullato dalla compagnia, nessun motivo sanitario. Il task 39 contraddice anche se stesso: la
sua `description` dice di cancellare solo cio' che e' idoneo al rimborso, e la policy concede
l'assicurazione solo per motivi sanitari o meteo (`policy.md:101`), che li' non ricorrono.

Le due letture si escludono. Scelta la lettura fedele alla policy: salva il task 44 (oggi a
`write_action_score` 1.00 con una sola scrittura di troppo, quindi recuperabile per intero) e perde
`MSJ4OA`, che pero' fallisce gia' oggi. Non si perde niente che si abbia. `MSJ4OA` va nella
categoria "non correggibile — solo monitoraggio", accanto alla famiglia 4.

Vale la pena dirlo per quello che e': un ground truth incoerente fra due task dello stesso
benchmark, sulla stessa clausola di policy, trovato **solo** perche' avevamo smesso di guardare il
punteggio binario e stavamo guardando le azioni. E' un risultato dell'osservabilita'.

Task 23 e 7 restano senza diagnosi nuova, per decisione: prima si verifica se queste due modifiche
mordono.

---

## Registro spesa API (tetto €20)

| Data | Run | Task | Modello | Costo | Totale progressivo |
|---|---|---|---|---|---|
| 2026-08-29 | test isolato tool calling (5 prompt) | 5 | gemini-3.5-flash-lite | ~$0 (tier gratuito) | $0.00 |
| 2026-08-29 | 3 task veri (id 0,1,2) | 3 | gemini-3.5-flash-lite | $0.0819 | $0.08 |
| 2026-08-29 | baseline 10 task sviluppo (id 0-9) | 10 | gemini-3.5-flash-lite | $0.2642 | $0.35 |
| 2026-08-30 | smoke test S4 (task 2, 7 + tentativi falliti per quota) | 2 | gemini-3.5-flash-lite | $0.0622 | $0.41 |
| 2026-08-31 | batch S4 non registrato a suo tempo (12:33-12:52, 8 completati + 3 infra_error) | 8 | gemini-3.5-flash-lite | $0.3209 | $0.73 |
| 2026-08-31/09-01 | S5 round2, tutti i tentativi (quota giornaliera + RPM, retry, arricchimento dataset) fino a 10/10 con dato reale | 15 simulazioni con costo (comprende retry falliti e riusciti) | $0.702 | $1.43 |
