# Premortem: il "bug" dell'hash ordine-sensibile in τ²-bench

Esercizio di avvocato del diavolo. Obiettivo: **falsificare** l'affermazione, non confermarla.
Tutto verificato in locale su `tau2-bench` @ `a2c0247` (= `main` upstream al 2026-08-18, v1.0.1),
senza consumare quota API: replay deterministico dell'ambiente airline.

## 1. Verdetto

**BUG CONFERMATO.** Non sono riuscito a smontarlo, e ci ho provato su cinque fronti.

## 2. Il miglior argomento PER la tesi "non è un bug"

Il tentativo più serio non è il codice: è la **semantica del dominio**. Il campo non si chiama
`payment_methods` nel DB, si chiama `payment_history` (`src/tau2/domains/airline/data_model.py:235`,
`List[Payment]`). Un *history* è un libro mastro append-only, non un insieme: `book_reservation`
scrive le voci iniziali (`tools.py:237`), `update_reservation_flights` ne appende
(`tools.py:583`, `tools.py:683`), `cancel_reservation` appende i rimborsi come importi negativi
(`tools.py:356-363`). Per un ledger l'ordine **è** semantica (cronologia), e un hash
ordine-sensibile è la scelta *corretta*: ordinare il ledger prima di confrontarlo distruggerebbe
la capacità di distinguere una sequenza di rimborsi sbagliata. Sotto questa lettura l'agente non
ha prodotto "lo stesso stato in ordine diverso": ha prodotto un ledger diverso, e il fatto che i
totali coincidano è irrilevante quanto lo è per una partita doppia.

A rinforzo: nel dominio retail l'ordine di `payment_history` **è davvero portante** —
`src/tau2/domains/retail/tools.py:577,582,587,604,616,699` indicizzano `payment_history[0]`
assumendo che l'elemento 0 sia il pagamento originale, e da lì decidono dove va il rimborso.

Argomento secondario che ho considerato e scartato subito: l'ordine "canonico" del profilo utente.
Falso — in `data/tau2/domains/airline/db.json` l'utente `mohamed_silva_9265` elenca
`gift_card_8020792` **prima** di `certificate_3765853`, mentre la gold action mette il certificato
per primo. La gold non segue l'ordine del profilo, quindi nessun ordine canonico è codificato.
Terzo argomento scartato: la `description.purpose` del task 14 dice "use **first** both gift cards
..., the $500 certificate", cioè l'ordine opposto a quello della sua stessa gold action. La prosa
del task si contraddice con i propri dati: nessuna regola d'ordine è desumibile da lì.

## 3. Perché quell'argomento non regge

**(a) Le voci iniziali non hanno cronologia.** Il ledger-argument vale per gli *append nel tempo*.
Le voci scritte da `book_reservation` sono tutte prodotte in una singola transazione atomica, con
un unico `created_at` fisso (`tools.py:100-102` ritorna la costante `"2024-05-15T15:00:00"`), e
`Payment` (`data_model.py:44`) ha solo `payment_id` e `amount`: nessun timestamp, nessun numero di
sequenza. Non c'è nessuna cronologia da preservare *fra* quelle voci.

**(b) L'engine stesso dimostra che l'ordine non ha effetti.** `book_reservation` valida *tutti* i
metodi prima di mutare qualsiasi cosa (`tools.py:284-301`) e solo dopo deduce
(`tools.py:303-311`). Con `payment_id` distinti il risultato è provabilmente indipendente
dall'ordine. Verificato empiricamente, non dedotto: replay locale gold-vs-agente,

- task 14 → `db_match: False`, ma `DeepDiff(gold, agent)` restituisce **solo** i due elementi
  `payment_history[1]`/`[2]` scambiati, e `DeepDiff(..., ignore_order=True)` restituisce `{}`;
- task 23 → identico, `ignore_order=True` restituisce `{}`;
- un hash con liste canonicalizzate combacia in entrambi i casi.

Quindi i due stati finali sono strutturalmente identici a meno dell'ordine. Non c'è nessun altro
campo, side-effect, timestamp o ID generato che differisca (`user_db_match` è `True` in entrambi).

**(c) Anche la lettura "priorità di addebito" non salva.** L'istruzione utente è "certificates as
much as possible, **then** gift cards, then master card". Gold e agente rispettano entrambi quella
gerarchia: certificato, poi le due gift card, poi la carta. Gli unici due elementi scambiati sono
**due gift card dello stesso tier**, entrambe **esaurite per intero** (198 = saldo pieno di
`gift_card_8020792`, 129 = saldo pieno di `gift_card_6136092`, da `db.json`). Nessuna regola di
priorità può distinguerle: l'ordine fra le due porta zero informazione.

**(d) Il contratto documentato dal progetto dice l'opposto.** `docs/evaluation.md:52`:
il check `DB` passa perché *"Any agent trajectory that produces an equivalent end state passes."*
Uno stato con `DeepDiff(ignore_order=True) == {}` è un equivalent end state per qualunque
definizione ragionevole.

