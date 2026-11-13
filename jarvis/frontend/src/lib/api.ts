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
export function getApiKey(): string {
  return localStorage.getItem('JARVIS_API_KEY') || 'JARVIS_DEV_KEY';
}

export async function getWebSocketTicket(): Promise<string | null> {
  const result = await apiFetch<{ ticket: string }>('/api/auth/ws-ticket', {
    method: 'POST',
  });
  return result.ok ? result.data.ticket : null;
}
let activeBaseUrl: string | null = null;
let isResolving = false;
let resolveQueue: ((url: string) => void)[] = [];

/**
 * Dynamically resolves the active backend URL by pinging candidate URLs
 * (local backend, env-configured, or relative paths).
 */
export async function getBaseUrl(forceRefresh = false): Promise<string> {
  if (activeBaseUrl !== null && !forceRefresh) {
    return activeBaseUrl;
  }

  if (isResolving) {
    return new Promise(resolve => resolveQueue.push(resolve));
  }

  isResolving = true;

  const isTauri = typeof window !== 'undefined' && (
    '__TAURI_INTERNALS__' in window ||
    '__TAURI__' in window ||
    window.location.protocol.startsWith('tauri') ||
    window.location.protocol === 'file:'
  );

  const isLocalHost = typeof window !== 'undefined' && (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.hostname === '0.0.0.0'
  );

  const customUrl = typeof localStorage !== 'undefined' ? localStorage.getItem('JARVIS_BACKEND_URL')?.trim() : null;
  const envStr = import.meta.env.VITE_API_BASE_URL || '';
  const envUrls = envStr.split(',').map((u: string) => u.trim()).filter(Boolean);

  const candidateUrls: string[] = [];
  if (customUrl) candidateUrls.push(customUrl);

  if (isTauri || isLocalHost) {
    if (!candidateUrls.includes('http://127.0.0.1:8000')) candidateUrls.push('http://127.0.0.1:8000');
    if (!candidateUrls.includes('http://localhost:8000')) candidateUrls.push('http://localhost:8000');
    if (!isTauri && !candidateUrls.includes('')) candidateUrls.push('');
  }

  for (const u of envUrls) {
    if (!candidateUrls.includes(u)) candidateUrls.push(u);
  }

  if (!isTauri && !candidateUrls.includes('')) candidateUrls.push('');
  if (isTauri && !candidateUrls.includes('http://127.0.0.1:8000')) candidateUrls.push('http://127.0.0.1:8000');

  let found: string | null = null;
  for (const url of candidateUrls) {
    try {
      const pingUrl = url ? `${url}/api/health` : '/api/health';
      const res = await fetch(pingUrl, { signal: AbortSignal.timeout(1500) });
      if (res.ok) {
        found = url;
        break;
      }
    } catch {
      continue;
    }
  }

  if (found === null) {
    found = isTauri
      ? 'http://127.0.0.1:8000'
      : (candidateUrls.includes('') ? '' : candidateUrls[0] || 'http://127.0.0.1:8000');
  }

  activeBaseUrl = found;
  isResolving = false;
  resolveQueue.forEach(resolve => resolve(found as string));
  resolveQueue = [];

  return activeBaseUrl || '';
}

/** Check if the backend is reachable by hitting the root endpoint. */
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const base = await getBaseUrl(true);
    const res = await fetch(`${base}/api/health`, {
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
  isRetry = false,
): Promise<ApiResult<T>> {
  const base = await getBaseUrl(isRetry);
  const url = `${base}${path}`;

  const headers: Record<string, string> = {
    'X-API-Key': getApiKey(),
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
        if (Array.isArray(body.detail)) {
          detail = body.detail.map((e: any) => e.msg || JSON.stringify(e)).join('; ');
        } else {
          detail = body.detail || body.message || res.statusText;
        }
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

  patch: <T = any>(path: string, body?: any, opts?: RequestInit) =>
    apiFetch<T>(path, {
      method: 'PATCH',
      body: body ? JSON.stringify(body) : undefined,
      ...opts,
    }),

  delete: <T = any>(path: string, opts?: RequestInit) =>
    apiFetch<T>(path, { method: 'DELETE', ...opts }),
};
