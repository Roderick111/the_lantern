/**
 * Custom render utility for tests
 *
 * Wraps components in all required providers (ThemeProvider, etc.)
 * so individual test files don't need to set them up manually.
 *
 * @module test/render
 */

import { type ReactElement } from 'react';
import { render, type RenderOptions } from '@testing-library/react';
import { AllProviders } from './providers';

function renderWithProviders(
  ui: ReactElement,
  options?: Omit<RenderOptions, 'wrapper'>
) {
  return render(ui, { wrapper: AllProviders, ...options });
}

export { renderWithProviders as render };
