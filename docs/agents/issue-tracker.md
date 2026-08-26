# Issue tracker: GitHub

Issues e spec per questo repo vivono come GitHub issue. Usare la CLI `gh` per tutte le operazioni.

> `gh` non è ancora installato su questa macchina (verificato 2026-08-26). Va installato
> (https://cli.github.com) e autenticato (`gh auth login`) prima che `to-tickets`/`to-spec`
> possano usarlo. Fino ad allora, queste convenzioni restano documentate ma inutilizzabili.

Repo: https://github.com/Migliaa/Project_Tassonomia

## Convenzioni

- **Creare una issue**: `gh issue create --title "..." --body "..."`. Heredoc per corpi multi-riga.
- **Leggere una issue**: `gh issue view <number> --comments`, filtrando commenti con `jq` e recuperando anche le label.
- **Elencare issue**: `gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'` con `--label`/`--state` appropriati.
- **Commentare**: `gh issue comment <number> --body "..."`
- **Applicare / rimuovere label**: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **Chiudere**: `gh issue close <number> --comment "..."`

Il repo si inferisce da `git remote -v` — `gh` lo fa automaticamente dentro un clone.

## Pull request come superficie di triage

**PR come superficie di richiesta: no.** Progetto solo, nessuna PR esterna prevista.

## Quando una skill dice "pubblica sull'issue tracker"

Crea una issue GitHub.

## Quando una skill dice "recupera il ticket rilevante"

`gh issue view <number> --comments`.

## `triage` e `wayfinder`: non usati in questo progetto

Per decisione del piano operativo (`TASSONOMIA.md`, sezione "Cosa NON si fa"): `triage` è solo
per issue non create da te, e i ticket di `to-tickets` sono già pronti; `wayfinder` è escluso
esplicitamente per feature ben delimitate. Le convenzioni di wayfinding non sono documentate qui.