**(e) Il progetto ha già trattato questa identica classe come bug, due volte.**
`CHANGELOG.md:63-65` (issue **#397**): *"DB hashes no longer depend on int-vs-float argument
spelling ... it removes a latent source of spurious failures"*. `CHANGELOG.md:56-62` (issue
**#329**): letture extra dell'agente finivano nell'hash e azzeravano il reward — corretto.
E la suite di test **asserisce esplicitamente** l'invariante che qui viene violato: input
dell'agente semanticamente equivalenti ma scritti diversamente devono produrre lo stesso
`get_db_hash()` — `tests/test_domains/test_banking_knowledge/test_tools_knowledge.py:3480`,
`:3493`, `:3508`, `:3531`, `:3620`. L'ordine di una lista è esattamente la stessa classe di
variazione incidentale dell'input dell'agente della "spelling" int-vs-float.

**(f) Nel dominio airline l'ordine non è mai portante.** `payment_history` compare solo a
`tools.py:237` (scrittura), `:356-363` (itera *tutte* le voci per generare rimborsi — effetto
indipendente dall'ordine), `:583`, `:683` (append). Nessuna indicizzazione posizionale, a
differenza di retail. L'obiezione (a)-(f) non scalfisce il fatto che in retail l'ordine conta:
scalfisce solo l'idea che *questa* sia una scelta deliberata in airline.

**(g) Non è già stato risolto upstream.** Il nostro clone è esattamente su `main` HEAD
(`a2c0247`, v1.0.1). Nessuna issue upstream copre questo caso.

## 4. Accuratezza dell'esempio del task 14 — e correzioni da fare prima di pubblicare

L'esempio **è accurato**. Verificato in `data/simulations/s6_custom_agent_t14/results.json`: la
chiamata `book_reservation` dell'agente è identica alla gold (stessi voli nello stesso ordine,
stessi passeggeri nello stesso ordine, stessi importi) tranne le due gift card scambiate;
`reward_breakdown = {"DB": 0.0, "COMMUNICATE": 1.0}`; nessun'altra write call nella traiettoria
(solo `get_user_details`, `get_reservation_details`, 3 search, `cancel_reservation`,
`book_reservation`). Task 23 idem: tre `book_reservation` che combaciano con la gold, lo stesso
scambio di gift card nella prima.

Però nella bozza `scratch_issue_taubench.md` ci sono **quattro cose da sistemare** prima di
mandarla a nome tuo:

1. **Path sbagliato (errore fattuale, riga 26).** Scrive `data/tasks/airline_tasks.json`. Il file
   vero è `data/tau2/domains/airline/tasks.json`. In una issue pubblica su un repo di terzi un
   path inventato è la cosa che fa scartare il report per primo.
2. **Affermazione troppo forte (righe 49-51).** "`COMMUNICATE` ... confirming the agent's booking
   was substantively correct" non regge: `COMMUNICATE` fa solo substring match su `["327", "1000",
   "1786"]`, non certifica la prenotazione. La prova forte è un'altra ed è più solida: sostituiscila
   con il `DeepDiff(ignore_order=True) == {}` fra i due stati finali.
3. **Il fix proposto è troppo largo (righe 54-57).** "use an order-insensitive structural diff
   (`DeepDiff(ignore_order=True)`) for the DB-match check" applicato all'intero DB renderebbe il
   confronto cieco anche dove l'ordine è portante — retail indicizza `payment_history[0]`
   (`src/tau2/domains/retail/tools.py:577-616,699`). Va detto esplicitamente, sia per onestà sia
   perché anticipa la prima obiezione di un manutentore.
4. **Prior art da citare.** Esiste già una issue aperta e senza risposta,
   [#325](https://github.com/sierra-research/tau2-bench/issues/325) (19 mag 2026), "Retail task 100
   / `modify_pending_order_items` may be order-sensitive in evaluation": stessa classe, dominio
   diverso, e il reporter non aveva individuato la causa radice (elencava tre ipotesi). Citarla
   conviene: evita l'accusa di duplicato, e il tuo contributo diventa chiaro — la causa radice in
   `get_dict_hash` e la prova che gli stati sono equivalenti. Nota che #325 nasce da un audit
   esterno (arXiv 2605.10448): vale la pena controllare se quel paper copre già il caso airline.

Aggiunta consigliata (rafforza il report, non lo indebolisce): la stessa ordine-sensibilità
colpisce anche `ActionEvaluator`, perché `Action.compare_with_tool_call` confronta con
`tool_args == action_args` (`src/tau2/data_model/tasks.py:195`). Nel run del task 14 infatti
`action_match` è `false` per `14_1`. In airline non incide sul reward (`ACTION` non è nel
`reward_basis`), ma nei task banking_knowledge che usano `ACTION` sì.
