import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, extname } from 'node:path';

const SCAN_DIRS = ['src/ui', 'src/styles'];
const HEX = /#[0-9a-fA-F]{3,8}\b/;
// raw px other than 0/1px hairlines
const PX = /(?<![\w.])(?!0px|1px)\d{1,4}px\b/;
const ALLOW = /(viewBox|tokens\.css|\.test\.|\.svg)/;

function walk(dir) {
  let out = [];
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) out = out.concat(walk(p));
    else if (['.tsx', '.ts', '.css'].includes(extname(p))) out.push(p);
  }
  return out;
}

const violations = [];
for (const dir of SCAN_DIRS) {
  for (const file of walk(dir)) {
    if (ALLOW.test(file)) continue;
    const text = readFileSync(file, 'utf8');
    text.split('\n').forEach((line, i) => {
      if (ALLOW.test(line)) return;
      if (HEX.test(line) || PX.test(line)) violations.push(`${file}:${i + 1}  ${line.trim()}`);
    });
  }
}

if (violations.length) {
  console.error('Token-discipline violations (use tokens, not literals):\n' + violations.join('\n'));
  process.exit(1);
}
console.log(`token-discipline OK (${SCAN_DIRS.join(', ')})`);
