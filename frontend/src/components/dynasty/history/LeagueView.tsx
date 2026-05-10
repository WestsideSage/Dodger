import { useEffect, useState } from 'react';
import { ProgramModal } from './ProgramModal';

interface LeagueData {
  directory: { club_id: string; name: string }[];
  dynasty_rankings: { club_id: string; club_name: string; championships: number; longest_win_streak: number }[];
  records: { record_type: string; holder_id: string; record_value: number; set_in_season: string }[];
  hof: { player_id: string; player_name: string; induction_season: string; career_elims: number; championships: number; seasons_played: number }[];
  rivalries: { club_a: string; club_b: string; a_wins: number; b_wins: number; draws: number; meetings: number }[];
}

const RECORD_LABEL: Record<string, string> = {
  most_eliminations_season: 'Most Elims (Season)',
  most_catches_season: 'Most Catches (Season)',
  most_eliminations_match: 'Most Elims (Match)',
  best_win_streak: 'Longest Win Streak',
};

export function LeagueView() {
  const [data, setData] = useState<LeagueData | null>(null);
  const [modal, setModal] = useState<{ clubId: string; clubName: string } | null>(null);

  useEffect(() => {
    fetch('/api/history/league')
      .then((res) => res.json())
      .then(setData);
  }, []);

  if (!data) return <div style={{ color: '#475569', padding: '1rem' }}>Loading league history…</div>;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Program Directory */}
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

      {/* Dynasty Rankings */}
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
                <span style={{ color: '#f97316' }}>🏆 {r.championships}</span>
                <span style={{ color: '#64748b', fontSize: '0.7rem' }}>streak {r.longest_win_streak}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* All-Time Records + HoF */}
      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
        <div className="dm-panel" style={{ flex: 1, minWidth: '240px' }}>
          <p className="dm-kicker">All-Time Records</p>
          {data.records.length === 0 ? (
            <p style={{ color: '#475569', fontSize: '0.8rem' }}>No records set.</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {data.records.map((r, i) => (
                <div key={i} style={{ fontSize: '0.75rem' }}>
                  <div style={{ color: '#94a3b8' }}>
                    {RECORD_LABEL[r.record_type] ?? r.record_type}
                  </div>
                  <div style={{ color: '#e2e8f0' }}>
                    {r.holder_id} — {r.record_value}
                    <span style={{ color: '#475569', marginLeft: '0.4rem' }}>{r.set_in_season}</span>
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
                  <div style={{ color: '#fbbf24', fontWeight: 700 }}>⭐ {h.player_name}</div>
                  <div style={{ color: '#64748b' }}>
                    Class of {h.induction_season} · {h.career_elims} elims · {h.championships} titles · {h.seasons_played} seasons
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Rivalries */}
      <div className="dm-panel">
        <p className="dm-kicker">Rivalries</p>
        {data.rivalries.length === 0 ? (
          <p style={{ color: '#475569', fontSize: '0.8rem' }}>No rivalry data yet — rivalries form after multiple meetings.</p>
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
                {i === 0 && <span style={{ color: '#f97316', marginRight: '0.25rem' }}>🔥</span>}
                <span style={{ flex: 1, color: '#e2e8f0' }}>
                  {r.club_a} vs {r.club_b}
                </span>
                <span style={{ color: '#94a3b8', fontSize: '0.7rem' }}>
                  {r.a_wins}–{r.b_wins}–{r.draws} ({r.meetings} meetings)
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal */}
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
