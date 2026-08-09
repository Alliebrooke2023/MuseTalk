// Bot suite — run against the realistic 9-item seed board.
// Product lookup, sold handling + substitutes, price filters, superlatives,
// category browse, catalog summary, tag lookup, policy Q&A, fallbacks,
// tappable result rows, chip regeneration, zero-config findability, no-exec injection.
import { boot, createSuite } from "./harness.mjs";

const t = createSuite("Bot");
const { check, assert, eq } = t;
const eqTags = (r, arr) => eq(JSON.stringify(r.results.map((l) => l.tag)), JSON.stringify(arr));

// one shared window is fine; mutating tests rebuild their own.
const w = boot();
const ask = (q) => w.EFS.bot(q);
const tags = (r) => r.results.map((l) => l.tag);

// ---- product lookup ----
check("finds a toolbox", () => assert(tags(ask("you got a toolbox?")).includes("EFS-1001")));
check("finds wheels", () => assert(tags(ask("any wheels")).includes("EFS-1002")));
check("finds the throttle body", () => assert(tags(ask("how much is the throttle body")).includes("EFS-1003")));
check("throttle-body answer includes the price", () => assert(ask("how much is the throttle body").text.includes("$85")));
check("single product match answers with condition + pickup", () => {
  const r = ask("corded impact wrench");
  assert(r.kind === "product" && r.text.includes("Pickup"));
});

// ---- price filters ----
check("under $100 returns only sub-$100 live items", () => {
  const r = ask("anything under $100");
  assert(r.results.length > 0);
  assert(r.results.every((l) => l.price <= 100 && !l.sold));
});
check("under $100 is sorted cheapest first", () => {
  const r = ask("anything under $100");
  for (let i = 1; i < r.results.length; i++) assert(r.results[i].price >= r.results[i - 1].price);
});
check("category + price filter together (truck parts under 200)", () => {
  const r = ask("truck parts under 200");
  assert(r.results.length === 2);
  assert(r.results.every((l) => l.category === "Truck Parts" && l.price <= 200 && !l.sold));
});
check("range filter between 100 and 300", () => {
  const r = ask("between 100 and 300");
  assert(r.results.every((l) => l.price >= 100 && l.price <= 300 && !l.sold));
  assert(tags(r).includes("EFS-1002"));
});
check("over filter (over 150)", () => {
  const r = ask("anything over 150");
  assert(r.results.every((l) => l.price >= 150 && !l.sold));
  assert(tags(r).includes("EFS-1001"));
});
check("empty price band answers gracefully, no results", () => {
  const r = ask("anything under 5");
  eq(r.results.length, 0);
});

// ---- superlatives ----
check("cheapest returns 3 items, cheapest first", () => {
  const r = ask("cheapest thing you got");
  eq(r.results.length, 3);
  eq(r.results[0].tag, "EFS-1009");
});
check("most expensive returns big-ticket first", () => {
  const r = ask("what's the most expensive");
  eq(r.results[0].tag, "EFS-1002");
});
check("anything new returns the newest item first", () => {
  const r = ask("anything new?");
  eq(r.results[0].tag, "EFS-1009");
});

// ---- recommend / sold list ----
check("recommend returns the featured items", () => {
  const r = ask("what do you recommend");
  const s = new Set(tags(r));
  assert(s.has("EFS-1001") && s.has("EFS-1004"));
});
check("what sold returns the sold item", () => {
  const r = ask("what sold recently");
  eqTags(r, ["EFS-1008"]);
});

// ---- category browse / catalog ----
check("show me 3D Printed lists that category", () => {
  const r = ask("show me 3D Printed");
  eq(new Set(tags(r)).size, 2);
  assert(r.results.every((l) => l.category === "3D Printed"));
});
check("catalog summary reports a live count", () => {
  const r = ask("what do you have");
  assert(r.kind === "catalog");
  assert(r.text.includes("8 items"));
});
check("catalog summary reports the price range", () => {
  const r = ask("what do you have");
  assert(r.text.includes("$9") && r.text.includes("$300"));
});

// ---- tag lookup ----
check("direct tag lookup returns that item", () => {
  const r = ask("EFS-1004");
  eqTags(r, ["EFS-1004"]);
});
check("tag lookup tolerates spacing (efs 1004)", () => {
  const r = ask("got efs 1004?");
  eq(r.results[0].tag, "EFS-1004");
});
check("tag lookup for a sold item says gone + offers substitutes", () => {
  const r = ask("is EFS-1008 still there");
  assert(r.kind === "sold");
  assert(r.text.toLowerCase().includes("sold"));
  assert(r.results.length > 1);
});

