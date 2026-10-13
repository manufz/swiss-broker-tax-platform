"""Prepare immutable public Kursliste releases and optionally upload to Azure Files."""

import argparse
import base64
import hashlib
import json
import shutil
import sqlite3
import subprocess
from pathlib import Path


def az(*args):
    return subprocess.check_output(["az", *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--storage-account", help="Omit for a local-only release")
    parser.add_argument("--share", default="kursliste")
    args = parser.parse_args()
    assert 2000 <= args.year <= 2100
    assert args.source.name == f"kursliste_{args.year}.sqlite"
    with sqlite3.connect(f"file:{args.source.resolve()}?mode=ro", uri=True) as db:
        assert db.execute("PRAGMA quick_check").fetchone() == ("ok",)
        source_metadata = dict(db.execute("SELECT key,value FROM metadata"))
        assert source_metadata.get("tax_year") == str(args.year), (
            "Database tax year does not match requested release"
        )
    with args.source.open("rb") as source:
        sha = hashlib.file_digest(source, "sha256").hexdigest()
    with args.source.open("rb") as source:
        md5 = base64.b64encode(hashlib.file_digest(source, "md5").digest()).decode()
    release_id = f"{args.year}-{sha[:12]}"
    directory = Path("data/releases") / release_id
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / args.source.name
    if not destination.exists():
        shutil.copyfile(args.source, destination)
    else:
        with destination.open("rb") as data:
            assert hashlib.file_digest(data, "sha256").hexdigest() == sha
    manifest = {
        "release_id": release_id,
        "year": args.year,
        "file": destination.name,
        "bytes": destination.stat().st_size,
        "sha256": sha,
        "md5_base64": md5,
        "source_metadata": source_metadata,
    }
    manifest_path = directory / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    if args.storage_account:
        common = [
            "--account-name",
            args.storage_account,
            "--share-name",
            args.share,
            "--auth-mode",
            "key",
        ]
        remote = f"releases/{release_id}"
        exists = az(
            "storage",
            "file",
            "exists",
            *common,
            "--path",
            f"{remote}/{destination.name}",
            "--query",
            "exists",
            "-o",
            "tsv",
        )
        if exists.lower() == "true":
            raise SystemExit(
                "Remote release already exists; refusing to overwrite immutable data."
            )
        for path in ("releases", remote):
            az("storage", "directory", "create", *common, "--name", path, "-o", "none")
        for path in (destination, manifest_path):
            command = [
                "storage",
                "file",
                "upload",
                *common,
                "--source",
                str(path),
                "--path",
                f"{remote}/{path.name}",
                "--validate-content",
                "-o",
                "none",
            ]
            if path == destination:
                command += ["--content-md5", md5]
            az(*command)
        size = az(
            "storage",
            "file",
            "show",
            *common,
            "--path",
            f"{remote}/{destination.name}",
            "--query",
            "properties.contentLength",
            "-o",
            "tsv",
        )
        assert int(size) == destination.stat().st_size
    print(
        json.dumps(
            {
                "release_id": release_id,
                "sha256": sha,
                "kursliste_directory": f"/data/kursliste/releases/{release_id}",
                "uploaded": bool(args.storage_account),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
