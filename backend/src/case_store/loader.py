"""YAML case file loader.

Loads case definitions from YAML files in the case_store directory.

Phase 5.4: Added case discovery and validation for "drop YAML -> case works" workflow.
"""

import logging
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from src.state.player_state import CaseMetadata

logger = logging.getLogger(__name__)

# Case store directory (same directory as this file)
CASE_STORE_DIR = Path(__file__).parent

# In-memory cache for parsed YAML case files (invalidated when file mtime changes)
_case_cache: dict[str, dict[str, Any]] = {}
_case_mtime: dict[str, float] = {}
_evidence_index_cache: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
_locale_cache: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}

_LOCALE_LIST_KEYS = {"witnesses", "hidden_evidence", "additional_evidence", "choices", "secrets"}
_LOCALE_TEXT_LIST_KEYS = {
    "knowledge",
    "surface_elements",
    "general_knowledge",
    "keywords",
    "deductions_required",
    "correct_reasoning_requires",
    "suspects",
}
_LOCALE_INDEXED_LIST_PATHS = {
    ("case", "timeline"),
    ("case", "briefing_context", "witnesses"),
    ("case", "post_verdict", "correct", "confrontation"),
    ("case", "post_verdict", "incorrect"),
}
_PROTECTED_LOCALE_KEYS = {
    "triggers",
    "trigger",
    "condition",
    "culprit",
    "key_evidence",
    "evidence",
    "suspect_accused",
    "confrontation_anyway",
    "strength",
    "points_to",
    "tag",
    "spell_contexts",
    "available_spells",
    "special_interactions",
}


def load_case(case_id: str) -> dict[str, Any]:
    """Load a case definition from YAML (cached until file changes on disk).

    Args:
        case_id: Case identifier (e.g., "case_001")

    Returns:
        Case dictionary with locations, evidence, triggers

    Raises:
        FileNotFoundError: If case file doesn't exist
        yaml.YAMLError: If YAML is malformed
        ValueError: If case_id contains invalid characters
    """
    # Security: Sanitize case_id to prevent path traversal
    if not re.match(r"^[a-zA-Z0-9_]+$", case_id):
        raise ValueError(f"Invalid case_id format: {case_id}")

    case_path = CASE_STORE_DIR / f"{case_id}.yaml"

    if not case_path.exists():
        raise FileNotFoundError(f"Case file not found: {case_path}")

    mtime = case_path.stat().st_mtime
    if case_id in _case_cache and _case_mtime.get(case_id) == mtime:
        return _case_cache[case_id]

    with open(case_path, encoding="utf-8") as f:
        data: dict[str, Any] = yaml.safe_load(f)

    is_valid, errors, _warnings = validate_case(data, case_id)
    if not is_valid:
        msg = "; ".join(errors[:5])
        raise ValueError(f"Invalid case {case_id}: {msg}")

    _case_cache[case_id] = data
    _case_mtime[case_id] = mtime
    return data


