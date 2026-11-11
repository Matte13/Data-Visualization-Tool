# Installazione con GitHub Container Registry e Azure SQL esistente

Configurazione del progetto: server **dbservertil.database.windows.net**, database **data-visualization-tool-db**, utente SQL **fuddos**. L'operatore inserisce successivamente la password. Il pacchetto non crea database né utenti e non accede al database aziendale durante build o test.

## Installazione dal portale

Seguire [azure-portal.md](azure-portal.md): include Image and tag, porta 8000, valori delle variabili e i passaggi **Container App → Settings → Secrets → azure-sql-password**, poi **Containers → Environment variables → AZURE_SQL_PASSWORD → Secret reference**.

L'immagine GHCR versionata include Python 3.12, Microsoft ODBC Driver 18 e pyodbc. Usa UID 10001 e non contiene Excel, dati di progetti o credenziali. Tutti i calcoli restano deterministici e indipendenti da servizi AI.

## Connessione e permessi sul database

Le connessioni usano TLS con **Encrypt=yes** e **TrustServerCertificate=no**. La Container App deve raggiungere il server esistente secondo la rete aziendale, tramite private endpoint/routing/DNS oppure le regole già approvate per quel server. Il template non apre il firewall SQL, non abilita l'accesso pubblico e non crea nuovi server.

Il login SQL esistente deve essere mappato al database e autorizzato. L'app inizializza soltanto queste tabelle, nello schema configurato (default `dbo`):

- `dvt_projects`: progetti, Excel attuale e prima importazione, nomi e date.
- `dvt_library_state`: riferimento al progetto attivo.

Per la prima inizializzazione servono CREATE TABLE nel database e ALTER/REFERENCES sullo schema. In alternativa un DBA può predisporre una volta le tabelle come segue: usare un account con i privilegi di inizializzazione per avviare il tool sul database scelto, poi limitare il login applicativo a **SELECT, INSERT, UPDATE** sulle due tabelle. L'app controlla se le tabelle esistono e non le ricrea. Per separare l'app dagli altri oggetti, il DBA può predisporre uno schema dedicato e impostare `AZURE_SQL_SCHEMA` di conseguenza. La serializzazione usa `sys.sp_getapplock` con lock di transazione nel database corrente.

I progetti di installazioni locali/PostgreSQL precedenti non vengono trasferiti automaticamente: importarli dai rispettivi Excel originali. Nessun file locale viene caricato di nascosto nel database SQL esistente. La libreria è condivisa fra gli utenti autorizzati all'app; il database non introduce da solo autenticazione individuale nell'interfaccia.

## Aggiornamento alla 1.4.8 e logiche di classificazione

Per i progetti già salvati con l'Excel originale è sufficiente aggiornare l'immagine alla 1.4.8 e riavviare l'app. Non occorre importare nuovamente il file. Il processo rilegge i workbook conservati e calcola la classificazione senza cambiare sorgenti, ID, date o contenuti dei progetti nel database.

La classificazione è disponibile con le intestazioni semantiche OT / local business / local complete oppure con il profilo numerico originale approvato: i cinque gruppi C=6, D=8, E=13, F=5 e G=9 (o Europa AI ACT 9), cardinalità delle X coerenti, 21 entità, OT comprese nelle Complete e Complete/Business disgiunte ed esaustive. Risultano 6 Complete con OT, 7 senza OT e 8 Business. Il riconoscimento non usa i nomi delle country; altri formati numerici validi rimangono senza classificazione.

Gli importi restano quelli salvati nelle righe di Remediations e OT. I calcoli di confronto annotati in LE_List non sono nuove remediation e non vengono sommati ai budget.

