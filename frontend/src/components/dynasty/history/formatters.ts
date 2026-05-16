const TOKEN_LABEL_OVERRIDES: Record<string, string> = {
  hof: 'Hall of Fame',
  mvp: 'MVP',
  ovr: 'OVR',
  most_eliminations_season: 'Most Eliminations (Season)',
  most_catches_season: 'Most Catches (Season)',
  most_eliminations_match: 'Most Eliminations (Match)',
  best_win_streak: 'Longest Win Streak',
  most_championships: 'Most Championships',
  career_catches: 'Career Catches',
  career_dodges: 'Career Dodges',
  career_elims: 'Career Eliminations',
};

function titleCaseWord(word: string) {
  if (!word) return word;
  if (word === word.toUpperCase() && /[A-Z]/.test(word) && word.length <= 4) {
    return word;
  }
  const lower = word.toLowerCase();
  if (TOKEN_LABEL_OVERRIDES[lower]) return TOKEN_LABEL_OVERRIDES[lower];
  if (/^\d+$/.test(word)) return word;
  return lower.charAt(0).toUpperCase() + lower.slice(1);
}

export function formatSeasonLabel(value: string | null | undefined) {
  if (!value) return 'Unknown season';
  const trimmed = value.trim();
  const seasonMatch = trimmed.match(/^season_(\d+)$/i);
  if (seasonMatch) {
    return `Season ${seasonMatch[1]}`;
  }
  return trimmed
    .replaceAll('-', ' ')
    .split(/[_\s]+/)
    .filter(Boolean)
    .map(titleCaseWord)
    .join(' ');
}

export function humanizeHistoryToken(value: string | null | undefined) {
  if (!value) return 'Unknown';
  const trimmed = value.trim();
  if (!trimmed) return 'Unknown';
  const override = TOKEN_LABEL_OVERRIDES[trimmed.toLowerCase()];
  if (override) return override;
  if (/^season_\d+$/i.test(trimmed)) return formatSeasonLabel(trimmed);
  return trimmed
    .replaceAll('-', ' ')
    .split(/[_\s]+/)
    .filter(Boolean)
    .map(titleCaseWord)
    .join(' ');
}

export function formatRecordLabel(recordType: string) {
  return TOKEN_LABEL_OVERRIDES[recordType.toLowerCase()] ?? humanizeHistoryToken(recordType);
}

export function formatTimelineLabel(value: string | null | undefined) {
  if (!value) return 'Milestone';
  const trimmed = value.trim();
  if (!trimmed) return 'Milestone';

  const match = trimmed.match(/^([^:]+):\s*(.+)$/);
  if (!match) {
    return humanizeHistoryToken(trimmed);
  }

  const [, prefix, suffix] = match;
  const normalizedPrefix = prefix.trim().toLowerCase();
  if (normalizedPrefix === 'record') {
    return `Record: ${humanizeHistoryToken(suffix)}`;
  }
  if (normalizedPrefix === 'hof') {
    return `Hall of Fame: ${humanizeHistoryToken(suffix)}`;
  }

  return `${humanizeHistoryToken(prefix)}: ${humanizeHistoryToken(suffix)}`;
}
