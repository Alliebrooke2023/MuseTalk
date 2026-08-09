// Site suite — boot/render, search, filter, sort, deep links, link building,
// tab routing, PIN gate, CRUD, export/rebuild round-trip, escaping, CSV shape.
import { boot, readSource, createSuite, SITE_URL } from "./harness.mjs";

const t = createSuite("Site");
const { check, assert, eq } = t;

// ---- boot / render ----
check("boots and exposes window.EFS", () => {
  const w = boot();
  assert(w.EFS && typeof w.EFS.bot === "function");
});

check("renders one card per listing", () => {
  const w = boot();
  eq(w.document.querySelectorAll("#grid .card").length, w.EFS.listings.length);
});

check("seed board has 9 listings", () => {
  const w = boot();
  eq(w.EFS.listings.length, 9);
});

check("sold listing shows a SOLD badge on its card", () => {
  const w = boot();
  assert(w.document.querySelectorAll("#grid .badge.sold").length === 1);
});

check("featured live listing shows a PICK badge", () => {
  const w = boot();
  assert(w.document.querySelectorAll("#grid .badge.feat").length >= 1);
});

// ---- search ----
check("search filters cards by title", () => {
  const w = boot();
  const s = w.document.querySelector("#search");
  s.value = "throttle";
  s.dispatchEvent(new w.Event("input"));
  const cards = w.document.querySelectorAll("#grid .card");
  eq(cards.length, 1);
  assert(cards[0].textContent.toLowerCase().includes("throttle"));
});

check("search matches on tag number", () => {
  const w = boot();
  const s = w.document.querySelector("#search");
  s.value = "EFS-1002";
  s.dispatchEvent(new w.Event("input"));
  eq(w.document.querySelectorAll("#grid .card").length, 1);
});

check("empty-result search reveals the empty note", () => {
  const w = boot();
  const s = w.document.querySelector("#search");
  s.value = "zzzznotathing";
  s.dispatchEvent(new w.Event("input"));
  assert(!w.document.querySelector("#shop-empty").classList.contains("hidden"));
});

// ---- category filter ----
check("category chips render All + every live category", () => {
  const w = boot();
  const chips = [...w.document.querySelectorAll("#catchips button")].map((b) => b.textContent);
  assert(chips[0] === "All");
  assert(chips.includes("Truck Parts") && chips.includes("Wheels"));
});

check("clicking a category chip filters the grid", () => {
  const w = boot();
  const chip = [...w.document.querySelectorAll("#catchips button")].find((b) => b.dataset.cat === "3D Printed");
  chip.click();
  const cards = w.document.querySelectorAll("#grid .card");
  eq(cards.length, 2);
});

// ---- sort ----
check("sort low→high orders ascending", () => {
  const w = boot();
  const out = w.EFS.filterAndSort({ sort: "low" });
  for (let i = 1; i < out.length; i++) assert(out[i].price >= out[i - 1].price);
});

check("sort high→low orders descending", () => {
  const w = boot();
  const out = w.EFS.filterAndSort({ sort: "high" });
  for (let i = 1; i < out.length; i++) assert(out[i].price <= out[i - 1].price);
});

check("sort newest orders by createdAt desc", () => {
  const w = boot();
  const out = w.EFS.filterAndSort({ sort: "new" });
  eq(out[0].tag, "EFS-1009");
});

// ---- deep links ----
check("?item= opens the item sheet", () => {
  const w = boot(readSource(), SITE_URL + "?item=EFS-1003");
  eq(w.EFS.state.openItem, "EFS-1003");
  assert(w.document.querySelector("#sheet").classList.contains("open"));
});

check("?tab=bot routes to the bot pane", () => {
  const w = boot(readSource(), SITE_URL + "?tab=bot");
  assert(w.document.querySelector("#pane-bot").classList.contains("active"));
});

check("?tab=sell routes to the sell pane", () => {
  const w = boot(readSource(), SITE_URL + "?tab=sell");
  assert(w.document.querySelector("#pane-sell").classList.contains("active"));
});

check("?tab=tips routes to the tips pane", () => {
  const w = boot(readSource(), SITE_URL + "?tab=tips");
  assert(w.document.querySelector("#pane-tips").classList.contains("active"));
});

check("no query param defaults to shop pane", () => {
  const w = boot();
  assert(w.document.querySelector("#pane-shop").classList.contains("active"));
});

// ---- link building ----
check("smsLink builds an sms: URL with digits and the tag", () => {
  const w = boot();
  const link = w.EFS.smsLink("EFS-1001");
  assert(link.startsWith("sms:6185550142"));
  assert(decodeURIComponent(link).includes("EFS-1001"));
});

check("mailtoLink builds a mailto: with the configured address", () => {
  const w = boot();
  const link = w.EFS.mailtoLink("EFS-1001");
  assert(link.startsWith("mailto:" + w.EFS.CONFIG.email));
  assert(link.includes("subject="));
});

