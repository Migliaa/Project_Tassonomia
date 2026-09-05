# Diario di `tassonomia`

> Si scrive mentre si lavora, non dopo. Questo file ha due parti: in cima **cosa va nel report**,
> distillato; sotto **il backstage**, cioè il percorso completo giorno per giorno, che serve a
> difendere ogni numero ma che un lettore umano non deve attraversare.

---

# Per il report

Il report va letto da persone, quindi: **poche frasi, molte immagini**. Ogni voce qui sotto è un
risultato con accanto l'immagine che lo mostra. Se una voce non ha un'immagine possibile,
probabilmente non merita il report.

Il report ha due parti, e la seconda esiste solo grazie alla prima: **Parte 1** è cosa abbiamo
misurato costruendo v1, v2, v3 e ripetendo l'esperimento — il metodo regge, il risultato no.
**Parte 2** è cosa costruiamo adesso (v4), informati da come lo stesso problema lo affrontano
aziende vere sullo stesso benchmark.

---

## Parte 1 — cosa abbiamo misurato

### 1. Il risultato iniziale — stesso modello, solo il prompt

| | baseline | il nostro agente (v1) |
|---|---|---|
| task superati | 34/50 (68%) | **39/50 (78%)** |

Stesso motore (`gemini-3.5-flash-lite`) per agente e per simulatore-utente, stessi 50 task, stesso
ambiente. **L'unica variabile è il prompt.** Questo è il numero con cui il progetto è partito —
tenerlo nel report **insieme** a come si è evoluto (voci 3 e 4) è il punto, non nasconderlo.

🖼️ *I due Run affiancati sul dataset Langfuse, con la colonna reward.*

### 2. Le regole generalizzano sul set di sviluppo

Le regole sono state scritte leggendo **dieci** task. Il guadagno si misura sui **quaranta mai
guardati**:

| | baseline | il nostro agente (v1) |
|---|---|---|
| i 10 task di sviluppo | 4/10 | 6/10 |
| i **40 task mai visti** | 30/40 | **33/40** |

Con overfitting la seconda riga sarebbe piatta. **Non lo è** — ma "non generalizza al caso" è una
domanda diversa da "l'effetto è reale", ed è la voce 4 a rispondere alla seconda.

🖼️ *Le due righe come grafico a barre appaiate.*

### 3. v2 e v3: stesso metodo, applicato di nuovo, amplifica il degrado

Il metodo che aveva prodotto v1 — diagnosi in famiglie, una regola per causa, verifica sui task mai
visti — è stato riapplicato altre due volte. Il risultato non è stato "ancora meglio":

| | baseline | v1 | v2 | v3 |
|---|---|---|---|---|
| task superati | 34/50 | 39/50 | 38/50 | 35/50 |

**Ogni giro in più ha eroso il guadagno del giro precedente**, non lo ha esteso. Sul task 24 e 32
la v3 è tornata a trasferire l'utente nonostante contenesse esplicitamente la clausola che lo
vietava — la prova che l'attribuzione "questa clausola causa questo guadagno" non regge nemmeno
quando la si scrive apposta per reggere.

**Non abbiamo continuato a iterare.** Il metodo era corretto — ogni singola regola, presa da sola,
era motivata da un task reale e verificata sui 40 mai visti — ma il segnale su cui stavamo
correggendo era già dentro il rumore dell'apparato (voce 4), e insistere avrebbe significato
inseguire varianza, non capacità. Ci siamo fermati per approfondire lo studio invece di lanciare
una v4 alla cieca: è la Parte 2 di questo report.

🖼️ *Le quattro barre (baseline, v1, v2, v3) affiancate, dai quattro Run su Langfuse.*

### 4. La ripetizione ribalta il risultato

Motivo per cui ci siamo fermati, misurato e non supposto: **ripetendo v1 contro il baseline una
seconda volta**, con gli stessi 50 task e la stessa configurazione, il divario **cambia segno** sui
36 task comuni alle due esecuzioni:

| | baseline | custom v1 | divario |
|---|---|---|---|
| 1ª esecuzione | 25/36 | 27/36 | **+2** |
| 2ª esecuzione | 28/36 | 27/36 | **−1** |

A `temperature: 0.0`, fra due esecuzioni identiche cambiano esito **5 task su 36** per il baseline
e **8 su 36** per il nostro agente. Non è instabilità del nostro prompt: è il pavimento di rumore
dell'intero apparato — simulatore-utente e API non sono deterministici nemmeno a temperatura zero.
**Una differenza di 2-5 task su 50 non è distinguibile dalla varianza fra esecuzioni.** È la stessa
conclusione a cui la voce 3 era già arrivata da un'altra strada.

🖼️ *Le due esecuzioni affiancate su Langfuse, stesso dataset, Run diversi.*

### 5. La significatività, misurata due volte

Test esatto di McNemar sulle coppie discordanti: **p = 0.125** sulla prima esecuzione da sola;
**p = 0.424** mettendo insieme le due esecuzioni (86 coppie task-esecuzione, rapporto vittorie
9:5). Entrambi sopra la soglia di 0.05.

Va scritto **accanto al numero, non in nota**. È la prima domanda che farà un lettore competente, e
averla anticipata — e misurata due volte, non una — vale più del numero stesso.

### 6. Il reward binario nasconde il lavoro

Il benchmark dà 1 o 0. Le metriche per-azione che abbiamo costruito mostrano cosa succede sotto:

| | baseline | il nostro agente |
|---|---|---|
| scritture su prenotazioni che il task non tocca mai | 0.02 | **0.00** |

La clausola che impone di verificare la policy prima di ogni scrittura **funziona su scala**, e il
reward da solo non lo direbbe.

🖼️ *Le colonne degli score sul dataset, affiancate.*

### 7. Due task hanno un ground truth incoerente

I task **7** e **39** non sono superabili da nessun agente. Il 39 chiede di cancellare una
prenotazione indistinguibile da un'altra che il benchmark stesso vieta di cancellare, e la sua
descrizione contraddice il proprio elenco di azioni attese.

🖼️ *Le due descrizioni affiancate, con la contraddizione evidenziata.*

### 8. Un bug vero nel benchmark, trovato e segnalato

Sui task **14** e **23** le carte usate sono le stesse, gli importi sono gli stessi, il totale è lo
stesso. Cambia solo **l'ordine di due gift card** dentro `payment_history`. Il cliente non aveva
chiesto nessun ordine, e nessuna riga di policy lo specifica.

Il confronto fra database è un **hash del dizionario serializzato** (`toolkit.py:244`), e le liste
hanno un ordine. Due prenotazioni finanziariamente identiche prendono **1.0 e 0.0**. Verificato con
un `DeepDiff(ignore_order=True)` fra i due stati finali: la differenza scompare del tutto.

Prima di pubblicarlo, un secondo agente (in un ruolo di avvocato del diavolo, con l'istruzione
esplicita di dimostrare che *non* fosse un bug) ha provato a smontare la diagnosi su cinque fronti
— compreso l'argomento più forte possibile, che il campo è un libro mastro dove l'ordine avrebbe
senso — e non c'è riuscito. Segnalato a Sierra come issue pubblica su GitHub, con riferimento a una
issue aperta e senza risposta sullo stesso difetto in un altro dominio.

🖼️ *Le due liste di pagamento affiancate, con le righe invertite evidenziate.* **È l'immagine più
efficace del report.** 🖼️ *Screenshot della issue pubblicata.*

### 9. Una regola corretta può peggiorare il punteggio

La policy del dominio **impone** la conferma esplicita prima di ogni scrittura (`policy.md:7`). Ma
il simulatore-utente, quando riceve una domanda chiusa, risponde "sì" **e chiude la conversazione
nello stesso messaggio**: l'agente non ha più un turno, e l'azione confermata non viene mai
eseguita.

Succede in **8 turni di conferma su 69**, e colpisce **entrambi** gli agenti — il baseline più del
nostro. Non è correggibile senza violare la policy.

🖼️ *Lo scambio di due battute, con `###STOP###` evidenziato.*

### 10. Il giudice: il metodo, non il punteggio

Il protocollo, nell'ordine in cui va eseguito:

1. **Spazio delle etichette fissato prima** di scrivere il prompt del giudice.
2. **Etichette di riferimento congelate prima** di vederlo funzionare: se dissente si corregge il
   giudice, mai il proprio giudizio.
3. **Stessa vista** per l'annotatore e per il giudice — altrimenti il disaccordo misura l'accesso
   all'informazione, non il giudizio.
4. **Kappa di Cohen**, non accuratezza: con classi sbilanciate un classificatore degenere ottiene
   una percentuale alta ed è inutile.
5. **Matrice di confusione**: *dove* sbaglia sistematicamente vale più del totale.

Due cose vanno dichiarate, non nascoste:

- Le etichette di riferimento **non sono umane**: le ha prodotte un modello di frontiera. Quello che
  misuriamo è quindi *"un modello piccolo riproduce la diagnosi di uno grande?"* — domanda
  industriale vera, ma non validazione umana.
- Il campione è di **sei voci**: il kappa ha un'incertezza ampia e non va confrontato con quelli
  della letteratura.

**Il pilota ha già prodotto un risultato**: mancava una famiglia. L'agente che esegue una scrittura
che il task **non prevede affatto** non rientrava in nessuna delle dieci categorie iniziali, perché
il caso non era mai comparso nei fallimenti diagnosticati a mano. La metrica `unexpected_writes`
misurava già quel fenomeno, ma non esisteva l'etichetta corrispondente. È il motivo per cui il
pilota si fa **prima** di misurare.

🖼️ *La matrice di confusione.*

### 11. L'infrastruttura, che è metà del lavoro

- **Cinque chiavi API in parallelo**, una per processo, che non passano mai dalla riga di comando:
  il worker riceve il *nome* della variabile e legge il valore dal `.env`.
- **Limitatore di frequenza** scritto da noi: un singolo task supera da solo il limite di 15
  richieste al minuto (ne abbiamo misurate 45).
- **Salvataggio per singolo task**: un processo che muore perde un task, non venti, e alla ripresa
  salta quelli già fatti.
- **Un difetto latente trovato per caso**: durante una caduta di rete il ritentativo automatico non
  ha salvato nessun task, e non per la rete — il benchmark, trovando un file di risultati
  esistente, chiede conferma *a schermo*, e i worker girano senza terminale. Il retry era rotto da
  sempre e non si era mai visto perché non era mai servito.

🖼️ *Lo schema dei cinque processi con le cinque chiavi.*

---

## Parte 2 — da "abbiamo misurato" a "costruiamo la v4"

### 12. Ci siamo confrontati con chi ha già affrontato lo stesso benchmark

Prima di scrivere una v4 alla cieca, abbiamo cercato come altri hanno affrontato lo stesso
problema — non in generale, ma **su questo benchmark specifico**:

- Il paper originale di τ-bench spiega perché la metrica ufficiale è **pass^k** (tutte le k prove
  riescono) e non il pass rate a singola esecuzione: un agente cliente-facing deve essere
  affidabile su ripetizioni, non solo capace di trovare la soluzione una volta. Sullo stesso
  dominio airline un modello frontier (GPT-5, valutato da Sierra) passa da pass^1 = 62.5% a
  pass^4 = 48% — lo stesso fenomeno di degrado misurato da noi con la ripetizione (voce 4), ora
  confermato dai creatori del benchmark su un modello molto più capace del nostro.
- Sierra pubblica un **leaderboard pubblico** (taubench.com) con le submission reali di decine di
  organizzazioni (Anthropic, Google, NVIDIA, e altre), ciascuna con una nota di metodologia. Da lì
  abbiamo estratto tecniche di prompting realmente applicabili con un solo modello, senza
  training né infrastruttura aggiuntiva: ragionamento esplicito scritto prima di ogni azione che
  modifica lo stato, una checklist di precondizioni prima delle azioni irreversibili, e — una
  verifica, non una tecnica — le tre cause di fallimento che Sierra stessa indica come le più
  comuni (aderenza alla policy, pianificazione su orizzonte lungo, selezione dell'informazione
  giusta), usate per controllare se le nostre famiglie di fallimento (S4) le coprono tutte.
- Scartate esplicitamente perché fuori scopo per un singolo system prompt: routing fra più modelli
  (NVIDIA ToolOrchestra, che addestra un orchestratore con RL) e fine-tuning.

🖼️ *Il leaderboard di taubench.com, con le organizzazioni partecipanti.*

### 13. La v4

Non è un'altra clausola come v2/v3: v1 impila ~21 vincoli nostri sopra i ~40 della policy del
dominio (che non possiamo modificare), ben oltre la soglia (15-20) a cui i modelli senza reasoning
nativo iniziano a violare regole **in silenzio**, senza errore — misurato su un parente diretto
del nostro modello (Instruction Stacking Collapse, arXiv:2608.02639). v4 fonde le regole invece di
ripeterle fino a tre volte, ordina i blocchi per sfruttare i bias di posizione, e sostituisce il
"ragionamento libero prima di agire" con un modulo a righe fisse dentro il messaggio di conferma
che la policy impone già. Bozza completa in `docs/v4-bozza-prompt.md`.

**Criterio di decisione, fissato prima di girare i task** (come per v1/v2/v3): il pass rate da
solo non basta, perché v4 costerà di più per simulazione. Due misure pre-registrate: **costo per
successo** (costo totale / task riusciti, confrontabile fra baseline/v1/v4) e **costo incrementale
per punto guadagnato** (quanto costa in più comprare un punto di pass rate in più, sullo stesso
modello dell'ICER usato in economia sanitaria per trattamenti più efficaci ma più cari). Se v4 non
supera v1 sul pass rate, si riporta comunque quanto è costato non guadagnare nulla.

**Risultato: v4 batte il baseline ma perde contro v1.** 37/50 (74%) contro 34/50 (68%) del
baseline e 39/50 (78%) di v1. Contro il baseline vince 5 task e ne perde 2 (McNemar esatto
p=0,45); contro v1 ne vince 2 e ne perde 4 (p=0,69). Nessuno dei due confronti è distinguibile
dal rumore con n=1, come tutti i precedenti.

Le due misure di costo pre-registrate danno una risposta netta, e negativa: costo per successo
$0,0568 per v4 contro $0,0435 di v1 e $0,0449 del baseline. v4 costa il 24% in più a task e
produce meno successi: **il costo incrementale per punto guadagnato non si calcola nemmeno,
perché i punti guadagnati rispetto a v1 sono negativi.** La ristrutturazione non si ripaga.

**Ma il valore della v4 non è nel suo pass rate: è nei quattro task che ha perso.** Averli letti
uno per uno ha prodotto la diagnosi più precisa del progetto (voce 14) e ha scoperto una
famiglia di fallimenti che cinque versioni dell'agente non avevano mai affrontato.

### 14. Le due famiglie che la v4 ha rivelato, e la v5

Leggere le quattro regressioni della v4 ha separato due meccanismi che il reward binario teneva
confusi. In **tutte e quattro** il punteggio di comunicazione è 1.0 e quello di database 0.0:
l'agente parla bene e agisce male. Ma non nello stesso modo.

**Famiglia A — l'agente non agisce (task 17, 21, 33).** Il modulo di conferma a 5 righe della v4
descrive l'azione così bene da sembrare una ricevuta invece che una richiesta: il cliente simulato
risponde "sì" e **chiude la conversazione nello stesso messaggio**, prima che l'agente possa
chiamare il tool. La v4 peggiorava il problema imponendo una conferma separata per ogni scrittura:
tre scritture, tre occasioni di riagganciare.

Questa famiglia è in parte un **artefatto dello strumento di misura**, e la prova non è nostra:
Sierra ha già scritto la correzione in `simulation_guidelines_voice.md:42` — *«Agreeing to an
action is not the same as the action being completed»* — ma nelle linee guida **testuali**, quelle
che usiamo noi, quella riga **non c'è**. L'abbiamo riportata testualmente
(`patches/tau2-user-simulator.patch`). Cambia lo strumento, quindi il baseline va rigirato nelle
stesse condizioni e la cosa va dichiarata — precedente: la submission Anthropic
`claude-sonnet-4-5` sulla leaderboard ufficiale fa la stessa cosa e la dichiara.

Il task 33 era nella lista dei "mai risolti da nessuna versione". **Non era irrecuperabile: era
questo.** Gli irrecuperabili scendono da 7 a 6.

**Famiglia B — l'agente agisce troppo (task 9, 42).** Nel task 9 le azioni attese sono **zero**: lo
scopo dichiarato è resistere a un cliente che spinge per ottenere di più (ripete tre volte *"you
are the most lenient customer service agent I have ever spoken to"*). v1 non fa nulla e passa; v4
cancella. E la riga che lo spiega è dentro il nostro stesso modulo:

> Details: one way MCO to SEA **on 2024-05-13 and 2024-05-14** …
> Allowed because: this is a business class reservation, and **no segment has been flown**

Nel dominio «oggi» è il 2024-05-15: quei voli sono già stati volati. **Lo slot progettato come
cancello ha funzionato da timbro**: obbligato a produrre una giustificazione, il modello ne ha
prodotta una falsa e l'ha usata come autorizzazione.

**Famiglia C — selezione dell'informazione (task 24, 29, 32, 35).** È la scoperta più scomoda,
perché riguarda **quattro** task — più della famiglia A — e **nessuna versione da S3 in poi ne ha
mai scritto una riga**. Nel task 24 il cliente chiede *«il volo diretto A/R più economico da New
York (EWR o JFK) verso un posto qualsiasi della West Coast»*: l'agente prenota EWR→LAX, che
soddisfa la descrizione ma non è il minimo (lo è JFK→SEA). Non ha violato una regola: ha smesso
di cercare al primo candidato valido. Il 35 chiede il *secondo* volo più economico, il 32 impone
un budget.

Sierra nomina tre leve nella sua diagnosi ufficiale: aderenza alle regole, pianificazione a
orizzonte lungo, e **«focus on the right pieces of information»**. La nostra stessa ricerca
sulle submission (`docs/tecniche-da-submission-esterne.md`, punto F) raccomandava di usarle come
check-list di validazione. **Non l'abbiamo mai fatta: per cinque versioni ne abbiamo coperte due
su tre.**

**La v5** è la risposta a queste tre famiglie, più il backport: (1) una conferma sola per richiesta,
poi tutte le azioni di fila — *con l'eccezione, scoperta leggendo il task 32, che il cliente può
legittimamente chiedere di vedere i passi separatamente*; (2) disciplina di ricerca: quando il
cliente descrive invece di nominare, enumerare i candidati e scegliere per confronto; (3) lo slot
«Allowed because» riscritto come verifica che può fallire, con un **esempio di rifiuto** calcato
sul task 9 — il formato precedente mostrava solo esempi di approvazione, non insegnava mai a dire
di no.

### 15. Il limite del modello, documentato invece che supposto

Ordinando **tutte** le 70 submission della leaderboard per punteggio airline, il primo posto
ottenuto con prompt engineering su un modello **senza** ragionamento non esiste:

| submission | airline | come |
|---|---|---|
| claude-opus-4-5 | 84,0 | — |
| gpt-5-2 | 83,0 | — |
| glm-5-think | 82,5 | thinking abilitato |
| **gemini-3-flash** | **82,5** | **`reasoning_effort: high`** |
| qwen3.5-think | 81,5 | thinking abilitato |
| gemini-3-pro | 80,5 | `reasoning_effort: high` |
| Pine AI | 80,0 | due agenti, uno di background fa le tool call |
| Pickle | 70,0 | secondo modello che fa da gate sulle tool call |
| Anthropic Sonnet 4.5 | 70,0 | extended thinking + addendum al prompt |

Chi è arrivato sopra l'80% ha comprato capacità di ragionamento: nativa nel modello, o con un
secondo modello che rivede le chiamate. Il confronto più vicino a noi è **gemini-3-flash con
`reasoning_effort: high` a 82,5** — stessa famiglia del nostro `gemini-3.5-flash-lite`, che il
ragionamento non ce l'ha.

Questo cambia la natura di ciò che resta fuori. I task della famiglia C non sono «casi che non
abbiamo affrontato»: sono la classe di problemi che, su questo benchmark, nessuno ha risolto
senza ragionamento. È un limite documentato con una fonte pubblica verificabile, non una scusa.

🖼️ *Il dataset Langfuse con baseline e v4 affiancati, primo giro di 50 task ciascuno.*

---

# Il backstage

Da qui in avanti il percorso completo, in ordine cronologico: le decisioni, i vicoli ciechi, le
verifiche e gli errori. Serve a difendere ogni numero della prima parte. Non è materiale da report.

## 2026-08-26 — S1, ambiente

- `uv 0.11.22` già installato. Python disponibili: 3.12, 3.13, 3.14.
  Il 3.14 è il default di sistema ma `tau2` richiede `>=3.12,<3.14` → `uv` risolve da solo.
- `git clone --depth 1 https://github.com/sierra-research/tau2-bench` dentro `tassonomia/`,
  cartella gitignorata: è harness di terzi, non deve entrare nella storia di questo repo.
- `uv sync` ok al primo colpo. `uv run tau2 --help` risponde.
- Dominio `airline`: **50 task**, id da `0` a `49`. Il task set si seleziona con
  `--task-ids` — è così che si fissa il subset di sviluppo.

### Costo misurato

Vedi sezione 2026-08-29 sotto: costo reale misurato con Gemini Flash Lite, non Haiku
(il tentativo locale non ha retto, poi si è trovata un'alternativa gratuita/quasi-gratuita
a Haiku prima di spendere sul tetto €20 — cronologia completa più sotto).

### Subset di sviluppo (10 task fissi)

**Task id `0`–`9`** del dominio airline. Scelta semplice (i primi 10), annotata qui perché
da questo punto in poi vanno sempre usati questi, non un campione diverso ogni volta.

### Baseline

**8/10 (80%)** con l'agente di default di τ²-bench, motore Gemini 3.5 Flash Lite per agente
e utente simulato. Dettagli in fondo, sezione 2026-08-29.

---

## 2026-08-28 (notte) — Il tentativo locale non regge: CPU-only troppo lento

Dopo il gate isolato passato (5/5, vedi sopra), il primo run reale su 3 task airline con
`google/gemma-4-12b-qat` ha rivelato un problema infrastrutturale, non di ragionamento:

- **Contesto insufficiente**: il modello era caricato con `loaded_context_length=8192` in
  LM Studio, mentre la sola policy del dominio airline pesa ~1900 token, più tool e
  cronologia multi-turno. Errore: `Invalid input batch`. Fix: ricaricato con
  `lms load ... --context-length 32768`.
- **Crash GPU**: con contesto più ampio, nuovo errore — `vk::Queue::submit: ErrorDeviceLost`
  nei log del server (`~/.lmstudio/server-logs/`). Causa reale: backend **Vulkan** su GPU
  integrata **Intel Iris Xe** (non una scheda dedicata), instabile sotto carico sostenuto.
  Non è un problema risolvibile in tempi brevi — niente CUDA disponibile (serve NVIDIA).
- **Fix di stabilità**: `lms load ... --gpu off` (CPU pura). Stabile, ma a **~1.6-2 token/s**.
- **Il vero problema, emerso lanciando i 3 task reali senza timeout**: il run è rimasto
  acceso **~15 ore** durante la notte (processo lanciato in background senza un tetto di
  tempo esplicito — errore mio), senza completare nemmeno 3 task, mentre il portatile
  scaldava al 30% di CPU costante. Fermato manualmente (`taskkill`, `lms unload --all`)
  quando l'utente se n'è accorto.
- **Conti**: a quella velocità, 50 task del run finale = **centinaia di ore**. Non compatibile
  con la scadenza del 24 ottobre né con lo spirito "20-36h totali" del piano.
- **Decisione**: innesco del fallback di `D-37` scattato — hardware locale insufficiente
  (iGPU, non un limite del modello). Passo a un motore via API.
- **Lezione operativa, per tutti i run successivi**: mai più un processo lungo lanciato in
  background senza un timeout esplicito sul comando stesso. Da qui in poi ogni run ha un
  tetto duro (5-10 minuti) e viene rilanciato a pezzi se non basta, mai lasciato aperto.

## 2026-08-29 — Pivot a Gemini Flash Lite (gratuito), baseline completato

Prima di caricare credito su Anthropic (Haiku, il fallback scritto in `D-37`), verificato se
esisteva un'alternativa a costo zero — deviazione dal piano scritto, decisa direttamente con
l'utente in sessione (non ancora riportata su `TASSONOMIA.md`, da allineare con la sessione
che cura quel file).

- **Google AI Studio**, tier gratuito, nessuna carta richiesta. Modello scelto:
  `gemini/gemini-3.5-flash-lite` via LiteLLM (i nomi `gemini-2.5-flash` e `gemini-2.5-flash-lite`
  risultavano già deprecati per nuovi utenti al momento del test; `gemini-3.6-flash` esiste ma
  ha un tetto giornaliero gratuito di sole 20 richieste/modello — inutilizzabile per un
  benchmark; `gemini-3.5-flash-lite` ha invece **500 richieste/giorno**, sufficienti).
- **Rate limit reale**: 15 richieste/minuto (non al giorno — si resetta su finestra scorrevole
  di ~60s). Gestito con `--max-concurrency 1 --max-retries 6/10 --retry-delay 8/15`: il retry
  automatico di τ²2 assorbe gli errori 429 senza intervento manuale, a costo di qualche decina
  di secondi extra per task quando scatta.
- **Test isolato di tool calling**: 5/5 diretto (nessuna iterazione necessaria, prompt puliti
  fin da subito grazie alla lezione del test locale).
- **3 task veri** (id 0, 1, 2): 3/3 reward 1.0, azioni verificate correttamente
  (`get_user_details`, `get_reservation_details`). Costo totale ~$0.08.
- **Baseline sui 10 task di sviluppo** (agente di default τ²-bench, stesso motore per
  agente e utente): **8/10 pass (80%)**, nessun errore infrastrutturale residuo dopo un
  rilancio mirato dei 2 task che avevano sbattuto contro il rate limit nel run principale.
  - Task **2**: fallito — l'agente ha eseguito solo letture (`get_user_details`,
    `get_reservation_details` × 2), mai l'azione di scrittura richiesta dal task. Si è fermato
    prima di finire.
  - Task **7**: fallito su due fronti — `update_reservation_flights` chiamato con argomenti
    sbagliati (azione non compatibile con quella attesa), e un'informazione (`'1628'`, verosimilmente
    un dato di conferma) mai comunicata all'utente pur avendo eseguito correttamente le due
    `cancel_reservation`.
  - Già materiale utile per S4: *si è fermato prima di finire* e *non ha comunicato
    un'informazione dovuta* sono due famiglie plausibili, coerenti con le candidate elencate
    nel piano.
