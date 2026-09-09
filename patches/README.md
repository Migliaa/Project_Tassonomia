# Patch su `tau2-bench`

`tau2-bench/` è un clone di terzi ed è **gitignorato**: non ha senso versionare qui migliaia
di file che non sono nostri, e tenerlo fuori rende evidente cosa abbiamo scritto noi e cosa no.

Il problema è che le nostre modifiche vivono dentro quella cartella, quindi sparirebbero se il
clone venisse rifatto o perso. Questa cartella risolve il problema: le modifiche stanno qui
come patch versionata, e la cartella clonata resta usa-e-getta.

## `tau2-infra.patch`

Osservabilità (S2) e limitatore di frequenza (S5). Si chiamava `tau2-langfuse-tracing.patch`
fino al 2026-09-01: rinominata quando ha smesso di riguardare solo Langfuse. Tocca cinque file:

| File | Modifica |
|---|---|
| `src/tau2/config.py` | `USE_LANGFUSE = True` |
| `src/tau2/utils/llm_utils.py` | callback `langfuse_otel` (successi **e** fallimenti); metadata di traccia per chiamata, con `generation_name` dal `call_name`; **limitatore RPM** (vedi sotto) |
| `src/tau2/utils/langfuse_tracing.py` | **nuovo** — uno span per simulazione, nome dalla `purpose` del task, reward come score |
| `src/tau2/runner/batch.py` | apre lo span attorno alla simulazione e registra il reward |
| `pyproject.toml` | dipendenza `langfuse` |

### Il limitatore RPM

Il tier gratuito Gemini concede **15 richieste al minuto** per progetto e modello. Il pacing
fra un task e l'altro non basta: è **un singolo task** a superare il limite da solo, perché
agente e simulatore-utente si alternano senza pause. Misurato il 2026-09-01: fino a **18
chiamate in 24 secondi**, cioè 45 al minuto.

Il limitatore sta in `generate()`, che è l'unico punto attraversato sia dall'agente sia
dall'utente simulato, ed è a **finestra scorrevole**: aspetta solo quando le ultime chiamate
stanno davvero saturando il minuto, invece di rallentare anche le conversazioni brevi.
`TAU2_RPM_LIMIT=0` lo disattiva (chiavi a pagamento); il default è 13, non 15, per margine.

## `tau2-custom-agent.patch`

Il nostro agente (`CustomAgent`), nato in S3 e corretto in S5. Tocca due file:

| File | Modifica |
|---|---|
| `src/tau2/agent/custom_agent.py` | **nuovo** — l'agente: system prompt in sezioni XML, limite di turni, gestione degli errori dei tool, e (S5) le regole comportamentali nate dalla tassonomia (`docs/s5-correzioni.md`) |
| `src/tau2/registry.py` | registra `create_custom_agent` come agente `"custom_agent"` |

Questa patch è rimasta scoperta da S3 fino a S5: il file era nuovo (mai tracciato da git) e la
riga di registrazione era una modifica non catturata da nessuna patch. Senza di essa, un
riclone perdeva silenziosamente tutto il lavoro su `custom_agent.py` — non solo S5. Non è mai
successo perché nel frattempo non c'è stato un riclone, ma il rischio era reale.

## Riapplicare dopo un clone nuovo

```bash
git -C tau2-bench apply patches/tau2-infra.patch
git -C tau2-bench apply patches/tau2-custom-agent.patch
cd tau2-bench && uv sync
```

Serve anche che `tau2-bench/.env` contenga `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` e
`LANGFUSE_OTEL_HOST` (le chiavi non stanno in git: vanno riprese da Langfuse).

## Rigenerare le patch dopo altre modifiche

```bash
cd tau2-bench && git add -N src/tau2/utils/langfuse_tracing.py && git diff -- src/tau2/config.py src/tau2/runner/batch.py src/tau2/utils/langfuse_tracing.py src/tau2/utils/llm_utils.py pyproject.toml > ../patches/tau2-infra.patch && git reset -q src/tau2/utils/langfuse_tracing.py
```

I file sono elencati uno per uno di proposito. Il comando precedente diffava tutto `src/tau2`,
quindi da quando esiste `custom_agent.patch` avrebbe risucchiato dentro anche `registry.py`,
facendo fallire l'applicazione delle due patch in sequenza su un clone nuovo.

```bash
cd tau2-bench && git add -N src/tau2/agent/custom_agent.py && git diff -- src/tau2/agent/custom_agent.py src/tau2/registry.py > ../patches/tau2-custom-agent.patch && git reset -q src/tau2/agent/custom_agent.py
```

`uv.lock` è escluso di proposito: è enorme e conflittuale, e `uv sync` lo rigenera da
`pyproject.toml`.

## `tau2-user-simulator.patch`

Una riga aggiunta a `data/tau2/user_simulator/simulation_guidelines.md`.

**Non e' una modifica nostra: e' un backport.** La riga e' copiata *testualmente* da
`simulation_guidelines_voice.md:42`, dove Sierra l'ha gia' scritta contro questo esatto
fallimento — «Agreeing to an action is not the same as the action being completed». Nelle
linee guida testuali manca.

Perche' serviva: sui task 17 e 21 il cliente simulato dice "si" all'ultima conferma e chiude
la conversazione **nello stesso messaggio**, prima che l'agente possa eseguire l'azione. Il
punteggio di comunicazione resta 1.0 e quello di database va a 0.0: l'agente e' penalizzato
per un'azione che il simulatore non gli ha lasciato compiere. E' un artefatto dello strumento
di misura, non un errore dell'agente — nella realta' una UI impedisce di chiudere la sessione
mentre un'operazione confermata e' in corso.

**Vincolo di misura**: cambia lo strumento, quindi ogni numero prodotto con questa patch
attiva e' confrontabile solo con altri numeri prodotti con la patch attiva. Il baseline va
rigirato nelle stesse condizioni, e la cosa va dichiarata nel report (precedente: la
submission Anthropic `claude-sonnet-4-5_anthropic_2025-10-02` sulla leaderboard ufficiale fa
la stessa cosa e la dichiara).

**Non attiva nei numeri pubblicati**: dopo la sonda `s12` (v5 senza backport sui task 17, 21,
33, per isolare le due correzioni) questa patch e' stata rimossa dal clone di lavoro e non era
applicata in nessuno dei run che contano per il risultato finale — ne' i quattro trial v6
(`s15`-`s18`) sottomessi alla classifica, ne' i baseline con cui sono confrontati. Resta qui
solo come contributo documentato (vedi README principale e issue tracker), non come parte
della submission.
