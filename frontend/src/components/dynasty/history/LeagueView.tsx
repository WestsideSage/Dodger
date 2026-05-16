import { useEffect, useState } from 'react';
import { ProgramModal } from './ProgramModal';
import { formatRecordLabel, formatSeasonLabel, humanizeHistoryToken } from './formatters';

interface LeagueData {
  directory: { club_id: string; name: string }[];
  dynasty_rankings: { club_id: string; club_name: string; championships: number; longest_win_streak: number }[];
  records: { record_type: string; holder_id: string; record_value: number; set_in_season: string }[];
  hof: { player_id: string; player_name: string; induction_season: string; career_elims: number; championships: number; seasons_played: number }[];
  rivalries: { club_a: string; club_b: string; a_wins: number; b_wins: number; draws: number; meetings: number }[];
}

export function LeagueView() {
  const [data, setData] = useState<LeagueData | null>(null);
  const [modal, setModal] = useState<{ clubId: string; clubName: string } | null>(null);

  useEffect(() => {
    fetch('/api/history/league')
      .then((res) => res.json())
      .then(setData);
  }, []);

  if (!data) return <div style={{ color: '#475569', padding: '1rem' }}>Loading league history...</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      <div className="dm-panel">
        <p className="dm-kicker">Program Directory</p>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {data.directory.map((c) => (
            <button
              key={c.club_id}
              onClick={() => setModal({ clubId: c.club_id, clubName: c.name })}
              style={{
                padding: '0.4rem 0.75rem',
                border: '1px solid #334155',
                borderRadius: '4px',
                background: '#0f172a',
                color: '#cbd5e1',
                cursor: 'pointer',
                fontSize: '0.8rem',
              }}
            >
              {c.name}
            </button>
          ))}
        </div>
      </div>

      <div className="dm-panel">
        <p className="dm-kicker">Dynasty Rankings</p>
        {data.dynasty_rankings.length === 0 ? (
          <p style={{ color: '#475569', fontSize: '0.8rem' }}>No dynasty data yet.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
            {data.dynasty_rankings.map((r, i) => (
              <div
                key={r.club_id}
                style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', fontSize: '0.8rem' }}
              >
                <span style={{ color: '#475569', width: '1.5rem', textAlign: 'right' }}>{i + 1}.</span>
                <span style={{ flex: 1, color: '#e2e8f0' }}>{r.club_name}</span>
                <span style={{ color: '#f97316' }}>{r.championships} title{r.championships === 1 ? '' : 's'}</span>
                <span style={{ color: '#64748b', fontSize: '0.7rem' }}>win streak {r.longest_win_streak}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <div className="dm-panel" style={{ flex: 1, minWidth: '240px' }}>
          <p className="dm-kicker">All-Time Records</p>
          {data.records.length === 0 ? (
            <p style={{ color: '#475569', fontSize: '0.8rem' }}>No records set.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
              {data.records.map((r, i) => (
                <div key={i} style={{ fontSize: '0.75rem', paddingBottom: '0.55rem', borderBottom: '1px solid rgba(30,41,59,0.7)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'baseline' }}>
                    <span style={{ color: '#94a3b8' }}>{formatRecordLabel(r.record_type)}</span>
                    <span style={{ color: '#22d3ee', fontFamily: 'var(--font-mono-data)' }}>{r.record_value}</span>
                  </div>
                  <div style={{ color: '#e2e8f0', marginTop: '0.15rem' }}>
                    {humanizeHistoryToken(r.holder_id)}
                  </div>
                  <div style={{ color: '#475569', marginTop: '0.1rem' }}>
                    Set in {formatSeasonLabel(r.set_in_season)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="dm-panel" style={{ flex: 1, minWidth: '240px' }}>
          <p className="dm-kicker">Hall of Fame</p>
          {data.hof.length === 0 ? (
            <p style={{ color: '#475569', fontSize: '0.8rem' }}>No inductees yet.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {data.hof.map((h) => (
                <div key={h.player_id} style={{ fontSize: '0.75rem' }}>
                  <div style={{ color: '#fbbf24', fontWeight: 700 }}>{h.player_name}</div>
                  <div style={{ color: '#64748b' }}>
                    Inducted in {formatSeasonLabel(h.induction_season)} | {h.career_elims} eliminations | {h.championships} titles | {h.seasons_played} seasons
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="dm-panel">
        <p className="dm-kicker">Rivalries</p>
        {data.rivalries.length === 0 ? (
          <p style={{ color: '#475569', fontSize: '0.8rem' }}>No rivalry data yet - rivalries form after multiple meetings.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {data.rivalries.slice(0, 5).map((r, i) => (
              <div
                key={i}
                style={{
                  display: 'flex',
                  gap: '0.5rem',
                  alignItems: 'center',
                  padding: '0.5rem 0.75rem',
                  border: i === 0 ? '1px solid #334155' : 'none',
                  borderRadius: i === 0 ? '6px' : 0,
                  background: i === 0 ? '#0a1628' : 'transparent',
                  fontSize: '0.8rem',
                }}
              >
                {i === 0 && <span style={{ color: '#f97316', marginRight: '0.25rem' }}>Top</span>}
                <span style={{ flex: 1, color: '#e2e8f0' }}>
                  {r.club_a} vs {r.club_b}
                </span>
                <span style={{ color: '#94a3b8', fontSize: '0.7rem' }}>
                  {r.a_wins}-{r.b_wins}-{r.draws} ({r.meetings} meetings)
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {modal && (
        <ProgramModal
          clubId={modal.clubId}
          clubName={modal.clubName}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  );
}
