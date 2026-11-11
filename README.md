# Data Visualization Tool

Applicativo locale per presentare e navigare piani di remediation da Excel. Gestisce **più progetti separati**, ciascuno con il proprio workbook, le proprie country/legal entity, i filtri e i budget. I futuri Excel devono seguire uno dei tracciati supportati descritti in [docs/workbook-format.md](docs/workbook-format.md).

Tutte le logiche sono offline e deterministiche: nessun modello AI, API esterna, CDN, font remoto o telemetria. Le remediation vengono lette dal file senza suggerimenti, riscritture o correzioni automatiche. Il frontend non richiede Node/npm o un processo di build.

## Modifiche per versione

Ogni aggiornamento del tool viene documentato in questo README, indicando funzionalità, logiche dei dati e passaggi richiesti all’utente. Le spiegazioni estese restano nelle [note di versione](docs/release-notes.md).

### 1.4.5 — Quattro impatti per remediation

- Supporto al nuovo Excel: **Risk Level in N**, **Reputational, Regulatory, Economic e Operational Impact in P–S**, CAPEX/OPEX in T e note in U. La colonna O è ignorata e non alimenta viste, ricerca, filtri o CSV.
- Entrambe le mappe mostrano i quattro impatti con il proprio livello e colore: High rosso, Medium giallo, Low verde. Il Risk Level resta separato; nessun livello viene dedotto da altri campi.
- Dettaglio remediation e CSV riportano i quattro valori distinti. Copia HTML offline e filtri mantengono i nuovi attributi; i budget non vengono moltiplicati per il numero di impatti.
- Compatibilità con i precedenti Excel mantenuta. Per vedere le nuove valutazioni, aggiornare il progetto caricando il nuovo Excel; nessuna migrazione del database. Versione **1.4.5**, tag immagine previsto `ghcr.io/matte13/data-visualization-tool:1.4.5`.

### 1.4.4 — Mappa per Risk Type

- Nuova vista subito dopo **Mappa rischi e investimenti**, con percorso **Anno → Risk Type → Remediation → Impact Type → Capex/Opex**, senza il livello dominio.
- Stesso stile e filtri condivisi; percorso indipendente dalla mappa esistente. Navigazione da tastiera, dettaglio remediation e selezioni conservate nella copia HTML offline.
- Nessuna modifica ai dati o ai calcoli del budget; nessuna reimportazione Excel richiesta.
- Versione nell’interfaccia e configurazioni di installazione aggiornate a **1.4.4**. Tag immagine previsto: `ghcr.io/matte13/data-visualization-tool:1.4.4`.

### 1.4.3 — Click di navigazione e dettagli centrali

- Nelle tre mappe il **click singolo** seleziona la remediation e prosegue il diagramma quando sono presenti livelli successivi. Il **doppio click** apre tutti i dettagli. Il doppio click rimane affidabile anche in presentazione, quando il primo click espande il grafico.
- La finestra **Dettaglio remediation** appare al centro dello schermo, con gli stessi contenuti, font, colori e pulsante X in alto a destra. Scorrimento interno per i contenuti lunghi, chiusura con X, Esc o click esterno; dimensioni adattate anche al mobile.
- Da tastiera **Invio** apre direttamente i dettagli; le schede della vista Remediation continuano ad aprirsi con un click. Filtri, note Capex/Opex, dati ed esportazioni restano invariati.
- Immagine Azure: `ghcr.io/matte13/data-visualization-tool:1.4.3`. Nessuna reimportazione Excel richiesta.

### 1.4.2 — Mappe essenziali e note nel dettaglio

