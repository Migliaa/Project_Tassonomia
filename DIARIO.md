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

## Registro spesa API (tetto €20)

| Data | Run | Task | Modello | Costo | Totale progressivo |
|---|---|---|---|---|---|
| 2026-08-29 | test isolato tool calling (5 prompt) | 5 | gemini-3.5-flash-lite | ~$0 (tier gratuito) | $0.00 |
| 2026-08-29 | 3 task veri (id 0,1,2) | 3 | gemini-3.5-flash-lite | $0.0819 | $0.08 |
| 2026-08-29 | baseline 10 task sviluppo (id 0-9) | 10 | gemini-3.5-flash-lite | $0.2642 | $0.35 |
| 2026-08-30 | smoke test S4 (task 2, 7 + tentativi falliti per quota) | 2 | gemini-3.5-flash-lite | $0.0622 | $0.41 |
