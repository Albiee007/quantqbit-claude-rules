// src/screens/home/services/home.service.ts
// Tiny service that calls the configurable API base URL. Returns a typed
// HomeData record. Falls back to a static stub if the request fails so the
// example screen renders even without a running backend.

import { env } from '../../../config/env';
import type { HomeData } from '../types/home.types';

const STUB: HomeData = {
  message: 'Welcome to your new app.',
  generatedAt: new Date(0).toISOString(),
};

export async function fetchHomeData(): Promise<HomeData> {
  const url = `${env.EXPO_PUBLIC_API_BASE_URL}/healthz`;
  try {
    const res = await fetch(url);
    if (!res.ok) {
      return STUB;
    }
    // Backend health response shape isn't a strict superset of HomeData; we
    // normalise on the way out so the screen always gets a HomeData.
    const body = (await res.json()) as { status?: string };
    return {
      message: `Backend status: ${body.status ?? 'unknown'}`,
      generatedAt: new Date().toISOString(),
    };
  } catch {
    return STUB;
  }
}
