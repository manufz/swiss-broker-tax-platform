import json
import sqlite3
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/data_release.py"


def database(tmp_path, year=2025):
    path = tmp_path / "kursliste_2025.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE metadata (key TEXT PRIMARY KEY, value TEXT)")
        db.execute("INSERT INTO metadata VALUES ('tax_year', ?)", (str(year),))
    return path


def run_release(tmp_path, source):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--year", "2025", "--source", str(source)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )


def test_local_release_has_provenance_and_detects_existing_file_tampering(tmp_path):
    source = database(tmp_path)
    result = run_release(tmp_path, source)
    assert result.returncode == 0, result.stderr
    receipt = json.loads(result.stdout)
    directory = tmp_path / "data/releases" / receipt["release_id"]
    manifest = json.loads((directory / "manifest.json").read_text())
    assert manifest["source_metadata"]["tax_year"] == "2025"
    assert manifest["sha256"] == receipt["sha256"]
    assert manifest["bytes"] == source.stat().st_size
    assert not receipt["uploaded"]
    assert run_release(tmp_path, source).returncode == 0
    (directory / source.name).write_bytes(b"tampered")
    assert run_release(tmp_path, source).returncode != 0


def test_release_rejects_wrong_database_tax_year(tmp_path):
    result = run_release(tmp_path, database(tmp_path, 2024))
    assert result.returncode != 0
    assert "Database tax year" in result.stderr
    assert not (tmp_path / "data/releases").exists()
