from pathlib import Path
from vwce_buy import __version__

def test_canonical_version_matches_package_and_changelog():
    root = Path(__file__).parents[1]
    assert (root / "VERSION").read_text(encoding="utf-8").strip() == __version__ == "0.2.1"
    assert f"## {__version__}" in (root / "CHANGELOG.md").read_text(encoding="utf-8")