- Il click su Capex/Opex prosegue la navigazione senza aprire popup. Le note originali, se presenti e diverse da `-`, compaiono soltanto nel pannello **Dettaglio remediation**, riferite alla singola riga.
- In tutte e tre le mappe i box mostrano il nome e il solo importo economico selezionato (Global, Local o entrambi). Rimossi conteggi, ID, owner e riferimenti a fogli/righe dai box; i dettagli completi restano nel pannello laterale e nelle esportazioni.
- Tutte le frecce sono curve. I collegamenti remediation→Impact Type aggirano i box dei rischi con raccordi morbidi, senza angoli retti e senza suggerire coppie rischio–impatto.
- Le modifiche valgono anche in presentazione e nella copia HTML offline. Formule, budget, filtri e dati importati rimangono invariati.
- Immagine Azure: `ghcr.io/matte13/data-visualization-tool:1.4.2`. Non occorre caricare nuovamente l’Excel già salvato.

### 1.4.1 — Importazione dell’ultimo Excel

- Corretto il blocco su `All Remediations!K1`: la colonna priorità accetta sia **Priority** sia **2027 CMA Priority**, conservando l’intestazione originale nei dettagli e nelle esportazioni.
- Il budget letterale **TBD** viene importato come stima non disponibile, distinto da zero. Il marcatore originale è conservato e segnalato; altri testi non numerici non vengono convertiti silenziosamente in importi.
- La priorità **N/A** è distinta dai campi vuoti e filtrabile come **Non applicabile**. Il filtro mostra il nome originale della colonna, senza estendere automaticamente la priorità 2027 ad altre annualità.
- Immagine corretta: `ghcr.io/matte13/data-visualization-tool:1.4.1`. Dopo l’aggiornamento ripetere il caricamento dello stesso Excel; non occorre modificare le intestazioni o il file sorgente.

### 1.4.0 — Nuovo consolidato, tipi di impatto e note Capex/Opex

- Supportato il nuovo file con **All Remediations + LE_List**. Il consolidato è l’unica fonte di budget, anno, owner e attributi; i fogli CMA/OT servono solo per recuperare descrizioni e note di applicabilità tramite abbinamenti verificabili. I fogli Budget non vengono sommati.
- Separati **Risk Type** (Cyber, OT, Business Continuity, Compliance), **Impact Type** (Reputational, Regulatory, Economic, Operational), **Risk Level** (High, Medium, Low) e **Type Of Remediation** (People, Process, Technology). I livelli High/Medium/Low guidano rosso/giallo/verde. Non si ricava il livello dal tipo di impatto.
- Rischi e tipi di impatto multipli, separati su più righe nella cella, restano attributi della stessa remediation: OR tra le opzioni di un filtro, AND tra filtri diversi. La riga e il suo budget si contano una sola volta. Nella mappa entrambi gli attributi partono dalla remediation; non vengono inventate coppie rischio–impatto. I budget dei gruppi sovrapposti non devono essere sommati.
- Cliccando un box **Capex/Opex** si apre un popup con le **Note originali** del box e dell’anno selezionati, rispettando i filtri. Note uguali sono raccolte con tutti i riferimenti alle remediation. Celle vuote e `-` mostrano “Nessuna nota presente”. Chiusura con pulsante, Esc o click esterno; funzionante anche in presentazione e HTML offline.
- Le righe NIS2 annuali, gli ID duplicati e gli ID VA Report restano distinti per riga sorgente. Anni e importi sono letti dal file e non vengono corretti automaticamente. Una formula con gruppi non associabili o riferimenti ad altre righe conserva il valore salvato senza inventare una ripartizione country.
- CSV e note PowerPoint includono attributi multipli, livello, tipologia, note e riferimenti al consolidato. Rimane il limite di 15 slide. I vecchi progetti continuano a funzionare con il tracciato precedente.
- **Installazione:** `ghcr.io/matte13/data-visualization-tool:1.4.0`. Dopo l’aggiornamento usare **Aggiorna Excel** nel progetto per caricare il nuovo file completo di LE_List e delle correzioni degli anni NIS2. Il workbook cliente non viene distribuito su GitHub o nell’immagine.

### 1.3.3 — Mappe a tutta larghezza in presentazione

