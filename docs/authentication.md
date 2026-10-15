# Microsoft Entra sign-in

Azure Container Apps authentication (EasyAuth) enforces single-tenant sign-in
and an explicit user allowlist before requests reach FastAPI. External ingress
requires HTTPS; unauthenticated requests return HTTP 401.

## Configuration and access policy

`terraform/environments/dev/authentication.tf` creates the Entra app registration,
service principal, client credential and rotation timestamp. AzAPI manages the
Container Apps `authConfigs/current` resource. The app receives the credential
through the `entra-client-secret` Container Apps secret.

The issuer is restricted to the configured Entra tenant, and the permitted token
audience is the app's client ID. `allowed_user_object_ids` is a required,
nonempty set of Entra user object IDs supplied through private settings. This
user authorization policy is separate from the managed identity used for ACR
image pulls. Application registration permissions in Entra are also distinct
from Azure subscription roles.

The login endpoint is `/.auth/login/aad`, returning to the workspace at `/`.
The Entra homepage targets `/`; `/docs` remains the developer API interface.
The HTTPS callback hostname is derived from the Container Apps environment's
default domain. ID-token issuance is enabled for the built-in hybrid OpenID
Connect flow; implicit access-token issuance is disabled.

No Graph permissions to read user files or mail are requested. EasyAuth's token
store is disabled; browser session cookies still authenticate requests.
Local development and HTTP requests inside the container bypass ingress
sign-in and cannot verify the deployed Entra policy.

## Using and checking sign-in

Obtain the deployment's sign-in URL:

```bash
terraform -chdir=terraform/environments/dev output -raw api_sign_in_url
```

An allowlisted user can open the workspace and generate a statement from the
synthetic fixture. Sign out through `/.auth/logout`, then request `/` directly
without revisiting the login endpoint to check denial. Entra SSO can sign a user
back in through the login endpoint; that is separate from app logout.

Check unauthenticated ingress from a session-free client:

```bash
api_url=$(terraform -chdir=terraform/environments/dev output -raw api_url)
curl --silent --show-error --output /dev/null --write-out '%{http_code}\n' "$api_url/"
```

Expected: 401. To verify the identity allowlist, use another authenticated
same-tenant account outside the allowed set and confirm forbidden access.
An anonymous 401 or wrong-tenant error does not establish that check.

## Credential lifetime

The credential expires after 180 days. `time_rotating.auth_secret` proposes
rotation after 150 days; rotation happens only when Terraform is run and applied.
It is not a background scheduler. A replacement password is created before the
old one is deleted, and the Container App secret is updated in the same apply.
Monitor expiry, apply the rotation before the credential expires and verify
sign-in afterward:

```bash
terraform -chdir=terraform/environments/dev output auth_client_secret_expires_at
```

Terraform stores the generated credential in restricted remote state. Its value
is sensitive and is not an output. Keep it out of source, screenshots, logs and
Git. Tenant IDs, client IDs and user object IDs are identifiers, not credentials.
Backend access controls also protect retained state versions.

References: [Microsoft Entra authentication for Container Apps](https://learn.microsoft.com/azure/container-apps/authentication-entra),
[Container Apps authentication policy schema](https://learn.microsoft.com/azure/templates/microsoft.app/2025-07-01/containerapps/authconfigs),
[Terraform rotation timing](https://github.com/hashicorp/terraform-provider-time/blob/main/docs/resources/rotating.md).
