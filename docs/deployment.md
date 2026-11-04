# Installazione GitHub Container Registry, PostgreSQL e Azure Container Apps

Il pacchetto contiene l'applicativo completo, le due mappe navigabili e l'export PowerPoint, senza Excel dei clienti né credenziali. L'immagine è Linux AMD64, usa Python 3.12 e l'utente non privilegiato UID 10001. Tutte le elaborazioni dei dati restano deterministiche: nessun servizio AI o API esterna.

## 1. Avvio con Docker e PostgreSQL

Prerequisiti: Docker Desktop o Docker Engine con Compose V2, Python 3.12+. Estrarre il pacchetto e aprire il terminale nella cartella `data-visualization-tool` (oppure clonare il repository).

```bash
python scripts/init-env.py
docker compose -f compose.postgres.yaml up -d --build
docker compose -f compose.postgres.yaml ps
```

Aprire **http://localhost:8000** e creare il primo progetto caricando l'Excel. In PowerShell i comandi sono gli stessi. L'immagine non contiene workbook di esempio o dati delle precedenti demo.

La configurazione genera `.env` e un file password privato in `deploy/secrets/postgres_password`, senza stampare la password. Non sovrascrive una configurazione esistente. La password non va inserita nella URL del database; l'app e PostgreSQL la leggono dal file montato come secret. Su Windows conservare la cartella in un percorso accessibile soltanto agli operatori autorizzati.

L'app è pubblicata solo su `127.0.0.1`; PostgreSQL non espone porte all'host. I progetti, gli Excel originali e le prime importazioni persistono nel volume `postgres-data`. `REQUIRE_POSTGRES=true` impedisce un ripiego involontario sul filesystem se manca la configurazione del database.

```bash
# Arresto senza cancellare i dati
docker compose -f compose.postgres.yaml down
# Riavvio dello stesso archivio
docker compose -f compose.postgres.yaml up -d
```

Non usare `down -v` sull'installazione che contiene dati da conservare. Cambiare una password nel file non cambia quella già memorizzata da PostgreSQL: la rotazione deve aggiornare prima il ruolo nel database e poi il secret, seguendo la procedura aziendale.

`compose.yaml` rimane disponibile per l'uso locale precedente con persistenza su file. Per l'installazione PostgreSQL usare esplicitamente `compose.postgres.yaml`.

## 2. Pubblicazione nel registry GitHub (GHCR)

Codice e configurazione restano nel repository GitHub. L'immagine per Azure viene pubblicata su **GitHub Container Registry (GHCR)**.

Eseguire **Actions → Publish GitHub Container Registry image → Run workflow**, indicando un tag come `1.0.0`. Il workflow usa il `GITHUB_TOKEN` temporaneo con permesso `packages:write`; non richiede un token personale per pubblicare. Per questo repository la destinazione è `ghcr.io/matte13/data-visualization-tool:1.0.0`.

Anche il push di un tag Git `v1.0.0` avvia il workflow e genera l'immagine `1.0.0`; le versioni stabili aggiornano anche `latest`. Il workflow esegue prima i test Python, JavaScript, PostgreSQL e dello stack container: se falliscono, l'immagine non viene pubblicata. Il push normale del codice non pubblica immagini. Ogni immagine ha anche un tag `sha-<commit completo>`. Il pacchetto compare nella sezione **Packages** di GitHub: controllarne visibilità, collegamento al repository e permessi dell'organizzazione. Non viene reso pubblico dal workflow.

Per pubblicare le versioni successive dal commit già verificato e caricato:

```bash
git tag v1.0.1
git push origin v1.0.1
```

Usare una nuova versione per ogni aggiornamento; non spostare i tag già installati. Attendere che il workflow risulti completato prima di usare il nuovo tag in Azure.

Per pubblicare manualmente, usare un token GitHub con i permessi necessari per Packages e inserirlo nel prompt, senza salvarlo nel repository:

```bash
docker login ghcr.io --username IL_TUO_UTENTE_GITHUB
docker build --build-arg APP_VERSION=1.0.0 -t ghcr.io/IL_TUO_NAMESPACE/data-visualization-tool:1.0.0 .
docker push ghcr.io/IL_TUO_NAMESPACE/data-visualization-tool:1.0.0
```