- In modalità **Presentazione** il contenuto sfrutta la larghezza della finestra con soli 16 px per lato, eliminando il limite centrale che lasciava due colonne vuote.
- Tutte e tre le mappe adattano il grafico alla larghezza del box: si vedono le colonne complete senza scorrimento orizzontale. Il rapporto tra larghezza e altezza viene conservato; finestre più piccole riducono proporzionalmente il grafico.
- La modalità normale mantiene le dimensioni precedenti. Filtri, dati ed esportazioni non cambiano.
- Immagine Azure: `ghcr.io/matte13/data-visualization-tool:1.3.3`.

### 1.3.2 — Opzioni dei filtri

- Rimossa l’opzione **Non specificato** dai filtri Capex/Opex, Rischi e Impatto, sia sopra la dashboard sia nella barra laterale, anche in presentazione e nella copia HTML offline.
- **Tutti** mantiene l’intero perimetro e i totali originali, comprese le righe prive di attributi. Le selezioni parziali considerano soltanto i valori scelti; **Seleziona tutti** ripristina il perimetro completo. I campi vuoti non vengono compilati automaticamente.
- Immagine Azure: `ghcr.io/matte13/data-visualization-tool:1.3.2`.

### 1.3.1 — Grafica della mappa e bandiere nei dettagli

- La mappa rischi e investimenti usa i componenti grafici delle altre mappe: stessi font, dimensioni dei box, colori per anno/dominio e stili delle frecce.
- Percorso aggiornato: **Anno → Capex/Opex → Dominio → Remediation → Rischio associato → Impatto**. Una remediation resta identificata dalla riga originale, anche quando il nome è duplicato. La sua selezione apre il dettaglio e consente di proseguire verso rischio e impatto.
- Nella sola mappa rischi e investimenti vengono mostrate righe con **Capex oppure Opex** e un **rischio compilato**. Le righe incomplete, comprese le eventuali OT senza attributi, restano nelle altre viste e nei totali; un avviso ne indica il numero. Non vengono create categorie “Non specificato” per Capex/Opex o rischio nella mappa. L’impatto mancante resta riconoscibile senza inventare un livello.
- Aggiunte piccole bandiere prima dei paesi nell’elenco di attribuzione del budget del dettaglio comune a tutte le viste, incluse le tre mappe. Le entità con più paesi mostrano più bandiere; per nomi non riconosciuti si mantiene l’icona neutra. Le immagini sono incorporate e funzionano offline.
- Aggiornamento Azure: `ghcr.io/matte13/data-visualization-tool:1.3.1`. Nessuna modifica al file Excel o ai dati nel database.

### 1.3.0 — Rischi e investimenti

