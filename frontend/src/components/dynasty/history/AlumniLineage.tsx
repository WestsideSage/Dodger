interface AlumnusEntry {
  id: string;
  name: string;
  seasons_played: number;
  career_elims: number;
  championships: number;
  ovr_final: number;
  potential_tier: string;
}

const TIER_TONE: Record<string, string> = {
  Elite: 'dm-badge-emerald',
  High: 'dm-badge-cyan',
  Limited: 'dm-badge-slate',
  Solid: 'dm-badge-violet',
  Unknown: 'dm-badge-slate',
};

export function AlumniLineage({ alumni }: { alumni: AlumnusEntry[] }) {
  if (alumni.length === 0) {
    return <p className="do-hist-card-note">No departed players have reached the archive yet.</p>;
  }

  return (
    <div className="do-hist-list">
      {alumni.map((entry) => (
        <div key={entry.id} className="do-hist-list-row">
          <div className="main">
            <strong>{entry.name}</strong>
            <span className="meta">
              {entry.seasons_played} season{entry.seasons_played === 1 ? '' : 's'} - {entry.career_elims} career elims
            </span>
          </div>
          <div className="side">
            <span className={`dm-badge ${TIER_TONE[entry.potential_tier] ?? 'dm-badge-slate'}`}>
              {entry.potential_tier}
            </span>
            <span className="note">
              {entry.championships} title{entry.championships === 1 ? '' : 's'} - Final OVR {entry.ovr_final}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
