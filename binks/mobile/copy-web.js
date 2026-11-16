// mobile/copy-web.js — copy ../web into ./www (the UI bundled into the native app)
const fs = require('fs');
const path = require('path');
const src = path.join(__dirname, '..', 'web');
const dst = path.join(__dirname, 'www');
fs.rmSync(dst, { recursive: true, force: true });
fs.cpSync(src, dst, { recursive: true });
fs.rmSync(path.join(dst, 'sw.js'), { force: true });
console.log('copied web -> mobile/www');
