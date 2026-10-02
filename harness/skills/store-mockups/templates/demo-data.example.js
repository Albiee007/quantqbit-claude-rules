/* Demo data for the store mockups: an API example only. REPLACE every value with data that fits
   the app's real screens. Rename to demo-data.js in your kit folder.

   Rules (see references/demo-data-rules.md):
   - Fictional people only: names from the markets the app serves, initial avatars, no stock faces.
   - One persona and one locale (dates, numbers, currency if any) across every frame.
   - Every figure that appears twice agrees across frames. Write the ledger below FIRST,
     then copy the numbers into the data.

   LEDGER (example):
   - Open items = 5; done this week = 12; the three recent rows are 3 of the 5 open items.
*/
const DEMO = {
  me: { name: 'Sam Okafor', initials: 'SO' },
  home: {
    stats: [
      { badge: 'This week', label: 'Done', value: '12', note: 'Across 3 lists', icon: 'checkmark-done|done_all', tint: 'var(--positiveTint)', color: 'var(--positive)' },
      { badge: 'Today', label: 'Open', value: '5', note: '2 due before noon', icon: 'time-outline|schedule', tint: 'var(--brandTint)', color: 'var(--brand)' },
    ],
    recent: [
      { icon: 'document-text-outline|description', title: 'Draft the brief', amount: '9:30', meta: 'Today · Work', secondary: '' },
      { icon: 'call-outline|call', title: 'Call with Ana', amount: '11:00', meta: 'Today · Work', secondary: '' },
      { icon: 'basket-outline|shopping_basket', title: 'Pick up the order', amount: '17:30', meta: 'Today · Home', secondary: '' },
    ],
  },
  activity: {
    title: 'Activity', sub: 'This week',
    days: [
      { date: 'Thursday', rows: [
        { icon: 'document-text-outline|description', title: 'Draft the brief', amount: '9:30', meta: 'Work', secondary: 'Open' },
        { icon: 'call-outline|call', title: 'Call with Ana', amount: '11:00', meta: 'Work', secondary: 'Open' },
      ] },
      { date: 'Wednesday', rows: [
        { icon: 'checkmark-circle-outline|check_circle', title: 'Send the invoice', amount: '16:00', meta: 'Work', secondary: 'Done' },
      ] },
    ],
  },
};
