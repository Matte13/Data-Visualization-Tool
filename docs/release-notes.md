# Note di versione

## 1.2.0

### Cosa cambia

- La barra dei filtri è collocata sopra i riquadri dei budget e rimane utilizzabile in presentazione.
- Il nuovo formato di `LE_List` distingue Local Complete + OT, Local Complete senza OT e Local Business attraverso le X. Il vecchio formato numerico continua a essere importabile.
- Il riepilogo mantiene separati budget di base, delta OT e importi non attribuibili con certezza. Gli importi restano quelli dell'Excel.
- L'owner precedentemente visualizzato come KPMG è denominato **Advisor**. Logo, colori, font e footer KPMG rimangono quelli approvati.
- Le due righe NIS2 con lo stesso ID restano interventi distinti. L'attribuzione NIS2 alle singole country rimane sospesa.

### Logiche di calcolo

#### 1. Fonti e unità

Il tool legge le righe di `Remediations` e, quando selezionato, `OT`. Righe e colonne nascoste e filtri applicati in Excel non escludono dati. I risultati delle formule devono essere già salvati nel workbook. L'app controlla le formule riconosciute ma non esegue un motore generico Excel e non usa AI per stimare budget o nuove remediation.

| Foglio e colonna | Significato |
| --- | --- |
| `Remediations!I` | Budget Global della riga, riferito al gruppo |
| `Remediations!J` | Costo unitario Local Complete |
| `Remediations!K` | Costo unitario Local Business |
| `Remediations!L` | Budget Local complessivo della riga, già esteso con i suoi moltiplicatori |
| `OT!E` | Delta Global OT della riga, riferito al gruppo |
| `OT!F` | Costo unitario Local OT |
| `OT!G` | Delta Local OT complessivo della riga |

Le somme delle colonne J, K e F sono somme di costi unitari. Non sono già i totali di tutte le legal entity e non sono automaticamente il budget di ogni singola entità. Le annotazioni di confronto in `LE_List` non sono importi aggiuntivi e non entrano una seconda volta nelle somme.

#### 2. Base e delta OT

Con entrambi i fogli selezionati:

```text
Global complessivo = somma Global Remediations + somma Global OT
Local complessivo  = somma Local Remediations  + somma Local OT
Budget complessivo = Global complessivo + Local complessivo
```

Il Global OT viene aggiunto una volta al budget di gruppo. Non viene moltiplicato per il numero delle entità. Il Local OT è un delta aggiunto una volta alle entità a cui è attribuibile. Se OT non è selezionato, il delta è escluso dal perimetro corrente.

Per una categoria Complete con OT il riepilogo espone **base + delta OT = totale**. Quando si sommano le categorie organizzative, si usa quel totale una sola volta: non si aggiunge nuovamente il delta OT già incluso.

#### 3. Moltiplicatori e appartenenza alle entità

Il Local esteso di ogni remediation segue la sua formula, per esempio:

```text
Local della riga = J della riga × gruppo Complete applicabile
                 + K della riga × gruppo Business applicabile
Local OT         = F della riga × gruppo OT applicabile
```

I moltiplicatori si applicano **riga per riga**. Restano validi anche i gruppi specifici, come quelli da 5, 6 o 9 entità: non vengono sostituiti con un unico numero generale di Complete o Business.

Le X identificano i membri di ogni gruppo. La categoria organizzativa dipende dalla legal entity:

- **Complete + OT:** appartiene sia alle Complete sia alle OT.
- **Complete senza OT:** appartiene alle Complete e non alle OT.
- **Business:** appartiene al gruppo Business.

Una specifica remediation può applicare il costo della colonna J a un'entità classificata Business. In questo caso l'importo continua a seguire la formula, ma nella vista per categoria viene attribuito alla categoria Business di quell'entità. Non si cambia il prezzo e non si riclassifica l'entità per farla coincidere con il nome della colonna.

Perciò il budget Business non è sempre uguale a `somma K × numero Business`. Allo stesso modo non si può moltiplicare tutta la somma J per il numero totale delle Complete ignorando le eccezioni delle singole righe.

#### 4. Riconciliazione per categoria