// ---- sold-item handling by name ----
check("asking for a sold item by name says it's gone", () => {
  const r = ask("fog lights");
  assert(r.kind === "sold");
  assert(r.text.toLowerCase().includes("sold"));
});
check("sold-item answer offers a same-category substitute", () => {
  const r = ask("fog lights");
  const subs = r.results.slice(1);
  assert(subs.length >= 1 && subs.every((l) => l.category === "Truck Parts" && !l.sold));
});

// ---- policy Q&A (strong) ----
check("shipping policy answers", () => assert(ask("do you ship?").kind === "policy" && ask("do you ship?").text.toLowerCase().includes("ship")));
check("hold policy answers", () => assert(ask("will you hold it").text.toLowerCase().includes("hold")));
check("trade policy answers", () => assert(ask("do you take trades").text.toLowerCase().includes("trade")));
check("cash policy answers", () => assert(ask("can I pay cash").text.toLowerCase().includes("cash")));
check("location policy answers", () => assert(ask("where are you located").text.toLowerCase().includes("illinois")));
check("hours policy answers", () => assert(ask("what are your hours").text.toLowerCase().includes("text")));

check("policy answers carry matching stock underneath", () => {
  const r = ask("do you ship?");
  assert(r.results.length > 0 && r.results.every((l) => !l.sold));
});

// ---- fallbacks ----
check("gibberish falls back to the phone number", () => {
  const r = ask("asdfqwer zxcv");
  eq(r.kind, "fallback");
  assert(r.text.includes(w.EFS.CONFIG.phone));
});
check("empty input returns the empty prompt, no crash", () => {
  const r = ask("");
  eq(r.kind, "empty");
});
check("off-topic question falls back to phone", () => {
  const r = ask("sing me a song");
  eq(r.kind, "fallback");
  assert(r.text.includes(w.EFS.CONFIG.phone));
});

// ---- tappable result rows ----
check("product answer returns tappable result rows", () => {
  const r = ask("wheels");
  assert(r.results.length >= 1 && r.results[0].tag);
});
check("result rows carry price, category and sold flag data", () => {
  const r = ask("is EFS-1008 still there");
  const l = r.results[0];
  assert(typeof l.price === "number" && typeof l.category === "string" && l.sold === true);
});
check("botAsk renders result rows into the DOM as tappable", () => {
  const win = boot();
  win.EFS.selectTab("bot");
  win.EFS.botAsk("wheels");
  const rows = win.document.querySelectorAll("#botlog .resrow[data-item]");
  assert(rows.length >= 1);
});

// ---- decision priority ----
check("tag beats an accompanying price phrase", () => {
  const r = ask("EFS-1002 under 50");
  eq(r.kind, "tag");
  eq(r.results[0].tag, "EFS-1002");
});
check("price filter beats a bare category browse", () => {
  const r = ask("truck parts under 200");
  eq(r.kind, "price");
});

// ---- chips regenerate from inventory ----
check("chips include a Show-me entry per live category", () => {
  const chips = w.EFS.chipsFromInventory();
  assert(chips.includes("Show me Wheels") && chips.includes("Show me 3D Printed"));
});
check("chips regenerate after adding a new category", () => {
  const win = boot();
  win.EFS.addListing({ title: "Camping stove", price: 30, category: "Outdoors", condition: "Good" });
  assert(win.EFS.chipsFromInventory().includes("Show me Outdoors"));
});

// ---- zero-config findability ----
check("a brand-new listing is findable by the bot with zero config", () => {
  const win = boot();
  win.EFS.addListing({ title: "Hydraulic floor jack", price: 65, category: "Tools", condition: "Works" });
  const r = win.EFS.bot("floor jack");
  assert(r.results.some((l) => l.title === "Hydraulic floor jack"));
});
check("deleting a listing makes the bot stop offering it", () => {
  const win = boot();
  win.EFS.deleteListing("EFS-1003");
  const r = win.EFS.bot("throttle body");
  assert(!r.results.some((l) => l.tag === "EFS-1003"));
});

// ---- injection safety ----
check("a malicious listing title runs no script when rendered by the bot", () => {
  const win = boot();
  win.EFS.addListing({ title: "<script>window.__pwned=1</script>", price: 3, category: "Misc" });
  win.EFS.selectTab("bot");
  win.EFS.botAsk("EFS-1010");
  assert(win.document.querySelectorAll("#botlog script").length === 0);
  assert(win.__pwned === undefined);
});

const summary = t.report();
export default summary;
