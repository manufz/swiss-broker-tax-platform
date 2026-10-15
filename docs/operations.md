# Operations, cost and recovery

## Scaling, cost and alerts

Min replicas 0, max replicas 1, 0.5 vCPU, 1 GiB RAM and one Uvicorn worker bound
the portfolio workload. HTTP traffic can wake the service and idle cooldown can
remove its final replica. The first authorized upload may take longer. `/health`
checks responsiveness; `/ready` checks schemas/year files without scanning SQLite
over SMB. Registry, storage, logs and alert costs remain when compute is idle.

The resource-group budget defaults to **25 units of Azure billing currency**,
with 80%/100% actual-cost notifications to the Owner role. Set
`TF_VAR_monthly_budget` to your chosen amount. It does not cap spending and excludes
the separate state-storage group. Cost reporting/notifications can be delayed.
The current deployment's billing currency was verified as EUR, so its default
budget is EUR 25 per month.

The error alert checks every five minutes for three engine/server 5xx events in
fifteen minutes. Busy events and invalid-input 4xx are excluded. A dead process
that produces no logs needs separate revision/readiness diagnosis.

## Inspect

```bash
az containerapp revision list -n ca-swiss-tax-statement-api-dev \
  -g rg-swiss-tax-statement-dev \
  --query '[].{name:name,active:properties.active,health:properties.healthState,image:properties.template.containers[0].image}' -o table
az containerapp replica list -n ca-swiss-tax-statement-api-dev \
  -g rg-swiss-tax-statement-dev --revision YOUR_ACTIVE_REVISION -o table
```

Read only scoped console logs; avoid `--debug` and full state/config dumps. In
Log Analytics, query:

```kusto
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "ca-swiss-tax-statement-api-dev"
| where Log_s contains "statement_processing"
| project TimeGenerated, Log_s
| order by TimeGenerated desc
```

| Symptom | Check / response |
| --- | --- |
| Unauthenticated 401 | Expected; use the Entra sign-in URL |
| Signed-in 403 | Tenant/user-object-ID allowlist; preserve access policy |
| 400 / 413 / 422 | XML, size, annual-report/year/canton requirements |
| Busy 503 + Retry-After | Wait for the current job, then retry |
| Readiness/data 503 | Mount, selected directory, schemas and year files |
| 504 / repeated engine 5xx | Status/duration logs, data and CPU/memory; reproduce with synthetic data |
| Unhealthy new revision | Image, AcrPull, probes and mount; roll back |
| Zero idle replicas | Expected; an authorized API request wakes the app |
| Terraform lock error | Check another apply and wait; don't force-unlock active work |

## Rollback and maintenance

Before each release, record the old image digest and data directory. Restore
them in Terraform, review/apply, then check health, synthetic processing, 401s and
a clean plan. Use the previously verified `api_image_digest` and
`kursliste_directory`; select a `readiness_probe_path` supported by that image.
Older images without `/ready` require `/health` instead. If the browser entry
point differs, restore the matching Entra homepage and sign-in return URL too.

Use the same variable values for plan and apply. Return to the committed
configuration with a reviewed `apply` and repeat readiness/processing checks.
Temporary overrides deliberately differ from defaults; a subsequent plan shows
that difference until the configuration is restored.

Check `auth_client_secret_expires_at` monthly. The rotation resource uses 150 days
with 180-day validity, but rotation happens only when Terraform runs. Apply before
expiry and confirm sign-in. Refresh data with [immutable releases](data-releases.md).
Measure representative SMB processing latency before adding a local read-only
database copy per replica. Never overwrite mounted databases.

## Removal

Scale-to-zero does not remove every paid resource. For deliberate removal,
preserve data/digests, review `terraform -chdir=terraform/environments/dev plan
-destroy`, and run `destroy` only when ready to remove the app. Bootstrap state
storage is separate and has `prevent_destroy`; retain it for recovery. State blob
versions/backups contain secrets and need deliberate retention/deletion.

Reference: [Container Apps scaling](https://learn.microsoft.com/azure/container-apps/scale-app).
