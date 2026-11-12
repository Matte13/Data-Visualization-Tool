# Installazione dal portale Azure con Azure SQL

Usare l'immagine **ghcr.io/matte13/data-visualization-tool:1.4.15**, collegata al database Azure SQL già disponibile. Non occorre creare un nuovo database. La versione `1.0.0` precede il supporto Azure SQL.

**Progetti già salvati:** per l'Excel originale basta cambiare il tag dell'immagine e riavviare. Non occorre ricaricare il file: la 1.4.15 rilegge i workbook conservati, riconosce il profilo numerico originale validato e calcola le categorie senza modificare gli originali o lo stato dei progetti nel database.

Se si decide in seguito di importare un file con nuove intestazioni, salvare prima uno snapshot completo compatibile con la 1.1.2 seguendo la [procedura di salvataggio e rollback](deployment.md#salvataggio-della-libreria-e-rollback-alla-112). Le [note 1.4.15](release-notes.md) spiegano il profilo riconosciuto, le logiche di calcolo e la compatibilità dei file.

## 1. Container details

| Campo | Valore |
| --- | --- |
| Name | `data-visualization-tool` |
| Image source | **Docker Hub or other registries** (include GHCR) |
| Image type | **Public** se il package GHCR è pubblico |
| Registry login server | `ghcr.io` |
| Image and tag | `ghcr.io/matte13/data-visualization-tool:1.4.15` |
| Command override | Vuoto |
| Arguments override | Vuoto |

Se repository e tag sono separati, usare repository `matte13/data-visualization-tool` e tag `1.4.15`. L'immagine Linux AMD64 include il driver Microsoft ODBC 18. Come base assegnare **0,5 vCPU / 1 GiB** e una sola replica, in modalità revisioni **Single**.

Abilitare l'ingress HTTP con porta di destinazione **8000**, HTTPS e accesso dalla rete aziendale. Scegliere un ambiente Container Apps che possa raggiungere il server Azure SQL esistente: risoluzione DNS, routing e firewall devono consentire il collegamento. Il template Bicep usa una VNet/subnet già esistente; non cambia le regole del database.

## 2. Dove inserire la password

La password richiesta è quella **già valida per l'utente SQL fuddos**. Le credenziali eventualmente generate per PostgreSQL non valgono per questo server.

1. Aprire nel portale Azure la **Container App** appena creata o da aggiornare.
2. Nel menu della Container App aprire **Settings → Secrets** (in italiano **Impostazioni → Segreti**).
3. Selezionare **Add / Aggiungi**. Nome: **azure-sql-password**. Tipo: **Manual**. Nel campo **Secret value / Valore segreto** incollare la password SQL esistente e salvare.
4. Aprire **Containers → Edit and deploy / Modifica e distribuisci**, scegliere il container del tool e la sezione **Environment variables / Variabili di ambiente**.
5. Aggiungere **AZURE_SQL_PASSWORD**, scegliere come origine del valore **Reference a secret / Riferimento a un segreto** e selezionare **azure-sql-password**. Non inserirla come variabile di testo normale.
6. Compilare anche le variabili della tabella seguente e distribuire la nuova revisione.

Se la procedura iniziale di creazione mostra già Secrets e variabili di ambiente, è possibile impostarle nello stesso passaggio. L'app deve avere la configurazione completa prima che la revisione possa risultare pronta. La password non va inserita nell'immagine, in Image and tag, nel repository o nella chat.

## 3. Variabili di ambiente

| Nome | Valore / origine |
| --- | --- |
| `STORAGE_BACKEND` | `azuresql` |
| `AZURE_SQL_SERVER` | `dbservertil.database.windows.net` |
| `AZURE_SQL_PORT` | `1433` |
| `AZURE_SQL_DATABASE` | `data-visualization-tool-db` |
| `AZURE_SQL_USER` | `fuddos` |
| `AZURE_SQL_SCHEMA` | `dbo` (oppure schema dedicato già predisposto dal DBA) |
| `AZURE_SQL_PASSWORD` | **Secret reference → azure-sql-password** |
| `ALLOWED_HOSTS` | FQDN completo della Container App, senza `https://` o percorsi |

Per più hostname usare una virgola. Rimuovere eventuali variabili `PG*`, `DATABASE_URL`, `DATABASE_URL_FILE` e `REQUIRE_POSTGRES` dalle revisioni precedenti: non fanno parte di questa configurazione. Non impostare `AZURE_SQL_TRUST_SERVER_CERTIFICATE`: per Azure la verifica del certificato è attiva e la connessione è cifrata.

Il login `fuddos` deve essere autorizzato al database. L'app inizializza soltanto `dbo.dvt_projects` e `dbo.dvt_library_state`; non crea database, login o altri schemi. Per predisporre le tabelle con un amministratore e poi usare permessi limitati, consultare [deployment.md](deployment.md).

## 4. Verificare l'avvio

Configurare probe HTTP, porta `8000`, header **Host: localhost**:

| Tipo | Percorso | Impostazione iniziale |
| --- | --- | --- |
| Startup | `/api/ready` | Ritardo 5 s, intervallo 5 s, timeout 6 s, 30 tentativi |
| Readiness | `/api/ready` | Intervallo 10 s, timeout 6 s, 3 tentativi |
| Liveness | `/api/health` | Intervallo 30 s, timeout 5 s, 3 tentativi |

Attendere una revisione pronta, aprire l'URL dalla rete aziendale e selezionare il progetto già salvato. Alla prima installazione creare un progetto caricando il relativo Excel. `/api/health` indica `storage: azuresql`; `/api/ready` verifica l'accesso al database. Se il database non è disponibile, l'app non salva sul filesystem temporaneo.

Se l'avvio fallisce, verificare: password e mapping del secret, accesso di `fuddos` al database, permessi sulle due tabelle, DNS e firewall/rete. I messaggi applicativi non contengono password o stringhe di connessione.

## 5. Aggiornare il tag

1. Verificare che la nuova versione sia pubblicata in GHCR e che il relativo workflow GitHub sia concluso.
2. In **Containers → Edit and deploy** impostare **Image and tag** su `ghcr.io/matte13/data-visualization-tool:1.4.15`.
3. Conservare tutte le variabili, il secret e lo stesso database. Distribuire la revisione e attenderne la readiness. Aprire il progetto salvato e verificare la composizione del budget; il file originale non deve essere importato nuovamente.

Gli aggiornamenti del container conservano i progetti nel database. Per installazioni ripetibili usare una versione specifica anziché `latest`. Per il rollback verificare la compatibilità dello schema prima di selezionare l'immagine precedente. Le versioni `1.0.x` non gestiscono questa persistenza Azure SQL.

Per pubblicare una versione, dal commit già caricato eseguire `git tag v1.4.15` e `git push origin v1.4.15`, oppure usare **Actions → Publish GitHub Container Registry image → Run workflow**. Il workflow esegue prima tutti i controlli. Il package deve essere pubblico per l'opzione Public; se è privato scegliere Private e fornire credenziali GHCR con `read:packages`.
