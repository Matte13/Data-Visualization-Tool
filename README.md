# Data Visualization Tool

Applicativo locale per presentare e navigare piani di remediation da Excel. Gestisce **più progetti separati**, ciascuno con il proprio workbook, le proprie country/legal entity, i filtri e i budget. I futuri Excel devono seguire lo stesso tracciato descritto in [docs/workbook-format.md](docs/workbook-format.md).

Tutte le logiche sono offline e deterministiche: nessun modello AI, API esterna, CDN, font remoto o telemetria. Le remediation vengono lette dal file senza suggerimenti, riscritture o correzioni automatiche. Il frontend non richiede Node/npm o un processo di build.

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
- I progetti persistono nella directory locale `runtime/`, ignorata da Git. La modalità PostgreSQL è opzionale. Il workbook originale dell'utente non viene modificato.

L'importazione supporta file `.xlsx` compatibili fino a 10 MB, anche tramite trascinamento nella pagina. Prima di caricare un file modificato ricalcolarlo e salvarlo in Excel o LibreOffice, affinché siano presenti i risultati salvati delle formule. Il tool non esegue formule arbitrarie. Errori di schema, cache assente e incoerenze nei budget vengono mostrati in italiano.

## Viste e filtri

L’interfaccia web usa il logo KPMG del template e la palette aziendale: sfumature **viola `#7213EA` → blu `#1E49E2`** nella navigazione e nelle azioni principali, pannelli chiari per leggere i dati e colori coerenti per anni, domini e budget. Il nome del prodotto resta **Data Visualization Tool**, con indicazione di uso interno.

Titoli, testo e controlli usano i font **KPMG / KPMG Bold già installati sul computer**; Arial è il ripiego quando non sono disponibili. Non vengono scaricati font da Internet. Il repository non redistribuisce né converte in webfont i font desktop incorporati nei template: la loro licenza distingue l’incorporamento nei documenti dall’uso web. Per mantenere la tipografia KPMG anche su computer privi dei font occorre aggiungere un pacchetto webfont aziendale autorizzato. Il foglio `web/brand.css` centralizza questa configurazione e viene incluso anche nella copia HTML offline.

**Panoramica** mostra gli investimenti annuali, per dominio e per owner. Subito sotto, **Mappa Navigabile** esplora anno → dominio → remediation: le frecce rappresentano raggruppamenti, non dipendenze progettuali. **Remediation** presenta schede visive con dominio, owner, anno e budget Global/Local, ricerca, ordinamento e paginazione. **Country / legal entity** associa ogni entità ai suoi investimenti annuali con schede e barre sulla stessa scala; un click sull’anno apre la mappa filtrata per entità e anno.

Tutti i filtri sono **selezionati di default**, incluso OT quando presente. Ogni gruppo (perimetro, anno, dominio, owner, entità, NIS2 e priorità) ha una casella **Seleziona tutti**: attivarla seleziona tutte le voci, disattivarla le esclude tutte. Una selezione vuota mostra zero risultati, mentre una selezione parziale è segnalata dalla casella intermedia. Durante le selezioni la barra laterale conserva posizione, gruppi aperti e focus del cursore.

I colori hanno un significato stabile: lo stesso anno mantiene lo stesso colore nelle diverse viste, i domini sono riconoscibili dai loro colori e Global/Local restano distinti. La precedente sezione “Qualità dei dati” è stata rimossa; gli avvisi necessari per interpretare importi mancanti o attribuzioni incerte restano nel dettaglio delle singole remediation e accanto ai grafici.

Filtri combinabili: perimetro Remediations/OT, anno, dominio, owner, country/legal entity, NIS2, priorità, ricerca e budget locale **positivo / zero / non determinato**. Il selettore Global/Local sceglie gli importi rappresentati, senza eliminare le righe a zero o prive di stima.

I budget Global sono importi di gruppo: non vengono ripartiti o moltiplicati per country. Complete/Business Oriented sono costi unitari; il Local complessivo viene letto dal file. Le attribuzioni per entità derivano esclusivamente dalle formule riconosciute e dai gruppi espliciti di LE_List, non certificano l'applicabilità operativa. Le attribuzioni ambigue restano segnalate e non diventano ripartizioni inventate. ID duplicati e righe senza ID rimangono distinti; celle vuote e zero rimangono distinguibili.

## Presentazione ed esportazioni

Il pulsante **Scarica PowerPoint** in alto esporta una presentazione `.pptx` modificabile di **massimo 15 slide**, rispettando i filtri, le entità e il budget Global/Local selezionati. Dopo la copertina, quattro separatori introducono **Budget → Anni → Country / legal entity → Remediation**. La sintesi mostra investimenti per anno, dominio e owner, fino a tre riepiloghi annuali, due viste country/anno e due slide sulle remediation. I dettagli completi di tutte le righe filtrate, comprese quelle fuori dalla pagina del tool, sono conservati nelle note delle ultime due slide. Importi e testi provengono dal file: non vengono generate nuove remediation.

