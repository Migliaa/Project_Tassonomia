# Tecniche da submission esterne (leaderboard τ²-bench) — ricerca per la v4

Ricerca sulle submission reali in `tau2-bench/web/leaderboard/public/submissions/` (73 cartelle,
incluse le 2 di esempio), sui paper/repo collegati, e sul blog di Sierra. Solo ricerca: nessun
file dell'agente toccato.

## Premessa sui risultati

Il pool di submission `submission_type: "custom"` su dominio testuale **airline/retail** è
piccolo (5 su 73), e nessuna è un caso pulito di "solo prompt, stesso modello, dominio testuale
airline/retail" — la maggior parte sono voce (audio-native) o richiedono training/infrastruttura
multi-modello. La fonte più utile per tecniche di *puro prompting* non è arrivata dalle
submission `custom`, ma dalle note delle submission **Anthropic** (non marcate "custom" nello
schema, ma che nel testo descrivono esplicitamente modifiche al prompt) e dal blog stesso di
Sierra. Lo riporto con onestà: niente è stato forzato per sembrare più ricco di quello che è.

## 1. Submission rilevanti trovate

| Submission | Org | Dominio (pass_1) | Tecnica descritta | Link |
|---|---|---|---|---|
| `claude-opus-4-1_anthropic_2025-01-15` | Anthropic | airline 56.0, retail 82.4 | Addendum al prompt di policy Airline/Retail: chiede al modello di scrivere i propri ragionamenti (extended thinking) distinti dal thinking normale, durante la traiettoria multi-turno; max step 30→100 | interno (submission.json) |
| `claude-opus-4_anthropic_2025-05-22` | Anthropic | airline 59.6, retail 81.4 | Stessa tecnica di cui sopra | interno |
| `claude-sonnet-4_anthropic_2025-05-22` | Anthropic | airline 60.0, retail 80.5 | Stessa tecnica di cui sopra | interno |
| `claude-sonnet-4-5_anthropic_2025-10-02` | Anthropic | airline 70.0, telecom 98.0 | Addendum al prompt di policy Airline/Telecom mirato ai *failure mode noti* del prompt "vanilla"; addendum separato al prompt Utente di Telecom per evitare che l'utente chiuda la conversazione in modo scorretto | interno |
| `gemini-3-pro_google_2025-11-18` | Google | airline 73.0, retail 85.3 | "standard sierra framework con un aggiustamento del prompt per fornire istruzioni rilevanti per ciascun ambiente" (vago, ma conferma che ogni lab frontier applica un addendum di prompt per dominio) | interno |
| `grok-voice-think-fast-1-0-tool-mentor_pickle_2026-07-07` | Pickle (indip.) | airline 70.0, retail 76.3 (voce) | "Tool-boundary mentor": una seconda LLM (Gemini 3.5 Flash) rivede le tool call dell'agente prima dell'esecuzione — gate pre-esecuzione su azioni di stato/escalation, note aggiunte ai risultati di lettura, intercetta gli stop indebiti | fork citato, non verificato in dettaglio |
| `pine-voice-preview-user-sim-gpt-5-5_pineai_2026-08-17` | Pine AI | airline 80.0, retail 85.1 (voce) | Sistema a due agenti (voce + agente di background che emette le tool call) con un messaggio di scaffold che definisce ruoli e coordinamento tra i due | 19pine.ai |
| `toolorchestra_nvidia_2025-12-02` | NVIDIA | airline 56.0, retail 84.2 | Orchestratore **addestrato** (8B, RL) che sceglie tra modello forte/debole per task | arxiv.org/abs/2511.21689, github.com/NVLabs/ToolOrchestra — **richiede training, escluso** |
| `raft-30b-a3b_neu_2026-04-29` | NEU (indip.) | retail 82.5 | Qwen3-30B **fine-tuned** su dati sintetici di dominio retail | **richiede training, escluso** |
| `distyl-buttonagent_distyl_2026-03-25` | Distyl AI | solo banking_knowledge 31.2 | Pipeline di retrieval custom (Mixedbread) per documenti di policy — dominio diverso (knowledge/RAG), non tool-calling conversazionale | interno |

Le submission `gpt-realtime-2_openai_2026-06-24` (custom, airline 66.0) sono marcate "custom" solo
perché cambiano il modello del simulatore utente, non lo scaffold dell'agente — escluse perché
irrilevanti alla domanda.

## 2. Tecniche concrete estratte

