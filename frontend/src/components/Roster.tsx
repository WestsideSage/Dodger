import { useMemo } from 'react';
import type { Player, RosterResponse } from '../types';
import { useApiResource } from '../hooks/useApiResource';
import { Badge, DataTable, PageHeader, RatingBar, StatChip, StatusMessage, TableCell, TableHeadCell } from './ui';

function overallRating(player: Player): number {
  if (Number.isFinite(player.overall)) return Math.round(player.overall);
  const ratings = player.ratings;
  return Math.round((ratings.accuracy + ratings.power + ratings.dodge + ratings.catch + (ratings.tactical_iq ?? 50)) / 5);
}

function ratingTone(value: number) {
  if (value >= 80) return 'text-[var(--color-teal)]';
  if (value >= 65) return 'text-[var(--color-sage)]';
  if (value >= 50) return 'text-[var(--color-mustard)]';
  return 'text-[var(--color-danger)]';
}

export function Roster() {
  const { data, loading, error } = useApiResource<RosterResponse>('/api/roster');

  const defaultLineupIds = useMemo(
    () => new Set(data?.default_lineup ?? []),
    [data?.default_lineup]
  );

  const roster = useMemo(
    () => (data?.roster ?? [])
      .map(player => ({ player, overall: overallRating(player), starter: defaultLineupIds.has(player.id) }))
      .sort((a, b) => Number(b.starter) - Number(a.starter) || b.overall - a.overall || a.player.age - b.player.age),
    [data?.roster, defaultLineupIds]
  );

  if (loading) return <StatusMessage title="Loading roster">Building the club sheet.</StatusMessage>;
  if (error) return <StatusMessage title="Roster unavailable" tone="danger">{error}</StatusMessage>;
  if (!data) return <StatusMessage title="No roster">No roster data returned.</StatusMessage>;

  const starters = roster.filter(row => row.starter).length;
  const averageOverall = roster.length
    ? Math.round(roster.reduce((total, row) => total + row.overall, 0) / roster.length)
    : 0;

  return (
    <div className="flex flex-col gap-5">
      <PageHeader
        eyebrow="Club room"
        title="Team Roster"
        description="Starters are pinned first; ratings stay compact so comparison is fast."
        stats={
          <>
            <StatChip label="Players" value={roster.length} />
            <StatChip label="Starters" value={starters} tone="warning" />
            <StatChip label="Avg OVR" value={averageOverall} tone="info" />
          </>
        }
      />

      <DataTable>
        <thead>
          <tr>
            <TableHeadCell sticky>Name</TableHeadCell>
            <TableHeadCell align="center">Role</TableHeadCell>
            <TableHeadCell align="center">Archetype</TableHeadCell>
            <TableHeadCell align="center">Age</TableHeadCell>
            <TableHeadCell align="center">OVR</TableHeadCell>
            <TableHeadCell align="center">Pot</TableHeadCell>
            <TableHeadCell>Tactical IQ</TableHeadCell>
            <TableHeadCell>Accuracy</TableHeadCell>
            <TableHeadCell>Power</TableHeadCell>
            <TableHeadCell>Dodge</TableHeadCell>
            <TableHeadCell>Catch</TableHeadCell>
            <TableHeadCell>Stamina</TableHeadCell>
          </tr>
        </thead>
        <tbody>
          {roster.map(({ player, overall, starter }) => (
            <tr key={player.id} className={`border-b border-[var(--color-line)] last:border-0 transition-colors hover:bg-[var(--color-cream)] ${starter ? 'bg-[color-mix(in_srgb,var(--color-mustard)_18%,var(--color-paper))]' : 'bg-[var(--color-paper)]'}`}>
              <TableCell sticky className="min-w-44 font-bold">
                <div className="flex flex-col">
                  <span>{player.name}</span>
                  {player.newcomer && <span className="text-[11px] font-normal text-[var(--color-muted)]">Newcomer</span>}
                </div>
              </TableCell>
              <TableCell align="center">
                <Badge tone={starter ? 'warning' : 'neutral'}>{player.role ?? (starter ? 'Starter' : 'Bench')}</Badge>
              </TableCell>
              <TableCell align="center"><span className="text-[11px] uppercase tracking-wider text-[var(--color-muted)]">{player.archetype ?? '–'}</span></TableCell>
              <TableCell align="center">{player.age}</TableCell>
              <TableCell align="center" className={`font-mono text-base font-bold ${ratingTone(overall)}`}>{overall}</TableCell>
              <TableCell align="center" className="font-mono font-bold">{player.traits.potential}</TableCell>
              <TableCell className="min-w-24"><RatingBar rating={player.ratings.tactical_iq ?? 50} compact /></TableCell>
              <TableCell className="min-w-24"><RatingBar rating={player.ratings.accuracy} compact /></TableCell>
              <TableCell className="min-w-24"><RatingBar rating={player.ratings.power} compact /></TableCell>
              <TableCell className="min-w-24"><RatingBar rating={player.ratings.dodge} compact /></TableCell>
              <TableCell className="min-w-24"><RatingBar rating={player.ratings.catch} compact /></TableCell>
              <TableCell className="min-w-24"><RatingBar rating={player.ratings.stamina} compact /></TableCell>
            </tr>
          ))}
        </tbody>
      </DataTable>
    </div>
  );
}
