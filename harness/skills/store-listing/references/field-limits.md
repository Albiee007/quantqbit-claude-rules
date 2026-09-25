# Listing fields: limits and what each one is for

The limits come from [store-specs](../../store-submission-precheck/references/store-specs.md); check that file if a store changes them.

## Google Play
| Field | Limit | Indexed for search? | Write it as |
|---|---|---|---|
| `play.title` | 30 chars | Yes, the heaviest weight | `Brand: descriptor`. The descriptor holds your 1–2 most important terms. No "best", "#1", "free", emoji, or CAPS for emphasis |
| `play.short` | 80 chars | Yes | One benefit-first sentence. It's often the only text people read before installing |
| `play.full` | 4000 chars | Yes, but repetition is penalised | Hook, pillars, extras, privacy, free vs Premium, a closing line. Scannable: caps headings, bullets, 1–2 emoji per heading at most |
| `play.whatsnew` | 500 chars | No | Release headline plus 3–6 bullets, framed as user benefits |

## Apple App Store
| Field | Limit | Indexed for search? | Write it as |
|---|---|---|---|
| `ios.name` | 30 chars | Yes, the heaviest weight | `Brand: descriptor`. It changes only with a new version |
| `ios.subtitle` | 30 chars | Yes | A benefit in **different words** from the name. Words are indexed once, so don't repeat them |
| `ios.promo` | 170 chars | **No** | Timely news. It can change at any time without review |
| `ios.keywords` | 100 **bytes** | Yes (hidden) | Comma-separated, no spaces, singular forms, no words from the name or subtitle, no competitor brands, no category names |
| `ios.description` | 4000 chars | **No** (for search) | Written for conversion, not keywords. No Android-only features |
| `ios.whatsnew` | 4000 chars | No | Same as Play's What's New |

## Bytes vs characters
Keywords are measured in bytes. ASCII letters are 1 byte; `é` is 2; `₹`, `¥` and most CJK characters are 3. Localised keyword fields fill up faster than they look.
