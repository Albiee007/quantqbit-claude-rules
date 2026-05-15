// src/lib/storage.ts
// Typed wrapper around AsyncStorage. JSON-encodes values on write, decodes
// on read, and returns null on a missing or malformed key.

import AsyncStorage from '@react-native-async-storage/async-storage';

export async function storageGet<T>(key: string): Promise<T | null> {
  try {
    const raw = await AsyncStorage.getItem(key);
    if (raw === null) return null;
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

export async function storageSet<T>(key: string, value: T): Promise<void> {
  await AsyncStorage.setItem(key, JSON.stringify(value));
}

export async function storageRemove(key: string): Promise<void> {
  await AsyncStorage.removeItem(key);
}
