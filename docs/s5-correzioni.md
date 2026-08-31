# S5 — Specifica delle correzioni a `custom_agent.py`

Documento vivo. Ogni famiglia della tassonomia S4 viene analizzata qui e, se correggibile, la
correzione viene scritta in forma **applicabile alla lettera** — testo esatto, posizione esatta —
in modo che l'implementazione sia una passata meccanica sola alla fine, non sei modifiche
successive allo stesso file.

Vincoli di metodo: ogni regola deve passare i nove controlli di
[`docs/regole-comportamentali-agenti.md`](regole-comportamentali-agenti.md) §4. La diagnosi delle
famiglie sta in `DIARIO.md` (sezione S4).

**Regola operativa per chi implementa**: `tau2-bench/` è gitignorato. Dopo aver applicato le
modifiche, **rigenerare la patch in `patches/`** (vedi `patches/README.md`), altrimenti il lavoro
si perde al primo riclone.

## Stato

| Famiglia | Titolo | Stato |
|---|---|---|
| 1 | Disambiguazione silenziosa | **approvata, pronta da applicare** |
| 2 | Formattazione numerica non USD | **approvata, pronta da applicare** |
| 3 | Lo strumento risponde correttamente ma non permette l'operazione richiesta | **approvata** — regola fusa con la 6 |
| 4 | L'utente chiude la chiamata nello stesso turno in cui conferma | **non correggibile — solo monitoraggio** |
| 5 | Usa un metodo di pagamento non specificato esplicitamente dal cliente | **approvata, pronta da applicare** |
| 6 | Richiesta multi-elemento con esiti misti | **approvata** — regola fusa con la 3 |

**Decisione sul dataset di verifica** (presa il 2026-08-31): il dataset `airline-s4-round2` resta
a 10 item, senza aggiungere i task 4, 8 e 43 come canary supplementari, pur sapendo che sarebbero
i più esposti alla correzione della famiglia 2. È un compromesso di budget su un progetto di
esercizio, non la pratica corretta in produzione, e va dichiarato come tale nel report.

---

## Famiglia 2 — Formattazione numerica non USD

### Diagnosi rivista

