// src/types/shared.ts
// Types reused by more than one feature. Keep this file small — feature-local
// types belong inside the feature's own types/ folder.

export type Iso8601 = string;

export interface PaginatedResult<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}