check("shareLink builds a ?item= deep link", () => {
  const w = boot();
  eq(w.EFS.shareLink("EFS-1004"), SITE_URL + "?item=EFS-1004");
});

// ---- PIN gate ----
check("wrong PIN is rejected", () => {
  const w = boot();
  assert(w.EFS.checkPin("0000") === false);
});

check("correct PIN unlocks the board", () => {
  const w = boot();
  w.EFS.selectTab("board");
  const pin = w.document.querySelector("#pin");
  pin.value = w.EFS.CONFIG.adminPin;
  w.document.querySelector("#pin-go").click();
  assert(!w.document.querySelector("#board").classList.contains("hidden"));
});

// ---- CRUD ----
check("addListing increases the count and is findable", () => {
  const w = boot();
  const before = w.EFS.listings.length;
  const l = w.EFS.addListing({ title: "Winch, 9000lb", price: 175, category: "Truck Parts", condition: "Works" });
  eq(w.EFS.listings.length, before + 1);
  assert(w.EFS.byTag(l.tag).title === "Winch, 9000lb");
});

check("addListing assigns the next EFS tag", () => {
  const w = boot();
  const l = w.EFS.addListing({ title: "x", price: 1, category: "Misc" });
  eq(l.tag, "EFS-1010");
});

check("updateListing edits a field", () => {
  const w = boot();
  w.EFS.updateListing("EFS-1001", { price: 199 });
  eq(w.EFS.byTag("EFS-1001").price, 199);
});

check("deleteListing removes the listing", () => {
  const w = boot();
  const before = w.EFS.listings.length;
  assert(w.EFS.deleteListing("EFS-1006") === true);
  eq(w.EFS.listings.length, before - 1);
  assert(w.EFS.byTag("EFS-1006") === null);
});

check("toggleSold flips the sold flag", () => {
  const w = boot();
  const was = w.EFS.byTag("EFS-1002").sold;
  w.EFS.toggleSold("EFS-1002");
  eq(w.EFS.byTag("EFS-1002").sold, !was);
});

check("toggleFeatured flips the featured flag", () => {
  const w = boot();
  const was = w.EFS.byTag("EFS-1002").featured;
  w.EFS.toggleFeatured("EFS-1002");
  eq(w.EFS.byTag("EFS-1002").featured, !was);
});

// ---- export / rebuild round-trip ----
check("buildSource embeds the current listings JSON", () => {
  const w = boot();
  const rebuilt = w.EFS.buildSource(readSource(), w.EFS.listings);
  assert(rebuilt.includes("EFS-1001"));
  assert(rebuilt.includes("/*LISTINGS_START*/") && rebuilt.includes("/*LISTINGS_END*/"));
});

check("rebuilt file boots and keeps every listing", () => {
  const w1 = boot();
  w1.EFS.addListing({ title: "Bench grinder", price: 55, category: "Tools", condition: "Good" });
  const rebuilt = w1.EFS.buildSource(readSource(), w1.EFS.listings);
  const w2 = boot(rebuilt);
  eq(w2.EFS.listings.length, w1.EFS.listings.length);
  assert(w2.EFS.byTag("EFS-1010").title === "Bench grinder");
});

check("rebuilt file preserves every tag", () => {
  const w1 = boot();
  const rebuilt = w1.EFS.buildSource(readSource(), w1.EFS.listings);
  const w2 = boot(rebuilt);
  const tags1 = w1.EFS.listings.map((l) => l.tag).sort();
  const tags2 = w2.EFS.listings.map((l) => l.tag).sort();
  eq(JSON.stringify(tags1), JSON.stringify(tags2));
});

// ---- escaping / injection ----
check("a malicious title is HTML-escaped in the card, no script node", () => {
  const w = boot();
  w.EFS.addListing({ title: "<img src=x onerror=alert(1)><script>1</script>", price: 5, category: "Misc" });
  const grid = w.document.querySelector("#grid");
  eq(grid.querySelectorAll("script").length, 0);
  eq(grid.querySelectorAll("img[onerror]").length, 0);
});

check("escapeHTML neutralizes angle brackets and quotes", () => {
  const w = boot();
  eq(w.EFS.escapeHTML('<b>"x"</b>'), "&lt;b&gt;&quot;x&quot;&lt;/b&gt;");
});

// ---- CSV / JSON shape ----
check("CSV export has a header row plus one row per listing", () => {
  const w = boot();
  const lines = w.EFS.listingsToCSV().trim().split("\n");
  eq(lines[0], "tag,title,price,category,condition,pickup,sold,featured");
  eq(lines.length, w.EFS.listings.length + 1);
});

check("listingsToJSON round-trips through JSON.parse", () => {
  const w = boot();
  const arr = JSON.parse(w.EFS.listingsToJSON());
  eq(arr.length, w.EFS.listings.length);
  eq(arr[0].tag, w.EFS.listings[0].tag);
});

const summary = t.report();
export default summary;
