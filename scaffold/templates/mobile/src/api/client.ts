// src/api/client.ts
// Shared fetch wrapper. Prefixes the configured base URL, sets JSON headers,
// and normalises non-2xx responses to thrown errors so screen-level hooks
// can hand them off to TanStack Query.

import { env } from '../config/env';

export interface ApiError extends Error {
  status: number;
  body?: unknown;
}

export async function apiFetch<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const url = /^https?:\/\//i.test(path)
    ? path
    : `${env.EXPO_PUBLIC_API_BASE_URL.replace(/\/+$/, '')}/${path.replace(/^\/+/, '')}`;

  const headers = new Headers(init.headers);
  if (!headers.has('Content-Type') && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (!headers.has('Accept')) headers.set('Accept', 'application/json');

  const res = await fetch(url, { ...init, headers });
  const text = await res.text();
  const body: unknown = text ? safeJson(text) : undefined;

  if (!res.ok) {
    const err = new Error(`API ${res.status} ${res.statusText}`) as ApiError;
    err.status = res.status;
    err.body = body;
    throw err;
  }

  return body as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
