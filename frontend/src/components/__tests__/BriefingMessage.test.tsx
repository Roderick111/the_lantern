/**
 * BriefingMessage Component Tests
 *
 * Tests for the dialogue message bubble component.
 *
 * @module components/__tests__/BriefingMessage.test
 * @since Phase 3.6
 */

import { describe, it, expect } from 'vitest';
import { render } from '../../test/render';
import { screen } from '@testing-library/react';
import { BriefingMessage } from '../BriefingMessage';

describe('BriefingMessage', () => {
  describe('Graves Messages', () => {
    it.todo('renders Graves label');

    it('renders message text', () => {
      render(<BriefingMessage speaker="graves" text="Test message content" />);

      expect(screen.getByText('Test message content')).toBeInTheDocument();
    });

    it.todo('has amber color for Graves label');

    it('has gray-200 text for Graves messages', () => {
      render(<BriefingMessage speaker="graves" text="Test message" />);

      const content = screen.getByText('Test message');
      expect(content).toHaveClass('text-gray-200');
    });

    it.todo('does not have left margin for Graves messages');
  });

  describe('Player Messages', () => {
    it.todo('renders YOU label');

    it('renders message text', () => {
      render(<BriefingMessage speaker="player" text="Player message content" />);

      expect(screen.getByText('Player message content')).toBeInTheDocument();
    });

    it.todo('has gray color for YOU label');

    it.todo('has gray-400 text for player messages');

    it.todo('has left margin for player messages');
  });

  describe('Styling', () => {
    it.todo('preserves whitespace');

    it('has relaxed line height', () => {
      render(<BriefingMessage speaker="graves" text="Test message" />);

      const content = screen.getByText('Test message');
      expect(content).toHaveClass('leading-[28px]');
    });

    it('has small text size', () => {
      render(<BriefingMessage speaker="graves" text="Test message" />);

      const content = screen.getByText('Test message');
      expect(content).toHaveClass('text-base');
    });

    it.todo('has bottom margin for spacing');
  });

  describe('Edge Cases', () => {
    it.todo('handles empty text');

    it.todo('handles special characters');

    it('handles multiline text', () => {
      const multilineText = `Line 1
Line 2
Line 3`;
      render(<BriefingMessage speaker="graves" text={multilineText} />);

      expect(screen.getByText(/Line 1/)).toBeInTheDocument();
    });
  });
});
