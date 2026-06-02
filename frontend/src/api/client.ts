import type {
  ClubOption,
  CoachPolicy,
  CommandCenterResponse,
  CommandCenterSimResponse,
  FastForwardResponse,
  FastForwardStopPoint,
  DynastyOfficeResponse,
  MatchHighlightsResponse,
  MatchReplayResponse,
  RecruitingActionResponse,
  SaveListResponse,
  StatusResponse,
} from '../types';

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

// WT-12: per-process launch token. The server mints it at startup, injects it
// into index.html as <meta name="launch-token">, and also exposes it at
// GET /api/launch-token. We attach it as a header on every mutating request so
// a cross-origin drive-by page (which cannot read the meta tag or that GET's
// body under the same-origin policy) cannot forge a mutating call. Read the
// meta synchronously when present (prod build); otherwise fetch it once and
// cache it (the vite dev server serves the un-rewritten source index.html).
const LAUNCH_TOKEN_HEADER = 'X-Dodgeball-Launch-Token';
let launchTokenPromise: Promise<string | null> | null = null;

function readLaunchTokenMeta(): string | null {
  if (typeof document === 'undefined') return null;
  const meta = document.querySelector('meta[name="launch-token"]');
  const content = meta?.getAttribute('content');
  return content && content.length > 0 ? content : null;
}

async function resolveLaunchToken(): Promise<string | null> {
  const fromMeta = readLaunchTokenMeta();
  if (fromMeta) return fromMeta;
  if (!launchTokenPromise) {
    launchTokenPromise = fetch('/api/launch-token')
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) =>
        isObject(payload) && typeof payload.token === 'string' ? payload.token : null,
      )
      .catch(() => null);
  }
  return launchTokenPromise;
}

export async function apiGet<T>(url: string): Promise<T> {
  return apiRequest<T>(url);
}

export async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  const token = await resolveLaunchToken();
  const headers: Record<string, string> = {};
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers[LAUNCH_TOKEN_HEADER] = token;
  return apiRequest<T>(url, {
    method: 'POST',
    headers: Object.keys(headers).length > 0 ? headers : undefined,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function apiRequest<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const payload = await readPayload(response);
  if (!response.ok) {
    const detail = isObject(payload) && typeof payload.detail === 'string'
      ? payload.detail
      : `Request failed: ${response.status}`;
    throw new ApiError(detail, response.status);
  }
  return payload as T;
}

async function readPayload(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) return {};
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null;
}

export const careerApi = {
  saveState: () => apiGet<{ loaded: boolean; active_path: string | null }>('/api/save-state'),
  status: () => apiGet<StatusResponse>('/api/status'),
  unloadSave: () => apiPost<{ status: string }>('/api/saves/unload'),
};

export const saveApi = {
  list: () => apiGet<SaveListResponse>('/api/saves'),
  clubs: () => apiGet<{ clubs: ClubOption[] }>('/api/saves/clubs'),
  load: (path: string) => apiPost<{ status: string; path: string }>('/api/saves/load', { path }),
  delete: (path: string) => apiPost<{ status: string }>('/api/saves/delete', { path }),
  create: (body: { name: string; club_id: string; ruleset_selection?: string | null }) =>
    apiPost<{ status: string; path: string }>('/api/saves/new', body),
  buildFromScratch: (body: {
    save_name: string;
    club_name: string;
    city: string;
    colors: string;
    coach_name: string;
    coach_backstory: string;
    roster_player_ids: string[];
    ruleset_selection?: string | null;
  }) => apiPost<{ status: string; path: string }>('/api/saves/build-from-scratch', body),
};

export const commandApi = {
  center: () => apiGet<CommandCenterResponse>('/api/command-center'),
  savePlan: (body: Partial<CommandCenterResponse['plan']> & { intent?: string }) =>
    apiPost<CommandCenterResponse>('/api/command-center/plan', body),
  saveTactics: (body: CoachPolicy) =>
    apiPost<CoachPolicy>('/api/tactics', body),
  saveLineup: (starterIds: string[]) =>
    apiPost<{ status: string; ordered_player_ids: string[]; warnings: string[] }>(
      '/api/lineup',
      { starter_ids: starterIds },
    ),
  clearLineup: () =>
    apiPost<{ status: string; ordered_player_ids: string[]; warnings: string[] }>(
      '/api/lineup',
      { starter_ids: null },
    ),
  skipSeasonPreview: (skipped: boolean) =>
    apiPost<CommandCenterResponse>('/api/command-center/season-preview/skip', { skipped }),
  scoutOpponent: () =>
    apiPost<CommandCenterResponse>('/api/command-center/scout', {}),
  confirmLineup: () =>
    apiPost<CommandCenterResponse>('/api/command-center/confirm-lineup', {}),
  simulate: (body: { intent?: string }) =>
    apiPost<CommandCenterSimResponse>('/api/command-center/simulate', body),
  fastForward: (body: { max_weeks?: number; stop_point?: FastForwardStopPoint } = {}) =>
    apiPost<FastForwardResponse>('/api/command-center/fast-forward', body),
  replay: (matchId: string) =>
    apiGet<MatchReplayResponse>(`/api/matches/${encodeURIComponent(matchId)}/replay`),
  highlights: (matchId: string) =>
    apiGet<MatchHighlightsResponse>(`/api/matches/${encodeURIComponent(matchId)}/highlights`),
  voiceRegister: (tier: number) =>
    apiGet<Record<string, string>>(`/api/voice-register/${tier}`),
};

export const dynastyApi = {
  office: () => apiGet<DynastyOfficeResponse>('/api/dynasty-office'),
  scoutProspect: (prospectId: string) =>
    apiPost<RecruitingActionResponse>(`/api/recruiting/scout/${encodeURIComponent(prospectId)}`),
  contactProspect: (prospectId: string) =>
    apiPost<RecruitingActionResponse>(`/api/recruiting/contact/${encodeURIComponent(prospectId)}`),
  visitProspect: (prospectId: string) =>
    apiPost<RecruitingActionResponse>(`/api/recruiting/visit/${encodeURIComponent(prospectId)}`),
  hireStaff: (candidateId: string) =>
    apiPost<DynastyOfficeResponse>('/api/dynasty-office/staff/hire', { candidate_id: candidateId }),
};
