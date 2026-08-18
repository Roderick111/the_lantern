#!/usr/bin/env python3
"""Fix substring corruption from IP migration (witch→adept broke switch, twitch, etc.)."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "coverage",
    ".venv",
    "venv_linux",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
}

SKIP_FILES = {
    "fix_migration_corruptions.py",
    "migrate_ip.py",
    "package-lock.json",
    "bun.lock",
    "uv.lock",
}

# Longest-first literal fixes
LITERAL_REPLACEMENTS: list[tuple[str, str]] = [
    ("noFallthroughCasesInSadept", "noFallthroughCasesInSwitch"),
    ("Sadeptes", "Switches"),
    ("sadeptes", "switches"),
    ("Sadepting", "Switching"),
    ("sadepting", "switching"),
    ("Sadepted", "Switched"),
    ("sadepted", "switched"),
    ("sadeptTab", "switchTab"),
    ("sadeptLocation", "switchLocation"),
    ("sadept_modes", "switch_modes"),
    ("Sadept", "Switch"),
    ("sadept", "switch"),
    ("tadept", "twitch"),
    ("Powerful adept", "Powerful scholar"),
    ("kind adept", "kind scholar"),
    # occlumency → mind shield left spaces in compound identifiers
    ("mind shield_backlash", "mind_shield_backlash"),
    ("mind shield_block", "mind_shield_block"),
    ("mind shield_modifier", "mind_shield_modifier"),
    ("mind shield_raw", "mind_shield_raw"),
    ("mind shield_skill", "mind_shield_skill"),
    # Missed bare-surname / character leaks from migrate_ip
    ("H. Granger", "E. Marsh"),
    ("Miss Granger", "Miss Marsh"),
    ("Granger's", "Marsh's"),
    ("Granger,", "Marsh,"),
    ("Granger?", "Marsh?"),
    ("Granger ", "Marsh "),
    ("Granger.", "Marsh."),
    ("Granger\"", "Marsh\""),
    ("Granger was", "Marsh was"),
    ("Granger did", "Marsh did"),
    ("Granger probably", "Marsh probably"),
    ("Granger looked", "Marsh looked"),
    ("Granger couldn't", "Marsh couldn't"),
    ("Granger and", "Marsh and"),
    ("accused Granger", "accused Marsh"),
    ("cornered Granger", "cornered Marsh"),
    (" teaching Longbottom", " tutoring Ashford"),
    ("Longbottom combat", "Ashford combat"),
    ("Longbottom spells", "Ashford spells"),
]

REGEX_REPLACEMENTS: list[tuple[str, str]] = [
    # Occlumency rename left spaces in prose/comments
    (r"\bmind shield\b", "mind-shield"),
    (r"\bMind shield\b", "Mind-shield"),
    # Bare "Granger" in narrative (after longer forms above)
    (r"\bGranger\b", "Marsh"),
]

# Patterns to report in --audit (not auto-fixed — review manually)
AUDIT_PATTERNS: list[tuple[str, str]] = [
    (r"\bsadept\w*\b", "switch corruption (witch→adept)"),
    (r"\btadept\w*\b", "twitch corruption (witch→adept)"),
    (r"mind shield[_\w]", "mind_shield identifier with space"),
    (r"\bGranger\b", "HP surname leak"),
    (r"\bLongbottom\b", "HP character leak"),
    (r"\bMalfoy\b", "HP surname leak"),
    (r"\bHermione\b", "HP character leak"),
    (r"\bHogwarts\b", "HP location leak"),
    (r"\bSnape\b", "HP character leak"),
    (r"\bDobby\b", "HP character leak"),
    (r"\bMoody\b", "HP character leak (not Graves)"),
    (r"\bocclumency\b", "unmigrated spell name"),
    (r"\blegilimency\b", "unmigrated spell name (outside aliases)"),
    (r"\bwand_signature\b", "unmigrated save field"),
    (r"\bhermione\b", "unmigrated witness id"),
    (r"\bdraco\b", "unmigrated witness id"),
    (r"\bdobby\b", "unmigrated witness id"),
    (r"lantern_inspector-(backend|frontend|network|saves)", "auror→lantern_inspector docker typo"),
]

TEXT_EXTENSIONS = {
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".yaml",
    ".yml",
    ".md",
    ".sh",
    ".json",
    ".toml",
    ".html",
    ".txt",
    ".example",
}


def should_process(path: Path) -> bool:
    if path.name in SKIP_FILES:
        return False
    for part in path.parts:
        if part in SKIP_DIRS:
            return False
    if path.suffix in TEXT_EXTENSIONS or path.name in {
        "Caddyfile",
        "Dockerfile",
        "Dockerfile.frontend",
        "CLAUDE.md",
        "README.md",
        "STATUS.md",
        "project.yml",
    }:
        return True
    return False


def fix_text(text: str) -> str:
    for old, new in LITERAL_REPLACEMENTS:
        text = text.replace(old, new)
    for pattern, repl in REGEX_REPLACEMENTS:
        text = re.sub(pattern, repl, text)
    return text


def audit() -> int:
    findings: dict[str, list[tuple[Path, int, str]]] = {}
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or not should_process(path):
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (UnicodeDecodeError, OSError):
            continue
        for line_no, line in enumerate(lines, start=1):
            for pattern, label in AUDIT_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE if "hermione" in pattern else 0):
                    findings.setdefault(label, []).append((path, line_no, line.strip()[:120]))

    if not findings:
        print("No audit issues found.")
        return 0

    print("Audit findings (review manually):")
    for label, hits in sorted(findings.items()):
        print(f"\n  [{label}] — {len(hits)} hit(s)")
        for path, line_no, snippet in hits[:8]:
            print(f"    {path.relative_to(ROOT)}:{line_no}: {snippet}")
        if len(hits) > 8:
            print(f"    ... and {len(hits) - 8} more")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Scan for remaining migration issues without modifying files",
    )
    args = parser.parse_args()

    if args.audit:
        return audit()

    changed: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or not should_process(path):
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        updated = fix_text(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed.append(path)

    print(f"Fixed {len(changed)} files")
    for p in changed:
        print(f"  {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())