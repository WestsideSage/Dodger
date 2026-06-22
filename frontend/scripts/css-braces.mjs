// Brace-balance helpers for the lint:tokens gate (check-tokens.mjs).
//
// Why this exists: on 2026-06-21 the Floodlight prod build rendered unstyled at
// every desktop width because index.css ended with an unclosed
// `@media (max-width: 720px) {`. Vite/Rolldown concatenate index.css + all
// *.module.css into ONE bundle, so the dangling block swallowed every later rule.
// CSS parsers auto-close unbalanced blocks at EOF, so `vite build`, `eslint`,
// `lint:tokens`, and `vitest` all stayed green. Counting `{` vs `}` per file is the
// only static signal that catches it.
//
// A naive count is fooled by braces that legitimately live inside `/* */` comments
// or inside string values (`content: "}"`). So we blank those out first. CSS has no
// `//` line comments, so only block comments and quoted strings can hide a brace.

// Replace the CONTENT of block comments and string literals with spaces, leaving
// everything else (and the source length) intact. Single pass over the text.
export function stripCssCommentsAndStrings(text) {
  let out = '';
  let i = 0;
  const n = text.length;
  let state = 'code'; // 'code' | 'block' | 'dquote' | 'squote'
  while (i < n) {
    const c = text[i];
    const c2 = i + 1 < n ? text[i + 1] : '';
    if (state === 'code') {
      if (c === '/' && c2 === '*') { state = 'block'; out += '  '; i += 2; continue; }
      if (c === '"') { state = 'dquote'; out += ' '; i += 1; continue; }
      if (c === "'") { state = 'squote'; out += ' '; i += 1; continue; }
      out += c;
      i += 1;
      continue;
    }
    if (state === 'block') {
      if (c === '*' && c2 === '/') { state = 'code'; out += '  '; i += 2; continue; }
      out += ' ';
      i += 1;
      continue;
    }
    // String states. A backslash escapes the next char (e.g. \" or \\), so it can
    // never terminate the string — consume both so the closing quote is found.
    const closer = state === 'dquote' ? '"' : "'";
    if (c === '\\') { out += '  '; i += 2; continue; }
    if (c === closer) { state = 'code'; out += ' '; i += 1; continue; }
    out += ' ';
    i += 1;
  }
  return out;
}

// Count braces in CSS, ignoring any that live inside comments or strings.
export function countBraces(text) {
  const stripped = stripCssCommentsAndStrings(text);
  let open = 0;
  let close = 0;
  for (const ch of stripped) {
    if (ch === '{') open += 1;
    else if (ch === '}') close += 1;
  }
  return { open, close };
}
