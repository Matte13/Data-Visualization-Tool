# Tracciato Excel supportato

Data Visualization Tool importa progetti diversi con lo **stesso tracciato**, non qualsiasi file Excel. I contenuti delle righe, anni, domini, owner, entity e gruppi possono cambiare. I fogli obbligatori sono `LE_List` e `Remediations`; `OT` è facoltativo. Gli altri fogli non vengono interpretati come sorgenti aggiuntive di remediation.

## LE_List

Riga 1: colonna A `Country/Legal Entities`, colonna B `Backup`. Dalla colonna C sono presenti i gruppi usati dalle formule dei budget Local. Sono accettati due formati.

### Intestazioni con significato organizzativo, dalla versione 1.2.0

Le tre intestazioni sono `OT`, `local business` e `local complete`. Maiuscole, spazi ai bordi e spazi non interrompibili vengono normalizzati. È ammesso un numero finale separato da uno spazio, ad esempio `Local Complete 3`; se presente deve coincidere con il numero delle X. Se si usa una delle tre intestazioni, devono essere presenti tutte e tre.

Le X sulle righe che hanno un nome in colonna A definiscono i membri. Le categorie rappresentate dal tool sono:

| Categoria | Regola sulle X |
| --- | --- |
| Local Complete + OT | X in `local complete` e in `OT` |
| Local Complete senza OT | X in `local complete`, senza X in `OT` |
| Local Business | X in `local business` |

Le entità OT devono essere comprese nelle Complete; Complete e Business devono essere disgiunte. I conteggi derivano dal file e possono variare fra progetti. Un gruppo semantico senza membri è ammesso e non genera entità fittizie.

Sono ammessi anche altri gruppi numerici o descrittivi, per esempio per backup o attività normative. Essi descrivono l'applicabilità economica delle singole formule e possono attraversare le categorie organizzative: un costo nella colonna J può quindi contribuire al budget di una legal entity classificata Business.

### Formato numerico precedente

Rimangono supportati interi positivi oppure etichette che terminano con quell'intero, ad esempio `3` o `Ambito operativo 3`. Il numero di X deve coincidere con il numero del gruppo. Le formule e le attribuzioni vengono lette come prima. Dalla 1.2.1 è riconosciuto anche il profilo originale approvato: precisamente i gruppi C=6, D=8, E=13, F=5 e G=9 (oppure `Europa AI ACT 9`), con cardinalità X coerenti, 21 entità, OT comprese nelle Complete e Complete/Business disgiunte ed esaustive. Per questo profilo C identifica OT, D Business ed E Complete: risultano 6 Complete con OT, 7 senza OT e 8 Business. Il riconoscimento non usa i nomi delle country.

Gli altri formati numerici validi restano senza classificazione; il tool non generalizza il significato di un moltiplicatore al di fuori del profilo originale. I progetti già salvati che corrispondono al profilo vengono classificati al riavvio, leggendo i file Excel conservati: non richiedono una nuova importazione o una riscrittura della sorgente.

### Regole comuni

Ogni riga con un nome in A identifica una legal entity univoca. Nei gruppi sono ammessi soltanto `x` (senza distinzione di maiuscole/minuscole) o celle vuote. Una X senza il nome dell'entità resta un errore. I gruppi numerici possono sovrapporsi; due gruppi con la stessa cardinalità devono avere gli stessi membri, perché una formula che contiene soltanto quel moltiplicatore non permette di distinguerli.

Le colonne prive di intestazione e di X vengono ignorate anche se contengono annotazioni o calcoli di confronto. I testi sotto l'elenco senza un nome di entità non diventano righe di anagrafica. Un'intestazione non vuota e non riconosciuta viene segnalata invece di attribuirle un significato presunto.

I riepiloghi scritti a lato o sotto la tabella non vengono sommati ai budget: i valori economici provengono dalle righe di `Remediations` e `OT`. Nessuna classificazione geografica o normativa viene ricavata da servizi esterni.

## Remediations

Le intestazioni sono nella **riga 3**, con queste posizioni:

