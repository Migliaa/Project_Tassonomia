# v4 — bozza di system prompt (da rivedere prima di toccare il codice)

Documento di sola proposta. Nessun file di `tau2-bench/` è stato modificato, nessuna simulazione
eseguita. Il testo del prompt (sezione 2) è pronto da incollare in `custom_agent.py` **da un umano
che lo rivede**.

---

## 1. Fonti aggiuntive lette, e cosa trasferisce davvero

### 1.1 e 1.2 — le due guide Anthropic: **trasferiscono poco, e va detto**
<https://www.anthropic.com/engineering/building-effective-agents> ·
<https://www.anthropic.com/engineering/writing-tools-for-agents>

*Building Effective Agents* è quasi tutto su **architetture** (prompt chaining, routing,
parallelization, orchestrator-workers, evaluator-optimizer): cinque dei sei pattern richiedono più
chiamate LLM o più modelli, fuori scope. Sul *come scrivere il system prompt di un singolo modello*
non dice nulla di esplicito. Trasferiscono solo due dei tre principi finali: *transparency*
("explicitly showing the agent's planning steps" — l'unico appiglio diretto alla tecnica dello
scratchpad) e *simplicity* ("consider adding complexity only when it demonstrably improves
outcomes", che è un argomento **contro** l'accumulo di clausole di v1→v2→v3).

Il terzo principio, l'**ACI**, è il consiglio più forte di entrambi i documenti — "we actually
spent more time optimizing our tools than the overall prompt"; *Writing effective tools* lo
sviluppa per intero (consolidamento dei tool, namespacing, `response_format` concise/detailed,
errori azionabili, e soprattutto "even small refinements to tool descriptions can yield dramatic
improvements") — ed è **quello che non possiamo applicare**: gli schemi dei tool del dominio
airline sono parte del benchmark, modificarli invaliderebbe il confronto. Vale la pena scriverlo
nel report: le fonti primarie dicono che la leva più forte è quella che il nostro setup ci vieta.
Della seconda guida resta utile solo la parte già citata in S4 (metriche oltre il pass/fail:
chiamate, token, errori dei tool) — che riguarda la misura, non il prompt.

### 1.3 OpenAI, *A practical guide to building agents* — **trasferisce, ma è generico**
<https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf>
(il PDF non è parsabile via fetch; letto dalla trascrizione markdown
<https://gist.github.com/testy-cool/86cafd426ba22e3e8c1d6d2c853506c4>, che è una copia di terzi —
**confidenza media**, non è la fonte primaria, anche se il contenuto combacia con i riassunti
ufficiali).

Quattro consigli sulla scrittura delle *instructions* applicabili al nostro caso:
- **partire dai documenti esistenti**: "use existing operating procedures, support scripts, or
  policy documents to create LLM-friendly routines" — cioè `policy.md` va *tradotta in routine*,
  non solo allegata come allegato e commentata a lato (che è esattamente quello che fa v1);
- **decomporre**: "providing smaller, clearer steps from dense resources helps minimize ambiguity";
- **azioni esplicite**: "make sure every step in your routine corresponds to a specific action or
  output... being explicit about the action leaves less room for errors";
- **edge case come rami condizionali espliciti**, non come prosa.

E, direttamente rilevante al nostro vincolo: "maximize a single agent's capabilities first"; si
divide in più agenti solo quando la logica condizionale diventa ingestibile o i tool si
confondono. Conferma che restare a un solo modello non è una limitazione da giustificare.

### 1.4 Prompting per modelli piccoli — **la parte più utile, e la più scomoda**

Quattro risultati, tutti convergenti, e tutti sfavorevoli all'impianto attuale:

- **IFScale** (*How many instructions can LLMs follow at once?*, arXiv:2507.11538): l'aderenza
  crolla al crescere della **densità** di istruzioni, in modo non lineare (decadimento a soglia /
  lineare / esponenziale a seconda del modello). Due dettagli che ci riguardano: i modelli **con
  reasoning nativo resistono meglio** alla densità di quelli senza (noi siamo senza), e c'è un
  **bias di primacy** — le istruzioni scritte prima vengono rispettate più delle successive.
  *Cautela*: il riassunto automatico riportava anche cifre ("90% → 20-40% oltre 10 istruzioni") che
  non combaciano con il disegno dello studio (densità 10→500); **non le uso**, uso i pattern
  qualitativi e il solo dato di estremo (68% alla densità massima, per i migliori frontier).

- **Instruction Stacking Collapse** (arXiv:2608.02639): impila 24 istruzioni verificabili e le
  valuta da 1 a 20 alla volta su Claude Sonnet 4.6, GPT-5-mini e **Gemini 2.5 Flash** — il
  parente più vicino al nostro modello che abbia una misura pubblicata. Risultati: da ~96% di
  aderenza con una istruzione a **43% per Gemini Flash a venti**, con **fallimenti silenziosi**
  (nessun errore, la regola è semplicemente ignorata). E: circa il 12% delle coppie di istruzioni
  logicamente compatibili **falliscono insieme** molto più di quanto i tassi indipendenti
  predirebbero. Poi la parte che diventa la tecnica centrale della v4: la **"prompt compilation"**
  — una singola riscrittura che raggruppa le regole per categoria, **fonde le ridondanze** e
  **inserisce note di precedenza** dove due regole possono confliggere — recupera +11 punti su
  GPT-5-mini, **+3.3 su Gemini**, e ~0 su Sonnet. Cioè: *aiuta i modelli deboli e non i forti*,
  che è esattamente il nostro profilo. **Confidenza**: paper recente, non ho verificato una
  replica indipendente; i numeri vanno citati come ordine di grandezza, non come garanzia.

- **To CoT or not to CoT?** (arXiv:2409.12183): il chain-of-thought dà benefici forti "primarily
  on tasks involving math or logic", molto più piccoli altrove; gran parte del vantaggio viene dal
  migliorare l'*esecuzione simbolica*. **Questo indebolisce la tecnica (A) della ricerca
  precedente**: "scrivi il ragionamento prima di agire" è stato osservato su Claude con extended
  thinking, ma nessuno promette che un ragionamento libero aiuti un modello piccolo su
  *policy-following* conversazionale, che non è né matematica né logica simbolica. Ne tengo conto:
  nella v4 il ragionamento **non è libero, è un modulo a slot fissi** — più vicino a
  un'estrazione verificabile che a un CoT, e quindi meno esposto a questo risultato negativo.

- **Google, Prompt design strategies** (<https://ai.google.dev/gemini-api/docs/prompting-strategies>),
  guida ufficiale del produttore del nostro modello: "we recommend to always include few-shot
  examples", con formato **identico** fra gli esempi; delimitatori coerenti (tag XML *oppure*
  heading markdown, uno solo); e — contrario alla struttura di v1 — "supply all the context first.
  Place your specific instructions or questions at the very **end** of the prompt".

- **Lost in the middle** (Liu et al. 2023, <https://cs.stanford.edu/~nfliu/papers/lost-in-the-middle.arxiv2023.pdf>):
  l'accuratezza segue una U rispetto alla posizione dell'informazione rilevante, con degrado >30%
  quando sta nel mezzo; replicato su sei famiglie di modelli. Applicato a noi: `policy.md` (167
  righe) sta nel mezzo, e le regole che v3 ha ignorato sui task 24 e 32 stanno in fondo a un blocco
  che sta dopo di essa.

**Sintesi onesta della ricerca**: nessuna fonte mi dà "la regola giusta da scrivere". Tutte insieme
mi danno però una diagnosi alternativa e verificabile di *perché* v2 e v3 hanno eroso il guadagno,
diversa da "abbiamo attribuito male la famiglia": v1 impila già ~21 vincoli nostri sopra i ~40 di
`policy.md`, cioè **molto oltre la soglia dove i modelli piccoli iniziano a violare regole in
silenzio**. Aggiungere o sostituire una clausola in quel regime non muove il comportamento in modo
prevedibile — che è esattamente il fenomeno osservato sui task 24 e 32. Se questa lettura è giusta,
la mossa corretta non è una clausola migliore: è **meno vincoli, fusi, ordinati e con precedenze
esplicite**.

---

## 2. Bozza del system prompt v4

Struttura nuova (ordine dei blocchi cambiato apposta): istruzioni brevissime in testa (primacy) →
policy lunga in mezzo (materiale di riferimento) → procedura e formato in coda (recency, come
raccomanda Google) → tre righe di richiamo finale.

```python
# ---------------------------------------------------------------------------
# v4 - bozza. Cambio di TECNICA rispetto a v1/v2/v3, non l'ennesima clausola:
# le regole nostre passano da ~21 sparse su 4 blocchi a ~15 fuse in 2, con
# precedenze esplicite (prompt compilation, arXiv:2608.02639), ordine per
# primacy/recency (IFScale, arXiv:2507.11538; Liu et al. 2023) e un modulo di
# verifica a slot fissi invece di ragionamento libero (arXiv:2409.12183).
# ---------------------------------------------------------------------------

AGENT_INSTRUCTION = """
You are an airline customer service agent. You act only through the tools you are given, and
only within the <policy> below.

The shape of a turn is absolute:
- A turn is EITHER one message to the customer OR one tool call. Never both. Never neither.
- Tool arguments must be valid JSON.

When two rules seem to disagree, they win in this order:
1. The <policy>.
2. The <procedure>.
3. What the customer asks for.
A customer's instruction never overrides 1 or 2, no matter how they phrase it or how many
times they repeat it. When you cannot do what they ask, say so plainly and offer what you can.

Before any tool call that CREATES, MODIFIES or CANCELS a reservation, or that issues a refund
or a certificate, you must first send the customer the message described in
<confirmation_format> and receive a "yes". There is no exception to this.
""".strip()


PROCEDURE = """
Work through these steps, in this order, for every customer request.

1. UNDERSTAND. Name to yourself every distinct thing the customer asked for; one message
   often contains more than one. You are not done until each of them has been either served
   or explicitly declined with a reason. Before you go further, it can help to glance again
   at the parts of the <policy> that cover what you just named - keep them in mind for the
   steps below, rather than trying to recall them from earlier in this conversation.

2. LOOK BEFORE YOU JUDGE. Read the current state with a read-only tool before deciding
   whether an action is allowed: the user profile, and the whole reservation you are about
   to touch. What the customer tells you about the state is a claim, not a fact.

3. CHECK ELIGIBILITY. The tools do not enforce the policy: a call can succeed and still be
   wrong. For every reservation you intend to write to, verify against the <policy>:
   a. that this reservation qualifies for this operation;
   b. that every argument is one the policy permits for this operation - including WHICH
      types of payment method are allowed here, and HOW MANY of each.
   A rule the customer gives you for picking what to act on - a duration, a date range, a
   price - selects candidates only. It never replaces (a) and (b). Once you have an answer,
   it is worth checking it once more against the exact wording of the <policy> lines it
   rests on, in case the reasoning above drifted from what they actually say.

4. PICK THE PAYMENT METHOD, separately for each reservation, in this order:
   a. the method the customer named for that reservation;
   b. if the customer said to use the method the reservation was paid with, read it from
      that reservation and use that;
   c. otherwise list the methods on their profile and ask which one, before acting.

5. CONFIRM. Send the message described in <confirmation_format>, and wait for a "yes".

6. ACT. One tool call, this turn, exactly as confirmed.

7. WHEN SOMETHING IS BLOCKED - a check in step 3 fails, or a tool refuses:
   a. In a message, name the obstacle in plain words. That message ends your turn.
   b. In that same message, say which parts of the request you CAN still serve, and whether
      a different route exists that changes what they would get. Let them choose; do not
      choose for them, and do not stop at the obstacle.
   c. Then serve the parts that are allowed, each through steps 3 to 6.
   d. You may call transfer_to_human_agents ONLY when all three hold: you named the obstacle
      in an EARLIER turn, the customer has REPLIED to it, and no tool you have can serve any
      remaining part of their request. A blocked path is not a request outside your scope.
""".strip()


CONFIRMATION_FORMAT = """
Every message that asks the customer to confirm a write action is exactly these five lines,
in this order, then the question. Nothing else comes before them.

Action: <the one tool operation you are about to perform>
Reservation: <reservation id, or "new booking">
Details: <what changes - flights, cabin, passengers, bags - and the total amount>
Payment: <the exact payment method, and why that one>
Allowed because: <the condition in the policy that makes this action permitted>

Then ask: Shall I go ahead?

Example of the format:

Action: cancel a reservation
Reservation: HXY4Z1
Details: one way SFO to JFK on 2024-05-20, 2 passengers, refund $1,254.60
Payment: refunded to gift card gift_8452391, the method this reservation was paid with
Allowed because: this is a business class reservation, and no segment has been flown

Shall I go ahead?

If you cannot fill in "Allowed because:" with a condition actually written in the <policy>,
then the action is not permitted. Do not call the tool. Go to step 7 of the <procedure>.
""".strip()


STYLE = """
- Write in the language the customer writes in.
- Money in US format: a comma every three digits, a period only before cents. $1,250 and
  $1,250.75 - never $1.250.
""".strip()


FINAL_REMINDERS = """
Three rules that are easy to lose in the length of the policy above:
- One turn is one message OR one tool call.
- Before every write: the five lines of <confirmation_format>, and a "yes".
- transfer_to_human_agents only under the three conditions in step 7d. Being blocked is not
  one of them.
""".strip()


SYSTEM_PROMPT = """
<instructions>
{agent_instruction}
</instructions>
<policy>
{domain_policy}
</policy>
<procedure>
{procedure}
</procedure>
<confirmation_format>
{confirmation_format}
</confirmation_format>
<style>
{style}
</style>
{final_reminders}
""".strip()
```

E la property corrispondente (l'unica modifica di codice necessaria, oltre alle costanti):

```python
    @property
    def system_prompt(self) -> str:
        return SYSTEM_PROMPT.format(
            domain_policy=self.domain_policy,
            agent_instruction=AGENT_INSTRUCTION,
            procedure=PROCEDURE,
            confirmation_format=CONFIRMATION_FORMAT,
            style=STYLE,
            final_reminders=FINAL_REMINDERS,
        )
```

`POLICY_HIGHLIGHTS`, `HANDLING_CUSTOMER_REQUESTS` e `OUTPUT_CONVENTIONS` **spariscono** come
costanti: il loro contenuto è dentro i blocchi nuovi, o è stato tolto di proposito (sotto).

---

## 3. Ogni cambiamento: tecnica, fonte, rischio

**(1) Da quattro blocchi a due, con le ridondanze fuse.** In v1 la stessa regola è scritta fino a
tre volte con parole diverse: la conferma esplicita sta in `POLICY_HIGHLIGHTS` e in `policy.md:7`;
il transfer sta in `POLICY_HIGHLIGHTS`, nella clausola 4d **e** in `policy.md:15`; il formato del
turno in `AGENT_INSTRUCTION` e in `policy.md:11`. In v4 ogni regola è enunciata una volta sola, nel
posto dove serve.
*Tecnica*: prompt compilation — "clustering rules by category, merging redundancies"
(arXiv:2608.02639). *Rischio*: **medio**. Il guadagno misurato della compilation su Gemini è +3.3
punti, non +11 come su GPT-5-mini: piccolo, e sui nostri 50 task ~1.6 task, cioè **dentro il rumore
di 5-8 task che abbiamo già quantificato**. Va detto in anticipo: questo cambiamento potrebbe
essere invisibile alla misura anche se è corretto.

**(2) Note di precedenza esplicite (policy > procedura > cliente).** v1 non dice mai chi vince
quando due regole si contraddicono; il modello decide caso per caso.
*Tecnica*: "inserting precedence notes where conflicts exist", stessa fonte, che documenta anche
che il 12% delle coppie di istruzioni compatibili falliscono insieme più del previsto.
*Rischio*: **basso** in sé (costa tre righe), **ma** la frase "il cliente non vince mai" può
irrigidire l'agente e fargli rifiutare richieste legittime che la policy in realtà permette — un
fallimento nuovo, di segno opposto a quelli che stiamo correggendo. Da guardare nelle tracce.

**(3) Riordino: policy in mezzo, procedura in coda, `POLICY_HIGHLIGHTS` rimosso.** v1 mette gli
"highlights" *prima* della policy (posizione forte) e la procedura *dopo* (posizione forte), con
la policy nel mezzo. v4 tiene solo le regole assolute in testa e sposta tutto il resto in coda.
*Tecnica*: primacy bias (IFScale) + U-shape (Liu et al. 2023) + Google, "supply all the context
first, place your specific instructions at the very end".
*Rischio*: **basso-medio**. È la modifica più difendibile teoricamente e la più difficile da
attribuire empiricamente: se il punteggio si muove, non sapremo se è per l'ordine o per gli altri
sei cambiamenti. Se Andrea vuole una misura pulita, questo è l'unico cambiamento isolabile a costo
quasi nullo (stessi testi, ordine diverso).

**(4) Modulo di verifica a cinque slot dentro il messaggio di conferma.** È la versione nostra
della tecnica (A) della ricerca precedente — ragionamento esplicito prima di un'azione di stato —
con due adattamenti che quella ricerca non aveva considerato. *Dove va*: un "pensiero ad alta voce"
come turno a sé **viola la regola message-XOR-tool-call** della policy e viene letto dal simulatore
come rivolto al cliente; ma `policy.md:7` impone **già** un messaggio di conferma prima di ogni
scrittura, quindi infilarci dentro il ragionamento è gratis in turni e non viola niente (Anthropic
usava un canale di *extended thinking* separato, che via prompt non abbiamo: questo è il
sostituto). *Che forma ha*: non ragionamento libero ma **cinque slot da riempire**, per il
risultato di arXiv:2409.12183. La riga chiave è l'ultima — *se non riesci a riempire "Allowed
because:" con una condizione scritta nella policy, l'azione non è permessa* — che trasforma
`policy.md:113` e `:149` ("the API does not check these... the agent must make sure the rules
apply") da esortazione in prosa a **completamento di uno slot**, molto più nelle corde di un
modello piccolo.
*Rischio*: **il più alto dei sette.** Tre modi di fallire: (i) il modello riempie "Allowed
because:" con una motivazione plausibile ma inventata, e la checklist diventa **teatro** che
legittima l'azione sbagliata invece di fermarla — il fallimento più insidioso, perché produce
tracce che *sembrano* più rigorose ed esiti uguali o peggiori; (ii) il messaggio a cinque righe è
burocratico e il simulatore-utente può reagirci diversamente (chiusure premature, "sì" più
facili), spostando l'esito per una ragione che non c'entra con l'agente; (iii) più token, sempre.

**(5) Un esempio few-shot, uno solo, inventato.** Google raccomanda di includere sempre esempi con
formato identico. Uno solo, con dati **inventati** (`HXY4Z1`, `gift_8452391`) e non presi da
nessuno dei 50 task: non vogliamo scrivere il test dentro il prompt.
*Rischio*: **medio**. Google avverte che troppi esempi causano overfitting al formato; con uno solo
il rischio opposto è che il modello copi *il contenuto* dell'esempio. Da controllare nelle tracce:
se compare "Allowed because: this is a business class reservation" su prenotazioni che business non
sono, l'esempio sta facendo danno e va reso più neutro o rimosso.

**(6) `policy.md` tradotta in procedura numerata di 7 passi.** v1 aveva 4 clausole di prosa fitta;
v4 ha 7 passi dove ognuno corrisponde a un'azione o a un output. *Tecnica*: OpenAI — "use existing
policy documents to create LLM-friendly routines", "every step corresponds to a specific action or
output", "capture edge cases with conditional branches".
*Rischio*: **basso-medio**, ed è la rigidità: non tutte le conversazioni cominciano al passo 1 (il
cliente risponde a metà, o cambia idea), e un modello piccolo istruito a seguire i passi in ordine
può ripartire da capo e bruciare turni. Il passo 2 ("leggi sempre lo stato prima di giudicare")
**aumenta le letture**: è il cambiamento che più probabilmente allunga le traiettorie.

**(7) Tre sottrazioni.** (a) Il bullet sulla compensazione sparisce dagli highlights: resta in
`policy.md:154-167`, e soprattutto **è coperto dallo slot "Allowed because:"** — offrire un
certificato è una scrittura, quindi il modello deve nominare la condizione (silver/gold,
assicurazione, business) per poterla fare. (b) Il bullet "se un tool torna errore, rileggi prima di
riprovare" sparisce: c'è già `TOOL_ERROR_STREAK_LIMIT = 3` nel **codice**, che è più affidabile
di una regola nel prompt, e il passo 7 copre il caso. (c) La clausola v1 n.1 (richieste multiple)
diventa il passo 1 invece di una clausola a sé.
*Rischio*: **la (a) è quella su cui sono meno sicuro.** Il bullet sulla compensazione era uno dei
quattro scelti in S3 come "i più facili da sbagliare", e toglierlo scommette che lo slot
"Allowed because:" faccia lo stesso lavoro. Se Andrea preferisce non correre questo rischio, la
mossa conservativa è rimettere quella sola riga in `FINAL_REMINDERS` (che diventa di quattro
righe) — costa un vincolo e annulla un po' del guadagno di compressione, ma è reversibile.

**Bilancio quantitativo, con la cautela che merita**: i vincoli nostri passano da ~21 (5 highlights
+ 11 sotto-passi di handling + 2 output + 3 di instruction) a ~15 indipendenti (5 instruction +
7 passi + 2 style + 1 regola di formato; i 5 slot sono *un* vincolo, non cinque; i 3 reminder sono
ripetizioni volute, non regole nuove). È una riduzione di circa il 30%, **ma "contare i vincoli"
non è una misura rigorosa** — nessuna delle fonti dà un metodo per contarli su prompt reali, e la
mia conta è un giudizio. La direzione è difendibile; il numero no.

---

## 4. `AGENT_TURN_LIMIT = 30`: **non alzarlo per necessità, alzarlo per igiene**

Misurato, non indovinato, sui risultati già in `tau2-bench/data/simulations/`:

- Ultimo giro completo del custom agent (50 simulazioni, `s9_custom_agent_t*`): **massimo 19 turni
  di assistente**, mediana 9.5, media 8.1. **Zero** simulazioni sopra 19.
- Su **tutte** le 299 simulazioni del custom agent nel repo: massimo 32 (il caso in cui il tetto
  ha morso: 30 turni + tool call di transfer + handoff), e solo **2 su 299 arrivano a 28+** (0.7%).

Il tetto oggi **non è vincolante** e non causa nessun fallimento noto. La tecnica (C) della ricerca
precedente va quindi riportata con la sua premessa vera: Anthropic ha alzato 30→100 perché
l'*extended thinking* allunga le traiettorie, non perché 30 fosse stretto — e infatti notavano che
la maggior parte restava sotto 30.

**Raccomandazione**: alzarlo comunque a **50**, per due motivi che non sono "ci serve". (1) Il
passo 2 e il passo 7 della procedura aggiungono turni per costruzione: con 11 turni di margine
attuale, un +30% di lunghezza media porta la coda vicino al tetto. (2) Un fallimento per tetto è un
**artefatto di misura** travestito da errore di policy, e nel confronto v1-vs-v4 non vogliamo che
un task cambi esito perché la v4 è più prolissa. 50 resta molto sotto il `DEFAULT_MAX_STEPS = 200`
del framework, quindi la protezione contro i loop infiniti rimane.

Attenzione: alzarlo **aggiunge una variabile** fra v1 e v4. Se lo si alza, va alzato **anche per il
baseline di confronto**, o il confronto non è pulito.

---

## 5. Rischi e incognite nuovi, che v1/v2/v3 non avevano

1. **Il rumore resta più grande dell'effetto atteso.** Il guadagno documentato della prompt
   compilation su Gemini è **+3.3 punti percentuali**: su 50 task, ~1.6 task. La varianza già
   misurata su questo progetto è **5-8 task su 36 fra due esecuzioni identiche**. Cioè: **anche se
   la v4 funzionasse esattamente come promette la fonte, non potremmo distinguerlo dal rumore con
   una sola esecuzione.** È la cosa più importante di tutto il documento. Per avere una risposta e
   non un aneddoto servono più ripetizioni per condizione (pass^k, come nel paper τ-bench), non un
   prompt migliore. Se il budget non lo consente, va scritto nel report che la v4 è una **scelta di
   metodo motivata dalla letteratura, non un risultato misurato** — che è comunque presentabile.

2. **La checklist può diventare teatro.** Il rischio qualitativamente nuovo. Un modello piccolo
   istruito a scrivere "Allowed because: <condizione>" produrrà *sempre* una stringa lì dentro; se
   la inventa, otteniamo tracce che leggono come rigorose e azioni sbagliate come prima — peggio di
   v1, perché diagnosticare guardando le tracce diventa più difficile. **Controllo suggerito**: su
   un campione, verificare che ogni "Allowed because:" corrisponda a una riga vera di `policy.md`.
   È il tipo di controllo che il giudice già costruito in S7/S8 può fare.

3. **Cambiamo il testo che il simulatore-utente legge.** v1/v2/v3 cambiavano il ragionamento
   dell'agente; v4 cambia **la forma dei messaggi al cliente**. Il simulatore è un LLM e può
   rispondere diversamente a un messaggio burocratico: chiudere prima, dire "sì" più o meno
   facilmente. Un cambio di esito potrebbe venire da lì e non dalla competenza dell'agente — una
   confusione che le versioni precedenti non avevano.

4. **Costo.** Il system prompt è di poco più corto di v1 (le sottrazioni compensano l'esempio), ma
   i **messaggi generati** e le **traiettorie** sono più lunghi. Stima grossolana: +15-30% di token
   di output per run. Con Flash Lite è poco in assoluto, ma con la quota RPD/RPM già incontrata nel
   progetto può significare più run spezzati in shard.

5. **Sette cambiamenti insieme = nessuna attribuzione.** v2/v3 hanno fallito anche perché
   isolavano una clausola alla volta con un segnale troppo piccolo; la v4 fa il contrario. È la
   scelta giusta date le fonti (la compilation *è* un intervento globale, non scomponibile), ma il
   prezzo è che **se la v4 va peggio non sapremo quale dei sette pezzi ha rotto**. Da dichiarare,
   non nascondere: la v4 è "un impianto alternativo da confrontare con v1", non "v1 più sette
   miglioramenti".

6. **Rischio residuo che nessuna fonte copre**: `policy.md` resta ~40 regole che nessuna nostra
   compilazione può accorciare (non possiamo modificarlo). Anche con i nostri vincoli da 21 a 15,
   il totale resta intorno a 55 — **ben oltre le soglie di collasso (15-20) di entrambi i paper**.
   La v4 sposta il sistema da "molto oltre soglia" a "un po' meno oltre soglia": non lo porta
   sotto. È probabilmente la ragione più profonda per cui il metodo delle famiglie si è esaurito, e
   la v4 la attenua senza risolverla.

---

## 6. Addendum — i due checkpoint di rilettura (proposta di Andrea)

Aggiunti a `PROCEDURE` (sezione 2): una riga morbida alla fine del passo 1 (prima di ragionare
sull'azione) e una alla fine del passo 3 (dopo aver deciso l'idoneità, prima di procedere al
pagamento e alla conferma). Non nuove regole numerate: frasi dentro i passi che già esistevano,
per non aumentare il conteggio dei vincoli che la sezione 3 discute.

**Correzione tecnica alla premessa**, perché cambia cosa ci si deve aspettare: la policy intera
viene già reinviata al modello a ogni singolo turno (`llm_agent.py:127`, `messages =
state.system_messages + state.messages` — così funziona qualunque API di chat a completamento).
Non c'è un file da rileggere e nessuna informazione viene recuperata che non fosse già in
ingresso. Il meccanismo per cui questi due checkpoint dovrebbero funzionare non è l'accesso ai
dati, è dove si concentra la generazione: forzare il modello a riattraversare la regola pertinente
subito prima di decidere sfrutta lo stesso effetto di recency/posizione già citato per il riordino
dei blocchi (Liu et al. 2023, "Lost in the middle") - non un risparmio su token di lettura, che
sono identici con o senza questi checkpoint. Il costo aggiuntivo è tutto in output (poche righe in
più per turno), non in input.

I due checkpoint corrispondono a due meccanismi distinti, entrambi con un referente diretto nella
ricerca già fatta:
- il primo (dopo il passo 1) è **priming**: tenere il modello concentrato sulle regole pertinenti
  proprio mentre affronta il ragionamento a breve termine che segue;
- il secondo (dopo il passo 3) è **auto-verifica**: dare al modello l'occasione di accorgersi da
  solo di un ragionamento approssimativo, la versione "a costo zero" - un solo modello invece di
  due - della tecnica del "tool-mentor" già scartata come infeasibile nella ricerca sulle
  submission esterne.

**Perché sono consigli e non regole** (scelta di Andrea, corretta): un'istruzione morbida non
entra nel conteggio dei vincoli che il modello deve tracciare e può violare in silenzio
(Instruction Stacking Collapse). Il rischio-teatro della sezione 5 vale anche qui, in una forma
più lieve: il modello potrebbe scrivere di aver "riguardato" la policy senza che la generazione
successiva ne risenta davvero. Non c'è modo di verificarlo dal testo dell'output con la stessa
precisione con cui si verifica lo slot "Allowed because:" (quello ha una riga di policy concreta
da controllare; un "ripasso" generico no) - un limite dichiarato, non risolto.

---

## 7. Come giudicheremo se il costo in più vale il risultato — fissato PRIMA di girare i 50 task

La sezione 5 già prevede che v4 costerà di più (più righe per turno, più letture al passo 2, e ora
anche i due checkpoint). Non basta guardare il solo pass rate: un agente che costa il doppio per
guadagnare due task su cinquanta non è ovviamente "meglio". Due misure, entrambe calcolabili dal
costo per simulazione che già registriamo in ogni `results.json` (`agent_cost + user_cost`), senza
bisogno di nulla di nuovo:

**Costo per successo** = costo totale del giro / numero di task riusciti. Si confronta
direttamente fra baseline, v1 e v4: se il costo-per-successo di v4 è **più basso** di quello di v1
o del baseline, il costo maggiore per simulazione è più che compensato dal tasso di successo più
alto — l'investimento nell'harness si ripaga. Se è più alto, il guadagno di pass rate (ammesso che
ci sia) non giustifica la spesa aggiuntiva.

**Costo incrementale per punto guadagnato** = (costo/sim di v4 − costo/sim di v1) / (pass rate di
v4 − pass rate di v1). Risponde alla domanda "quanti centesimi in più costa comprare un punto
percentuale di affidabilità in più", nello stesso modo in cui l'economia sanitaria misura il costo
incrementale di un trattamento più efficace ma più caro (ICER). Non ha una soglia "giusta"
universale - va giudicata insieme alla dimensione dell'effetto (sezione 5, punto 1: un guadagno di
+3.3 punti attesi dalla letteratura è già sotto il rumore misurato) - ma è il numero che permette
di dire "questo miglioramento, se reale, costa X e vale la pena" invece di ignorare il costo.

Se il pass rate di v4 non supera quello di v1 (esito plausibile, sezione 5), il costo-per-successo
di v4 sarà quasi certamente peggiore per costruzione, e non serve calcolare l'incrementale: si
riporta comunque il numero, perché "quanto abbiamo pagato per non guadagnare nulla" è a sua volta
un risultato onesto per il report.
