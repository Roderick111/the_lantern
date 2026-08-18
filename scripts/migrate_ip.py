#!/usr/bin/env python3
"""One-time IP migration: Harry Potter → The Lantern universe."""

from __future__ import annotations

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
    "uv.lock",
}

SKIP_FILES = {
    "migrate_ip.py",
    "package-lock.json",
    "bun.lock",
}

# Longest-first literal replacements (case-sensitive where noted)
LITERAL_REPLACEMENTS: list[tuple[str, str]] = [
    # Brand / product
    ("Mad-Eye Moody", "Inspector Graves"),
    ("Auror's Handbook", "Lantern Compendium"),
    ("Auror-in-training", "probationary Lantern Inspector"),
    ("Auror Academy", "The Lantern"),
    ("auror-academy", "the-lantern"),
    ("hp-investigation-game", "the-lantern"),
    ("hp-game-backend", "lantern-backend"),
    ("HP_GAME_DB_PATH", "LANTERN_DB_PATH"),
    ("hp_game_test.db", "lantern_test.db"),
    ("hp_game_location_", "lantern_game_location_"),
    ("hp_game_player_id", "lantern_game_player_id"),
    ("hp-detective-active-session", "lantern-active-session"),
    ("hp-detective-hints-enabled", "lantern-hints-enabled"),
    ("hp-detective-music-track-", "lantern-music-track-"),
    ("hp-detective-music-volume", "lantern-music-volume"),
    ("hp-detective-music-muted", "lantern-music-muted"),
    ("hp-detective-music-enabled", "lantern-music-enabled"),
    ("hp-detective-theme", "lantern-theme"),
    ("hp_player_token", "lantern_player_token"),
    ("hp-session-expired", "lantern-session-expired"),
    ("hp_llm_settings", "lantern_llm_settings"),
    ("hp_player_id", "lantern_player_id"),
    ("hp_save_", "lantern_save_"),
    ("hp_game.db", "lantern.db"),
    ("hp_game", "lantern_game"),
    ("hp-game", "the-lantern"),
    ("AurorHandbook", "LanternCompendium"),
    ("AUROR_ACADEMY_GAME_DESIGN", "LANTERN_GAME_DESIGN"),
    # Functions / fields
    ("build_moody_feedback_llm", "build_graves_feedback_llm"),
    ("build_moody_briefing_prompt", "build_graves_briefing_prompt"),
    ("build_moody_roast_prompt", "build_graves_roast_prompt"),
    ("build_moody_praise_prompt", "build_graves_praise_prompt"),
    ("ask_moody_question", "ask_graves_question"),
    ("build_legilimency_narration_prompt", "build_mnemonic_delving_narration_prompt"),
    ("calculate_legilimency_specificity_bonus", "calculate_mnemonic_delving_specificity_bonus"),
    ("calculate_legilimency_success", "calculate_mnemonic_delving_success"),
    ("handle_programmatic_legilimency", "handle_programmatic_mnemonic_delving"),
    ("find_witness_for_legilimency", "find_witness_for_mnemonic_delving"),
    ("detect_focused_legilimency", "detect_focused_mnemonic_delving"),
    ("legilimency_redirect", "mnemonic_delving_redirect"),
    ("legilimency_detected", "mnemonic_delving_detected"),
    ("test_moody_feedback", "test_graves_feedback"),
    # YAML keys
    ("moody_all_paths_continue", "graves_all_paths_continue"),
    ("moody_response_wrong_low", "graves_response_wrong_low"),
    ("moody_response_correct", "graves_response_correct"),
    ("moody_final_word", "graves_final_word"),
    ("moody_response", "graves_response"),
    ("moody_teaches", "graves_teaches"),
    ("moody_leverage", "graves_leverage"),
    ("moody_reaction", "graves_reaction"),
    ("moody_style", "graves_style"),
    ("moody_test", "graves_test"),
    ("moody_lesson", "graves_lesson"),
    ("moody_tone", "graves_tone"),
    # Evidence / witness IDs (before bare names)
    ("hermione_wand_check", "elena_focus_check"),
    ("hermione_book_slip", "elena_book_slip"),
    ("draco_confession", "cassian_confession"),
    ("dobby_frostbite", "wisp_frostbite"),
    ("lucius_order", "magnus_order"),
    ("stolen_hellebore", "stolen_nightshade"),
    # Spell IDs
    ("homenum_revelio", "sense_presence"),
    ("specialis_revelio", "identify_substance"),
    ("prior_incantato", "echo_reading"),
    ("mnemonic_delving", "mnemonic_delving"),  # noop anchor
    ("legilimency", "mnemonic_delving"),
    ("raise_the_lamp", "raise_the_lamp"),  # noop
    ("revelio", "unveil"),
    ("lumos", "raise_the_lamp"),
    ("reparo", "mend"),
    # Spell display names
    ("Homenum Revelio", "Sense Presence"),
    ("Specialis Revelio", "Identify Substance"),
    ("Prior Incantato", "Echo Reading"),
    ("Legilimency", "Mnemonic Delving"),
    ("Legilimens", "Mnemonic Delver"),
    ("Revelio", "Unveil"),
    ("Lumos", "Raise the Lamp"),
    ("Reparo", "Mend"),
    # Characters (longer first)
    ("Severus Snape", "Professor Aldric Vane"),
    ("Professor Snape", "Professor Aldric Vane"),
    ("Lucius Malfoy", "Lord Magnus Thorne"),
    ("Hermione Granger", "Elena Marsh"),
    ("Draco Malfoy", "Cassian Thorne"),
    ("Mrs. Norris", "Morrigan"),
    ("Professor McGonagall", "Professor Whitmore"),
    ("McGonagall", "Professor Whitmore"),
    ("Heir of Slytherin", "Iron Lodge claimant"),
    ("Hand of Glory", "Thief's Candle"),
    ("Felix Felicis", "Fortune's Draught"),
    ("Chamber of Secrets", "The Hollow Below"),
    ("Ministry of Magic", "Crown Occult Bureau"),
    ("Restricted Section", "Sealed Stacks"),
    ("Diagon Alley", "Candlewick Lane"),
    ("Harry Potter", "Victorian occult detective"),
    ("house-elf", "bound familiar"),
    ("house_elf", "bound_familiar"),
    ("Muggle-born", "uninitiated-born"),
    ("Potions Master", "Alchemy Master"),
    ("Blackwood Collegiate", "Blackwood Collegiate"),  # noop
    ("Hogwarts", "Blackwood Collegiate"),
    ("Gringotts", "Ironwright Vaults"),
    ("Gryffindor", "Scarlet Court"),
    ("Slytherin", "Iron Lodge"),
    ("Ravenclaw", "Candlewick"),
    ("Hufflepuff", "Ashford"),
    ("Azkaban", "Dreadmoor Penitentiary"),
    ("Butterbeer", "spiced ale"),
    ("Quidditch", "sky-hunt"),
    ("Galleons", "sovereigns"),
    ("Galleon", "sovereign"),
    ("Muggle", "Uninitiated"),
    ("Squib", "Null-blooded"),
    ("Dumbledore", "Headmaster Ashford"),
    ("Malfoy", "Thorne"),
    ("Hermione", "Elena"),
    ("Snape", "Professor Vane"),
    ("Draco", "Cassian"),
    ("Dobby", "Wisp"),
    ("Filch", "Mr. Crankshaw"),
    ("MOODY:", "GRAVES:"),
    ("Moody", "Graves"),
    ("moody", "graves"),
    ("Potions", "Alchemy"),
    ("petrification", "paralytic binding"),
    ("petrified", "held in stillness"),
    ("petrify", "bind in stillness"),
    ("Petrification", "Paralytic binding"),
    ("Petrified", "Held in stillness"),
    ("wandlight", "lamplight"),
    ("wand history", "focus history"),
    ("Wand history", "Focus history"),
    ("Auror", "Lantern Inspector"),
    ("auror", "lantern_inspector"),
    # Witness IDs in YAML
    ('speaker: "moody"', 'speaker: "graves"'),
    ("mcgonagall", "whitmore"),
    ("hermione", "elena"),
    ("draco", "cassian"),
    ("dobby", "wisp"),
    ("snape", "vane"),
    ("filch", "crankshaw"),
    ("lucius", "magnus"),
    # Docker / infra
    ("auror-backend", "lantern-backend"),
    ("auror-frontend", "lantern-frontend"),
    ("auror-network", "lantern-network"),
    ("auror-saves", "lantern-saves"),
    ("Auror investigations", "Lantern investigations"),
    ("cast spells", "perform rites"),
    ("Cast Spells", "Perform Rites"),
    ("spell reference", "rite reference"),
    ("Spell reference", "Rite reference"),
    ("investigation spells", "investigation rites"),
    ("Investigation Spells", "Investigation Rites"),
    ("7 Investigation Spells", "7 Investigation Rites"),
    ("7 investigation spells", "7 investigation rites"),
    ("7 spells", "7 rites"),
    ("Magic System", "Rite System"),
    ("magic system", "rite system"),
    ("Cast 7 investigation spells", "Perform 7 investigation rites"),
    ("© J.K. Rowling", ""),
    ("Harry Potter fans", "detective game enthusiasts"),
    ("Harry Potter universe", "original Victorian occult setting"),
    ("Harry Potter Investigation Game", "The Lantern Investigation Game"),
    ("Harry Potter detective game", "Victorian occult detective game"),
    ("Setting:** Harry Potter Universe", "Setting:** Victorian Occult Britain"),
    ("magical mysteries at Hogwarts", "occult mysteries at Blackwood Collegiate"),
    ("solving magical mysteries", "solving occult mysteries"),
    ("magical crimes", "occult crimes"),
    ("magical Britain", "hidden Britain"),
    ("magical discharge", "etheric discharge"),
    ("dark magic", "forbidden craft"),
    ("Dark magic", "Forbidden craft"),
    ("dark artifact", "cursed artifact"),
    ("Dark artifact", "Cursed artifact"),
    ("wizard artifact", "scholar's artifact"),
    ("wizards", "initiates"),
    ("Wizards", "Initiates"),
    ("wizard", "initiate"),
    ("Wizard", "Initiate"),

    ("charms", "cantrips"),
    ("Charms", "Cantrips"),
    ("Transfiguration", "Transmutation"),
    ("Defense Against Dark Arts", "Warding Against the Unseen"),
    ("N.E.W.T.s", "Final Examinations"),
    ("Wingardium Leviosa", "Levitation Cantrip"),
    ("Obliviate", "Memory Veil"),
    ("Alohomora", "Lock Whisper"),
    ("Finite Incantatem", "Dispel"),
    ("Protego Totalum", "Ward Circle"),
    ("Order of Merlin", "Order of the Lantern"),
    ("Wizengamot", "Occult Bench"),
    ("Department of Mysteries", "Department of Veiled Studies"),
    ("Constant vigilance", "Trust nothing unseen"),
    ("Order of the Phoenix", "Lantern Circle"),
    ("The Restricted Section", "The Sealed Stacks"),
    # Second pass cleanup
    ("AUROR ACADEMY", "THE LANTERN"),
    ("AUROR HANDBOOK // SPELL INDEX", "LANTERN COMPENDIUM // RITE INDEX"),
    ("MOODY'S QUERY:", "GRAVES'S QUERY:"),
    ("MOODY'S VOICE INTEGRATION", "GRAVES'S VOICE INTEGRATION"),
    ("MOODY LLM FEEDBACK TEST", "GRAVES LLM FEEDBACK TEST"),
    ("MOCKED MOODY FEEDBACK", "MOCKED GRAVES FEEDBACK"),
    ("cassian_malfoy", "cassian_thorne"),
    ("cassian malfoy", "cassian thorne"),
    ("wand_signature", "focus_signature"),
    ("wand_evidence", "focus_evidence"),
    ("missing_wand_defensive_posture", "missing_focus_defensive_posture"),
    ("helena_wand_attempt", "helena_focus_attempt"),
    ("flints_wand_result", "flints_focus_result"),
    ("vectors_wand_result", "vectors_focus_result"),
    ("wand_dust", "focus_dust"),
    ("second_wand", "second_focus"),
    ("victim_wand", "victim_focus"),
    ("malfoy's things", "thorne's things"),
    ("malfoy orders", "thorne orders"),
    ("EVIDENCE THE AUROR HAS SHOWN YOU", "EVIDENCE THE LANTERN INSPECTOR HAS SHOWN YOU"),
    ("displays MOODY label", "displays GRAVES label"),
    ("speaker name (MOODY or YOU)", "speaker name (GRAVES or YOU)"),
    ("HERMIONE", "ELENA"),
    ("slytherins hexing", "iron lodge hexing"),
    ("prior incantato", "echo reading"),
    ("Prior Incantato", "Echo Reading"),
    ("slytherin_common_room", "iron_lodge_common_room"),
    ("slytherin common room", "iron lodge common room"),
    ("slytherin room", "iron lodge room"),
    ("HOGWARTS", "BLACKWOOD COLLEGIATE"),
    ("TO MOODY", "TO GRAVES"),
    ("wand_last_spell_signature", "focus_last_spell_signature"),
    ("cast REVELIO", "cast Unveil"),
    ("cast revelio", "cast unveil"),
    ("REVELIO", "UNVEIL"),
    ("ReVeLiO", "UnVeil"),
    ("No wands lying around. Marcus has his own focus. Any other wands would be at the crime scene.", "No spare focuses lying around. Marcus has his own. Any other focuses would be at the crime scene."),
    ("teaching_neville", "tutoring_a_peer"),
    ("bare wands", "bare focuses"),
    # Fourth pass — remaining narrative IP
    ("Neville Longbottom", "Rowan Ashford"),
    ("Petrificus Totalus", "Binding Cantrip"),
    ("Professor Flitwick", "Professor Langley"),
    ("Chamber Emergency", "Hollow Below emergency"),
    ("Chamber entrance", "Hollow Below entrance"),
    ("Chamber situation", "Hollow Below situation"),
    ("Chamber attacks", "Hollow Below attacks"),
    ("the Chamber", "the Hollow Below"),
    ("The Chamber", "The Hollow Below"),
    ("CHAMBER", "HOLLOW BELOW"),
    ("Black Lake", "Greymere"),
    ('silver "DM"', 'silver "CT"'),
    ("FILCH", "CRANKSHAW"),
    ("SQUIB", "NULL-BLOODED"),
    ("Winky", "Pippa"),
    ("Protego", "Ward Cantrip"),
    ("Neville", "Rowan"),
    ("teaching neville", "tutoring rowan"),
    ("teaching Neville", "tutoring Rowan"),
    ("Teaching Neville", "Tutoring Rowan"),
    ("Hellebore", "Nightshade"),
    ("hellebore", "nightshade"),
    ("malfoy", "thorne"),
    # Fifth pass — corner cases & metadata
    ("lantern_inspector-backend", "lantern-backend"),
    ("lantern_inspector-frontend", "lantern-frontend"),
    ("lantern_inspector-network", "lantern-network"),
    ("lantern_inspector-saves", "lantern-saves"),
    ("DOBBY'S ANNOTATION", "WISP'S ANNOTATION"),
    ("DRACO'S CONFESSION", "CASSIAN'S CONFESSION"),
    ("Miss Granger", "Miss Marsh"),
    ("initiateing", "initiate"),
    ("Kreacher", "Grimble"),
    ("Master Lucius", "Lord Magnus"),
    ("Old Master Lucius", "Old Lord Magnus"),
    ("from Lucius", "from Magnus"),
    ("Lucius's", "Magnus's"),
    ("Lucius ", "Magnus "),
    ("Lucius,", "Magnus,"),
    ("Lucius.", "Magnus."),
    ("Lucius ordered", "Magnus ordered"),
    ("Lucius sent", "Magnus sent"),
    ("Lucius will", "Magnus will"),
    ("Lucius had", "Magnus had"),
    ("Lucius also", "Magnus also"),
    ("against Lucius", "against Magnus"),
    ("Speaking against Lucius", "Speaking against Magnus"),
    ("son of Lucius", "son of Magnus"),
    ("Severus", "Aldric"),
    ("House-elf", "Bound familiar"),
    ("house-elves", "bound familiars"),
    ("House-elves", "Bound familiars"),
    ("house-elf", "bound familiar"),
    ("House elf", "Bound familiar"),
    ("pince_confiscation_log", "hawthorne_confiscation_log"),
    ("madam_pince", "miss_hawthorne"),
    ("Madam Pince", "Miss Hawthorne"),
    ("pince_office", "librarian_office"),
    ("pince_reveals", "hawthorne_reveals"),
    ("pince_observes", "hawthorne_observes"),
    ("pince_as_killer", "hawthorne_as_killer"),
    (" distract pince", " distract Hawthorne"),
    ("hand_of_glory", "thief_candle"),
    ("received_hand_of_glory", "received_thief_candle"),
    ("occlumency_skill", "mind_shield_skill"),
    ("Occlumency", "Mind shield"),
    ("occlumency", "mind_shield"),
    ("apparate", "slip through wards"),

    ("finite incantatem", "dispel"),
    ("Finite Incantatem", "Dispel"),
    ("hagrid_hut", "groundskeeper_cottage"),
    ("hagrid", "groundskeeper"),
    ("muggleborn", "uninitiated-born"),
    ("muggle_influence", "mundane_influence"),
    ("muggleborn_advocacy", "uninitiated_advocacy"),
    ("muggleborn_restitution", "uninitiated_restitution"),
    ("muggleborn_business", "uninitiated_business"),
    ("hogwarts_curriculum", "collegiate_curriculum"),
    ("hogwarts:", "blackwood_collegiate:"),
    ("quidditch_pitch", "sky_hunt_pitch"),
    ("quidditch_stadium", "sky_hunt_arena"),
    ("quidditch_betting", "sky_hunt_betting"),
    ("quidditch_corruption", "sky_hunt_corruption"),
    ("Potter connection", "Lantern legacy"),
    ("AUROR'S HANDBOOK", "LANTERN COMPENDIUM"),
    ("LEGILIMENCY", "MNEMONIC DELVING"),
    ("LUMOS", "RAISE THE LAMP"),
    ("foreign_lantern_inspector", "foreign_lantern"),
    ("senior_lantern_inspector_dawlish", "senior_inspector_hartley"),
    ("lantern_inspector_proudfoot", "inspector_proudfoot"),
    ("lantern_inspector_office", "lantern_office"),
    ("lantern_inspectors_handbook", "lantern_compendium"),
]

