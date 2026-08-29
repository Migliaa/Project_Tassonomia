# tassonomia

Vedi `TASSONOMIA.md` (fuori da questo repo, in `Progetti/Personale/progetti/`) per il piano
operativo completo: sprint, decisioni tecniche, link. Le decisioni lì sono prese e motivate;
non riaprirle.

## Esecuzione dei run

- `tau2-bench/` è un clone di terzi, gitignorato. **Le nostre modifiche stanno in
  `patches/`**, non lì: se le tocchi, rigenera la patch (vedi `patches/README.md`),
  altrimenti si perdono al primo riclone.
- Anteporre sempre `PYTHONIOENCODING=utf-8 PYTHONUTF8=1` ai comandi `tau2 run`
  (altrimenti crash di encoding su Windows).
- **`--max-retries 1`.** Quel parametro rigioca il *task intero*, non la singola chiamata:
  alzarlo contro un rate limit moltiplica i token sprecati. I 429 li assorbe il retry
  interno di LiteLLM. Dopo un fallimento da rate limit si aspetta, non si rilancia.
- Ogni run lungo va lanciato con un `timeout` esplicito.
- Il diario (`DIARIO.md`) lo committa l'agente, non l'utente.

## Agent skills

### Issue tracker

GitHub (repo: https://github.com/Migliaa/Project_Tassonomia). Vedi `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `CONTEXT.md` + `docs/adr/` alla radice, creati lazily quando servono. Vedi `docs/agents/domain.md`.
