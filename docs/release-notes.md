# Note di versione

## 1.4.9

Verificato il workbook finale con le formule delle tre tabelle CMA nel foglio Budget CAPEX-OPEX estese dalla riga 62 alla 63. Tutte le 18 celle (CAPEX/OPEX × Global/Complete unitario/Business unitario × 2027/2028/2029) coincidono con le righe sorgente e con gli aggregati importati. Per il 2028 il totale è Global 1.035.000 €, Complete unitario 127.000 €, Business unitario 30.000 €.

L’app importa All Remediations e includeva già l’ultima remediation: non occorre modificare gli algoritmi o aggiungere importi ai totali. Il nuovo workbook produce le stesse 79 righe del precedente. Test sintetico di regressione: riga finale 63 nei due fogli, preservata in importazione e nei totali della presentazione filtrata per 2027, 2028 e 2029. Aggiornare il file del progetto per conservare il sorgente finale; nessun workbook del cliente è incluso nel repository.

## 1.4.8

Rimosso il simbolo a croce dagli importi delle celle annuali, dai totali country e dalla legenda nelle tabelle budget PowerPoint. Nessuna modifica agli importi o ai calcoli: la nota testuale chiarisce che i totali sono calcolati sulle stime disponibili, mentre dati mancanti, zeri e dettagli originali rimangono distinguibili.

## 1.4.7

Esportazione PowerPoint aggiornata ai separatori fotografici del deck Italfarmaco_CMA_ppt. I quattro modelli distinti vengono mescolati per ogni esportazione e usati una volta ciascuno; l’ordine delle sezioni rimane Budget → Anni → Country / legal entity → Remediation. Titoli modificabili e data corrente calcolata in Europe/Rome. La slide finale originale è sempre l’ultima.

Immagini, layout, loghi e collegamenti sono conservati in un pacchetto portabile, con risorse superflue, vecchia copertina e note sorgente rimosse. Il pacchetto di installazione include la risorsa. Grafici e dati rimangono modificabili e rispettano i filtri. Massimo 15 slide incluse le conclusioni: i riepiloghi annuali diventano al massimo due, con dettaglio completo nelle note. Nessuna migrazione dati o nuova importazione richiesta.

## 1.4.6

Tutti i box remediation nelle mappe mostrano totale e split Global/Local quando è attivo il perimetro combinato, rispettando le entità selezionate. I perimetri singoli mostrano soltanto il relativo budget; importi mancanti restano distinti da zero.

Aggiunta Mappa remediation dopo Mappa per Risk Type: Anno → Remediation → Risk Type → Impact Type → Capex/Opex. Percorso indipendente, navigazione e dettaglio coerenti con le altre mappe, selezioni conservate nell’HTML offline. Rimossi i budget da box e tooltip degli impatti; livelli e colori sono mantenuti. Nessuna modifica alle righe o ai calcoli del file, nessuna reimportazione richiesta.

## 1.4.5

Supporto al tracciato finale All Remediations: N = Risk Level, P–S = Reputational/Regulatory/Economic/Operational Impact, T = CAPEX/OPEX, U = Note. O è un campo di ragionamento personale, ignorato dall’importazione. I quattro impatti vengono conservati con livelli indipendenti dal rischio e mostrati nelle due mappe, nel dettaglio e nel CSV. I valori mancanti restano non specificati. Nessuna duplicazione delle righe o degli importi; supporto ai tracciati precedenti conservato.

Riconosciute anche le colonne spostate del foglio di dettaglio CMA, WIFI, VA Remediations. Aggiornare l’Excel del progetto per acquisire le nuove valutazioni; non serve migrare il database. L’Excel originale scaricabile conserva, come sempre, tutti i contenuti del file caricato, inclusa O.

## 1.4.4

Aggiunta **Mappa per Risk Type** dopo la mappa rischi e investimenti: Anno → Risk Type → Remediation → Impact Type → Capex/Opex, senza dominio. Riutilizza il grafico e i filtri condivisi, con percorso di selezione indipendente, navigazione da tastiera e dettaglio remediation. La copia HTML offline conserva entrambi i percorsi.

Aggiornati versione visibile, README e riferimenti di installazione. Nessuna migrazione, modifica dei budget o reimportazione Excel richiesta.

## 1.4.3

Nelle mappe un click seleziona/prosegue, due click aprono il dettaglio. La gestione considera l’eventuale ridimensionamento del grafico dopo il primo click in presentazione. Invio mantiene l’accesso da tastiera ai dettagli; nelle schede non cambia il click singolo.

La finestra del dettaglio è centrata, senza modificare lo stile dei contenuti o il pulsante X. Altezza limitata allo schermo e scorrimento interno; funzionamento anche su mobile e nella copia offline. Nessuna modifica a dati, budget o formato Excel.

## 1.4.2

Note Capex/Opex spostate nel pannello della singola remediation, soltanto quando il campo contiene una nota effettiva. Rimosso il popup dei box Capex/Opex.

