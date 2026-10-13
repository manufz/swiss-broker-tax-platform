"""Check tracked files and reachable Git history without printing secret values.

Heuristic checks supplement review; a passing result cannot prove absence of secrets.
"""

import re
import subprocess
from pathlib import Path

PUBLIC_PDFS = {"examples/synthetic-basic-2025.pdf"}
PATTERNS = {
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub credential": re.compile(
        rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{60,})"
    ),
    "Azure storage credential": re.compile(rb"AccountKey=[A-Za-z0-9+/]{40,}={0,2}"),
    "AWS credential": re.compile(rb"\bAKIA[A-Z0-9]{16}\b"),
    "JWT": re.compile(
        rb"\beyJ[A-Za-z0-9_-]{20,}\.eyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}"
    ),
}


def git(*args):
    return subprocess.check_output(["git", *args])


def forbidden(path):
    name = Path(path).name
    return (
        path.startswith(
            (
                "private/",
                "statements/",
                "uploads/",
                "outputs/",
                "data/kursliste/",
                "data/releases/",
            )
        )
        or name.startswith(".env")
        and name != ".env.example"
        or ".terraform/" in path
        or ".tfstate" in name
        or name.endswith((".tfplan", ".sqlite", ".tfvars", ".tfvars.json"))
        or name.endswith(".pdf")
        and path not in PUBLIC_PDFS
    )


def main():
    findings = set()
    objects = git("rev-list", "--objects", "--all").decode().splitlines()
    pairs = [
        (line.split(" ", 1)[0], line.split(" ", 1)[1])
        for line in objects
        if " " in line
    ]
    for oid, path in pairs:
        if forbidden(path):
            findings.add(f"History: private artifact path {path}")
        if git("cat-file", "-t", oid).strip() != b"blob":
            continue
        content = git("cat-file", "blob", oid)
        for kind, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.add(f"History: {kind} marker in {path}")
    for path in (
        git("ls-files", "--cached", "--others", "--exclude-standard")
        .decode()
        .splitlines()
    ):
        if forbidden(path):
            findings.add(f"Working tree: private artifact path {path}")
        if Path(path).is_file():
            for kind, pattern in PATTERNS.items():
                if pattern.search(Path(path).read_bytes()):
                    findings.add(f"Working tree: {kind} marker in {path}")
    if findings:
        raise SystemExit(
            "Publication audit failed (values withheld):\n"
            + "\n".join(sorted(findings))
        )
    print(
        "Publication audit PASS: reviewed paths and common credential markers in files/history."
    )


if __name__ == "__main__":
    main()