def _merge_locale_values(
    base: Any,
    overlay: Any,
    *,
    path: tuple[str, ...] = (),
) -> Any:
    """Merge authored locale text into canonical case data.

    Locale files use dictionaries keyed by stable IDs for list-shaped case
    sections. This prevents translations from drifting when evidence order
    changes in the English source file.
    """
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = deepcopy(base)
        for key, value in overlay.items():
            if key in _PROTECTED_LOCALE_KEYS:
                raise ValueError(f"Locale cannot override mechanics at {'.'.join(path + (key,))}")
            if key not in merged:
                raise ValueError(f"Locale key does not exist at {'.'.join(path + (key,))}")
            merged[key] = _merge_locale_values(merged[key], value, path=path + (key,))
        return merged

    if isinstance(base, list) and isinstance(overlay, dict):
        if not path or path[-1] not in _LOCALE_LIST_KEYS:
            raise ValueError(
                f"Locale list override must use a stable-ID section at {'.'.join(path)}"
            )
        by_id = {str(item.get("id")): item for item in base if isinstance(item, dict) and item.get("id")}
        merged = deepcopy(base)
        for item_id, item_overlay in overlay.items():
            if item_id not in by_id:
                raise ValueError(f"Locale ID does not exist at {'.'.join(path)}: {item_id}")
            if not isinstance(item_overlay, dict):
                raise ValueError(f"Locale entry must be a mapping at {'.'.join(path + (item_id,))}")
            index = next(i for i, item in enumerate(merged) if item.get("id") == item_id)
            merged[index] = _merge_locale_values(
                merged[index], item_overlay, path=path + (item_id,)
            )
        return merged

    if isinstance(base, list) and isinstance(overlay, list):
        if path in _LOCALE_INDEXED_LIST_PATHS or (path and path[-1] == "not_present"):
            if len(base) != len(overlay):
                raise ValueError(f"Locale list length mismatch at {'.'.join(path)}")
            merged = deepcopy(base)
            for index, item_overlay in enumerate(overlay):
                if not isinstance(item_overlay, dict) or not isinstance(base[index], dict):
                    raise ValueError(f"Locale entry must be a mapping at {'.'.join(path)}[{index}]")
                merged[index] = _merge_locale_values(
                    base[index], item_overlay, path=path + (str(index),)
                )
            return merged
        if not path or path[-1] not in _LOCALE_TEXT_LIST_KEYS:
            raise ValueError(f"Locale list override is not text-only at {'.'.join(path)}")
        if not all(isinstance(item, str) for item in overlay):
            raise ValueError(f"Locale text list contains non-text at {'.'.join(path)}")
        return overlay

    if isinstance(base, str) and isinstance(overlay, str):
        return overlay

    raise ValueError(f"Locale type mismatch at {'.'.join(path)}")


def load_localized_case(case_id: str, language: str = "en") -> dict[str, Any]:
    """Return canonical case with locale-authored player text merged in.

    English remains the canonical source. Russian has an explicit locale file;
    other legacy languages keep the existing English-authored static content
    until their authored overlays are added.
    """
    base = load_case(case_id)
    if language == "en":
        return base
    if not re.match(r"^[a-zA-Z]{2}$", language):
        raise ValueError(f"Invalid language: {language}")

    locale_path = CASE_STORE_DIR / "locales" / language / f"{case_id}.yaml"
    if not locale_path.exists():
        # Existing non-EN languages currently localize generated narration only.
        # Keep their legacy behavior until authored case overlays exist.
        if language != "ru":
            return base
        raise FileNotFoundError(f"Locale not found for {case_id}: {language}")

    cache_key = (case_id, language)
    mtime = locale_path.stat().st_mtime
    cached = _locale_cache.get(cache_key)
    if cached and cached[0] == mtime:
        return cached[1]

    with open(locale_path, encoding="utf-8") as f:
        overlay: dict[str, Any] = yaml.safe_load(f) or {}
    if not isinstance(overlay, dict) or set(overlay) != {"case"}:
        raise ValueError(f"Invalid locale wrapper in {locale_path}")
    overlay_case = overlay["case"]
    base_case = get_case_section(base)
    if overlay_case.get("id") != base_case.get("id"):
        raise ValueError(f"Locale case.id mismatch in {locale_path}")

    merged = _merge_locale_values(base, overlay)
    _locale_cache[cache_key] = (mtime, merged)
    return merged


def get_case_section(case_data: dict[str, Any]) -> dict[str, Any]:
    """Return the inner ``case`` dict from loaded case data."""
    return case_data.get("case", case_data)


def get_case_setting(case_data: dict[str, Any]) -> str:
    """Human-readable setting for narrator/witness prompt framing.

    Prefer explicit ``setting`` in case YAML; fall back to title.
    """
    case = get_case_section(case_data)
    setting = case.get("setting")
    if setting and str(setting).strip():
        return str(setting).strip()
    title = case.get("title")
    if title:
        return str(title).strip()
    return "a Crown Occult Bureau investigation"


def get_crime_scene_label(case_data: dict[str, Any]) -> str:
    """Display name of the primary crime scene for witness prompts."""
    case = get_case_section(case_data)
    if scene := case.get("crime_scene"):
        return str(scene).strip()

    locations: dict[str, dict[str, Any]] = case.get("locations", {})
    for loc_id in ("library", "sealed_stacks", "crime_scene"):
        if loc_id in locations:
            return locations[loc_id].get("name", "the crime scene")
    if locations:
        return next(iter(locations.values())).get("name", "the crime scene")
    return "the crime scene"


