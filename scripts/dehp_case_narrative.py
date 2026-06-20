#!/usr/bin/env python3
"""Replace HP-parallel narrative framing in case YAML files."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CASE_DIR = ROOT / "backend" / "src" / "case_store"

# Longest-first literal replacements per file group
CASE_001_REPLACEMENTS: list[tuple[str, str]] = [
    (
        "It is the students' second year at Blackwood Collegiate. The The Hollow Below has been opened. Mr. Crankshaw's cat, Morrigan, was found held in stillness weeks ago. Messages about the \"Iron Lodge claimant\" have appeared on the walls. uninitiated-born students live in fear. The school is tense, divided, suspicious.\n\n    Cassian, Elena, and the other students are twelve or thirteen years old — children dealing with forces beyond their understanding.",
        "It is autumn term at Blackwood Collegiate, 1887. Three nights ago someone breached the ward on the eastern alcove of the Sealed Stacks — not simple theft, but the prelude to something worse. Mr. Crankshaw's raven was found stiff on the parapet last month. Graffiti about an Iron Lodge succession feud has appeared on the walls. Uninitiated-born students live in fear. The college is tense, divided, suspicious.\n\n    Cassian, Elena, and the other students are sixteen or seventeen — young initiates dealing with forces beyond their understanding.",
    ),
    ("The The Hollow Below", "the undercroft breach"),
    ("THE HOLLOW BELOW", "THE UNDERCROFT BREACH"),
    ("HOLLOW BELOW", "UNDERCROFT BREACH"),
    ("The Hollow Below", "the undercroft breach"),
    ("Hollow Below", "undercroft breach"),
    ("Iron Lodge claimant", "Iron Lodge succession feud"),
    ("Morrigan was held in stillness", "the custodian's raven was found stiff"),
    ("attack on Morrigan", "attack on the custodian's raven"),
    ("Morrigan", "the custodian's raven"),
    ("Second-year", "Third-year"),
    ("second-year", "third-year"),
    ("students' second year", "students' autumn term"),
    ("Dungeons: DOUBLED patrols (undercroft breach entrance suspected nearby)", "Lower vaults: DOUBLED patrols (breach point suspected nearby)"),
    ("undercroft breach mythology section", "undercroft breach lore section"),
]

CASE_002_REPLACEMENTS: list[tuple[str, str]] = [
    ("Professor Septima Vector", "Professor Celia Morraine"),
    ("Professor Vector", "Professor Morraine"),
    ("S. Vector", "C. Morraine"),
    ("Vector's", "Morraine's"),
    ("Arithmancy", "Numeromancy"),
    ("Rowena Candlewick", "Rowena Ashford"),
    ("RESTRICTED SECT.", "SEALED STACKS"),
    ("Restricted SECT.", "Sealed Stacks"),
    ("Restricted Section", "Sealed Stacks"),
    ("Restricted Sect.", "Sealed Stacks"),
]

# Apply after longer forms above
CASE_002_WORD_REPLACEMENTS: list[tuple[str, str]] = [
    (" Vector ", " Morraine "),
    (" Vector.", " Morraine."),
    (" Vector,", " Morraine,"),
    (" Vector'", " Morraine'"),
    (" Vector\n", " Morraine\n"),
    ("(Vector ", "(Morraine "),
    (" Vector)", " Morraine)"),
    (" Vector:", " Morraine:"),
    (" Vector;", " Morraine;"),
    (" Vector—", " Morraine—"),
    (" Vector killed", " Morraine killed"),
    (" Vector was", " Morraine was"),
    (" Vector had", " Morraine had"),
    (" Vector found", " Morraine found"),
    (" Vector asked", " Morraine asked"),
    (" Vector cast", " Morraine cast"),
    (" Vector emerged", " Morraine emerged"),
    (" Vector blackmailed", " Morraine blackmailed"),
    (" Vector 'discovers'", " Morraine 'discovers'"),
    (" Vector arrives", " Morraine arrives"),
    (" Vector uses", " Morraine uses"),
    (" Vector knows", " Morraine knows"),
    (" Vector saw", " Morraine saw"),
    (" Vector couldn't", " Morraine couldn't"),
    (" Vector mentored", " Morraine mentored"),
    (" Vector felt", " Morraine felt"),
    (" Vector hid", " Morraine hid"),
    (" Vector helped", " Morraine helped"),
    (" Vector read", " Morraine read"),
    (" Vector watched", " Morraine watched"),
    (" Vector covered", " Morraine covered"),
    (" Vector is", " Morraine is"),
    (" Vector are", " Morraine are"),
    (" Vector and", " Morraine and"),
    (" Vector or", " Morraine or"),
    (" Vector to", " Morraine to"),
    (" Vector in", " Morraine in"),
    (" Vector at", " Morraine at"),
    (" Vector on", " Morraine on"),
    (" Vector for", " Morraine for"),
    (" Vector with", " Morraine with"),
    (" Vector when", " Morraine when"),
    (" Vector who", " Morraine who"),
    (" Vector that", " Morraine that"),
    (" Vector which", " Morraine which"),
    (" Vector alone", " Morraine alone"),
    (" Vector)", " Morraine)"),
    ("twist: \"Helena came to save her mentor's reputation, not destroy it. Vector killed", "twist: \"Helena came to save her mentor's reputation, not destroy it. Morraine killed"),
    ("name: \"Professor Septima Vector\"", "name: \"Professor Celia Morraine\""),
]


def apply_replacements(text: str, replacements: list[tuple[str, str]]) -> str:
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def main() -> int:
    changed: list[Path] = []

    case_001 = CASE_DIR / "case_001.yaml"
    if case_001.exists():
        original = case_001.read_text(encoding="utf-8")
        updated = apply_replacements(original, CASE_001_REPLACEMENTS)
        if updated != original:
            case_001.write_text(updated, encoding="utf-8")
            changed.append(case_001)

    case_002 = CASE_DIR / "case_002.yaml"
    if case_002.exists():
        original = case_002.read_text(encoding="utf-8")
        updated = apply_replacements(original, CASE_002_REPLACEMENTS)
        updated = apply_replacements(updated, CASE_002_WORD_REPLACEMENTS)
        updated = re.sub(r"\bVector\b", "Morraine", updated)
        if updated != original:
            case_002.write_text(updated, encoding="utf-8")
            changed.append(case_002)

    print(f"Updated {len(changed)} case files")
    for path in changed:
        print(f"  {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())