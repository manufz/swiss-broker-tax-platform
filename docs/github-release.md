# GitHub CI and image promotion

CI runs tests/lint, a publication audit, Terraform validation without Azure
access, and an amd64 Docker smoke check. Actions use verified commit SHAs; the
base-image digest, uv version and Git revisions are pinned. Debian mirrors are
not snapshotted, so builds are not guaranteed byte-identical; record each tested
image's digest. Never expose Terraform state or saved plans to CI.

## Manual image publishing

From the repository root, commit the application source and use a new commit tag
for each release. Test the exact Linux amd64 image before uploading it:

```bash
registry_name=$(terraform -chdir=terraform/environments/dev output -raw container_registry_name)
registry_server=$(terraform -chdir=terraform/environments/dev output -raw container_registry_login_server)
image_tag=$(git rev-parse --short HEAD)
image_ref="$registry_server/swiss-tax-statement-api:$image_tag"

docker build --platform linux/amd64 -t "$image_ref" .
bash scripts/docker_smoke.sh "$image_ref"
az acr login --name "$registry_name"
docker push "$image_ref"
az acr repository show --name "$registry_name" \
  --image "swiss-tax-statement-api:$image_tag" --query digest --output tsv
```

Do not overwrite release tags. Set `api_image_digest` to the returned digest,
review the Terraform plan and apply it to promote the image. Retain the previous
image and reference-data release for rollback. Registry upload alone does not
deploy the application.

## One-time setup after publication

1. Create a GitHub environment `azure-dev`, restricted to `main`. Add environment
   approval where your account supports it; releases require manual dispatch.
2. Run **Inspect OIDC subject** in Actions. Copy its exact subject; it prints no
   token. New repositories may include immutable owner/repository IDs, so do not
   use an old name-only example.
3. Set the subject privately and review/apply Terraform:

   ```bash
   export TF_VAR_github_oidc_subject='COPY_THE_EXACT_SUBJECT'
   export ARM_SUBSCRIPTION_ID="$(az account show --query id -o tsv)"
   terraform -chdir=terraform/environments/dev apply
   terraform -chdir=terraform/environments/dev output -raw github_release_client_id
   ```

   Keep the subject in an ignored `dev.auto.tfvars` file for future plans;
   removing it plans identity deletion. Terraform creates a dedicated Entra
   application/SP and exact-subject federation, AcrPush + Reader at the registry,
   Contributor at the Container App, and Managed Identity Operator at its existing
   AcrPull identity (for Azure's identity-assignment check on app updates).
   It grants no subscription-wide role,
   password, Graph permission or state-storage access.
4. Set these **environment variables** in GitHub `azure-dev`:

   | Variable | Value |
   | --- | --- |
   | `AZURE_CLIENT_ID` | Terraform `github_release_client_id` |
   | `AZURE_TENANT_ID` | `az account show --query tenantId -o tsv` |
   | `AZURE_SUBSCRIPTION_ID` | `az account show --query id -o tsv` |
   | `ACR_NAME` | Terraform `container_registry_name` |
   | `AZURE_RESOURCE_GROUP` | Terraform `resource_group_name` |
   | `AZURE_CONTAINER_APP` | Terraform `container_app_name` |

   These are identifiers, not secrets. Allow time for RBAC propagation.

## Release and rollback

1. Merge source changes after CI passes.
2. Run **Publish verified image** on `main`: source tests, amd64 build, smoke test
   of that exact image, then push under the full commit SHA. Existing tags are
   not overwritten. The job summary gives the digest.
3. Set `api_image_digest` in Terraform to that digest, commit, push and wait for
   CI. This is the reviewable promotion checkpoint.
4. Run **Deploy reviewed image** on `main`. It reads the committed digest,
   verifies it exists, updates only the app image and checks ready revision health
   and unauthenticated 401 responses.
5. Test a signed-in synthetic upload. Locally run Terraform `plan` to refresh
   state; the image should have no drift because configuration matches the release.

Infrastructure changes stay reviewed local Terraform operations. The workflow
does not prove authenticated authorization, processing correctness or import
acceptance. A failed health check does not automatically roll back: commit a
previous verified digest and repeat deployment/acceptance. Retain old images and
data directories until rollback is checked.

References: [GitHub OIDC in Azure](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-azure),
[OIDC subjects](https://docs.github.com/en/actions/reference/security/oidc).
