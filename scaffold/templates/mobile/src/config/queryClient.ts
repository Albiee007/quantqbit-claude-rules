// src/config/queryClient.ts
// Singleton TanStack Query client. Tuned defaults for mobile: longer stale
// time, no window-focus refetch (irrelevant on RN), one retry.

import { QueryClient } from '@tanstack/react-query';

export const queryClient: QueryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
  },
});