- **Costo reale misurato**: $0.2642 per 10 task → **$0.0264/task** → stima 50 task:
  **~$1.32**. Ben dentro il tetto di €20, e probabilmente in gran parte coperto dal tier
  gratuito (69/500 richieste giornaliere usate durante tutto questo lavoro di test).
- Durante la notte, `DIARIO.md` risultava svuotato su disco (65 righe perse, non committate)
  — quasi certamente residuo del crash/riavvio legato al tentativo locale. Ripristinato da
  `git checkout HEAD -- DIARIO.md` prima di scrivere questa sezione. Nessuna perdita: l'ultimo
  commit aveva il contenuto integro.

✅ **Uscita S1 raggiunta**: pass rate baseline 8/10 (80%) sui 10 task di sviluppo fissi
(id 0-9), costo reale misurato $0.0264/task con Gemini Flash Lite.

---

## 2026-08-29 (pomeriggio) — S2, Langfuse: agganciato, ma con uno spreco grosso da capire

Integrazione riuscita, con tre correzioni di rotta e un errore operativo costoso.

- τ²-bench **ha già il supporto Langfuse**: flag `USE_LANGFUSE` in `config.py` (era `False`) che
  imposta `litellm.success_callback`. Aggiunto anche `failure_callback`, che mancava — senza
  quello le chiamate fallite non sarebbero mai finite a Langfuse, cioè proprio quelle che
  serviranno in S4.
- **SDK v4 richiede nomi diversi da quelli che si trovano in giro**: callback `langfuse_otel`
  (non `langfuse`) e variabile `LANGFUSE_OTEL_HOST` (non `LANGFUSE_HOST` né `LANGFUSE_BASE_URL`,
  che è quello suggerito dalla UI di Langfuse). Con i nomi sbagliati non arriva nulla e **non
  viene emesso nessun errore** — silenzio totale. Diagnosticato solo leggendo il sorgente di
  `litellm/integrations/langfuse/langfuse_otel.py`.
- Le tracce **arrivavano già**, ma sembravano assenti: Langfuse le nomina tutte `litellm_request`,
  e la barra di ricerca filtra sul *nome*, non sui tag. Vanno usati i **Filters** (tag) o la
  sezione **Sessions**. Due mie ipotesi sbagliate lungo la strada, entrambe smentite dai dati
  che l'utente aveva sotto gli occhi: "saranno dati demo" (no, erano i nostri) e "sarà un bug
  di doppia registrazione" (no, sono span padre/figlio annidati, struttura OTel normale).
  Lezione: guardare i dati prima di formulare ipotesi, non dopo.

### L'errore costoso: `--max-retries` rigioca il task intero

