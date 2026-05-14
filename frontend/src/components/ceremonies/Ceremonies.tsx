import { useState } from 'react';
import { CeremonyShell } from './CeremonyShell';
import type {
  OffseasonAward,
  OffseasonBeat,
  OffseasonFixture,
  OffseasonRetiree,
  OffseasonSigning,
} from '../../types';

type AwardsBeat = Extract<OffseasonBeat, { key: 'awards' }>;
type RetirementsBeat = Extract<OffseasonBeat, { key: 'retirements' }>;
type RecruitmentBeat = Extract<OffseasonBeat, { key: 'recruitment' }>;
type ScheduleRevealBeat = Extract<OffseasonBeat, { key: 'schedule_reveal' }>;

const AWARD_ICON: Record<string, string> = {
  mvp: '🏆',
  best_thrower: '🎯',
  best_catcher: '🤲',
  best_newcomer: '⚡',
};

const AWARD_COLOR: Record<string, string> = {
  mvp: '#f97316',
  best_thrower: '#3b82f6',
  best_catcher: '#10b981',
  best_newcomer: '#eab308',
};

const TIER_COLOR: Record<string, string> = {
  Elite: '#10b981',
  High: '#3b82f6',
  Solid: '#94a3b8',
  Limited: '#64748b',
  Unknown: '#475569',
};

export function AwardsNight({ beat, onComplete, acting }: { beat: AwardsBeat; onComplete: () => void; acting?: boolean }) {
    const awards = beat.payload.awards;

    if (awards.length === 0) {
        return (
            <CeremonyShell
                title={beat.title}
                eyebrow="Awards"
                description="The league honors the season's finest."
                stages={1}
                renderStage={() => (
                    <div style={{ textAlign: 'center', color: '#94a3b8' }}>
                        {typeof beat.body === 'string' ? beat.body : 'No awards this season.'}
                    </div>
                )}
                onComplete={onComplete}
                isActing={acting}
            />
        );
    }

    return (
        <CeremonyShell
            title={beat.title}
            eyebrow="Awards Night"
            description="The league gathers to honor the season's best."
            stages={awards.length}
            renderStage={(stage) => (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%', maxWidth: '480px', margin: '0 auto' }}>
                    {awards.slice(0, stage).map((award: OffseasonAward, i: number) => {
                        const color = AWARD_COLOR[award.award_type] ?? '#f97316';
                        const icon = AWARD_ICON[award.award_type] ?? '🏅';
                        // MVP (index 0) is always highlighted; others are dimmer
                        const isHighlighted = i === 0;
                        return (
                            <div
                                key={i}
                                className="fade-in"
                                style={{
                                    border: `1px solid ${isHighlighted ? color : '#334155'}`,
                                    borderRadius: '8px',
                                    padding: '1rem',
                                    background: isHighlighted ? `${color}11` : '#0f172a',
                                    opacity: isHighlighted ? 1 : 0.65,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '1rem',
                                }}
                            >
                                <span style={{ fontSize: '2rem' }}>{icon}</span>
                                <div style={{ flex: 1 }}>
                                    <div style={{ fontSize: '0.65rem', color: isHighlighted ? color : '#475569', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '0.2rem' }}>
                                        {award.award_name}
                                    </div>
                                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: isHighlighted ? color : '#e2e8f0' }}>
                                        {award.player_name}
                                    </div>
                                    <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.15rem' }}>
                                        {award.club_name} · {award.season_stat_label}
                                    </div>
                                    <div style={{ fontSize: '0.7rem', color: '#475569', marginTop: '0.1rem' }}>
                                        {award.career_stat} career elims{award.ovr ? ` · OVR ${award.ovr}` : ''}
                                    </div>
                                </div>
                                {!isHighlighted && i < stage - 1 && <span style={{ color: '#475569' }}>✓</span>}
                            </div>
                        );
                    })}
                </div>
            )}
            onComplete={onComplete}
            isActing={acting}
        />
    );
}

