# Architecture and data flow

## Azure resource view

The development environment separates application resources from Terraform state
storage in two resource groups in Switzerland North. Microsoft Entra applications
live at tenant scope. Solid arrows show runtime and monitoring dependencies;
dotted arrows show identity assignments and access permissions.

```mermaid
flowchart TB
    subgraph Tenant["Microsoft Entra tenant"]
        Login["Sign-in application<br/>and service principal"]
        Release["Release application / service principal<br/>GitHub OIDC federation"]
    end

    subgraph Subscription["Azure subscription"]
        subgraph PlatformRG["rg-swiss-tax-statement-dev · Switzerland North"]
            Registry["Azure Container Registry<br/>Basic / admin disabled"]
            PullIdentity["User-assigned managed identity<br/>registry pull"]

            subgraph Environment["Container Apps environment · cae-swiss-tax-statement-dev"]
                App["Container App<br/>ca-swiss-tax-statement-api-dev<br/>HTTPS / Entra authentication"]
                Mount["Environment storage binding<br/>kursliste / ReadOnly"]
            end

            subgraph ReferenceStorage["Storage account · reference data"]
                Share["Azure Files share<br/>kursliste"]
            end

            Logs["Log Analytics workspace"]
            Alert["Scheduled-query alert<br/>processing failures"]
            ActionGroup["Monitor action group<br/>operations notifications"]
            Budget["Resource-group budget<br/>80% / 100% notifications"]
        end

        subgraph StateRG["rg-swiss-tax-state-dev · Switzerland North"]
            subgraph StateStorage["Storage account · Terraform state"]
                State["Private Blob container · tfstate<br/>bootstrap and development state<br/>versioning / soft delete"]
            end
        end
    end

    Operator["Terraform operator identity"]
    GitHub["GitHub Actions<br/>azure-dev / main"]

    Login -. "Entra sign-in / user allowlist" .-> App
    GitHub -. "exact-subject federation" .-> Release
    Release -. "AcrPush / Reader" .-> Registry
    Release -. "Contributor at app scope" .-> App
    Release -. "Managed Identity Operator" .-> PullIdentity
    PullIdentity -. "assigned identity" .-> App
    PullIdentity -. "AcrPull at registry scope" .-> Registry
    Registry -->|image pinned by digest| App
    Share -->|SMB / storage key| Mount
    Mount -->|read-only /data/kursliste| App
    App -->|console logs| Logs
    Logs -->|failure query| Alert
    Alert -->|notify| ActionGroup
    Operator -. "Storage Blob Data Contributor at container scope" .-> State
```

The `tfstate` container holds separate `bootstrap.terraform.tfstate` and
`dev.terraform.tfstate` blobs. The bootstrap Terraform root owns this storage;
the development root owns the application resource group and Entra sign-in
configuration. Neither the app nor the release identity has access to Terraform
state. Budget notifications are independent of the processing-failure alert and
its action group.

GitHub release federation is restricted to the repository's `azure-dev`
environment, which permits only `main`. Its scoped registry, app and identity
permissions are described in the [release guide](github-release.md).

## Request and data flow

```mermaid
flowchart LR
    User[Allowlisted developer] -->|HTTPS / Entra sign-in| Auth[Container Apps authentication]
    Auth --> API[FastAPI / one worker]
    API -->|bounded XML upload| Job[Temporary directory + engine subprocess]
    Job --> Schema[Local eCH XSD schemas]
    Job -->|read only| Data[Azure Files / public Kursliste SQLite]
    Job --> PDF[PDF with compressed eCH XML in PDF417]
    PDF -->|no-store response| User
    API -->|status + duration only| Logs[Log Analytics / failure alert]
    TF[Terraform / developer identity] --> Infra[Azure resources and Entra policy]
    TF --> State[Private Azure Blob state / leases / versions]
    CI[GitHub Actions / federated identity] -->|push verified amd64 image| ACR[Azure Container Registry]
    ACR -->|AcrPull managed identity| API
    CI -->|committed digest only| API
```

The current environment is a single-user portfolio MVP in Switzerland North.
Entra terminates authentication before traffic reaches the API. The application
does not implement user accounts or accept identity headers from public clients.
One Uvicorn worker and at most one replica bound engine concurrency; another
upload returns 503 with a retry hint. A 12 MiB whole-request limit bounds multipart
spooling, with a separate 10 MiB XML-file limit. Jobs time out after 120 seconds.

The engine is isolated in a subprocess with empty per-job configuration and
identifier files. Broker XML and PDFs live in a temporary directory removed
after completion or failure; they are not written to Azure Files or application
logs. Request cancellation does not remove files underneath the running worker.
The PDF is returned with `Cache-Control: no-store`; the client controls downloaded
copies. Reference data is public and mounted read-only, separately from the image.

`/health` verifies process responsiveness. `/ready` verifies nonempty files for
configured years and required schemas; it does not scan a 551 MiB database over
SMB or prove calculation correctness. Processing and import checks provide that
additional evidence. Scale-to-zero allows idle runtime shutdown; the first
authenticated request after an idle period can be slower.

Terraform owns infrastructure and desired image configuration. The manual image
deployment workflow reads the committed digest and changes only the runtime image
through Azure CLI. A subsequent Terraform plan refreshes state and should have no
image drift. Infrastructure changes remain reviewed local Terraform operations;
the release identity cannot access the sensitive Terraform state container.
