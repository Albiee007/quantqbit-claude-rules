# Demo data rules

Store screenshots are read closely: people zoom in, and reviewers compare frames. Inconsistent or fake-looking numbers cost trust. Real data costs privacy.

## Never
- **Real people:** no real names, photos, emails, phone numbers or account balances, including the owner's and the testers'. A capture of a real account is only a layout reference.
- **Test artefacts:** "(replica)", "Test new", "U4", placeholder avatars like "U(", absurd totals (₹2.80 Cr, "13611% of income spent").
- **Stock photos of faces** as avatars. Use initial circles (what most apps show when there's no photo) or neutral illustrations.
- **Other brands' logos or trademarks** inside the UI (payment apps, banks). Use plain-text names where the app itself does.

## Always
- **One persona per set:** first name, last initial or surname, one home currency and one locale. Give the friends and household names from several cultures when the positioning is global.
- **A ledger first.** Before writing `demo-data.js`, write every figure that appears in more than one frame, and how it's made:
  ```
  Trip money: ¥150,000 bought for $1,000.00. Left ¥117,400 + Spent ¥32,600 = ¥150,000.
  Pool bills: Sushi ¥18,600 + Ramen ¥7,500 = ¥26,100 spent from the pool.
  Dashboard "You're owed $212.46" = settlement rows $118.30 + $94.16.
  ```
  Then check each frame against it during visual QA.
- **Correct currency formats.** Use the currency's own decimals (¥ has 0, $ and € have 2, KWD has 3) and grouping (lakh/crore only for INR). Use the same symbols the app's formatter produces.
- **Plausible scale.** Everyday amounts, with a mix of round and odd figures ($42.10, $7.50, $620.00). Percentages the UI would really show.
- **Dates close to the release**, and in the format the app shows ("18 Sept 2026").
- **The app's own labels, character for character.** Read the screen component, not the old screenshots.
- **Platform truth.** Android-only shortcuts appear only in Android frames. Premium-only screens appear only where Premium can be bought.

## Worked example
See [worked-example-splitexpenz.md](worked-example-splitexpenz.md) for a full ledger (a Tokyo trip in yen, settled in USD) and the frame-by-frame checks it survived.
