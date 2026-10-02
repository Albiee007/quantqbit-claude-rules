/* Demo data for the store mockups. Rename to demo-data.js in your kit folder.

   Rules (see references/demo-data-rules.md):
   - Fictional people only: first names from several cultures, initial avatars, no stock faces.
   - One persona and one home currency across every frame.
   - Every figure that appears twice agrees across frames. Write the ledger below FIRST,
     then copy the numbers into the data.

   LEDGER (example):
   - This month = 1,012.40 personal + 642.18 shared = 1,654.58.
   - Recent rows: 42.10 + 18.60 + 7.50 = 68.20 of the 1,012.40.
*/
const DEMO = {
  me: { name: 'Maya Chen', initials: 'MC' },
  home: {
    stats: [
      { badge: 'This month', label: 'Spent', value: '$1,654.58', note: 'Personal and shared', icon: 'trending-down|trending_down', tint: '#fee2e2', color: '#dc2626' },
      { badge: 'This month', label: 'Saved', value: '$845.42', note: 'Of your $2,500.00 plan', icon: 'trending-up|trending_up', tint: '#dcfce7', color: '#16a34a' },
    ],
    recent: [
      { icon: 'restaurant|restaurant', title: 'Lunch with Leo', amount: '$42.10', meta: 'Today · Food', secondary: '' },
      { icon: 'cart|shopping_cart', title: 'Groceries', amount: '$18.60', meta: 'Today · Home', secondary: '' },
      { icon: 'cafe|local_cafe', title: 'Coffee', amount: '$7.50', meta: 'Yesterday · Food', secondary: '' },
    ],
  },
  activity: {
    title: 'Activity', sub: 'September 2026',
    days: [
      { date: '18 Sept 2026', rows: [
        { icon: 'restaurant|restaurant', title: 'Lunch with Leo', amount: '$42.10', meta: 'Food', secondary: 'Card' },
        { icon: 'cart|shopping_cart', title: 'Groceries', amount: '$18.60', meta: 'Home', secondary: 'Cash' },
      ] },
      { date: '17 Sept 2026', rows: [
        { icon: 'cafe|local_cafe', title: 'Coffee', amount: '$7.50', meta: 'Food', secondary: 'Card' },
      ] },
    ],
  },
};
