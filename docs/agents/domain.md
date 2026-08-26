# Domain Docs

Come le skill di engineering devono consumare la documentazione di dominio di questo repo
durante l'esplorazione del codice.

## Prima di esplorare, leggere questi

- **`CONTEXT.md`** alla radice del repo.
- **`docs/adr/`** — leggere le ADR che toccano l'area su cui si sta per lavorare.

Se questi file non esistono ancora, **procedere in silenzio**. Non segnalarne l'assenza, non
proporre di crearli in anticipo. La skill `domain-modeling` li crea lazily quando termini o
decisioni vengono davvero risolti — ed è comunque fuori scope per questo progetto
(vedi `TASSONOMIA.md`, "Cosa NON si fa": over-engineering su un progetto di 20-30h).

## Struttura, single-context

```
/
├── CONTEXT.md
├── docs/adr/
│   └── 0001-....md
└── src/
```

Questo repo è single-context: un dominio (airline), un agente, una pipeline di eval. Nessun
segnale di monorepo (niente `pnpm-workspace.yaml`, nessun `packages/*`).

## Usare il vocabolario del glossario

Quando l'output nomina un concetto di dominio (titolo di issue, proposta di refactor, nome di
test), usare il termine come definito in `CONTEXT.md`, se esiste. Non derivare a sinonimi che
il glossario evita esplicitamente.

## Segnalare conflitti con le ADR

Se l'output contraddice una ADR esistente, segnalarlo esplicitamente invece di sovrascriverla
in silenzio.
