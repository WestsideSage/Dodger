import type {
  ClubOption,
  CommandCenterResponse,
  CommandCenterSimResponse,
  DynastyOfficeResponse,
  MatchReplayResponse,
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

export async function apiGet<T>(url: string): Promise<T> {
  return apiRequest<T>(url);
}

export async function apiPost<T>(url: string, body?: unknown): Promise<T> {
  return apiRequest<T>(url, {
    method: 'POST',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
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
  create: (body: { name: string; club_id: string }) => apiPost<{ status: string; path: string }>('/api/saves/new', body),
  buildFromScratch: (body: {
    save_name: string;
    club_name: string;
    city: string;
    colors: string;
    coach_name: string;
    coach_backstory: string;
    roster_player_ids: string[];
  }) => apiPost<{ status: string; path: string }>('/api/saves/build-from-scratch', body),
};

export const commandApi = {
  center: () => apiGet<CommandCenterResponse>('/api/command-center'),
  savePlan: (body: Partial<CommandCenterResponse['plan']> & { intent?: string }) =>
    apiPost<CommandCenterResponse>('/api/command-center/plan', body),
  simulate: (body: { intent?: string }) =>
    apiPost<CommandCenterSimResponse>('/api/command-center/simulate', body),
  replay: (matchId: string) =>
    apiGet<MatchReplayResponse>(`/api/matches/${encodeURIComponent(matchId)}/replay`),
};

export const dynastyApi = {
  office: () => apiGet<DynastyOfficeResponse>('/api/dynasty-office'),
  hireStaff: (candidateId: string) =>
    apiPost<DynastyOfficeResponse>('/api/dynasty-office/staff/hire', { candidate_id: candidateId }),
};
