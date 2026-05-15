// src/lib/stringUtils.ts
// Pure string helpers. No side effects, no I/O.

export function slugify(input: string): string {
  return input
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/(^-|-$)/g, '');
}

export function truncate(input: string, max: number, suffix = '...'): string {
  if (input.length <= max) return input;
  return input.slice(0, Math.max(0, max - suffix.length)) + suffix;
}

export function isNonEmpty(input: unknown): input is string {
  return typeof input === 'string' && input.trim().length > 0;
}