export function Graduation({ beat, onComplete, acting }: { beat: RetirementsBeat; onComplete: () => void; acting?: boolean }) {
  const retirees = beat.payload.retirees;

  if (retirees.length === 0) {
    return (
      <CeremonyShell
        title={beat.title}
        eyebrow="Graduation"
        description="Farewell to departing veterans."
        stages={1}
        renderStage={() => (
          <div style={{ textAlign: 'center', color: '#94a3b8' }}>
            {typeof beat.body === 'string' ? beat.body : 'No retirements this off-season.'}
          </div>
        )}
        onComplete={onComplete}
        isActing={acting}
      />
    );
  }

  return (
    <CeremonyShell
      title={beat.title}
      eyebrow="Graduation"
      description="Saying goodbye to departing veterans."
      stages={retirees.length}
      renderStage={(stage) => (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%', maxWidth: '480px', margin: '0 auto' }}>
          {retirees.slice(0, stage).map((r: OffseasonRetiree, i: number) => {
            const isLatest = i === stage - 1;
            const tierColor = TIER_COLOR[r.potential_tier] ?? '#475569';
            return (
              <div
                key={i}
                className="fade-in"
                style={{
                  border: `1px solid ${isLatest ? '#10b981' : '#334155'}`,
                  borderRadius: '8px',
                  padding: '1rem',
                  background: '#0f172a',
                  opacity: isLatest ? 1 : 0.55,
                }}
              >
                <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.35rem' }}>
                  {r.name}
                </div>
                {r.ovr_final ? (
                  <div style={{ fontSize: '0.75rem', color: '#64748b', marginBottom: '0.35rem' }}>
                    OVR {r.ovr_final}
                  </div>
                ) : null}
                <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginBottom: '0.5rem' }}>
                  {r.career_elims} career elims · {r.championships} titles · {r.seasons_played} seasons
                </div>
                <div style={{ fontSize: '0.7rem', color: tierColor, fontWeight: 600 }}>
                  {r.potential_tier} potential
                </div>
              </div>
            );
          })}
        </div>
      )}
      onComplete={onComplete}
      isActing={acting}
    />
  );
}

export function SigningDay({ beat, onComplete, acting }: { beat: RecruitmentBeat; onComplete: () => void; acting?: boolean }) {
  const playerSigning = beat.payload.player_signing;
  const otherSignings = beat.payload.other_signings;
  const totalStages = 1 + otherSignings.length;

  return (
    <CeremonyShell
      title={beat.title}
      eyebrow="Signing Day"
      description="The nation's top prospects have made their commitments."
      stages={totalStages}
      renderStage={(stage) => (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%', maxWidth: '480px', margin: '0 auto' }}>
          {/* Stage 1: player's pick */}
          {stage >= 1 && playerSigning && (
            <div
              className="fade-in"
              style={{
                border: '2px solid #22d3ee',
                borderRadius: '8px',
                padding: '1.25rem',
                background: '#083344',
              }}
            >
              <div style={{ fontSize: '0.65rem', color: '#22d3ee', fontWeight: 700, letterSpacing: '0.08em', marginBottom: '0.5rem' }}>
                YOUR PICK
              </div>
              <div style={{ fontSize: '1.2rem', fontWeight: 800, color: '#e2e8f0', marginBottom: '0.25rem' }}>
                {playerSigning.name}
              </div>
              <div style={{ fontSize: '0.8rem', color: '#94a3b8' }}>
                OVR {playerSigning.ovr}
                {playerSigning.age ? ` · Age ${playerSigning.age}` : ''}
                {playerSigning.role ? ` · ${playerSigning.role}` : ''}
              </div>
            </div>
          )}

          {/* Subsequent stages: AI signings */}
          {otherSignings.slice(0, stage - 1).map((s: OffseasonSigning, i: number) => (
            <div
              key={i}
              className="fade-in"
              style={{
                border: '1px solid #334155',
                borderRadius: '6px',
                padding: '0.75rem 1rem',
                background: '#0f172a',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
              }}
            >
              <div>
                <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{s.name}</span>
                <span style={{ color: '#64748b', fontSize: '0.75rem', marginLeft: '0.5rem' }}>→ {s.club_name}</span>
              </div>
              <span style={{ color: '#64748b', fontSize: '0.75rem' }}>OVR {s.ovr}</span>
            </div>
          ))}

          {!playerSigning && (
            <div style={{ textAlign: 'center', color: '#94a3b8' }}>
              {typeof beat.body === 'string' ? beat.body : 'Signing complete.'}
            </div>
          )}
        </div>
      )}
      onComplete={onComplete}
      isActing={acting}
    />
  );
}

