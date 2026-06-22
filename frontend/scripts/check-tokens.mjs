import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, extname } from 'node:path';
import { countBraces } from './css-braces.mjs';

// Phase 8: the gate now scans the WHOLE component tree. SCAN_DIRS is the design
// surface; SCAN_FILES pins explicit files outside those dirs.
const SCAN_DIRS = ['src/ui', 'src/styles', 'src/components', 'src/legibility', 'src/domain'];
// SCAN_FILES may contain explicit files (scanned as-is) that live outside SCAN_DIRS.
const SCAN_FILES = ['src/App.module.css', 'src/components/SaveMenu.module.css'];
// Px discipline is tight ONLY in the design-system layer (tokens + primitives +
// shared styles). Component layout DIMENSIONS (widths/heights) are legitimate raw
// px per spec §5, so the raw-px rule applies to these dirs alone. COLOR checks
// (hex/rgba/hsl/legacy-var) apply to EVERY scanned file regardless.
const PX_SCOPE_DIRS = ['src/ui', 'src/styles'];

const HEX = /#[0-9a-fA-F]{3,8}\b/;
// raw px other than 0/1px hairlines
const PX = /(?<![\w.])(?!0px|1px)\d{1,4}px\b/;
// raw color FUNCTION literals: legit color usage goes through var(--token)
// (no `rgba(`/`hsl(` substring), so a raw rgba()/hsl() in a component is a literal.
const COLORFN = /\b(?:rgba?|hsla?)\(/i;
// Legacy token namespaces. Floodlight components must reference ONLY Floodlight
// tokens (--court/--raise/--text/--volt/--ok/--gold/--out/--line/--space/--radius/
// --font/--overlay/--tint-neutral/--out-line/--volt-glow). The retired global
// systems used `var(--dm-*)` (dark) and `var(--color-*)` (warm) — flag both so a
// component cannot pull color through a legacy var. NOTE: `--legacy-*` is the
// SANCTIONED archive-screen namespace (tokens.css §legacy) and is intentionally
// NOT matched here.
const LEGACYVAR = /var\(\s*--(?:dm|color)-/;
// Whole-file exemptions: the token source itself + test fixtures.
const ALLOW_FILE = /(tokens\.css|\.test\.)/;
// Per-line exemptions:
//   - viewBox: SVG viewBox attributes legitimately carry coordinate numbers.
//   - token-gate-allow: an explicit code-comment marker tagging a line as
//     user/club IDENTITY content color (kit swatches, monogram palette) — NOT
//     theme palette, so exempt. The marker MUST survive comment-stripping, so it
//     is matched against the RAW line (before comments are removed).
const ALLOW_LINE = /viewBox/;
const KIT_DATA_MARKER = 'token-gate-allow';

// Strip // line comments and /* */ block-comment CONTENT so hex/rgba/px that live
// in COMMENTS never flag (marker comments, doc examples). Block comments may span
// MANY lines, so a whole file is stripped in one pass that tracks open-block state
// across lines, then split back into lines (indices stay aligned 1:1 with input).
function stripComments(text) {
  const lines = text.split('\n');
  let inBlock = false;
  return lines.map(line => {
    let out = '';
    let i = 0;
    while (i < line.length) {
      if (inBlock) {
        const close = line.indexOf('*/', i);
        if (close === -1) {
          i = line.length; // whole rest of line is comment
        } else {
          i = close + 2;
          inBlock = false;
        }
        continue;
      }
      // not in a block comment
      const lineComment = line.startsWith('//', i);
      const blockOpen = line.startsWith('/*', i);
      if (lineComment) {
        // `//` starts a line comment UNLESS it's part of a URL scheme (`://`).
        if (i > 0 && line[i - 1] === ':') {
          out += line[i];
          i += 1;
          continue;
        }
        break; // rest of line is a comment
      }
      if (blockOpen) {
        inBlock = true;
        i += 2;
        continue;
      }
      out += line[i];
      i += 1;
    }
    return out;
  });
}

function walk(dir) {
  let out = [];
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) out = out.concat(walk(p));
    else if (['.tsx', '.ts', '.css'].includes(extname(p))) out.push(p);
  }
  return out;
}

function normalize(file) {
  return file.split('\\').join('/');
}

function inPxScope(file) {
  const f = normalize(file);
  return PX_SCOPE_DIRS.some(d => f.startsWith(d + '/') || f.startsWith(d));
}

function checkFile(file, violations) {
  if (ALLOW_FILE.test(file)) return;
  const pxApplies = inPxScope(file);
  const text = readFileSync(file, 'utf8');
  const rawLines = text.split('\n');
  // Comment-stripped lines (block state tracked across the whole file).
  const strippedLines = stripComments(text);
  rawLines.forEach((rawLine, i) => {
    // Identity-content carve-out + viewBox exemption are checked on the RAW line
    // (the marker is a comment that comment-stripping would remove).
    if (ALLOW_LINE.test(rawLine)) return;
    if (rawLine.includes(KIT_DATA_MARKER)) return;
    // Scan the comment-stripped line so hex/rgba/px inside comments never flag.
    const line = strippedLines[i];
    const colorHit = HEX.test(line) || COLORFN.test(line) || LEGACYVAR.test(line);
    const pxHit = pxApplies && PX.test(line);
    if (colorHit || pxHit) {
      violations.push(`${normalize(file)}:${i + 1}  ${rawLine.trim()}`);
    }
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

// CSS brace-balance gate. Scans EVERY src/**/*.css (incl. *.module.css) — a WIDER
// net than the token scope above — because Vite/Rolldown concatenate index.css +
// all module CSS into ONE prod bundle, so a single unclosed @media/rule block
// silently swallows every later rule (2026-06-21: the whole app rendered unstyled
// on desktop from one missing `}` at the end of index.css). CSS parsers auto-close
// at EOF, so this is invisible to `vite build`/`eslint`/`vitest` — counting `{` vs
// `}` per file is the only static catch. No file is exempt (tokens.css included):
// an unclosed brace ANYWHERE in the concatenated bundle is fatal.
const cssFiles = walk('src').filter(f => extname(f) === '.css');
const braceViolations = [];
for (const file of cssFiles) {
  const { open, close } = countBraces(readFileSync(file, 'utf8'));
  if (open !== close) {
    braceViolations.push(
      `${normalize(file)}: ${open} '{' vs ${close} '}' (off by ${open - close})`,
    );
  }
}

let failed = false;
if (violations.length) {
  console.error('Token-discipline violations (use tokens, not literals):\n' + violations.join('\n'));
  failed = true;
} else {
  console.log(`token-discipline OK (${[...SCAN_DIRS, ...SCAN_FILES].join(', ')})`);
}
if (braceViolations.length) {
  console.error('CSS brace-balance violations (unclosed @media/rule block?):\n' + braceViolations.join('\n'));
  failed = true;
} else {
  console.log(`css-brace-balance OK (${cssFiles.length} css files)`);
}
if (failed) process.exit(1);
