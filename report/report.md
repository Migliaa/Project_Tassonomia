# Migliorare un agente AI cambiando solo il prompt

*Sei passi su un banco di prova pubblico, e un difetto trovato per strada.*

Testo approvato da Andrea l'8 settembre 2026. Istruzioni per l'implementazione: `CONSEGNA.md`.

---

## Sintesi

*Da mettere in apertura, prima dei passi.*

Le aziende non mettono in produzione i modelli più potenti, ma i più economici: l'assistenza
clienti si misura in milioni di conversazioni. Far rispettare un regolamento di quaranta pagine
a un modello piccolo è quindi un problema commerciale, non accademico.

Questo progetto misura quanto si guadagna agendo solo sul prompt — e soprattutto costruisce il
modo di saperlo: ogni conversazione tracciata, metriche per singola azione, previsioni registrate
prima dell'esperimento, ripetizioni per separare il risultato dal caso.

È l'infrastruttura che resta quando il modello cambia.

*(85 parole)*

---

## 1 · Il banco di prova

**Figura**: `fig1-banco-di-prova.svg`

τ²-bench è un banco di prova costruito da Sierra per misurare gli agenti conversazionali. Un
agente fa l'assistente di una compagnia aerea: parla con un cliente simulato da un altro modello,
consulta e modifica un database di prenotazioni vero, e deve rispettare un regolamento aziendale
di quaranta pagine.

Un task riesce solo se lo stato finale del database coincide esattamente con quello atteso e le
informazioni richieste sono state comunicate al cliente. Non esistono mezzi voti.

La domanda era una sola, e volutamente stretta: **a modello fisso, quanto si guadagna cambiando
solo il prompt?** Niente addestramento, niente secondo modello, niente strumenti aggiuntivi.

Il modello scelto è piccolo e senza ragionamento esplicito — la stessa classe che si usa quando
un servizio deve reggere volumi veri.

*(125 parole)*

---

## 2 · La prima misura, e il muro

**Figura**: `fig2-punteggio-binario.svg`

L'agente di default fornito dal benchmark risolve **34 task su 50**. È il numero da battere.

Ma il punteggio dice «fallito» e nient'altro. Sedici fallimenti, sedici scatole nere. Non si sa
se l'agente abbia violato una regola, dimenticato un passaggio, o scelto l'opzione sbagliata fra
due legittime.

La prima cosa costruita non è stata quindi un agente migliore, ma **un modo per guardare**: ogni
esecuzione tracciata, e il punteggio scomposto nelle sue due componenti — *ha comunicato
correttamente?* e *ha lasciato il database nello stato giusto?* — insieme a metriche per singola
azione: quante azioni non richieste, quante con argomenti sbagliati.

Un agente che comunica benissimo e non esegue nulla, e un agente che esegue azioni vietate senza
dire niente, prendono lo stesso zero. Sono problemi opposti e richiedono correzioni opposte:
finché il punteggio resta un numero solo, non si sa nemmeno quale dei due si ha davanti.

*(157 parole)*

---

## 3 · Leggere i fallimenti uno per uno

**Figura A**: `screenshots/` — la traccia Langfuse con `reward: 0.00`
**Figura B**: `fig3-famiglie.svg`

Ogni fallimento è stato letto turno per turno, come si legge la registrazione di una telefonata.
Da lì sono emerse tre famiglie con cause distinte.

**Non agisce.** L'agente descrive l'operazione così bene che il cliente crede sia già fatta, dice
«sì» e chiude la conversazione — prima che l'azione parta. Comunicazione perfetta, database
intatto.

**Agisce troppo.** L'agente si scrive da solo una giustificazione e la usa come autorizzazione.

**Sceglie male.** Al cliente che chiede «il volo più economico verso la costa ovest», l'agente
cerca una sola combinazione e prenota la prima valida. Valida, ma non la più economica.

