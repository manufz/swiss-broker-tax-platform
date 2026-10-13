import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/audit_publication.py"


def test_private_notification_identity_is_checked_in_git_metadata(tmp_path):
    def git(*args, private=False):
        email = (
            "example@example.test"
            if private
            else "123+example@users.noreply.github.com"
        )
        subprocess.run(
            [
                "git",
                "-c",
                "user.name=Example",
                "-c",
                f"user.email={email}",
                "-c",
                "commit.gpgsign=false",
                *args,
            ],
            cwd=tmp_path,
            check=True,
            capture_output=True,
        )

    git("init")
    (tmp_path / "README.md").write_text("Synthetic publication audit fixture\n")
    git("add", "README.md")
    git("commit", "-m", "synthetic", private=True)
    settings = tmp_path / "terraform/environments/dev/dev.auto.tfvars"
    settings.parent.mkdir(parents=True)
    settings.write_text('notification_email = "example@example.test"\n')
    (tmp_path / ".gitignore").write_text("*.tfvars\n")

    def audit():
        return subprocess.run(
            [sys.executable, str(SCRIPT)],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

    result = audit()
    assert result.returncode != 0
    assert "author/committer metadata" in result.stderr
    assert "example@example.test" not in result.stdout + result.stderr
    git("commit", "--amend", "--no-edit", "--reset-author")
    assert audit().returncode == 0
    (tmp_path / "README.md").write_text("EXAMPLE@EXAMPLE.TEST\n")
    git("add", "README.md")
    git("commit", "-m", "synthetic content leak")
    result = audit()
    assert result.returncode != 0
    assert "tracked file content" in result.stderr
    assert "EXAMPLE@EXAMPLE.TEST" not in result.stdout + result.stderr