def get_location(case_data: dict[str, Any], location_id: str) -> dict[str, Any]:
    """Get a specific location from case data.

    Args:
        case_data: Loaded case dictionary
        location_id: Location identifier (e.g., "library")

    Returns:
        Location dictionary with description, evidence, not_present, witnesses_present

    Raises:
        KeyError: If location doesn't exist
    """
    case: dict[str, Any] = case_data.get("case", case_data)
    locations: dict[str, dict[str, Any]] = case.get("locations", {})

    if location_id not in locations:
        raise KeyError(f"Location not found: {location_id}")

    location = dict(locations[location_id])

    # Ensure witnesses_present field exists (backward compatibility)
    if "witnesses_present" not in location:
        location["witnesses_present"] = []

    return location


def count_hidden_evidence(case_data: dict[str, Any]) -> int:
    """Count discoverable hidden evidence across all locations in a case."""
    return max(len(build_evidence_index(case_data)), 1)


def build_evidence_index(case_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build evidence ID → metadata index for O(1) lookups."""
    case_inner: dict[str, Any] = case_data.get("case", case_data)
    index: dict[str, dict[str, Any]] = {}
    for loc_id, location in case_inner.get("locations", {}).items():
        for evidence in location.get("hidden_evidence", []):
            eid = evidence.get("id")
            if not eid:
                continue
            index[eid] = {
                **evidence,
                "id": eid,
                "name": evidence.get("name", eid),
                "location_found": evidence.get("location_found", loc_id),
                "description": evidence.get("description", "").strip(),
            }
    for evidence in case_inner.get("additional_evidence", []):
        eid = evidence.get("id")
        if eid:
            index[eid] = {
                **evidence,
                "id": eid,
                "name": evidence.get("name", eid),
                "location_found": evidence.get("location_found", "unknown"),
                "description": evidence.get("description", "").strip(),
            }
    return index


def get_evidence_index(case_id: str, case_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Cached evidence index, isolated per canonical or localized case object."""
    cache_key = (case_id, id(case_data))
    cached = _evidence_index_cache.get(cache_key)
    if cached is not None:
        return cached
    index = build_evidence_index(case_data)
    _evidence_index_cache[cache_key] = index
    return index


def get_evidence_details_for_ids(
    case_id: str,
    case_data: dict[str, Any],
    evidence_ids: list[str],
) -> list[dict[str, Any]]:
    """Resolve discovered evidence IDs without scanning all locations."""
    index = get_evidence_index(case_id, case_data)
    return [index[eid] for eid in evidence_ids if eid in index]


def get_first_location_id(case_data: dict[str, Any]) -> str:
    """Get the first location ID from case data.

    Args:
        case_data: Loaded case dictionary

    Returns:
        First location ID (e.g., "library")

    Raises:
        ValueError: If case has no locations
    """
    case: dict[str, Any] = case_data.get("case", case_data)
    locations: dict[str, dict[str, Any]] = case.get("locations", {})

    if not locations:
        raise ValueError("Case has no locations defined")

    return next(iter(locations))


def list_cases() -> list[str]:
    """List all available case IDs.

    Returns:
        List of case IDs (without .yaml extension)
    """
    return [p.stem for p in CASE_STORE_DIR.glob("*.yaml")]


def load_witnesses(case_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Load witnesses from case data as a dict keyed by witness ID.

    Args:
        case_data: Loaded case dictionary

    Returns:
        Dictionary of witness_id -> witness data
    """
    case: dict[str, Any] = case_data.get("case", case_data)
    witnesses_list: list[dict[str, Any]] = case.get("witnesses", [])

    return {w["id"]: w for w in witnesses_list if "id" in w}


def get_witness(case_data: dict[str, Any], witness_id: str) -> dict[str, Any]:
    """Get a specific witness from case data.

    Args:
        case_data: Loaded case dictionary
        witness_id: Witness identifier (e.g., "elena", "cassian")

    Returns:
        Witness dictionary with personality, knowledge, secrets, lies

    Raises:
        KeyError: If witness doesn't exist
    """
    witnesses = load_witnesses(case_data)

    if witness_id not in witnesses:
        raise KeyError(f"Witness not found: {witness_id}")

    return witnesses[witness_id]


def list_witnesses(case_data: dict[str, Any]) -> list[str]:
    """List all witness IDs in a case.

    Args:
        case_data: Loaded case dictionary

    Returns:
        List of witness IDs
    """
    witnesses = load_witnesses(case_data)
    return list(witnesses.keys())


def get_evidence_by_id(
    case_data: dict[str, Any],
    location_id: str | None,
    evidence_id: str,
) -> dict[str, Any] | None:
    """Get evidence item by ID with full metadata.

    Args:
        case_data: Loaded case dictionary
        location_id: Location identifier (None to search all locations)
        evidence_id: Evidence identifier

    Returns:
        Evidence dict with name, location_found, description, etc. or None if not found
    """
    case: dict[str, Any] = case_data.get("case", case_data)
    locations_map: dict[str, dict[str, Any]] = case.get("locations", {})

    # Determine which locations to search
    search_locations: list[tuple[str, dict[str, Any]]] = []

    if location_id is None:
        return build_evidence_index(case_data).get(evidence_id)

    if location_id:
        # Search specific location
        if location_id in locations_map:
            search_locations.append((location_id, locations_map[location_id]))
        else:
            # If specified location doesn't exist, we can't find it there
            # (matches original behavior of implicitly failing or raising key error if we called get_location)
            # But get_location raises KeyError. Let's try to be safe.
            try:
                loc = get_location(case_data, location_id)
                search_locations.append((location_id, loc))
            except KeyError:
                return None
    else:
        # Search all locations
        for loc_id, loc_data in locations_map.items():
            search_locations.append((loc_id, loc_data))

    # Iterate through selected locations
    for loc_id, location in search_locations:
        hidden_evidence = location.get("hidden_evidence", [])

        for evidence in hidden_evidence:
            if evidence.get("id") == evidence_id:
                # Ensure all metadata fields exist (backward compatibility)
                return {
                    "id": evidence.get("id", ""),
                    "name": evidence.get("name", evidence.get("id", "Unknown")),
                    "location_found": evidence.get("location_found", loc_id),
                    "description": evidence.get("description", "").strip(),
                    "type": evidence.get("type", "unknown"),
                    "triggers": evidence.get("triggers", []),
                    "tag": evidence.get("tag", ""),
                }

    return None


def get_all_evidence(
    case_data: dict[str, Any],
    location_id: str | None,
) -> list[dict[str, Any]]:
    """Get all evidence items from a location (or all locations) with full metadata.

    Args:
        case_data: Loaded case dictionary
        location_id: Location identifier (None for all locations)

    Returns:
        List of evidence dicts with name, location_found, description
    """
    case: dict[str, Any] = case_data.get("case", case_data)
    locations_map: dict[str, dict[str, Any]] = case.get("locations", {})

    # Determine which locations to search
    search_locations: list[tuple[str, dict[str, Any]]] = []

    if location_id:
        if location_id in locations_map:
            search_locations.append((location_id, locations_map[location_id]))
        else:
            try:
                # Try fallback just in case
                loc = get_location(case_data, location_id)
                search_locations.append((location_id, loc))
            except KeyError:
                return []
    else:
        # Search all locations
        for loc_id, loc_data in locations_map.items():
            search_locations.append((loc_id, loc_data))

    result = []
    for loc_id, location in search_locations:
        hidden_evidence = location.get("hidden_evidence", [])
        for evidence in hidden_evidence:
            result.append(
                {
                    "id": evidence.get("id", ""),
                    "name": evidence.get("name", evidence.get("id", "Unknown")),
                    "location_found": evidence.get("location_found", loc_id),
                    "description": evidence.get("description", "").strip(),
                    "type": evidence.get("type", "unknown"),
                    "triggers": evidence.get("triggers", []),
                    "tag": evidence.get("tag", ""),
                }
            )

    return result


def load_solution(case_data: dict[str, Any]) -> dict[str, Any]:
    """Load solution from case data.

    Args:
        case_data: Loaded case dictionary

    Returns:
        Solution dict with culprit, method, motive, key_evidence, deductions_required
    """
    case: dict[str, Any] = case_data.get("case", case_data)
    return case.get("solution", {})


def load_wrong_suspects(case_data: dict[str, Any]) -> dict[str, Any]:
    """Load wrong suspects dict from case data.

    Args:
        case_data: Loaded case dictionary

    Returns:
        Dict of wrong suspect_id -> data (with why_innocent, graves_response, etc).
        Empty dict if absent.
    """
    case: dict[str, Any] = case_data.get("case", case_data)
    suspects = case.get("wrong_suspects", {})
    return suspects if isinstance(suspects, dict) else {}


def load_confrontation(
    case_data: dict[str, Any],
    accused_id: str,
    correct: bool,
) -> dict[str, Any] | None:
    """Load confrontation dialogue.

    Args:
        case_data: Full case data
        accused_id: Who player accused
        correct: Whether verdict was correct

    Returns:
        {
            "dialogue": [{"speaker": str, "text": str, "tone": str}],
            "aftermath": str,
        }
        or None if no confrontation available
    """
    case: dict[str, Any] = case_data.get("case", case_data)
    post_verdict = case.get("post_verdict", {})

    if correct:
        correct_data = post_verdict.get("correct", {})
        dialogue = correct_data.get("confrontation", [])
        aftermath = correct_data.get("aftermath", "")
        if dialogue or aftermath:
            return {
                "dialogue": dialogue,
                "aftermath": aftermath,
            }
        return None
    else:
        # Check if we show confrontation anyway for wrong verdict
        incorrect_list = post_verdict.get("incorrect", [])
        for item in incorrect_list:
            if item.get("suspect_accused", "").lower() == accused_id.lower():
                if item.get("confrontation_anyway", False):
                    # Show real culprit confrontation (educational)
                    correct_data = post_verdict.get("correct", {})
                    return {
                        "dialogue": correct_data.get("confrontation", []),
                        "aftermath": correct_data.get("aftermath", ""),
                    }
        return None


def load_mentor_templates(case_data: dict[str, Any]) -> dict[str, Any]:
    """Load mentor feedback templates from case data.

    Args:
        case_data: Loaded case dictionary

    Returns:
        Templates dict with fallacies, reasoning_quality, wrong_suspect_responses
    """
    case: dict[str, Any] = case_data.get("case", case_data)
    return case.get("mentor_feedback_templates", {})


def load_wrong_verdict_info(
    case_data: dict[str, Any],
    accused_id: str,
) -> dict[str, Any] | None:
    """Load info for wrong verdict accusation.

    Args:
        case_data: Loaded case dictionary
        accused_id: Who player (wrongly) accused

    Returns:
        Dict with reveal, teaching_moment, confrontation_anyway, or None if not found
    """
    case: dict[str, Any] = case_data.get("case", case_data)
    post_verdict = case.get("post_verdict", {})
    incorrect_list = post_verdict.get("incorrect", [])

    for item in incorrect_list:
        if item.get("suspect_accused", "").lower() == accused_id.lower():
            return {
                "reveal": item.get("reveal", ""),
                "teaching_moment": item.get("teaching_moment", ""),
                "confrontation_anyway": item.get("confrontation_anyway", False),
            }

    return None


def list_locations(case_data: dict[str, Any]) -> list[dict[str, str]]:
    """List all locations in a case with metadata.

    Args:
        case_data: Loaded case dictionary

    Returns:
        List of location dicts with id, name, type
    """
    case: dict[str, Any] = case_data.get("case", case_data)
    locations: dict[str, dict[str, Any]] = case.get("locations", {})

    result = []
    for location_id, location in locations.items():
        result.append(
            {
                "id": location.get("id", location_id),
                "name": location.get("name", "Unknown"),
                "type": location.get("type", "micro"),
            }
        )
    return result


# ============================================================================
# Phase 5.4: Case Discovery and Validation
# ============================================================================


def validate_case(
    case_dict: dict[str, Any],
    case_id: str,
) -> tuple[bool, list[str], list[str]]:
    """Validate case has required fields.

    Phase 5.4 Checks (errors - block loading):
    - case.id exists and matches filename
    - case.title exists
    - case.difficulty exists and is valid
    - At least 1 location
    - At least 1 witness
    - At least 1 evidence item across all locations
    - solution.culprit exists and matches a witness ID
    - briefing.case_assignment exists
    - briefing.teaching_question exists

    Phase 5.5 Checks (errors if present, warnings for recommended):
    - If victim section present -> victim.name required
    - If witness has wants but not fears (or vice versa) -> error
    - If evidence.strength exists and not 0-100 integer -> error
    - If timeline entry exists but missing time/event -> error

    Args:
        case_dict: Loaded YAML case data
        case_id: Expected case ID (from filename)

    Returns:
        Tuple of (is_valid, errors, warnings)
        - errors: Blocking issues (case won't load)
        - warnings: Optional fields missing (case loads but logs)
    """
    errors: list[str] = []
    warnings: list[str] = []
    case = case_dict.get("case", {})

    # Required: case.id
    yaml_case_id = case.get("id")
    if not yaml_case_id:
        errors.append("Missing required field: case.id")
    elif yaml_case_id != case_id:
        errors.append(f"case.id '{yaml_case_id}' does not match filename '{case_id}'")

    # Required: case.title
    if not case.get("title"):
        errors.append("Missing required field: case.title")

    # Required: case.difficulty (must be valid value)
    difficulty = case.get("difficulty")
    if not difficulty:
        errors.append("Missing required field: case.difficulty")
    elif difficulty not in ("beginner", "intermediate", "advanced"):
        errors.append(
            f"Invalid case.difficulty: '{difficulty}' (must be beginner/intermediate/advanced)"
        )

    # Required: at least 1 location
    locations = case.get("locations", {})
    if not locations:
        errors.append("Must have at least 1 location (case.locations)")

    # Required: at least 1 witness
    witnesses = case.get("witnesses", [])
    if not witnesses:
        errors.append("Must have at least 1 witness (case.witnesses)")

    # Collect witness IDs for culprit validation
    witness_ids = {w.get("id") for w in witnesses if w.get("id")}

    # Required: at least 1 evidence item across all locations
    evidence_count = 0
    for location in locations.values():
        hidden_evidence = location.get("hidden_evidence", [])
        evidence_count += len(hidden_evidence)
    if evidence_count == 0:
        errors.append("Must have at least 1 evidence item (locations.*.hidden_evidence)")

    # Required: solution.culprit (must match a witness ID)
    solution = case.get("solution", {})
    culprit = solution.get("culprit")
    if not culprit:
        errors.append("Missing required field: solution.culprit")
    elif culprit not in witness_ids:
        errors.append(f"solution.culprit '{culprit}' does not match any witness ID")

    # Required: briefing.dossier (formerly case_assignment)
    briefing = case.get("briefing", {})
    if not briefing.get("dossier") and not briefing.get("case_assignment"):
        errors.append("Missing required field: briefing.dossier (or legacy case_assignment)")

    # Required: briefing.teaching_questions (or legacy teaching_question)
    if not briefing.get("teaching_questions") and not briefing.get("teaching_question"):
        errors.append("Missing required field: briefing.teaching_questions")

    # =========================================================================
    # Phase 5.5: Enhanced YAML Schema Validation
    # =========================================================================

    # Victim validation (if section present)
    victim = case.get("victim")
    if victim:
        if not victim.get("name"):
            errors.append(
                "Missing required field: victim.name (victim section present but name not specified)"
            )
        if not victim.get("humanization"):
            warnings.append(
                "Missing recommended field: victim.humanization (adds emotional impact)"
            )

    # Witness validation (wants/fears consistency)
    for witness in witnesses:
        witness_id = witness.get("id", "unknown")
        has_wants = witness.get("wants")
        has_fears = witness.get("fears")

        # If one specified, both should be specified
        if has_wants and not has_fears:
            errors.append(
                f"Witness '{witness_id}': wants specified but fears missing "
                "(both required together)"
            )
        if has_fears and not has_wants:
            errors.append(
                f"Witness '{witness_id}': fears specified but wants missing "
                "(both required together)"
            )

        # Warn if moral_complexity missing when wants/fears present
        if (has_wants or has_fears) and not witness.get("moral_complexity"):
            warnings.append(
                f"Witness '{witness_id}': moral_complexity recommended for psychological depth"
            )

    # Evidence validation (strength range)
    for location_id, location in locations.items():
        evidence_list = location.get("hidden_evidence", [])
        for evidence in evidence_list:
            evidence_id = evidence.get("id", "unknown")
            strength = evidence.get("strength")

            if strength is not None:
                if not isinstance(strength, int) or strength < 0 or strength > 100:
                    errors.append(
                        f"Evidence '{evidence_id}': strength must be integer 0-100, got {strength}"
                    )

    # Timeline validation (time and event required for each entry)
    timeline = case.get("timeline", [])
    for i, entry in enumerate(timeline):
        if not entry.get("time"):
            errors.append(f"Timeline entry {i}: missing required field 'time'")
        if not entry.get("event"):
            errors.append(f"Timeline entry {i}: missing required field 'event'")

    return (len(errors) == 0, errors, warnings)


def discover_cases(
    case_dir: str | Path | None = None,
    language: str = "en",
) -> tuple[list[CaseMetadata], list[str]]:
    """Scan directory for case YAML files, validate, and extract metadata.

    Gracefully handles errors:
    - Malformed YAML: logs warning, skips file
    - Missing required fields: logs warning, skips file
    - Empty files: logs warning, skips file

    Args:
        case_dir: Directory to scan (defaults to CASE_STORE_DIR)

    Returns:
        Tuple of (list of CaseMetadata, list of error messages)
    """
    if case_dir is None:
        case_dir = CASE_STORE_DIR
    else:
        case_dir = Path(case_dir)

    cases: list[CaseMetadata] = []
    errors: list[str] = []

    if not case_dir.exists():
        logger.warning(f"Case directory not found: {case_dir}")
        return [], []

    # Scan for case_*.yaml files (sorted for consistent ordering)
    # Skip template files and hidden files
    yaml_files = sorted(
        f
        for f in case_dir.glob("case_*.yaml")
        if not f.name.startswith(".") and f.name != "case_template.yaml"
    )

    for yaml_file in yaml_files:
        case_id = yaml_file.stem  # "case_001.yaml" -> "case_001"

        try:
            # Load YAML safely
            with open(yaml_file, encoding="utf-8") as f:
                case_data = yaml.safe_load(f)

            # Handle empty file
            if case_data is None:
                error_msg = f"{case_id}: Empty YAML file"
                errors.append(error_msg)
                logger.warning(f"Skipped {case_id}: empty YAML file")
                continue

            # Validate case structure (Phase 5.5: now returns warnings too)
            is_valid, validation_errors, validation_warnings = validate_case(case_data, case_id)

            if not is_valid:
                error_msg = f"{case_id}: {'; '.join(validation_errors)}"
                errors.append(error_msg)
                logger.warning(f"Skipped {case_id}: validation failed - {validation_errors}")
                continue

            # Log warnings (don't block loading)
            for warning in validation_warnings:
                logger.warning(f"{case_id}: {warning}")

            # Extract metadata from the authored locale when requested.
            case_section = case_data.get("case", {})
            if language != "en" and case_dir == CASE_STORE_DIR:
                try:
                    case_section = get_case_section(load_localized_case(case_id, language))
                except FileNotFoundError:
                    if language == "ru":
                        # Do not show a Russian player an English-only case.
                        # Publish its authored overlay before making it selectable.
                        logger.info("Skipped %s from %s case list: locale missing", case_id, language)
                        continue
            metadata = CaseMetadata(
                id=case_section.get("id", case_id),
                title=case_section.get("title", "Untitled Case"),
                difficulty=case_section.get("difficulty", "beginner"),
                description=case_section.get("description", ""),
            )
            cases.append(metadata)
            logger.info(f"Discovered: {case_id}")

        except yaml.YAMLError as e:
            error_msg = f"{case_id}: YAML parse error"
            errors.append(error_msg)
            logger.error(f"Skipped {case_id}: YAML parse error - {e}")

        except Exception as e:
            error_msg = f"{case_id}: {str(e)}"
            errors.append(error_msg)
            logger.error(f"Skipped {case_id}: unexpected error - {e}")

    # Summary log
    logger.info(f"Case discovery: {len(cases)} valid, {len(errors)} errors")

    return cases, errors


def list_cases_with_metadata(language: str = "en") -> tuple[list[CaseMetadata], list[str]]:
    """List all cases with metadata (convenience wrapper).

    Returns:
        Tuple of (list of CaseMetadata, list of error messages)
    """
    return discover_cases(CASE_STORE_DIR, language=language)
