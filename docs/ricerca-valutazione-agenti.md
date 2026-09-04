# Ricerca: valutare agenti LLM oltre il pass rate binario

Nota metodologica: documento di ricerca, nessuna modifica a codice o esperimenti. Ogni
affermazione è citata con fonte primaria.

## 1. Perché τ-bench/τ²-bench usano pass^k e non il pass rate a singola esecuzione

Il paper originale è **τ-bench: A Benchmark for Tool-Agent-User Interaction in Real-World
Domains** (Yao, Shinn, Razavi, Narasimhan — Sierra Research, arXiv:2406.12045, giugno 2024,
https://arxiv.org/abs/2406.12045). Il dominio "airline" del nostro progetto viene da qui; il
sequel telecom **τ²-Bench** (arXiv:2506.07982, giugno 2025,
https://arxiv.org/abs/2506.07982) mantiene la stessa metrica.

- **Definizione**: pass^k è "la probabilità che tutte le k prove i.i.d. sullo stesso task
  abbiano successo, mediata sui task" — formula: `pass^k = E_task[C(c,k) / C(n,k)]`, dove n =
  prove totali, c = prove riuscite, C = coefficiente binomiale (arXiv:2406.12045). È
  l'opposto concettuale di pass@k (usato in code-gen, tipo Codex/HumanEval): pass@k misura
  la probabilità che *almeno una* prova su k riesca (capacità di scoperta), pass^k misura che
  *tutte* riescano (affidabilità/consistenza).
- **Motivazione testuale**: gli autori distinguono esplicitamente i due casi d'uso — pass@k
  è adatto quando conta la "scoperta di soluzioni" (code generation), mentre un agente
  conversazionale verso clienti reali deve garantire "affidabilità e consistenza" su
  interazioni ripetute con la stessa semantica del task, perché un singolo fallimento è
  costoso e il cliente non può "ritentare" come farebbe un compilatore.
- **Fonte della varianza**: la non-determinatezza viene dal campionamento del modello sia
  nel simulatore-utente sia nell'agente, nonostante database e istruzioni siano fissi
  (arXiv:2406.12045).
- **Numeri riportati**: nel dominio retail, GPT-4o passa da pass^1 = 61.2% a pass^8 < 25%;
  nel dominio airline pass^1 = 35.2% con degradazione rapida all'aumentare di k. Cioè un
  agente che "funziona" al primo tentativo può fallire la maggioranza delle volte se
  richiamato più volte sullo stesso task — esattamente il fenomeno di cui l'autore del
  progetto ha fatto esperienza diretta.

## 2. Gestione professionale della varianza nella valutazione di agenti

- **Anthropic, "A statistical approach to model evaluations"** (nov. 2024,
  https://www.anthropic.com/research/statistical-approach-to-model-evals): raccomanda di
  riportare sempre l'errore standard (SEM) accanto al punteggio di un eval, con intervallo di
  confidenza al 95% calcolato come media ± 1.96×SEM; per confronti fra due sistemi, il test
  "paired-differences" è definito una tecnica di riduzione della varianza "gratuita" perché
  elimina la variabilità dovuta alla difficoltà del singolo task e isola quella dovuta alla
  risposta del modello (la correlazione fra modelli frontier è tipicamente 0.3–0.7). Nota:
  il post si concentra su punteggi continui/CLT più che su intervalli alla Wilson per
  proporzioni binarie — per il pass/fail binario del nostro progetto (50 task, esito 0/1),
  l'intervallo di Wilson (o Clopper-Pearson) resta lo standard per proporzioni, ma non è
  trattato in dettaglio in questo post specifico.
- **Non-determinismo a temperature=0**: *"Non-Determinism of 'Deterministic' LLM Settings"*
  (arXiv:2408.04667, https://arxiv.org/html/2408.04667v5) misura su run ripetuti a
  temperatura 0 variazioni di accuratezza fino al 15% fra run "identici", con gap fra
  performance migliore e peggiore fino al 70% su alcuni benchmark (es. matematica college:
  75%→3%). Gli autori attribuiscono la causa a ottimizzazioni infrastrutturali (continuous
  batching, prefix caching) più che al modello stesso, e raccomandano di riportare
  min/max su più run invece di un singolo numero — il che conferma indipendentemente,
  su un altro tipo di benchmark, il fenomeno osservato dall'autore del progetto.
- **Ripetizioni tipiche**: la pratica varia parecchio nella letteratura recente. Uno studio
  di valutazione closed-loop per agenti di sviluppo software (ScienceDirect,
  https://www.sciencedirect.com/science/article/pii/S1383762126002559) usa 3 ripetizioni per
  task, esplicitamente per "esporre differenze comportamentali major, non per risolvere
  differenze piccole" — con un campione binario effettivo di sole 15 osservazioni (5 task ×
  3). Altri lavori usano bootstrap con 1.000–10.000 resample per calcolare intervalli di
  confidenza al 95% sulle metriche aggregate. Non esiste un numero "magico" universalmente
  citato: la scelta dipende dal budget e dal quanto piccolo è l'effetto che si vuole
  distinguere dal rumore — il punto rilevante per noi è che con k=1 (una sola esecuzione per
  condizione, come nei nostri run) qualunque differenza sotto ~5-10 punti su 50 task è
  compatibile con puro rumore campionario, coerente con quanto osservato empiricamente dal
  progetto.

## 3. La figura "evaluation engineer" / AI evals

- **Hamel Husain**, ML engineer (ex Airbnb/GitHub) e coautore del libro *Evals for AI
  Engineers* (O'Reilly), è la fonte primaria più citata sul tema. Nel post **"Your AI
  Product Needs Evals"** (https://hamel.dev/blog/posts/evals/) descrive il lavoro concreto su
  tre livelli: (1) *unit test/assertion* rapidi ed economici da eseguire a ogni modifica di
  codice; (2) **error analysis** sistematica — "you must remove all friction from the process
  of looking at data" — cioè costruire strumenti per leggere le tracce e classificare i
  fallimenti a mano prima di automatizzare; (3) **LLM-as-judge**, iterando sul prompt del
  giudice finché non è allineato al giudizio umano di dominio. Nel post FAQ
  (https://hamel.dev/blog/posts/evals-faq/) stima che il 60-80% del tempo in questi progetti
  va in error analysis, non nella costruzione dell'infrastruttura di giudizio automatico.
- **Anthropic, "Writing effective tools for AI agents—using AI agents"**
  (https://www.anthropic.com/engineering/writing-tools-for-agents) descrive concretamente
  cosa si misura per un agente che usa tool, oltre al pass/fail: tempo totale di esecuzione
  dei singoli tool call e del task, numero totale di chiamate, consumo di token, errori dei
  tool. Raccomandano anche di evitare eval "sandbox" troppo semplicistiche e di costruire
  task realistici che richiedano "potenzialmente decine" di tool call — un promemoria utile
  perché i nostri 50 task airline sono comparabili come scala.
- In sintesi (fonti concordi): il lavoro non è "scrivere un giudice e finire", ma leggere
  molte tracce a mano, costruire dataset di errori etichettati, iterare sul prompt del
  giudice/agente, e solo dopo automatizzare — un ciclo molto simile a quanto già fatto nel
  progetto per S4 (diagnosi in famiglie di fallimento).

## 4. Metriche a grana fine oltre il binario, per agenti che eseguono azioni

- **Il codice sorgente di τ-bench stesso** è la fonte più rilevante qui, perché è il
  benchmark che stiamo usando. Il reward ufficiale (https://github.com/sierra-research/tau-bench)
  è binario: a fine conversazione l'ambiente rigioca le azioni "golden" (ground-truth) sul
  DB iniziale, confronta l'hash SHA256 dello stato finale con quello prodotto dall'agente, e
  assegna 1.0/0.0. Non c'è F1 o partial credit nel reward primario.
  - Un **issue reale sul repo** (#12, https://github.com/sierra-research/tau-bench/issues/12)
    documenta un problema concreto della parte "output" del reward: viene fatto un semplice
    substring match fra la risposta testuale dell'agente e l'output atteso, e questo può dare
    reward 1.0 a una risposta *fattualmente sbagliata* solo perché la stringa attesa compare
    per caso nel testo — un caso reale, non teorico, di quanto un reward binario può essere
    fragile.
  - Sierra ha però pubblicato un secondo script, **`auto_error_identification.py`**
    (https://github.com/sierra-research/tau-bench/blob/main/auto_error_identification.py),
    che NON dà un punteggio ma classifica ogni fallimento con un giudice LLM in una
    tassonomia a due livelli: (a) chi ha causato il fallimento — utente (azione non motivata
    dalla sua istruzione), agente, o ambiente; (b) per i fallimenti causati dall'agente, il
    tipo — tool sbagliato, argomento del tool sbagliato, goal completato solo parzialmente,
    altro. È strutturalmente lo stesso approccio delle "famiglie di fallimento" già usato nel
    progetto per S4 — conferma indipendente, dagli stessi autori del benchmark, che
    classificare-per-causa è più informativo del reward binario.
- **Standard più ampi in letteratura** (survey/guide, non tutti primari ma tecnicamente
  concreti): il **"Tool-Calling F1"** confronta l'insieme di tool invocati dalla traiettoria
  candidata con quelli della traiettoria "golden", con una variante bag-based per gestire
  chiamate ripetute (precision/recall sui singoli tool call). Alcuni framework di step-level
  evaluation confrontano l'azione predetta con quella di riferimento passo-per-passo
  ("operation accuracy/F1"), con scoring a partial credit (es. 0 / 0.5 / 1 per
  incorretto/parziale/esatto). Anche i **grader di OpenAI Evals**
  (https://developers.openai.com/api/docs/guides/graders) supportano esplicitamente il
  partial credit tramite "fact grading": se una risposta copre 3 fatti attesi su 5, il
  punteggio è 0.6 invece di tutto-o-niente. Non ho trovato uno standard unico e
  universalmente adottato per la "edit-distance sulla traiettoria" in agenti conversazionali
  multi-turno come τ-bench: le F1 su tool-call sono lo strumento più citato, ma restano
  ad-hoc per progetto.

## Cosa possiamo usare nel nostro report

1. **La citazione più forte e diretta**: il paper τ-bench stesso mostra che pass^1 e pass^8
   possono differire di decine di punti sullo stesso agente — è la prova, dagli stessi autori
   del benchmark, che una singola esecuzione a 50 task non misura la vera capacità
   dell'agente, e giustifica esplicitamente perché "±2-5 task" osservato dall'autore rientra
   nel rumore atteso, non è una scoperta isolata.
2. **Onesto**: il progetto non ha ripetuto k esecuzioni per task (k=1), quindi non possiamo
   calcolare pass^k reale — possiamo solo citarlo come standard di riferimento che
   spiegherebbe la varianza osservata, non applicarlo retroattivamente ai run già fatti.
3. **Utile per la sezione limiti**: la vulnerabilità del reward per-substring documentata
   nell'issue #12 di tau-bench è un parallelo diretto e verificabile a eventuali dubbi sulla
   robustezza della valutazione binaria nel nostro giudice — vale la pena menzionarla come
   precedente noto, non come nostro difetto.
4. **Coerenza col lavoro già fatto**: `auto_error_identification.py` di Sierra conferma che
   l'approccio "famiglie di fallimento" (S4) è in linea con la pratica dello stesso team che
   ha creato il benchmark — buon argomento per il report, non un'invenzione ad-hoc del
   progetto.
5. **Da non forzare**: non abbiamo dati per affermare quante ripetizioni "servirebbero"
   per il nostro caso specifico (dipende dall'effect size che vogliamo rilevare, che non
   abbiamo stimato) — meglio dire onestamente "la letteratura non converge su un numero
   fisso" piuttosto che citare una cifra (es. "3 run" o "8 run") come se fosse una regola.