export function NewSeasonEve({ beat, onComplete, acting }: { beat: ScheduleRevealBeat; onComplete: () => void; acting?: boolean }) {
    const fixtures = beat.payload.fixtures;
    const prediction: string = beat.payload.prediction;
    const seasonLabel: string = beat.payload.season_label;
    const [showAll, setShowAll] = useState(false);

    const playerFixtures = fixtures.filter((f: OffseasonFixture) => f.is_player_match);
    const displayedFixtures = showAll ? fixtures : playerFixtures;

    return (
        <CeremonyShell
            title={beat.title}
            eyebrow={seasonLabel ? `Season ${seasonLabel}` : 'New Season'}
            description="A new chapter begins."
            stages={2}
            renderStage={(stage) => (
                <div style={{ width: '100%', maxWidth: '520px', margin: '0 auto' }}>
                    {stage >= 1 && (
                        <div className="fade-in" style={{ marginBottom: '1rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                                <span style={{ fontSize: '0.7rem', color: '#64748b' }}>
                                    {showAll ? `All ${fixtures.length} matches` : `Your ${playerFixtures.length} match${playerFixtures.length !== 1 ? 'es' : ''}`}
                                </span>
                                {fixtures.length > playerFixtures.length && (
                                    <button
                                        onClick={() => setShowAll(!showAll)}
                                        style={{
                                            background: 'none',
                                            border: '1px solid #334155',
                                            borderRadius: '4px',
                                            padding: '0.2rem 0.5rem',
                                            color: '#64748b',
                                            fontSize: '0.7rem',
                                            cursor: 'pointer',
                                        }}
                                    >
                                        {showAll ? 'My Games' : 'Full Schedule'}
                                    </button>
                                )}
                            </div>

                            {displayedFixtures.length === 0 ? (
                                <div style={{ color: '#94a3b8', textAlign: 'center' }}>
                                    {typeof beat.body === 'string' ? beat.body : 'Schedule not available.'}
                                </div>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
                                    {displayedFixtures.map((f: OffseasonFixture, i: number) => (
                                        <div
                                            key={i}
                                            style={{
                                                display: 'flex',
                                                gap: '0.5rem',
                                                alignItems: 'center',
                                                padding: '0.4rem 0.6rem',
                                                borderRadius: '4px',
                                                background: f.is_player_match ? '#1c1009' : 'transparent',
                                                border: f.is_player_match ? '1px solid #f97316' : '1px solid transparent',
                                            }}
                                        >
                                            <span style={{ color: '#475569', fontSize: '0.65rem', width: '3rem', flexShrink: 0 }}>
                                                Wk {f.week}
                                            </span>
                                            <span style={{ color: f.is_player_match ? '#fb923c' : '#94a3b8', fontSize: '0.8rem', flex: 1 }}>
                                                {f.home} vs {f.away}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {stage >= 2 && prediction && (
                        <div
                            className="fade-in"
                            style={{
                                borderLeft: '3px solid #f97316',
                                paddingLeft: '1rem',
                                color: '#cbd5e1',
                                fontSize: '0.9rem',
                                fontStyle: 'italic',
                                lineHeight: 1.5,
                            }}
                        >
                            {prediction}
                        </div>
                    )}
                </div>
            )}
            onComplete={onComplete}
            actionLabel="Start New Season"
            actionDescription="The offseason is complete. Start the next season when ready."
            isActing={acting}
        />
    );
}
