import '@testing-library/jest-dom';

// Node 22+ defines an experimental `localStorage` accessor on the global that
// returns undefined unless node runs with --localstorage-file, and it shadows
// the DOM test environment's implementation. Replace it with a working
// in-memory Storage so components and tests can use the standard API.
class MemoryStorage {
    #data = new Map();
    get length() { return this.#data.size; }
    key(i) { return [...this.#data.keys()][i] ?? null; }
    getItem(k) { return this.#data.has(String(k)) ? this.#data.get(String(k)) : null; }
    setItem(k, v) { this.#data.set(String(k), String(v)); }
    removeItem(k) { this.#data.delete(String(k)); }
    clear() { this.#data.clear(); }
}

for (const name of ['localStorage', 'sessionStorage']) {
    if (!globalThis[name]) {
        Object.defineProperty(globalThis, name, {
            value: new MemoryStorage(),
            writable: true,
            configurable: true,
        });
    }
}