### A. Ragionamento esplicito scritto nel prompt di policy ("scratchpad" prima del tool call)
**Fonte**: submission Anthropic (Opus 4/4.1, Sonnet 4), note testuali sopra.
Il "prompt addendum" non è generico: dice esplicitamente al modello di *scrivere i propri
pensieri* come step distinto, durante la traiettoria a più turni, prima di agire — in pratica un
CoT strutturato dentro la policy, non lasciato all'improvvisazione del modello.
**Fattibilità per un singolo sviluppatore**: **alta**. Non richiede l'API di extended thinking di
Claude — l'idea di fondo (istruire il modello a produrre un breve ragionamento esplicito, in un
formato fisso, prima di ogni tool call che modifica stato) è implementabile con qualunque modello
via system prompt, incluso uno senza reasoning nativo (rilevante perché il nostro agente non usa
Claude). Il costo è più token per turno, non più infrastruttura.

### B. Colpire i *failure mode noti* con un addendum mirato, non un rewrite generico
**Fonte**: Claude Sonnet 4.5 (Anthropic), note: "prompt addendum... instructing Claude to better
target its known failure modes when using the vanilla prompt."
Questo è essenzialmente il metodo già seguito nel progetto (diagnosi in famiglie di fallimento →
fix di prompt mirato), applicato qui da un lab frontier sullo stesso benchmark. **Fattibilità**:
è già la nostra strategia — questa submission serve più da conferma esterna che da tecnica nuova.
Nota utile: hanno applicato un addendum *anche al prompt dell'utente simulato* (dominio Telecom,
per evitare chiusure premature della conversazione) — un'idea che nel nostro caso non si applica
(non controlliamo lo user simulator in produzione) ma è un promemoria che un fallimento può
nascere anche da come l'agente reagisce a comportamenti ambigui dell'utente, non solo da policy.

### C. Aumentare il budget di step, non solo il prompt
**Fonte**: Anthropic (Opus 4/4.1, Sonnet 4), note: max step aumentato da 30 a 100 per accomodare
il ragionamento aggiuntivo (la maggior parte delle traiettorie restava comunque sotto i 30 step).
**Fattibilità**: alta, è una leva del harness (`tau2 run`), non del modello — banale da provare,
zero rischio, va verificato che il nostro harness non abbia già un cap più basso che silenziosamente
tronca i trial più lunghi generati da un prompt "pensa più a lungo".

