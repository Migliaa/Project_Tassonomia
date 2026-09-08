# Migliorare un agente AI cambiando solo il prompt

*Sei passi, un benchmark pubblico, e un bug trovato per strada.*

---

## 1 · Il banco di prova

**Figura**: `fig1-banco-di-prova.svg`

τ²-bench è un banco di prova costruito da Sierra per misurare gli agenti conversazionali. Un
agente fa l'assistente di una compagnia aerea: parla con un cliente simulato da un altro modello,
consulta e modifica un database di prenotazioni vero, e deve rispettare un regolamento aziendale
di quaranta pagine.

Il punteggio è spietato: un task riesce **solo** se lo stato finale del database coincide
esattamente con quello atteso **e** le informazioni richieste sono state comunicate al cliente.
Non esistono mezzi voti.

La domanda del progetto era una sola, e volutamente stretta: **a modello fisso, quanto si può
guadagnare cambiando solo il prompt?** Niente fine-tuning, niente secondo modello, niente
strumenti aggiuntivi. Solo le istruzioni date all'agente.

Il modello scelto è piccolo e senza capacità di ragionamento esplicito. È una scelta deliberata:
su un modello già forte i margini di miglioramento sono minimi, e un eventuale guadagno sarebbe
indistinguibile dal rumore.

*(146 parole)*

---

## 2 · La prima misura, e il muro

**Figura**: `fig2-punteggio-binario.svg`

L'agente di default fornito dal benchmark risolve **34 task su 50**. È il numero da battere.

Ma qui arriva il problema che ha definito tutto il progetto: il punteggio dice «fallito» e
nient'altro. Sedici fallimenti, sedici scatole nere. Non si sa se l'agente abbia violato una
regola, dimenticato un passaggio, o scelto l'opzione sbagliata fra due legittime.

La prima cosa costruita non è stata quindi un agente migliore, ma **un modo di guardare**: ogni
esecuzione viene tracciata su Langfuse, e il punteggio viene scomposto nelle sue due componenti
— *ha comunicato correttamente?* e *ha lasciato il database nello stato giusto?* — insieme a
metriche per singola azione: quante azioni non richieste, quante con argomenti sbagliati.

È una distinzione che sembra banale e non lo è. Un agente che comunica benissimo e non esegue
nulla, e un agente che esegue azioni vietate senza dire niente, prendono lo stesso zero. Sono
problemi opposti e richiedono correzioni opposte.

*(158 parole)*

---

## 3 · Leggere i fallimenti uno per uno

**Figura A**: screenshot Langfuse — vedi `screenshot.md`, voce «traccia»
**Figura B**: `fig3-famiglie.svg`

Nessuna scorciatoia: ogni fallimento è stato letto turno per turno, come si legge la
registrazione di una telefonata. Da lì sono emerse tre famiglie con cause distinte.

**Non agisce.** L'agente descrive l'operazione così bene che il cliente crede sia già fatta, dice
«sì» e chiude la conversazione — prima che l'azione parta. Comunicazione perfetta, database
intatto.

**Agisce troppo.** L'agente si scrive da solo una giustificazione e la usa come autorizzazione.
In un caso reale scrive *«nessun volo è stato ancora effettuato»* due righe sotto delle date che
sono nel passato, e cancella una prenotazione che il regolamento proteggeva.

**Sceglie male.** Al cliente che chiede «il volo più economico verso la costa ovest», l'agente
cerca una sola combinazione e prenota la prima valida. Valida, ma non la più economica.

E leggendo è emerso qualcos'altro. Un task passava o falliva in modo apparentemente casuale, a
parità di soluzione. La causa non era l'agente: era **un difetto nel modo in cui il benchmark
confronta i risultati**. Due carte regalo elencate in ordine diverso producono un verdetto
diverso. → *approfondimento a pagina dedicata*

*(211 parole)*

---

## 4 · L'errore che è costato di più

**Figura**: `fig4-versioni.svg`

L'istinto, dopo una diagnosi, è aggiungere una regola per ogni problema trovato. È esattamente
quello che ho fatto, per tre versioni consecutive. E il punteggio è **sceso**.

La spiegazione è arrivata dalla letteratura, non dall'intuito: superata una certa densità di
istruzioni — attorno alla ventina — i modelli piccoli iniziano a violarle **in silenzio**, senza
alcun errore visibile. Il regolamento del dominio ne conteneva già una quarantina. Ogni clausola
aggiunta per risolvere un problema ne slatentizzava un altro altrove.

