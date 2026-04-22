"""Version and distribution-name guards for v0.3.1."""
from pathlib import Path
import tomllib

from scriptorium import __version__

ROOT = Path(__file__).resolve().parent.parent


def test_package_version_is_v031():
    assert __version__ == "0.3.1"


def test_pyproject_distribution_name_is_scriptorium_cli():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["project"]["name"] == "scriptorium-cli"
    assert data["project"]["version"] == "0.3.1"
    scripts = data["project"]["scripts"]
    assert scripts["scriptorium"] == "scriptorium.cli:main"


def test_plugin_manifest_version_is_v031():
    import json
    manifest = json.loads(
        (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert manifest["version"] == "0.3.1"