L’esportazione PowerPoint funziona nell’app locale; la copia HTML autonoma mantiene le altre esportazioni. La presentazione usa grafici, forme e testi modificabili, senza servizi esterni. Il riferimento grafico principale è **Global Cyber Pitch**: formato 16:9, sfondo sfumato viola–blu soltanto per la copertina e i separatori con il solo titolo, sfondo bianco per le slide con i dati, titoli in KPMG Bold e corpo in Arial. Global è viola, Local blu; la stessa codifica compare nelle legende e nei grafici. Ogni slide riprende il footer originale con logo KPMG vettoriale, copyright **2026**, classificazione e numero pagina nelle posizioni del template, bianchi su sfondo sfumato e blu/grigi su bianco.

Per rispettare il limite anche con progetti più grandi, i riepiloghi raggruppano esplicitamente le categorie eccedenti in **Altri**, senza perdere i relativi importi: fino a otto categorie nei grafici budget, tre riepiloghi annuali e 22 righe country in due slide. Se gli anni sono più di tre, il dettaglio mostra i due con maggiore budget e un riepilogo degli altri. Le viste country mostrano fino a cinque colonne annuali, con le altre annualità aggregate. La sintesi remediation presenta i conteggi e le sei voci con il maggiore budget selezionato; l’ordinamento non modifica la priorità del file. Tutti gli anni, le country, i domini e gli owner restano documentati integralmente nelle note dei rispettivi riepiloghi; valori mancanti e zero restano distinti.

Il font KPMG è incorporato nel PowerPoint usando i dati originali del template. PowerPoint è il riferimento per la resa tipografica; altri programmi possono sostituire i font incorporati. Le risorse incluse contengono soltanto il tema, i font incorporabili e il logo del footer: nessuna slide, dato commerciale o nota dei template originali viene distribuita. Sfondi, icone, testi e grafici sono elementi nativi della presentazione.

`Presentazione` nasconde i controlli per screenshot e presentazioni al cliente; Escape esce dalla modalità o chiude un dettaglio. `Esporta` offre CSV delle righe filtrate, Excel sorgente, copia HTML offline e stampa/PDF. La mappa si può salvare in PNG.

La copia HTML è una modalità aggiuntiva di condivisione: contiene **tutti i dati del solo progetto aperto**, compresi quelli nascosti dai filtri, e conserva vista/filtri correnti. Si naviga senza server o connessione. Per importare Excel e gestire i progetti usare l'applicativo. La stampa delle schede remediation mostra la pagina corrente, come segnalato nel documento stampato; il CSV include tutte le righe filtrate. I campi CSV interpretabili come formule vengono neutralizzati senza modificare i dati importati.

Per produrre un HTML anche da riga di comando:

```bash
python -m app.export --input percorso/progetto.xlsx --output dist/progetto-offline.html
```

## Docker e PostgreSQL opzionale

```bash
# Docker Compose >= 2.20; persistenza locale, database non obbligatorio
docker compose up --build
```

La porta pubblicata da Compose è limitata al loopback locale. L'immagine usa un utente non privilegiato; il volume `workbook-state` conserva i progetti. La build richiede connessione, l'applicazione avviata in modalità locale no.

Per PostgreSQL, configurare un `.env` locale (ignorato da Git) con `POSTGRES_PASSWORD` e una `DATABASE_URL` coerente, quindi:

```bash
docker compose --profile postgres up --build
```

Il database Compose usa nome `remediation`, utente `explorer`, host interno `db`, porta 5432. La password deve essere scelta dall'utente; codificare nella URL eventuali caratteri speciali. La porta del DB non è esposta all'host. Per un database esistente, installare `requirements-postgres.txt` e configurare `DATABASE_URL` nell'ambiente. Se impostata, PostgreSQL è obbligatorio: una connessione fallita non provoca un ripiego silenzioso su disco.

Il servizio mantiene dati e progetto attivo in memoria: usare una singola istanza applicativa. Per Azure Container Apps sono disponibili porta 8000, endpoint `/api/health` e configurazione `ALLOWED_HOSTS`/`DATABASE_URL`. Prima dell'accesso remoto servono autenticazione, controllo degli accessi e TLS/ingress tramite la piattaforma. **Docker, PostgreSQL e Azure sono predisposti ma non validati o distribuiti da questa versione.** Nessuna immagine è stata pubblicata su Docker Hub.

## Test

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/model.test.cjs
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
