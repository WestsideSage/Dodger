import type { Player } from '../../types';
import { RatingBar } from '../ui';
import { formatOverall, formatPlayerName, formatRole } from './playerDisplay';

export function PlayerCompactRow({ player, starter, onClick }: { player: Player, starter: boolean, onClick?: () => void }) {
  return (
    <tr
      onClick={onClick}
      style={{
        background: starter ? 'rgba(34,211,238,0.06)' : undefined,
        cursor: onClick ? 'pointer' : undefined,
      }}
    >
      <td style={{ padding: '0.5rem' }}>{formatPlayerName(player)}</td>
      <td style={{ padding: '0.5rem' }}><RatingBar rating={player.ratings.accuracy} compact /></td>
      <td style={{ padding: '0.5rem' }}><RatingBar rating={player.ratings.power} compact /></td>
      <td style={{ padding: '0.5rem' }}><RatingBar rating={player.ratings.dodge} compact /></td>
      <td style={{ padding: '0.5rem' }}><RatingBar rating={player.ratings.catch} compact /></td>
      <td style={{ padding: '0.5rem', fontWeight: 700 }}>{formatOverall(player)}</td>
      <td style={{ padding: '0.5rem' }}><span className={`dm-badge ${starter ? 'dm-badge-cyan' : 'dm-badge-slate'}`}>{formatRole(player)}</span></td>
    </tr>
  );
}