### D. Verifica di una seconda "voce" prima di eseguire azioni di stato
**Fonte**: submission "tool-mentor" (Pickle, indipendente) — una seconda LLM che approva/blocca
le tool call di stato prima dell'esecuzione, aggiunge note ai risultati di lettura, e intercetta
gli hand-off indebiti.
**Fattibilità**: **bassa nella forma originale** — richiede una seconda chiamata a un secondo
modello per turno, cioè infrastruttura aggiuntiva, esplicitamente fuori scope per la v4. Il
principio però è recuperabile *dentro un solo prompt*: si può chiedere allo stesso modello di
eseguire un check esplicito (checklist di pre-condizioni: stato del prenotazione, conferma
esplicita dell'utente, ecc.) come step di testo separato immediatamente prima di ogni tool call
che muta stato — una versione "povera" a costo zero d'infrastruttura, meno robusta di un vero
secondo giudice ma coerente con il vincolo "solo prompt".

### E. Separazione di ruoli tramite scaffold nel prompt
**Fonte**: Pine AI (voce + agente di tool-calling con context condiviso, definiti da un
"messaggio di scaffold" che assegna identità e responsabilità).
**Fattibilità**: **parziale**. L'architettura a due agenti reali è fuori scope (due modelli). Ma
l'idea di un blocco di scaffold che assegna esplicitamente "ruoli" o "fasi" interni a un unico
prompt (es. "fase di raccolta informazioni" vs "fase di esecuzione") è applicabile a costo zero,
e in parte già presente implicitamente in molti prompt di agenti ben scritti.

### F. Diagnosi autorevole di Sierra sulle cause di fallimento
**Fonte**: blog Sierra, post originale τ-bench (sierra.ai/blog/benchmarking-ai-agents): "key
challenges lie around improving their ability to follow rules consistently, plan over long
horizons and focus on the right pieces of information"; e specificamente "function calling agents
are not great at following rules provided in the policy documents." Il post non fornisce
raccomandazioni prescrittive di prompting — resta diagnostico, non prescrittivo — ma è la
conferma più autorevole possibile (viene da chi ha costruito il benchmark) che le tre leve giuste
sono: aderenza alla policy, pianificazione su orizzonte lungo, selezione dell'informazione
rilevante. Nessun post del blog Sierra (controllati: τ-bench originale, τ²-bench, τ-voice,
τ-knowledge, τ³-bench task fixes) contiene una guida pratica "come scrivere un prompt migliore".

### G. Fonti scartate per infeasibilità (training/infrastruttura)
- **ToolOrchestra (NVIDIA)**: orchestratore 8B addestrato con RL multi-obiettivo (esito,
  efficienza, preferenza utente) per instradare tra modelli forte/debole — richiede training e
  routing multi-modello. Confermato leggendo l'abstract via WebFetch: nessuna componente di
  prompting "staccabile" dal training.
- **RAFT-30B-A3B (NEU)**: fine-tuning di Qwen3-30B su dati sintetici di dominio retail —
  training, escluso.
- **"Prompting Policies for Multi-step Reasoning..." (arXiv 2605.14443)**: valutato anche su
  tau-bench (74%→91% su task di tool-use), ma il metodo addestra un modello "prompter" separato
  via RL con un buffer di esperienza contrastivo — non è "solo prompt di sistema". L'idea di fondo
  (raffinare iterativamente il prompt sulla base di critiche testuali sui fallimenti passati) è
  concettualmente identica al nostro processo manuale di diagnosi-a-famiglie → fix di prompt, ma
  qui automatizzato con infrastruttura di training: nessuna tecnica nuova da rubare, solo
  conferma indiretta che l'approccio manuale del progetto è nella direzione giusta.
- **Distyl ButtonAgent**: retrieval custom su documenti — dominio banking_knowledge (RAG), non
  applicabile a un agente di policy-following/tool-calling su airline.
- **Post indipendente (Medium, S. Dutta)**: non leggibile direttamente (403 sulla pagina), solo
  uno snippet di ricerca disponibile — riferisce risultati che sembrano derivare dal paper
  originale tau-bench (function calling nativo > ReAct/Act; few-shot aiuta di più su retail che
  su airline, dove la policy è troppo complessa perché esempi da altri task trasferiscano bene).
  Riportato solo come indizio a bassa confidenza, **non verificato alla fonte primaria** — non
  affidarsi a questo dato senza controllo incrociato.

## 3. Raccomandazione per la v4

Tra tutto il materiale trovato, solo poche tecniche sono realmente "solo prompt, stesso modello,
nessuna infrastruttura" e coerenti con l'approccio già in uso nel progetto:

1. **Scratchpad di ragionamento esplicito prima di ogni tool call di stato** (da tecnica A).
   È l'unica tecnica con una fonte diretta e un meccanismo chiaro: aggiungere alla policy
   dell'agente un'istruzione che obbliga a scrivere un breve ragionamento testuale (non nascosto,
   nel canale normale se il modello non supporta thinking nativo) immediatamente prima di azioni
   che mutano stato (booking, refund, cambio prenotazione). Economico da provare, facilmente
   isolabile in un A/B, e il tipo di leva che il nostro S4 (diagnosi a famiglie) già suggerisce
   essere debole nell'agente attuale.

2. **Checklist di pre-condizioni come surrogato "a costo zero" del tool-mentor** (da tecnica D).
   Non replicare il secondo modello, ma imitarne l'effetto: nella policy, prima di ogni tool call
   irreversibile, richiedere esplicitamente all'agente di elencare le pre-condizioni verificate
   (identità utente confermata, stato attuale della prenotazione, conferma esplicita dell'utente)
   come testo prima della chiamata. Stesso principio della submission Pickle, zero costo
   aggiuntivo di infrastruttura.

3. **Alzare il budget di step in parallelo a un prompt più "pensante"** (da tecnica C). Se si
   applica la tecnica 1, verificare che il numero massimo di step del nostro harness non tronchi
   prematuramente le traiettorie più lunghe generate da un ragionamento esplicito — copiando
   l'osservazione Anthropic (30→100, quasi mai raggiunto), alzare il cap è a rischio zero e
   previene un artefatto di misura (fallimento per timeout invece che per errore di policy).

4. **Trattare la diagnosi di Sierra come check-list di validazione, non solo come tecnica da
   copiare** (da tecnica F). Prima di scrivere l'addendum di prompt per la v4, verificare
   esplicitamente che copra le tre leve che Sierra stessa nomina come le cause dei fallimenti
   nel benchmark — aderenza alla policy, pianificazione su orizzonte lungo, selezione
   dell'informazione rilevante — usandole come lista di controllo per capire se le famiglie di
   fallimento già diagnosticate nel nostro S4 coprono davvero tutte e tre, o se ne manca una.

Esplicitamente **non** raccomandato: routing multi-modello (ToolOrchestra), fine-tuning
(RAFT-30B-A3B), o un vero secondo modello "mentore" (Pickle) — tutte tecniche che richiedono
infrastruttura o training fuori scope per un system prompt su un singolo modello.
