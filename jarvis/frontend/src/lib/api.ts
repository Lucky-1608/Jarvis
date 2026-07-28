/**
 * Jarvis OS — Centralized API Client.
 *
 * Provides a consistent fetch wrapper with:
 * - Connection status tracking (backend reachable / unreachable)
 * - Automatic API key injection
 * - Typed responses
 * - Global error handling
 */

import { useJarvisStore } from '../store/jarvisStore';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const API_KEY = 'JARVIS_DEV_KEY';
const BASE = ''; // same-origin (Vite proxy in dev; same server in prod)

/** Check if the backend is reachable by hitting the root endpoint. */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE}/`, {
      // short timeout so this doesn't hang
      signal: AbortSignal.timeout(3000),
    });
    return res.ok;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// Fetch wrapper
// ---------------------------------------------------------------------------

export interface ApiError {
  ok: false;
  status: number;
  detail: string;
}

export interface ApiOk<T> {
  ok: true;
  data: T;
}

export type ApiResult<T> = ApiOk<T> | ApiError;

/**
 * Call an API endpoint. Returns `{ ok: true, data }` on success
 * or `{ ok: false, status, detail }` on any failure (network or 4xx/5xx).
 *
 * On network errors it automatically logs to the Jarvis store.
 */
export async function apiFetch<T = any>(
  path: string,
  options: RequestInit = {},
): Promise<ApiResult<T>> {
  const url = `${BASE}${path}`;

  const headers: Record<string, string> = {
    'X-API-Key': API_KEY,
    ...(options.headers as Record<string, string> | undefined),
  };

  // Don't set Content-Type for GET / HEAD / DELETE with no body
  if (options.body && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  try {
    const res = await fetch(url, { ...options, headers });
    useJarvisStore.getState().setBackendConnected(true);

    if (!res.ok) {
      let detail = '';
      try {
        const body = await res.json();
        detail = body.detail || body.message || res.statusText;
      } catch {
        detail = res.statusText;
      }

      // Track the backend connection failure
      if (res.status >= 500) {
        useJarvisStore.getState().addLog({
          message: `API ${res.status} on ${path}: ${detail}`,
          type: 'error',
        });
      }

      return { ok: false, status: res.status, detail };
    }

    // 204 No Content
    if (res.status === 204) {
      return { ok: true, data: undefined as unknown as T };
    }

    const data: T = await res.json();
    return { ok: true, data };
  } catch (err: any) {
    // Network error — backend is down or unreachable
    const detail = err?.message || 'Backend unreachable';
    useJarvisStore.getState().setAIState('error');
    useJarvisStore.getState().addLog({
      message: `Backend connection failed: ${detail}`,
      type: 'error',
    });

    return { ok: false, status: 0, detail };
  }
}

// ---------------------------------------------------------------------------
// Convenience methods
// ---------------------------------------------------------------------------

export const api = {
  get: <T = any>(path: string, opts?: RequestInit) =>
    apiFetch<T>(path, { method: 'GET', ...opts }),

  post: <T = any>(path: string, body?: any, opts?: RequestInit) =>
    apiFetch<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
      ...opts,
    }),

  put: <T = any>(path: string, body?: any, opts?: RequestInit) =>
    apiFetch<T>(path, {
      method: 'PUT',
      body: body ? JSON.stringify(body) : undefined,
      ...opts,
    }),

  delete: <T = any>(path: string, opts?: RequestInit) =>
    apiFetch<T>(path, { method: 'DELETE', ...opts }),
};