# Regex replacements: (pattern, replacement, optional flags)
REGEX_REPLACEMENTS: list[tuple[str, str, int]] = [
    (r"\bWand\b", "Focus", 0),
    (r"\bwand\b", "focus", 0),
    (r"\bLegilimens\b", "Mnemonic Delver", 0),
    (r"\blegilimens\b", "mnemonic delving", 0),
    (r"\bScarpin\b", "Alchemist", 0),
    (r"\bscarpin\b", "alchemist", 0),
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
    ".conf",
    ".json",
    ".toml",
    ".html",
    ".css",
    ".txt",
    ".example",
    ".env",
    ".lock",
    ".tsv",
    ".csv",
}


def should_process(path: Path) -> bool:
    if path.name in SKIP_FILES:
        return False
    for part in path.parts:
        if part in SKIP_DIRS:
            return False
    if path.suffix and path.suffix not in TEXT_EXTENSIONS and path.name not in {
        "Caddyfile",
        "Dockerfile",
        "Dockerfile.frontend",
        "CLAUDE.md",
        "README.md",
        "STATUS.md",
        ".env.production.example",
    }:
        if path.suffix in {".png", ".jpg", ".webp", ".gif", ".db", ".jsonl"}:
            return False
    return True


def migrate_text(text: str) -> str:
    for old, new in LITERAL_REPLACEMENTS:
        if old == new:
            continue
        text = text.replace(old, new)
    for pattern, repl, flags in REGEX_REPLACEMENTS:
        text = re.sub(pattern, repl, text, flags=flags)
    return text


def main() -> int:
    changed: list[Path] = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or not should_process(path):
            continue
        try:
            original = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        updated = migrate_text(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            changed.append(path)

    print(f"Updated {len(changed)} files")
    for p in changed[:50]:
        print(f"  {p.relative_to(ROOT)}")
    if len(changed) > 50:
        print(f"  ... and {len(changed) - 50} more")
    return 0


if __name__ == "__main__":
    sys.exit(main())