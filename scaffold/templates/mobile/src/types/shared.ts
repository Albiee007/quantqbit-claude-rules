// src/types/shared.ts
// Shared cross-cutting types. Keep small — feature-local types belong in
// the feature/screen's own `types/` folder.

export interface ApiResponseMeta {
  requestId?: string;
  timestamp?: string;
}