I box delle tre mappe conservano etichetta e importo del budget selezionato. Conteggi, ID, owner e riferimenti tecnici non occupano più spazio nel grafico; restano nei dettagli. Tutti i collegamenti utilizzano curve, inclusi i percorsi separati remediation→Impact Type: nessuna associazione rischio–impatto viene dedotta.

Layout normale, presentazione e HTML offline condividono le modifiche. Nessuna variazione ai dati o alle logiche di calcolo; nessuna reimportazione richiesta per i progetti già salvati.

## 1.4.1

Corretto l’import dell’ultimo consolidato: K1 può essere Priority oppure 2027 CMA Priority, con normalizzazione di spazi e maiuscole. L’intestazione originale resta tracciabile.

La stringa letterale TBD nei budget indica una stima non disponibile: viene conservata come marcatore sorgente, non diventa zero e non genera una stima. La priorità N/A è rappresentata come Non applicabile, distinta dal dato vuoto. Formule e altri valori economici restano sottoposti ai controlli numerici.

Dopo aver aggiornato l’immagine a 1.4.1, ripetere Aggiorna Excel usando lo stesso file. Il caricamento fallito non sostituisce il progetto precedentemente salvato.

## 1.4.0

Nuovo importatore per All Remediations con LE_List, compatibile con i file precedenti. Il consolidato viene importato una sola volta, distinguendo OT dagli ID R.OT.; descrizioni e applicabilità dei fogli di dettaglio vengono aggiunte solo da abbinamenti verificabili. Riferimenti e formule originali restano tracciabili.

### Logiche dei dati

- Risk Type e Impact Type sono liste indipendenti di attributi della remediation, non coppie. I filtri usano OR nello stesso campo e AND tra campi; budget e conteggi lavorano su righe sorgente univoche. I gruppi di attributi possono sovrapporsi e non sono sommabili.
- Risk Level è distinto da Impact Type: High rosso, Medium giallo, Low verde. Type Of Remediation distingue People, Process e Technology.
- Le formule locali riconosciute del consolidato sono E×n+F×m per CMA e E×n per OT, con riferimenti assoluti o relativi. Si verificano i risultati salvati; le attribuzioni usano le X di LE_List. Gruppi non associabili o riferimenti ad altre righe conservano il totale Excel senza attribuzione country inventata.
- Gli interventi annuali NIS2 restano separati e il loro budget è annuale. Gli anni vengono sempre letti dall’Excel: le correzioni vanno caricate con Aggiorna Excel.
- Il Global resta di gruppo e il delta OT viene conteggiato una sola volta. Il nuovo foglio consolidato non si somma ai fogli CMA/OT o ai riepiloghi Budget.

### Note Capex/Opex

Il click sul box apre le note originali delle righe incluse nell’anno e nei filtri correnti. Testi identici sono mostrati una volta con tutti i riferimenti alle righe. Celle vuote o `-` non generano spiegazioni automatiche. Il popup è richiudibile con pulsante, Esc o click esterno e funziona nella copia HTML offline.

L’immagine 1.4.0 supporta entrambi i tracciati. Il caricamento del nuovo formato non è leggibile dalle immagini 1.3.x: conservare uno snapshot della libreria prima dell’aggiornamento dei dati se serve ripristinare anche quella versione. Nessuna migrazione delle tabelle SQL.

## 1.3.3

La modalità presentazione usa la larghezza disponibile della finestra, con margini laterali di 16 px. I grafici delle tre mappe si adattano al contenitore conservando le proporzioni: tutte le colonne rientrano nella larghezza visibile. Il layout normale e le logiche dei dati rimangono invariati. Il controllo browser verifica i margini e l’assenza di scorrimento orizzontale su schermi larghi.

## 1.3.2

Rimossa l’opzione Non specificato dai filtri Capex/Opex, Rischi e Impatto nelle due barre e nella copia offline. Tutti conserva le righe prive di attributi nei totali; le selezioni parziali escludono le righe senza i valori selezionati. Nessuna modifica ai dati importati o alle regole della mappa rischi e investimenti.

## 1.3.1

- Grafica della mappa rischi e investimenti allineata alle altre mappe mediante le stesse classi, tipografia, dimensioni e palette di anni e domini.
- Percorso **Anno → Capex/Opex → Dominio → Remediation → Rischio associato → Impatto**. Le remediation sono selezionate per chiave di riga: nessun accorpamento di nomi duplicati. La selezione apre il dettaglio e mostra il collegamento al rischio; l’impatto rimane l’ultimo livello.
- Capex/Opex e rischio devono essere compilati per comparire in questa mappa. I casi incompleti sono esclusi solo da questa vista con conteggio esplicito; restano nei dati, nelle altre viste e nei totali. Nessuna categoria o attribuzione viene inventata e l’importazione dei vecchi file resta possibile.
- Bandiere incorporate prima del nome nell’elenco paesi del dettaglio, condiviso da tutte le viste. Un’entità composta può avere più bandiere; i nomi non riconosciuti mantengono il simbolo neutro. Nessun caricamento da Internet.

## 1.3.0

Aggiunta la vista **Mappa rischi e investimenti**: Anno → Capex/Opex → Rischio → Impatto → Dominio → Remediation. Selezionare un box per aprire il livello successivo; frecce e importi rappresentano esclusivamente le righe del percorso e i filtri Global/Local e country correnti. I dettagli conservano anche owner e descrizioni originali.

