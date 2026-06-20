#!/usr/bin/env python3
"""Audit LLM prompt files for leftover Harry Potter terminology."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCAN_DIRS = [
    ROOT / "backend" / "src" / "context",
    ROOT / "backend" / "src" / "api" / "routes",
]

SKIP_FILES = {"migrate_ip.py", "fix_migration_corruptions.py", "audit_prompt_ip.py"}

PATTERNS: list[tuple[str, str]] = [
    (r"\bHogwarts\b", "HP location"),
    (r"\bHarry Potter\b", "HP franchise"),
    (r"\bHermione\b", "HP character"),
    (r"\bDraco\b", "HP character"),
    (r"\bDobby\b", "HP character"),
    (r"\bSnape\b", "HP character"),
    (r"\bMoody\b", "HP character (check if Graves context)"),
    (r"Mad-Eye", "HP Moody nickname"),
    (r"CONSTANT VIGILANCE", "HP Moody catchphrase"),
    (r"\bDeath Eater\b", "HP faction"),
    (r"\bLegilimency\b", "HP spell (use mnemonic delving)"),
    (r"\bRevelio\b", "HP spell (use unveil)"),
    (r"\bLumos\b", "HP spell"),
    (r"\bOcclumency\b", "HP spell"),
    (r"\bMinistry of Magic\b", "HP institution"),
    (r"\bDaily Prophet\b", "HP newspaper"),
    (r"\bbroomstick\b", "HP transport"),
    (r"\bfirst-year\b", "HP school year"),
    (r"\bchase dragons\b", "HP idiom"),
    (r"\bwand\b", "HP item (use focus)"),
    (r"\bAuror\b", "HP role (use Lantern Inspector)"),
]


def main() -> int:
    findings: list[tuple[Path, int, str, str]] = []

    for scan_dir in SCAN_DIRS:
        if not scan_dir.exists():
            continue
        for path in sorted(scan_dir.rglob("*.py")):
            if path.name in SKIP_FILES:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for line_no, line in enumerate(lines, start=1):
                for pattern, label in PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append((path, line_no, label, line.strip()[:120]))

    if not findings:
        print("No HP terminology found in prompt scan paths.")
        return 0

    print("HP terminology in prompts (fix these):")
    by_label: dict[str, list[tuple[Path, int, str]]] = {}
    for path, line_no, label, snippet in findings:
        by_label.setdefault(label, []).append((path, line_no, snippet))

    for label, hits in sorted(by_label.items()):
        print(f"\n  [{label}] — {len(hits)} hit(s)")
        for path, line_no, snippet in hits[:6]:
            print(f"    {path.relative_to(ROOT)}:{line_no}: {snippet}")
        if len(hits) > 6:
            print(f"    ... and {len(hits) - 6} more")
    return 1


if __name__ == "__main__":
    sys.exit(main())