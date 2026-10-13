# Immutable public reference-data releases

Download public data separately from images:

```bash
uv run --frozen opensteuerauszug kursliste download --year 2025 --destination data/kursliste
python3 scripts/data_release.py --year 2025 --source data/kursliste/kursliste_2025.sqlite
```

The script runs SQLite `quick_check` locally, computes SHA-256 and transfer MD5,
and copies the database into ignored `data/releases/<year>-<sha-prefix>/`. Its
manifest records source metadata, size and hashes. A local integrity check does
not establish tax-data completeness; retain official export provenance too.

Upload to a new directory, preserving current runtime data:

```bash
account=$(terraform -chdir=terraform/environments/dev output -raw reference_data_storage_account_name)
python3 scripts/data_release.py --year 2025 \
  --source data/kursliste/kursliste_2025.sqlite --storage-account "$account"
```

Azure CLI resolves the SMB account key through your Azure identity; the script
never prints it. Existing release databases are not overwritten. Transfer MD5
is validated and remote size checked. If upload was interrupted, inspect/remove
only that incomplete new directory before retrying; preserve mounted releases.

Promote the returned directory by updating `kursliste_directory` in Terraform,
reviewing its plan and applying it. Check readiness and synthetic processing.
Retain old releases/root data and roll back by selecting the previous directory.
GitHub's image workflow does not refresh reference data. Never put personal XML
or PDFs in the share. See [current provenance](kursliste-provenance.md).
