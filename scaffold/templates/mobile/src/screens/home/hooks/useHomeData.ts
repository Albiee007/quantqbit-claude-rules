// src/screens/home/hooks/useHomeData.ts
// TanStack Query hook for the Home screen. Wraps the home.service call so
// the screen component stays declarative.

import { useQuery, type UseQueryResult } from '@tanstack/react-query';
import { fetchHomeData } from '../services/home.service';
import type { HomeData } from '../types/home.types';

export function useHomeData(): UseQueryResult<HomeData> {
  return useQuery<HomeData>({
    queryKey: ['home'],
    queryFn: fetchHomeData,
  });
}
