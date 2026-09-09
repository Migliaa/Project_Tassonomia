# Istruzioni per l'implementazione sul sito

Contenuto approvato. Da qui non cambia più il testo: se serve una modifica, passa da Andrea.

## Cosa c'è in questa cartella

| file | |
|---|---|
| `report.md` | **il testo**, nell'ordine in cui va pubblicato |
| `fig1…fig6`, `fig-bug` (`.svg`) | le figure, una per passo |
| `screenshots/` | due catture da Langfuse, in PNG |
| `preview.html` | come si legge il tutto — **solo riferimento, non è il design** |

## Struttura della pagina

Una pagina sola, in sette blocchi nell'ordine di `report.md`:

1. **Sintesi** — 85 parole. Va in apertura, prima dei passi, ed è l'unico blocco senza figura.
   È il testo che deve reggere da solo se qualcuno legge solo quello.
2. **Sei passi numerati**, ciascuno con titolo, testo e figura affiancata.
3. **Approfondimento sul difetto del benchmark** — separato dai sei passi: una pagina a sé, o
   una sezione chiaramente staccata. Dal passo 3 parte un rimando.

## Figure

Ogni passo indica la propria figura in cima al blocco (`**Figura**: nome-file.svg`). Due passi
ne hanno due:

- **Passo 3**: la cattura Langfuse con `reward: 0.00` **e** `fig3-famiglie.svg`
- **Passo 6**: `fig6-risultato.svg` **e** la cattura del dataset con le dieci esecuzioni

Gli SVG sono vettoriali: scalali liberamente, non convertirli in immagini. Le loro tinte sono
provvisorie — **vanno riportate alla palette del sito**. La riga `**Figura**: …` è un'indicazione
per te, non testo da pubblicare.

Le due catture PNG stanno in `screenshots/`, con il nome che riporta data e ora:

- `…185406.png` — la tabella delle esecuzioni a confronto (passo 6)
- `…190748.png` — la traccia di una conversazione fallita (passo 3)

## Testo

Il markdown è già impaginato: i grassetti sono voluti, le virgolette basse «così» sono una scelta
tipografica, il corsivo marca le citazioni dalle conversazioni. I conteggi in fondo a ogni blocco
(`*(157 parole)*`) servivano alla stesura: **non vanno pubblicati**.

Due link vanno resi cliccabili e aperti in una scheda nuova:

- `issue #514` → <https://github.com/sierra-research/tau2-bench/issues/514>
- `#325` → <https://github.com/sierra-research/tau2-bench/issues/325>

## Se serve un titolo per la voce di menu

**«Migliorare un agente AI cambiando solo il prompt»**, oppure la forma breve
**«τ²-bench: un agente, sei versioni»**. Il carattere τ è una tau greca: se il font del sito non
la supporta, scrivi «tau2-bench».
