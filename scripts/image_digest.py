"""Read the committed development image digest for the manual release workflow."""

import re
from pathlib import Path

source = Path("terraform/environments/dev/variables.tf").read_text()
match = re.search(
    r'variable "api_image_digest"\s*\{.*?default\s*=\s*"(sha256:[a-f0-9]{64})"',
    source,
    re.DOTALL,
)
if not match:
    raise SystemExit("Missing committed image digest")
print(match.group(1))