La diagnosi originale di S4 ("importo comunicato in formato europeo, il controllo cerca la stringa
esatta e non la trova") è corretta ma superficiale. Verificando il messaggio per intero è emersa
la causa vera.

Task 18, messaggio finale dell'agente:

> "Ho completato con successo il passaggio di tutte e 5 le tue prenotazioni dalla classe business
> alla classe economy… In totale, hai risparmiato **$23.553**"

**L'agente risponde in italiano a un cliente che scrive in inglese.** Non è isolato:

| Agente | Task con almeno una risposta in italiano |
|---|---|
| `custom_agent` (nostro) | **10 su 20**: 4, 7, 8, 18, 23, 37, 41, 42, 43, 44 |
| `llm_agent` (baseline) | **0** su 49 messaggi assistant |

La causa è nostra: `POLICY_HIGHLIGHTS`, introdotto in S3, è **scritto in italiano** ed è l'unico
blocco non inglese del system prompt (sta tra `<instructions>` e `<policy>`, entrambi in inglese).
Il modello ne specchia la lingua. Il baseline, che quel blocco non ha, non lo fa mai.

Il formato del numero è il sintomo, non la malattia: `$23.553` è il separatore delle migliaia
italiano, coerente col resto del messaggio.

Meccanismo del controllo verificato in
`tau2-bench/src/tau2/evaluator/evaluator_communicate.py:70`: il match è letterale, dopo
`.replace(",", "")` sul messaggio dell'agente. Quindi `$23,553` → `23553` ✓, `$23553` ✓, ma
`$23.553` ✗ perché i punti non vengono rimossi. Su questo task `DB` valeva 1.0 (tutte le azioni
corrette): il reward è andato a zero solo sul separatore.

**Da dire nel report**: che il grader tolga le virgole ma non i punti è un artefatto del
benchmark, e parte del guadagno su questo task viene da lì. La regola però sta in piedi per conto
suo — compagnia aerea statunitense, importi in USD, cliente che scrive in inglese — quindi non è
scritta per compiacere il grader. La distinzione va dichiarata, non lasciata implicita.

### Correzione A — tradurre `POLICY_HIGHLIGHTS` in inglese

Non è una regola comportamentale: è la rimozione della causa. Checklist punto 6 (se il problema è
meccanico, si risolve nel codice e non chiedendo al modello di compensare).

Sostituire il valore di `POLICY_HIGHLIGHTS` (`custom_agent.py:44-55`) con questa traduzione
fedele — **stesse cinque regole, stesso ordine, nessuna aggiunta**:

```python
POLICY_HIGHLIGHTS = """
Before proceeding, keep these in mind in particular:
- Before any action that MODIFIES a reservation (booking, changing flights, baggage,
  cabin, passenger details), you must obtain an explicit confirmation ("yes") from the user.
- Each turn is either a message to the user or a tool call. Never both, never neither.
- Extra compensation is offered ONLY if the user is a silver/gold member, or has travel
  insurance, or is flying business. Never offer it on your own initiative.
- If the request falls outside the scope of what you can do, transfer to a human agent
  instead of improvising.
- If a tool returns an error, re-read the customer's message and the policy to check
  whether the procedure was correct, before retrying.
""".strip()
```

Il commento italiano sopra la costante (`# S3, decisione 1: ...`) **resta invariato**: i commenti
sono per Andrea, il prompt è per il modello. Aggiungere in coda al commento esistente una riga che
spiega perché il testo è passato all'inglese, citando questa sezione.

### Correzione B — regola sul formato degli importi

Anche in inglese un modello può scrivere `23.553`. Nuova costante, da definire dopo
`POLICY_HIGHLIGHTS`:

```python
# S5, famiglia 2: sezione separata per le convenzioni di output verso il cliente.
# Va in fondo al system prompt, dopo <policy>, non in mezzo: le regole "decadono con la
# distanza" (vedi docs/regole-comportamentali-agenti.md, 2.8) e questa serve proprio nel
# momento in cui il modello genera il messaggio, quindi sta il piu' vicino possibile.
OUTPUT_CONVENTIONS = """
1. Reply in the language the customer is writing in.
2. Write every monetary amount in US dollar format: a comma every three digits, a period
   only before cents. Example: $1,250 and $1,250.75 - never $1.250.
""".strip()
```

E in `SYSTEM_PROMPT` (`custom_agent.py:80-90`), aggiungere una sezione **in fondo**, dopo
`</policy>`:

```
<output_conventions>
{output_conventions}
</output_conventions>
```

più il corrispondente `output_conventions=OUTPUT_CONVENTIONS` nella `.format(...)` a
`custom_agent.py:129-132`.

### Verifica contro la checklist

| # | Controllo | Esito |
|---|---|---|
| 1 | Trigger osservabile prima dell'azione | ✓ "sto per comunicare un importo" è riconoscibile mentre il modello scrive |
| 2 | Azione, non divieto | ✓ prescrive il formato; il "never" chiude l'esempio, non è la regola |
| 3 | Verificabile in un turno | ✓ si legge il messaggio e si risponde sì/no |
| 4 | Nessun conflitto/duplicato | ✓ nessuna delle 5 regole esistenti parla di lingua o formato |
| 5 | Altitudine giusta | ✓ nessun id, nessun task, nessun importo del caso osservato |
| 6 | Prompt o codice? | ✓ la lingua si risolve nel codice (A), il formato resta prompt (vedi sotto) |
| 7 | Passi numerati | ✓ |
| 8 | Esempio canonico | ✓ la regola descrive una forma, quindi l'esempio serve — ma con una cifra neutra ($1,250), non con l'importo del task 18 |
| 9 | Costo di regressione | dichiarato sotto |

**Alternativa considerata e scartata**: normalizzare i numeri nel codice con una regex sul
messaggio in uscita. Più deterministico, ma riscrivere in silenzio ciò che l'agente ha detto è un
anti-pattern: la traccia non corrisponde più a quello che il modello ha generato, quindi
l'osservabilità che stiamo costruendo in questo stesso progetto mentirebbe. In più non coprirebbe
un importo scritto a lettere. Scelta: regola di prompt con esempio.

**Costo di regressione**: cinque task che oggi **passano** (4, 8, 41, 42, 43) contengono risposte
in italiano — passano nonostante la lingua sbagliata. Cambiare la lingua del prompt cambia la
distribuzione di generazione anche per loro. Due dei cinque (41, 42) sono già canary nel dataset;
4, 8 e 43 no, per la decisione di budget dichiarata sopra.

---

## Decisione strutturale, valida per tutte le famiglie

Tutte le regole comportamentali nate da S5 vanno in **un'unica sezione nuova**
`<handling_customer_requests>`, e le convenzioni di output nella sezione
`<output_conventions>` della famiglia 2. Entrambe **in fondo al `SYSTEM_PROMPT`, dopo
`</policy>`**, non in mezzo.

Motivo: le regole "decadono con la distanza" (`docs/regole-comportamentali-agenti.md` §2.8) —
un documento di regole non funziona come autorità permanente ma come una fonte in più, la cui
influenza cala man mano che ci si allontana. Queste regole servono nel momento esatto in cui il
modello genera il turno, quindi stanno il più vicino possibile al punto di generazione.
`POLICY_HIGHLIGHTS` resta dov'è: è un riassunto della policy del dominio, non una nostra regola,
e mescolarci dentro le correzioni renderebbe illeggibile la distinzione tra le due cose.

---

## Famiglia 1 — Disambiguazione silenziosa

### Diagnosi rivista

Nel task 7, al turno 11, il cliente chiede due cose in un solo messaggio:

> "Upgrade XEHM4B to business first using my credit card ending in 2135, then cancel it.
> **Also, do I have any other upcoming flights, and what is the total cost for those?**"

Il nostro agente recupera i dettagli di tutte e quattro le altre prenotazioni (turni 14-21) —
quindi la domanda l'ha capita e i dati li ha — poi chiede conferma per l'upgrade (turno 22),
esegue, e chiude i saluti (turno 28) **senza mai comunicare il costo**. `DB: 1.0` (cinque azioni
su cinque corrette), `COMMUNICATE: 0.0` sull'informazione attesa `1628`.

Quindi in quella traccia l'agente **non** ha scelto l'interpretazione sbagliata: ha lasciato
cadere metà richiesta.

**L'ambiguità però esiste, ed è dimostrata dal baseline.** In due run indipendenti `llm_agent`
risponde, e risponde `$708`:

> "You have two other upcoming reservations: 1. **7WPL39** ($402) 2. **3EMQJ6** ($306).
> The total cost for these upcoming reservations is **$708**."

Il ground truth è `1628`. Ricostruzione da `db.json` (data di simulazione fissata al 2024-05-15
da `tools.py:102`, quindi "upcoming" sono quattro prenotazioni su sei):

| Prenotazione | Calcolo | Totale |
|---|---|---|
| 7WPL39 | 171 × 2 pax + 30 × 2 assicurazione | $402 |
| 3EMQJ6 | 306 × 1 pax | $306 |
| XEHM4B | 148 × 2 pax | $296 |
| 59XX6W | 282 × 2 pax + 30 × 2 assicurazione | $624 |
| | | **$1.628** |

I primi due valori coincidono con quelli calcolati indipendentemente dal baseline, il che verifica
il modello di calcolo. `$1.628` = tutte e quattro le prenotazioni imminenti, **incluse** le due
appena cancellate; `$708` = solo le altre due. Cioè il benchmark legge *other* come "quelle che
non hai ancora visto", il modello lo legge come "diverse da quelle che stiamo cancellando" — una
lettura in inglese quantomeno altrettanto difendibile, data tre volte su tre.

**Conseguenza per il metodo**: la famiglia 1 è confermata, ma non dalla traccia su cui era stata
definita. È confermata dalle tracce del baseline. La traccia del nostro agente mostra un secondo
comportamento, distinto.

### Le due clausole

Andrea ha giudicato che il secondo comportamento appartiene alla stessa famiglia: entrambi
riguardano la parte *informativa* di una richiesta, che non viene servita — una volta perché
abbandonata, una volta perché risolta arbitrariamente. La regola quindi ha due clausole, non due
sezioni.

Nuova costante, da definire dopo `OUTPUT_CONVENTIONS`:

```python
# S5, famiglia 1: sezione che raccogliera' tutte le regole comportamentali nate dalla
# tassonomia. Va in fondo al system prompt, dopo <policy> - stesso motivo di
# OUTPUT_CONVENTIONS (le regole decadono con la distanza).
HANDLING_CUSTOMER_REQUESTS = """
1. When the customer's message contains more than one request, serve all of them before
   closing the conversation. If one request is an action and another is a question, answer
   the question in the same message in which you ask for confirmation of the action.
2. When a question uses a scope word that could reasonably be read in more than one way
   (for example "other", "the rest", "remaining", "all"), do not choose one reading
   silently. State which reading your answer refers to, and give the answer for the other
   reading as well, in the same message.
""".strip()
```

E in `SYSTEM_PROMPT`, dopo `</policy>` e prima o dopo `<output_conventions>`:

```
<handling_customer_requests>
{handling_customer_requests}
</handling_customer_requests>
```

più il corrispondente argomento nella `.format(...)`.

### Note sulle scelte

**Nessun esempio.** Prima versione della clausola 2 conteneva un esempio costruito con i numeri
del task 7 ($402, $306, $708, $1.628): overfitting travestito da buona pratica, e violazione del
punto 5 della checklist mentre si dichiarava di soddisfare il punto 8. Rimosso. La regola si
esprime bene a parole, quindi l'esempio sarebbe stato solo token in più. Il criterio generale è
stato riscritto nella checklist (punto 8): esempio solo per le forme difficili da dire a parole,
e mai costruito con i dati del caso che si sta correggendo.

**La clausola 2 non chiede all'agente di indovinare**, gli chiede di non scegliere. Coprendo
entrambe le letture l'agente è corretto qualunque sia quella attesa, e per il cliente è servizio
migliore, non un espediente per passare il controllo.

### Verifica contro la checklist

| # | Controllo | Esito |
|---|---|---|
| 1 | Trigger prima dell'azione | ✓ entrambi i trigger sono nel messaggio del cliente: più richieste, oppure una parola di scopo |
| 2 | Azione, non divieto | ✓ "servile tutte", "dichiara la lettura e dai anche l'altra" |
| 3 | Verificabile in un turno | ✓ o le richieste sono servite tutte e le due cifre ci sono, o no |
| 4 | Conflitti/duplicati | ✓ nessuna regola esistente parla di ambiguità o di richieste multiple; la clausola 1 rinvia alla regola di conferma esplicita già presente in `POLICY_HIGHLIGHTS` senza contraddirla |
| 5 | Altitudine | ✓ nessun id, nessun importo, nessun task; generalizzata alle parole di scopo e alle richieste multiple |
| 6 | Prompt o codice? | ✓ prompt: riconoscere un'ambiguità linguistica non è meccanico |
| 7 | Passi numerati | ✓ |
| 8 | Esempio | ✓ assente per scelta motivata (vedi sopra) |
| 9 | Costo di regressione | verbosità: l'agente potrebbe iniziare a qualificare ogni risposta. Il trigger della clausola 2 è ristretto alle parole di scopo apposta. La clausola 1 spinge verso messaggi più lunghi che mescolano risposta e richiesta di conferma: da controllare che non finisca per confondere il simulatore-utente nei task che oggi passano |

### Evidenza della clausola 1

Una sola osservazione (task 7). Va detto nel report: è l'unica regola di S5 scritta su un caso
singolo, ed è stata inclusa perché senza di essa la correzione della famiglia 1 quasi certamente
non recupera il task 7 — l'agente non arriva nemmeno al punto di scegliere una lettura.

---

## Famiglie 3 e 6 — una sola procedura

Diagnosi separate (restano due famiglie distinte nella tassonomia S4), **una sola regola**: le due
situazioni condividono la stessa precondizione — *qualcosa nella richiesta non si può fare* — e
differiscono solo in cosa resta servibile. Due clausole separate avrebbero duplicato il trigger;
una frase sola le avrebbe schiacciate in una regola troppo larga per essere azionabile in
entrambi i casi.

### Famiglia 3 — l'evidenza (task 23)

Turni 19-24. Il cliente chiede di pagare con certificati, poi gift card, poi Mastercard.
L'agente calcola e poi chiama `transfer_to_human_agents`, con questa motivazione:

> "the user wants to […] split the payment across travel certificates, gift cards, and a credit
> card, which requires multiple payment methods not supported by the single-payment reservation
> update"

**Il ragionamento è fattualmente corretto**: `policy.md:131` impone "a single gift card or credit
card" per un cambio volo, quindi tre certificati su un aggiornamento in place sono davvero
impossibili. L'errore non è nei fatti, è nella conclusione: ha trattato *"il percorso che ho
scelto è bloccato"* come *"la richiesta è fuori dal mio raggio d'azione"*. Il percorso alternativo
(cancellare e riprenotare) era quello atteso dal ground truth, e lo scenario del task prevede
esplicitamente che sia **il cliente** a proporre l'idea delle tre prenotazioni separate: l'agente
non doveva inventarla, doveva solo non chiudere la conversazione prima che il cliente parlasse.

**La causa prossima è una nostra regola di S3.** Confronto:

| | Testo |
|---|---|
| `policy.md:15` | "You should transfer the user to a human agent **if and only if** the request cannot be handled within the scope of your actions." |
| `POLICY_HIGHLIGHTS` (nostro) | "Se la richiesta esce dallo scopo di quello che puoi fare, trasferisci a un umano **invece di improvvisare**." |

Riassumendo la policy abbiamo perso l'*if and only if* — la metà restrittiva, quella che vieta il
trasferimento negli altri casi — e aggiunto "invece di improvvisare", che scoraggia proprio il
comportamento richiesto qui. **La nostra sintesi ha reso la policy più propensa al trasferimento
dell'originale**, e l'agente ha seguito la nostra regola, non l'ha violata.

Insieme alla famiglia 2 (la lingua), sono due famiglie su tre in cui la causa prossima è una
correzione introdotta da noi in S3. Per il report questo vale più di qualche punto di reward:
correggere un agente introduce nuovi modi di fallire, e senza osservabilità non ce ne si accorge.

### Famiglia 6 — l'evidenza (task 44, poi 39)

Task 44, turno 41 — il cliente contesta la cancellazione e **nello stesso messaggio autorizza
esplicitamente e separatamente tre upgrade**:

> "regarding the cancellation of `S61CZX` […] Is there really no way to cancel it? As for the
> upgrades for `NM1VX1`, `KC18K6`, and `H8Q05L`, the total of $1,207 sounds fine to me.
> **Please go ahead and process those upgrades.**"

Turno 42: `transfer_to_human_agents` per l'intero blocco. Conferma esplicita in mano per tre
azioni di scrittura, zero eseguite. Il ground truth chiede esattamente quei tre upgrade e **zero**
cancellazioni (`nl_assertions`: "Agent does not cancel reservation S61CZX as the user is
healthy").

Task 39, stessa forma: sette prenotazioni da cancellare, l'agente le esamina tutte (turni 14-21),
ne trova alcune già volate e alcune non idonee, e trasferisce il blocco al turno 22. Ground truth:
cancellarne esattamente tre (8C8K4E, LU15PA, MSJ4OA) e nessun'altra.

In entrambi i casi `DB: 0.0` con `COMMUNICATE: 1.0`: l'agente aveva capito e comunicato tutto
correttamente, e non ha eseguito nulla.

### La correzione

**A — riparare la riga distorta**, dentro la traduzione in inglese già prevista dalla famiglia 2
(quindi nessuna riga in più nel prompt). Sostituire il quarto punto di `POLICY_HIGHLIGHTS` con:

```
- Transfer to a human agent only if no action available to you can serve the customer's
  goal. A blocked path is not the same as a request outside your scope.
```

**B — clausola 3 di `HANDLING_CUSTOMER_REQUESTS`**, come procedura numerata:

```
3. When part of the customer's request cannot be done, or the path you first tried is
   blocked:
   a. Identify which parts of the request the policy still allows you to serve, including
      through a different sequence of actions than the one you first tried.
   b. Carry out those parts, asking for explicit confirmation first where the policy
      requires it. If the customer has already confirmed them, carry them out now.
   c. Tell the customer plainly which part could not be done, and why.
   d. Transfer to a human agent only if step (a) leaves nothing you can serve.
```

**Perché "the policy still allows you to serve" e non "you can serve"**: nel task 39 il cliente
insiste per cancellare anche le prenotazioni non idonee ("Even if the agent says you will not
receive a refund for some of them, you want to proceed anyway"), e il ground truth ne vuole
cancellate tre su sette. Una regola che spinge a servire *di più* senza ancorarsi all'idoneità da
policy farebbe fallire il task nella direzione opposta. Il vincolo è nella scelta delle parole,
non è un dettaglio di stile.

### Verifica contro la checklist

| # | Controllo | Esito |
|---|---|---|
| 1 | Trigger prima dell'azione | ✓ forte: "una parte della richiesta non si può fare" è noto prima di decidere cosa fare, e il momento critico è una chiamata identificabile (`transfer_to_human_agents`) |
| 2 | Azione, non divieto | ✓ quattro azioni in sequenza; il "only if" del passo (d) chiude la procedura, non è la regola |
| 3 | Verificabile in un turno | ✓ prima del trasferimento c'è l'esecuzione della parte servibile e la spiegazione del resto, o non c'è |
| 4 | Conflitti/duplicati | ⚠️ **conflitto reale** con la regola esistente sul transfer, risolto fondendo (correzione A) e non aggiungendo. Sovrapposizione lieve con la clausola 1 (famiglia 1, "servi tutte le richieste"): triggers distinti — lì il fallimento è la dimenticanza, qui l'abbandono — quindi restano separate |
| 5 | Altitudine | ✓ nessun id, nessun certificato, nessun metodo di pagamento, nessun numero di task |
| 6 | Prompt o codice? | prompt per ora. **Alternativa considerata**: un gate nel codice che rifiuta la prima chiamata a `transfer_to_human_agents` e chiede di riconsiderare. Più deterministico, ma costa un turno, sporca la traccia con un rifiuto che non viene dall'ambiente reale e non impedisce di ritrasferire identico. Decisione (Andrea, 2026-08-31): prompt adesso, gate nel codice da riconsiderare solo se dopo il round 2 il trasferimento prematuro è ancora vivo |
| 7 | Passi numerati | ✓ è il motivo per cui è una procedura e non una frase |
| 8 | Esempio | non serve: la regola si dice a parole |
| 9 | Costo di regressione | rischio opposto e reale: un agente che non trasferisce mai e insiste su richieste davvero fuori scope, bruciando turni. Mitigato dal limite di 30 turni già forzato dal codice (S3, decisione 3). Secondo rischio: over-execution — l'agente che esegue anche le parti non idonee per compiacere un cliente insistente; è il motivo del vincolo lessicale del passo (a) |

### Copertura

Tre dei sette fallimenti (23, 39, 44) hanno questo meccanismo. È la regola con il rapporto
copertura/costo più alto di tutta S5.

---

## Famiglia 5 — Metodo di pagamento non specificato dal cliente

### Evidenza (task 37)

| Turno | Cosa succede |
|---|---|
| 14 | L'agente chiede conferma per l'upgrade di `M20IZO`. **Non chiede quale metodo di pagamento.** |
| 15 | Il cliente conferma: "Yes, I confirm that I want to upgrade M20IZO to business class." Nessuna carta nominata — lo scenario prevede la carta che finisce in 7334, ma il simulatore la nomina solo se gliela si chiede. |
| 16 | `update_reservation_flights` con `payment_id: "credit_card_4959530"`, pescata dal profilo. Atteso: `credit_card_9074831`. |

`DB: 0.0`, `COMMUNICATE: 1.0`. Il reward è andato a zero su un argomento che nessuno aveva
fornito. `policy.md:130-131` richiede che sia l'utente a fornire il metodo, e che il metodo sia
già nel profilo — l'agente ha rispettato la seconda metà e saltato la prima.

### La correzione

Clausola 4 di `HANDLING_CUSTOMER_REQUESTS`:

```
4. When an action requires you to supply a payment method, use only a method the customer
   has named in this conversation - the specific card, gift card, or certificate. If they
   have not named one, list the payment methods on their profile and ask which to use,
   before acting.
```

**Delimitazione del trigger, verificata nel codice.** In `src/tau2/domains/airline/tools.py`:
`cancel_reservation` (riga 339) non prende alcun argomento di pagamento, mentre `book_reservation`
(196), `update_reservation_baggages` (553) e `update_reservation_flights` (597) richiedono
`payment_methods`/`payment_id`. Quindi "when an action requires you to supply a payment method"
seleziona esattamente le tre operazioni giuste e **non** fa scattare la domanda prima di una
cancellazione, dove il rimborso va d'ufficio sul metodo originale. Senza questa delimitazione la
regola avrebbe generato domande inutili nei task che oggi passano — è il punto 9 della checklist
risolto nella formulazione invece che accettato come rischio.

**Perché tutti e tre i tipi di pagamento e non solo la carta di credito** (caso osservato): la
policy del dominio ne definisce tre, quindi generalizzare a tre è sostenuto dall'evidenza
documentale, non inventato. Generalizzare oltre — a "ogni informazione sensibile" — non lo
sarebbe: un caso solo non è un pattern. È la prima regola di metodo di S4 applicata alla lettera.

### Verifica contro la checklist

| # | Controllo | Esito |
|---|---|---|
| 1 | Trigger prima dell'azione | ✓ molto forte: "sto per chiamare un tool che richiede un `payment_id`" |
| 2 | Azione, non divieto | ✓ "usa solo un metodo nominato; se non c'è, elenca e chiedi" — nessun "non fare" |
| 3 | Verificabile in un turno | ✓ esiste o non esiste un messaggio del cliente che nomina quel metodo |
| 4 | Conflitti/duplicati | ✓ complementare, non sovrapposta, alla regola di conferma esplicita in `POLICY_HIGHLIGHTS`: quella riguarda l'assenso all'azione, questa un dato obbligatorio in input. Meccanismi diversi, come già stabilito in S4 tenendo separate le famiglie 1 e 5 |
| 5 | Altitudine | ✓ nessun id, nessuna carta, nessun task; generalizzata ai tre tipi di pagamento della policy e non oltre |
| 6 | Prompt o codice? | ✓ prompt, per una ragione verificata: un controllo di codice dovrebbe confrontare il `payment_id` in uscita con quanto detto dal cliente, ma il cliente dice "la carta che finisce in 7334", non `credit_card_9074831`. Servirebbe risalire dalle ultime quattro cifre, e per gift card e certificati non esiste un numero che il cliente pronunci. Non è meccanizzabile in modo affidabile |
| 7 | Passi numerati | ✓ |
| 8 | Esempio | non serve |
| 9 | Costo di regressione | risolto nella formulazione (vedi delimitazione del trigger). Rischio residuo: un turno in più di conversazione prima di ogni scrittura con pagamento, che avvicina il limite dei 30 turni nei task lunghi |

---

# Stato finale — tutto il testo da applicare

Questa sezione è il riepilogo operativo: chi implementa può lavorare **solo da qui**, le sezioni
precedenti sono la motivazione di ogni scelta. Cinque famiglie correggibili producono **tre
modifiche** a `custom_agent.py`, non sei: la 3 e la 6 condividono una procedura, e la 2 e la 3
condividono la riscrittura di `POLICY_HIGHLIGHTS`.

Le clausole sono ordinate per flusso di conversazione (capire la richiesta → raccogliere gli input
obbligatori → gestire ciò che è bloccato), non per numero di famiglia.

## Modifica 1 — `POLICY_HIGHLIGHTS` (righe 44-55): in inglese, con il quarto punto riparato

```python
POLICY_HIGHLIGHTS = """
Before proceeding, keep these in mind in particular:
- Before any action that MODIFIES a reservation (booking, changing flights, baggage,
  cabin, passenger details), you must obtain an explicit confirmation ("yes") from the user.
- Each turn is either a message to the user or a tool call. Never both, never neither.
- Extra compensation is offered ONLY if the user is a silver/gold member, or has travel
  insurance, or is flying business. Never offer it on your own initiative.
- Transfer to a human agent only if no action available to you can serve the customer's
  goal. A blocked path is not the same as a request outside your scope.
- If a tool returns an error, re-read the customer's message and the policy to check
  whether the procedure was correct, before retrying.
""".strip()
```

Il commento italiano sopra la costante resta; aggiungerci in coda una riga che spiega il passaggio
all'inglese (famiglia 2) e la riparazione del quarto punto (famiglia 3), con rinvio a questo file.

## Modifica 2 — due costanti nuove, dopo `POLICY_HIGHLIGHTS`

```python
# S5, famiglia 2: convenzioni di output verso il cliente.
OUTPUT_CONVENTIONS = """
1. Reply in the language the customer is writing in.
2. Write every monetary amount in US dollar format: a comma every three digits, a period
   only before cents. Example: $1,250 and $1,250.75 - never $1.250.
""".strip()

# S5, famiglie 1, 3, 5, 6: regole comportamentali nate dalla tassonomia. Ordinate per
# flusso di conversazione, non per numero di famiglia. Vanno in fondo al system prompt
# (vedi docs/s5-correzioni.md, "Decisione strutturale").
HANDLING_CUSTOMER_REQUESTS = """
1. When the customer's message contains more than one request, serve all of them before
   closing the conversation. If one request is an action and another is a question, answer
   the question in the same message in which you ask for confirmation of the action.
2. When a question uses a scope word that could reasonably be read in more than one way
   (for example "other", "the rest", "remaining", "all"), do not choose one reading
   silently. State which reading your answer refers to, and give the answer for the other
   reading as well, in the same message.
3. When an action requires you to supply a payment method, use only a method the customer
   has named in this conversation - the specific card, gift card, or certificate. If they
   have not named one, list the payment methods on their profile and ask which to use,
   before acting.
4. When part of the customer's request cannot be done, or the path you first tried is
   blocked:
   a. Identify which parts of the request the policy still allows you to serve, including
      through a different sequence of actions than the one you first tried.
   b. Carry out those parts, asking for explicit confirmation first where the policy
      requires it. If the customer has already confirmed them, carry them out now.
   c. Tell the customer plainly which part could not be done, and why.
   d. Transfer to a human agent only if step (a) leaves nothing you can serve.
""".strip()
```

## Modifica 3 — `SYSTEM_PROMPT` (righe 80-90) e la `.format(...)` (righe 129-132)

```python
SYSTEM_PROMPT = """
<instructions>
{agent_instruction}
</instructions>
<policy_highlights>
{policy_highlights}
</policy_highlights>
<policy>
{domain_policy}
</policy>
<handling_customer_requests>
{handling_customer_requests}
</handling_customer_requests>
<output_conventions>
{output_conventions}
</output_conventions>
""".strip()
```

e nella `.format(...)` aggiungere `handling_customer_requests=HANDLING_CUSTOMER_REQUESTS` e
`output_conventions=OUTPUT_CONVENTIONS`.

**Poi rigenerare la patch in `patches/`.** `tau2-bench/` è gitignorato: senza patch, tutto questo
si perde al primo riclone.

## Cosa non viene toccato

- `AGENT_INSTRUCTION`, `TOOL_ERROR_STREAK_LIMIT`, `AGENT_TURN_LIMIT` e i due messaggi forzati dal
  codice: le tre decisioni di S3 restano invariate.
- **Famiglia 4** (l'utente chiude nello stesso turno in cui conferma): nessuna correzione, per
  decisione presa in S4 e verificata leggendo `orchestrator.py:836-843`. Resta nella tassonomia
  come categoria da monitorare. Il task 33 resterà a zero, ed è atteso.

## Copertura attesa e cosa aspettarsi davvero

| Famiglia | Task | Modifica che la copre |
|---|---|---|
| 1 | 7 | clausole 1 e 2 |
| 2 | 18 | modifica 1 (lingua) + `OUTPUT_CONVENTIONS` |
| 3 | 23 | clausola 4 + quarto punto riparato |
| 4 | 33 | nessuna — monitoraggio |
| 5 | 37 | clausola 3 |
| 6 | 39, 44 | clausola 4 |

Sei dei sette fallimenti sono coperti da una regola. **Questo non significa che sei task
passeranno**: il reward di τ²-bench va a zero se una qualsiasi regola di policy è violata, quindi
un task recuperato su una famiglia può fallire su un'altra cosa, e le simulazioni sono
stocastiche. Con un run solo per task un delta di uno o due task non distingue un miglioramento
dal rumore. Va scritto così nel report — vedi `docs/regole-comportamentali-agenti.md` §5.

Il rischio simmetrico, da guardare esplicitamente nei canary (0, 41, 42): tre delle regole nuove
spingono verso messaggi più lunghi e turni in più (clausole 1, 3 e 4), e il codice ferma l'agente
a 30 turni. Un task che oggi passa al turno 28 può non passare più.