| Colonna | Intestazione |
| --- | --- |
| C | Domain |
| D | Remediation name |
| E | Global |
| F | Local |
| G | Applicable Countries (to be verified) |
| H | Who has this? |
| I | Budget Global |
| J | Budget Local - Complete |
| K | Budget Local - Business Oriented |
| L | BUDGET LOCAL TOT |
| M | Year |
| N | NIS2 |
| O | Countries NIS2 - Complete |
| P | Countries NIS2 - Business Oriented |
| Q | OWNER |
| R | PRIORITY |
| S | DOMAIN2 |

Le righe dati iniziano dalla 4 e devono avere il nome della remediation in D. B contiene l'ID originale, se presente. ID ripetuti e assenti sono conservati: la chiave interna usa foglio e riga Excel. Righe/colonne nascoste e filtri Excel non escludono dati. I testi di descrizione restano invariati; spazi ai bordi di domini/owner sono normalizzati per il raggruppamento.

I, J, K e L accettano numeri oppure celle vuote. Le formule devono avere risultati numerici salvati nel workbook. Una stima assente resta distinta dallo zero. I valori salvati vengono usati senza motore generico di calcolo; i totali disponibili sono riconciliati dove il file contiene una riga di totale. J e K sono costi unitari, mentre L è il totale esteso della singola remediation: sommare i valori di J o K non produce automaticamente il costo di una categoria organizzativa.

Per attribuire il Local alle singole entità, il formato riconosciuto è:

```text
=J4*3+K4*2
```

Sono ammesse lettere minuscole, spazi e riferimenti assoluti come `$J$4`. I riferimenti devono puntare alla stessa riga della remediation e i moltiplicatori a gruppi definiti in LE_List. Il totale salvato in L deve coincidere con l'aritmetica della formula. Formule non riconosciute non vengono eseguite: il valore Excel può restare disponibile a livello complessivo ma senza attribuzione per entità.

L'attribuzione economica non equivale a conferma dell'applicabilità operativa. Se un elenco esplicito di country contraddice i gruppi economici, il tool segnala l'ambiguità e non inventa la ripartizione. Il budget Global rimane di gruppo anche applicando filtri sulle entità. Per le righe NIS2 con country non riconciliate, l’attribuzione rimane sospesa: i budget complessivi restano inclusi e non vengono assegnati automaticamente al gruppo OT solo perché compare lo stesso moltiplicatore.

## OT (facoltativo)

Le intestazioni sono nella **riga 1**:

| Colonna | Intestazione |
| --- | --- |
| C | Domain |
| D | Remediation name |
| E | Budget Global |
| F | Budget Local |
| G | Local Complessivo |
| H | Anno |
| I | NIS 2 |

Le righe iniziano dalla 2. B contiene l'ID, E il Global, F il costo locale unitario, G il Local complessivo. Per l'attribuzione è riconosciuta una formula della stessa riga come `=F2*3`, dove `3` identifica un gruppo LE_List. OT resta un perimetro selezionabile separatamente. Il suo Global viene aggiunto una volta al Global di gruppo; il Local è un delta aggiunto una volta alle entità attribuibili dalla formula. Con la classificazione semantica, le entità OT appartengono alla categoria Local Complete + OT. Il riepilogo conserva distinti base Complete e delta OT: non somma una seconda volta il valore già comprensivo di OT.

## Owner e tracciabilità

La label dell'owner `KPMG` viene mostrata come `Advisor` in filtri, viste e presentazioni. La sostituzione riguarda soltanto l'owner; loghi, stile e copyright KPMG restano invariati. Il documento importato conserva sia l'owner visualizzato sia il testo originale della cella per la tracciabilità. Il file Excel originale non viene riscritto.

ID uguali non uniscono le remediation: foglio e riga identificano ogni record. Le due righe NIS2 confermate restano entrambe nei totali; l'assenza di una ripartizione per country non comporta la loro esclusione.

