import { apiFetch } from '../../api/client';

jest.mock('../../config/env', () => ({ env: { EXPO_PUBLIC_API_BASE_URL: 'https://example.com/' } }));

const originalFetch = global.fetch;
afterEach(() => { global.fetch = originalFetch; });

it('joins relative paths and preserves Headers objects', async () => {
  const fetchMock = jest.fn().mockResolvedValue({ ok: true, text: async () => '' });
  global.fetch = fetchMock;
  await apiFetch('healthz', { headers: new Headers({ Authorization: 'Bearer example' }) });
  expect(fetchMock.mock.calls[0][0]).toBe('https://example.com/healthz');
  expect(fetchMock.mock.calls[0][1].headers.get('Authorization')).toBe('Bearer example');
});

it('preserves absolute URLs and exposes response error status', async () => {
  const fetchMock = jest.fn().mockResolvedValue({ ok: false, status: 503, text: async () => '{}' });
  global.fetch = fetchMock;
  await expect(apiFetch('https://other.example/path')).rejects.toMatchObject({ status: 503 });
  expect(fetchMock.mock.calls[0][0]).toBe('https://other.example/path');
});
