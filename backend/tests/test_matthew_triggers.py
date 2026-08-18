"""Tests for Matthew spirit companion legacy triggers (Phase 4).

Covers:
- Trigger condition parsing and evaluation
- Tier-based selection logic
- Rare trigger probability
- Fired trigger exclusion
- YAML loading
- API endpoint integration
"""

from unittest.mock import patch

import pytest

from src.context.matthew_triggers import (
    _check_condition,
    clear_trigger_cache,
    load_matthew_triggers,
    select_matthew_trigger,
)
from src.state.player_state import MatthewCompanionState


class TestConditionEvaluation:
    """Test evidence_count condition parsing and evaluation."""

    def test_check_condition_greater_than(self) -> None:
        """Test > operator."""
        assert _check_condition("evidence_count>3", 4) is True
        assert _check_condition("evidence_count>3", 3) is False
        assert _check_condition("evidence_count>3", 2) is False

    def test_check_condition_greater_than_or_equal(self) -> None:
        """Test >= operator."""
        assert _check_condition("evidence_count>=3", 4) is True
        assert _check_condition("evidence_count>=3", 3) is True
        assert _check_condition("evidence_count>=3", 2) is False

    def test_check_condition_equal(self) -> None:
        """Test == operator."""
        assert _check_condition("evidence_count==3", 3) is True
        assert _check_condition("evidence_count==3", 2) is False
        assert _check_condition("evidence_count==3", 4) is False

    def test_check_condition_less_than(self) -> None:
        """Test < operator."""
        assert _check_condition("evidence_count<3", 2) is True
        assert _check_condition("evidence_count<3", 3) is False
        assert _check_condition("evidence_count<3", 4) is False

    def test_check_condition_less_than_or_equal(self) -> None:
        """Test <= operator."""
        assert _check_condition("evidence_count<=3", 2) is True
        assert _check_condition("evidence_count<=3", 3) is True
        assert _check_condition("evidence_count<=3", 4) is False

    def test_check_condition_not_equal(self) -> None:
        """Test != operator."""
        assert _check_condition("evidence_count!=3", 2) is True
        assert _check_condition("evidence_count!=3", 4) is True
        assert _check_condition("evidence_count!=3", 3) is False

    def test_check_condition_empty_string(self) -> None:
        """Test empty condition always passes."""
        assert _check_condition("", 0) is True
        assert _check_condition("", 5) is True
        assert _check_condition("", 100) is True

    def test_check_condition_whitespace(self) -> None:
        """Test conditions with whitespace."""
        assert _check_condition("evidence_count >= 3", 4) is True
        assert _check_condition("evidence_count>= 3", 3) is True
        assert _check_condition("evidence_count >=3", 2) is False

    def test_check_condition_malformed(self) -> None:
        """Test malformed condition returns False."""
        assert _check_condition("invalid_condition", 5) is False
        assert _check_condition("evidence > 5", 10) is False
        assert _check_condition("count>=3", 5) is False


