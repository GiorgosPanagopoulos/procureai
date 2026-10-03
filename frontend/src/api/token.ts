const STORAGE_KEY = 'procureai.access_token';

let memoryToken: string | null = null;

function readStorage(): string | null {
  try {
    return sessionStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function getToken(): string | null {
  if (memoryToken === null) memoryToken = readStorage();
  return memoryToken;
}

export function setToken(token: string): void {
  memoryToken = token;
  try {
    sessionStorage.setItem(STORAGE_KEY, token);
  } catch {
    // Storage unavailable (private mode); the in-memory copy still works for this tab.
  }
}

export function clearToken(): void {
  memoryToken = null;
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // ignore
  }
}