Per installare l'immagine pubblicata, generare la configurazione come nel punto 1 e impostare in `.env` (namespace in minuscolo):

```dotenv
DVT_IMAGE=ghcr.io/il_tuo_namespace/data-visualization-tool:1.0.0
```

```bash
docker login ghcr.io
docker compose -f compose.postgres.yaml pull
docker compose -f compose.postgres.yaml up -d --no-build
```

Se il package è privato, Docker Desktop e Azure devono avere accesso in lettura a GHCR. Per Azure usare un token GitHub autorizzato con `read:packages`, conservato nel file segreto indicato sotto; autorizzare anche l'eventuale SSO dell'organizzazione. Il token usato da Azure è distinto dal `GITHUB_TOKEN` temporaneo del workflow.

Usare tag di release o digest per installazioni e rollback ripetibili. Un digest `@sha256:...` identifica esattamente l'immagine; i tag possono essere sovrascritti da chi ha accesso al registry.

## 3. Azure Container Apps e PostgreSQL gestito

Per inserire l'immagine direttamente nella schermata del portale Azure, consultare **[Installazione dal portale Azure](azure-portal.md)**. La guida indica i campi per GHCR, tag di versione, variabili PostgreSQL e probe; il solo nome dell'immagine non crea il database.

`infra/azure/main.bicep` crea nel resource group scelto:

- VNet con subnet separate per Container Apps e PostgreSQL.
- Ambiente Container Apps con **load balancer interno**, DNS privato e ingresso HTTPS sulla porta 8000.
- Azure Database for PostgreSQL Flexible Server 16, database `remediation`, rete pubblica disabilitata e backup gestiti.
- App con immagine GitHub Container Registry, secret del database e registry privato opzionale, replica minima/massima 1 e revisioni in modalità Single.
- Log Analytics e probe distinti per avvio, liveness e readiness.

L'ingress dell'app usa `external=true` per essere raggiungibile dai client nella VNet, ma **l'ambiente ha `internal=true`: non viene creato un accesso Internet pubblico**. Serve un collegamento alla rete aziendale tramite VPN, peering, VDI o altra rete privata, con risoluzione dei DNS privati Azure. Il pacchetto crea una nuova VNet: il collegamento a una rete aziendale esistente va configurato dall'operatore di rete. Scegliere prefissi IP non sovrapposti; quelli nel template sono esempi modificabili.

Questa distribuzione limita l'accesso tramite rete, non implementa autenticazione individuale o ruoli applicativi. Per un'identità utente Entra ID o politiche di accesso più dettagliate integrare il gateway/SSO aziendale prima di allargare l'accesso. Non trasformare l'ambiente in pubblico senza questa configurazione.

Prerequisiti: Azure CLI con supporto Bicep, login Azure dell'operatore, subscription corretta e permessi per risorse App/Network/PostgreSQL/Log Analytics. Provider da registrare nella subscription secondo le regole aziendali: `Microsoft.App`, `Microsoft.Network`, `Microsoft.DBforPostgreSQL`, `Microsoft.OperationalInsights`. Le risorse create con `--apply` comportano costi Azure; lo SKU B1ms è un punto di partenza, non un dimensionamento definitivo.

Preparare una password in un file privato, senza scriverla nei comandi o nel repository. La password deve rispettare i requisiti di Azure PostgreSQL. Per una nuova installazione si può generare un file dedicato:

```bash
python -c "from pathlib import Path; import secrets; p=Path('deploy/secrets/azure_postgres_password'); p.parent.mkdir(parents=True, exist_ok=True); f=p.open('x'); f.write('Aa1!'+secrets.token_urlsafe(36)); f.close(); p.chmod(0o600)"
```

Da Bash/WSL/Azure Cloud Shell, configurare i valori dell'installazione:

```bash
export AZURE_SUBSCRIPTION_ID='ID-DELLA-SUBSCRIPTION'
export AZURE_RESOURCE_GROUP='rg-data-visualization-tool'
export AZURE_LOCATION='westeurope'
export DVT_PREFIX='dvt-azienda'
export DVT_IMAGE='ghcr.io/il_tuo_namespace/data-visualization-tool:1.0.0'
export AZURE_POSTGRES_PASSWORD_FILE="$PWD/deploy/secrets/azure_postgres_password"
# Opzionali per un'immagine privata GitHub Container Registry:
export GHCR_USERNAME='IL_TUO_UTENTE'
export GHCR_TOKEN_FILE='/percorso/privato/ghcr-token'
```

