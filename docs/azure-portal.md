# Installazione dal portale Azure

L'immagine del tool è distribuita tramite GitHub Container Registry. Per ogni aggiornamento cambiare il tag della versione, mantenendo lo stesso database PostgreSQL. Il codice resta nel repository [Matte13/Data-Visualization-Tool](https://github.com/Matte13/Data-Visualization-Tool).

## 1. Pubblicare una versione su GitHub

Dal commit già caricato su GitHub creare un tag di versione:

```bash
git tag v1.0.0
git push origin v1.0.0
```

In **GitHub → Actions → Publish GitHub Container Registry image** attendere la conclusione dei test e della pubblicazione. Il tag Git `v1.0.0` produce `ghcr.io/matte13/data-visualization-tool:1.0.0` e, per una versione stabile, anche `:latest`. Per le successive versioni usare `v1.0.1`, `v1.1.0`, ecc. È disponibile anche **Run workflow** con il numero di versione.

La disponibilità del codice su GitHub non implica che l'immagine sia già pubblicata: verificare che il relativo tag compaia in **Packages → data-visualization-tool**.

Per scegliere **Public** nel portale Azure, il package GHCR deve essere pubblico. Dopo la prima pubblicazione, il proprietario può impostarlo da **Package settings → Change visibility → Public**. Il workflow non modifica la visibilità. L'immagine include il software e le risorse grafiche necessarie, senza Excel, progetti caricati o credenziali. Se il package resta privato, selezionare **Private** in Azure e fornire utente GitHub e token con permesso `read:packages` ed eventuale autorizzazione SSO.

## 2. Compilare “Container details”

Nella schermata mostrata dall'utente inserire:

| Campo | Valore |
| --- | --- |
| Name | `data-visualization-tool` |
| Image source | **Docker Hub or other registries** (include GHCR) |
| Image type | **Public** se il package GHCR è pubblico, altrimenti **Private** |
| Registry login server | `ghcr.io` |
| Image and tag | `ghcr.io/matte13/data-visualization-tool:1.0.0` |
| Command override | Lasciare vuoto |
| Arguments override | Lasciare vuoto |

Se il portale separa ulteriormente repository e tag, usare repository `matte13/data-visualization-tool` e tag `1.0.0`, mantenendo `ghcr.io` come registry.

Impostare **Ingress HTTP**, porta di destinazione **8000** e HTTPS. Come base usare **0,5 vCPU / 1 GiB**, una replica minima e una massima, revisioni **Single**. L'immagine è Linux AMD64 e parte con il comando già incluso.

Per l'uso interno scegliere un ambiente Container Apps con rete privata accessibile dalla rete aziendale. Il template [main.bicep](../infra/azure/main.bicep) crea ambiente, database e DNS privati; le relative istruzioni sono in [deployment.md](deployment.md). Con la creazione manuale verificare il collegamento fra ambiente e rete del database.

## 3. Collegare PostgreSQL

Creare o utilizzare **Azure Database for PostgreSQL Flexible Server 16** e un database dedicato chiamato `remediation`, raggiungibile dall'ambiente Container Apps. Il nome dell'immagine non crea il database: l'app inizializza le proprie tabelle nel database configurato. PostgreSQL conserva i progetti e gli Excel originali; il filesystem temporaneo del container non viene usato come archivio.

In **Container App → Secrets** creare il secret `postgres-password`. In **Containers → Environment variables** impostare:

| Variabile | Valore |
| --- | --- |
| `REQUIRE_POSTGRES` | `true` |
| `PGHOST` | Nome completo del server, es. `server-azienda.postgres.database.azure.com` |
| `PGPORT` | `5432` |
| `PGDATABASE` | `remediation` |
| `PGUSER` | Login PostgreSQL autorizzato a inizializzare e usare le tabelle dell'app |
| `PGPASSWORD` | Tipo **Secret reference**, selezionare `postgres-password` |
| `PGSSLMODE` | `verify-full` |
| `PGSSLROOTCERT` | `/etc/ssl/certs/ca-certificates.crt` |
| `ALLOWED_HOSTS` | Hostname completo della Container App, senza `https://` o percorsi |

Per più hostname (es. dominio personalizzato) separarli con virgole. Non configurare contemporaneamente `DATABASE_URL`: se presente ha precedenza sui parametri `PG*`. Il server e il database devono essere pronti prima di avviare la revisione.

Configurare probe HTTP sulla porta `8000` con header **Host: localhost**:

| Tipo | Percorso | Impostazione iniziale |
| --- | --- | --- |
| Startup | `/api/ready` | Ritardo 5 s, intervallo 5 s, timeout 6 s, 30 tentativi |
| Readiness | `/api/ready` | Intervallo 10 s, timeout 6 s, 3 tentativi |
| Liveness | `/api/health` | Intervallo 30 s, timeout 5 s, 3 tentativi |

La readiness conferma anche l'accesso al database. Aprire l'URL dell'app dalla rete autorizzata e caricare il primo Excel.

## 4. Installare una nuova versione

1. Pubblicare la nuova versione e attenderne la presenza in GHCR.
2. Aprire **Container App → Containers → Edit and deploy** (oppure **Revisions and replicas → Create new revision**).
3. Cambiare soltanto **Image and tag**, ad esempio da `ghcr.io/matte13/data-visualization-tool:1.0.0` a `ghcr.io/matte13/data-visualization-tool:1.0.1`.
4. Conservare variabili, secret, rete e database. Distribuire la revisione e verificare che risulti pronta prima di utilizzarla.

Per installazioni ripetibili usare il numero di versione, evitando `latest`. Conservare i tag già installati; per un rollback selezionare l'immagine precedente dopo aver verificato la compatibilità dello schema del database. I normali aggiornamenti dell'immagine non cancellano i progetti.
