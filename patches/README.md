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

## Riapplicare dopo un clone nuovo

```bash
git -C tau2-bench apply patches/tau2-langfuse-tracing.patch
cd tau2-bench && uv sync
```

Serve anche che `tau2-bench/.env` contenga `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` e
`LANGFUSE_OTEL_HOST` (le chiavi non stanno in git: vanno riprese da Langfuse).

## Rigenerare la patch dopo altre modifiche

```bash
cd tau2-bench && git add -N src/tau2/utils/langfuse_tracing.py && git diff -- src/tau2 pyproject.toml > ../patches/tau2-langfuse-tracing.patch && git reset -q src/tau2/utils/langfuse_tracing.py
```

`uv.lock` è escluso di proposito: è enorme e conflittuale, e `uv sync` lo rigenera da
`pyproject.toml`.