Il file token deve contenere il token di lettura del registry (può essere diverso dal token di pubblicazione). Eseguire prima la simulazione su un resource group già esistente:

```bash
bash scripts/deploy-azure.sh --plan
```

Per creare il resource group se manca e applicare il template:

```bash
bash scripts/deploy-azure.sh --apply
```

Lo script verifica la subscription attiva e non esegue login né cambia account implicitamente. I segreti vengono letti da file e passati ad Azure tramite un file temporaneo con permessi privati, eliminato al termine; non compaiono negli argomenti del processo. L'output include l'URL **privato** dell'app, la VNet e il server PostgreSQL, senza password. `infra/azure/parameters.example.json` mostra soltanto i parametri non segreti; non è una configurazione completa da distribuire da sola.

La connessione app → database usa `sslmode=verify-full` con il bundle CA del container. `ALLOWED_HOSTS` viene impostato sul vero FQDN dell'app; eventuali hostname aggiuntivi vanno dichiarati esplicitamente. I probe impostano `Host: localhost` per rispettare la validazione degli host.

Il template iniziale usa il login amministrativo PostgreSQL per inizializzare lo schema. Per installazioni aziendali con separazione dei privilegi, creare un ruolo applicativo con accesso al solo database/schema dell'app e aggiornare `PGUSER`/secret dopo l'inizializzazione. L'app crea soltanto le proprie tabelle; non elimina database o tabelle esistenti.

## 4. Aggiornamenti, salute e backup

Per Docker, pubblicare un nuovo tag, cambiare `DVT_IMAGE` in `.env`, poi eseguire `pull` e `up -d --no-build`. Il volume del database resta invariato. Per Azure, rieseguire il template con un nuovo tag/digest e gli stessi parametri/password: non scegliere un nuovo prefisso per aggiornare un'installazione esistente. Per il rollback ripristinare il tag/digest precedente, verificando la compatibilità dello schema prima di tornare a versioni più vecchie.

`/api/health` controlla il processo; `/api/ready` verifica anche PostgreSQL e restituisce 503 se non è raggiungibile. Una perdita del database non attiva una persistenza locale alternativa. Le operazioni PostgreSQL ricaricano lo stato in transazione con un lock del database, evitando sovrascritture fra processi durante i cambi di revisione; non usare questo meccanismo come un'indicazione di scalabilità illimitata. Il template mantiene una singola replica e i progetti costituiscono una libreria condivisa fra gli utenti autorizzati.

Per Docker creare e verificare periodicamente un dump:

```bash
docker compose -f compose.postgres.yaml exec -T db pg_dump -U explorer -d remediation -Fc > remediation-backup.dump
```

Conservare dump ed Excel secondo le procedure aziendali, fuori dal repository. Prima del ripristino fermare l'app e provare il backup su un database separato. Su Azure usare i backup e il ripristino point-in-time di Flexible Server, verificando regolarmente la procedura.

## 5. Pacchetto e verifiche

```bash
python scripts/package-release.py
```

Genera `dist/data-visualization-tool-deploy.zip` e il checksum `.sha256` con un elenco esplicito dei file ammessi. Il pacchetto non include `.env`, password, runtime, dump, Excel caricati, audio, documenti di riunione o slide originali dei template. Include le risorse di stile già approvate necessarie all'export PPT.

Verifiche disponibili:

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/*.test.cjs
# In CI o con un PostgreSQL di test (schema temporaneo dedicato):
TEST_DATABASE_URL='postgresql://utente:password@localhost:5432/database_test' python -m unittest discover -s tests -p 'test_postgres_integration.py' -v
```

La build Docker, lo stack Compose e i test PostgreSQL sono verificabili localmente senza creare risorse Azure. La compilazione Bicep verifica sintassi e tipi, non sostituisce un deployment di prova in una subscription. La pubblicazione reale su GitHub Container Registry e il deployment Azure richiedono gli account e i permessi dell'operatore.