E leggendo è emerso qualcos'altro: un task che passava o falliva senza che l'agente cambiasse
comportamento. La causa non era l'agente, ma **il modo in cui il benchmark confronta i
risultati**. È diventata una segnalazione agli autori, aperta e verificabile
([issue #514](https://github.com/sierra-research/tau2-bench/issues/514)) →
*approfondimento a pagina dedicata*.

*(165 parole)*

---

## 4 · L'errore che è costato di più

**Figura**: `fig4-versioni.svg`

L'istinto, dopo una diagnosi, è aggiungere una regola per ogni problema trovato. È esattamente
quello che ho fatto, per tre versioni consecutive. E il punteggio è **sceso**.

La spiegazione è arrivata dalla letteratura, non dall'intuito: superata una certa densità di
istruzioni — attorno alla ventina — i modelli piccoli iniziano a violarle **in silenzio**, senza
alcun errore visibile. Il regolamento del dominio ne conteneva già una quarantina. Ogni clausola
aggiunta per chiudere un problema ne apriva un altro altrove.

Conclusione scomoda ma utile: **su un modello piccolo, aggiungere istruzioni ha rendimenti
negativi.** Serviva cambiare metodo, non aggiungere righe.

Una precisazione sul grafico, perché altrimenti inganna: il 78% della v1 viene da **una sola**
esecuzione, l'80,5% della v6 dalla media di **quattro**. Non sono numeri della stessa
attendibilità, e il perché è il passo 6.

*(148 parole)*

---

## 5 · Sottrarre invece che aggiungere

**Figura**: `fig5-prima-dopo.svg`

Il cambio di metodo: **smettere di scrivere regole e cominciare a togliere le cause.**

Il prompt conteneva un esempio che mostrava all'agente come aggiungere bagagli gratuiti a un
cliente che ne aveva diritto. In un task reale l'agente ha aggiunto due bagagli a un cliente che
aveva appena detto di non averne — copiando l'esempio invece di ascoltare. **Il difetto non era
una regola mancante: era un esempio che insegnava la cosa sbagliata.** Tolto l'esempio, dieci
righe di casistica sono state sostituite da una frase: *un diritto non è un'istruzione*.

Stessa logica per la famiglia «non agisce»: invece di regole su quando confermare, una riga apre
ogni messaggio di conferma — *«non ho ancora fatto nessuna di queste modifiche»* — e toglie al
cliente la ragione per riagganciare.

Ogni modifica è stata registrata come previsione prima di girare l'esperimento — quali task
dovevano cambiare esito e quali no — in modo tale che l'esperimento potesse smentirmi, invece di
darmi ragione comunque.

*(165 parole)*

---

## 6 · Il risultato, e cosa non dice

**Figura A**: `fig6-risultato.svg`
**Figura B**: `screenshots/` — le dieci esecuzioni a confronto nel dataset

Quattro esecuzioni complete, 200 simulazioni: **80,5% contro il 68%** dell'agente di default.

Ma i quattro giri servivano soprattutto a un'altra cosa. I singoli punteggi vanno da 74% a 86% —
stesso agente, stessi task, campionamento deterministico.

Sull'affidabilità, infine, il nuovo agente è **alla pari** con quello di default: il guadagno è
sul punteggio medio, non sulla costanza.

*(63 parole)*

---

# Pagina di approfondimento · Il difetto nel benchmark

**Figura**: `fig-bug.svg`

τ²-bench decide se un task è superato confrontando due impronte digitali del database: quella
prodotta dall'agente e quella attesa.

L'impronta si calcola mettendo il database in ordine e riducendolo a testo. Ma quell'ordinamento
riguarda i campi, **non gli elementi di una lista** — e la cronologia dei pagamenti di una
prenotazione è una lista.

Due prenotazioni identiche — stesse carte, stessi importi, stesso totale — ma con i pagamenti
elencati in ordine diverso, producono impronte diverse. Il benchmark le giudica differenti.

Verificato su due esecuzioni reali dello stesso agente: unica differenza in tutta la chiamata,
l'ordine di due carte regalo. Una superata, l'altra bocciata.

**Non è un errore del modello.** Le due risposte sono entrambe corrette, e nessuna regola dice in
che ordine elencare i pagamenti: è il metro di misura a distinguere ciò che non andrebbe
distinto. E poiché l'ordine che un modello produce non è stabile, il difetto rende un task
risolto una monetina — proprio dentro un banco di prova che esiste per misurare quanto un agente
è costante.

Segnalato agli autori: [issue #514](https://github.com/sierra-research/tau2-bench/issues/514),
collegata a [#325](https://github.com/sierra-research/tau2-bench/issues/325), che aveva osservato
lo stesso sintomo su un altro dominio senza individuarne la causa.

*(196 parole)*

---

**Totale: ~1.104 parole**