Un secondo esperimento ha chiuso la questione: riscrivendo **una sola** clausola, i fallimenti
cambiavano su task che con quella clausola non c'entravano nulla. Il comportamento non era
attribuibile alla regola, ma alla perturbazione del prompt nel suo insieme.

Conclusione scomoda ma utile: **su un modello piccolo, aggiungere istruzioni ha rendimenti
negativi.** Bisognava cambiare metodo, non aggiungere righe.

*(151 parole)*

---

## 5 · Sottrarre invece che aggiungere

**Figura**: `fig5-prima-dopo.svg`

Il cambio di metodo è stato questo: **smettere di scrivere regole e cominciare a rimuovere le
cause.**

Un esempio concreto. Il modulo di conferma conteneva un esempio d'uso in cui l'agente aggiungeva
bagagli gratuiti a cui il cliente aveva diritto. Quell'esempio insegnava un comportamento
sbagliato: in un task reale l'agente ha aggiunto due bagagli a un cliente che aveva detto di non
averne, giustificandoli con il diritto ad averli. **La correzione è stata togliere l'esempio**, e
sostituire dieci righe di casistica con un principio solo: *un diritto non è un'istruzione*.

Stessa logica per la famiglia «non agisce». Invece di aggiungere regole sul quando confermare,
una riga sola apre ogni messaggio di conferma: *«non ho ancora fatto nessuna di queste
modifiche»*. Toglie al cliente la ragione per riagganciare.

Due righe al posto di due blocchi. E ogni modifica è stata **registrata come previsione prima di
girare l'esperimento**: quali task specifici dovevano cambiare esito, e quali no. È ciò che
distingue una correzione da un aggiustamento fortunato.

*(174 parole)*

---

## 6 · Il risultato, e cosa non dice

**Figura**: `fig6-risultato.svg`

Quattro esecuzioni complete, 200 simulazioni, come richiede lo standard dichiarato da Sierra per
la propria classifica pubblica.

**80,5% contro il 68% dell'agente di default.** Tre repliche su quattro battono il baseline in
modo statisticamente significativo, e in due di esse il nuovo agente non perde **nemmeno un
task**. Cinque task non li risolve nessuna versione: sono, in tutte e quattro le esecuzioni,
esattamente quelli diagnosticati come difettosi nel benchmark o fuori dalla portata del modello.

Ma i quattro trial servivano soprattutto a misurare un'altra cosa. Presi singolarmente, i quattro
punteggi vanno da 74% a 86%: **lo stesso agente, sugli stessi task, con temperatura a zero.** Con
una sola esecuzione avrei pubblicato l'86% in buona fede, e sarebbe caduto alla prima verifica.

E sull'affidabilità — riuscire più volte di fila sullo stesso task — il nuovo agente è **alla pari**
con quello di default, non migliore. Il guadagno è sul punteggio medio, non sulla costanza.

Dirlo è meno soddisfacente che fermarsi all'86%. È anche l'unica versione che regge a un
controllo.

*(184 parole)*

---

# Pagina di approfondimento · Il bug

**Figura**: `fig-bug.svg`

τ²-bench verifica il risultato confrontando due impronte digitali del database: quella prodotta
dall'agente e quella attesa. Se coincidono, il task è superato.

L'impronta si calcola serializzando il database in testo e ordinandone le chiavi
(`json.dumps(..., sort_keys=True)`). Ma quell'ordinamento riguarda **le chiavi dei dizionari, non
gli elementi delle liste**. E la cronologia dei pagamenti di una prenotazione è una lista.

La conseguenza: due prenotazioni identiche — stesse carte, stessi importi, stesso totale — ma con
i pagamenti elencati in ordine diverso, producono impronte diverse. Il benchmark le giudica
differenti.

Verificato su due esecuzioni reali dello stesso agente. Unica differenza in tutta la chiamata:
l'ordine di due carte regalo. Una esecuzione superata, l'altra bocciata.

L'effetto va oltre il singolo falso negativo. Poiché l'ordine che un modello produce non è
stabile, **il difetto inietta casualità nella metrica di affidabilità**: un task effettivamente
risolto diventa una monetina. Un benchmark che misura proprio quanto un agente è costante viene
reso, in quel punto, meno costante di quanto misuri.

Segnalazione preparata per gli autori.

*(178 parole)*

---

**Totale: ~1.202 parole**
