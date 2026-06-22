import { describe, it, expect } from 'vitest';
import { countBraces, stripCssCommentsAndStrings } from './css-braces.mjs';

// These guard the brace-balance half of `npm run lint:tokens` (check-tokens.mjs).
// The 2026-06-21 incident: index.css ended with an unclosed `@media (max-width:720px) {`.
// CSS parsers auto-close at EOF, so build/eslint/vitest stayed green — only counting
// `{` vs `}` per file catches it. The comment/string cases below are why a naive count
// is not enough: a brace inside a comment or a `content:` string must NOT count.

describe('countBraces', () => {
  it('reports equal counts for a balanced rule', () => {
    const { open, close } = countBraces('.a { color: red; }');
    expect(open).toBe(1);
    expect(close).toBe(1);
  });

  it('flags an unclosed @media block (open > close)', () => {
    const css = '@media (max-width: 720px) {\n  .a { color: red; }';
    const { open, close } = countBraces(css);
    expect(open).toBe(2);
    expect(close).toBe(1);
  });

  it('ignores braces inside block comments', () => {
    // The comment carries 3 stray `}` that would unbalance a naive count.
    const css = '/* }}} a dangling block */ .a { color: red; }';
    const { open, close } = countBraces(css);
    expect(open).toBe(1);
    expect(close).toBe(1);
  });

  it('ignores braces inside double-quoted strings', () => {
    const css = '.a::before { content: "}"; }';
    const { open, close } = countBraces(css);
    expect(open).toBe(1);
    expect(close).toBe(1);
  });

  it('ignores braces inside single-quoted strings', () => {
    const css = ".a::before { content: '{{{'; }";
    const { open, close } = countBraces(css);
    expect(open).toBe(1);
    expect(close).toBe(1);
  });

  it('handles escaped quotes inside strings without losing string state', () => {
    // The escaped quote must not be read as the string terminator, or the trailing
    // `}` would leak back into code and miscount.
    const css = '.a::before { content: "he said \\"}\\" here"; }';
    const { open, close } = countBraces(css);
    expect(open).toBe(1);
    expect(close).toBe(1);
  });
});

describe('stripCssCommentsAndStrings', () => {
  it('removes block comment content but keeps surrounding code', () => {
    const out = stripCssCommentsAndStrings('a /* { drop } */ b');
    expect(out).not.toContain('{');
    expect(out).not.toContain('}');
    expect(out).toContain('a');
    expect(out).toContain('b');
  });

  it('removes string content but keeps the declaration braces', () => {
    const out = stripCssCommentsAndStrings('.a { content: "}}}"; }');
    // The rule braces survive; the ones inside the string are gone.
    expect((out.match(/\{/g) || []).length).toBe(1);
    expect((out.match(/\}/g) || []).length).toBe(1);
  });
});
