import { TtlCache } from '../../lib/ttl-cache';
import { retry } from '../../lib/retry';

afterEach(() => jest.useRealTimers());

describe('TtlCache', () => {
  it('expires at the deadline and bounds retained entries', () => {
    jest.useFakeTimers().setSystemTime(0);
    const cache = new TtlCache<string, number>(10, 2);
    cache.set('a', 1);
    jest.advanceTimersByTime(10);
    expect(cache.get('a')).toBeUndefined();
    cache.set('a', 1);
    cache.set('b', 2);
    cache.set('c', 3);
    expect(cache.get('a')).toBeUndefined();
    expect(cache.get('b')).toBe(2);
    cache.set('b', 4, 0);
    expect(cache.get('b')).toBeUndefined();
  });

  it('rejects invalid lifetimes and capacity', () => {
    expect(() => new TtlCache(-1)).toThrow(RangeError);
    expect(() => new TtlCache(10, 0)).toThrow(RangeError);
    expect(() => new TtlCache().set('a', 1, NaN)).toThrow(RangeError);
  });
});

describe('retry', () => {
  it('rejects invalid options without calling the operation', async () => {
    const fn = jest.fn();
    for (const attempts of [0, -1, 1.5, Infinity, NaN]) {
      await expect(retry(fn, { attempts })).rejects.toThrow(RangeError);
    }
    await expect(retry(fn, { initialDelayMs: -1 })).rejects.toThrow(RangeError);
    expect(fn).not.toHaveBeenCalled();
  });

  it('caps the first delay and propagates the final error', async () => {
    jest.useFakeTimers();
    const error = new Error('unavailable');
    const fn = jest.fn().mockRejectedValue(error);
    const result = retry(fn, { attempts: 2, initialDelayMs: 100, maxDelayMs: 10 });
    const assertion = expect(result).rejects.toBe(error);
    await jest.advanceTimersByTimeAsync(10);
    await assertion;
    expect(fn).toHaveBeenCalledTimes(2);
  });
});
