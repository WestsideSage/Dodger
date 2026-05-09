import type { Player } from '../../types';
import { RatingBar } from '../ui';
import { PotentialBadge } from './PotentialBadge';
import { Sparkline } from './Sparkline';

export function PlayerTheaterRow({ player, starter }: { player: Player, starter: boolean }) {
  return (
    <tr style={{ background: starter ? 'rgba(34,211,238,0.06)' : undefined }}>
      <td style={{ padding: '1rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <div style={{ fontSize: '1.25rem', fontWeight: 900, color: '#475569' }}>#{player.id.split('_')[1]}</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: '1rem' }}>
                {player.name}
                {player.newcomer && <span style={{ marginLeft: '0.5rem', fontSize: '0.625rem', color: '#a78bfa', border: '1px solid #a78bfa', padding: '0 0.25rem', borderRadius: '2px' }}>NEWCOMER</span>}
            </div>
            <div style={{ fontSize: '0.75rem', color: '#94a3b8' }}>{player.archetype} · Age {player.age}</div>
          </div>
        </div>
      </td>
      <td style={{ padding: '1rem' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem 2rem' }}>
          <div>
            <div style={{ fontSize: '0.625rem', color: '#64748b', textTransform: 'uppercase' }}>Accuracy</div>
            <RatingBar rating={player.ratings.accuracy} compact />
          </div>
          <div>
            <div style={{ fontSize: '0.625rem', color: '#64748b', textTransform: 'uppercase' }}>Power</div>
            <RatingBar rating={player.ratings.power} compact />
          </div>
          <div>
            <div style={{ fontSize: '0.625rem', color: '#64748b', textTransform: 'uppercase' }}>Dodge</div>
            <RatingBar rating={player.ratings.dodge} compact />
          </div>
          <div>
            <div style={{ fontSize: '0.625rem', color: '#64748b', textTransform: 'uppercase' }}>Catch</div>
            <RatingBar rating={player.ratings.catch} compact />
          </div>
        </div>
      </td>
      <td style={{ padding: '1rem' }}>
        <PotentialBadge tier={player.potential_tier} confidence={player.scouting_confidence} />
      </td>
      <td style={{ padding: '1rem', textAlign: 'right' }}>
        <div style={{ fontSize: '1.25rem', fontWeight: 800, color: '#22d3ee' }}>{player.overall}</div>
        <Sparkline data={player.weekly_ovr_history} />
      </td>
      <td style={{ padding: '1rem' }}>
        <span className={`dm-badge ${starter ? 'dm-badge-cyan' : 'dm-badge-slate'}`}>{player.role}</span>
      </td>
    </tr>
  );
}