I tre filtri nuovi sono disponibili nella barra laterale e sopra i KPI, anche in presentazione. Si applicano a tutte le viste e alle esportazioni. Il CSV include i tre attributi e il PowerPoint riporta i filtri selezionati nelle note. La copia HTML conserva la nuova vista e il percorso senza servizi esterni.

### Logiche dei nuovi attributi

Le colonne opzionali sono lette per nome dalla riga 3 di Remediations, lasciando intatte le colonne esistenti. Ogni riga ha un rischio e un impatto principale. Alto è rosso, Medio giallo, Basso verde: i colori descrivono il livello fornito, senza calcoli di rischio. Capex/Opex classifica l’intero budget della riga; non ne produce una ripartizione percentuale.

Valori vuoti e righe OT restano Non specificato. Il tool non deduce dati dai domini. I file precedenti continuano a funzionare e non richiedono reimportazione; per mostrare i nuovi valori compilati occorre caricare il nuovo Excel nel progetto. Formule, totali, moltiplicatori, duplicati e attribuzioni NIS2 conservano le logiche precedenti.

### Verifiche

Test Python e JavaScript, controlli browser del nuovo percorso, filtri sincronizzati, PPT filtrata e HTML offline. Confronto dei budget prima/dopo l’aggiunta delle colonne su workbook sintetici: totali e attribuzioni invariati. Il workflow di rilascio verifica anche la persistenza SQL su un database di prova.

## 1.2.1

### Correzione per i progetti già salvati

La classificazione delle legal entity è disponibile anche per l'Excel originale già conservato nella libreria. Per applicare la patch aggiornare l'immagine a **1.2.1** e riavviare il processo: **non occorre ricaricare l'Excel**.

All'avvio il tool rilegge i workbook salvati e riconosce il profilo originale descritto sotto. Il riconoscimento calcola la classificazione in memoria: non riscrive i file Excel, non modifica le appartenenze X e non aggiorna ID, date o contenuti dei progetti nel database.

La versione installata è visibile nell’interfaccia: nel footer in basso a sinistra della barra laterale e nel footer della pagina, disponibile anche in modalità presentazione.

### Logiche di riconoscimento del formato originale

Il profilo di compatibilità richiede precisamente i cinque gruppi nelle colonne C:G di `LE_List`:

| Colonna | Intestazione accettata | Significato nel profilo originale |
| --- | --- | --- |
| C | `6` | Entità con OT |
| D | `8` | Local Business |
| E | `13` | Local Complete |
| F | `5` | Gruppo specifico della formula |
| G | `9` oppure `Europa AI ACT 9` | Gruppo specifico della formula |

Il tool verifica le cardinalità delle X, la presenza di 21 entità, l'inclusione delle OT nelle Complete e la separazione completa fra Complete e Business. Il riconoscimento non usa i nomi delle country. Da questo profilo validato derivano **6 Complete con OT, 7 Complete senza OT e 8 Business**.

Le formule specifiche dei gruppi da 5 e 9 entità continuano a essere applicate riga per riga; non determinano la categoria organizzativa dell'entità. Gli altri formati numerici validi rimangono importabili, ma restano senza classificazione quando non corrispondono a questo profilo approvato. Le intestazioni semantiche introdotte nella 1.2.0 restano supportate.

### Cosa rimane uguale

Il budget continua a provenire dalle righe originali e dalle formule salvate: la patch aggiunge il riconoscimento della classificazione al formato esistente. Base e delta OT sono conteggiati una volta; il Global rimane di gruppo. Restano il trattamento delle stime mancanti e dello zero, l'owner Advisor e le attribuzioni NIS2 sospese. Le [logiche di calcolo della 1.2.0](#logiche-di-calcolo) si applicano anche a questa patch.

Per una libreria che conserva esclusivamente workbook compatibili con la 1.1.2, il riconoscimento non richiede una migrazione dei dati. Se invece sono stati importati file con nuove intestazioni, seguire la [procedura di snapshot e rollback](deployment.md#salvataggio-della-libreria-e-rollback-alla-112) prima di ripristinare l'immagine precedente.

### Verifiche della patch

Le verifiche locali della patch sono state completate:

- 159 test Python eseguiti: 146 superati, 13 integrazioni SQL/PostgreSQL riservate agli ambienti di prova dedicati e quindi saltate localmente.
- 47 test JavaScript superati.
- Verifiche browser dei filtri e della riconciliazione semantica superate.
- Confronto indipendente dell'Excel originale e di quello con nuove intestazioni: righe, formule, attribuzioni, segnalazioni e totali restano invariati; sul formato originale cambia soltanto la disponibilità della classificazione.
- Riapertura della libreria locale persistita senza nuova importazione: byte dei file, SHA-256, ID e date dei progetti invariati.

Il workflow di rilascio ripete i controlli e include la verifica di persistenza su SQL Server di prova. La pubblicazione dell'immagine richiede il suo superamento; i controlli non accedono al database aziendale.

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
