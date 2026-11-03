# Tracciato Excel supportato

Data Visualization Tool importa progetti diversi con lo **stesso tracciato**, non qualsiasi file Excel. I contenuti delle righe, anni, domini, owner, entity e gruppi possono cambiare. I fogli obbligatori sono `LE_List` e `Remediations`; `OT` è facoltativo. Gli altri fogli non vengono interpretati come sorgenti aggiuntive di remediation.

## LE_List

Riga 1: colonna A `Country/Legal Entities`, colonna B `Backup`. Dalla colonna C iniziano i gruppi usati dalle formule dei budget Local. Il nome del gruppo deve essere un intero positivo oppure un'etichetta terminante con quell'intero, ad esempio `3` o `Ambito operativo 3`.

Ogni riga successiva identifica una legal entity univoca. Nei gruppi sono ammessi `x` (senza distinzione di maiuscole/minuscole) o cella vuota. Il numero di `x` deve coincidere con l'intero del gruppo, perché le formule usano quel valore come moltiplicatore. Ad esempio un gruppo `3` deve contenere tre entità. I gruppi possono sovrapporsi. Due gruppi con lo stesso numero devono avere gli stessi membri: una formula contenente soltanto un moltiplicatore non permetterebbe di distinguerli altrimenti.

I gruppi non sono fissati nel codice a numeri o country del progetto iniziale. Nessuna appartenenza geografica o normativa viene derivata da servizi esterni.

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

I, J, K e L accettano numeri oppure celle vuote. Le formule devono avere risultati numerici salvati nel workbook. Una stima assente resta distinta dallo zero. I valori salvati vengono usati senza motore generico di calcolo; i totali disponibili sono riconciliati dove il file contiene una riga di totale.

Per attribuire il Local alle singole entità, il formato riconosciuto è:

```text
=J4*3+K4*2
```

Sono ammesse lettere minuscole, spazi e riferimenti assoluti come `$J$4`. I riferimenti devono puntare alla stessa riga della remediation e i moltiplicatori a gruppi definiti in LE_List. Il totale salvato in L deve coincidere con l'aritmetica della formula. Formule non riconosciute non vengono eseguite: il valore Excel può restare disponibile a livello complessivo ma senza attribuzione per entità.

L'attribuzione economica non equivale a conferma dell'applicabilità operativa. Se un elenco esplicito di country contraddice i gruppi economici, il tool segnala l'ambiguità e non inventa la ripartizione. Il budget Global rimane di gruppo anche applicando filtri sulle entità.

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

Le righe iniziano dalla 2. B contiene l'ID, E il Global, F il costo locale unitario, G il Local complessivo. Per l'attribuzione è riconosciuta una formula della stessa riga come `=F2*3`, dove `3` identifica un gruppo LE_List. OT resta un perimetro selezionabile separatamente, senza sovrapposizioni o collegamenti automatici con Remediations.

## Limiti e ricalcolo

Il limite di upload è 10 MB; il parser applica anche limiti ai contenuti ZIP e alle dimensioni dei fogli. Sono esclusi file con macro. Dopo aver modificato formule o importi, aprire in Excel/LibreOffice, ricalcolare e salvare prima dell'importazione. Una cache assente o incoerente viene rifiutata con un messaggio esplicito; il progetto precedente rimane disponibile.

Per usare fogli, intestazioni o logiche differenti occorre implementare una mappatura di importazione esplicita. Le celle non vengono interpretate attraverso AI e non vengono inferiti legami verso Findings, dipendenze progettuali o nuove remediation.