Il totale di gruppo rimane il valore presente nel file. La ripartizione per categorie usa le attribuzioni alle entità riconoscibili dalla formula e dalle X. I valori delle entità senza categoria esplicita restano distinti da quelli privi di un'attribuzione per legal entity.

```text
Local complessivo = Local attribuito alle categorie
                  + Local attribuito a entità non classificate
                  + Local non attribuito con certezza
```

Il residuo non viene suddiviso in modo proporzionale e non scompare dal totale. Per una selezione di singole legal entity il tool mostra soltanto gli importi attribuibili alle entità scelte, segnalando le stime mancanti o incerte. Il Global resta di gruppo anche quando si selezionano country o legal entity.

#### 5. Esempio con dati fittizi

Si considerino tre entità Complete, di cui una con OT, e due Business. Una remediation ha Global 500 €, costo Complete unitario 100 € e costo Business unitario 20 €. Una riga OT ha Global 50 € e costo Local unitario 30 €, applicabile all'unica entità OT.

| Componente | Calcolo | Importo |
| --- | --- | --- |
| Global base | 500 | 500 € |
| Delta Global OT | 50, aggiunto una volta | 50 € |
| Local Complete con OT | 100 di base + 30 OT | 130 € |
| Local Complete senza OT | 100 × 2 | 200 € |
| Local Business | 20 × 2 | 40 € |
| Local complessivo | 130 + 200 + 40 | 370 € |
| Budget complessivo | 500 + 50 + 370 | **920 €** |

Il Local di base è 340 € e il delta Local OT è 30 €. Sommare 370 € e di nuovo 30 € conterebbe l'OT due volte. L'esempio illustra il metodo; i dati reali restano quelli del workbook caricato e dei filtri correnti.

#### 6. Valori mancanti, NIS2 e duplicati

- Una cella vuota è una stima assente; uno zero è un valore esplicito. Le somme espongono gli importi disponibili con le relative segnalazioni.
- Una formula non riconosciuta conserva il totale di gruppo salvato, senza inventare una ripartizione per entità.
- Un elenco country in conflitto con il gruppo della formula rimane da confermare. Per le righe NIS2 sospese non viene usato automaticamente il gruppo OT solo perché ha lo stesso numero di membri.
- Ogni record è identificato da foglio e riga Excel. ID ripetuti restano record distinti e vengono inclusi una volta ciascuno.

#### 7. Filtri ed esportazioni

Anno, dominio, owner, entità, perimetro e livello Global/Local determinano la vista corrente. Dashboard, CSV e PowerPoint devono riferirsi allo stesso perimetro. Il CSV conserva anche i valori originali e il budget visualizzato; il PowerPoint conserva i dettagli nelle note delle slide. L'Excel originale resta scaricabile senza riscrittura.

### Compatibilità e ritorno alla versione precedente

La 1.2.0 accetta sia le intestazioni semantiche sia il vecchio formato numerico. Per il formato numerico privo di classificazione esplicita le categorie non vengono dedotte automaticamente.

La versione 1.1.2 non accetta le nuove intestazioni semantiche. Prima di importare il nuovo Excel salvare quindi una copia completa e verificata della libreria, con gli Excel attuali e quelli della prima importazione. Per tornare indietro ripristinare quel salvataggio con gli strumenti 1.2.0 e poi selezionare l'immagine precedente. La procedura è descritta in [deployment.md](deployment.md#salvataggio-della-libreria-e-rollback-alla-112).

### Verifiche di rilascio

Le verifiche locali di importazione, calcolo, interfaccia ed esportazione sono state completate. I workflow ripetono i controlli e includono test di persistenza e ripristino su SQL Server di prova: la pubblicazione dell'immagine richiede il loro superamento.

- Confronto indipendente fra celle/formule Excel e risultati dell'importatore, per anno e per componente.
- Riconciliazione fra totale di gruppo, categorie, delta OT e residui senza attribuzione certa.
- Test Python e JavaScript su classificazioni, eccezioni, stime mancanti, zero e ID ripetuti.
- Verifica nel browser di filtri, modalità presentazione, copie offline ed esportazioni.
- Confronto dei medesimi importi fra dashboard, CSV e PowerPoint.
- Verifica di esportazione/ripristino della libreria e compatibilità dello snapshot con la versione precedente.
