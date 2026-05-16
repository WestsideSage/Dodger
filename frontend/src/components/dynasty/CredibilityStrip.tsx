import type { DynastyOfficeResponse } from '../../types';

type RecruitingCredibility = DynastyOfficeResponse['recruiting']['credibility'];

export function CredibilityStrip({ credibility }: { credibility: RecruitingCredibility }) {
  return (
    <div className="dm-panel dynasty-credibility-card">
      <p className="dm-kicker">Program Credibility</p>
      <div style={{ marginTop: '0.4rem', fontSize: '2.4rem', lineHeight: 1, fontWeight: 900, color: '#22d3ee' }}>
        Tier {credibility.grade}
      </div>
      <p style={{ margin: '0.45rem 0 0', fontSize: '0.78rem', color: '#94a3b8' }}>
        Score <span className="dm-data" style={{ color: '#e2e8f0', fontWeight: 800 }}>{credibility.score}</span>
      </p>
      <div style={{ marginTop: '1rem', borderTop: '1px solid #1e293b', paddingTop: '0.85rem' }}>
        {credibility.evidence.map((item: string, index: number) => (
          <div
            key={`${index}-${item}`}
            style={{ display: 'flex', gap: '0.45rem', fontSize: '0.74rem', color: '#94a3b8', lineHeight: 1.45, marginBottom: '0.45rem' }}
          >
            <span style={{ color: '#22d3ee' }}>+</span>
            <span>{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
