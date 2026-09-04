# Etichette di riferimento — set di misura

**Congelate il 2026-09-04, prima di scrivere una riga del prompt del giudice.** Da qui in avanti
non si toccano: se il giudice dissente, si corregge il giudice.

## Chi ha etichettato, e cosa questo significa

Le ha prodotte **un modello di frontiera** (io), leggendo la vista ridotta di `da-etichettare.md` —
la stessa che ricevera' il giudice. **Non e' annotazione umana**, e nel report va scritto cosi'.

Andrea ha deciso consapevolmente di non etichettare a mano: il progetto e' un esercizio di
portfolio a tempo, e leggere e classificare tracce e' la parte che costa piu' ore e ne insegna meno.
La perdita e' reale e va dichiarata: senza un annotatore umano indipendente **non stiamo validando
il giudice contro il giudizio umano**.

Quello che resta misurabile e' pero' una domanda industriale vera, e non un ripiego:

> **Un modello piccolo ed economico riproduce la diagnosi di un modello grande?**

E' esattamente cio' che si vuole sapere prima di mettere un classificatore su decine di migliaia di
tracce in produzione, dove il modello grande costa troppo per girare su tutto. Il giudice girera'
su `gemini-3.5-flash-lite` — lo stesso motore dell'agente e del simulatore — mentre queste etichette
vengono da un modello molto piu' capace. Il confronto e' quindi fra due classificatori di taglia
diversa, ed e' informativo purche' lo si chiami col suo nome.

## Le etichette

| voce | etichetta | perche' |
|---|---|---|
| **T01** | `F0` | Nessuna scrittura attesa, nessuna eseguita, database e comunicazione entrambi a 1.0. Il trasferimento c'e' stato ed era la mossa corretta: il cliente chiedeva una spiegazione su un ritardo, fuori da cio' che gli strumenti possono fare. |
| **T02** | `F3` | L'azione giusta (`book_reservation`) sulla rotta e sul volo giusti — HAT271, ORD→PHL, 2024-05-26 — ma il database non combacia. La divergenza e' negli argomenti, non nel bersaglio: dal messaggio finale si vede un secondo passeggero (Kevin Smith) che la richiesta iniziale non nominava. |
| **T03** | `F0` | Come T01: nessuna scrittura attesa, nessuna eseguita, entrambi i punteggi a 1.0. Il trasferimento e' la risposta corretta a un reclamo per ritardo. |
| **T04** | `F6` | Tre scritture attese, due eseguite. Manca `update_reservation_passengers`. Niente ha impedito la terza: la conversazione prosegue normale e l'agente chiude annunciando il successo, senza accorgersi di aver saltato un pezzo. |
| **T05** | `F10` | Il benchmark non prevede **nessuna** scrittura su questa prenotazione: il task chiedeva di rifiutare. L'agente ha invece eseguito due modifiche, portando la cabina a business. E' la famiglia che questo pilota ha fatto emergere. |
| **T06** | `F2` | L'agente propone il trasferimento **mentre** una richiesta che poteva servire e' ancora aperta: nello stesso messaggio chiede conferma per l'upgrade di `M20IZO`. Il cliente accetta entrambe le cose, il trasferimento chiude l'episodio, e l'upgrade non viene mai eseguito. |

## Un caso ambiguo, dichiarato prima di misurare

**T06 e' contendibile fra `F2`, `F1` e `F8`**, e la cosa va scritta adesso e non dopo aver visto
cosa risponde il giudice.

- `F1` perche' il cliente approva e chiude nello stesso messaggio;
- `F8` perche' a terminare e' `###TRANSFER###`, un'uscita del simulatore;
- `F2` — la scelta — perche' applicando la regola della **causa prossima**, la prima cosa andata
  storta e' che l'agente ha offerto il trasferimento mentre restava qualcosa da servire. Senza
  quell'offerta la conversazione sarebbe proseguita e l'upgrade sarebbe stato eseguito.

Se il giudice risponde `F1` o `F8` su T06, **non e' un errore secco**: e' il segnale che la regola
della causa prossima non e' abbastanza esplicita nelle definizioni. In quel caso si corregge la
definizione della famiglia, mai l'etichetta.

## Distribuzione, e cosa implica per la misura

Sei voci: `F0` ×2, `F2`, `F3`, `F6`, `F10`. Quattro famiglie diverse su quattro fallimenti — cioe'
**nessuna classe maggioritaria**.

E' un bene per l'interpretazione (un giudice degenere che risponde sempre la stessa cosa prende
al massimo 2 su 6) ma rende il kappa molto instabile: con sei voci ogni singolo disaccordo sposta
il valore di circa 0.2. **Il numero va riportato con la dimensione del campione accanto, sempre**,
e non va confrontato con i kappa della letteratura, che si calcolano su centinaia di voci.