class TestTriggerSelection:
    """Test tier-based trigger selection logic."""

    @pytest.fixture
    def sample_triggers(self) -> dict[int, list[dict]]:
        """Create sample triggers for testing."""
        return {
            1: [
                {
                    "id": "t1_a",
                    "condition": "evidence_count<3",
                    "type": "helpful",
                    "text": "T1A",
                    "is_rare": False,
                },
                {
                    "id": "t1_b",
                    "condition": "evidence_count<3",
                    "type": "misleading",
                    "text": "T1B",
                    "is_rare": False,
                },
            ],
            2: [
                {
                    "id": "t2_a",
                    "condition": "evidence_count>=3",
                    "type": "helpful",
                    "text": "T2A",
                    "is_rare": False,
                },
                {
                    "id": "t2_b",
                    "condition": "evidence_count>=4",
                    "type": "misleading",
                    "text": "T2B",
                    "is_rare": False,
                },
                {
                    "id": "t2_rare",
                    "condition": "evidence_count>=3",
                    "type": "helpful",
                    "text": "T2RARE",
                    "is_rare": True,
                },
            ],
            3: [
                {
                    "id": "t3_a",
                    "condition": "evidence_count>=6",
                    "type": "helpful",
                    "text": "T3A",
                    "is_rare": False,
                },
            ],
        }

    def test_tier_3_priority(self, sample_triggers: dict[int, list[dict]]) -> None:
        """Test Tier 3 triggers have highest priority."""
        # With 6 evidence, tier 3 available
        result = select_matthew_trigger(sample_triggers, 6, [])
        assert result is not None
        assert result["id"] == "t3_a"

    def test_tier_2_fallback(self, sample_triggers: dict[int, list[dict]]) -> None:
        """Test Tier 2 when Tier 3 unavailable."""
        # With 4 evidence, tier 3 unavailable but tier 2 available
        result = select_matthew_trigger(sample_triggers, 4, [])
        assert result is not None
        assert result["id"] in ["t2_a", "t2_b", "t2_rare"]
        assert result["id"] != "t3_a"

    def test_tier_1_fallback(self, sample_triggers: dict[int, list[dict]]) -> None:
        """Test Tier 1 when higher tiers unavailable."""
        # With 1 evidence, only tier 1 available
        result = select_matthew_trigger(sample_triggers, 1, [])
        assert result is not None
        assert result["id"] in ["t1_a", "t1_b"]

    def test_fired_trigger_exclusion(self, sample_triggers: dict[int, list[dict]]) -> None:
        """Test fired triggers are excluded."""
        # Exclude both tier 1 triggers
        result = select_matthew_trigger(sample_triggers, 1, ["t1_a", "t1_b"])
        # Should escalate to tier 2
        assert result is None or result["id"] not in ["t1_a", "t1_b"]

    def test_condition_filtering(self, sample_triggers: dict[int, list[dict]]) -> None:
        """Test condition filtering excludes unmet triggers."""
        # With 2 evidence, t2_b condition (>=4) not met
        for _ in range(10):  # Multiple runs due to randomness
            result = select_matthew_trigger(sample_triggers, 2, [])
            if result and result.get("id") == "t2_b":
                pytest.fail("t2_b selected despite condition not met")

    def test_rare_trigger_7_percent_chance(self, sample_triggers: dict[int, list[dict]]) -> None:
        """Test ~7% chance for rare triggers when available."""
        # Run many times, collect rare selections
        rare_count = 0
        total_runs = 500
        for _ in range(total_runs):
            result = select_matthew_trigger(sample_triggers, 3, [])
            if result and result.get("id") == "t2_rare":
                rare_count += 1

        # 7% of 500 = 35, allow 20-50 range (4-10%)
        assert 20 <= rare_count <= 50, f"Rare trigger selected {rare_count} times (expected ~35)"

    def test_no_eligible_triggers(self, sample_triggers: dict[int, list[dict]]) -> None:
        """Test None returned when no eligible triggers."""
        # Exclude all triggers
        fired = ["t1_a", "t1_b", "t2_a", "t2_b", "t2_rare", "t3_a"]
        result = select_matthew_trigger(sample_triggers, 3, fired)
        assert result is None

    def test_empty_triggers(self) -> None:
        """Test empty triggers dict."""
        result = select_matthew_trigger({}, 5, [])
        assert result is None


class TestLoadMatthewTriggers:
    """Test YAML trigger loading."""

    def test_load_triggers_case_001(self) -> None:
        """Test loading triggers from case_001."""
        clear_trigger_cache()
        triggers = load_matthew_triggers("case_001")

        # Skip if no triggers (graceful empty handling)
        if not triggers:
            pytest.skip("No triggers in case_001")

        # Should have all three tiers
        assert 1 in triggers
        assert 2 in triggers
        assert 3 in triggers

        # Each tier should have triggers
        assert len(triggers[1]) > 0
        assert len(triggers[2]) > 0
        assert len(triggers[3]) > 0

    def test_load_triggers_structure(self) -> None:
        """Test trigger structure is valid."""
        clear_trigger_cache()
        triggers = load_matthew_triggers("case_001")

        for tier, trigger_list in triggers.items():
            for trigger in trigger_list:
                # Each trigger should have required fields
                assert "id" in trigger
                assert "type" in trigger
                assert "text" in trigger
                assert trigger["type"] in ["helpful", "misleading", "emotional", "self_aware"]
                # Optional fields
                if "is_rare" in trigger:
                    assert isinstance(trigger["is_rare"], bool)

    def test_load_triggers_caching(self) -> None:
        """Test triggers are cached."""
        clear_trigger_cache()
        triggers1 = load_matthew_triggers("case_001")
        triggers2 = load_matthew_triggers("case_001")
        # Should be same object (cached)
        assert triggers1 is triggers2

    def test_load_triggers_missing_case(self) -> None:
        """Test missing case returns empty dict."""
        clear_trigger_cache()
        triggers = load_matthew_triggers("nonexistent_case")
        assert triggers == {}

    def test_load_triggers_no_inner_voice_section(self) -> None:
        """Test case without inner_voice section returns empty dict."""
        clear_trigger_cache()
        with patch("src.context.matthew_triggers.load_case") as mock_load:
            mock_load.return_value = {"case": {"locations": []}}
            triggers = load_matthew_triggers("test_case")
            assert triggers == {}


