"""Hosted release-version validation is also executable locally."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from vwce_buy import __version__


def test_quality_gate_checks_all_version_files_and_tag(monkeypatch, tmp_path):
    gate_path = Path(__file__).parents[2] / "scripts/repository_quality_gate.py"
    spec = spec_from_file_location("quality_gate", gate_path)
    gate = module_from_spec(spec)
    spec.loader.exec_module(gate)
    assert gate.main(["--version-only", "--tag", f"v{__version__}"]) == 0
    assert gate.main(["--version-only", "--tag", "v999.0.0"]) == 1
    project = tmp_path / "project"
    (project / "src/vwce_buy").mkdir(parents=True)
    for name in (
        "VERSION",
        "pyproject.toml",
        "CHANGELOG.md",
        "src/vwce_buy/__init__.py",
    ):
        (project / name).write_text(
            (gate.PROJECT / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    (project / "CHANGELOG.md").write_text(
        "# Changelog\n\n## 999.0.0\n", encoding="utf-8"
    )
    monkeypatch.setattr(gate, "PROJECT", project)
    assert gate.main(["--version-only"]) == 1
