/**
 * WitnessSelector Component Tests
 *
 * Tests for the witness selection interface including:
 * - Witness list rendering
 * - Trust level display
 * - Selection handling
 * - Secrets revealed indicator
 * - Loading and error states
 *
 * @module components/__tests__/WitnessSelector.test
 * @since Phase 2
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '../../test/render';
import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { WitnessSelector } from '../WitnessSelector';
import type { WitnessInfo } from '../../types/investigation';

// ============================================
// Test Data
// ============================================

const mockWitnesses: WitnessInfo[] = [
  {
    id: 'elena',
    name: 'Elena Marsh',
    trust: 55,
    secrets_revealed: [],
  },
  {
    id: 'cassian',
    name: 'Cassian Thorne',
    trust: 25,
    secrets_revealed: ['secret_1'],
  },
  {
    id: 'rowan',
    name: 'Rowan Ashford',
    trust: 80,
    secrets_revealed: ['secret_a', 'secret_b'],
  },
];

const defaultProps = {
  witnesses: mockWitnesses,
  loading: false,
  error: null,
  onSelectWitness: vi.fn(),
};

// ============================================
// Test Suite
// ============================================

describe('WitnessSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ------------------------------------------
  // Rendering Tests
  // ------------------------------------------

  describe('Rendering', () => {
    it('renders header', () => {
      render(<WitnessSelector {...defaultProps} />);

      expect(screen.getByText(/Available Witnesses/i)).toBeInTheDocument();
    });

    it('renders all witness names', () => {
      render(<WitnessSelector {...defaultProps} />);

      expect(screen.getByText('Elena Marsh')).toBeInTheDocument();
      expect(screen.getByText('Cassian Thorne')).toBeInTheDocument();
      expect(screen.getByText('Rowan Ashford')).toBeInTheDocument();
    });

    it('renders trust percentages', () => {
      render(<WitnessSelector {...defaultProps} />);

      expect(screen.getByText(/55%/)).toBeInTheDocument();
      expect(screen.getByText(/25%/)).toBeInTheDocument();
      expect(screen.getByText(/80%/)).toBeInTheDocument();
    });

    it('renders witness bullet symbols', () => {
      render(<WitnessSelector {...defaultProps} />);

      // Should have bullet symbols for each witness
      const bullets = screen.getAllByText('•');
      expect(bullets.length).toBe(mockWitnesses.length);
    });
  });

  // ------------------------------------------
  // Trust Level Color Tests
  // ------------------------------------------

  describe('Trust Level Display', () => {
    it('shows ASCII trust bar for all trust levels', () => {
      render(<WitnessSelector {...defaultProps} />);

      // Should display trust bars with percentages
      // Elena (55%), Cassian (25%), Rowan (80%)
      expect(screen.getByText(/55%/)).toBeInTheDocument();
      expect(screen.getByText(/25%/)).toBeInTheDocument();
      expect(screen.getByText(/80%/)).toBeInTheDocument();
    });

    it('displays trust labels for all witnesses', () => {
      render(<WitnessSelector {...defaultProps} />);

      // All trust labels should be visible
      const trustLabels = screen.getAllByText(/Trust:/);
      expect(trustLabels.length).toBe(mockWitnesses.length);
    });
  });

  // ------------------------------------------
  // Secrets Revealed Tests
  // ------------------------------------------

  describe('Secrets Revealed', () => {
    it('shows secrets badge when secrets revealed', () => {
      render(<WitnessSelector {...defaultProps} />);

      // Cassian has 1 secret
      expect(screen.getByText('1 secret revealed')).toBeInTheDocument();

      // Rowan has 2 secrets
      expect(screen.getByText('2 secrets revealed')).toBeInTheDocument();
    });

    it('does not show secrets badge when no secrets', () => {
      render(<WitnessSelector {...defaultProps} />);

      // Elena has no secrets - should not have a secrets badge
      const elenaCard = screen.getByText('Elena Marsh').closest('button');
      expect(elenaCard).not.toHaveTextContent(/secret/i);
    });
  });

  // ------------------------------------------
  // Selection Tests
  // ------------------------------------------

  describe('Selection', () => {
    it('calls onSelectWitness when witness clicked', async () => {
      const user = userEvent.setup();
      const onSelectWitness = vi.fn();

      render(
        <WitnessSelector {...defaultProps} onSelectWitness={onSelectWitness} />
      );

      const elenaCard = screen.getByText('Elena Marsh').closest('button');
      await user.click(elenaCard!);

      expect(onSelectWitness).toHaveBeenCalledWith('elena');
    });

    it('shows witness names with white text', () => {
      render(<WitnessSelector {...defaultProps} />);

      const elenaText = screen.getByText('Elena Marsh');
      expect(elenaText).toHaveClass('text-white');

      const cassianText = screen.getByText('Cassian Thorne');
      expect(cassianText).toHaveClass('text-white');
    });
  });

  // ------------------------------------------
  // Loading State Tests
  // ------------------------------------------

  describe('Loading State', () => {
    it('shows loading indicator when loading with no witnesses', () => {
      render(
        <WitnessSelector
          {...defaultProps}
          witnesses={[]}
          loading={true}
        />
      );

      expect(screen.getByText(/Loading witnesses/i)).toBeInTheDocument();
    });

    it('shows witnesses when loading with existing witnesses', () => {
      render(
        <WitnessSelector {...defaultProps} loading={true} />
      );

      // Should still show witnesses (refresh scenario)
      expect(screen.getByText('Elena Marsh')).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Error State Tests
  // ------------------------------------------

  describe('Error State', () => {
    it('shows error message when error with no witnesses', () => {
      render(
        <WitnessSelector
          {...defaultProps}
          witnesses={[]}
          error="Failed to load witnesses"
        />
      );

      expect(screen.getByText(/Failed to load witnesses/i)).toBeInTheDocument();
    });

    it('shows witnesses when error with existing witnesses', () => {
      render(
        <WitnessSelector {...defaultProps} error="Refresh failed" />
      );

      // Should still show witnesses
      expect(screen.getByText('Elena Marsh')).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Empty State Tests
  // ------------------------------------------

  describe('Empty State', () => {
    it('shows empty message when no witnesses', () => {
      render(
        <WitnessSelector {...defaultProps} witnesses={[]} />
      );

      expect(
        screen.getByText(/No witnesses available for this case/i)
      ).toBeInTheDocument();
    });
  });

  // ------------------------------------------
  // Accessibility Tests
  // ------------------------------------------

  describe('Accessibility', () => {
    it.todo('has accessible witness cards as buttons');

    it('has accessible aria-labels on witness cards', () => {
      render(<WitnessSelector {...defaultProps} />);

      const elenaCard = screen.getByLabelText(
        /Select Elena Marsh for interrogation\. Trust: 55%\. Secrets revealed: 0/i
      );
      expect(elenaCard).toBeInTheDocument();

      const cassianCard = screen.getByLabelText(
        /Select Cassian Thorne for interrogation\. Trust: 25%\. Secrets revealed: 1/i
      );
      expect(cassianCard).toBeInTheDocument();
    });
  });
});
