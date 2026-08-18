/**
 * LanternCompendium Component Tests
 *
 * Tests for the read-only rite reference modal:
 * - Renders all 7 rites
 * - No action buttons (read-only)
 * - Category badges
 * - Modal close behavior
 * - Keyboard shortcut
 *
 * @module components/__tests__/LanternCompendium.test
 * @since Phase 4.5
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render } from "../../test/render";
import { screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { LanternCompendium, SPELL_DEFINITIONS } from "../LanternCompendium";

// ============================================
// Test Data
// ============================================

const defaultProps = {
  isOpen: true,
  onClose: vi.fn(),
};

// ============================================
// Test Suite
// ============================================

describe("LanternCompendium", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ------------------------------------------
  // Rendering Tests
  // ------------------------------------------

  describe("Rendering", () => {
    it.todo("renders modal title");

    it("renders all 7 rites", () => {
      render(<LanternCompendium {...defaultProps} />);

      expect(screen.getByText("Veil, dissolve")).toBeInTheDocument();
      expect(screen.getByText("Presence, answer")).toBeInTheDocument();
      expect(screen.getByText("Essence, speak")).toBeInTheDocument();
      expect(screen.getByText("Trace, gleam")).toBeInTheDocument();
      expect(screen.getByText("Echo, speak")).toBeInTheDocument();
      expect(screen.getByText("Shards, unite")).toBeInTheDocument();
      expect(screen.getByText("Memory, open")).toBeInTheDocument();
    });

    it("renders spell descriptions", () => {
      render(<LanternCompendium {...defaultProps} />);

      expect(screen.getByText(/Reveals hidden writing/)).toBeInTheDocument();
      expect(screen.getByText(/Detects someone nearby/)).toBeInTheDocument();
    });

    it.todo("renders instructions text");

    it.todo("renders restricted spell warning footer");

    it("does not render when isOpen is false", () => {
      render(<LanternCompendium isOpen={false} onClose={vi.fn()} />);

      expect(
        screen.queryByText("Lantern Compendium - Investigation Rites")
      ).not.toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Read-Only Tests (No Action Buttons)
  // ------------------------------------------

  describe("Read-Only Behavior", () => {
    it("does NOT have spell cast buttons", () => {
      render(<LanternCompendium {...defaultProps} />);

      // No buttons with cast-related names
      expect(screen.queryByRole("button", { name: /cast/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /use/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /select/i })).not.toBeInTheDocument();
    });

    it("spell cards are not clickable buttons", () => {
      render(<LanternCompendium {...defaultProps} />);

      // Spell cards should be divs, not buttons
      const spellCards = screen.getAllByTestId(/spell-card-/);
      spellCards.forEach((card) => {
        expect(card.tagName.toLowerCase()).toBe("div");
      });
    });

    it("has exactly 7 spell cards (read-only display)", () => {
      render(<LanternCompendium {...defaultProps} />);

      const spellCards = screen.getAllByTestId(/spell-card-/);
      expect(spellCards).toHaveLength(7);
    });
  });

  // ------------------------------------------
  // Category Badge Tests
  // ------------------------------------------

  describe("Category Badges", () => {
    it("renders category badges for all spells", () => {
      render(<LanternCompendium {...defaultProps} />);

      // Check for detection category (3 spells: Unveil, Sense Presence, Raise the Lamp)
      const detectionBadges = screen.getAllByText("detection");
      expect(detectionBadges.length).toBe(3);
    });

    it("renders analysis category", () => {
      render(<LanternCompendium {...defaultProps} />);

      const analysisBadges = screen.getAllByText("analysis");
      expect(analysisBadges.length).toBe(2);
    });

    it("renders restoration category", () => {
      render(<LanternCompendium {...defaultProps} />);

      expect(screen.getByText("restoration")).toBeInTheDocument();
    });

    it("renders mental category for Mnemonic Delving", () => {
      render(<LanternCompendium {...defaultProps} />);

      expect(screen.getByText("mental")).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Modal Close Behavior Tests
  // ------------------------------------------

  describe("Modal Close Behavior", () => {
    it("calls onClose when close button is clicked", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      render(<LanternCompendium isOpen={true} onClose={onClose} />);

      const closeButton = screen.getByRole("button", { name: /close modal/i });
      await user.click(closeButton);

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("calls onClose when backdrop is clicked", async () => {
      const user = userEvent.setup();
      const onClose = vi.fn();

      render(<LanternCompendium isOpen={true} onClose={onClose} />);

      // Backdrop is the element with aria-hidden="true"
      const backdrop = document.querySelector('[aria-hidden="true"]');
      expect(backdrop).toBeInTheDocument();

      await user.click(backdrop!);
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("calls onClose when Escape key is pressed", () => {
      const onClose = vi.fn();

      render(<LanternCompendium isOpen={true} onClose={onClose} />);

      fireEvent.keyDown(document, { key: "Escape" });

      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  // ------------------------------------------
  // Keyboard Shortcut Tests
  // ------------------------------------------

  describe("Keyboard Shortcut", () => {
    it("closes on Ctrl+H when open", () => {
      const onClose = vi.fn();

      render(<LanternCompendium isOpen={true} onClose={onClose} />);

      fireEvent.keyDown(document, { key: "h", ctrlKey: true });

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("closes on Cmd+H when open (Mac)", () => {
      const onClose = vi.fn();

      render(<LanternCompendium isOpen={true} onClose={onClose} />);

      fireEvent.keyDown(document, { key: "h", metaKey: true });

      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("does not call onClose when Cmd+H pressed without modal open", () => {
      const onClose = vi.fn();

      render(<LanternCompendium isOpen={false} onClose={onClose} />);

      fireEvent.keyDown(document, { key: "h", metaKey: true });

      expect(onClose).not.toHaveBeenCalled();
    });
  });

  // ------------------------------------------
  // Spell Data Integrity Tests
  // ------------------------------------------

  describe("Spell Data Integrity", () => {
    it("exports SPELL_DEFINITIONS with 7 rites", () => {
      expect(SPELL_DEFINITIONS).toHaveLength(7);
    });

    it("all spells have required fields", () => {
      SPELL_DEFINITIONS.forEach((spell) => {
        expect(spell).toHaveProperty("id");
        expect(spell).toHaveProperty("name");
        expect(spell).toHaveProperty("legacyName");
        expect(spell).toHaveProperty("description");
        expect(spell).toHaveProperty("example");
        expect(spell).toHaveProperty("safetyLevel");
        expect(spell).toHaveProperty("category");
      });
    });

    it("Mnemonic Delving is the only restricted spell", () => {
      const restrictedSpells = SPELL_DEFINITIONS.filter(
        (spell) => spell.safetyLevel === "restricted"
      );
      expect(restrictedSpells).toHaveLength(1);
      expect(restrictedSpells[0].id).toBe("mnemonic_delving");
    });
  });

  // ------------------------------------------
  // Accessibility Tests
  // ------------------------------------------

  describe("Accessibility", () => {
    it("modal has proper ARIA attributes", () => {
      render(<LanternCompendium {...defaultProps} />);

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });

    it("close button has aria-label", () => {
      render(<LanternCompendium {...defaultProps} />);

      const closeButton = screen.getByRole("button", { name: /close modal/i });
      expect(closeButton).toBeInTheDocument();
    });

    it("each spell card has a test ID for testing", () => {
      render(<LanternCompendium {...defaultProps} />);

      expect(screen.getByTestId("spell-card-unveil")).toBeInTheDocument();
      expect(screen.getByTestId("spell-card-mnemonic_delving")).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Styling Tests
  // ------------------------------------------

  describe("Styling", () => {
    it.todo("Mnemonic Delving card has red styling");

    it("safe spell cards have gray border", () => {
      render(<LanternCompendium {...defaultProps} />);

      const unveilCard = screen.getByTestId("spell-card-unveil");
      expect(unveilCard).toHaveClass("border-gray-700");
    });

    it("Mnemonic Delving name is red", () => {
      render(<LanternCompendium {...defaultProps} />);

      const mnemonicDelvingName = screen.getByText("Memory, open");
      expect(mnemonicDelvingName).toHaveClass("text-red-400");
    });

    it.todo("safe spell names are yellow");
  });
});
