# Come si scrivono regole comportamentali che un agente segue davvero

Ricerca su fonti primarie, fatta prima della fase di correzione. Serve a rispondere a una domanda
precisa: abbiamo sei famiglie di fallimento diagnosticate; **con che criterio scriviamo le regole
che dovrebbero correggerle, in modo da essere ragionevolmente sicuri che funzionino invece di
limitarci a sperarlo?**

Non è una rassegna generale di prompt engineering. È il set di vincoli che applicheremo a ogni
singola regola che scriveremo in `custom_agent.py`.

---

## 1. Fonti

Tutte primarie (documentazione ufficiale dei produttori di modelli e paper), non riassunti di terzi:

| Fonte | Cosa ci dà |
|---|---|
| [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) (Anthropic) | il concetto di "altitudine giusta", struttura del system prompt, esempi canonici |
| [The new rules of context engineering for Claude 5](https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models) (Anthropic) | costo delle regole in conflitto, regole positive vs divieti, "codice invece di prosa" |
| [Prompting best practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices) (Claude Platform Docs) | essere espliciti sull'azione, istruzioni come passi numerati |
| [Building effective AI agents](https://www.anthropic.com/engineering/building-effective-agents) (Anthropic) | semplicità, trasparenza dei passi di pianificazione |
| [A practical guide to building agents](https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/) (OpenAI) | routine derivate dai documenti operativi esistenti, guardrail come layer separato |
| [τ²-Bench](https://arxiv.org/pdf/2506.07982) | il nostro benchmark: reward 0 se una qualsiasi regola di policy è violata |
| [Analyzing and Internalizing Complex Policy Documents for LLM Agents](https://arxiv.org/pdf/2510.11588) | tassonomia delle clausole di policy: fattuali / comportamentali / condizionali |
| [HANDBOOK.md: A Benchmark for Long-Context Agentic Instruction Following](https://arxiv.org/html/2607.25398v1) | i quattro modi in cui gli agenti smettono di seguire una policy permanente |

---

## 2. Cosa dicono, tema per tema

### 2.1 L'altitudine giusta

Il punto centrale di tutta la ricerca. Anthropic descrive due modi opposti di sbagliare un system
prompt:

- **troppo basso**: "hardcoding complex, brittle logic in their prompts to elicit exact agentic
  behavior" — un if-else scritto in prosa, che copre il caso visto e nient'altro;
- **troppo alto**: "vague, high-level guidance that fails to give the LLM concrete signals for
  desired outputs".

La formulazione che ci interessa: *"specific enough to guide behavior effectively, yet flexible
enough to provide the model with strong heuristics"*.

Questo è **esattamente** il compromesso determinismo/overfitting che avevamo già stabilito in S4
per la definizione delle famiglie, arrivandoci per conto nostro. Vale identico per le regole.
Buona notizia metodologica: la regola che abbiamo scritto in `DIARIO.md` non è un'invenzione
locale, è consenso di settore.

### 2.2 Regole positive, non divieti

Anthropic documenta un cambiamento nel proprio prompt di Claude Code, da:

> "Never write multi-paragraph docstrings or multi-line comment blocks"

a:

> "Write code that reads like the surrounding code: match its comment density, naming, and idiom"

Il divieto dice cosa non fare e lascia indeterminato cosa fare al suo posto; la formulazione
positiva descrive il comportamento desiderato ed è quindi eseguibile. Le nostre famiglie sono
descrizioni di *errori*: tradurle in "non fare X" è la strada facile e sbagliata. Ogni regola deve
prescrivere l'azione alternativa, esplicitamente.

### 2.3 Le regole in conflitto costano più di quanto rendono

Sempre Anthropic, dall'analisi delle proprie tracce: istruzioni sovrapposte creano "cognitive
overhead", con esempi reali di contraddizioni nello stesso prompt ("leave documentation as
appropriate" + "DO NOT add comments"). Il modello spende ragionamento a risolvere la
contraddizione invece che a fare il lavoro.

Corollario diretto per noi: **aggiungere sei regole a un prompt che ne ha già cinque non è
un'operazione neutra**. Ogni regola nuova va confrontata con quelle esistenti in
`POLICY_HIGHLIGHTS` per verificare che non le contraddica e non le duplichi.

### 2.4 Codice invece di prosa, dove si può

> "design better interfaces and tool parameters"

L'esempio di Anthropic: rendere lo stato del Todo tool un'enum `(pending, in_progress, completed)`
insegna l'uso meglio di qualsiasi regola scritta. Una regola davvero deterministica non dovrebbe
stare nel prompt: dovrebbe stare nel codice, dove non può essere ignorata.

Abbiamo già applicato questo principio senza chiamarlo così, in S3: il limite di 3 errori
consecutivi e il limite di 30 turni sono forzati dal codice, non affidati al giudizio del modello.
La domanda da porsi per ogni famiglia diventa quindi: *questa correzione è una regola di prompt o
è un controllo di codice?*

### 2.5 Struttura e minimalismo

Organizzare il prompt in sezioni distinte (`<background_information>`, `<instructions>`,
`## Tool guidance`, `## Output description`) con tag XML o intestazioni Markdown. E puntare al
"minimal set of information that fully outlines your expected behavior" — dove *minimal* non
significa *corto*: significa niente di superfluo, ma tutto il necessario.

### 2.6 Esempi canonici

> "For an LLM, examples are the 'pictures' worth a thousand words."

L'indicazione è di curare "diverse, canonical examples", non di accumularne tanti. Per una regola
che riguarda un formato (la famiglia 2, formattazione numerica) un esempio vale più di qualsiasi
descrizione a parole.

### 2.7 Essere espliciti sull'azione da compiere

Dalle best practice ufficiali: i modelli addestrati a seguire istruzioni alla lettera fanno
esattamente ciò che chiedi. "Can you suggest some changes" produce suggerimenti; "Change this
function" produce modifiche. E: dare le istruzioni come **passi sequenziali numerati** quando
l'ordine o la completezza contano.

Rilevante per la famiglia 6 (richiesta multi-elemento con esiti misti): il comportamento corretto
è una procedura in più passi, e va scritta come tale, non come principio.

### 2.8 Le regole "decadono con la distanza"

Il risultato più scomodo, dal paper HANDBOOK.md. Quattro modi ricorrenti in cui gli agenti
smettono di rispettare una policy permanente:

1. lasciano che una richiesta plausibile ma non autorizzata **sovrascriva** la policy;
2. eseguono il controllo richiesto **e poi agiscono contro il suo risultato**;
3. **perdono i dettagli** della regola su orizzonti lunghi;
4. **dichiarano una conformità che non hanno raggiunto**.

E, sulla natura del problema: il documento non funziona come autorità permanente contro cui
vengono filtrate le azioni candidate, ma come una fonte in più, la cui influenza decade con la
distanza. Con criteri di valutazione applicati in modo rigoroso, il modello migliore del paper
arriva al 36,2%.

Due conseguenze pratiche. Primo: mettere una regola nel system prompt **non garantisce** che venga
applicata al turno 20 — la posizione e la ripetizione al punto d'uso contano. Secondo: il punto 4
spiega perché non ci fidiamo di quello che l'agente dichiara di aver fatto, ma andiamo a leggere
`results.json`. Era già la nostra pratica (regola "verifica prima di diagnosticare"): qui è
documentata come modo di fallire tipico, non come nostra prudenza.

### 2.9 Le clausole di policy non sono tutte dello stesso tipo

Il paper su CC-Gen classifica le specifiche di policy in tre categorie — **fattuali**,
**comportamentali**, **condizionali** — e isola quelle condizionali come le vere responsabili
della complessità di workflow. Trova che il fine-tuning supervisionato "degrada bruscamente al
crescere della complessità della policy".

Utile come griglia diagnostica sulle nostre famiglie: la 2 è fattuale (un formato), la 1 e la 5
sono comportamentali (chiedi prima di agire), la 3 e la 6 sono condizionali (dipendono dall'esito
di un controllo) — ed è coerente col paper che le condizionali siano le più difficili. Non
adottiamo la loro soluzione (continued pretraining: fuori scope, richiederebbe addestrare un
modello), ma la classificazione ci dice **dove aspettarci che una regola di prompt non basti**.

### 2.10 Routine e guardrail (OpenAI)

Due indicazioni utili: derivare le routine dai documenti operativi che già esistono — nel customer
service, una routine corrisponde grosso modo a un articolo della knowledge base — e scomporre le
risorse dense in passi più piccoli e chiari, il che riduce l'ambiguità. In più, i guardrail sono
trattati come un **layer separato** dalle istruzioni (filtri sull'input, sull'uso dei tool,
intervento umano), non come regole di prompt: la stessa distinzione del §2.4.

Per noi: `policy.md` **è** il documento operativo. Le nostre regole non devono riscrivere la
policy, devono trasformare i punti che l'agente sbaglia in procedure passo-passo.

---

## 3. Un caveat che vale per tutto il resto

Anthropic scrive che per i modelli di ultima generazione hanno potuto **eliminare** molte regole,
perché hanno "better judgement... can handle these decisions well without explicit rules".

**Questo non vale per noi.** Il nostro agente gira su `gemini-3.5-flash-lite`: un modello piccolo,
scelto per costo. Il consiglio "togli le regole, fidati del giudizio" è calibrato su modelli di
frontiera. Nel nostro caso l'indicazione va letta al contrario: dove un modello grande se la cava
con un'euristica, il nostro ha bisogno che la procedura sia scritta.

Il che rende ancora più importante il principio del §2.4: più il modello è piccolo, più conviene
spostare i vincoli deterministici fuori dal suo giudizio.

---

## 4. La checklist operativa

Questo è il deliverable. Ogni regola che scriveremo deve passare **tutti** questi controlli prima
di finire nel codice. Sono formulati come test binari, apposta.

1. **Trigger osservabile prima dell'azione.** La regola parte da una situazione che l'agente può
   riconoscere *prima* di sbagliare, non dall'errore. (Regola già nostra, da S4 — vedi `DIARIO.md`.)
2. **Prescrive un'azione, non un divieto.** Se la regola contiene "non", riscriverla dicendo cosa
   fare al suo posto. (§2.2)
3. **Verificabile nel turno.** Un revisore umano che legge un singolo turno deve poter dire sì/no
   se la regola è stata rispettata. Se serve interpretazione, la regola è troppo alta. (§2.1)
4. **Nessun conflitto e nessun duplicato.** Confronto esplicito con le regole già presenti in
   `AGENT_INSTRUCTION` e `POLICY_HIGHLIGHTS`. Se si sovrappone, si fonde: non si aggiunge. (§2.3)
5. **Altitudine giusta.** La regola non nomina il caso osservato (nessun id di prenotazione,
   nessun numero di task), ma non è nemmeno un principio generale ("sii accurato"). Generalizzata
   al minimo che l'evidenza sostiene. (§2.1)
6. **Prompt o codice?** Se la condizione è verificabile in modo puramente meccanico dallo stato
   della conversazione, il posto giusto è il codice, non il prompt. (§2.4)
7. **Procedura, se ha più passi.** I comportamenti in più passi si scrivono come passi numerati in
   ordine, non come principio. (§2.7)
8. **Esempio solo se serve, e mai preso dal caso osservato.** Un esempio si aggiunge solo quando
   la regola descrive una forma difficile da dire a parole — tipicamente un formato. Se la regola
   si esprime bene in prosa, l'esempio è solo token in più. E l'esempio deve essere *canonico*,
   cioè rappresentativo della classe: costruirlo con i numeri o i dati del task che si sta
   correggendo è overfitting travestito da buona pratica. (§2.6, e §2.5 sul minimalismo)
9. **Costo di regressione dichiarato.** Prima di scrivere la regola, dire quale task già passante
   potrebbe rompere. È il motivo per cui il dataset `airline-s4-round2` contiene i tre canary
   (0, 41, 42) accanto ai sette fallimenti.

Una regola che non passa un controllo non è necessariamente da buttare: può voler dire che va
spostata nel codice (6), spezzata in due (4), o che quella famiglia non è correggibile con una
regola — come già stabilito per la famiglia 4.

---

## 5. Nota sulla verifica

τ²-bench assegna reward 0 se **una qualsiasi** regola di policy è violata, anche quando la
richiesta dell'utente è stata soddisfatta. Quindi una regola nuova che sistema una famiglia ma ne
rompe un'altra si vede subito nel punteggio: è un segnale netto, ed è il motivo per cui i canary
stanno nel dataset.

Ma un singolo run non è una misura: le simulazioni sono stocastiche, e il benchmark originale
misura la consistenza su più tentativi (pass^k) proprio perché l'esito varia tra run identici. Con
il nostro budget non possiamo fare k run per task; la conseguenza è che un delta di **un solo
task** tra prima e dopo non è una prova di miglioramento, e va detto come tale nel report finale
invece di essere venduto come risultato.