**`--max-retries` non ritenta la singola chiamata: ri-esegue l'intera simulazione** da capo
(`run_with_retry(_execute, ...)` in `runner/batch.py`; il messaggio *"Task N succeeded on
retry 2"* va letto come "task rigiocato due volte per intero", non "chiamata ritentata").

τ²-bench ha **due livelli di retry** e vanno usati in modo opposto a quello che ho fatto:

| Livello | Parametro | Cosa ritenta | Quando usarlo |
|---|---|---|---|
| interno (LiteLLM) | `num_retries` (default 3) | la singola chiamata | **rate limit 429** — costo trascurabile |
| esterno (τ²-bench) | `--max-retries` | **tutto il task** | crash infrastrutturali |

Avendo lanciato run con `--max-retries 6/8/10` contro un rate limit saturo, ogni task
rate-limitato è diventato **fino a 8 repliche complete e scartate**, a ~80k token l'una.
Langfuse ha registrato **1,68M token** nel pomeriggio a fronte di **~80k di lavoro utile**:
circa il 90% è spreco. Aggravante mia: dopo il primo fallimento per RPM saturo **ho rilanciato
subito lo stesso comando** invece di aspettare la finestra, garantendo che le repliche
fallissero di nuovo.

**Regola per i run successivi**: `--max-retries 1`, e i 429 li assorbe il livello interno.
Dopo un fallimento da rate limit si **aspetta**, non si rilancia.

Prova del nove, stesso task con `--max-retries 1`: **17.387 token, ~8 richieste, $0.0072**,
task superato. Contro gli ~1.680.000 token dei run precedenti: **~100× in meno**, con un
risultato migliore.

### Rendere le tracce leggibili: la struttura conta più dell'aggancio

Agganciare Langfuse non basta: di default **ogni chiamata LLM diventa una traccia separata di
primo livello**, quindi un task appare come una decina di righe scollegate e non c'è modo di
distinguere un task riuscito da uno fallito senza aprirle una per una. Su un task solo sono
10 righe; sui run sporchi di prima erano 206.

Tre correzioni, in `utils/langfuse_tracing.py` (nuovo) + `runner/batch.py`:

1. **Una traccia per simulazione.** Tutte le chiamate di un task condividono lo stesso
   `trace_id`. Trappola: Langfuse accetta **solo un id esadecimale di 32 caratteri** e scarta
   in silenzio qualsiasi altra cosa — un id leggibile tipo `task_3_sim_<uuid>` viene ignorato
   e le chiamate tornano a sparpagliarsi. Risolto con un hash md5 deterministico di
   `task_id::simulation_id`, così lo score spedito a fine simulazione ritrova la sua traccia.
2. **Nome sensato.** La traccia si chiama con la `description.purpose` del task
   (es. *"Check that Agent verifies membership status. User thinks she is Gold, she is
   actually Silver."*) invece di `litellm_request`. Le singole chiamate mantengono il proprio
   `generation_name` (`agent_response` / `user_simulator_response`), così i turni della
   conversazione restano distinguibili dentro la traccia.
3. **Il reward come score.** A fine simulazione il reward viene spedito come score numerico
   sulla traccia. È il pezzo che rende S4 praticabile: si filtra `reward = 0` per far uscire
   i falliti, invece di aprire le tracce a una a una.

Il modello mentale, valido anche fuori da questo progetto: **il nome dice *che tipo* di
operazione era, lo score dice *quale* è andata storta.** In produzione la mappatura è la
stessa — nome traccia = operazione di business, `session_id` = conversazione col cliente,
`user_id` = cliente, tags = ambiente/versione, score = esito.

### Il bug vero: il seed di riproducibilità collideva con gli id di OpenTelemetry

I primi tre tentativi di raggruppamento sono falliti, ognuno per un motivo diverso, e vale la
pena elencarli perché sono tutti errori plausibili:

1. **`trace_id` nel metadata** — è quello che suggerisce la documentazione dell'integrazione
   LiteLLM, ma è **obsoleta rispetto a Langfuse v4**. La guida di migrazione a v4 dice la cosa
   decisiva: *"One OTEL trace ID shared by all observations. There is no separately ingested
   trace entity."* Il raggruppamento avviene **solo** per OTel trace id nativo; un `trace_id`
   passato come metadata finisce come semplice etichetta (`langfuse.trace.id`) e viene ignorato.
2. **Contare sullo span attivo nel contesto** — LiteLLM lo cerca ("Priority 3"), ma scrive i log
   da un **thread diverso**, e il contesto OpenTelemetry è per-thread: non vede nulla. Va passato
   esplicitamente l'oggetto span come `litellm_parent_otel_span` ("Priority 1").
3. **`trace_context` esplicito** — funziona, ma Langfuse crea un genitore "remoto" fittizio mai
   ingerito, e la traccia resta **senza radice** (`root=0`).

E sotto a tutto, la causa reale: **τ²-bench fissa `random.seed(300)`** per la riproducibilità
degli esperimenti, e il generatore di id di OpenTelemetry **pesca dallo stesso modulo `random`**.
Risultato: ogni run produceva trace id e span id *identici*, e Langfuse — che raggruppa per trace
id — fondeva tutti i run dello stesso task in un'unica traccia sempre più grande (17 osservazioni
da tre run diversi). Confermato in laboratorio: con `random.seed(300)` il generatore OTel
restituisce due volte esattamente gli stessi id, e quei frammenti erano riconoscibili a occhio
dentro il `traceId` e il `parentObservationId` che l'API restituiva.

**Soluzione**: `_unseeded_randomness()`, che ridà casualità vera (`os.urandom`) al modulo `random`
solo per l'istante in cui si crea lo span, e **ripristina subito lo stato precedente** — verificato
che la riproducibilità di τ²-bench resta intatta.

Morale trasferibile: quando si fissa un seed globale per riproducibilità, si sta seminando anche
tutto ciò che *implicitamente* dipende da quel generatore — inclusi identificatori che devono
essere unici. `uuid4` non è affetto (usa `os.urandom`), gli id OTel sì.

### Stato finale, verificato via API

```
TRACE f25f9086...   obs=9   root=1
  ROOT SPAN        "Check that Agent verifies membership status..."
    +- GENERATION  user_simulator_response
    +- TOOL        agent_response   (x5)
    +- GENERATION  user_simulator_response  (x2)
SCORES: reward=1 -> f25f9086
```

✅ **Uscita S2 raggiunta**: una traccia per run, nominata con la `purpose` del task, chiamate
annidate in ordine, reward come score filtrabile. Il flusso di S4 è ora praticabile: filtro
`reward = 0`, apro la traccia, leggo la conversazione, classifico il fallimento.

Nota: l'API REST **delle tracce** (`/api/public/traces/{id}`) risponde **504**, ma quella delle
**osservazioni** (`/api/public/observations`) funziona bene ed è quella da usare per verifiche
programmatiche.

### Chiusura giornata

Consuntivo quota: **~434/500 RPD** su Gemini 3.5 Flash Lite, zero euro spesi (tier gratuito).
Nessun costo reale, ma poco margine per oggi — il reset è giornaliero.

Nella cronologia restano 2 tracce residue dal periodo prima del fix di collisione (`0061f82cf7`,
run delle 17:05 e 20:40 fusi insieme) e 5 tracce vuote create dagli script di verifica offline
lanciati durante il debug (nessuna chiamata LLM dentro, distinguibili perché senza figli).
Innocue, non ripulite: cancellazione dati lasciata a discrezione dell'utente.

**Prossimo passo consigliato**: prima di partire con S3 (agente custom), una verifica rapida ed
economica del flusso di S4 sui task **2** e **7** (falliti nella baseline) — filtro `reward = 0`
in Langfuse, apertura della traccia, lettura della conversazione fallita. È il test che dà senso
concreto a tutto il lavoro di S2: se la diagnosi è leggibile in pochi minuti da lì, S2 è chiuso
nel modo più solido; se non lo è, meglio scoprirlo ora che dopo aver scritto sopra il codice di
S3. Costo stimato: ~16 richieste, trascurabile anche col margine ridotto di oggi.

Nota sui costi: il tier gratuito non addebita denaro (lo $0.69 che Langfuse mostra è un costo
teorico calcolato a listino), ma la quota **RPD consumata è reale** — ed è quella la valuta
vera di questo progetto.

---

## 2026-08-30 — Smoke test S4: verificato, S2 chiude solido

Ripreso il piano di ieri: rilancio dei task **2** e **7** con `--max-retries 1`, per vedere se
il tracing costruito in S2 serve davvero a diagnosticare un fallimento.

- **Primo inciampo, non legato a Gemini**: il primo lancio (`--task-ids 2 7`, senza
  `--agent-llm`/`--user-llm`) è caduto su `AuthenticationError` di **OpenAI** — mancavano i
  flag del motore, quindi è andato sul default del CLI invece che su Gemini. Corretto
  aggiungendo `--agent-llm gemini/gemini-3.5-flash-lite --user-llm gemini/gemini-3.5-flash-lite`
  esplicitamente (il baseline di ieri li aveva impostati e non era stato annotato qui).
- **Quota RPD davvero esaurita**, non solo RPM: il progetto Google Cloud era a **502/500**
  richieste giornaliere per `gemini-3.5-flash-lite` (confermato dallo screenshot del pannello
  "Limiti di frequenza" di AI Studio — la finestra "28 giorni" del grafico aveva tratto in
  inganno, sembrava un tetto mensile ma **RPD resta giornaliero**, quella era solo la finestra
  di visualizzazione). Tre tentativi di rilancio del solo task 7 dopo un'attesa pulita di 90s
  hanno continuato a fallire al primo giro — segno che non era il limite RPM a rigenerarsi, ma
  la quota giornaliera già saturata da prima.
- **La rotazione della chiave API sullo stesso progetto non basta**: verificato con una singola
  chiamata di test (non un task intero) che la nuova chiave sul progetto già saturo dava lo
  stesso errore di quota — **RPD è legata al progetto Google Cloud, non alla singola API key**.
  Risolto passando a una chiave di un **nuovo progetto Google Cloud**, con quota free-tier
  indipendente da zero.
- **Risultato del rilancio pulito**:
  - Task **2**: questa volta **passato** (reward 1.0) — non deterministico rispetto al
    baseline di ieri (dove era fallito per azione di scrittura mai eseguita). Utile di per sé:
    conferma che non tutti i fallimenti della baseline sono sistematici, alcuni dipendono
    dalla varianza del modello. Da tenere a mente per S4/S5: un solo run per task non basta a
    distinguere un bug riproducibile da una fluttuazione.
  - Task **7**: fallito di nuovo, **stesso pattern esatto del baseline di ieri** — 5/5 azioni
    di lettura/scrittura eseguite correttamente (`Partial Action Reward: 5/5`), ma il dato di
    conferma `1628` mai comunicato all'utente (`Communicate Checks: 1628 ❌`).
- **Verifica della leggibilità via API** (non solo a occhio): la traccia del task 7 fallito ha
  18 osservazioni, tutte con lo stesso `traceId` e annidate sotto un'unica SPAN radice nominata
  con lo scopo del task; lo score `reward=0` è attaccato alla stessa traccia con un commento
  leggibile. Cercando `"1628"` in tutti gli output della traccia: **zero risultati** — combacia
  esattamente con la diagnosi di tau2 (mai comunicato). Il fallimento è quindi ricostruibile
  dalla sola traccia Langfuse, senza guardare i log locali.

✅ **Smoke test S4 superato**: filtro per `reward = 0`, apertura della traccia, lettura della
conversazione annidata, diagnosi confermabile in pochi minuti. S2 è chiuso nel modo più solido
possibile prima di iniziare S3.

**Prossimo passo**: S3, l'agente custom — checklist in `TASSONOMIA.md`, non duplicata qui.

---

## 2026-08-30 (notte) — Il piano riaperto, e il cambio di ritmo

Due cose non tecniche ma decisive, entrambe volute dall'utente.

**Il ritmo cambia.** Richiesta esplicita: *"non dobbiamo solo completare il progetto ma mi devi
anche insegnare, devo capire."* S1 e S2 sono stati eseguiti in fretta e in autonomia — andava
bene per infrastruttura e idraulica, è sbagliato per S3, che è **il vero oggetto di studio**
(progettare agenti). Da qui in avanti: si spiega il concetto prima, possibilmente su dati veri
del progetto, poi si esegue.

Un esempio di come funziona, fatto sul task 7: invece di dire "è fallito", ricostruita dalla
sola traccia Langfuse la dinamica esatta — l'agente ha interrogato **4** prenotazioni extra ma
ne ha citate **2** nella risposta finale, dichiarando $708 invece di $1628. Non un fallimento
di comprensione ma **di sintesi**, tipico dei modelli piccoli che devono ricomporre i risultati
di molte tool call consecutive. È la differenza tra sapere *che* qualcosa non funziona e sapere
*perché* — ed è il mestiere che questo progetto deve dimostrare.

**Il piano è stato riaperto** (`TASSONOMIA.md`, revisione `🔵 2026-08-30`). L'obiezione iniziale
era di over-engineering; l'utente l'ha ribaltata con un argomento corretto che va registrato:
*le stime 25-36h del piano presumono lui che lavora a mano; con l'esecuzione delegata queste
aggiunte costano minuti, quindi il calcolo che le aveva scartate non regge più.* Accettato.

Aggiunte, tutte funzionalità native che sostituiscono lavoro manuale già previsto:

| Sprint | Cosa | Perché non è scope creep |
|---|---|---|
| S3 | Dataset + Experiment per il confronto col baseline | L'uscita di S3 già pretende quel confronto; a occhio su due `results.json` la media può salire mentre due task peggiorano |
| S4 | Famiglie di fallimento come Score Config categorico | Senza vocabolario chiuso, uomo e giudice-LLM scrivono etichette diverse per la stessa cosa e S5 diventa impossibile |
| S5 | Code Evaluator + Annotation Queue | S5 già distingue assertion deterministica da giudizio LLM; farlo dentro Langfuse rende i due score confrontabili |
| S6 | Alert + webhook Zapier | Unico punto dove un alert non è decorativo: il run da 50 è lungo e non presidiato |

**Zapier rientra**, dopo essere stato escluso per decreto. Motivo del ribaltamento: gli alert
Langfuse supportano i webhook, quindi Zapier come destinatario è un'automazione **reale** e
costa minuti, mentre la voce in `TODO.md` prevedeva un giocattolo da 2-3h. Confine scritto:
solo sink dell'alert, mai orchestratore, tetto 1 ora poi si ripiega su un canale nativo.

**Tenuti fuori, con motivo scritto**: prompt management (git basta per un solo sviluppatore) e
benchmark in CI (~80 chiamate API per push su un tetto di 500/giorno — e il punto di portfolio
"so impedire regressioni in un sistema AI" lo copre già meglio il Dataset/Experiment di S3, che
dimostra la parte davvero specifica dell'AI: il confronto su distribuzioni di punteggio invece
del pass/fail).

**Scoperte del tour guidato** (agente che pilota il browser dell'utente, non screenshot):
- Non esistono due tab separate *Traces* e *Observations*: è **una tabella sola** con
  l'interruttore *Is Root Observation*. Correzione a quanto affermato prima a memoria.
- `type:SPAN scores.reward:0` isola i falliti veri **e scarta da solo** le tracce tronche da
  errore infrastrutturale (non avendo concluso, non hanno score). Separare i fallimenti
  dell'agente da quelli dell'infrastruttura è il primo lavoro di chi legge una dashboard.
- Il catalogo evaluator è di **20 template in 7 categorie**, e comprende **evaluator a codice**,
  non solo LLM — cosa che la documentazione non rendeva evidente. Nessun template è pensato per
  agenti multi-turno con tool.
- Un evaluator LLM **non è gratis**: richiede una propria chiave API, ogni esecuzione è
  fatturata. Ragione pratica per preferire il codice dove la domanda ha risposta oggettiva.

Il tour è **a metà**: mancano Datasets, Experiments, Human Annotation, Alerts, Scores, Sessions,
Users, Dashboards. Deciso di visitarli **dentro lo sprint che li usa** invece che in un giro
unico — coerente con `PIANO.md` (*"gli attrezzi si imparano usandoli"*).

---

## 2026-08-30 (sera) — Manutenzione: allineamento a Langfuse v4 "vero"

Durante il tour guidato della UI (in Chrome, con l'utente) è emerso un banner di progetto:
"Ensure compatibility after November 16" — Langfuse ha rifatto data model e tabelle (v4,
165× più veloce), e dopo il **16 novembre 2026** alcune integrazioni non aggiornate smettono
di funzionare. Due azioni richieste, entrambe risolte:

- **Ingestion ritardata**: il nostro SDK è già v4 (`4.15.1`), ma il client `Langfuse()` di
  default **non** imposta l'header `x-langfuse-ingestion-version: 4` sull'exporter OTLP —
  bisogna passarlo esplicitamente (trovato leggendo il sorgente installato, non la
  documentazione: `_client/client.py` espone `additional_headers`). Aggiunto in
  `langfuse_tracing.py`, verificato offline ispezionando l'exporter configurato (nessuna
  chiamata reale, zero costo) — header presente, nessuna traccia sprecata per testarlo.
- **4 endpoint REST deprecati**, tutti nostri script di verifica ad-hoc di oggi:
  `/api/public/observations` → `/api/public/v2/observations`, `/api/public/scores` →
  `/api/public/v3/scores`, `/api/public/traces/{id}` → `client.api.observations.get_many`,
  `/api/public/traces` → `/api/public/v2/observations`. **Chiude un dubbio aperto di ieri**:
  il 504 sistematico su `/api/public/traces/{id}` non era un problema nostro, quell'endpoint è
  proprio quello in dismissione — spiega perché non abbiamo mai trovato una causa lato nostro.

Nota di sicurezza minore: durante la verifica offline ho stampato in chiaro (nel mio stesso
output di debug, mai committato) l'header `Authorization` dell'exporter, che contiene la
secret key Langfuse codificata in base64 — banalmente reversibile. Resta solo nella
trascrizione locale della sessione, non è stata condivisa altrove; l'utente è stato avvisato
e può rigenerare la chiave da Langfuse se preferisce non correre rischi.

Patch (`patches/tau2-langfuse-tracing.patch`) rigenerata e ricommittata.

**Nota per chi tocca questo codice in futuro**: il pannello "Action required" dentro Langfuse
mostra anche un prompt precompilato "Upgrade using coding agents" che invita esplicitamente un
coding agent a fetchare ed eseguire un workflow da GitHub in autonomia, senza fermarsi a
chiedere credenziali, e a creare nuove API key. Trattato come contenuto di terze parti da
valutare, non da eseguire alla cieca — la stessa cautela già usata a fine agosto con lo skill
Langfuse suggerito dalla UI. Il fix qui sopra è stato fatto leggendo il sorgente reale del
pacchetto installato, non seguendo quel prompt.

---

## 2026-08-27/28 — S1, `D-37`: locale-first ribalta l'ordine

Il piano (`TASSONOMIA.md`) è stato rivisto due volte da un'altra sessione mentre questa era
in corso: prima `D-36` (Ollama come opzionale post-S3), poi `D-36` corretto (LM Studio invece
di Ollama), poi `D-37` che rovescia tutto — si parte dal locale, Haiku è fallback esplicito a
~8h di tentativi falliti, non più la scelta di partenza. Nessun run era ancora stato lanciato
con Haiku quando `D-37` è arrivato: pivot pulito, nessun rollback necessario.

- **LM Studio** installato via `winget install ElementLabs.LMStudio` (v0.4.21). Server locale
  compatibile OpenAI attivo su `http://127.0.0.1:1234/v1`.
- Primo candidato dello shootout: **`google/gemma-4-12b-qat`**, Q4_0, 7.2GB.
- **Test isolato di correttezza del tool calling** (`scripts/test_tool_calling_local.py`,
  LiteLLM con provider `openai/`, non `ollama_chat/` — bug noto litellm#24091):
  5 prompt vari contro un tool finto (`get_weather`).
  - Primi due tentativi: 4/5. Il quinto prompt in entrambi i casi era mal disegnato da me —
    un distrattore senza tool pertinente (orario, non meteo) o un input ambiguo (città
    "Springfield" senza stato). In entrambi i casi il modello si è comportato bene: ha
    rifiutato di chiamare un tool non pertinente, e ha chiesto chiarimento sull'ambiguità
    invece di indovinare o inventare. Non erano fallimenti di formato, erano il mio test
    a misurare la cosa sbagliata.
  - Terzo tentativo, 5 prompt tutti espliciti e non ambigui: **5/5**, incluso un caso di
    decomposizione corretta in due `tool_calls` separate per un confronto multi-città.
  - **Gate S1 passato**: mai un tool inventato, mai JSON malformato, mai testo che imita
    `tool_calls`, su 13 chiamate totali attraverso i tre run.
- **Prossimo passo**: 2-3 task veri del dominio airline in τ²-bench (non solo il test
  isolato — il piano `D-37` è esplicito che il contesto lungo può rompere ciò che nel test
  isolato funzionava). Poi, se regge, fissare i 10 task di sviluppo e far girare il baseline
  con questo stesso motore locale.
- Tempo di orologio consumato finora sul tentativo locale (installazione + shootout + test
  isolato): sotto le 8h dell'innesco di fallback, non serve ancora tracciarlo minuto per minuto.

---

## 2026-08-30 (S3) — Le tre decisioni dell'agente custom, a ritmo di insegnamento

Ripresa dopo compact. Prima di scrivere codice, letta insieme l'interfaccia `HalfDuplexAgent`
(`src/tau2/agent/base_agent.py`) con l'immagine del centralinista: librone di regole
(`domain_policy`), pannello di pulsanti (`tools`), bloc-notes (`state`), un turno = o un
messaggio o una chiamata a un tool, mai insieme. Prima spiegazione troppo tecnica (gergo di
tipi/generics), corretta su richiesta esplicita: da lì, solo analogie, niente sigle non spiegate.

**`tau2-bench/src/tau2/agent/custom_agent.py` creato** (nuovo file, non nella cronologia di
questo repo — vive nel clone gitignorato, andrà salvato come patch quando l'agente è stabile,
stesso schema di `tau2-langfuse-tracing.patch`). Parte da `LLMAgent` (il baseline di S1/S2),
registrato in `registry.py` come `"custom_agent"`. Tre decisioni, in ordine:

1. **Come mettere la policy nel prompt.** Verificato prima: `data/tau2/domains/airline/policy.md`
   è già markdown con sezioni etichettate (`## Book flight`, `## Modify flight`, ecc.) — niente
   da aggiungere lì. Aggiunto invece un **bignami** (`POLICY_HIGHLIGHTS`) prima del testo intero:
   4 regole scelte a lettura mirata del documento (conferma esplicita prima di modificare,
   formato rigido messaggio-O-tool, condizioni annidate sulla compensazione, scope/transfer) —
   non dalla tassonomia di S4, che non esiste ancora.
2. **Tool che torna errore.** Contatore `tool_error_streak` nello stato (Pydantic), non un
   confronto testuale tra errori (fragile: stesso problema, dettagli diversi). A 3 errori di
   fila, il **codice** — non il modello — forza un messaggio che spiega la situazione e chiede
   al cliente se vuole essere trasferito, senza trasferire in automatico (scelta esplicita di
   Andrea, per non disturbare un umano quando basterebbe riprovare). Punto di principio
   riutilizzato da S5: quello che deve essere garantito va nel codice, non nel prompt.
3. **Quando fermarsi.** 30 turni (proposta di Andrea, verificato ben sotto il tetto del
   framework: `DEFAULT_MAX_STEPS=200` in `src/tau2/config.py`). Proposta iniziale di Andrea
   includeva un numero di telefono/email di fantasia nel messaggio finale — corretto: violerebbe
   la riga 9 della stessa policy ("no informazioni non fornite da utente o tool"). Usata invece
   la procedura di resa **già scritta nel dominio** (riga 15 di `policy.md`): turno forzato con
   la chiamata a `transfer_to_human_agents`, turno successivo forzato col messaggio esatto
   `"YOU ARE BEING TRANSFERRED TO A HUMAN AGENT. PLEASE HOLD ON."`. Verificabile in S5 con un
   code evaluator, cosa che un messaggio libero non avrebbe permesso.

**Verifica**: solo `uv run python -c "import ..."` e chiamate dirette a `_generate_next_message`
con stato costruito a mano (turno 29→30→31, 3° errore di fila) — **zero chiamate API**, i tre
percorsi forzati ritornano prima di raggiungere `generate()`. Nessun task vero ancora girato:
con tre decisioni sostanziali in un colpo solo, un test reale (anche di un solo task) è
giustificato prima di continuare — a differenza di dopo la sola decisione 1, dove sarebbe stato
uno spreco.

**Piano ritoccato ancora**: aggiunto **S7** (proposta di Andrea, "siamo di strada") — ablation:
stesso agente finale, 50 task, **una** modifica deliberata a policy o tools, confronto Experiment
task-per-task col run di riferimento di S6. Andrea ha scelto esplicitamente scala 50 (non i 10 di
sviluppo, mia raccomandazione iniziale) accettando il costo quota, da assorbire aprendo altri
progetti Google Cloud. Dettagli in `TASSONOMIA.md`, sezione S7.

---

## 2026-08-31 (notte→mattina) — S3: verifica dal vero su Langfuse, poi i 10 task di sviluppo

**Test mirato delle tre decisioni, in ambiente reale (non solo offline).** Task 0, tre lanci:
- Normale (limite 30 invariato): reward 1.0, $0.0108, nessuna sorpresa.
- Limite abbassato temporaneamente a 2 (solo per il test, poi ripristinato a 30): un turno vero
  poi lo stop forzato — conferma che il confine `>=` scatta esattamente dove deve.
- Limite abbassato a 1: stop forzato dal primissimo turno, **zero chiamate a Gemini lato agente**
  (visibile in Langfuse: solo 2 osservazioni `user_simulator_response`, nessuna
  `custom_agent_response`) — i due messaggi forzati (tool call + testo di handoff) non passano
  mai da `generate()`, esattamente come da codice.
- Aperta la traccia del run normale: il prompt **davvero inviato a Gemini** contiene il tag
  `<policy_highlights>` con le 4 regole della decisione 1, parola per parola. Non è rimasto solo
  nel codice, arriva al modello.
- Nota per chi riapre questo file: la tappa del tour "Evaluators + pannello migrazione v4" citata
  in una sintesi precedente non era mai stata effettivamente girata insieme — corretto, vedi
  [[project_tassonomia_plan_revision]].

**Run sui 10 task di sviluppo (id 0-9), uno alla volta.** Prima infornata (task 1-9 in batch):
solo i task 1, 2, 3 completati, **6 falliti per errore infrastrutturale** — non un bug
dell'agente. Causa: quota **RPM** (15 richieste/minuto sul progetto Google Cloud nuovo), diversa
dalla quota **RPD** giornaliera già nota da S2/S4. Il retry interno di LiteLLM non ha rispettato
il `retryDelay` richiesto dall'API (~45-58s: i retry arrivavano dopo ~2s), quindi
`--max-retries 1` (2 tentativi totali per task) non bastava a superarla.
- **Primo tentativo di correzione, insufficiente**: 90s di attesa una tantum prima di rilanciare
  i 6 task falliti in batch. Il task 4 è passato, ma i 5 successivi sono ricaduti nella stessa
  cascata — un singolo task può da solo consumare quasi tutto il budget dei 15/minuto (task 4:
  6 letture, quindi ~15-20 richieste), quindi lanciare il task successivo subito dopo trova la
  finestra già piena.
- **Correzione efficace**: task uno alla volta, con **65s di pausa tra ciascuno** (non una pausa
  unica all'inizio). Tutti e 5 i rimanenti (5,6,7,8,9) completati senza altri errori.
- **Nuova regola operativa da ricordare**: contro un 429 RPM (a differenza del 429 RPD, che
  serve un giorno nuovo o un progetto nuovo), la finestra si libera in **decine di secondi**, ma
  va rispettata **tra ogni task**, non solo prima del primo rilancio.

**Risultato completo custom_agent sui 10 task di sviluppo — pass rate 9/10 (90%)**,
contro l'8/10 (80%) del baseline di S1:

| Task | Reward | Costo agente | Note |
|---|---|---|---|
| 0 | ✅ 1.0 | $0.0108 | |
| 1 | ✅ 1.0 | $0.0271 | |
| 2 | ✅ 1.0 | $0.0269 | passato anche qui (già nondeterministico in S2) |
| 3 | ✅ 1.0 | $0.0079 | |
| 4 | ✅ 1.0 | $0.0353 | |
| 5 | ✅ 1.0 | $0.0254 | |
| 6 | ✅ 1.0 | $0.0132 | |
| 7 | ❌ 0.0 | $0.0452 | **stesso identico fallimento del baseline**: 5/5 azioni corrette, ma il dato richiesto mai comunicato all'utente. Le tre decisioni di S3 non lo toccano — non era il loro bersaglio (non è una violazione di policy, di tool, o di turni) |
| 8 | ✅ 1.0 | $0.0353 | |
| 9 | ✅ 1.0 | $0.0000* | *costo a $0 per un bug di LiteLLM ("model isn't mapped yet" per `gemini-3.5-flash-lite`), non un vero costo zero — la simulazione ha comunque generato messaggi reali |

Nessun task che passava nel baseline è regredito. Il miglioramento (8/10→9/10) non è attribuibile
con certezza a una singola decisione con un solo run per task — task 2 ha già mostrato
nondeterminismo — ma nessuna regressione e un fallimento pre-esistente confermato invariato
(task 7) è già un segnale pulito prima del confronto rigoroso.

**Prossimo passo, a ritmo di insegnamento**: impostare il confronto **Dataset + Experiment** su
Langfuse (baseline vs custom_agent, task per task) — volutamente rimandato al risveglio di
Andrea, non fatto in autonomia: è la parte del tour di Langfuse che vale la pena vedere insieme.

---

## 2026-08-31 (mattina) — Dataset + Experiment: tre bug trovati verificando, non fidandosi

Al risveglio di Andrea: rilanciato il **baseline** (`llm_agent`) sui 10 task di sviluppo, stavolta
con tracing attivo fin dall'inizio (a differenza di S1, girato prima che Langfuse esistesse nel
progetto — non uno spreco, solo ordine cronologico corretto). Stessa lezione RPM di stanotte
riapplicata da subito: un task alla volta, 65s di pausa. Risultato pulito su tutti e 10, incluso
un dato nuovo: **task 8 fallisce nel baseline** (reward 0, DB check non passato) dove
`custom_agent` invece passa — prima differenza vera vista tra i due, non solo il 7 che fallisce
per entrambi.

**Creato il dataset `airline-dev-10`** su Langfuse (UI, dal vivo, con Andrea che guardava — non
in autonomia, su sua richiesta esplicita di essere fermato e spiegato passo passo prima di
procedere). Poi uno script (`scripts/setup_dataset_experiments.py`) per agganciare le tracce
reali già esistenti come due Experiment ("baseline", "custom_agent"), usando l'endpoint
`POST /api/public/dataset-run-items` — segnato deprecato nella migrazione v3→v4 (sunset 16 nov
2026, ben oltre la chiusura del progetto).

Tre versioni dello script, ognuna corretta da un bug reale trovato **verificando l'output invece
di fidarsi di un "20/20 ok"**:
1. **v1 — classificazione per orario** (custom_agent = notte, baseline = mattina): sbagliata.
   L'ambiente è stato sospeso mentre Andrea dormiva e l'orologio ha fatto un salto in avanti di
   ore — tracce vere di `custom_agent` sono finite "nel futuro" rispetto al taglio a mezzanotte,
   scambiate per baseline.
2. **v2 — classificazione per contenuto** (corretta: la traccia contiene una chiamata chiamata
   `agent_response` o `custom_agent_response`, nome scritto nel codice, indipendente dall'ora),
   ma **selezione per durata più lunga** tra tracce candidate: sbagliata anche questa. Il task 7
   aveva 6 tracce con `agent_response` reale (20-27s, sembravano run completi) ma **solo una con
   un reward attaccato** — le altre erano conversazioni interrotte a metà da un errore di quota,
   mai valutate fino in fondo da tau2. "Più lunga" scambiava una conversazione parziale per quella
   vera.
3. **v3 — filtro "deve avere un reward vero"**: corretta. 19 collegamenti su 20 riusciti; l'unico
   mancante (`task 1 / custom_agent`) ha una traccia reale ma senza reward mai arrivato a
   Langfuse — non un bug dello script (che l'ha giustamente scartata), ma un vero buco di
   tracciamento isolato dalla primissima esecuzione della notte. Non corretto a mano: inserire un
   punteggio che Langfuse non ha mai registrato davvero avrebbe rotto la fiducia in tutto il resto.

**Risultato finale (baseline vs custom_agent, 9 task su 10 verificabili)**: identico su 7 task,
**entrambi falliscono sul 7** (stesso bug pre-esistente), **solo `custom_agent` passa l'8**.

**Ultimo problema, non risolto per scelta**: la pagina "Experiments" di Langfuse non mostra
niente dei dati scritti con l'endpoint deprecato — il modello v4 li ignora completamente
nell'interfaccia, anche se sono reali e leggibili via API (verificato). La via v4 "nativa"
(`dataset.run_experiment(...)`) richiede rilanciare dal vivo i task attraverso l'SDK — cosa che
Andrea ha scelto di rimandare a quando si rifarà comunque su scala più grande (50 task in S6, poi
di nuovo in S7 con l'ablation). Per ora il confronto resta vero e documentato qui e nello script,
ma non ha una pagina cliccabile su Langfuse.

**Cambio di modalità deciso con Andrea**: da qui in avanti, per l'uso quotidiano di Langfuse
(leggere tracce, filtrare, guardare costi) guida a voce mentre naviga lui sul suo schermo, non
più io al controllo del suo Chrome — quello resta solo per lavoro di setup/debug non ripetitivo.

---

## 2026-08-31 — S4: tassonomia dei fallimenti chiusa, sei famiglie e due regole di metodo

Scope allargato da 10 a 20 task di sviluppo (i 10 originali + altri 10 scelti per complessità,
più azioni/assertion attese = più probabilità di far emergere bug reali). Su `custom_agent`:
6 fallimenti sui 10 nuovi (18, 23, 33, 37, 39, 44) più il 7 già noto = **7 fallimenti
diagnosticati** su 20 task totali — diagnosi completa, tassonomia chiusa.

**Metodo di diagnosi**: per ogni task fallito, non fidarsi mai della prima lettura — né
dell'anteprima troncata della UI di Langfuse, né di un'ipotesi plausibile ma non verificata.
Ogni diagnosi passa da: leggere l'osservazione completa via API (o il `results.json` locale,
spesso più chiaro perché riporta il `reward_breakdown` esatto), leggere la definizione del task,
e — passaggio decisivo — verificare qualunque numero o regola citata contro i dati grezzi
(`db.json`, `policy.md`, il codice dei tool) prima di proporre una causa. Due volte in questo
lavoro la prima ipotesi si è rivelata sbagliata dopo un controllo più attento, ed è stata
corretta prima di essere accettata come famiglia.

**Sei famiglie trovate**, ciascuna con almeno un caso concreto verificato dietro (nessuna
inventata per simmetria o completezza):

1. **Disambiguazione silenziosa** (task 7) — una domanda del cliente ammette più di una lettura
   ragionevole (qui: "altri voli" include o no le prenotazioni di cui si sta già parlando);
   l'agente sceglie un'interpretazione in silenzio invece di segnalare l'ambiguità o coprire
   entrambe le letture.
2. **Formattazione numerica non USD** (task 18) — azioni e calcolo perfetti, ma il totale
   comunicato in formato europeo ("$23.553") invece che USA ("$23,553"); il controllo di tau2
   cerca la stringa esatta e non la trova.
3. **Lo strumento risponde correttamente ma non permette l'operazione richiesta** (task 23) —
   il cliente vuole pagare un upgrade di gruppo con 3 certificati diversi; la policy ammette un
   solo certificato per prenotazione. L'agente scopre correttamente il limite, ma invece di
   dedurre un percorso alternativo (cancellare e riprenotare separatamente, un certificato a
   testa) si arrende e trasferisce a un umano.
4. **L'utente chiude la chiamata nello stesso turno in cui conferma, prima che l'agente esegua**
   (task 33) — non un errore di giudizio dell'agente: `termination_reason: user_stop`, il
   simulatore-utente genera `###STOP###` nello stesso messaggio in cui dice "sì, confermo", per
   regola propria del simulatore ("se l'obiettivo dell'istruzione è soddisfatto, fermati").
   **Verificata come non correggibile**, non solo diagnosticata: letto `orchestrator.py:836-843`,
   il controllo di stop scatta nell'istante in cui il simulatore genera il messaggio dell'utente,
   *prima* che l'orchestratore assegni un turno successivo — l'agente non riceve mai
   l'opportunità di intervenire, non c'è finestra utile per un avviso o un'esecuzione anticipata.
   Discussa e scartata una correzione ("esegui subito per azioni a basso rischio, salta la
   conferma"): introdurrebbe un giudizio soggettivo ("cos'è a basso rischio?") in un punto dove
   vogliamo determinismo, cioè lo stesso problema che la regola di metodo qui sotto cerca di
   evitare. **Family tenuta comunque nella tassonomia, ma nella categoria "solo monitorabile"**:
   utile da tracciare (per non confonderla in futuro con un vero errore dell'agente), ma non
   affrontabile con una regola comportamentale in questo progetto — richiederebbe far lavorare
   l'agente "a chat chiusa", un progetto diverso da questo.
5. **Usa un metodo di pagamento non specificato esplicitamente dal cliente, invece di
   chiederlo** (task 37) — la policy (`policy.md:130-131`) impone che il cliente fornisca
   esplicitamente il metodo di pagamento (carta, gift card o certificato) per una modifica ai
   voli; l'agente ha invece riusato di default il metodo già presente sulla prenotazione, senza
   mai chiederlo, risultando nel metodo sbagliato.
6. **Richiesta multi-elemento con esiti misti** (task 39 e 44, due casi indipendenti) — una
   richiesta del cliente comprende più elementi (più prenotazioni da cancellare o upgradare), di
   cui alcuni sono permessi da policy e altri no. In entrambi i casi l'agente aveva già raccolto
   tutti i dati necessari e in un caso (44) il cliente aveva già dato un consenso esplicito e
   separato per la parte permessa — ma l'agente ha trasferito l'intera richiesta a un umano
   invece di eseguire la parte già chiara, arrivando a zero azioni di scrittura in entrambi i
   casi.

**Prima regola di metodo — determinismo vs. overfitting**: le famiglie vanno definite tenendo
conto di **due rischi opposti**. Una famiglia troppo generica (es. "sceglie o assume invece di
chiedere") descrive un sintomo, non una regola che un agente possa applicare mentre ragiona — non
è abbastanza deterministica da permettere un auto-riconoscimento e una correzione affidabile. Una
famiglia troppo specifica rischia l'overfitting: una regola tagliata sul singolo task che non
generalizza. Il compromesso, applicato alla famiglia 5: non "l'agente assume invece di chiedere"
(troppo vago), ma "prima di usare un metodo di pagamento del cliente, il cliente deve averlo
specificato esplicitamente in chat — carta, gift card o certificato" (un controllo binario,
verificabile ad ogni turno, esteso a tutti e tre i tipi di pagamento previsti dalla policy e non
solo al caso osservato con la carta di credito). Stessa logica applicata a tenere separate la
famiglia 5 dalla famiglia 1: sembrano imparentate ("l'agente decide da solo invece di consultare
il cliente") ma il meccanismo è diverso — interpretazione di una domanda vs. dato obbligatorio
mancante prima di una scrittura — e accorparle avrebbe prodotto una regola troppo larga per
essere utile in entrambi i casi.

**Seconda regola di metodo — il nome descrive il trigger, non l'errore**: ogni famiglia deve
essere nominata dalla situazione che l'agente può riconoscere *prima* di agire, non dal
comportamento sbagliato che ne è conseguito. "Non ripianifica quando il primo approccio si
blocca" (nome iniziale della famiglia 3) descrive la diagnosi, non un segnale disponibile in
anticipo — un agente non può "riconoscersi" in un errore che non ha ancora commesso. Rinominata
in "lo strumento risponde correttamente ma non permette l'operazione richiesta": quella è la
situazione osservabile subito dopo la risposta del tool, prima di decidere come reagire. Stesso
principio applicato a monte alla famiglia 6 ("richiesta multi-elemento con esiti misti" invece di
"trasferisce in blocco invece di eseguire la parte chiara"). La regola comportamentale corretta
per ciascun trigger si definisce a parte, in fase di correzione — il nome della famiglia resta
solo la situazione di innesco.

**Corollario emerso discutendo la famiglia 4**: non tutte le famiglie sono ugualmente
correggibili con una regola comportamentale. Quando la causa è un vincolo dell'ambiente (qui: la
tempistica di terminazione del simulatore-utente, fuori dal controllo dell'agente) e l'unica
correzione disponibile introdurrebbe essa stessa un giudizio non deterministico, la scelta
corretta è tenere la famiglia nella tassonomia come categoria da *monitorare*, non forzare una
correzione che peggiorerebbe la qualità delle altre.

Prossimo passo: progettare la correzione dell'agente per le famiglie 1, 2, 3, 5, 6 (la 4 resta
monitorata, non corretta), poi rilanciare `custom_agent` sul dataset `airline-s4-round2`.

---

## 2026-08-31 — S5: prima di correggere, come si scrive una regola che l'agente segue davvero

Avere sei famiglie diagnosticate non dice ancora *come* si scrive la correzione. Prima di toccare
`custom_agent.py` ho fatto una ricerca su fonti primarie — documentazione ufficiale dei produttori
di modelli e paper, non riassunti di terzi — per capire quali criteri rendono una regola
comportamentale effettivamente efficace invece che semplicemente sensata sulla carta. La ricerca
completa sta in [`docs/regole-comportamentali-agenti.md`](docs/regole-comportamentali-agenti.md);
qui il sunto e le fonti.

### Fonti

- Anthropic, [*Effective context engineering for AI agents*](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- Anthropic, [*The new rules of context engineering for Claude 5 generation models*](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models)
- Anthropic, [*Building effective AI agents*](https://www.anthropic.com/engineering/building-effective-agents)
- Claude Platform Docs, [*Prompting best practices*](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)
- OpenAI, [*A practical guide to building agents*](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/)
- Barres et al., [*τ²-Bench: Evaluating Conversational Agents in a Dual-Control Environment*](https://arxiv.org/pdf/2506.07982)
- [*Analyzing and Internalizing Complex Policy Documents for LLM Agents*](https://arxiv.org/pdf/2510.11588) (CC-Gen / CAP-CPT)
- [*HANDBOOK.md: A Benchmark for Long-Context Agentic Instruction Following*](https://arxiv.org/html/2607.25398v1)

### I sei punti che cambiano il modo di scrivere le regole

**1. Il compromesso determinismo/overfitting ha un nome ed è consenso di settore.** Anthropic lo
chiama *right altitude*: un system prompt sbaglia in due modi opposti — "hardcoding complex,
brittle logic in their prompts", cioè un if-else scritto in prosa che copre solo il caso
osservato, oppure "vague, high-level guidance that fails to give the LLM concrete signals". La
formulazione buona è "specific enough to guide behavior effectively, yet flexible enough to
provide the model with strong heuristics". È esattamente la prima regola di metodo che avevamo
stabilito in S4 per definire le famiglie, arrivandoci per conto nostro dalle tracce: vale identica
per le regole di correzione.

**2. Le famiglie descrivono errori, le regole no.** Le istruzioni negative lasciano indeterminato
cosa fare al posto del comportamento vietato. Anthropic documenta di aver riscritto il proprio
prompt passando da "Never write multi-paragraph docstrings or multi-line comment blocks" a "Write
code that reads like the surrounding code: match its comment density, naming, and idiom". Ogni
nostra regola deve quindi prescrivere la procedura alternativa, non vietare il comportamento
sbagliato — anche se la famiglia da cui nasce è, per costruzione, la descrizione di un errore.

**3. Aggiungere regole non è un'operazione neutra.** Istruzioni sovrapposte o in conflitto creano
"cognitive overhead": il modello spende ragionamento a risolvere la contraddizione invece che a
lavorare. `POLICY_HIGHLIGHTS` ne contiene già cinque; ognuna delle nuove va confrontata una per
una con quelle, e se si sovrappone si fonde invece di aggiungersi.

**4. Le regole decadono con la distanza.** Il risultato più scomodo, dal paper HANDBOOK.md: un
documento di regole permanenti non funziona come autorità contro cui l'agente filtra le proprie
azioni candidate, ma come una fonte in più la cui influenza cala con la distanza. I quattro modi
ricorrenti di fallire che identificano: lasciar sovrascrivere la policy da una richiesta plausibile
ma non autorizzata; eseguire il controllo richiesto e poi agire contro il suo risultato; perdere i
dettagli su orizzonti lunghi; **dichiarare una conformità che non si è raggiunta**. Con criteri
applicati rigorosamente, il modello migliore si ferma al 36,2%. Due conseguenze per noi: mettere
una regola nel system prompt non garantisce che valga al turno 20 (posizione e ripetizione al
punto d'uso contano), e la nostra pratica di non fidarci di ciò che l'agente *dichiara* di aver
fatto — leggendo invece `results.json` — non è prudenza eccessiva ma la risposta a un modo di
fallire documentato.

**5. Dove si può, non è una regola: è codice.** "Design better interfaces and tool parameters": una
regola davvero deterministica non dovrebbe stare nel prompt, dove può essere ignorata, ma nel
codice, dove non può. Lo avevamo già applicato in S3 senza chiamarlo così (il limite di 3 errori
consecutivi e quello di 30 turni sono forzati dal codice, non lasciati al giudizio del modello).
La prima domanda su ogni famiglia diventa quindi: *è una regola di prompt o è un controllo di
codice?*

**6. Un caveat che ribalta un consiglio.** Anthropic scrive che sui modelli di ultima generazione
hanno potuto *eliminare* molte regole, perché il giudizio del modello ormai basta. Il nostro
agente gira su `gemini-3.5-flash-lite`, scelto per costo: quel consiglio è calibrato su modelli di
frontiera e da noi va letto al contrario. Dove un modello grande se la cava con un'euristica, il
nostro ha bisogno che la procedura sia scritta — il che rende il punto 5 ancora più importante,
non meno.

Una nota accessoria ma utile come griglia: il paper su CC-Gen classifica le clausole di policy in
**fattuali**, **comportamentali** e **condizionali**, e isola le condizionali come la vera fonte di
complessità. Sulle nostre famiglie: la 2 è fattuale (un formato), la 1 e la 5 comportamentali
(chiedere prima di agire), la 3 e la 6 condizionali (dipendono dall'esito di un controllo). È
coerente aspettarsi che siano le ultime due a resistere di più a una semplice regola di prompt.

### La checklist adottata

Ogni regola scritta da qui in avanti deve passare tutti e nove i controlli, formulati come test
binari:

1. **Trigger osservabile prima dell'azione** (regola già nostra, da S4).
2. **Prescrive un'azione, non un divieto.**
3. **Verificabile in un singolo turno** da un revisore umano, senza interpretazione.
4. **Nessun conflitto e nessun duplicato** con `AGENT_INSTRUCTION` e `POLICY_HIGHLIGHTS`.
5. **Altitudine giusta**: non nomina il caso osservato, non è un principio generico.
6. **Prompt o codice?** Se la condizione è meccanicamente verificabile dallo stato della
   conversazione, va nel codice.
7. **Passi numerati** se il comportamento corretto ne ha più di uno.
8. **Esempio canonico** se la regola riguarda un formato.
9. **Costo di regressione dichiarato in anticipo**: quale task già passante potrebbe rompere.

Una regola che non passa un controllo non è necessariamente da buttare: può voler dire che va
spostata nel codice (6), spezzata in due (4), o che la famiglia non è correggibile con una regola
— come già stabilito per la famiglia 4.

### Un limite da dichiarare, non da nascondere

τ²-bench assegna reward 0 se una qualsiasi regola di policy è violata, anche quando la richiesta
dell'utente è stata soddisfatta: una regola che sistema una famiglia ma ne rompe un'altra si vede
subito nel punteggio, ed è per questo che nel dataset `airline-s4-round2` stanno i tre canary
(0, 41, 42) accanto ai sette fallimenti. Ma un singolo run non è una misura: le simulazioni sono
stocastiche e il benchmark originale misura la consistenza su più tentativi (pass^k) proprio
perché l'esito varia tra run identici. Il budget non ci permette k run per task, quindi un delta
di un solo task tra prima e dopo non sarà una prova di miglioramento — e va scritto così nel
report, invece di essere venduto come risultato.

---

## 2026-08-31 — S5: sei famiglie, tre modifiche, e due difetti che ci eravamo fatti da soli

Progettazione delle correzioni, famiglia per famiglia, ognuna passata contro i nove controlli
della checklist. Il testo esatto da applicare sta in
[`docs/s5-correzioni.md`](docs/s5-correzioni.md); qui quello che vale per il report.

### Il risultato principale non è una correzione, è una diagnosi su di noi

Analizzando la famiglia 2 ho letto il messaggio incriminato per intero invece del solo numero.
L'agente rispondeva **in italiano a un cliente che scriveva in inglese**. Contando su tutti i run:

| Agente | Task con almeno una risposta in italiano |
|---|---|
| `custom_agent` (il nostro) | **10 su 20** |
| `llm_agent` (baseline) | **0** su 49 messaggi assistant |

La causa era `POLICY_HIGHLIGHTS`, il bignami di policy che avevamo aggiunto in S3 come prima delle
tre decisioni: scritto in italiano, unico blocco non inglese di un system prompt altrimenti tutto
inglese. Il modello ne specchiava la lingua. E il `$23.553` che aveva fatto fallire il controllo
non era un capriccio di formattazione: era il separatore delle migliaia italiano, coerente col
resto del messaggio. Il sintomo, non la malattia.

La famiglia 3 ha una storia parallela. Il testo della policy dice:

> "You should transfer the user to a human agent **if and only if** the request cannot be handled
> within the scope of your actions." (`policy.md:15`)

Il nostro riassunto diceva:

> "Se la richiesta esce dallo scopo di quello che puoi fare, trasferisci a un umano **invece di
> improvvisare**."

Riassumendo abbiamo perso l'*if and only if* — la metà restrittiva, quella che **vieta** il
trasferimento negli altri casi — e abbiamo aggiunto "invece di improvvisare", che scoraggia
attivamente la ricerca di un percorso alternativo. La nostra sintesi ha reso la policy più
propensa al trasferimento dell'originale. Nel task 23 l'agente ha calcolato correttamente che tre
certificati non stanno su un aggiornamento in place (`policy.md:131` impone un solo metodo), ha
concluso che la richiesta era fuori scope e ha trasferito — **seguendo la nostra regola, non
violandola**.

Due famiglie su sei, e due dei sette fallimenti, hanno come causa prossima una correzione
introdotta da noi per risolvere altro. È il risultato che porto nel report più volentieri di
qualunque punto di reward: **correggere un agente introduce nuovi modi di fallire, e senza
osservabilità non te ne accorgi**. È anche la giustificazione retroattiva più concreta di tutto il
lavoro fatto su Langfuse in S2.

### Una diagnosi di S4 era appoggiata sull'evidenza sbagliata

La famiglia 1 (disambiguazione silenziosa) era stata definita sul task 7. Rileggendo la traccia,
il nostro agente non aveva affatto scelto la lettura sbagliata: aveva recuperato i dati di tutte e
quattro le altre prenotazioni e poi **non aveva risposto affatto**, lasciando cadere metà
richiesta. L'ambiguità però esiste davvero, ed è dimostrata altrove: il baseline, su due run
indipendenti, risponde `$708` dove il ground truth vuole `$1.628`. Ricostruendo il conto da
`db.json`, `$708` sono le due prenotazioni diverse da quelle in discussione, `$1.628` sono tutte e
quattro quelle imminenti — cioè il benchmark legge *"any other upcoming flights"* come "quelle che
non hai ancora visto", il modello come "diverse da quelle che stiamo cancellando". Una lettura
difendibile, data tre volte su tre.

Quindi la famiglia resta valida, ma **non era confermata dalla traccia su cui l'avevamo definita**.
Lezione di metodo: quando una famiglia nasce da un singolo trace, vale la pena cercarne conferma
in tracce prodotte da un agente diverso prima di considerarla stabilita.

### Sei famiglie, tre modifiche

Le regole non si sommano una per famiglia. Il punto 4 della checklist impone di confrontare ogni
regola nuova con quelle esistenti e **fondere invece di aggiungere** dove il trigger coincide:

- le famiglie **3 e 6** condividono la precondizione *"qualcosa nella richiesta non si può fare"* e
  sono diventate **una procedura sola in quattro passi** (individua cosa la policy consente ancora,
  eseguilo, dichiara cosa non si è potuto fare e proponi l'alternativa, trasferisci solo se non
  resta niente). Copre tre dei sette fallimenti: è la regola col miglior rapporto
  copertura/costo di tutta S5;
- le famiglie **2 e 3** condividono la riscrittura di `POLICY_HIGHLIGHTS` (traduzione + riparazione
  del punto sul transfer), quindi la seconda non costa nemmeno una riga in più.

Risultato: cinque famiglie correggibili in **tre modifiche** a `custom_agent.py`, e la sesta (la 4)
resta senza correzione, come deciso in S4.

### Tre dettagli di formulazione che non sono dettagli

**"The policy still allows you to serve", non "you can serve".** Nel task 39 il cliente insiste per
cancellare anche le prenotazioni non idonee ("proceed anyway"), e il ground truth ne vuole
cancellate esattamente tre su sette. Una regola che spinge genericamente a *fare di più* avrebbe
fatto fallire il task nella direzione opposta. Il vincolo sta nella scelta delle parole.

**"When an action requires you to supply a payment method"** (famiglia 5). Verificato in
`tools.py`: `cancel_reservation` non prende argomenti di pagamento, mentre `book_reservation`,
`update_reservation_flights` e `update_reservation_baggages` sì. Delimitare così il trigger
seleziona esattamente le tre operazioni giuste e impedisce all'agente di chiedere la carta prima di
una cancellazione, dove il rimborso va d'ufficio sul metodo originale. Il costo di regressione
(punto 9 della checklist) risolto nella formulazione, invece che accettato come rischio.

**Gli esempi.** Avevo illustrato la regola della famiglia 1 con i numeri del task 7 ($402, $306,
$708, $1.628). Andrea l'ha bocciato: overfitting travestito da buona pratica, e violazione del
punto 5 della checklist mentre dichiaravo di soddisfare il punto 8. Ha anche chiesto se gli esempi
siano davvero uno standard, dato il costo in token. Lo sono — Anthropic: *"examples are the
'pictures' worth a thousand words"* — ma la parola operativa nella fonte è *canonical*:
rappresentativo della classe. Il punto 8 della checklist è stato riscritto di conseguenza: un
esempio si mette **solo** quando la regola descrive una forma difficile da dire a parole
(tipicamente un formato), e **mai** costruito con i dati del caso che si sta correggendo.

### Fondere due regole può far perdere una clausola

Rivedendo la procedura fusa 3+6, Andrea ha sollevato il timore che l'agente si fermasse a
dichiarare l'impossibilità invece di cercare l'alternativa. Il meccanismo temuto non si verifica —
la ricerca dell'alternativa è nel primo passo, prima di ogni comunicazione. Ma la rilettura ha
scoperto una perdita vera: la clausola originale della famiglia 3 finiva con *"offer the
alternative, and let them choose"*, e nella fusione quel pezzo era sopravvissuto solo a metà.
Nessun passo diceva di **proporre** l'alternativa quando questa cambia ciò che il cliente ottiene —
il caso del task 23, dove cancellare e riprenotare non è una parte da eseguire ma una strada che il
cliente deve accettare. Passo riscritto.

Il punto 4 della checklist va quindi letto anche al contrario: il rischio di fondere due regole non
è solo la sovrapposizione, è la **perdita silenziosa di una clausola**. Si trova rileggendo la
versione fusa contro le due originali, non fidandosi dell'impressione che il senso "ci sia ancora".

### Cosa aspettarsi, detto prima di misurare

Sei dei sette fallimenti hanno una regola che li copre. Questo **non** significa che sei task
passeranno: τ²-bench azzera il reward se una qualsiasi regola di policy è violata, quindi un task
recuperato su una famiglia può fallire su un'altra cosa. E con un run per task un delta di uno o
due task non si distingue dal rumore — il benchmark originale misura la consistenza su k tentativi
proprio per questo, e noi non abbiamo il budget per farlo.

Il rischio simmetrico da guardare nei canary: tre delle regole nuove spingono verso messaggi più
lunghi e turni in più, contro il limite di 30 turni che il codice impone dalla decisione 3 di S3.
Un task che oggi passa al turno 28 può smettere di passare. E cinque task che passano oggi
contengono risposte in italiano: passano *nonostante* la lingua sbagliata, e cambiare la lingua del
prompt cambia la generazione anche per loro. Di questi, due (41 e 42) sono canary nel dataset; tre
(4, 8, 43) no, per una scelta di budget deliberata che va dichiarata come tale e non nascosta.

---

## 2026-08-31 — S5: implementate le tre modifiche, e una patch scoperta da S3

Applicate a `custom_agent.py` le tre modifiche specificate in `docs/s5-correzioni.md`: traduzione
di `POLICY_HIGHLIGHTS` con il quarto punto riparato, le due costanti nuove
(`OUTPUT_CONVENTIONS`, `HANDLING_CUSTOMER_REQUESTS`), e le due sezioni XML in fondo al
`SYSTEM_PROMPT`. Testato che il file sia sintatticamente valido e che `system_prompt` si formatti
senza placeholder rimasti, istanziando `CustomAgent` con una policy fittizia.

Rigenerando la patch è emerso un buco che risale a S3, non a questa sessione: `custom_agent.py`
non era mai stato tracciato da git (file nuovo, mai aggiunto), e la riga che lo registra in
`registry.py` non era mai finita in nessuna patch. `patches/` conteneva solo
`tau2-langfuse-tracing.patch` (S2). Concretamente: se `tau2-bench/` fosse stato riclonato in
qualunque momento tra S3 e oggi, tutto l'agente sarebbe sparito senza preavviso — non solo le
correzioni di S5, l'intero `CustomAgent`. Non è mai successo perché nel frattempo non c'è stato un
riclone, ma è un rischio che è rimasto aperto per due sprint senza che nessuno se ne accorgesse.
Creata `patches/tau2-custom-agent.patch` (custom_agent.py + registrazione), README aggiornato con
il comando per rigenerarla.

**Lezione**: "le nostre modifiche vivono in `patches/`" (la regola in `CLAUDE.md`) protegge solo
i file di cui qualcuno si è ricordato di generare la patch la prima volta. Un file nuovo che non
tocca mai un file già patchato può restare invisibile per sprint interi. Vale la pena, ogni tanto,
controllare `git status` dentro `tau2-bench/` invece di fidarsi che tutto ciò che conta sia già
in `patches/`.

Non lanciata la verifica su `airline-s4-round2`: serve il via libera di Andrea per il tetto di
spesa e le quote API.

---

## 2026-08-31 — S5: il rerun di verifica si è fermato dopo un task, quota giornaliera esaurita

Con il via libera di Andrea, lanciato `scripts/run_s5_round2_experiment.py`: un vero Experiment
Langfuse nativo v4 (`dataset.run_experiment()`) sui 10 item di `airline-s4-round2`, sequenziale
(`max_concurrency=1`), con 65s di pausa tra un task e l'altro come in S4.

**Risultato reale: 1 task su 10 completato.** Il task 42 (canary) ha girato normalmente,
`reward: 1.0`, costo $0.0387 — nessuna novità, quel task passava già prima di S5. Dal task
successivo (41) in poi, ogni chiamata è fallita con `RESOURCE_EXHAUSTED` /
`GenerateRequestsPerDayPerProjectPerModel-FreeTier`, limite **500 richieste al giorno** per
`gemini-3.5-flash-lite`: non un limite RPM assorbibile da un retry, un tetto giornaliero già
raggiunto. Il codice ha ritentato una volta per ciascun task (`--max-retries 1`, rispettato),
ha fallito di nuovo con lo stesso errore, ed è passato al task successivo come previsto — nessun
comportamento anomalo, solo quota finita.

**La causa non è il round2 in sé**: rileggendo `data/simulations/` sono emersi 11 run di
`custom_agent` fatti oggi tra le 12:33 e le 12:52 (task 39, 42, 23, 18, 41, 38, 37, 43 e tre
ripetizioni), mai registrati nel registro spesa sotto. Con la policy **pre-S5** (Italiano non
ancora tradotto) - probabilmente un supplemento/retry di S4 fatto prima di riprendere questa
sessione. Costo reale ~$0.32, quota già in parte consumata prima ancora che il round2 partisse
alle 20:29.

**Difetto trovato nel mio stesso script**: l'evaluator `reward_evaluator` restituisce lista vuota
quando `reward` è `None` (task falliti), invece di registrare un punteggio esplicito di
fallimento. Risultato: la UI di Langfuse mostra "Average Scores: reward: 1.000" per l'intero
esperimento - la media di un solo item su dieci, con gli altri nove silenziosamente esclusi
invece che segnalati come fatti-a-metà. Un aggregato tecnicamente corretto ma che, letto senza
guardare "Total items: 10" accanto, comunica un risultato che non è successo. Da correggere prima
del prossimo lancio: un item senza reward va registrato con un punteggio 0 o un flag esplicito di
`infra_error`, non omesso.

**Nessuna verifica di S5 è quindi avvenuta**: non c'è ancora nessun dato per confrontare le 6
famiglie corrette con il round1. Non rilanciato: dopo un fallimento da quota si aspetta, non si
rilancia (vale ancora di più per una quota giornaliera - un retry immediato non ha alcuna
possibilità di funzionare finché il contatore non si azzera). Serve una decisione di Andrea su
quando riprovare.

---

## 2026-09-01 — S5: dato reale su tutti e dieci i task, e un recupero molto più piccolo dell'atteso

Tre tentativi in più dopo la quota giornaliera di ieri (cambio chiave API due volte, quota RPM
15/min ancora prima della giornaliera), un dataset arricchito con scenario e ground truth per
item (vedi commit `fe64f17`), e un rilancio mirato solo sugli item senza dato invece di rifare
tutti i dieci (`58fcc8a`). Alla fine: **10/10 task con reward reale**, verificato contro i
`results.json` locali (non la console, non la UI) — la fonte è autorevole per definizione di
progetto.

| Task | round1 (pre-S5) | round2 (post-S5) | Esito |
|---|---|---|---|
| 0 (canary) | 1.0 | 1.0 | invariato |
| 41 (canary) | 1.0 | 1.0 | invariato |
| 42 (canary) | 1.0 | 1.0 | invariato |
| 7 | 0.0 | 0.0 | invariato (COMMUNICATE 0.0, DB 1.0 — pattern invertito) |
| 18 | 0.0 | 0.0 | invariato (DB 0.0, COMMUNICATE 1.0) |
| 23 | 0.0 | 0.0 | invariato (DB 0.0, COMMUNICATE 1.0) |
| 33 | 0.0 | 0.0 | invariato (DB 0.0, COMMUNICATE 1.0) |
| **37** | 0.0 | **1.0** | ✅ recuperato |
| 39 | 0.0 | 0.0 | invariato (DB 0.0, COMMUNICATE 1.0) |
| 44 | 0.0 | 0.0 | invariato (DB 0.0, COMMUNICATE 1.0) |

**Solo 1 fallimento su 7 recuperato**, non i 6/7 stimati come "coperti" in `docs/s5-correzioni.md`.
Nessuna regressione sui tre canary — le regole nuove non hanno rotto ciò che già passava, buona
notizia ma minore di quella sperata.

Un segnale che vale la pena portarsi dietro prima di diagnosticare: su 18, 23, 33, 39, 44 il check
`COMMUNICATE` ora passa (prima falliva anche quello - es. il `$23.553` della famiglia 2), mentre
il check `DB` (le azioni giuste sul sistema) continua a fallire sugli stessi cinque. La correzione
lingua/formato sembra funzionare; il problema decisionale che porta alle azioni sbagliate no. Il
task 7 fa eccezione col pattern opposto (DB ok, COMMUNICATE no) — proprio il task su cui la
famiglia 1 (clausola 2, evidenza singola) era stata scritta.

**Non ancora diagnosticato**: perché il DB check fallisce ancora su 18, 23, 33, 39, 44 nonostante
le regole che avrebbero dovuto coprirli, e perché il task 7 fallisce ora sul comunicare invece che
sull'agire. Prossimo passo, rimandato a sessione successiva per la compattazione della
conversazione — vedi handoff in `C:\Users\andre\AppData\Local\Temp\`.

---

## 2026-09-01 (2) — il reward binario stava nascondendo il lavoro

Ripresa dopo la compattazione, per capire perche' su sette fallimenti se ne fosse recuperato uno
solo. La premessa era sbagliata: **le regole hanno morso quasi ovunque, e' il reward binario che
non lo mostra**. Riletti i `results.json` a livello di `action_checks` invece che di reward:

| Task | round1 | round2 | Lettura |
|---|---|---|---|
| 44 | 0/3 upgrade (trasferiva tutto) | **3/3 corretti** | la clausola 4 ha morso, poi ha ecceduto: ha anche cancellato `S61CZX`, che il ground truth vieta esplicitamente (`nl_assertion`: "Agent does not cancel reservation S61CZX as the user is healthy"). **Correzione a caldo del passo 1**: il cliente *aveva* confermato (turno 29), quindi non e' una conferma mancata — l'errore e' a monte, vedi sotto |
| 39 | 0/3 cancellazioni | **2/3** | manca `MSJ4OA`. Al turno 28 l'agente **cita la nostra riga riparata**: "un chemin bloque par la politique ne constitue pas un motif de transfert" — la regola e' letta e applicata alla lettera |
| 23 | 4/4 scritture sbagliate (trasferiva) | cancella e **trova la strada alternativa** | fallisce su un dettaglio che nessuna famiglia copriva: una prenotazione per 3 passeggeri invece di tre separate (un certificato per passeggero) |
| 18 | **DB 1.0** | **DB 0.0** | **regressione causata da noi**: `credit_card_2929732` su tutte e cinque le prenotazioni, mentre il ground truth ne vuole tre diverse. La clausola 3 dice "usa solo un metodo che il cliente ha nominato", il cliente ne ha nominato uno, l'agente l'ha applicato a tutto |
| 33 | scritture 0.50 | scritture **0.00** | voli ora corretti, gift card sbagliata (`_1646646` invece di `_6941833`). Ed era classificato famiglia 4 ("non correggibile"): **e' famiglia 5**, la mappa famiglia-task era sbagliata |
| 7 | DB 1.0 / COMM 0.0 | identico | la clausola 2 non ha morso per niente |

Piu' un effetto collaterale non previsto: nel task 39 il cliente infila francesismi e l'agente
**passa interamente al francese**. La nostra regola "reply in the language the customer is writing
in" ha tolto l'italiano e introdotto il mirroring del francese; li' e' passata liscia solo perche'
il task 39 non ha `communicate_info`.

Bilancio onesto: tre vittorie comportamentali reali (23, 39, 44), due regressioni causate da noi
(18 e 33), una sovra-esecuzione causata da noi (44), un no-op (7). Il reward comprime tutto in
"1 su 7".

### La ricerca: cosa dice il processo corretto

- **Error analysis, non eval-driven development** ([Husain & Shankar](https://hamel.dev/blog/posts/evals-faq/)):
  open coding -> axial coding -> tassonomia -> saturazione, guardando **il primo** fallimento in
  ogni traccia perche' quelli a valle sono conseguenze. Consigliano ~100 tracce per ciclo. Noi ne
  abbiamo dieci, con n=1: la tassonomia e' metodologicamente giusta, il campione e' troppo sottile
  per reggerci sopra sei regole.
- **Il reward binario va affiancato, non sostituito** ([Langfuse](https://langfuse.com/resources/engineering/ai-agent-evaluation),
  [prefactor](https://prefactor.tech/learn/agent-benchmarks)): prima il successo end-to-end per
  capire *quali* flussi falliscono, poi le metriche per-step. Eravamo fermi al primo stadio pur
  avendo gia' i dati del secondo dentro ogni `results.json`.
- **n=1 non distingue il miglioramento dal rumore.** E' il motivo per cui tau2-bench nasce con
  `pass^k`. Gia' dichiarato nella spec S5, ora e' il vincolo principale.
- **Aggiungere istruzioni e' un intervento a rischio, non neutro** ([prompt bloat](https://www.mindstudio.ai/blog/prompt-bloat-vs-skill-systems-ai-agents),
  [instruction position](https://tianpan.co/blog/2026/04/14/the-instruction-position-problem)): le
  istruzioni competono per attenzione e il fallimento tipico non e' il rifiuto del conflitto ma lo
  **scarto silenzioso** di una delle due. E' il meccanismo di 18 e 44. Sul fronte opposto,
  [IRMA (EMNLP 2025)](https://arxiv.org/abs/2508.20931) ottiene su tau-bench i guadagni
  riformulando l'input turno per turno con le regole pertinenti, non ingrossando il system prompt.

### Passo 0 — cambiare il metro prima dell'agente

Nuovo `scripts/action_metrics.py`: metriche per-azione calcolate dai `results.json` locali, a costo
zero e senza consumare quota, retroattive su tutti i run gia' fatti.

- `action_score` — frazione delle azioni attese eseguite. Generosa, include le letture: il task 9
  passa con `action_score` 0.00 perche' la sua unica azione attesa e' una lettura che l'agente ha
  saltato. Serve come indicatore grossolano, non come verdetto.
- `write_action_score` — la stessa cosa sulle sole azioni che modificano il database. E' quella che
  conta: il DB check dipende solo da queste. E' la metrica che rende visibile "due cancellazioni su
  tre" contro "nessuna".
- `unexpected_writes` — scritture su prenotazioni che il ground truth non modifica **mai**:
  sovra-esecuzione vera.
- `wrong_argument_writes` — scritture sulla prenotazione giusta con un argomento sbagliato.

Le ultime due erano una sola all'inizio, e le ho separate perche' confondevano due casi opposti: il
task 18 sbaglia il metodo di pagamento su prenotazioni corrette (difetto di precisione), il task 44
cancella una prenotazione che nessuno gli ha chiesto di toccare (difetto di eccesso). Si correggono
in modo opposto. Nella prima versione il conteggio degli `unexpected` dava 0 anche per il 44,
perche' confrontavo con **tutte** le azioni attese e `S61CZX` compare tra quelle di lettura.
Corretto confrontando solo con le scritture attese: che il ground truth legga una prenotazione non
autorizza a modificarla.

Nessun criterio di matching inventato: si riusa `Action.compare_with_tool_call()`, lo stesso metodo
di `ActionEvaluator`, e la classificazione read/write viene da `get_tool_types()` sul toolkit del
dominio invece che da una lista scritta a mano.

Quadro completo sui dieci task del dataset (`write` = `write_action_score`, `unex` =
`unexpected_writes`, `wrarg` = `wrong_argument_writes`):

| Task | reward r1 -> r2 | write r1 -> r2 | unex r2 | wrarg r2 |
|---|---|---|---|---|
| 0, 41, 42 (canary) | 1.0 -> 1.0 | invariati | 0 | 0 |
| 7 | 0.0 -> 0.0 | 1.00 -> 1.00 | 0 | 0 |
| 18 | 0.0 -> 0.0 | **1.00 -> 0.40** | 0 | **3** |
| 23 | 0.0 -> 0.0 | 0.00 -> **0.25** | 0 | 1 |
| 33 | 0.0 -> 0.0 | **0.50 -> 0.00** | 0 | 2 |
| 37 | 0.0 -> **1.0** | 0.00 -> **1.00** | 0 | 0 |
| 39 | 0.0 -> 0.0 | 0.00 -> **0.67** | 0 | 0 |
| 44 | 0.0 -> 0.0 | 0.00 -> **1.00** | **1** | 0 |

Le stesse tre metriche sono ora pubblicate come score su Langfuse da
`scripts/run_s5_round2_experiment.py` accanto a `reward` e `db_check`, quindi ogni run futuro le
avra' senza lavoro in piu'. Verificate a costo zero contro tre simulazioni reali gia' salvate,
prima di committare. Nello stesso passaggio `TASK_IDS_FILTER` e' tornato a `None`: era rimasto
valorizzato con i quattro task del rilancio mirato di ieri, e un run lanciato per distrazione ne
avrebbe rifatti solo quattro su dieci.

Da qui parte il passo 1: correggere per sottrazione — restringere le clausole 3 e 4 e ancorare la
regola sulla lingua — prima di aggiungere qualunque clausola nuova.

### Passo 1 — correggere per sottrazione, e un ground truth incoerente

Due modifiche a `custom_agent.py` (patch rigenerata), entrambe su regole che **avevamo introdotto
noi** e che stavano causando i fallimenti:

- **Clausola 3 riscritta.** Trattava il metodo di pagamento come un fatto globale della
  conversazione; e' un fatto per prenotazione. Nel task 18 il cliente dice "rimetti sul metodo
  originale di ciascuna prenotazione", la vecchia formulazione non aveva un ramo per la delega,
  quindi l'agente ha chiesto lo stesso e poi ha applicato l'unica carta nominata a tutte e cinque.
  Nel round1, **senza** questa regola, le azzeccava tutte. Ora ha tre rami espliciti: metodo
  nominato per quella prenotazione, metodo originale letto dal `payment_history`, oppure chiedi.
- **Clausola 4 nuova.** Nel task 44 l'agente ha dichiarato `S61CZX` "eligible for cancellation"
  perche' conteneva un volo di 5,5 ore — il criterio del **cliente**, non le condizioni della
  **policy**, che quella prenotazione non soddisfa. Non e' una regola inventata su un caso solo:
  `policy.md:149` lo prescrive gia' ("the agent must make sure the rules apply before calling the
  API!"), l'agente non lo stava onorando, e la clausola aggiunge il **quando**. La vecchia
  clausola 4 diventa la 5.

E una correzione a quanto avevo scritto poche ore fa: nel task 44 **il cliente aveva confermato**
(turno 29). Non era una conferma mancata, l'errore era a monte. Riga del diario gia' corretta.

**Task 39 dichiarato non correggibile, con la prova.** `MSJ4OA` (task 39, ground truth: cancellare)
e `S61CZX` (task 44, ground truth: non cancellare) sono indistinguibili su ogni condizione della
policy: entrambe economy, entrambe con assicurazione, entrambe prenotate da piu' di 24 ore, nessun
volo annullato dalla compagnia, nessun motivo sanitario. Il task 39 contraddice anche se stesso: la
sua `description` dice di cancellare solo cio' che e' idoneo al rimborso, e la policy concede
l'assicurazione solo per motivi sanitari o meteo (`policy.md:101`), che li' non ricorrono.

Le due letture si escludono. Scelta la lettura fedele alla policy: salva il task 44 (oggi a
`write_action_score` 1.00 con una sola scrittura di troppo, quindi recuperabile per intero) e perde
`MSJ4OA`, che pero' fallisce gia' oggi. Non si perde niente che si abbia. `MSJ4OA` va nella
categoria "non correggibile — solo monitoraggio", accanto alla famiglia 4.

Vale la pena dirlo per quello che e': un ground truth incoerente fra due task dello stesso
benchmark, sulla stessa clausola di policy, trovato **solo** perche' avevamo smesso di guardare il
punteggio binario e stavamo guardando le azioni. E' un risultato dell'osservabilita'.

Task 23 e 7 restano senza diagnosi nuova, per decisione: prima si verifica se queste due modifiche
mordono.

### Passo 1, seconda revisione — diagnosi di 23 e 7, e una regola tolta

Diagnosticati anche gli ultimi due task. Il risultato ha cambiato la clausola scritta poche ore
prima e ne ha fatta togliere un'altra.

**Il task 23 ha la stessa radice del 44.** Al turno 16 l'agente propone di pagare una prenotazione
sola con **tre certificati**; `policy.md:78` ne ammette uno. L'API accetta lo stesso, perche'
`policy.md:113` dice esplicitamente che non controlla. E il danno e' a catena: lo scenario prevede
che sia il **cliente** a proporre le tre prenotazioni separate, ma solo *"if the agent tells you
that due to policy only one certificate can be used"*. L'agente non l'ha mai detto, l'idea non e'
mai arrivata. Quindi non era un problema di "una prenotazione per passeggero" come avevo ipotizzato:
e' una scrittura vietata dalla policy che nessun tool ferma, esattamente come nel 44.

**Il task 7 non e' correggibile, e la clausola sulle parole di scopo va tolta.** Altra correzione a
quello che avevo scritto stamattina: quella clausola **ha morso**, alla lettera. Al turno 32
l'agente dichiara entrambe le letture, $708 e $2.076. Solo che il valore atteso e' 1628, cioe'
`402 + 306 + 296 + 624`: include due prenotazioni **cancellate durante la telefonata stessa**, e
valorizza `XEHM4B` al prezzo di prima dell'upgrade invece che a quello appena addebitato. Il
baseline rispondeva $708, come noi. Nessuna regola difendibile ci arriva senza ricalcare il caso —
cioe' senza rifare l'overfitting gia' corretto una volta in S5. Il task 7 va in monitoraggio.

E quindi la regola si toglie: era l'unica di S5 scritta su una sola osservazione, ha fatto quello
per cui era nata, il task per cui era nata resta a zero per un motivo che nessuna regola copre, e
nel frattempo costa token e fa produrre risposte doppie in ogni caso ambiguo. La clausola 1
("servi tutte le richieste prima di chiudere") resta: e' quella che ha eliminato l'abbandono della
domanda, ed e' sostenuta da piu' di un'osservazione.

**Bilancio del passo 1 sul prompt**: una clausola riscritta (pagamenti, ora per prenotazione), una
generalizzata (verifica di policy prima di ogni scrittura, che copre 44 e 23), una rimossa (parole
di scopo), zero aggiunte. Da cinque clausole a quattro. Dopo aver documentato che sul task 18 una
regola in piu' aveva **tolto** all'agente un comportamento che gia' aveva, accorciare non e'
estetica.

### Cosa mi aspetto dal round3, e dove guarderei se non funziona

Recuperi plausibili: **18 e 33** (meccanismo identificato con precisione, e il round1 dimostra che
senza la nostra regola l'agente li faceva giusti — e' l'unico caso in cui abbiamo la prova che il
comportamento corretto e' alla portata del modello); **44** (mancava una sola scrittura di troppo,
tutto il resto era gia' corretto); **23** solo in parte, perche' richiede che l'agente dica il
limite *e* che il simulatore-utente produca l'idea delle tre prenotazioni *e* che l'agente le
esegua tutte e tre con lo split di pagamento giusto — tre passaggi in serie, ognuno dei quali puo'
saltare.

Fuori portata per costruzione: **7** e **39** (`MSJ4OA`), entrambi in monitoraggio.

Dubbi, in ordine di quanto mi preoccupano:

1. **La clausola 3 e' la piu' ambiziosa che abbiamo scritto.** Chiede una verifica di conformita'
   prima di ogni scrittura, su una policy lunga, a un modello piccolo. Puo' produrre l'errore
   opposto — rifiutare operazioni legittime — che e' esattamente come abbiamo perso `MSJ4OA`. I
   canary 0, 41 e 42 sono la spia: se uno regredisce, e' quasi certamente questa.
2. **Il ramo (b) della clausola 2 puo' scattare a sproposito**, leggendo "l'originale" quando il
   cliente ne voleva un altro.
3. **Le clausole 3 e 4 si incatenano** (la 3 scopre il blocco, la 4 dice cosa fare dopo). In teoria
   non confliggono; e' lo stesso ragionamento ottimista che nel round2 si e' rivelato sbagliato.
4. **n=1 resta il limite di fondo**: un delta di uno o due task non distingue il miglioramento dal
   rumore, in nessuna delle due direzioni.

Se il round3 non migliora, il primo posto dove guarderei **non** e' il testo delle regole: sono le
metriche per-azione, `write_action_score` e `unexpected_writes` prima del reward. La domanda e' se
la clausola 3 stia sparando e sbagliando bersaglio (allora si legge il turno in cui l'agente
dichiara l'idoneita' e si vede quale condizione ha valutato male) oppure se non stia sparando
affatto (allora il problema e' di posizione o di competizione nel prompt, non di formulazione — e
la mossa successiva e' spostarla, non riscriverla). Sono due diagnosi opposte e le metriche le
distinguono in un colpo d'occhio, che e' esattamente il motivo per cui il passo 0 e' venuto prima.

### Sonda sul task 44 — la clausola 3 spara, ma solo per meta'

Invece di lanciare subito i dieci task, una sonda sul solo task 44: costa una simulazione invece
di dieci e risponde alla domanda da cui dipende tutto il resto, cioe' se la clausola nuova spara.
Quattro tentativi, di cui due andati a vuoto per motivi che non riguardano l'agente.

| # | Esito | Costo |
|---|---|---|
| 1 | troncata dal **nostro** timeout a 300s: l'agente era ancora nelle letture | $0.044 |
| 2 | `infrastructure_error`, 0 messaggi — DNS caduto (`getaddrinfo failed`) | $0 |
| 3 | **completata** | $0.113 |
| 4 | `infrastructure_error` x2 — rate limit RPM (15/min) | $0 |

Il tentativo 1 ha insegnato una cosa che e' finita nel codice: **il timeout non va tarato sulla
durata osservata**. Il task 44 era durato 134s nel round2 e ne ha impiegati 321 quella sera — la
latenza dell'API varia di un fattore tre nella stessa giornata. Un run troncato costa comunque i
suoi token e non risponde a niente. Alzato a 900s con la motivazione nel commento.

I due `infrastructure_error` hanno confermato l'utilita' del passo 0 in modo inatteso: con il solo
reward avrei visto `0.0` in tutti e quattro i tentativi e avrei potuto scambiare un problema di
rete per una regressione dell'agente. Le metriche per-azione distinguono a colpo d'occhio un
troncamento (`act 0.47`, `write 0.00`, breakdown assente) da un fallimento vero da un
`infrastructure_error` (tutto a zero, 0 messaggi, 0 secondi).

**Il risultato della sonda 3**, contro il round2 sullo stesso task:

| | reward | DB | COMM | write | unex | wrarg |
|---|---|---|---|---|---|---|
| round2 | 0.00 | 0.00 | 1.00 | **1.00** | **1** | 0 |
| sonda 3 | 0.00 | 0.00 | 1.00 | 0.67 | **0** | **2** |

**Il passo (a) funziona, ed e' verificato sul testo.** Turno 34:

> "we cannot cancel reservation `S61CZX`. [...] Since `S61CZX` is an economy class booking made
> more than 24 hours ago, and your reason for cancellation (**flights longer than 4 hours** /
> change of plans) is not covered by travel insurance (which only covers health or weather
> reasons), this cancellation cannot be processed."

Ha riconosciuto le quattro ore come criterio del *cliente* e le ha tenute separate dalle condizioni
della *policy* — la clausola in azione, alla lettera. `unexpected_writes` da 1 a 0. E regge la
pressione: al turno 35 il cliente insiste, l'agente non cede. Soprattutto **non sovra-rifiuta**: i
tre upgrade li esegue comunque. Il rischio numero 1 che avevo dichiarato prima del run — "spara e
produce l'errore opposto" — su questo task non si e' materializzato.

**Ma i passi (b) e (c) no, ed erano scritti male.** Al turno 38 l'agente prova a pagare un upgrade
con `certificate_8045380`; `policy.md:131` per un cambio volo ammette solo "a single gift card or
credit card". Il ramo (b) diceva *"including how many payment methods of each type"* — parlava di
QUANTI, non di QUALI, e il divieto violato era di tipo: **la clausola letteralmente non copriva
quel controllo**. E' lo stesso frammento che l'audit anti-overfitting aveva segnalato come il piu'
orientato a un caso specifico; si e' rivelato anche troppo stretto. L'ha fermato il tool, non la
regola.

Il passo (c) diceva *"tell the customer before proposing anything"*, ma era una frase in coda a una
clausola lunga invece che un passo. L'agente ha fatto l'opposto: ha eseguito le tre scritture e ha
messo la spiegazione in una nota a fine messaggio, al turno 46. Avendo deciso da solo come allocare
un piano di pagamento che era in parte inammissibile, ha messo `H8Q05L` sulla gift card invece che
sulla Visa che il ground truth si aspetta — da cui `write_action_score` 0.67.

Quindi una catena sola con tre sintomi: **(b) troppo stretto -> non rileva l'inammissibilita' ->
(c) non scatta -> l'agente decide al posto del cliente -> `payment_id` sbagliato.**

**Correzione, per ristrutturazione e non per aggiunta**: (b) passa da "quanti" a "quali e quanti",
(c) diventa un passo invece di una frase in coda. Stessa lunghezza, nessuna idea nuova.

Va pero' dichiarato un limite metodologico, e va dichiarato nel report: la sonda 3 e il round2 **non
sono un confronto A/B pulito**. Nel round2 il cliente diceva "using my credit card
`credit_card_4196779`" — un metodo solo, nominato; nella sonda dice "use my gift card and both
travel certificates toward the total, and charge the remaining balance to my Visa" — un piano
aggregato sui tre. Il simulatore-utente ha detto un'altra cosa, quindi parte della differenza e'
varianza conversazionale, non effetto della regola.

### Nota metodologica da riportare nel report

Da qui in avanti stiamo iterando su un singolo task con **una sola esecuzione per iterazione**.
Questo non permette di distinguere un miglioramento reale dalla varianza, ed e' overfitting per
costruzione. Il presidio che abbiamo adottato e' sul **contenuto** delle regole, non sul metodo
statistico: ogni clausola deve stare in piedi leggendola senza sapere quale task l'ha generata, e
deve citare la policy del dominio invece dei dati del caso. La misura corretta sarebbe `pass^k` con
piu' esecuzioni per task; non e' stata fatta per il tetto di spesa e le quote gratuite. E' una
limitazione del progetto, non una scelta difendibile, e nel report va scritta cosi'.

Decisione di Andrea, esplicita: si tiene la correzione anche se dovesse passare per fortuna, perche'
e' difendibile in se', e si dichiara il limite invece di fingere un rigore che il budget non
consente.

### Sonda 5 — task 44 recuperato, reward 1.0

Prima sonda con la clausola 3 ristrutturata e il limitatore RPM attivo. Verificato contro il
`results.json` locale, non contro la UI:

| | reward | DB | COMM | write | unex | wrarg |
|---|---|---|---|---|---|---|
| round1 (pre-S5) | 0.00 | 0.00 | 1.00 | 0.00 | 0 | 0 |
| round2 | 0.00 | 0.00 | 1.00 | 1.00 | 1 | 0 |
| sonda 3 | 0.00 | 0.00 | 1.00 | 0.67 | 0 | 2 |
| **sonda 5** | **1.00** | **1.00** | **1.00** | **1.00** | **0** | **0** |

Tre upgrade corretti con il `payment_id` giusto, nessuna scrittura di troppo, `db_match` True.
Il task 44 passa da "trasferiva tutto" (round1) a completo.

**Cosa e' stato davvero messo alla prova, e cosa no.** Il passo (a) della clausola 3 e' stato
esercitato in modo severo: il cliente chiede di cancellare `S61CZX` **tre volte**, con pressione
crescente, e l'agente rifiuta tre volte elencando le quattro condizioni della policy e spiegando
che l'assicurazione copre solo motivi sanitari o meteo, non la durata dei voli. Alla fine il
simulatore chiude con `###OUT-OF-SCOPE###`. E' il comportamento che il ground truth chiede.

I passi (b) e (c) invece **non sono stati esercitati**: al turno 37 il cliente nomina direttamente
la carta ("charge the total additional cost of $1,387.00 to my credit card ending in
`credit_card_4196779`"), quindi il pagamento e' passato dal ramo (a) della clausola 2 e non c'e'
mai stato un piano di pagamento inammissibile da intercettare. La ristrutturazione di (b) e (c)
resta quindi **non verificata**: e' motivata dall'evidenza della sonda 3, ma nessun run l'ha
ancora messa alla prova.

Va detto per intero, perche' e' lo stesso limite di prima con il segno opposto: **sonda 3 e sonda 5
non sono un confronto A/B**. Nella 3 il cliente proponeva un piano aggregato con i certificati,
nella 5 nomina una carta sola. Parte della differenza fra 0.00 e 1.00 e' varianza del simulatore,
non effetto delle nostre modifiche. Quello che si puo' affermare con sicurezza e' solo che il
passo (a) regge sotto pressione ripetuta, perche' quello si legge nel testo.

**Il limitatore RPM non e' mai intervenuto** (zero attese nel log): l'API era abbastanza lenta da
sola, 48 messaggi in 128 secondi. Resta come assicurazione per i run in cui e' veloce, dove
avevamo misurato 45 chiamate al minuto contro un limite di 15.

### Round 3 — 7 task su 10, quattro recuperi su sette

Nove task eseguiti piu' il 44 riusato dalla sonda 5 (stessa versione dell'agente, campo
`reused_from` nell'output di quell'item). Verificato contro i `results.json` locali:

| Task | round1 | round2 | **round3** | note |
|---|---|---|---|---|
| 0 (canary) | 1.0 | 1.0 | **1.0** | nessuna regressione |
| 41 (canary) | 1.0 | 1.0 | **1.0** | nessuna regressione |
| 42 (canary) | 1.0 | 1.0 | **1.0** | nessuna regressione |
| 7 | 0.0 | 0.0 | 0.0 | monitoraggio, atteso |
| **18** | 0.0 | 0.0 | **1.0** | recuperato |
| 23 | 0.0 | 0.0 | 0.0 | ma vedi sotto: e' cambiata la famiglia |
| **33** | 0.0 | 0.0 | **1.0** | recuperato |
| 37 | 0.0 | 1.0 | **1.0** | tenuto |
| 39 | 0.0 | 0.0 | 0.0 | monitoraggio, atteso |
| **44** | 0.0 | 0.0 | **1.0** | recuperato (sonda 5) |

**4 dei 7 fallimenti originali recuperati**, canary intatti. E' esattamente il tetto realistico
dichiarato *prima* del run ("il massimo raggiungibile e' 4 su 7, con il 23 come quinto in caso
fortunato"): il 23 non e' arrivato, il 7 e il 39 sono rimasti dove li avevamo messi.

**Il task 23 e' il risultato piu' importante del round, e il reward lo nasconde di nuovo.** I
passi (b) e (c) della clausola 3 — quelli che la sonda 5 non aveva potuto mettere alla prova —
qui hanno sparato entrambi. Turno 22:

> "According to our policy, when changing flights, only a single payment method (gift card or
> credit card) can be used for the transaction, so we cannot combine certificates, gift cards,
> and your Mastercard."

E' il controllo di ammissibilita' degli argomenti fatto **prima** della chiamata, e comunicato al
cliente prima di proporre. Al turno 23 il simulatore reagisce esattamente come lo scenario del task
prevedeva:

> "I have a great idea: can we cancel the current reservation and book three separate reservations
> instead? [...] For Raj's reservation, we can use `certificate_9984806`."

Al turno 24 l'agente stende il piano corretto, con l'allocazione giusta dei tre certificati. Al
turno 25 il cliente dice "Yes, please proceed" **e chiude con `###STOP###` nello stesso messaggio**.
La conversazione finisce prima che l'agente possa eseguire.

Cioe': la catena che avevamo progettato ha funzionato in tutti i suoi passaggi, e il task fallisce
ora per la **famiglia 4** — "l'utente chiude la chiamata nello stesso turno in cui conferma" — che
avevamo dichiarato non correggibile in S4 leggendo `orchestrator.py:836-843`. Il task 23 e' passato
da un fallimento correggibile a uno non correggibile. Il reward resta 0.0 in entrambi i casi.

**Caveat sulle nostre stesse metriche**: il task 33 passa con `reward` 1.0 pur avendo
`write_action_score` 0.50 e tre scritture con argomenti fuori dal ground truth. Il DB finale
coincide comunque, quindi il `db_check` passa. Le metriche per-azione misurano l'aderenza alla
traiettoria attesa, non l'esito: una sequenza diversa che arriva allo stesso stato le fa scendere
senza che nulla sia sbagliato. Vanno lette insieme al reward, non al posto suo.

### Cura del dataset Langfuse

Il Run del round3 era nato con il nome sbagliato: una sostituzione di stringa nello script non
aveva fatto match e il Run aveva ereditato il nome della sonda 5. Un Run mal nominato rende
illeggibile il confronto nella pagina Experiments, che e' proprio il materiale che serve al report.
Risolto ripubblicando lo stesso identico contenuto con il nome giusto tramite `REUSE_EXISTING`,
che rilegge le simulazioni salvate invece di rigiocarle: punteggi identici, **zero chiamate LLM,
zero costo**. Resta da eliminare il duplicato mal nominato.

Struttura del dataset `airline-s4-round2` a fine giornata: un solo dataset, un Run per iterazione,
dieci item con scenario (`input`) e ground truth (`expected_output`), cinque score per item
(`reward`, `db_check`, `write_action_score`, `unexpected_writes`, `wrong_argument_writes`) e il
dialogo completo leggibile nella colonna Output senza saltare a Tracing. I Run del round2 non
hanno i tre score per-azione, nati con il passo 0: per quelli il confronto sta nelle tabelle qui
sopra, ricostruito dai file locali.

### Una colonna per leggere gli zeri: `failure_family`

Osservazione di Andrea, e ha ragione: il "monitoraggio" non riguarda i singoli task ma le
**famiglie** di cui fanno parte, e se un fallimento e' gia' diagnosticato e dichiarato fuori
portata, chi apre la pagina Experiments deve poterlo vedere senza rileggersi il diario. Un reward
0.0 mette nello stesso mucchio tre cose molto diverse:

1. l'agente ha sbagliato;
2. l'agente ha fatto la cosa giusta ma il ground truth ne voleva un'altra;
3. il simulatore-utente ha chiuso prima che l'agente potesse agire.

Aggiunto quindi uno **score categoriale** (`data_type="CATEGORICAL"`, il meccanismo standard di
Langfuse per le etichette non numeriche) chiamato `failure_family`, pubblicato accanto agli altri
cinque. Valori pochi e stabili di proposito, cosi' la colonna resta filtrabile nella UI:

| Valore | Significato | Task nel round3 |
|---|---|---|
| `famiglia N - <titolo>` | una delle famiglie della tassonomia S4 | 23 (famiglia 4) |
| `ground truth incoerente` | l'atteso contraddice la policy del dominio o non e' ricostruibile dalla conversazione | 7, 39 |
| `da diagnosticare` | fallimento non ancora classificato — **e' il default** | nessuno |
| `run non riuscito` | nessun risultato (quota, rete): non e' un fallimento dell'agente | nessuno |

Due scelte di progetto che vale la pena aver fatto apposta:

- **Nessuna etichetta sui task che passano.** La colonna serve a leggere gli zeri, non a decorare
  gli uni; lasciandola vuota sui successi, filtrare per "non vuoto" da' esattamente l'elenco dei
  fallimenti classificati.
- **`da diagnosticare` come default.** Un fallimento senza etichetta non deve poter passare per
  "gia' capito". Se domani un task nuovo fallisce, la colonna lo dice invece di tacere.

Il commento di ogni score porta la motivazione per esteso, con il rimando a
`docs/s5-correzioni.md`. E porta anche l'avvertenza che conta: **la classificazione e' la nostra
diagnosi a quella data, non un dato del benchmark, e va riverificata quando cambia l'agente.** Il
task 23 e' l'esempio vivo: fino al round2 era un fallimento correggibile, nel round3 e' diventato
famiglia 4.

### Pulizia del dataset

Cancellati cinque Run: le sonde 1, 2 e 4 (troncata dal timeout, DNS caduto, quota RPM — un item
ciascuna, **non vuote come avevo detto**: contenevano il record del fallimento, ma nessun dato
utile), il duplicato del round3 col nome della sonda, e la versione del round3 pubblicata prima di
`failure_family`, superata dalla ripubblicazione.

Restano sette Run: i quattro del round2 (compresi quelli parziali per quota, che fanno parte della
storia), le sonde 3 e 5 sul task 44 — le due con dati veri, che raccontano l'iterazione — e il
round3 completo. Ripubblicare il round3 con la colonna nuova e' costato **zero**: `REUSE_EXISTING`
rilegge le dieci simulazioni salvate invece di rigiocarle.

### Revisione del piano — 2026-09-01

`TASSONOMIA.md` (fuori dal repo) aggiornato con il via libera di Andrea, dopo aver scoperto che
quello che stavamo chiamando S5 non era l'S5 del piano. Backup del file precedente accanto
all'originale come `.bak-20260901`. Quattro modifiche:

**S5 riscritto in due parti.** S5a — correzioni all'agente e metriche per-azione — e' fatto, e non
era in quella forma nel piano: e' nato da S4, che chiedeva di verificare se le famiglie fossero
correggibili. Registrato che **le assertion deterministiche del piano sono state fatte sotto altro
nome**: `action_metrics.py` e' esattamente il "codice dove basta" che il piano considerava meta'
del valore, con la prova sperimentale che serviva (senza quelle metriche il round2 sembrava un
fallimento mentre le regole stavano gia' mordendo su tre task).

**S5b — il giudice — ridotto e ridefinito.** Le "2-3 famiglie piu' frequenti" del piano non sono
determinabili: con dieci task e un run per task non c'e' base per dire cosa sia frequente, e
sceglierle sarebbe stato inventare una statistica. Lo scopo nuovo e' piu' stretto e piu' utile: un
giudice che assegna la **famiglia di fallimento** leggendo la traccia, cioe' automatizza il lavoro
diagnostico fatto a mano. Le etichette di riferimento esistono gia' — la colonna `failure_family`
piu' le diagnosi di S4 — per **~16 fallimenti**, non i 30 del piano: il numero va dichiarato per
quello che e'.

**S7 ridimensionato da run da 50 task a paragrafo del report.** L'ablation e' gia' stata fatta
senza volerlo durante S5, con nesso causale documentato in tre casi: la lingua di
`POLICY_HIGHLIGHTS` (10 task su 20 contro 0 su 49 del baseline), l'"if and only if" perso nella
nostra sintesi, la clausola sui pagamenti che ha fatto passare il task 18 da `DB 1.0` a `DB 0.0`.
Quest'ultima ha la forma di un esperimento controllato vero, con il round1 come controllo. Rifarla
su 50 task costerebbe due giorni di quota per la stessa conclusione: la quota va al 50+50 di S6.

**Il decreto "non si ottimizza il prompt per alzare il pass rate" e' stato revocato**, su decisione
di Andrea. Nasceva da una preoccupazione giusta — tarare finche' il numero non e' bello — ma
proibiva la cosa sbagliata. Sostituito da un **obbligo**: ogni miglioramento di pass rate va
riportato insieme al metodo, cioe' quante iterazioni, quante esecuzioni per task, quali task erano
irrecuperabili e perche'. Il caso da dichiarare e' il nostro: 7/10 ottenuto con **n=1 per
iterazione**, che non distingue il miglioramento dalla varianza.

**S6 aggiornato**: sono **due** run da 50 (baseline `llm_agent` e `custom_agent`) e non uno, con la
nota su quota e pianificazione — circa 2.000 richieste contro un tetto di 500 al giorno.

---

## 2026-09-02 (notte) — S6: i 100 task, baseline contro il nostro agente

Cento simulazioni sui 50 task airline, due agenti, eseguite mentre Andrea dormiva. **Zero
fallimenti infrastrutturali**: dieci blocchi su dieci chiusi con `falliti 0`. La sera prima, sullo
stesso volume di lavoro, ne avevamo persi tre fra quota, DNS e timeout — la differenza sono il
limitatore RPM e la divisione per chiave.

### Il numero

| | baseline `llm_agent` | `custom_agent` |
|---|---|---|
| **reward** | **34/50 — 68%** | **39/50 — 78%** |
| `db_check` | 0.70 | **0.80** |
| `write_action_score` | 0.62 | **0.69** |
| `unexpected_writes` | 0.02 | **0.00** |
| `wrong_argument_writes` | **0.06** | 0.14 |

**+5 task netti, +10 punti percentuali.** Sei task recuperati (9, 12, 20, 21, 37, 44), **uno perso**
(11), 33 passati da entrambi, 10 falliti da entrambi.

Due colonne raccontano più del reward. `unexpected_writes` **a zero** contro 0.02 del baseline: la
clausola sulla verifica della policy prima di ogni scrittura fa il suo mestiere su scala, non solo
sul task 44 dove l'avevamo sondata. Ma `wrong_argument_writes` è **più che doppio** del baseline
(0.14 contro 0.06): la clausola sui pagamenti continua a produrre scritture sulla prenotazione
giusta con l'argomento sbagliato. È il difetto che avevamo identificato in S5 e corretto solo in
parte — su cinquanta task si vede che non è risolto.

### L'unica regressione, ed è la famiglia 4

Il **task 11** è l'unico caso in cui il baseline passa e noi no. Verificato sulla traccia:

- il **baseline** esegue `update_reservation_flights` e poi comunica l'esito → `reward` 1.0;
- il **nostro agente** descrive la modifica correttamente (`COMMUNICATE` 1.0), chiede la conferma
  esplicita, e al turno 19 il cliente risponde *"Yes, please just get this done quickly!"*
  **chiudendo con `###STOP###` nello stesso messaggio**. Zero scritture eseguite, `DB` 0.0.

È esattamente la famiglia 4, e stavolta con il controllo perfetto che al task 23 mancava: **la
nostra regola di conferma esplicita — decisione 1 di S3, presa leggendo la policy — ci costa un
task, perché il simulatore chiude la conversazione nell'atto stesso di confermare.** Il baseline
vince proprio per essere meno scrupoloso.

Vale la pena scriverlo nel report senza addolcirlo: una regola **corretta rispetto alla policy del
dominio** produce un punteggio peggiore su un benchmark il cui simulatore-utente non aspetta.
Non è un difetto del nostro agente, è il costo di aderire alla policy quando il grader misura solo
lo stato finale.

### Come è stato eseguito

Cinque chiavi API di cinque progetti Google diversi, venti task ciascuna (10 baseline + 10 custom),
cinque processi in parallelo. Tre cose hanno retto:

- **Le chiavi non passano mai dalla riga di comando**: il worker riceve il nome della variabile e
  legge il valore dal `.env`, quindi non finiscono nella lista dei processi né nei log.
- **`load_dotenv` con `override=False`** fa vincere la chiave passata nell'ambiente del processo,
  quindi lo smistamento non ha richiesto una riga di modifica al codice di terzi.
- **Il limitatore RPM è per-processo**, quindi ogni chiave si autolimita sui propri 13/minuto senza
  sapere delle altre — che è la cosa giusta, perché anche le quote sono per progetto.

Un `save_to` per singolo task invece che per blocco: un processo che muore perde un task e non
venti, e al riavvio il worker salta quelli già fatti. Non è servito, ma è il motivo per cui potevo
lasciarlo girare senza sorveglianza continua.

Esecuzione e pubblicazione separate: i worker hanno scritto solo su disco, e `s6_publish.py` ha
consolidato in **due Run da 50 item sullo stesso dataset** (`airline-50-baseline-vs-custom`).
Pubblicare dai worker avrebbe prodotto dieci frammenti da dieci item, e il confronto item-per-item
— il motivo per cui il dataset esiste — sarebbe stato illeggibile. Come effetto collaterale, la
ripubblicazione costa zero: si può aggiungere uno score o correggere un nome senza rigiocare nulla.

Su `failure_family` sono state applicate **solo le etichette intrinseche al task** (il ground truth
incoerente dei task 7 e 39). L'etichetta "famiglia 4" del task 23 era la diagnosi di una traccia
specifica del round3, non una proprietà del task: riusarla su cento esecuzioni mai lette avrebbe
significato etichettare fallimenti che nessuno ha guardato. Tutto il resto è `da diagnosticare`,
che è la verità — e sono **dieci task falliti da entrambi gli agenti**, il materiale naturale per
il giudice di S5b.

### Cosa resta aperto

- I dieci task falliti da entrambi non sono ancora diagnosticati: è il corpus su cui far girare il
  giudice, molto più ricco dei sedici fallimenti ripetuti dei round precedenti.
- `wrong_argument_writes` più che raddoppiato rispetto al baseline è un difetto **nostro**, noto e
  non risolto.
- Resta n=1 per task: cinque task di differenza su cinquanta non sono statisticamente separati
  dalla varianza, e va scritto nel report accanto al numero.

### Cosa fare adesso — analisi post-S6 e piano concordato

Andrea si aspettava di piu' dal 68% -> 78%, temendo che i cinque task di guadagno fossero solo
quelli corretti a mano. **Verificato: non e' cosi'.** Dei sei recuperi (9, 12, 20, 21, 37, 44)
**quattro sono su task mai guardati**; solo 37 e 44 erano nel set di sviluppo.

| | baseline | custom |
|---|---|---|
| i 10 task del set di sviluppo | 4/10 | 6/10 |
| i **40 task mai visti** | 30/40 | **33/40** |

**Le correzioni generalizzano**, ed e' questo il risultato del progetto, non la percentuale: regole
scritte leggendo sette fallimenti su dieci task migliorano il comportamento su quaranta task nuovi.
Con overfitting la riga dei "mai visti" sarebbe piatta.

**Ma il risultato non e' statisticamente stabilito.** Test esatto di McNemar (quello corretto per
esiti binari appaiati): 7 coppie discordanti, 6 a favore, **p = 0.125 a due code**, sopra la soglia
di 0.05. La letteratura sulla valutazione di agenti indica di leggere con cautela differenze sotto
gli 8-10 punti percentuali su un singolo benchmark; siamo a 10 esatti con n=1 per task. Da scrivere
nel report accanto al numero, non in nota.

**Il bersaglio residuo e' uno solo.** Dei 10 task falliti da entrambi gli agenti, **nove hanno la
stessa firma**: `DB` 0.0 con `COMMUNICATE` 1.0 - l'agente dice la cosa giusta e scrive la cosa
sbagliata (task 14, 23, 24, 25, 29, 32, 33, 35, 39). L'unica eccezione e' il 7, firma opposta e
gia' dichiarato non correggibile. Nove task su cinquanta valgono 18 punti potenziali: e' l'unica
leva rimasta grande abbastanza da giustificare una spesa, tutto il resto vale 2-4 punti, cioe'
rumore.

**Cosa dice la ricerca quando il prompt plafona**: la verifica e' l'intervento con piu' ritorno
(togliere la fase di verifica costa 7.1 punti contro i 3.5 della pianificazione, in uno studio su
planning verification-aware), le descrizioni dei tool sono una leva mai toccata, e su tau2-bench una
riscrittura di prompt ha portato un modello piccolo a +20%. **Ma il "verifier tax" e' documentato e
noi lo paghiamo gia'**: il task 11 e' la nostra regola di conferma esplicita che costa un task
perche' il simulatore chiude nell'atto di confermare. Aggiungere verifica puo' ripetere quel danno
su scala, con i turni contingentati a 30.

**Piano concordato**: (1) diagnosticare il grappolo dei nove a costo zero, chiedendosi se sia UN
meccanismo o nove cause diverse - in S5 la stessa domanda ebbe risposta "cinque cause diverse";
(2) se e' un meccanismo solo, una correzione mirata e il rilancio del solo custom sui 50 (~$1.8),
altrimenti **non si corregge** e diventa la tassonomia del report; (3) il giudice di S5b su questo
corpus, molto migliore dei sedici fallimenti ripetuti di prima; (4) il report, e stop.

Handover per la prossima sessione: `tassonomia-handoff-S6-dopo-i-100-task.md` nella cartella
temporanea dell'utente.

---

## 2026-09-02 (notte) — Diagnosi del grappolo, e la v2 dell'agente

### Un meccanismo o nove cause?

La domanda del piano ha risposta: **sette cause per nove task**. Ma due risultati valgono piu'
della tassonomia.

**I task 14 e 23 non sono errori dell'agente.** L'unico campo che diverge dal ground truth e'
l'*ordine* di due gift card dentro `payment_methods`: stesse quattro carte, stessi importi, stesso
totale, due gift card invertite. Il cliente non aveva chiesto nessun ordine, e infatti
`COMMUNICATE` vale 1.0. Verificato nel codice invece che dedotto: `evaluator_env.py:118` confronta
`get_db_hash()`, che in `toolkit.py:244` e' `get_dict_hash(self.db.model_dump())` - **un hash del
dizionario serializzato**. Le liste conservano l'ordine. Due prenotazioni finanziariamente
identiche prendono 1.0 e 0.0.

**Correzione a quanto scritto ieri sul task 11.** Avevo scritto che la nostra regola di conferma
esplicita ci costa un task. Misurato sui 100 run: delle **69 richieste di conferma**, solo **8**
sono seguite da `###STOP###`, cioe' il 12%. Il baseline ci finisce sopra 4 volte e perde tutte e
quattro (12, 20, 24, 25); noi 5 volte e ne salviamo 2. In quella famiglia **vinciamo 2-0**, non
perdiamo: due dei nostri sei recuperi (12 e 20) sono esattamente task in cui il baseline e' caduto
nella trappola e noi no. Il "5 su 5" che avevo riportato prima era vero ma selezionato - guardavo
solo i run *finiti* su una conferma, e un run fallito finisce li' per definizione.

**E quella famiglia non e' correggibile.** `policy.md:7`: *"you must list the action details and
obtain explicit user confirmation (yes) to proceed"*. Sui task 11 e 25 la conferma e' l'ultimo
turno prima dell'unica scrittura: per evitare la trappola l'agente dovrebbe agire senza attendere
il "si'", cioe' violare la regola aziendale che l'esercizio serve a implementare. Un punto
guadagnato disobbedendo al committente non e' un punto.

### Cosa abbiamo cambiato, e cosa no

Due modifiche, entrambe **sostituzioni**, nessuna aggiunta - la forma che in S5 e' stata l'unica a
funzionare.

**Clausola 2c, il metodo di pagamento predefinito.** Prima diceva: se il cliente non ha indicato
nulla, *elenca i metodi del profilo e chiedi*. Sul task 33 questo produce il danno: l'agente offre
`gift_card_1646646` o `gift_card_6941833`, il cliente ne sceglie una, e il ground truth voleva
l'altra - quella con cui la prenotazione era stata pagata. **Chiedere ha causato la risposta
sbagliata**, portando il cliente fuori dalla sua stessa istruzione (*"you are ok with paying using
the original form of payment"*). Ora la clausola propone il metodo con cui la prenotazione e' stata
pagata, nominandolo, e lascia sostituire.

Ancoraggio: `policy.md:152`, *"The refund will go to original payment methods"*. Non e' letta dal
task 33. Verifica sul db: `HXDUBJ` ha `payment_history` = `gift_card_6941833`, esattamente il
metodo atteso.

**Costo di regressione misurato prima di scrivere** (checklist §4.9): sulle 25 azioni attese dei 50
task che portano un `payment_id`, **19 usano il metodo originale e 6 no**. Le sei che divergono
stanno nei task 21, 32, 37, 44 - e in tutte il cliente **indica lui** il metodo ("la carta che
finisce per 7334", "la gift card col saldo piu' basso"), quindi le copre la clausola 2a, che viene
prima. Per proteggerle davvero 2a e' stata allargata da "named" a "named or otherwise identified":
se il modello leggesse "named" in senso stretto, una carta descritta a parole cadrebbe in 2c e la
nuova 2c e' assertiva dove la vecchia era innocua. Rischio residuo dichiarato: un task in cui il
cliente tace *e* il ground truth diverge dall'originale. Nei 50 non esiste.

**Clausola 4d, il trasferimento.** Sui task 24 e 32 l'agente trasferisce a un umano nello stesso
turno in cui scopre l'ostacolo. Sul 24 aveva appena scritto *"se avevi un'altra richiesta, fammi
sapere"*, e la seconda richiesta del cliente non viene mai servita; sul 32 il cliente era pronto a
pagare l'upgrade a economy - c'era scritto nelle sue istruzioni - ma non gliene e' stata data
l'occasione. La clausola era una *condizione* ("trasferisci solo se non resta nulla"); ora e' una
*sequenza*: dichiara l'ostacolo, aspetta la risposta, e solo dopo trasferisci.

Il mio istinto era "trasferisce troppo". **E' falso, e averlo verificato ha cambiato la regola**:
su 18 run in cui il nostro agente trasferisce, **16 passano**. Trasferire e' spesso la mossa giusta.
Una regola che lo scoraggia in generale avrebbe messo a rischio 16 task funzionanti - l'errore di
S5, ripetuto. Per questo la regola parla del *momento*, non della frequenza. Raggio d'azione
comunque largo: 18 run. E' la piu' rischiosa delle due.

Stessa occasione, **rimosso un duplicato**: la regola sul trasferimento era scritta sia in
`POLICY_HIGHLIGHTS` sia nella 4d. Il checklist §4.4 dice di fondere. In `POLICY_HIGHLIGHTS` resta
solo la distinzione di merito; la procedura la possiede la 4d.

### Cosa NON abbiamo cambiato, potendo

**L'ordine dei metodi di pagamento** (task 14 e 23) recupererebbe due task addebitando le gift card
dalla piu' capiente alla meno capiente. Scartata: le due prove vengono dallo **stesso profilo
cliente**, quindi e' un dato solo; nessuna riga di policy stabilisce un ordine; e la regola non
descriverebbe un comportamento corretto ma *l'ordine in cui il ground truth ha scritto una lista*.
Alla domanda "perche' la piu' capiente prima?" l'unica risposta onesta sarebbe "perche' cosi'
combaciava l'hash". Vale piu' raccontata che spesa.

**La selezione per rango** (task 35, "il secondo volo piu' economico"): sarebbe un passo di verifica
in piu' su ogni ricerca voli, con i turni contingentati a 30, per **un** task. Rimandata.

### Regola di decisione, scritta PRIMA di lanciare

Perche' scegliere fra v1 e v2 dopo aver visto i numeri sarebbe cherry-picking:

- **v2 diventa l'agente pubblicato se non regredisce** rispetto ai 39/50 della v1.
- **Se regredisce, resta pubblicata la v1** e la v2 va nel report come iterazione fallita, **con il
  suo numero**, non cancellata.
- In entrambi i casi il baseline resta quello di S6: task e baseline non cambiano, quindi il
  confronto 34/50 resta valido.

Il rischio e' reale e asimmetrico: la 2c e' stretta e ancorata, la 4d tocca 18 run.

---

## 2026-09-02 (notte) — Il verdetto sulla v2: regola pre-registrata applicata

**v2 = 38/50, v1 = 39/50.** La regola scritta prima di lanciare dice che la v2 resta pubblicata
solo se non regredisce. Non e' cosi', quindi **l'agente del repo torna a essere la v1** (patch
verificata byte-identica a quella pre-modifica), e la v2 resta qui documentata con il suo numero,
nel commit `fec7be5` e come terzo Run su Langfuse.

| | baseline | custom v1 | custom v2 |
|---|---|---|---|
| reward | 34/50 | **39/50** | 38/50 |
| `db_check` | 0.70 | 0.80 | 0.78 |
| `write_action_score` | 0.62 | 0.69 | 0.70 |
| `unexpected_writes` | 0.02 | 0.00 | 0.00 |
| `wrong_argument_writes` | 0.06 | 0.14 | **0.20** |

### Ma l'aggregato nasconde due storie opposte

Un task di differenza non dice niente (`p=1.0`). Quello che dice qualcosa e' l'attribuzione per
clausola, che il reward complessivo distrugge:

**Clausola 2 (trasferimento): ha funzionato. +1, nessuna perdita.**
- task 24: trasferiva a un umano, ora no -> **reward 0 -> 1.0**
- task 32: trasferiva, ora no. Comportamento corretto, task ancora fallito per altro
- nessuno dei task persi dalla v2 contiene un trasferimento: il raggio d'azione dichiarato (18 run)
  non ha prodotto danni

**Clausola 1 (pagamento): ha fatto danno. -2.**
- task 33, il suo bersaglio: la v1 usava `gift_card_1646646`, la v2 usa **`gift_card_6941833`**,
  cioe' esattamente il metodo atteso. **La clausola ha centrato il proprio obiettivo.** Il task
  resta 0.0 perche' l'agente si ferma dopo la prima azione e non esegue
  `update_reservation_baggages`: un difetto diverso, che era nascosto sotto quello del pagamento.
  Progresso a livello di azione, zero a livello di reward - il fenomeno per cui esiste
  `action_metrics.py`
- task 44: perso. Il cliente dice *"use my Visa credit card ending in 7238"*, e la v2 usa un misto
  che include `gift_card_5094406`, cioe' l'originale della prenotazione. **La clausola ha scavalcato
  un'istruzione esplicita del cliente**, che e' precisamente cio' che l'allargamento di 2a a "named
  or otherwise identified" doveva impedire. Non e' bastato
- task 21: perso. Il cliente chiede *"la gift card col saldo piu' basso"*; la v1 la trovava, la v2
  ne usa un'altra
- `wrong_argument_writes` sale da 0.14 a **0.20**: peggiora proprio la metrica che doveva sanare

**Il costo di regressione dichiarato si e' materializzato.** Nel diario, prima di lanciare, avevo
scritto che il rischio della clausola 1 erano i task 21, 32, 37, 44 - quelli in cui il ground truth
usa un metodo diverso dall'originale - e che 2a li avrebbe protetti. Due dei quattro si sono rotti
lo stesso. La previsione del *dove* era giusta, quella del *se* era sbagliata.

### Il resto e' rimescolamento, e va detto

Fra v1 e v2 ci sono **9 coppie discordanti** su 50 task, fra due versioni che differiscono per due
clausole, a `temperature: 0.0`. Tre dei quattro recuperi (11, 25, 29) e tre delle cinque perdite
(8, 20, 42) non c'entrano ne' col pagamento ne' col trasferimento: sono task che cambiano esito
perche' un prompt piu' lungo fa prendere al dialogo un percorso diverso dal primo messaggio, e a
cascata cambia **quali task finiscono nella trappola della conferma** - che ha un tasso di base del
12% sui turni di conferma.

Il task 20 e' l'esempio: la v2 lo perde perche' l'utente risponde *"Yes, I confirm and wish to
proceed. ###STOP###"*. Non e' una regressione delle clausole, e' la trappola che si e' spostata.

**Conseguenza per il report**: con n=1 per task, qualunque modifica al prompt ridistribuisce una
trappola stocastica su tutto il campione. Un delta di uno o due task fra due versioni dello stesso
agente non e' misurabile in questo modo. L'attribuzione per clausola, fatta sulle tracce, e' l'unico
strumento che ha separato il segnale dal rumore - e ha detto una cosa che il reward diceva al
contrario: **una delle due modifiche era buona.**

### Ipotesi non testata (costo ~$2)

Una v3 con la sola clausola del trasferimento, senza quella del pagamento: +1 dalla 2, +2 dai task
21 e 44 non piu' rotti. Stima 40-42/50. **Non lanciata**: Andrea aveva autorizzato un run solo, e
l'autorizzazione non si estende da sola. Decide lui da sveglio.

### Nota infrastrutturale: il retry era rotto da sempre

Durante il run e' caduta la connessione e sono morti cinque task, uno per blocco. Il ritentativo
automatico dopo 90s non ne ha salvato nessuno, e **non per la rete**: `run_domain`, trovando un
`results.json` gia' presente, chiede a schermo *"Do you want to resume the run? (y/n)"*, e in un
processo senza stdin quella domanda e' un `EOFError`. Il primo tentativo moriva per la rete
lasciando la cartella a meta', il secondo moriva per la domanda.

Era un difetto latente da S6, mai emerso perche' il retry non era mai servito davvero. Ora
`s6_worker.py` scarta da se' le simulazioni senza reward prima di ritentare, e i cinque task sono
rientrati al primo colpo. Costo dell'incidente: circa $0.05 e mezz'ora.

---

## 2026-09-02 (notte) — La v3 falsifica l'attribuzione, ed e' il risultato piu' importante

**v3 = 35/50.** Regola pre-registrata applicata di nuovo: regredisce, quindi **resta pubblicata la
v1** (patch di nuovo verificata byte-identica). Quattro Run sullo stesso dataset Langfuse.

| | baseline | **custom v1** | custom v2 | custom v3 |
|---|---|---|---|---|
| reward | 34/50 | **39/50** | 38/50 | 35/50 |
| `db_check` | 0.70 | 0.80 | 0.78 | 0.72 |
| `write_action_score` | 0.62 | 0.69 | 0.70 | 0.58 |
| `unexpected_writes` | 0.02 | 0.00 | 0.00 | 0.04 |

### Cosa doveva dimostrare la v3, e cosa ha dimostrato invece

L'ipotesi era precisa: l'attribuzione per clausola sulla v2 diceva che la clausola del
**trasferimento** valeva +1 senza perdite (recuperava il task 24) e quella del **pagamento** valeva
−2. La v3 teneva solo la prima. Previsione: 40-42 su 50.

Ha fatto 35, e il modo conta piu' del numero:

| task | v1 | v2 | v3 | trasferisce a un umano? |
|---|---|---|---|---|
| 24 | 0.0 | **1.0** | 0.0 | SI / **no** / SI |
| 32 | 0.0 | 0.0 | 0.0 | SI / **no** / SI |

**Nella v3 i task 24 e 32 tornano a trasferire, pur essendo la v3 la versione che contiene la
clausola sul trasferimento.** Nella v2 - stessa identica clausola, parola per parola - non
trasferivano. L'unica differenza fra le due versioni e' la clausola sui **pagamenti**, che col
trasferimento non c'entra niente.

Conclusione obbligata: **quel comportamento non era causato dalla clausola.** Era causato dalla
perturbazione del prompt nel suo insieme. L'attribuzione per clausola che avevo scritto poche ore
prima - con sicurezza, e con tanto di tabella - era **anch'essa un artefatto del rimescolamento**.

### Il risultato metodologico, che vale piu' di tutti e tre i numeri

Tre varianti di prompt sullo stesso agente, stesso motore, `temperature: 0.0`, stessi 50 task:
**39, 38, 35**. Tutti i confronti a coppie fra le tre sono statisticamente indistinguibili
(McNemar `p=1.0`), e le coppie discordanti sono 9, 10 e 5 - cioe' ogni modifica sposta l'esito di
5-10 task su 50 in entrambe le direzioni.

**Con un'esecuzione per task, una modifica al prompt non e' separabile dal rumore, e nemmeno
attribuibile a una clausola.** Non e' un limite del nostro metodo diagnostico: la diagnosi sulle
tracce era corretta ogni volta (il task 33 usa davvero la carta giusta con la clausola nuova; il
task 44 viene davvero scavalcato). Il problema e' che il *risultato* di una modifica si misura solo
su ripetizioni, e noi non ne abbiamo.

Retroattivamente questo mette una condizione anche sul risultato principale: **v1 contro baseline
resta il confronto meglio sostenuto** - delta piu' grande (+5), `p=0.125`, e soprattutto e' un
confronto fra "nessuna regola" e "tutte le regole", non fra due varianti vicine. Ma la stessa
cautela va scritta accanto anche a quello.

### Cosa cambia nel piano

**La leva del prompt e' chiusa.** Non per stanchezza: perche' abbiamo misurato che sotto i ~5 task
di differenza questo apparato non distingue nulla, e tre tentativi su tre lo confermano. Una v4
sarebbe una scommessa, non un esperimento.

Il budget residuo va dove ripara la causa: **ripetizioni**. Con `n=2` o `n=3` per task si passa da
"39 contro 34" a "39 contro 34, e il divario ha tenuto su esecuzioni indipendenti", e diventa
possibile misurare la varianza invece di subirla.

Speso finora **$9.68 su €20**.

---

## 2026-09-04 — La ripetizione ribalta il risultato

Seconda esecuzione indipendente di baseline e custom v1 sugli stessi task. Si e' fermata a **73
simulazioni su 100** perche' le quattro chiavi API nuove sono morte insieme a meta' lavoro (vedi
sotto). Restano pero' **36 task presenti in tutte e quattro le esecuzioni**, ed e' un confronto
appaiato valido.

| | baseline | custom v1 | divario |
|---|---|---|---|
| 1a esecuzione | 25/36 | 27/36 | **+2** |
| 2a esecuzione | 28/36 | 27/36 | **-1** |

**Il divario cambia segno.** Combinando le due esecuzioni il pass rate medio e' **0.736 contro
0.750**, cioe' **+1.4 punti percentuali**, non +10.

### Il dato che spiega tutto: il benchmark non e' deterministico

Fra due esecuzioni identiche, **a `temperature: 0.0`**, cambiano esito:

- **5 task su 36** per il baseline
- **8 task su 36** per il nostro agente

Non e' il nostro agente a essere instabile: lo e' l'apparato. Temperatura zero non significa
determinismo — restano la non-determinatezza dell'API e il simulatore-utente, che a ogni giro puo'
prendere una strada diversa e, soprattutto, decidere in un momento diverso di chiudere la
conversazione.

**Conseguenza, e vale piu' di qualunque numero di questo progetto: una differenza di 2-5 task su 50
non e' distinguibile dalla varianza fra esecuzioni.** E' la stessa conclusione a cui erano arrivate
le varianti v2 e v3 per un'altra strada - tre prompt che davano 39, 38, 35 spostando 5-10 task per
volta - e ora ha una **seconda prova indipendente**, ottenuta senza toccare il prompt.

### Cautela sul campione, dichiarata

I 14 task mancanti (18-24 e 43-49) sono proprio quelli su cui il divario della prima esecuzione era
concentrato: su questi 36 la prima esecuzione dava +2, non +5. Il sottoinsieme **non e'
rappresentativo**, quindi il numero definitivo non e' stabilito in nessuna delle due direzioni.
Quello che e' stabilito - e non dipende dai 14 mancanti - e' l'instabilita' per task.

### Perche' e' stata la spesa migliore del progetto

$2.52 hanno impedito di pubblicare un **+10 punti che non regge**. Senza ripetizione il report
avrebbe dichiarato "da 68% a 78%, stesso modello" con accanto un `p=0.125` che sembrava solo
prudenza formale. Era invece il segnale corretto, e l'abbiamo verificato invece di sperare.

### Le chiavi: 401, non quota

Le quattro chiavi nuove hanno smesso di funzionare tutte insieme con
`401 ACCOUNT_STATE_INVALID: "The bound service account is deleted or disabled"`. Non e' esaurimento
quota - e' la disattivazione degli account Google dietro le chiavi. Verificato: morte anche a
posteriori, mentre la chiave originale funziona.

Da ricordare per chiunque replichi: **la firma "tutti i blocchi falliscono in coda alla propria
lista" somiglia moltissimo all'esaurimento quota, e non lo era.** Solo leggere il testo
dell'eccezione lo ha chiarito. Costo dell'ipotesi sbagliata, se non l'avessimo letta: aspettare un
giorno per un reset che non sarebbe mai arrivato.

---

## 2026-09-04 (2) — Dal reward binario alle metriche per-azione, e la domanda "vale la pena rifare tutto?"

### La rianalisi per-azione: stessa direzione, ancora dentro il rumore

Messe insieme le due esecuzioni indipendenti, `write_action_score` (frazione delle scritture
attese eseguite correttamente) dà +0.071 e +0.056 nelle due esecuzioni — **stessa direzione in
entrambe**, con due metodi di conteggio diversi (media per-task e tasso micro pesato per azione).
Bootstrap a blocchi (10.000 ricampionamenti, blocco = task, per rispettare la clusterizzazione
delle azioni dentro lo stesso task): divario +9.0 punti, IC 95% **[-5.6, +23.5]** — attraversa lo
zero. Anche alzando la risoluzione di un ordine di grandezza (da 50 bit a 78 azioni scritte
osservate) il segnale resta compatibile col rumore, ma consistentemente dalla stessa parte.

**pass^2** (la metrica ufficiale del benchmark: successo in *entrambe* le esecuzioni, non almeno
una) dà un risultato scomodo: baseline 0.667, custom v1 0.639 — **il baseline è leggermente più
affidabile**, non il nostro agente. Riportato perché e' quello che dicono i dati, non perché
conferma la tesi.

### Il paper del benchmark giustifica quello che avevamo osservato

Il paper originale di τ-bench (Sierra, arXiv:2406.12045) motiva esplicitamente la metrica pass^k
con la stessa osservazione fatta empiricamente da noi: un agente cliente-facing deve essere
affidabile su ripetizioni, non solo capace di risolvere una volta. Numero citato dal paper: GPT-4o
passa da pass^1=61.2% a pass^8<25% sul dominio retail. Non e' un'analogia, e' la prova dagli
autori del benchmark che una singola esecuzione a 50 task non misura la capacita' reale.

Trovato nello stesso passaggio (nel codice del repo, non in letteratura terza): un secondo script
di Sierra, `auto_error_identification.py`, classifica i fallimenti con un giudice LLM in una
tassonomia a due livelli (chi ha causato l'errore, che tipo) — strutturalmente la stessa cosa
fatta a mano in S4. E una issue reale (#12) sul reward per-substring del benchmark, un precedente
diretto per la fragilita' dello scoring binario che il nostro giudice cerca di risolvere.

### La domanda vera: rifare tutto da zero, o continuare?

Con tutto quanto sopra ancora dentro il rumore, la domanda successiva e' stata se ripartire da un
altro progetto per riuscire a dimostrare un miglioramento reale. Risposta, con i numeri:

- **Sierra stessa pubblica lo standard**: `docs/leaderboard-submission.md`, nel repo clonato,
  richiede **4+ trial per dominio** e copertura completa del task set per una submission
  affidabile statisticamente. Il dominio airline ha **esattamente 50 task** — li abbiamo gia'
  tutti. Il gap rispetto allo standard del settore non e' concettuale, e' aritmetico: 2 trial
  fatti, 4 richiesti.
- **Ma il rapporto vittorie:sconfitte si restringe aggiungendo dati**, non si allarga: 6:1 (86%)
  sulla sola prima esecuzione, **9:5 (64%)** mettendo insieme le due. E' il segno classico di una
  stima iniziale gonfiata che torna verso il rumore. Proiettando lo stesso 64% su un volume pari a
  4 trial, `p` scenderebbe a 0.044 — sopra la soglia per un soffio, *se* il rapporto vero regge e
  non continua a scendere.
- Deciso: **non fare altri 2×100 su v1** solo per inseguire un p-value che probabilmente non
  arriva. Investire lo stesso budget in una **v4** progettata meglio, non in piu' ripetizioni
  della stessa v1.

### Il bug del task 14/23: passato al vaglio di un avvocato del diavolo prima di pubblicarlo

Prima di aprire una issue pubblica su un repository di terzi a nome di Andrea, un secondo agente
(Opus, istruito esplicitamente a *falsificare* la diagnosi, non confermarla) ha provato a
smontarla su cinque fronti — incluso l'argomento piu' forte possibile: il campo si chiama
`payment_history`, non `payment_methods`, ed e' concettualmente un libro mastro dove l'ordine
avrebbe senso. Non ce l'ha fatta: le voci sono scritte in un'unica transazione atomica, senza
timestamp ne' numero di sequenza, quindi non c'e' cronologia da preservare. Ha trovato inoltre
un precedente diretto: issue **#325**, aperta e senza risposta, stesso sintomo su un altro
dominio (retail) senza causa radice individuata — il nostro contributo la completa, non la
duplica. Correzioni fatte alla bozza prima dell'invio: un path sbagliato, un'affermazione
("COMMUNICATE conferma la prenotazione corretta") sostituita con una prova piu' solida
(`DeepDiff(ignore_order=True) == {}`), e il fix proposto ristretto per non rompere il dominio
retail (dove `payment_history[0]` e' indicizzato posizionalmente per il rimborso).

### Il leaderboard pubblico di Sierra: dove si vede chi altro l'ha fatto

`taubench.com` esiste, e' vivo, e le submission reali di oltre 60 organizzazioni (Anthropic,
Google, NVIDIA, e altre) sono **gia' clonate in locale** in
`tau2-bench/web/leaderboard/public/submissions/` — non serve andare sul sito. Ogni submission ha
un campo `methodology.notes` con cosa hanno fatto, e spesso link a paper/repo. Trovato un
esempio diretto della categoria "custom submission" (= modifica al prompt/scaffold, la nostra
stessa categoria): NVIDIA, `toolorchestra_nvidia_2025-12-02`, paper pubblico (arXiv:2511.21689) +
repo GitHub. Trovato anche il dato piu' utile per il report: GPT-5 valutato da Sierra stessa su
airline con 4 trial, pass^1=62.5 -> pass^4=48 — lo stesso degrado misurato da noi, confermato dai
creatori del benchmark su un modello molto piu' capace del nostro.

Ricerca sulle tecniche di prompting applicabili (non infrastruttura, non training): nessuna
submission "custom" del leaderboard e' un caso pulito di solo-prompt su airline/retail (per lo
piu' voce o richiedono training). Le tecniche piu' utili sono arrivate dalle note delle
submission **ufficiali** di Anthropic (non marcate "custom" ma testualmente esplicite su cosa
hanno cambiato nel prompt): scrivere un ragionamento esplicito prima di ogni azione che modifica
stato, e alzare il tetto di step del harness in parallelo (30->100) per non confondere "ragiona
meglio" con "va in timeout".

Documenti prodotti: `docs/ricerca-valutazione-agenti.md`, `docs/premortem-bug-hash-ordine.md`,
`docs/tecniche-da-submission-esterne.md`.

---

## 2026-09-04 (3) — La bozza v4, il modello più capace scartato (per ora), e i prezzi veri

### La bozza v4, scritta da un secondo agente con ricerca supplementare

Le due guide di Anthropic sull'architettura degli agenti (Building Effective Agents, Writing
effective tools) **trasferiscono poco**: quasi tutto riguarda architetture multi-chiamata fuori
scope, e il consiglio più forte di entrambe - ottimizzare le descrizioni dei tool - e' proprio
quello che non possiamo applicare, perche' i tool sono parte del benchmark. La scoperta utile e'
venuta da altrove: un paper (arXiv:2608.02639, Instruction Stacking Collapse) misura su Gemini 2.5
Flash - il parente pubblicato piu' vicino al nostro modello - che l'aderenza alle istruzioni
crolla dal 96% con una istruzione al 43% con venti, con fallimenti **silenziosi**. v1 impila ~21
vincoli nostri sopra i ~40 di `policy.md`: molto oltre quella soglia. E' una spiegazione piu'
verificabile di quella che avevamo per v2/v3 - non un'attribuzione sbagliata da parte nostra, ma
un regime in cui sostituire una clausola non sposta il comportamento in modo prevedibile.

La v4 (bozza in `docs/v4-bozza-prompt.md`) fonde le regole invece di ripeterle, ordina i blocchi
per posizione (primacy/recency, "Lost in the middle"), e sostituisce il "pensa prima di agire"
libero - che un altro paper (arXiv:2409.12183) dice aiutare poco fuori da matematica/logica - con
un modulo a 5 righe fisse dentro il messaggio di conferma gia' imposto dalla policy. Rischio piu'
alto dichiarato dall'agente stesso, senza che gli fosse chiesto: la checklist puo' diventare
**teatro** - il modello riempie sempre lo slot "Allowed because", e se se lo inventa produce
tracce piu' rigorose in apparenza con esiti uguali o peggiori.

### Un modello piu' capace? I prezzi veri correggono l'intuizione, in entrambe le direzioni

Cercati i prezzi reali (non stimati) di GPT-5.6 e GLM-5.3-Flash, le due alternative proposte.
Sorpresa: **non sono piu' costosi** del nostro Gemini 3.5 Flash Lite - GPT-5.6 Luna ($0.20/$1.20
per milione di token) e GLM-5.3 Flash ($0.075-0.15/$0.25-0.50) sono i livelli budget delle
rispettive famiglie, comparabili o piu' economici dei nostri $0.30/$2.50. Il budget non era
l'ostacolo che sembrava.

Ma la stessa ricerca che ha prodotto la v4 dice l'opposto di quello che l'intuizione suggeriva
sull'effetto: la tecnica centrale (prompt compilation) da' +11 punti su un modello debole
(GPT-5-mini), **+3.3 su un modello della nostra fascia**, ~0 su un modello forte (Sonnet).
L'effetto si restringe con la capacita' del modello, non si allarga. Un modello piu' recente e
probabilmente piu' capace di Gemini 3.5 Flash Lite renderebbe questa specifica tecnica **meno**
efficace secondo la fonte da cui e' presa, non piu'. Trovata pero' una versione piu' solida
dell'intuizione originale: un modello che soffre meno il collasso da densita' fallisce in modo
meno casuale, il che potrebbe rendere piu' pulita l'attribuzione causa-effetto (il problema che
ha affossato v2/v3) anche senza rendere piu' facile il miglioramento in se'. Deciso: non sostituire
il binario Gemini-vs-Gemini, che e' il cuore della tesi del progetto ("stesso modello, solo il
prompt"); un secondo esperimento su un modello diverso resta un'aggiunta possibile, non un
sostituto.

### Due checkpoint di rilettura, proposti da Andrea - con una correzione tecnica

Proposta: far "rileggere" all'agente le regole pertinenti in punti scelti del ragionamento,
prima e dopo, per aiutarlo a restare concentrato o ad accorgersi di un ragionamento approssimativo.
Verificato nel codice (`llm_agent.py:127`) che la policy intera viene gia' reinviata al modello a
ogni turno - non c'e' nulla da "rileggere" in senso letterale, e il costo aggiuntivo non e' in
lettura ma in output (le righe che il modello scrive in piu'). Il meccanismo per cui l'idea
dovrebbe comunque funzionare e' reale: costringere il modello a riattraversare la regola pertinente
nella generazione, subito prima di deciderla, sfrutta lo stesso effetto di posizione gia' citato
per il riordino dei blocchi. Aggiunti come due righe morbide dentro i passi 1 e 3 della procedura
esistente - non nuove regole numerate, per non peggiorare la densita' di istruzioni che la v4
cerca di ridurre. Dettagli e limiti dichiarati in `docs/v4-bozza-prompt.md`, sezione 6.

### Il criterio di costo, fissato prima di girare i 50 task

Aggiunta una misura che il progetto non aveva ancora: **costo per successo** (costo totale del
giro / task riusciti) e **costo incrementale per punto guadagnato**, sullo stesso principio
dell'ICER usato in economia sanitaria per giudicare un trattamento piu' efficace ma piu' caro.
Se v4 costa di piu' per simulazione - atteso, per via del modulo di conferma e dei checkpoint -
queste due misure dicono se il costo in piu' vale il risultato, invece di guardare il solo pass
rate. Fissato prima di vedere il numero, come per ogni criterio di decisione di questo progetto.

### Infrastruttura Langfuse pronta per il primo giro v4

Aggiunto `s10` a `scripts/s6_publish.py`: il primo giro di 50 task v4 (quando esistera') si
pubblica nello stesso dataset del baseline S6, pronto per il confronto affiancato sulla pagina
Experiments - la stessa infrastruttura gia' usata per v1/v2/v3, senza bisogno di altro codice.
Generalizzata anche l'etichetta di sprint nei metadata dei Run (prima un ternario `s6`/altro,
ora un dizionario per prefisso).

Deciso: **niente pilota di 5-10 task**. Si gira tutto il primo giro da 50 direttamente.

### v4 implementata, patch rigenerata

`custom_agent.py` sostituito con la v4 (inclusi i due checkpoint di rilettura), patch rigenerata
in `patches/tau2-custom-agent.patch`. Verificato che il modulo importa e il `system_prompt` si
formatta senza errori prima di committare - nessuna simulazione lanciata.

**`AGENT_TURN_LIMIT` alzato 30->50.** Verifica nel codice, non supposizione: il limite riguarda
solo `CustomAgent` (un contatore nostro, `S3, decisione 3`) - il baseline (`LLMAgent`) non ne ha
mai avuto uno, e' vincolato solo dal tetto di framework `DEFAULT_MAX_STEPS=200`. Alzarlo per v4
non introduce quindi nessuna asimmetria col Run baseline `s6` con cui si confronta: correzione a
quanto scritto in una bozza di handover di questa stessa sessione, che raccomandava di lasciarlo a
30 proprio per timore di un'asimmetria che una lettura del codice ha escluso.

**Conferma sul dettaglio in Langfuse**: la colonna Output del Dataset Run mostra gia' il dialogo
turno per turno (UTENTE/AGENTE/TOOL) dentro l'item stesso, senza dover aprire la Trace - fissato
il 2026-09-01 dopo la stessa osservazione di Andrea, riusato identico per v4 via `base.my_task`.

---

## 2026-09-04 (4) — La v4 gira, perde contro v1, e proprio per questo produce la diagnosi migliore

I 50 task della v4 sono girati in un colpo solo (nessun pilota, come deciso): 74%, contro il 68%
del baseline e il 78% di v1. Il criterio di costo pre-registrato si applica pulito e dà una
risposta netta — costo per successo peggiore del 31% rispetto a v1. Numeri nella voce 13.

Prima di lanciare avevo dichiarato due riserve sulla v4 e ho scelto di **non** correggerle, per
non annacquare la cosa che l'esperimento stava misurando. Una delle due (il modulo a 5 righe che
schiaccia le risposte al cliente) si è rivelata **sbagliata**: il punteggio di comunicazione è
1.0 su tutte e quattro le regressioni. Il fallimento era l'opposto di quello che temevo.

### Il metodo che ha funzionato: leggere le tracce prima di scrivere regole

La lezione di v2/v3 era che scrivere clausole partendo dalla teoria fa perdere giri. Questa volta
ogni modifica della v5 nasce da una traccia letta, e due sono nate da errori miei trovati leggendo:

- **Il task 33 non era irrecuperabile.** Era in lista fra i "mai risolti da nessuna versione"; è
  la stessa chiusura anticipata di 17 e 21. Gli irrecuperabili scendono a 6.
- **Il task 32 smontava una modifica che avevo appena scritto.** Il cliente chiede esplicitamente
  *«prima l'upgrade e conferma, poi separatamente cambia i voli, voglio vedere i due passi
  completati individualmente»*, e il ground truth vuole due chiamate distinte. La mia regola
  «una conferma sola, poi esegui tutto di fila» avrebbe reso il task **più** difficile. Corretta
  con un'eccezione esplicita: il sequenziamento è una richiesta su *come* lavorare, non un
  conflitto con la policy, e vince sul default.
- **I task 24 e 29 non erano mai stati diagnosticati.** Da lì è uscita la famiglia C (voce 14).

### Il canale nascosto che non esiste

Andrea ha chiesto di spostare il modulo di verifica «fuori dalla chat con l'utente», seguendo
Anthropic. Verificato nel codice: **non è possibile.** `orchestrator.py:722` solleva un errore se
un messaggio dell'agente contiene sia testo sia una chiamata a tool — ogni parola scritta va al
cliente, oppure è una tool call. Anthropic poteva farlo perché aveva il *thinking* nativo di
Claude, un canale vero; il nostro modello non ce l'ha. È la stessa asimmetria della voce 15.

La leva utile però c'era, due righe sopra: **le tool call consecutive non passano mai dall'utente**
(`orchestrator.py:538`). Un solo "sì" seguito da tutte le azioni di fila non lascia al cliente
nessuna occasione di riagganciare a metà — ed è esattamente ciò che fa il baseline sul task 17,
che infatti lo passa. La rigidità di una conferma per azione l'avevamo aggiunta noi: `policy.md:7`
non la impone.

### Una proposta rifiutata, e perché

Per ragioni di budget è stato proposto di rigirare solo i task falliti e sommarli ai successi già
ottenuti, chiamandolo "un round". Non si può, per due motivi indipendenti: (1) i successi restano
congelati e i fallimenti hanno una seconda estrazione, quindi il punteggio può solo salire — e il
bias non è nemmeno simmetrico, perché il baseline avrebbe avuto 16 ritiri contro i 13 della v5;
(2) i successi tenuti erano stati prodotti dal prompt v4 e dal simulatore non corretto, quindi il
"round v5" sarebbe stato 37 risultati v4 più 13 v5, un numero che non descrive nessuna delle due.

Distinzione che resta valida e che stiamo usando: **girare solo i falliti va bene per diagnosticare,
mai per calcolare un pass rate.** Il controllo `s11` è esattamente questo, ed è dichiarato tale.

### Il controllo s11, con le previsioni registrate prima

Nove task (esclusi i quattro rotti in partenza: 7, 39, 14, 23), previsioni scritte prima di
lanciare: 17/21/33 passano; 9 e 42 al ~55-60%; 29 e 32 al ~35-50%; 24 e 35 fuori. È un
esperimento con gruppo di controllo — se passassero anche 9 e 42 *senza* le altre, la diagnosi
della famiglia B sarebbe da rifare.

**Esito: 5 recuperi su 9** (9, 17, 21, 24, 33). L'ipotesi principale regge su tutti e tre i task
della famiglia A. Due previsioni sbagliate, una per direzione: il 24 passa contro una stima del
20%, il 42 fallisce contro una del 55%.

Due letture di traccia prima di dichiarare qualcosa, e danno esiti diversi:

- **Task 24 — meccanismo confermato, non fortuna.** La v4 faceva *una* ricerca e prenotava il primo
  candidato valido (EWR→LAX). La v5 ne fa **sedici** — 2 origini × 5 destinazioni West Coast per
  l'andata, più i ritorni — enumera i candidati con i totali e sceglie il minimo: $106 JFK→SEA
  (HAT069 + HAT276), esattamente il ground truth. EWR→LAX compare terzo a $163. Il blocco sulla
  ricerca fa precisamente ciò per cui è scritto, e si vede nella traccia.
- **Task 9 — esito giusto, catena causale non dimostrata.** Zero scritture, quindi corretto. Ma la
  motivazione scritta dall'agente poggia sulle condizioni di policy delle altre prenotazioni, e
  quella che dichiara idonea semplicemente non la cancella. **Il successo non è attribuibile
  all'esempio di rifiuto**: il comportamento è quello voluto, il meccanismo no.

Il 42, che era il gruppo di controllo, resta fallito come previsto.

### Le due correzioni, isolate — e il backport esce dal disegno

In `s11` erano attive due correzioni insieme (conferma unica + backport), quindi non si sapeva
quale salvasse 17, 21 e 33. Separarle è costato $0,13: `s12` gira la v5 sugli stessi tre task
**senza** backport. **Passano 21 e 33, non il 17** — che fallisce con la stessa firma di sempre,
domanda in sospeso e cliente che riaggancia. La conferma unica fa quindi da sola quasi tutto il
lavoro; il backport vale **+1 task**.

E a quel punto il conto si rovescia. Misurando la firma sui run già in archivio, i task che il
backport potrebbe recuperare sono 3 per la v4 (17, 21, 33) ma **2 per il baseline** (21, 24).
Attivarlo darebbe +1 a noi e ~+2 al baseline: **costerebbe $1,55 di baseline da rigirare per
ridurre il nostro stesso margine.** In più introduce un rischio identificato per nome — il task
43 è un task **riuscito** che finisce con una domanda in sospeso, quindi tenere il cliente in
linea gli dà altri turni per fare qualcosa di non richiesto — e obbligherebbe a dichiarare nel
report uno strumento di misura modificato.

**Decisione: backport fuori dal disegno sperimentale.** Il clone torna alle linee guida originali;
la patch resta versionata in `patches/tau2-user-simulator.patch` come contributo documentato, non
come componente del nostro numero. Il ritrovamento vale comunque: Sierra ha scritto quella riga
per il canale vocale e non per quello testuale, e ora sappiamo anche quanto pesa — +1 sulla v5,
~+2 sul baseline, 4 task su 50 di raggio d'azione.

Nota di metodo: è la seconda volta in questa sessione che una misura da pochi centesimi ribalta
una raccomandazione che avevo dato con sicurezza. La prima era il tetto dei turni.

### Regola di arresto per i 4 trial, registrata PRIMA di girare

Deciso di puntare ai **4 trial** dello standard Sierra (`docs/leaderboard-submission.md`, requisito
5) accettando lo sforamento del tetto di ~$2: con 1 trial il report finirebbe come tutti i round
precedenti — «dentro il rumore» — mentre 4 trial danno il pass^k, cioè la potenza statistica che
manca al progetto da tre sprint, **e** rendono la sottomissione conforme.

Proposta di Andrea, respinta con i dati: fermare il trial appena la v5 perde **un** task che il
baseline passa. Non regge per quattro motivi, tutti misurati sui nostri stessi run:

1. **Avrebbe ucciso la v1**, il miglior agente del progetto. La v1 vince 6 task che il baseline
   perde e ne perde **uno solo, il task 11**: la regola si sarebbe attivata lì, buttando via il 78%.
2. **Un singolo task che si ribalta è rumore, non segnale.** Girando *lo stesso* agente v1 due
   volte cambiano esito **8 task**; il baseline, girato due volte, ne cambia 5. La regola si
   attiverebbe quasi subito, e su rumore.
3. **Sarebbe sovradattamento sul set di valutazione**, e per una sottomissione pubblica
   comprometterebbe la credibilità che la PR dovrebbe comprare.
4. **Un trial interrotto non è utilizzabile**: non entra nel pass^k e non è sottomissibile. I token
   spesi fino all'interruzione sono persi davvero.

**Regola adottata, sull'aggregato invece che sul singolo task**: si completa il **trial 1 per
intero**. Se la v5 non raggiunge **37/50 (74%)** ci si ferma e si analizza, senza spendere i ~$6
dei trial 2-4. La soglia è il pass rate della v4: sotto quella, il segnale sarebbe più debole di
una versione già scartata, e non ha senso comprare precisione per misurare bene un miglioramento
che non c'è. Costa quanto lo scenario peggiore proposto da Andrea, ma lascia un trial completo e
utilizzabile in ogni caso, decide su 50 osservazioni invece che su una, ed è dichiarabile: un'
analisi intermedia con regola pre-registrata è prassi, non una toppa.

Nota infrastrutturale: il primo lancio è morto perché la chiave era stata cancellata, e il
processo killato ha continuato a scrivere sullo stesso log del rilancio a offset diverso — il
file risulta binario e contiene righe di due run diverse. **La fonte attendibile sono i
`results.json` su disco, non il log.**

## 2026-09-05 — Il trial 1 della v5, due difetti nostri, e la sottomissione a Sierra

**Trial 1 completo: v5 = 38/50 (76%).** Baseline 34/50 (68%), v1 39/50 (78%), v4 37/50 (74%).
Contro il baseline: 6 vinti, 2 persi, McNemar p=0,289. Contro v1: 3 vinti, 4 persi, p=1,000.
Costo per successo $0,0534 (v1 $0,0435, baseline $0,0449).

La regola di arresto (≥37/50) è rispettata. Ma il quadro onesto è un altro: **le differenze fra le
nostre versioni sono rumore** — 74%, 76%, 78% sono uno o due task, e lo stesso agente girato due
volte ne cambia otto. Il task 33 lo mostra da solo: passa in `s11`, passa in `s12`, fallisce qui.
**L'unica cosa solida è che tutte le versioni battono il baseline**, sempre nella stessa direzione,
mai una volta sotto: +10 (v1), +8 (v5), +6 (v4). Nessuna presa da sola è significativa; la
coerenza fra quattro esperimenti indipendenti dice più di ciascuno.

Correzione a una memoria imprecisa: al secondo giro la v1 fece **27/36 = 75%**, non 35/50, e sui
36 task comuni fece 27 entrambe le volte — fu **stabile**. A muoversi fu il baseline (26 → 29).

### Le due regressioni contro il baseline sono nostre, e il meccanismo è nel testo

**Task 2** (azioni attese: zero) — la v5 emette `send_certificate` per $100. È il buco previsto
**prima** del lancio della v4: la clausola v1 «non offrire compensazioni di tua iniziativa» fu
rimossa, e avevo scritto che lo slot «Allowed because» non la copre perché scatta solo sulle
chiamate a tool. Previsione registrata prima, confermata dopo.

**Task 8** — tutto corretto tranne `total_baggages`: atteso 0, inviato 2, con il cliente che dice
«You don't have any baggages». La giustificazione scritta dall'agente è:

> Allowed because: *regular members get 1 free checked bag per passenger in economy*

e l'esempio che avevo scritto io in `CONFIRMATION_FORMAT` dice:

> Allowed because: *gold members get 3 free checked bags per passenger in economy*

Stessa frase, cambiati livello e numero. **L'esempio ha innescato il comportamento**: l'agente ha
preso un *diritto* e l'ha trattato come un *ordine*. È il rischio del «mettiamo esempi più
espliciti», manifestatosi dove non lo aspettavo. Difetto introdotto dalla v5: la v4, che non
aveva quell'esempio, passava il task 8.

Radice comune: **un diritto non è un'istruzione.** Compensazione permessa ≠ da dare, bagaglio
incluso ≠ richiesto. Una riga sola le copre entrambe, ed è un principio generale, non una toppa
sui due task — distinzione che tengo perché correggere dopo aver visto fallire è la stessa
categoria di mossa che avevo respinto ad Andrea il giorno prima, e va dichiarata nel report.

### Sottomissione a Sierra: cosa è valido e cosa no

Deciso di puntare alla PR sul repo pubblico. Vincoli letti in `docs/leaderboard-submission.md`:

- **Non serve nessuna registrazione**: è una pull request. Fork, `submission.json`, una riga in
  `manifest.json`, tracce ospitate fuori dal repo e linkate nella PR.
- **Un solo dominio è ammesso** («you may submit results for a single domain»). Airline basta.
- **I 4 trial sono una preferenza dichiarata** («we strongly prefer»), non un requisito.
- La nostra è **Custom**: `submission_type: "custom"`, note metodologiche complete,
  `modified_prompts: true`, link all'implementazione (questo repo).

**Piano scartato**: 1 trial di v5 + 3 di v6 dichiarati come «4 trial». Viola il requisito 2
(«all trajectory files must use the same agent… with identical arguments») e svuota di senso il
pass^k, che misura *lo stesso sistema* ripetuto. Sarebbe l'unica cosa del progetto che un
revisore potrebbe chiamare scorretta. Le strade valide sono tre: v5 a 1 trial (costo zero, già
conforme salvo la preferenza), v5 a 4 trial (~$6, consolida i due difetti noti), v6 a 4 trial
(~$8, il trial 1 resta dato del report ma non della sottomissione).

### Chi si vede accettato — con il limite del dato

67 submission accettate, 9 custom e 58 standard. Fuori dai grandi laboratori: Distyl AI, Pine AI,
LiveKit (aziende), Pickle (indipendente), NEU (università). **Nessuna da un individuo senza
organizzazione.** Il regolamento non chiede alcun accreditamento — i criteri sono tutti tecnici —
ma non esiste precedente di una persona singola: assenza di precedenti, non divieto. Limite del
dato, dichiarato: stiamo guardando solo le submission **accettate**, non quelle rifiutate.

### In coda, non fatto

La segnalazione del bug dell'hash (`scratch_issue_taubench.md`) resta **non inviata**. Bozza
verificata da un secondo agente in ruolo di avvocato del diavolo, quattro correzioni applicate.
È contenuto pubblico e permanente su un repo di terzi a nome di Andrea: la manda lui, o serve un
`gh auth login` fatto da lui più un via libera esplicito.

## 2026-09-05 (2) — La v6: la conferma unica concentrava il rischio invece di ridurlo

Il trial 1 della v5 ha rivelato un difetto di progetto che la sonda `s11` non poteva vedere,
perché girava solo su task già falliti. **La v5 ha più fallimenti da chiusura anticipata della
v4, non meno**: 4 contro 3 (baseline: 2). La conferma unica non ha risolto il problema, l'ha
spostato — recupera 17 e 21, ma crea 20 e 44, dove la v4 eseguiva tutte le scritture e la v5
non ne esegue **nessuna**.

Il meccanismo, una volta visto, è ovvio: confermare azione per azione distribuisce il rischio, e
se il cliente riaggancia a metà il grosso è già fatto. **Una conferma sola concentra tutto in un
istante**: se quel "sì" non arriva, non è stato fatto niente. Avevamo ottimizzato il numero di
finestre di rischio senza accorgerci di averne aumentato la posta.

Correzione a una nostra stima: il backport valeva "+1 sulla v5" solo perché l'avevamo misurato
sul set di fallimenti della **v4**. Sul set reale della v5 (20, 33, 44) ne varrebbe fino a 3.
La stima era giusta sul campione sbagliato.

### Le due modifiche della v6

1. **Un diritto non è un'istruzione.** Copre entrambe le regressioni contro il baseline: la
   compensazione non richiesta del task 2 e il bagaglio non richiesto del task 8. È un principio
   generale, non una toppa sui due casi. Rimosso anche l'esempio sul bagaglio gratuito che li
   innescava.
2. **Il messaggio di conferma si apre con «non ho ancora fatto nessuna di queste modifiche».**
   Attacca il meccanismo (il cliente crede che il lavoro sia fatto) senza toccare il benchmark.

### Sonda `s14`: 4 recuperi su 5, e la firma sparisce da tutti

| task | v5 | v6 | |
|---|---|---|---|
| 2 | 0.0 | **1.0** | nessuna compensazione emessa |
| 8 | 0.0 | **1.0** | nessun bagaglio inventato |
| 20 | 0.0 | **1.0** | prenotazione eseguita |
| 44 | 0.0 | **1.0** | tutte e tre le modifiche eseguite |
| 33 | 0.0 | 0.0 | ma **esegue entrambe** le azioni attese |

**Nessuno dei cinque finisce più con una domanda in sospeso**, il 33 compreso: fallisce ora per
argomenti, non per abbandono. Una riga di prompt ha fatto, senza modificare lo strumento di
misura, più di quanto avrebbe fatto il backport che avevamo scartato.

Cautela dichiarata: i 5 task erano scelti perché fallivano, e le due modifiche toccano *tutti* i
task. Proiettare 38+4=42/50 sarebbe l'errore esatto commesso con la v5, dove i 5 recuperi della
sonda si riassorbirono. Il numero vero lo dà solo un trial completo.

### Vincoli reali della sottomissione, verificati sulle PR di Sierra

- **62 PR di sottomissione: 50 accettate, 12 chiuse.** Ma dieci delle dodici corrispondono a
  submission oggi presenti sulla leaderboard (Pine, Distyl, ToolOrchestra, Sonnet 4.5, Gemini
  Flash Live, gpt-realtime): erano duplicati o PR rifatte, non rifiuti. **Ripresentare una PR non
  brucia nulla** — ToolOrchestra e Distyl l'hanno fatto entrambe.
- **Il criterio d'accettazione, dalle parole del maintainer** (PR #368): *«acceptance — including
  for custom submissions — requires that we can verify what was evaluated»*. I tre motivi che
  bloccavano quella PR erano: nessun link all'implementazione, prompt segreti non auditabili,
  percorso di servizio non dichiarato. **Nessuno riguarda chi sei.** Su tutti e tre siamo messi
  meglio di quella submission aziendale: repo pubblico, prompt in chiaro, API standard.
- **Le submission a 1 trial vengono accettate**: quella di Anthropic per Claude Opus 4 ha
  `pass_1: 59.6` e `pass_2/3/4: null`, con nota «incomplete evaluation (Pass^1 only)».
- **Il baseline non serve a Sierra**: si sottomette il proprio agente, non un termine di paragone.
  I trial multipli riguardano solo noi.
- **Scartato** (di nuovo, su richiesta): dichiarare 4 trial mescolando v5 e v6 perché «cambia una
  riga sola». L'argomento si autodistrugge: se quella riga cambia il comportamento — ed è la cosa
  che vorremmo mostrare — allora i trial non sono dello stesso sistema. Il confronto v5/v6 su una
  riga va nelle note metodologiche, dove è un contributo interessante, non nel conteggio.

### Langfuse, verificato via API

Sei Run nello stesso dataset (baseline, v1, v2, v3, v4, v5), 50 item ciascuno sugli stessi task.
Ogni item porta `transcript` (dialogo turno per turno), `reward`, `db_check`,
`reward_breakdown`, `action_metrics`, `communicate_checks`, `termination_reason`, più gli score
agganciati riga per riga. Due note per gli screenshot: l'SDK accoda un timestamp ISO lungo al
nome del Run (prolisso in una schermata di confronto, si può ripulire ripubblicando a costo
zero), e `failure_family`/`write_action_score` compaiono solo dove hanno senso, quindi su un
task riuscito quelle colonne appaiono vuote.

## Registro spesa API (tetto €20)

| Data | Run | Task | Modello | Costo | Totale progressivo |
|---|---|---|---|---|---|
| 2026-08-29 | test isolato tool calling (5 prompt) | 5 | gemini-3.5-flash-lite | ~$0 (tier gratuito) | $0.00 |
| 2026-08-29 | 3 task veri (id 0,1,2) | 3 | gemini-3.5-flash-lite | $0.0819 | $0.08 |
| 2026-08-29 | baseline 10 task sviluppo (id 0-9) | 10 | gemini-3.5-flash-lite | $0.2642 | $0.35 |
| 2026-08-30 | smoke test S4 (task 2, 7 + tentativi falliti per quota) | 2 | gemini-3.5-flash-lite | $0.0622 | $0.41 |
| 2026-08-31 | batch S4 non registrato a suo tempo (12:33-12:52, 8 completati + 3 infra_error) | 8 | gemini-3.5-flash-lite | $0.3209 | $0.73 |
| 2026-08-31/09-01 | S5 round2, tutti i tentativi (quota giornaliera + RPM, retry, arricchimento dataset) fino a 10/10 con dato reale | 15 simulazioni con costo (comprende retry falliti e riusciti) | $0.702 | $1.43 |
| 2026-09-01 | S5 round3, sonde sul task 44 (1 troncata dal nostro timeout, 1 completata, 3 infrastructure_error a costo zero) | 2 simulazioni con costo | $0.157 | $1.59 |
| 2026-09-01 | S5 sonda 5 sul task 44, con clausola 3 ristrutturata e limitatore RPM: **reward 1.0** | 1 simulazione | $0.095 | $1.69 |
| 2026-09-01 | **S5 round3 completo**: 9 task eseguiti (il 44 riusato dalla sonda 5 a costo zero) — 7/10, quattro recuperi su sette | 9 simulazioni | $0.426 | $2.11 |
| 2026-09-02 | **S6: i 100 task** (50 baseline `llm_agent` + 50 `custom_agent`), cinque chiavi in parallelo, zero fallimenti | 100 simulazioni | $3.680 | $5.79 |
| 2026-09-02 | **S7: la v2 sui 50 task** (piu' 5 ripetuti dopo la caduta di rete) | 55 simulazioni | $1.997 | $7.79 |
| 2026-09-02 | **S7: la v3 sui 50 task**, solo clausola del trasferimento — falsifica l'attribuzione per clausola | 50 simulazioni | $1.890 | $9.68 |
| 2026-09-04 | **Il giudice**: 3 giri di sviluppo + 48 etichette sul run v1 | 81 chiamate | $0.052 | $9.73 |
| 2026-09-04 | **Seconda esecuzione** di baseline e custom v1, interrotta a 73/100 dalla morte delle chiavi | 73 simulazioni | $2.523 | $12.25 |
| 2026-09-04 | **S8: la v4 sui 50 task** (`s10`), un solo processo, zero fallimenti — 74%, sotto v1 | 50 simulazioni | $2.103 | $14.35 |
| 2026-09-04 | **Controllo `s11`**: la v5 sui 9 task falliti e non rotti in partenza — diagnosi, non pass rate | 9 simulazioni | ~$0.40 | ~$14.75 |
| 2026-09-05 | **`s12`**: v5 senza backport sui task 17, 21, 33 — isola le due correzioni | 3 simulazioni | ~$0.13 | ~$14.88 |
| 2026-09-05 | **Trial 1 della v5** (`s13`), 50 task — 38/50, sopra la soglia di arresto | 50 simulazioni | $2.028 | ~$16.91 |
| 2026-09-05 | **Sonda `s14`**: v6 sui 5 task da recuperare — 4 su 5, diagnosi non pass rate | 5 simulazioni | ~$0.21 | ~$17.12 |
