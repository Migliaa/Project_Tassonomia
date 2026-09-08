# Screenshot da catturare su Langfuse

Non allegati come immagini: catturarli a schermo pieno dà una risoluzione molto migliore di
quella ottenibile in automatico. Serve essere loggati con l'account del progetto.

**Impostazione comune**: finestra massimizzata, tema scuro (com'è di default), e in alto a destra
il selettore del periodo su **«Past 30 days»** — altrimenti la lista risulta vuota, perché i run
sono del 5 settembre.

---

## 1. Traccia — lo scambio di messaggi *(step 3 del report)*

**È lo screenshot più importante**: mostra che ogni singola conversazione è ispezionabile.

```
https://cloud.langfuse.com/project/cmtefvd6j05kqad0i158liz8k/traces/708da1f15bcd8f49c35167e1d3a1f83a
```

Una volta aperta, cliccare nell'albero a sinistra su una riga **`user_simulator_response`** o
**`custom_agent_response`**: il pannello di destra mostra il messaggio in ingresso e la risposta.

Cosa deve restare visibile nell'inquadratura:
- il titolo della traccia e il punteggio **`reward: 1.00`** in alto a sinistra
- l'albero delle chiamate con costo e token per ciascuna
- le etichette **`gemini-3.5-flash-lite`**, **`temperature: 0`**, **`seed`**
- il blocco **User / Assistant** con lo scambio di battute

Il dettaglio della temperatura a zero è quello che rende credibile il discorso sulla varianza
nello step 6: stesso prompt, campionamento deterministico, risultati diversi.

---

## 2. Il dataset di confronto *(opzionale, step 6)*

Mostra le dieci versioni misurate sugli stessi 50 task.

```
https://cloud.langfuse.com/project/cmtefvd6j05kqad0i158liz8k/datasets/cmtj7uyem05uiad0ckmuw4s97/experiments
```

Scorrere la tabella orizzontalmente fino alla colonna **`# reward (api)`**: la colonna del nome
resta fissa, quindi nome e punteggio si vedono insieme. I valori devono leggersi
`0.6800` per `baseline - llm_agent` e `0.8200 / 0.7400 / 0.8000 / 0.8600` per i quattro trial
della v6.

**Attenzione, due trappole:**

1. La tabella contiene anche righe storiche di esperimenti più vecchi, che non si possono
   cancellare. Inquadrare solo le prime dieci righe, quelle con i nomi puliti.
2. **Non usare la vista «Compare»** per uno screenshot con dei numeri: lì le medie in cima sono
   calcolate sulla pagina visibile, non sull'intero run, e mostrerebbero valori che contraddicono
   il report.
