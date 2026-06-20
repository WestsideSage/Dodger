import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, extname } from 'node:path';

const SCAN_DIRS = ['src/ui', 'src/styles', 'src/components/shell'];
// SCAN_FILES may contain explicit files (scanned as-is) that live outside SCAN_DIRS.
const SCAN_FILES = ['src/App.module.css', 'src/components/SaveMenu.module.css'];
const HEX = /#[0-9a-fA-F]{3,8}\b/;
// raw px other than 0/1px hairlines
const PX = /(?<![\w.])(?!0px|1px)\d{1,4}px\b/;
// Whole-file exemptions: the token source itself + test fixtures.
const ALLOW_FILE = /(tokens\.css|\.test\.)/;
// Per-line exemption: ONLY SVG viewBox attributes (legitimately carry coordinate numbers).
const ALLOW_LINE = /viewBox/;

function walk(dir) {
  let out = [];
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) out = out.concat(walk(p));
    else if (['.tsx', '.ts', '.css'].includes(extname(p))) out.push(p);
  }
  return out;
}

function checkFile(file, violations) {
  if (ALLOW_FILE.test(file)) return;
  const text = readFileSync(file, 'utf8');
  text.split('\n').forEach((line, i) => {
    if (ALLOW_LINE.test(line)) return;
    if (HEX.test(line) || PX.test(line)) violations.push(`${file}:${i + 1}  ${line.trim()}`);
  });
}

const violations = [];
for (const dir of SCAN_DIRS) {
  for (const file of walk(dir)) {
    checkFile(file, violations);
  }
}
for (const file of SCAN_FILES) {
  checkFile(file, violations);
}

if (violations.length) {
  console.error('Token-discipline violations (use tokens, not literals):\n' + violations.join('\n'));
  process.exit(1);
}
console.log(`token-discipline OK (${[...SCAN_DIRS, ...SCAN_FILES].join(', ')})`);
