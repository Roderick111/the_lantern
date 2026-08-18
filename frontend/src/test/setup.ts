import '@testing-library/jest-dom';

// Mock scrollTo for tests
Object.defineProperty(HTMLElement.prototype, 'scrollTo', {
  // eslint-disable-next-line @typescript-eslint/no-empty-function
  value: () => {},
  writable: true,
});

// Ensure localStorage is available (jsdom sometimes has issues)
function createStorage(): Storage {
  const store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] ?? null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { Object.keys(store).forEach((k) => delete store[k]); },
    get length() { return Object.keys(store).length; },
    key: (index: number) => Object.keys(store)[index] ?? null,
  };
}

if (typeof globalThis.localStorage === 'undefined' || typeof globalThis.localStorage.getItem !== 'function') {
  globalThis.localStorage = createStorage();
}

if (typeof globalThis.sessionStorage === 'undefined' || typeof globalThis.sessionStorage.getItem !== 'function') {
  globalThis.sessionStorage = createStorage();
}
