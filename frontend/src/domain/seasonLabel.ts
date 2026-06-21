// Single source of truth for season-label parsing, display, and ordering.
// Replaces the divergent dynasty/history/formatters.ts formatSeasonLabel +
// MyProgramView seasonTick string handling, and adds the NUMERIC comparator
// that fixes the season_10 < season_2 lexical-sort trap (audit §2.J #96).

const SEASON_RE = /^season_(\d+)$/i;

/** The integer season for `season_N` labels; null when not a numbered season. */
export function parseSeasonNumber(value: string | null | undefined): number | null {
  if (!value) return null;
  const m = value.trim().match(SEASON_RE);
  return m ? Number(m[1]) : null;
}

/** Display label. `season_N` → "Season N"; other tokens pass through humanized. */
export function formatSeasonLabel(value: string | null | undefined): string {
  if (!value) return 'Unknown season';
  const n = parseSeasonNumber(value);
  if (n !== null) return `Season ${n}`;
  return value
    .trim()
    .replaceAll('-', ' ')
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((w) => (/^\d+$/.test(w) ? w : w.charAt(0).toUpperCase() + w.slice(1).toLowerCase()))
    .join(' ');
}

/** Ascending numeric comparator. Unparseable labels sort AFTER all numbered ones. */
export function compareSeasonAsc(a: string | null | undefined, b: string | null | undefined): number {
  const na = parseSeasonNumber(a);
  const nb = parseSeasonNumber(b);
  if (na === null && nb === null) return 0;
  if (na === null) return 1;
  if (nb === null) return -1;
  return na - nb;
}

/** Descending numeric comparator (latest season first). Unparseable labels last. */
export function compareSeasonDesc(a: string | null | undefined, b: string | null | undefined): number {
  const na = parseSeasonNumber(a);
  const nb = parseSeasonNumber(b);
  if (na === null && nb === null) return 0;
  if (na === null) return 1;
  if (nb === null) return -1;
  return nb - na;
}
