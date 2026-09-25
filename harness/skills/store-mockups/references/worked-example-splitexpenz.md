# Worked example: an expense app repositioned for travellers worldwide (2026-09)

A real run with this kit, on an Expo expense-splitting app. It shows the decisions the skill asks for. The persona and all figures are fictional.

## Starting point
- **Captures:** 183 real-device captures from `mobile-screen-capture`. They were full of test data: the owner's name and photo, "(replica)" groups, placeholder members, absurd balances, and INR only. There was no capture of the newest features (bills in foreign currencies, a trip money pool).
- **Brief:** reposition the app as an **all-in-one expense app for anyone, anywhere**, and lead with foreign trips, multi-currency groups and the pooled trip money.
- **Decision:** rebuild each screen in HTML from the real components, with clean data. The captures and the theme file were the layout reference, and the screen components gave the exact labels.

## Persona and ledger
- **Persona:** Maya, with USD as home currency. Friends Leo, Aiko, Sam and Priya get initial avatars.
- **Trip money:** "Tokyo 2026", settled in USD. ¥150,000 was bought for $1,000.00, shown as "1 JPY = 0.00667 USD", the app's own rate format.
  - Left ¥117,400 + Spent ¥32,600 = ¥150,000.
  - The trip pool opened at ¥100,000 and spent ¥18,600 + ¥7,500. Leo's allowance: ¥25,000 − ¥6,500. Maya's: ¥25,000, untouched.
- **Bill conversions:** bills paid from the pool convert at the purchase rate (÷150); card bills at the card's rate (÷149.5). Each share is ⅕.
- **Dashboard:** owe $48.20 (a home group), owed $212.46 = settlement rows $118.30 + $94.16.
- **This month:** 1,012.40 personal + 642.18 shared + 1,530.02 recurring = 3,184.60. Income 4,850.00, so 66% of income is spent.

## Storyboard (8 frames)
| # | Headline | Screen |
|---|---|---|
| 1 | Every expense. Every trip. <em>Anywhere.</em> | Dashboard |
| 2 | Travel abroad. Split in <em>any currency.</em> | Trip: yen bills, each showing ≈ $ and your share |
| 3 | Changed cash before you <em>flew?</em> | Trip money: left, spent so far, held by, share with its cost |
| 4 | Pay from the <em>trip pool</em>, split it your way | Add expense in JPY, paid by the trip pool |
| 5 | Who owes whom, <em>worked out</em> for you | Balance + settlement list |
| 6 | Know where your <em>money goes</em> | Analytics |
| 7 | Salary, rent, subscriptions: <em>planned</em> | Recurring |
| 8 | Roommates, couples, <em>trips</em>, work | Groups list, with trips in different currencies |

## What visual QA caught (and the fix)
- **The FAB covered figures.** The floating add button hid a share amount (frame 2), the owners' shares (frame 3), a recurring amount (frame 7) and a bill count (frame 8). It was removed from those frames and kept where it covered nothing.
- **A badge overlapped its label.** The "Current" badge on the month selector sat on top of the month name. It was moved to straddle the card's top edge.
- **The totals didn't add up.** The first draft of the share list showed 3 of 5 owners, so the listed shares didn't sum to "Left". All 5 were added, and the list scrolls off the bottom of the frame.
- **The spacing looked odd.** The caption font had wide gaps before full stops. Switching the headline font to Inter 800 with −0.025em tracking fixed it.
- **Platform truth:** the Android Dashboard shows an "Import SMS" shortcut, and the iOS frames leave it out, matching the app's platform gate.

## Output
- 8 frames × 5 sizes (Play phone, 7″, 10″, iOS 6.9″, 6.5″) plus a 1024 × 500 feature graphic built around currency chips and the Trip money screen.
- All files RGB, at exact size, under 8 MB. A contact sheet went to the owner for sign-off.
