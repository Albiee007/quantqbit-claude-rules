# Claims guardrails: say only what the build can back

Every sentence in a listing is a promise. Build a **truth table** before you write, and check the copy against it afterwards.

## 1. Build the feature inventory (from the code, not from memory)
- **Screens and flows:** list the navigator routes and screen components, and quote the in-app labels exactly ("Trip money", "Settle up"). Using the app's own words keeps the copy and the screenshots consistent.
- **Entitlements:** find the free and premium tier defaults (grep `premium|entitlement|tier|paywall`). Record the limits (e.g. "3 groups of 5 members") but don't quote them in copy, because they change.
- **Platform gates:** grep `Platform.OS`, server platform headers, and platform-only permissions.
- **Server flags:** check `.env.example` or the config for `*_ENABLED` defaults. If a feature depends on a flag, add it to "Check before you publish".
- **Lists with counts:** currencies, languages, integrations. Count them in code, and note **where** the count applies (e.g. "28 currencies on trips" but "10 home currencies").
- **What's not there:** export, offline use, other languages, a budget feature. Write these down so nobody implies them.

## 2. Truth table
| Claim | Android | iOS | Premium? | Evidence (path:line) | Notes |
|---|---|---|---|---|---|
| Bills in any currency on trips | ✅ | ✅ | No | `utils/moneyCore.ts:12` | 28 currencies, trips only |
| SMS import | ✅ | ❌ | Yes | `DashboardScreen.tsx:140` (Android gate) | Play copy only |

Anything without evidence is **not claimable**.

## 3. Turn the gaps into guardrails
Write `listing-guardrails.txt` next to LISTING.md so the checker enforces the table:
```
# Android-only features
ios: \bSMS\b
ios: receipt scan|scan receipts?
# Not in the mobile app
all: \bexport(s|ing)?\b
all: \boffline\b
# Split modes that don't exist
all: \bby shares?\b
```

## 4. Common traps
- **Fixed prices:** store prices are localised. Say "optional subscription".
- **"Free forever":** true only for the free tier's limits. Say "free for small groups".
- **Superlatives and rankings** ("#1", "best") need proof, and the stores reject them in titles.
- **Other companies' marks:** no competitor names in keywords or copy. Name payment apps only where the app really integrates them, and never with their logos.
- **Regional features in global copy:** frame them as regional ("In India? Pay back through your UPI app").
- **Premium on iOS without IAP:** don't describe Premium in the iOS copy until iOS purchases ship. Make sure the review notes agree.
