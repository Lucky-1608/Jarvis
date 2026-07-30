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

let activeBaseUrl: string | null = null;
let isResolving = false;
let resolveQueue: ((url: string) => void)[] = [];

/**
 * Dynamically resolves the active backend URL by pinging the list of URLs
 * provided in VITE_API_BASE_URL (comma-separated).
 */
export async function getBaseUrl(forceRefresh = false): Promise<string> {
  if (activeBaseUrl !== null && !forceRefresh) {
    return activeBaseUrl;
  }

  if (isResolving) {
    return new Promise(resolve => resolveQueue.push(resolve));
  }

  isResolving = true;
  const envStr = import.meta.env.VITE_API_BASE_URL || '';
  const urls = envStr.split(',').map((u: string) => u.trim()).filter(Boolean);

  if (urls.length === 0) {
    urls.push(''); // fallback to relative
  }

  let found = urls[0];
  for (const url of urls) {
    if (!url) {
      found = '';
      break; // relative path is assumed to work
    }
    try {
      const res = await fetch(`${url}/`, { signal: AbortSignal.timeout(2000) });
      if (res.ok || res.status === 404) {
        found = url;
        break;
      }
    } catch {
      continue; // ping failed, try next
    }
  }

  activeBaseUrl = found;
  isResolving = false;
  resolveQueue.forEach(resolve => resolve(found));
  resolveQueue = [];

  return activeBaseUrl || '';
}

/** Check if the backend is reachable by hitting the root endpoint. */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const base = await getBaseUrl(true);
    const res = await fetch(`${base}/`, {
      signal: AbortSignal.timeout(3000),
    });
    return res.ok || res.status === 404;
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
  isRetry = false,
): Promise<ApiResult<T>> {
  const base = await getBaseUrl(isRetry);
  const url = `${base}${path}`;

  const headers: Record<string, string> = {
    'X-API-Key': API_KEY,
    ...(options.headers as Record<string, string> | undefined),
  };

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

      if (res.status >= 500) {
        useJarvisStore.getState().addLog({
          message: `API ${res.status} on ${path}: ${detail}`,
          type: 'error',
        });
      }

      return { ok: false, status: res.status, detail };
    }

    if (res.status === 204) {
      return { ok: true, data: undefined as unknown as T };
    }

    const data: T = await res.json();
    return { ok: true, data };
  } catch (err: any) {
    if (!isRetry) {
      // Network error, try one more time by forcing a refresh of the base URL
      return apiFetch(path, options, true);
    }

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