Per le formule e un esempio completo di riconciliazione consultare [Logiche di calcolo nelle note della versione](release-notes.md#logiche-di-calcolo).

## Limiti e ricalcolo

Il limite di upload è 10 MB; il parser applica anche limiti ai contenuti ZIP e alle dimensioni dei fogli. Sono esclusi file con macro. Dopo aver modificato formule o importi, aprire in Excel/LibreOffice, ricalcolare e salvare prima dell'importazione. Una cache assente o incoerente viene rifiutata con un messaggio esplicito; il progetto precedente rimane disponibile.

Per usare fogli, intestazioni o logiche differenti occorre implementare una mappatura di importazione esplicita. Le celle non vengono interpretate attraverso AI e non vengono inferiti legami verso Findings, dipendenze progettuali o nuove remediation.

## Campi opzionali degli investimenti (1.3.0)

Nel solo foglio **Remediations**, aggiungere alla riga 3 le colonne `Capex/Opex`, `Rischi` e `Impatto`, dopo le colonne esistenti. Sono riconosciute dal nome, non dalla posizione reciproca. Le colonne esistenti devono restare nelle loro posizioni.

Ogni riga ha un solo valore Capex oppure Opex, un rischio principale (testo libero) e un impatto principale Alto, Medio o Basso. Spazi esterni e maiuscole dei valori Capex/Opex e dei livelli vengono normalizzati. I nomi dei rischi non sono predefiniti. Non sono ricavati dai domini e non si dividono celle in più rischi.

Le colonne possono mancare nei file già salvati. Celle vuote, colonne assenti e righe OT sono mostrate come **Non specificato**. Valori non riconosciuti sono conservati e mostrati senza assegnare loro un livello o un colore di rischio. Intestazioni duplicate vengono rifiutate. Nessun budget viene stimato o modificato.

Dalla 1.3.1, la mappa rischi e investimenti richiede Capex oppure Opex e un rischio non vuoto. Le righe che non soddisfano questi requisiti sono escluse soltanto da quella mappa con un avviso e un conteggio; rimangono nei dati importati, nelle altre viste e nei totali. L’impatto può ancora risultare non specificato: non viene attribuito automaticamente un livello.

## Consolidato All Remediations (1.4.0)

Richiede LE_List e All Remediations. Intestazioni alla riga 1: Remediation, Domain, Remediation name, Budget Global, Budget Local - Complete, Budget Local - Business Oriented, BUDGET LOCAL TOT, Year, NIS2, Owner, Priority, Type Of Remediation, Risk Type, Impact type, Risk Level, CAPEX/OPEX, Note. Le descrizioni tra parentesi su righe successive delle intestazioni Risk/Impact sono accettate.

Il consolidato è la fonte unica di dati economici e attributi. I fogli CMA, WIFI, VA Remediations e OT Remediations sono facoltativi per descrizioni e applicabilità: si confrontano anno, importi e nome normalizzato (oppure ID quando il nome non coincide). Non si sommano i loro budget. I riepiloghi Budget non sono fonti additive. Gli ID R.OT. identificano il perimetro OT; le chiavi univoche sono All Remediations:riga.

Risk Type e Impact Type possono contenere più valori separati da ritorni a capo; non definiscono coppie rischio–impatto. Risk Level ammette High/Medium/Low e resta separato dai tipi di impatto. CAPEX/OPEX classifica la riga intera. Note è testo originale riferito alla classificazione economica; non cambia automaticamente classificazioni o budget.

I risultati numerici delle formule devono essere salvati. La formula originale è conservata. Se una formula richiama un’altra riga o usa un gruppo non identificabile in LE_List, il totale viene conservato senza attribuzione country automatica. Gli anni delle righe annuali NIS2 devono essere corretti nel file, non vengono ricostruiti dal nome o dall’ID.

Dalla 1.4.1, All Remediations!K1 accetta anche `2027 CMA Priority`. I valori N/A di questa colonna indicano priorità non applicabile e sono distinti dalle celle vuote. Nei campi budget è ammesso il marcatore letterale `TBD` per una stima da definire: l’importo resta non disponibile e il testo è conservato nei metadati sorgente. Non vengono convertiti in zero né testi arbitrari né formule senza risultati validi.

## Tracciato finale con quattro impatti (1.4.5)

In All Remediations: N = Risk Level; P = Reputational Impact; Q = Regulatory Impact; R = Economic Impact; S = Operational Impact; T = CAPEX/OPEX; U = Note. La colonna O è ignorata. Ogni impatto ha il proprio livello High/Medium/Low, distinto dal Risk Level. I campi vuoti restano non specificati; non vengono dedotti da O né dal Risk Level. I tracciati precedenti rimangono supportati.
