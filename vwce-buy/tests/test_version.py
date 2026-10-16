from pathlib import Path
import tomllib
from vwce_buy import __version__


def test_canonical_version_matches_package_and_changelog():
    root = Path(__file__).parents[1]
    metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    assert (
        (root / "VERSION").read_text(encoding="utf-8").strip()
        == __version__
        == metadata["project"]["version"]
    )
    assert metadata["project"]["scripts"]["vwce"] == "vwce_buy.status_cli:main"
    assert f"## {__version__}" in (root / "CHANGELOG.md").read_text(encoding="utf-8")
