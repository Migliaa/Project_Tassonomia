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

Nota: l'API REST di lettura di Langfuse risponde **504** da questa macchina (problema loro,
non di configurazione — le scritture passano e `auth_check()` è verde). La verifica delle
tracce va fatta dalla UI.

Nota sui costi: il tier gratuito non addebita denaro (lo $0.69 che Langfuse mostra è un costo
teorico calcolato a listino), ma la quota **RPD consumata è reale** — ed è quella la valuta
vera di questo progetto.

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

## Registro spesa API (tetto €20)

| Data | Run | Task | Modello | Costo | Totale progressivo |
|---|---|---|---|---|---|
| 2026-08-29 | test isolato tool calling (5 prompt) | 5 | gemini-3.5-flash-lite | ~$0 (tier gratuito) | $0.00 |
| 2026-08-29 | 3 task veri (id 0,1,2) | 3 | gemini-3.5-flash-lite | $0.0819 | $0.08 |
| 2026-08-29 | baseline 10 task sviluppo (id 0-9) | 10 | gemini-3.5-flash-lite | $0.2642 | $0.35 |
