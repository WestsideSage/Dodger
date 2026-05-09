import type { Player } from '../../types';
import { RatingBar } from '../ui';

export function PlayerCompactRow({ player, starter }: { player: Player, starter: boolean }) {
  return (
    <tr style={{ background: starter ? 'rgba(34,211,238,0.06)' : undefined }}>
      <td style={{ padding: '0.5rem' }}>{player.name}</td>
      <td style={{ padding: '0.5rem' }}><RatingBar rating={player.ratings.accuracy} compact /></td>
      <td style={{ padding: '0.5rem' }}><RatingBar rating={player.ratings.power} compact /></td>
      <td style={{ padding: '0.5rem' }}><RatingBar rating={player.ratings.dodge} compact /></td>
      <td style={{ padding: '0.5rem' }}><RatingBar rating={player.ratings.catch} compact /></td>
      <td style={{ padding: '0.5rem', fontWeight: 700 }}>{player.overall}</td>
      <td style={{ padding: '0.5rem' }}><span className={`dm-badge ${starter ? 'dm-badge-cyan' : 'dm-badge-slate'}`}>{player.role}</span></td>
    </tr>
  );
}
