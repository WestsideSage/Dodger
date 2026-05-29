import { Badge } from '../../ui';
import type { Aftermath } from '../../../types';
import { formatScoreline } from '../matchResult';

export function MatchCard({ data }: { data: Aftermath['match_card'] }) {
  if (!data) return null;
  const scoreline = formatScoreline(data);
  const unit = scoreline.isOfficial ? 'PTS' : 'Survivors';
  return (
    <div className="dm-panel">
      <div style={{ display: 'flex', justifyContent: 'space-around', alignItems: 'center' }}>
        <div style={{ textAlign: 'center' }}>
          <h3>{data.home_club_id}</h3>
          <Badge>{scoreline.home.value} {unit}</Badge>
        </div>
        <div style={{ fontSize: '2rem', fontWeight: 800 }}>VS</div>
        <div style={{ textAlign: 'center' }}>
          <h3>{data.away_club_id}</h3>
          <Badge>{scoreline.away.value} {unit}</Badge>
        </div>
      </div>
    </div>
  );
}
