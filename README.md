# Atlas · Remediation Explorer

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

**Panoramica** mostra investimenti annuali, per dominio e per owner; click sui grafici per approfondire. **Remediation** offre tabella ricercabile, ordinamento, paginazione e dettaglio dei testi originali con riferimento a foglio/riga. **Mappa navigabile** esplora anno → dominio → remediation: le frecce rappresentano raggruppamenti, non dipendenze progettuali. **Country / legal entity** confronta le attribuzioni Local fra le entità. **Qualità dei dati** raccoglie riconciliazione e anomalie della fonte.

Filtri combinabili: perimetro Remediations/OT (se presente), anno, dominio, owner, country/legal entity, NIS2, priorità, ricerca e budget locale **positivo / zero / non determinato**. Il selettore Global/Local sceglie gli importi rappresentati, senza eliminare le righe a zero o prive di stima.

I budget Global sono importi di gruppo: non vengono ripartiti o moltiplicati per country. Complete/Business Oriented sono costi unitari; il Local complessivo viene letto dal file. Le attribuzioni per entità derivano esclusivamente dalle formule riconosciute e dai gruppi espliciti di LE_List, non certificano l'applicabilità operativa. Le attribuzioni ambigue restano segnalate e non diventano ripartizioni inventate. ID duplicati e righe senza ID rimangono distinti; celle vuote e zero rimangono distinguibili.

## Presentazione ed esportazioni

`Presentazione` nasconde i controlli per screenshot e presentazioni al cliente; Escape esce dalla modalità o chiude un dettaglio. `Esporta` offre CSV delle righe filtrate, Excel sorgente, copia HTML offline e stampa/PDF. La mappa si può salvare in PNG.

La copia HTML è una modalità aggiuntiva di condivisione: contiene **tutti i dati del solo progetto aperto**, compresi quelli nascosti dai filtri, e conserva vista/filtri correnti. Si naviga senza server o connessione. Per importare Excel e gestire i progetti usare l'applicativo. La stampa della tabella mostra la pagina corrente, come segnalato nel documento stampato; il CSV include tutte le righe filtrate. I campi CSV interpretabili come formule vengono neutralizzati senza modificare i dati importati.

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
