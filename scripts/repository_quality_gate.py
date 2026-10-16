"""Run advisory installed-toolchain auto-fix, then repository correctness checks."""

from __future__ import annotations

import argparse
import ast
from pathlib import Path
import re
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / "vwce-buy"


def affected_paths() -> list[str]:
    tracked = (
        subprocess.check_output(["git", "diff", "--name-only", "-z", "HEAD"], cwd=ROOT)
        .decode("utf-8")
        .split("\0")
    )
    untracked = (
        subprocess.check_output(
            ["git", "ls-files", "--others", "--exclude-standard", "-z"], cwd=ROOT
        )
        .decode("utf-8")
        .split("\0")
    )
    return sorted(
        {
            name
            for name in tracked + untracked
            if name and (ROOT / name).is_file() and not (ROOT / name).is_symlink()
        }
    )


def validate_version(tag: str | None = None) -> None:
    version = (PROJECT / "VERSION").read_text(encoding="utf-8").strip()
    if re.fullmatch(r"\d+\.\d+\.\d+", version) is None:
        raise ValueError("VERSION must contain a stable Semantic Version.")
    metadata = tomllib.loads((PROJECT / "pyproject.toml").read_text(encoding="utf-8"))
    tree = ast.parse((PROJECT / "src/vwce_buy/__init__.py").read_text(encoding="utf-8"))
    versions = [
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "__version__"
            for target in node.targets
        )
    ]
    headings = re.findall(
        r"^## (\S+)",
        (PROJECT / "CHANGELOG.md").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if (
        metadata["project"]["version"] != version
        or versions != [version]
        or not headings
        or headings[0] != version
    ):
        raise ValueError(
            "VERSION, pyproject, package, and current changelog entry must agree."
        )
    if tag is not None and tag != f"v{version}":
        raise ValueError(f"Tag must be v{version}.")
    if metadata["project"]["scripts"].get("vwce") != "vwce_buy.status_cli:main":
        raise ValueError("The vwce console entry point is missing or incorrect.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", type=Path)
    parser.add_argument("--print-affected-paths", action="store_true")
    parser.add_argument("--tag")
    parser.add_argument("--version-only", action="store_true")
    args = parser.parse_args(argv)
    if args.print_affected_paths:
        print("\n".join(affected_paths()))
        return 0
    if not args.version_only:
        if args.cache_root is None:
            print(
                "Format/Lint advisory: installed MPP toolchain unavailable; continuing to Test.",
                flush=True,
            )
        else:
            toolchain = (
                args.cache_root
                / "payload/skills/format-and-lint/scripts/quality_toolchain.py"
            )
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-B",
                        str(toolchain),
                        "--root",
                        str(ROOT),
                        "--cache-root",
                        str(args.cache_root),
                        "--autoFix",
                        "--paths",
                        *affected_paths(),
                    ],
                    cwd=ROOT,
                    check=False,
                )
                if result.returncode:
                    print(
                        f"Format/Lint advisory: exit {result.returncode}; continuing to Test.",
                        flush=True,
                    )
            except OSError as exc:
                print(f"Format/Lint advisory: {exc}; continuing to Test.", flush=True)
    print("Test: version consistency", flush=True)
    try:
        validate_version(args.tag)
    except (ValueError, KeyError, OSError) as exc:
        print(f"Version validation failed: {exc}", file=sys.stderr)
        return 1
    if args.version_only:
        return 0
    print("Test: offline unit suite (broker integrations are opt-in)", flush=True)
    return subprocess.run(
        [sys.executable, "-B", "-m", "pytest", "--ignore=tests/integration"],
        cwd=PROJECT,
        check=False,
    ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
