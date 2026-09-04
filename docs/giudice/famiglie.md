# Le famiglie di fallimento — definizioni per l'etichettatura

Questo è lo **spazio delle etichette** del giudice. Va fissato *prima* di scrivere il prompt del
giudice e *prima* di etichettare, altrimenti si finisce per adattare le categorie ai casi, che è il
modo più rapido di ottenere un numero che non misura niente.

Le definizioni nascono dalla diagnosi manuale di S4, S5 e della notte del 2 settembre. Non sono
inventate a tavolino: ognuna corrisponde a un meccanismo osservato almeno una volta su una traccia
reale, e nominato dal **suo innesco**, non dal suo effetto.

---

## Come si assegna un'etichetta

Una sola etichetta per traccia, quella della **causa prossima del mancato `db_check`** — cioè:
*qual è la prima cosa andata storta, senza la quale il database finale sarebbe stato quello atteso?*

Se più famiglie sembrano applicabili, si sceglie quella **più a monte** nella conversazione.
Esempio di ragionamento: se l'agente prima sbaglia il metodo di pagamento e poi si ferma senza
completare la seconda azione, la causa prossima è l'arresto, perché anche col pagamento corretto il
database resterebbe incompleto — a meno che l'argomento sbagliato non sia proprio ciò che ha
bloccato il seguito.

**Non forzare mai un'etichetta.** `F9` esiste apposta.

---

## Le famiglie

### `F0` · Nessun fallimento
Il task è riuscito: le azioni attese sono state eseguite e le informazioni richieste comunicate.
Presente nel set apposta: un giudice a cui mostri solo fallimenti impara a vederli ovunque.

### `F1` · Trappola della conferma
L'agente presenta l'azione e chiede la conferma esplicita che la policy impone. Il cliente approva
**e chiude la conversazione nello stesso messaggio**. L'agente non ha più un turno, e la scrittura
non viene mai eseguita.
*Segno riconoscibile*: l'ultimo messaggio dell'agente è una richiesta di conferma; nessuna
scrittura eseguita dopo.

### `F2` · Trasferimento prematuro
L'agente trasferisce a un operatore umano mentre restava qualcosa che poteva servire: una richiesta
del cliente non ancora evasa, o una strada alternativa che non ha proposto.
*Attenzione*: trasferire è spesso **corretto**. È un fallimento solo se una parte servibile è
rimasta sul tavolo.

### `F3` · Argomento sbagliato
L'azione giusta, sull'oggetto giusto, con un parametro errato — tipicamente il metodo di pagamento.
La chiamata riesce, il database finale è diverso da quello atteso.

### `F4` · Equivalenza non riconosciuta
Le azioni eseguite sono **sostanzialmente equivalenti** a quelle attese — stessi effetti, stessi
importi — ma differiscono in ordine o in forma, e il confronto fra database, che è un hash, non
combacia.
*Non è un errore dell'agente*: è un limite della misura. Esiste come etichetta proprio per poterlo
contare.

### `F5` · Selezione sbagliata
L'agente agisce sull'oggetto sbagliato: un volo diverso da quello richiesto, una prenotazione al
posto di un'altra. L'operazione è corretta, il bersaglio no.

### `F6` · Esecuzione parziale
L'agente esegue una parte delle azioni attese e si ferma, senza che nulla glielo impedisse.
*Da distinguere da `F1`*: qui la conversazione continua, semplicemente l'agente non completa.

### `F7` · Ground truth incoerente
Il task **non è risolvibile**: le azioni attese contraddicono la policy del dominio, o la
descrizione del task contraddice le proprie azioni attese. Nessun agente può passarlo.

### `F8` · Uscita del simulatore
L'utente simulato termina la conversazione per una ragione propria — `###OUT-OF-SCOPE###`,
`###TRANSFER###` — interrompendo un percorso che stava procedendo.

### `F10` · Esecuzione non dovuta
L'agente esegue una scrittura che il ground truth **non prevede affatto**: il task chiedeva di
rifiutare, o di non toccare quella prenotazione, e l'agente ha agito lo stesso.
*Da distinguere da `F3`*: li' l'azione era dovuta e un parametro era sbagliato; qui l'azione non
andava fatta.

> Questa famiglia **e' stata aggiunta durante il pilota di etichettatura**, non prima. Le dieci
> famiglie iniziali nascevano dai fallimenti diagnosticati a mano, dove il caso non era mai
> comparso; alla prima traccia mai vista si e' presentato subito. La metrica `unexpected_writes`
> misurava gia' esattamente questo, ma non esisteva l'etichetta corrispondente — un buco fra le
> due viste dello stesso fenomeno. E' il motivo per cui un pilota si fa **prima** di misurare:
> allargare lo spazio delle etichette dopo aver visto i verdetti del giudice sarebbe stato
> adattare la domanda alla risposta.

### `F9` · Non determinabile
La traccia non contiene abbastanza per decidere, o il meccanismo non rientra in nessuna delle
famiglie sopra. **Usarla senza esitazione**: un'etichetta forzata sporca la misura più di
un'astensione.

---

## Come verrà usato tutto questo

1. Le etichette umane si scrivono **prima** di vedere il giudice, e non si toccano più. Se il
   giudice dissente, si corregge il prompt del giudice, mai il proprio giudizio.
2. Il materiale è diviso in due: una parte per iterare sul prompt, una **toccata una volta sola**
   alla fine. Serve a non sovradattare il giudice sugli esempi — lo stesso errore che abbiamo
   documentato sull'agente.
3. L'accordo si misura con il **kappa di Cohen**, non con l'accuratezza: con classi sbilanciate un
   giudice che risponde sempre la famiglia più comune ottiene una percentuale alta ed è inutile.
4. Il risultato che conta non è il totale ma la **matrice di confusione**: *dove* sbaglia
   sistematicamente.
