import { beforeEach, describe, expect, it, vi } from 'vitest';
import { fireEvent, screen, waitFor } from '@testing-library/react';
import { render } from '../../test/render';
import { LocationHeaderBar } from '../LocationHeaderBar';

const locations = [
  { id: 'library', name: 'Library', type: 'crime_scene' },
  { id: 'courtyard', name: 'Courtyard', type: 'outdoor' },
];

const defaultProps = {
  locations,
  currentLocationId: 'library',
  locationData: null,
  onSelectLocation: vi.fn(),
  showNavigationHint: true,
};

describe('LocationHeaderBar', () => {
  beforeEach(() => {
    vi.stubGlobal('matchMedia', vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    }));
  });

  it('shows first-use navigation hint across multiple locations', async () => {
    render(<LocationHeaderBar {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('location-footstep-hint')).toBeInTheDocument();
    });

    const footprints = screen.getByTestId('location-footstep-hint').querySelectorAll('[data-footprint-mark]');
    expect(footprints.length).toBeGreaterThanOrEqual(10);
    const firstFootprint = footprints[0];
    expect(firstFootprint?.querySelectorAll('[data-footprint-part]')).toHaveLength(2);
  });

  it('does not show navigation hint when dismissed', () => {
    render(<LocationHeaderBar {...defaultProps} showNavigationHint={false} />);

    expect(screen.queryByTestId('location-footstep-hint')).not.toBeInTheDocument();
  });

  it('keeps footprints safely spaced inside the header path', async () => {
    const makeRect = (left: number, width: number): DOMRect => ({
      x: left,
      y: 32,
      left,
      top: 32,
      right: left + width,
      bottom: 72,
      width,
      height: 40,
      toJSON: () => ({}),
    });
    const rectSpy = vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
      if (this instanceof HTMLButtonElement && this.dataset.locationId === 'library') return makeRect(100, 200);
      if (this instanceof HTMLButtonElement && this.dataset.locationId === 'courtyard') return makeRect(400, 200);
      return makeRect(0, 1000);
    });

    render(<LocationHeaderBar {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByTestId('location-footstep-hint')).toBeInTheDocument();
    });

    const hint = screen.getByTestId('location-footstep-hint');
    const positions = Array.from(hint.querySelectorAll<HTMLElement>('[data-footprint-position]')).map((element) => ({
      x: Number(element.dataset.footprintX),
      y: Number(element.dataset.footprintY),
      angle: Number(element.dataset.footprintAngle),
    }));
    const distances = positions.slice(1).map((position, index) =>
      Math.hypot(position.x - positions[index].x, position.y - positions[index].y),
    );

    expect(Math.min(...distances)).toBeGreaterThanOrEqual(22);
    expect(Math.min(...positions.map((position) => position.y))).toBeGreaterThanOrEqual(-20);
    const angleChanges = positions.slice(1).map((position, index) => {
      const difference = Math.abs(position.angle - positions[index].angle) % 360;
      return Math.min(difference, 360 - difference);
    });
    expect(Math.max(...angleChanges)).toBeLessThanOrEqual(45);
    expect(hint).toHaveAttribute('data-footprint-interval-seconds', '1');
    expect(hint).toHaveAttribute('data-footprint-lifetime-seconds', '4');
    rectSpy.mockRestore();
  });

  it('keeps location tabs interactive', () => {
    const onSelectLocation = vi.fn();
    render(<LocationHeaderBar {...defaultProps} onSelectLocation={onSelectLocation} />);

    fireEvent.click(screen.getByRole('button', { name: /Go to Courtyard/i }));

    expect(onSelectLocation).toHaveBeenCalledWith('courtyard');
  });
});
