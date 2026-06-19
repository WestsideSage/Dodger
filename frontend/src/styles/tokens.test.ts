import { readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { describe, it, expect } from 'vitest';

const css = readFileSync(resolve(dirname(fileURLToPath(import.meta.url)), 'tokens.css'), 'utf8');

describe('floodlight tokens', () => {
  for (const name of [
    '--court', '--raise', '--raise2', '--line', '--line2', '--lit',
    '--text', '--text2', '--muted', '--out',
    '--volt', '--volt2', '--ok', '--gold', '--gold2',
    '--font-disp', '--font-head', '--font-ui', '--font-mono', '--font-serif',
    '--space-3', '--radius-lg',
  ]) {
    it(`defines ${name}`, () => { expect(css).toContain(`${name}:`); });
  }
  it('contains a base reset (box-sizing)', () => { expect(css).toContain('box-sizing'); });
});
