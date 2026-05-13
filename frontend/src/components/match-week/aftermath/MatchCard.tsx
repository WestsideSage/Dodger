import { Badge } from '../../ui';
import type { Aftermath } from '../../../types';

export function MatchCard({ data }: { data: Aftermath['match_card'] }) {
  if (!data) return null;
  return (
    <div className="dm-panel">
      <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <h3>{data.home_club_id}</h3>
          <Badge>{data.home_survivors} Survivors</Badge>
        </div>
        <div style={{ fontSize: '2rem', fontWeight: 800 }}>VS</div>
        <div style={{ textAlign: 'center' }}>
          <h3>{data.away_club_id}</h3>
          <Badge>{data.away_survivors} Survivors</Badge>
        </div>
      </div>
    </div>
  );
}
