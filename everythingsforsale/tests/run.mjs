// Runs both headless suites and exits non-zero if anything fails.
const site = (await import("./site.test.mjs")).default;
const bot = (await import("./bot.test.mjs")).default;

const total = site.total + bot.total;
const passed = site.passed + bot.passed;
const failed = site.failed + bot.failed;

console.log(`\n================================`);
console.log(`TOTAL: ${passed}/${total} checks passing (Site ${site.passed}/${site.total}, Bot ${bot.passed}/${bot.total})`);
console.log(`================================`);

process.exit(failed === 0 ? 0 : 1);
