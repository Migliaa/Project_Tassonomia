# Patch su `tau2-bench`

`tau2-bench/` è un clone di terzi ed è **gitignorato**: non ha senso versionare qui migliaia
di file che non sono nostri, e tenerlo fuori rende evidente cosa abbiamo scritto noi e cosa no.

Il problema è che le nostre modifiche vivono dentro quella cartella, quindi sparirebbero se il
clone venisse rifatto o perso. Questa cartella risolve il problema: le modifiche stanno qui
come patch versionata, e la cartella clonata resta usa-e-getta.

## `tau2-langfuse-tracing.patch`

Tutto ciò che serve per l'osservabilità di S2. Tocca cinque file:

| File | Modifica |
|---|---|
| `src/tau2/config.py` | `USE_LANGFUSE = True` |
| `src/tau2/utils/llm_utils.py` | callback `langfuse_otel` (successi **e** fallimenti); metadata di traccia per chiamata, con `generation_name` dal `call_name` |
| `src/tau2/utils/langfuse_tracing.py` | **nuovo** — uno span per simulazione, nome dalla `purpose` del task, reward come score |
| `src/tau2/runner/batch.py` | apre lo span attorno alla simulazione e registra il reward |
| `pyproject.toml` | dipendenza `langfuse` |

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
git -C tau2-bench apply patches/tau2-langfuse-tracing.patch
git -C tau2-bench apply patches/tau2-custom-agent.patch
cd tau2-bench && uv sync
```

Serve anche che `tau2-bench/.env` contenga `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` e
`LANGFUSE_OTEL_HOST` (le chiavi non stanno in git: vanno riprese da Langfuse).

## Rigenerare le patch dopo altre modifiche

```bash
cd tau2-bench && git add -N src/tau2/utils/langfuse_tracing.py && git diff -- src/tau2 pyproject.toml > ../patches/tau2-langfuse-tracing.patch && git reset -q src/tau2/utils/langfuse_tracing.py
```

```bash
cd tau2-bench && git add -N src/tau2/agent/custom_agent.py && git diff -- src/tau2/agent/custom_agent.py src/tau2/registry.py > ../patches/tau2-custom-agent.patch && git reset -q src/tau2/agent/custom_agent.py
```

`uv.lock` è escluso di proposito: è enorme e conflittuale, e `uv sync` lo rigenera da
`pyproject.toml`.
