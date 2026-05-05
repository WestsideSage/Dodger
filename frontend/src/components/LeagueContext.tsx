import type { NewsResponse, ScheduleResponse, StandingsResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { Badge, CompactList, CompactListRow, DataTable, PageHeader, StatChip, StatusMessage, TableCell, TableHeadCell, type Tone } from './ui';

function scheduleTone(status: string): Tone {
  const normalized = status.toLowerCase();
  if (normalized.includes('complete') || normalized.includes('played')) return 'success';
  if (normalized.includes('pending')) return 'warning';
  return 'neutral';
}

export function Standings() {
  const { data, error, loading } = useApiResource<StandingsResponse>('/api/standings');

  if (error) return <StatusMessage title="Standings unavailable" tone="danger">{error}</StatusMessage>;
  if (loading) return <StatusMessage title="Loading standings">Updating the table.</StatusMessage>;
  if (!data) return <StatusMessage title="No standings">No standings data returned.</StatusMessage>;

  const leader = data.standings[0];
  const userClub = data.standings.find(row => row.is_user_club);

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow="League office"
        title="Standings"
        description="Dense table view with the managed club highlighted for quick league context."
        stats={
          <>
            <StatChip label="Leader" value={leader?.club_name ?? '-'} tone="warning" />
            <StatChip label="Your Pts" value={userClub?.points ?? '-'} tone="info" />
          </>
        }
      />
      <DataTable>
        <thead>
          <tr>
            <TableHeadCell sticky>Club</TableHeadCell>
            <TableHeadCell align="center">W</TableHeadCell>
            <TableHeadCell align="center">L</TableHeadCell>
            <TableHeadCell align="center">D</TableHeadCell>
            <TableHeadCell align="center">Pts</TableHeadCell>
            <TableHeadCell align="center">Diff</TableHeadCell>
          </tr>
        </thead>
        <tbody>
          {data.standings.map((row, index) => (
            <tr key={row.club_id} className={`border-b border-[var(--color-line)] last:border-0 hover:bg-[var(--color-cream)] ${row.is_user_club ? 'bg-[color-mix(in_srgb,var(--color-gym)_15%,var(--color-paper))]' : 'bg-[var(--color-paper)]'}`}>
              <TableCell sticky className="font-bold">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-[var(--color-muted)]">{index + 1}</span>
                  <span>{row.club_name}</span>
                  {row.is_user_club && <Badge tone="info">You</Badge>}
                </div>
              </TableCell>
              <TableCell align="center">{row.wins}</TableCell>
              <TableCell align="center">{row.losses}</TableCell>
              <TableCell align="center">{row.draws}</TableCell>
              <TableCell align="center" className="font-mono text-base font-bold">{row.points}</TableCell>
              <TableCell align="center" className={row.elimination_differential >= 0 ? 'text-[var(--color-teal)] font-bold' : 'text-[var(--color-danger)] font-bold'}>
                {row.elimination_differential > 0 ? '+' : ''}{row.elimination_differential}
              </TableCell>
            </tr>
          ))}
        </tbody>
      </DataTable>
    </div>
  );
}

export function Schedule() {
  const { data, error, loading } = useApiResource<ScheduleResponse>('/api/schedule');

  if (error) return <StatusMessage title="Schedule unavailable" tone="danger">{error}</StatusMessage>;
  if (loading) return <StatusMessage title="Loading schedule">Collecting fixtures.</StatusMessage>;
  if (!data) return <StatusMessage title="No schedule">No schedule data returned.</StatusMessage>;

  const userMatches = data.schedule.filter(row => row.is_user_match).length;

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow="Fixture desk"
        title="Schedule"
        description="Match list uses one row pattern so upcoming user fixtures stand out without extra scanning."
        stats={
          <>
            <StatChip label="Matches" value={data.schedule.length} />
            <StatChip label="Your games" value={userMatches} tone="info" />
          </>
        }
      />
      <CompactList>
        {data.schedule.map(row => (
          <CompactListRow
            key={row.match_id}
            highlight={row.is_user_match}
            className="schedule-row"
          >
            <span className="font-display uppercase tracking-wider text-xs text-[var(--color-muted)]">Week {row.week}</span>
            <span className="min-w-0 font-bold">
              {row.home_club_name} <span className="text-[var(--color-muted)]">vs</span> {row.away_club_name}
            </span>
            <Badge tone={scheduleTone(row.status)}>{row.status.replaceAll('_', ' ')}</Badge>
          </CompactListRow>
        ))}
      </CompactList>
    </div>
  );
}

export function NewsWire() {
  const { data, error, loading } = useApiResource<NewsResponse>('/api/news');

  if (error) return <StatusMessage title="News unavailable" tone="danger">{error}</StatusMessage>;
  if (loading) return <StatusMessage title="Loading wire">Checking league headlines.</StatusMessage>;
  if (!data) return <StatusMessage title="No news">No news data returned.</StatusMessage>;

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow="League wire"
        title="News"
        description="Compact headlines from recent match reports and season events."
        stats={<StatChip label="Items" value={data.items.length} tone="info" />}
      />
      <CompactList>
        {data.items.length === 0 && (
          <CompactListRow>
            <span className="text-[var(--color-muted)]">Season headlines will populate after match reports.</span>
          </CompactListRow>
        )}
        {data.items.map((item, index) => (
          <CompactListRow key={`${item.tag}-${item.match_id ?? item.player_id ?? index}`}>
            <div className="flex flex-col gap-1">
              <Badge tone="info" className="w-fit">{item.tag}</Badge>
              <span className="font-bold">{item.text}</span>
            </div>
          </CompactListRow>
        ))}
      </CompactList>
    </div>
  );
}