class TestMatthewCompanionState:
    """Test MatthewCompanionState model."""

    def test_fire_trigger(self) -> None:
        """Test firing a trigger."""
        state = MatthewCompanionState(case_id="case_001")

        state.fire_trigger(
            trigger_id="t1", text="Test trigger", trigger_type="helpful", tier=1, evidence_count=2
        )

        assert "t1" in state.fired_triggers
        assert len(state.trigger_history) == 1
        assert state.trigger_history[0].trigger_id == "t1"

    def test_trigger_already_fired_check(self) -> None:
        """Test checking if trigger already fired."""
        state = MatthewCompanionState(case_id="case_001")

        state.fire_trigger(
            trigger_id="t1", text="Test trigger", trigger_type="helpful", tier=1, evidence_count=2
        )

        assert "t1" in state.fired_triggers
        assert "t2" not in state.fired_triggers

    def test_multiple_fired_triggers(self) -> None:
        """Test multiple fired triggers."""
        state = MatthewCompanionState(case_id="case_001")

        state.fire_trigger(
            trigger_id="t1", text="First trigger", trigger_type="helpful", tier=1, evidence_count=1
        )

        state.fire_trigger(
            trigger_id="t2",
            text="Second trigger",
            trigger_type="misleading",
            tier=2,
            evidence_count=3,
        )

        assert "t1" in state.fired_triggers
        assert "t2" in state.fired_triggers
        assert len(state.trigger_history) == 2
        assert state.total_interruptions == 2


class TestMatthewTriggersIntegration:
    """Integration tests for full Matthew trigger flow."""

    def test_select_trigger_with_fired_list(self) -> None:
        """Test realistic scenario with fired triggers."""
        clear_trigger_cache()
        triggers = load_matthew_triggers("case_001")

        if not triggers:
            pytest.skip("No triggers in case_001")

        # First call with no fired
        result1 = select_matthew_trigger(triggers, 2, [])
        assert result1 is not None

        # Second call should avoid first trigger
        fired = [result1["id"]]
        result2 = select_matthew_trigger(triggers, 2, fired)
        # May be None if only one trigger available, or different trigger
        if result2 is not None:
            assert result2["id"] != result1["id"]

    def test_evidence_threshold_progression(self) -> None:
        """Test triggers change as evidence count increases."""
        clear_trigger_cache()
        triggers = load_matthew_triggers("case_001")

        if not triggers:
            pytest.skip("No triggers in case_001")

        # At low evidence count
        result_low = select_matthew_trigger(triggers, 1, [])

        # At high evidence count
        result_high = select_matthew_trigger(triggers, 6, [])

        # One should be available (unless case doesn't have triggers)
        assert result_low is not None or result_high is not None

    def test_tier_thresholds_enforced(self) -> None:
        """Test tier thresholds are enforced correctly.

        Tier 1: evidence_count >= 0 (always eligible)
        Tier 2: evidence_count >= 3
        Tier 3: evidence_count >= 6

        Regression test for bug where Tier 2 triggers with loose conditions
        (like evidence_count<6) would fire at evidence_count=1.
        """
        clear_trigger_cache()
        triggers = load_matthew_triggers("case_001")

        if not triggers:
            pytest.skip("No triggers in case_001")

        # evidence_count=1 should only get Tier 1 triggers
        result_ev1 = select_matthew_trigger(triggers, 1, [])
        if result_ev1:
            assert result_ev1["tier"] == 1, (
                f"evidence_count=1 should get Tier 1, got Tier {result_ev1['tier']}"
            )

        # evidence_count=2 should still only get Tier 1 triggers
        result_ev2 = select_matthew_trigger(triggers, 2, [])
        if result_ev2:
            assert result_ev2["tier"] == 1, (
                f"evidence_count=2 should get Tier 1, got Tier {result_ev2['tier']}"
            )

        # evidence_count=3 can get Tier 1 or Tier 2 (Tier 2 priority)
        result_ev3 = select_matthew_trigger(triggers, 3, [])
        if result_ev3:
            assert result_ev3["tier"] in [1, 2], (
                f"evidence_count=3 should get Tier 1 or 2, got Tier {result_ev3['tier']}"
            )

        # evidence_count=6 can get any tier (Tier 3 priority)
        result_ev6 = select_matthew_trigger(triggers, 6, [])
        if result_ev6:
            assert result_ev6["tier"] in [1, 2, 3], "evidence_count=6 should get Tier 1, 2, or 3"
