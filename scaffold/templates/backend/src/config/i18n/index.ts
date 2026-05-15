// src/config/i18n/index.ts
// Minimal i18n stub. Add locales by importing them here and registering them
// in the `dictionaries` map.

import en from './en';

const dictionaries: Record<string, Record<string, string>> = {
  en,
};

export function t(locale: string, key: string): string {
  const dict = dictionaries[locale] ?? dictionaries.en;
  return dict[key] ?? key;
}