- Nuova **Mappa rischi e investimenti**, con box e frecce navigabili: **Anno → Capex/Opex → Rischio → Impatto → Dominio → Remediation**. Selezionare un box apre il livello successivo; aprire una remediation mostra anche owner, descrizioni e riferimenti al file.
- Aggiunti i filtri **Capex/Opex**, **Rischi** e **Impatto**, sia nella barra laterale sia sopra i KPI, disponibili anche in presentazione. Aggiornano tutte le viste e le esportazioni insieme ai filtri esistenti.
- Ogni remediation ha una classificazione **Capex oppure Opex**, un rischio principale e un impatto principale. I livelli **Alto, Medio e Basso** sono rappresentati rispettivamente in **rosso, giallo e verde**. I nomi dei rischi provengono dall’Excel.
- Le colonne opzionali `Capex/Opex`, `Rischi` e `Impatto` si aggiungono alla **riga 3 del solo foglio Remediations**, dopo le colonne esistenti. Sono riconosciute per nome, senza modificare il tracciato precedente. Vedere il [formato delle colonne](docs/workbook-format.md#campi-opzionali-degli-investimenti-130).
- Colonne assenti, celle vuote e righe OT restano **Non specificato**. I valori non vengono dedotti dai domini; formule, budget, moltiplicatori e attribuzioni mantengono le logiche precedenti.
- Il CSV include i tre attributi; il PowerPoint rispetta le selezioni e riporta i filtri nelle note, mantenendo il limite di 15 slide. La copia HTML offline conserva la nuova mappa e il percorso selezionato.
- **Per aggiornare:** usare l’immagine `ghcr.io/matte13/data-visualization-tool:1.3.0`. I progetti esistenti continuano a funzionare; quando l’Excel sarà compilato, caricarlo dal pulsante **Aggiorna Excel** del progetto. Nessun Excel cliente è incluso nel repository.
- Verifiche: test Python e JavaScript, navigazione del grafico da tastiera, filtri condivisi, budget invariati, PowerPoint filtrato, HTML senza rete e persistenza SQL su database di prova.

### 1.2.1 — Compatibilità senza reimportazione

- Riconoscimento del profilo numerico originale di LE_List per mostrare le categorie Local nei progetti già salvati, senza reimportare o riscrivere l’Excel.
- Versione del tool visibile nel footer dell’interfaccia, anche in modalità presentazione.

### 1.2.0 — Composizione del budget

- Distinzione tra base Remediations e delta OT e tra Local Complete con OT, Complete senza OT e Business.
- Filtri sopra i KPI, label owner **Advisor** e strumenti per snapshot e rollback della libreria.
- Logiche e limiti di attribuzione documentati nelle [note della versione](docs/release-notes.md#120).

## Avvio locale

Prerequisito: Python 3.12 o superiore. Dalla cartella del repository:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell, in alternativa:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m app.server
```

Aprire nel browser **http://127.0.0.1:8000**. Il server ascolta solo sul computer locale. Non servono account, segreti o database; dopo l'installazione iniziale funziona senza connessione. Per scegliere una porta diversa: `python -m app.server --port 8080`.

Al primo avvio il workspace è vuoto: creare un progetto, assegnargli un nome e caricare il relativo `.xlsx`. Il repository non contiene workbook dei clienti, esportazioni con dati o credenziali.

## Gestione dei progetti

- **Nuovo progetto** importa un Excel in un progetto separato senza sovrascrivere gli altri. Il selettore nella barra laterale permette di passare fra i progetti salvati.
- **Aggiorna Excel** nel progetto aperto aggiorna soltanto quel progetto. I dati vengono validati prima della sostituzione: un file errato lascia intatto quello precedente.
- **Ripristina prima importazione** ripristina il primo Excel caricato in quel progetto, senza toccare gli altri.
- I progetti persistono nella directory locale `runtime/`, ignorata da Git. In Azure i progetti vengono conservati nel database Azure SQL configurato. Il workbook originale dell'utente non viene modificato.

L'importazione supporta file `.xlsx` compatibili fino a 10 MB, anche tramite trascinamento nella pagina. Prima di caricare un file modificato ricalcolarlo e salvarlo in Excel o LibreOffice, affinché siano presenti i risultati salvati delle formule. Il tool non esegue formule arbitrarie. Errori di schema, cache assente e incoerenze nei budget vengono mostrati in italiano.

## Viste e filtri

L’interfaccia web usa il logo KPMG del template e le sfumature aziendali **viola `#7213EA` → blu `#1E49E2`** nella navigazione e nelle azioni principali. Dati e grafici conservano la palette precedente: Global blu, Local verde acqua e colori distinti e stabili per anni, domini e owner. Il nome del prodotto resta **Data Visualization Tool**, con indicazione di uso interno.

Titoli, testo e controlli web usano la tipografia precedente, **Inter / font di sistema**, senza il carattere condensato KPMG. Le formule mantengono il carattere monospaziato. Non vengono scaricati font da Internet. Il foglio `web/brand.css` centralizza la configurazione e viene incluso anche nella copia HTML offline.

**Panoramica** mostra gli investimenti annuali, per dominio e per owner. Subito sotto, **Mappa Navigabile** esplora anno → dominio → remediation. **Mappa Navigabile per Owner** aggiunge il percorso anno → owner → dominio → remediation: mostra gli owner riportati nel file e apre le remediation selezionando un dominio, nel rispetto dei filtri correnti. Le frecce delle mappe rappresentano raggruppamenti, non dipendenze progettuali. **Remediation** presenta schede visive con dominio, owner, anno e budget Global/Local, ricerca, ordinamento e paginazione. **Country / legal entity** associa ogni entità ai suoi investimenti annuali con schede e barre sulla stessa scala; un click sull’anno apre la mappa filtrata per entità e anno.

Tutti i filtri sono **selezionati di default**, incluso OT quando presente. Ogni gruppo (perimetro, anno, dominio, owner, entità, NIS2, priorità, Capex/Opex, rischi e impatto) ha una casella **Seleziona tutti**: attivarla seleziona tutte le voci, disattivarla le esclude tutte. Una selezione vuota mostra zero risultati, mentre una selezione parziale è segnalata dalla casella intermedia. Durante le selezioni la barra laterale conserva posizione, gruppi aperti e focus del cursore.

Gli stessi filtri sono disponibili anche nella barra **Filtri** sopra i riquadri dei budget, prima delle schede Panoramica, Mappe, Remediation e Country / legal entity. Le due barre condividono le selezioni; i menu superiori restano aperti durante le scelte multiple e conservano la posizione nell'elenco. Escape chiude prima il menu aperto. In modalità **Presentazione** la barra superiore rimane visibile e offre anche ricerca, livello Global/Local e filtro sul budget locale. I controlli vengono esclusi dalla stampa e funzionano anche nella copia HTML offline.

**Budget da visualizzare** è disponibile sia nella barra laterale sia in quella sopra le viste, anche fuori dalla presentazione. Nella Panoramica si può cambiare la stessa selezione cliccando **Global** e **Local** nelle legende di Budget per dominio e Budget per anno. Almeno una componente resta attiva: sono disponibili Global, Local o entrambe. La scelta aggiorna il budget selezionato, importi, scale e ordinamento dei grafici, mappe ed esportazioni, conservando tutte le remediation filtrate. Il CSV mantiene i valori originali e aggiunge il livello e l'importo del budget visualizzato; il PowerPoint usa la medesima selezione.

I colori hanno un significato stabile: lo stesso anno mantiene lo stesso colore nelle diverse viste, i domini sono riconoscibili dai loro colori e Global/Local restano distinti. La precedente sezione “Qualità dei dati” è stata rimossa; gli avvisi necessari per interpretare importi mancanti o attribuzioni incerte restano nel dettaglio delle singole remediation e accanto ai grafici.

Filtri combinabili: perimetro Remediations/OT, anno, dominio, owner, country/legal entity, NIS2, priorità, Capex/Opex, rischi, impatto, ricerca e budget locale **positivo / zero / non determinato**. Il selettore Global/Local sceglie gli importi rappresentati, senza eliminare le righe a zero o prive di stima.

I budget Global sono importi di gruppo: non vengono ripartiti o moltiplicati per country. Complete/Business Oriented sono costi unitari; il Local complessivo viene letto dal file. Le attribuzioni per entità derivano esclusivamente dalle formule riconosciute e dai gruppi espliciti di LE_List, non certificano l'applicabilità operativa. Le attribuzioni ambigue restano segnalate e non diventano ripartizioni inventate. ID duplicati e righe senza ID rimangono distinti; celle vuote e zero rimangono distinguibili.

La **Composizione del budget** separa base Remediations e delta OT, per Global e Local. Con le intestazioni esplicite di LE_List o il profilo numerico originale validato mostra Local Complete + OT, Complete senza OT e Business, attribuendo i costi alla categoria delle rispettive entità anche quando una formula usa una colonna unitaria diversa. Il residuo senza attribuzione certa rimane nel totale di gruppo e viene mostrato separatamente. L'owner KPMG è visualizzato come **Advisor**, con il valore originale conservato e senza modificare branding o Excel sorgente.

Le **[note della versione 1.4.5](docs/release-notes.md)** spiegano il riconoscimento del formato originale e le logiche di calcolo con formule ed esempi. Per i progetti già salvati con quel formato basta aggiornare l’immagine e riavviare: non serve importare di nuovo l’Excel e i file originali rimangono invariati. Prima di caricare formati diversi leggere anche la **[procedura di snapshot e rollback](docs/deployment.md#salvataggio-della-libreria-e-rollback-alla-112)**, che distingue il ritorno al software precedente dal ripristino dei dati.

## Presentazione ed esportazioni

Il pulsante **Scarica PowerPoint** in alto esporta una presentazione `.pptx` modificabile di **massimo 15 slide**, rispettando i filtri, le entità e il budget Global/Local selezionati. Dopo la copertina, quattro separatori introducono **Budget → Anni → Country / legal entity → Remediation**. La sintesi mostra investimenti per anno, dominio e owner, fino a tre riepiloghi annuali, due viste country/anno e due slide sulle remediation. I dettagli completi di tutte le righe filtrate, comprese quelle fuori dalla pagina del tool, sono conservati nelle note delle ultime due slide. Importi e testi provengono dal file: non vengono generate nuove remediation.

L’esportazione PowerPoint funziona nell’app locale; la copia HTML autonoma mantiene le altre esportazioni. La presentazione usa grafici, forme e testi modificabili, senza servizi esterni. Il riferimento grafico principale è **Global Cyber Pitch**: formato 16:9, sfondo sfumato viola–blu soltanto per la copertina e i separatori con il solo titolo, sfondo bianco per le slide con i dati, titoli in KPMG Bold e corpo in Arial. Global è viola, Local blu; la stessa codifica compare nelle legende e nei grafici. Ogni slide riprende il footer originale con logo KPMG vettoriale, copyright **2026**, classificazione e numero pagina nelle posizioni del template, bianchi su sfondo sfumato e blu/grigi su bianco.

Per rispettare il limite anche con progetti più grandi, i riepiloghi raggruppano esplicitamente le categorie eccedenti in **Altri**, senza perdere i relativi importi: fino a otto categorie nei grafici budget, tre riepiloghi annuali e 22 righe country in due slide. Se gli anni sono più di tre, il dettaglio mostra i due con maggiore budget e un riepilogo degli altri. Le viste country mostrano fino a cinque colonne annuali, con le altre annualità aggregate. La sintesi remediation presenta i conteggi e le sei voci con il maggiore budget selezionato; l’ordinamento non modifica la priorità del file. Tutti gli anni, le country, i domini e gli owner restano documentati integralmente nelle note dei rispettivi riepiloghi; valori mancanti e zero restano distinti.

Il font KPMG è incorporato nel PowerPoint usando i dati originali del template. PowerPoint è il riferimento per la resa tipografica; altri programmi possono sostituire i font incorporati. Le risorse incluse contengono soltanto il tema, i font incorporabili e il logo del footer: nessuna slide, dato commerciale o nota dei template originali viene distribuita. Sfondi, icone, testi e grafici sono elementi nativi della presentazione.

`Presentazione` nasconde la barra laterale e le azioni di gestione, mantenendo disponibili i filtri sopra le viste; Escape chiude un menu o un dettaglio aperto, poi esce dalla modalità. `Esporta` offre CSV delle righe filtrate, Excel sorgente, copia HTML offline e stampa/PDF. La mappa si può salvare in PNG.

La copia HTML è una modalità aggiuntiva di condivisione: contiene **tutti i dati del solo progetto aperto**, compresi quelli nascosti dai filtri, e conserva vista/filtri correnti. Si naviga senza server o connessione. Per importare Excel e gestire i progetti usare l'applicativo. La stampa delle schede remediation mostra la pagina corrente, come segnalato nel documento stampato; il CSV include tutte le righe filtrate. I campi CSV interpretabili come formule vengono neutralizzati senza modificare i dati importati.

Per produrre un HTML anche da riga di comando:

```bash
python -m app.export --input percorso/progetto.xlsx --output dist/progetto-offline.html
```

## Azure Container Apps con Azure SQL esistente

L'immagine `ghcr.io/matte13/data-visualization-tool:1.4.5` include Microsoft ODBC Driver 18 e il connettore Azure SQL. Configurazione richiesta: server **dbservertil.database.windows.net**, database **data-visualization-tool-db**, utente **fuddos**; la password va inserita come secret dall'operatore. Il pacchetto non crea server o database SQL.

Per installare e cambiare versione dal portale Azure seguire **[docs/azure-portal.md](docs/azure-portal.md)**: contiene i campi della schermata Container details e i passaggi esatti per **Secrets → azure-sql-password → AZURE_SQL_PASSWORD**. La porta HTTP del container è **8000**. Per rete, template Bicep, Docker locale, aggiornamenti e backup consultare **[docs/deployment.md](docs/deployment.md)**.

Per avviare lo stesso container in Docker, collegato al database esistente:

```bash
python scripts/init-env.py --user fuddos
docker compose --env-file .env.azuresql -f compose.azuresql.yaml up -d --build
```

Lo script chiede la password nel terminale senza visualizzarla. Salva solo in file locali ignorati da Git; non genera credenziali per il database esistente. Aprire **http://localhost:8000** da una rete che possa raggiungere Azure SQL. Il server usa TLS con verifica del certificato e non ripiega su file se SQL non è disponibile. Progetti e originali Excel persistono nel database anche dopo un cambio di immagine.

Il template Azure crea app, ambiente interno, log e DNS su una VNet/subnet esistente collegata ad Azure SQL. Non modifica database, utenti SQL o firewall. Il collegamento al database aziendale deve essere configurato dall'operatore; non è stato effettuato durante la preparazione del pacchetto.

Il push di un tag Git come `v1.4.5` avvia i test e la pubblicazione GHCR con tag `1.4.5`. Le versioni stabili aggiornano anche `latest`; per installazioni e rollback usare il tag di versione. Il workflow include test su SQL Server compatibile con Azure SQL, senza accedere al database aziendale, e allega il pacchetto di installazione. È disponibile anche **Actions → Publish GitHub Container Registry image → Run workflow**.

`python scripts/package-release.py` genera l'archivio installabile e il checksum, escludendo Excel, password e dati delle demo. La modalità desktop `python -m app.server` e `compose.yaml` conservano l'uso locale su file senza database esterno. La versione `1.0.0` e i relativi file PostgreSQL restano disponibili per compatibilità; questa installazione usa Azure SQL.

## Test

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.cjs
```

Node 18+ è necessario soltanto per i test delle logiche JavaScript. I workbook dei test sono generati da [tests/fixtures.py](tests/fixtures.py) con nomi e importi fittizi: il codice e la CI funzionano senza Excel dei clienti. I controlli coprono importazione, gruppi di entità diversi, cache/totali, filtri, valori mancanti/zero, CSV, persistenza multi-progetto e controlli HTTP.

Test browser opzionale con Chromium e Playwright:

```bash
python -m pip install -r requirements-dev.txt
# Se Chromium non è già installato, installarlo con il sistema operativo.
# CHROMIUM_PATH può indicare un eseguibile alternativo.
python tests/ui_smoke.py
```

Il test UI usa solo store temporanei e dati fittizi. La navigazione diretta a URL `file://` può essere bloccata dalle policy del browser gestito: il test verifica il contenuto HTML autosufficiente con richieste esterne bloccate. Non viene eseguito un deployment.

La vista **Mappa per Risk Type**, subito dopo **Mappa rischi e investimenti**, offre il percorso **Anno → Risk Type → Remediation → Impact Type → Capex/Opex**, senza il livello dominio. Mantiene filtri e budget condivisi, navigazione da tastiera, dettaglio con doppio click e percorso selezionato nella copia HTML offline. I due percorsi di esplorazione restano indipendenti.