Le regole su importi unitari, totali estesi, delta OT, gruppi specifici e residui non attribuiti sono spiegate nelle [note della versione](release-notes.md#logiche-di-calcolo). Lo schema Excel dettagliato è in [workbook-format.md](workbook-format.md). La nuova classificazione non richiede la creazione di un altro database.

## Docker locale, collegato allo stesso Azure SQL

Prerequisiti: Docker Desktop/Engine con Compose V2, Python 3.12+ e rete abilitata al server SQL. Il database resta quello esistente; viene avviato un solo container applicativo.

```bash
python scripts/init-env.py --user fuddos
docker compose --env-file .env.azuresql -f compose.azuresql.yaml up -d --build
```

Il primo comando chiede la password nel terminale senza mostrarla. Scrive `.env.azuresql` e `deploy/secrets/azure_sql_password`, ignorati da Git, senza generare credenziali nuove e senza sovrascrivere configurazioni esistenti. La password resta fuori dal file `.env.azuresql`. Su Windows proteggere la cartella con i permessi dell'utente autorizzato.

Aprire **http://localhost:8000**. L'immagine pubblicata può essere usata con `docker compose --env-file .env.azuresql -f compose.azuresql.yaml pull`, poi `up -d --no-build`. Per cambiare versione aggiornare `DVT_IMAGE` nel file `.env.azuresql`. Per fermare l'app usare `down`: i dati sono nel database SQL e non nel container.

Per sviluppo desktop senza database usare `python -m app.server`: se non sono presenti parametri SQL, l'archivio rimane su file in `runtime/`. L'immagine container richiede invece Azure SQL per default e si arresta se manca la configurazione. `compose.yaml` seleziona esplicitamente il backend locale. In modalità Azure SQL eventuali errori impediscono la persistenza; non viene usato un archivio alternativo.

## Template Azure Container Apps

`infra/azure/main.bicep` crea soltanto Container App, ambiente interno, Log Analytics e DNS privato dell'app. Usa **VNet e subnet Container Apps già esistenti**, collegate al server SQL. Non contiene risorse Microsoft.Sql o PostgreSQL.

Prerequisiti: Azure CLI/Bicep, login nella subscription corretta e permessi App/Network/Log Analytics. La subnet deve essere dedicata, delegata a `Microsoft.App/environments`, con dimensioni compatibili con un ambiente workload profiles (almeno /27; /23 se richiesto dal dimensionamento aziendale). La rete deve risolvere i DNS privati dell'app e del database. Il template usa un load balancer interno: l'URL dell'app richiede VPN, peering, VDI o accesso dalla rete autorizzata. L'identità/SSO dell'app va integrata con l'infrastruttura aziendale prima di ampliarvi l'accesso.

Preparare la password SQL esistente in un file privato, senza inserirla nei comandi o nel repository, poi configurare da Bash/WSL/Azure Cloud Shell:

```bash
export AZURE_SUBSCRIPTION_ID='ID-SUBSCRIPTION'
export AZURE_RESOURCE_GROUP='rg-data-visualization-tool'
export AZURE_LOCATION='westeurope'
export DVT_PREFIX='dvt-azienda'
export DVT_IMAGE='ghcr.io/matte13/data-visualization-tool:1.4.8'
export AZURE_SQL_SERVER='dbservertil.database.windows.net'
export AZURE_SQL_DATABASE='data-visualization-tool-db'
export AZURE_SQL_USER='fuddos'
export AZURE_SQL_PASSWORD_FILE='/percorso/privato/password-sql'
export AZURE_VNET_ID='/subscriptions/ID/resourceGroups/NETWORK_RG/providers/Microsoft.Network/virtualNetworks/VNET'
export AZURE_INFRASTRUCTURE_SUBNET_ID='/subscriptions/ID/resourceGroups/NETWORK_RG/providers/Microsoft.Network/virtualNetworks/VNET/subnets/CONTAINER_APPS'
```

Eseguire `bash scripts/deploy-azure.sh --plan` su un resource group esistente per il what-if. `bash scripts/deploy-azure.sh --apply` crea il resource group se manca e distribuisce l'app. Le risorse App/Network/Log Analytics hanno i normali costi Azure; il database esistente mantiene la propria configurazione.

Lo script verifica la subscription attiva, legge il secret da file, crea parametri temporanei privati e li elimina al termine. Non esegue login, non cambia subscription e non scrive password negli argomenti del processo. Per immagini GHCR private usare anche `GHCR_USERNAME` e `GHCR_TOKEN_FILE` con un token di sola lettura Packages. `parameters.example.json` è solo un esempio privo di password, non un deployment completo.

## Versioni, disponibilità e backup

Il push di `v1.4.8` avvia **Publish GitHub Container Registry image**, che esegue prima i test Python, JavaScript e SQL Server/ODBC, poi pubblica `ghcr.io/matte13/data-visualization-tool:1.4.8`, `sha-<commit>` e per le versioni stabili `latest`. La pubblicazione manuale è disponibile nelle Actions. L'archivio e il checksum sono negli artifact della run. La normale push del codice esegue i test e non pubblica immagini.

Non spostare un tag di versione già installato. Per aggiornare il portale cambiare il tag mantenendo la configurazione di connessione. Un digest `@sha256:...` identifica esattamente l'immagine. Le versioni `1.0.x` non supportano Azure SQL. Per tornare da 1.2.x a 1.1.2 seguire la procedura seguente: il formato dei workbook salvati nella libreria fa parte della compatibilità del ripristino.

`/api/health` verifica il processo e dichiara il backend `azuresql`; `/api/ready` verifica anche SQL. In caso di indisponibilità del database la readiness restituisce 503. Ogni operazione aggiorna la cache all'interno di una transazione con lock, per non sovrascrivere progetti durante il cambio di revisione. Il dimensionamento iniziale rimane una replica; questo meccanismo non sostituisce una valutazione di carico.

I progetti e gli Excel originali restano nel database Azure SQL. Backup, conservazione e ripristino point-in-time seguono le impostazioni già adottate per quel database; verificarle con il DBA e provare il ripristino su un database separato. Il tool non modifica le politiche di backup esistenti.

## Salvataggio della libreria e rollback alla 1.1.2

Un tag conserva il software di quella versione. Gli Excel caricati e lo stato della libreria restano invece nel database. La 1.4.8 riconosce il profilo originale senza riscriverlo: se la libreria contiene solo workbook già compatibili con la 1.1.2, questo riconoscimento non richiede un ripristino dei dati per tornare al software precedente. Dopo aver caricato file con le nuove intestazioni, invece, la 1.1.2 potrebbe non riuscire a leggerli: in quel caso occorre ripristinare uno snapshot compatibile prima di cambiare immagine.

Lo strumento `app.library_backup`, disponibile dalla 1.2.0, esporta e ripristina la libreria completa: tutti i progetti, i file Excel attuali e della prima importazione, nomi, date e progetto attivo. Lo snapshot ha un digest di integrità e contiene dati riservati dei progetti, senza credenziali di connessione. Conservarlo fuori dal repository e dai pacchetti pubblici, in un percorso privato autorizzato. Il file viene creato con permessi 0600 ove supportati; su Windows applicare anche i permessi della cartella. Lo snapshot non può superare 256 MiB; per librerie più grandi concordare il backup del database con il DBA.

Usare gli strumenti della versione corrente (1.4.8) su una postazione o un container amministrativo che abbia rete, driver e **le stesse variabili di connessione** dell'installazione. Per Azure SQL sono necessari Microsoft ODBC Driver 18, `requirements-azuresql.txt` e la configurazione `AZURE_SQL_*`; il secret può essere letto tramite `AZURE_SQL_PASSWORD_FILE`. Le credenziali non vanno inserite negli argomenti dei comandi. Per l'archivio locale eseguire i comandi dalla stessa installazione che contiene `runtime/`.

### Prima di importare un formato diverso

Questa procedura serve quando si decide di caricare un formato diverso. Per aggiornare i progetti salvati con l'Excel originale alla 1.4.8 non è richiesta una nuova importazione.

1. Avviare il codice 1.4.8 lasciando ancora nella libreria i workbook precedenti.
2. Esportare uno snapshot in un percorso privato già disponibile, diverso a ogni salvataggio:

```bash
python -m app.library_backup export --output /percorso/privato/prima-1.2.json --require-legacy-compatible
python -m app.library_backup inspect --input /percorso/privato/prima-1.2.json
```

L'opzione `--require-legacy-compatible` richiede che **sia il file corrente sia quello della prima importazione di ogni progetto** usino il tracciato supportato dalla 1.1.2. Se il controllo non passa, non considerare quello snapshot un punto di ritorno alla 1.1.2. Recuperare uno stato precedente compatibile con l'operatore/DBA. Il comando di esportazione non sovrascrive un file esistente e richiede che la cartella di destinazione sia già presente. `inspect` legge lo snapshot senza collegarsi al database e riporta il numero di progetti e la compatibilità del contenuto.

Solo dopo aver conservato e controllato lo snapshot importare l'Excel con le nuove intestazioni. Un export della libreria è distinto dal download del solo Excel del progetto aperto.

### Ripristino dello stato precedente

Fermare l'app e tutte le revisioni/processi che possono modificare la stessa libreria. Eseguire il ripristino da una postazione o un container amministrativo separato, usando il codice 1.4.8. Salvare prima anche lo stato corrente se deve essere recuperabile in seguito:

```bash
python -m app.library_backup export --output /percorso/privato/prima-del-rollback.json
python -m app.library_backup restore --input /percorso/privato/prima-1.2.json --require-legacy-compatible
```

Il ripristino **sostituisce l'intera libreria con lo snapshot**. Le modifiche successive vengono annullate e i progetti aggiunti dopo quel salvataggio vengono rimossi. Digest, contenuti Excel, prime importazioni e compatibilità vengono controllati prima delle scritture. Su Azure SQL l'operazione usa una transazione con il lock della libreria; per il ripristino il login deve avere anche DELETE sulle due tabelle applicative. Il normale utilizzo dell'app non richiede questo permesso aggiuntivo.

Al termine selezionare in Azure l'immagine `ghcr.io/matte13/data-visualization-tool:1.1.2`, mantenere le variabili SQL e il secret, distribuire la revisione e verificarne readiness, progetti e budget. Per l'archivio locale il salvataggio viene sostituito in modo atomico; gli altri processi devono comunque rimanere fermi durante il ripristino.

Questa utility non cambia i backup gestiti del database. Restano validi la conservazione e il ripristino point-in-time concordati con il DBA; verificarli anche per il caso in cui uno snapshot applicativo non sia disponibile. Il pacchetto non esegue automaticamente alcun ripristino sul database aziendale.

## Pacchetto e verifiche

`python scripts/package-release.py` genera `dist/data-visualization-tool-deploy.zip` e il checksum SHA-256, includendo codice, risorse grafiche approvate, licenze, configurazione e istruzioni. Esclude Excel, runtime, `.env*` operativi, password e allegati originali. La versione precedente conserva i file PostgreSQL per compatibilità: le istruzioni di questa versione usano **compose.azuresql.yaml**, il backend **azuresql** e il database SQL esistente.

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.test.cjs
```

I test Azure SQL compatibili girano in CI su un SQL Server di test dedicato con Microsoft ODBC 18: verificano progetti, reset, riavvio, transazioni, scritture concorrenti e readiness. Usano schemi temporanei e dati fittizi, mai `dbservertil`. La compilazione Bicep verifica sintassi e tipi; la connessione effettiva al database aziendale richiede password e rete dell'operatore e non viene certificata dai test di compatibilità.
