import { afterEach, expect, it, vi } from 'vitest';
import { apiFetch, buildUrl } from '../../lib/api-client';

afterEach(() => vi.unstubAllGlobals());

it.each([
  new Headers({ Authorization: 'Bearer example' }),
  [['Authorization', 'Bearer example']] as [string, string][],
])('preserves supported header formats', async (headers) => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 204 });
  vi.stubGlobal('fetch', fetchMock);
  await expect(apiFetch('/resource', { headers })).resolves.toBeUndefined();
  expect(fetchMock.mock.calls[0][1].headers.get('Authorization')).toBe('Bearer example');
});

it('leaves multipart content type to the browser', async () => {
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 204 });
  vi.stubGlobal('fetch', fetchMock);
  await apiFetch('/upload', { method: 'POST', body: new FormData() });
  expect(fetchMock.mock.calls[0][1].headers.has('content-type')).toBe(false);
});

it('joins relative URLs and preserves absolute URLs', () => {
  expect(buildUrl('healthz', 'https://example.com/')).toBe('https://example.com/healthz');
  expect(buildUrl('https://other.example/test')).toBe('https://other.example/test');
});
