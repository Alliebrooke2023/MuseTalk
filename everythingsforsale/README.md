# EVERYTHING'S FOR SALE — deploy sheet

One file. No build step, no server, no database. **`index.html` is the whole site.**

---

## 1. Edit 3 things first

Open `index.html`, find the block near the bottom marked `/*CONFIG_START*/`:

```js
const CONFIG = {
  phone: "618-555-0142",                 // <-- your real number
  email: "TrailTradeSupplies@protonmail.com",
  tagline: "Southern Illinois · Built, fixed, flipped",
  adminPin: "1989",                      // <-- CHANGE THIS
  goatcounter: "",                       // <-- your GoatCounter code, e.g. "everythingsforsale"
  currency: "$"
};
```

The phone number drives every **Text about this** button. The PIN opens the Board tab.

---

## 2. Put it on Netlify

**From the S25:**
1. app.netlify.com → your site → **Deploys**
2. Scroll to the drag-and-drop box → **Browse to upload**
3. Pick `index.html`
4. Done. Live in ~10 seconds.

**New site instead:** Netlify → Add new site → Deploy manually → upload `index.html`.

Netlify serves the file at the root, so `index.html` is automatically your homepage. No config file needed.

---

## 3. The loop for adding listings

This is the part that matters. There's no database, so the flow is:

```
Board tab  →  add/edit listings  →  Build new index.html  →  upload to Netlify
```

1. Open the live site on your phone
2. **Board** tab → enter PIN
3. Add a listing. Tap the photo field → **Take Photo** → it auto-resizes to 1000px wide so the file doesn't balloon
4. Tap **Save listing**
5. Scroll to Publish → **Build new index.html** — downloads a fresh file with your listings baked in
6. Upload that file to Netlify

**Important:** changes are only on your screen until you build and upload. Close the tab before uploading and you lose them. **Build first.**

**Backup:** tap **Save listings.json** any time. If you ever lose the site, upload a clean `index.html` and load the JSON back in.

---

## 4. QR codes

Every listing has its own link:

```
https://yoursite.netlify.app/?item=EFS-1001
```

Open a listing → **Share** → copies that link. Feed it to any QR generator, print it, stick it on the item or the truck window. Scanning drops the buyer straight onto that listing.

Tabs deep-link too: `?tab=sell`, `?tab=bot`, `?tab=tips`.

---

## 5. Truck-Bot

**It indexes your listings automatically.** Save something on the Board tab and the bot knows about it immediately — no config, no retraining, nothing to maintain. Delete something and it stops offering it.

What it handles:

| Buyer asks | Bot does |
|---|---|
| "you got a toolbox?" | finds it, gives price + condition + pickup |
| "any wheels" | returns every match, ranked |
| "how much is the throttle body" | price, condition, whether it's still there |
| "anything under $100" | price filter, sorted cheapest first |
| "truck parts under 200" | category + price filter together |
| "between 100 and 300" | range filter |
| "cheapest thing you got" | 3 cheapest live items |
| "most expensive" | biggest ticket items |
| "anything new?" | most recently added |
| "what do you have" | count, category breakdown, price range |
| "show me 3D Printed" | everything in that category |
| "what do you recommend" | your featured items |
| "what sold recently" | sold list |
| "EFS-1004" | direct tag lookup |
| asks about a **sold** item | says it's gone, offers the closest thing you still have |
| "do you ship / will you hold it / take trades" | policy answer, plus matching stock underneath |
| anything else | hands out your phone number |

Every answer comes back with **tappable result rows** — price, category, sold flag. Tapping one opens the full listing. Quick-question chips at the top rebuild themselves from your live categories.

**Tuning it:** the policy answers live in the `/*BOTKB_START*/` block — keywords plus the reply:

```js
{ k:["ship","shipping","mail","deliver"],
  a:"Small stuff ships — printed parts, brackets, decals..." },
```

Add entries as you notice questions repeating. You never need to touch it for products.

**How it decides:** tag number > price filter > sold-list > superlative > recommend > category browse > catalog > strong policy match > product search > weak policy match > phone number. Runs entirely in the browser — no API key, no cost, no network call, instant.

---

## 6. Known limits — read these

- **The PIN is not security.** Anyone who views source can read it. It keeps casual visitors out of the Board tab, nothing more. Don't put anything private in a listing.
- **Photos are embedded as base64.** ~60–120KB each after resize. Keep it to 3–4 photos per listing or the file gets heavy on mobile data. Watch the file size — past about 4MB, first load gets slow.
- **Build new index.html needs the site to be hosted.** It reads its own source via fetch, which is blocked on `file://`. Open it locally and it'll save `listings.json` instead. On Netlify it works fine.

---

## Tests

Two headless suites (jsdom), **80 checks, all passing.**

```bash
npm install     # one-time: pulls in jsdom
npm test        # runs both suites
```

**Site (36):** boot/render, search (title + tag), category filter, sort (3 ways), deep links (`?item`, `?tab`), SMS + mailto + share link building, tab routing, PIN gate (wrong/right), add/edit/delete/sold/featured, next-tag assignment, export rebuild round-trip (rebuilt file boots and keeps every listing + tag), HTML escaping / no-script injection, CSV shape, JSON round-trip.

**Bot (44):** product lookup, single-match answers with price/condition/pickup, sold-item handling with same-category substitutes (by tag and by name), all four price filters (under / over / between / category+price), superlatives (cheapest / most expensive / newest), recommend, sold list, category browse, catalog summary (count + range), tag lookup (exact + spaced), six policy questions with matching stock underneath, gibberish/empty/off-topic fallbacks to the phone number, tappable result rows (data + rendered DOM), decision-priority ordering (tag beats price, price beats category), chips regenerating from inventory, a brand-new listing being findable with zero config, a deleted listing dropping out, and no script execution from a malicious listing title.
