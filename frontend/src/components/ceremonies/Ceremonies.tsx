import { useState } from 'react';
import { CeremonyShell } from './CeremonyShell';
import type {
  OffseasonAward,
  OffseasonBeat,
  OffseasonFixture,
  OffseasonRetiree,
  OffseasonSigning,
  SigningCard,
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

// The ceremony engine emits multi-line briefs ("Current roster sizes:" plus
// indented club rows, "Label: value" facts, blank-line section breaks). A bare
// {prose} render collapses all of it onto one run-on line — this keeps the
// backend's structure: section labels, indented rows, and fact rows stay rows.
function BriefProse({ text }: { text: string }) {
  const lines = text.split('\n');
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.3rem' }}>
      {lines.map((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={index} aria-hidden="true" style={{ height: '0.35rem' }} />;
        }
        const indented = line.startsWith('  ') || trimmed.startsWith('- ');
        const content = trimmed.startsWith('- ') ? trimmed.slice(2) : trimmed;
        if (!indented && trimmed.endsWith(':')) {
          return (
            <p
              key={index}
              style={{
                margin: '0.2rem 0 0',
                fontSize: '0.66rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
                color: '#64748b',
              }}
            >
              {trimmed.slice(0, -1)}
            </p>
          );
        }
        const kv = /^([^:]{2,42}):\s+(.+)$/.exec(content);
        if (kv) {
          return (
            <p key={index} style={{ margin: 0, paddingLeft: indented ? '0.85rem' : 0 }}>
              <span style={{ color: '#94a3b8' }}>{kv[1]}</span>
              <span style={{ color: '#475569' }}>{' · '}</span>
              <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{kv[2]}</span>
            </p>
          );
        }
        return (
          <p key={index} style={{ margin: 0, paddingLeft: indented ? '0.85rem' : 0 }}>
            {content}
          </p>
        );
      })}
    </div>
  );
}

export function AwardsNight({ beat, onComplete, acting }: { beat: AwardsBeat; onComplete: () => void; acting?: boolean }) {
    const allAwards = beat.payload.awards;

    if (allAwards.length === 0) {
        return (
            <CeremonyShell
                beatIndex={beat.beat_index}
                totalBeats={beat.total_beats}
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

    // MVP is pinned first (prestige sort done on backend), others follow
    const mvp = allAwards.find((a: OffseasonAward) => a.award_type === 'mvp');
    const supportingAwards = allAwards.filter((a: OffseasonAward) => a.award_type !== 'mvp');
    const orderedAwards: OffseasonAward[] = mvp ? [mvp, ...supportingAwards] : allAwards;

    return (
        <CeremonyShell
                beatIndex={beat.beat_index}
                totalBeats={beat.total_beats}
            title={beat.title}
            eyebrow="Awards Night"
            description="The league gathers to honor the season's best."
            stages={orderedAwards.length}
            renderStage={(stage) => (
                <div style={{ width: '100%', maxWidth: '640px', margin: '0 auto' }}>
                    {/* MVP Hero Card — revealed at stage 1 */}
                    {stage >= 1 && orderedAwards[0] && (() => {
                        const award = orderedAwards[0];
                        const color = AWARD_COLOR[award.award_type] ?? '#f97316';
                        const icon = AWARD_ICON[award.award_type] ?? '🏅';
                        return (
                            <div
                                className="fade-in"
                                style={{
                                    border: `1px solid ${color}`,
                                    borderRadius: '12px',
                                    padding: '1.5rem',
                                    background: 'linear-gradient(135deg, #1c0900 0%, #0f172a 60%)',
                                    boxShadow: `0 0 40px ${color}33`,
                                    position: 'relative',
                                    marginBottom: '0.75rem',
                                }}
                            >
                                {/* Award badge - top right */}
                                <div style={{
                                    position: 'absolute',
                                    top: '1rem',
                                    right: '1rem',
                                    background: color,
                                    color: '#fff',
                                    padding: '0.2rem 0.6rem',
                                    borderRadius: '999px',
                                    fontSize: '0.65rem',
                                    fontWeight: 800,
                                    letterSpacing: '0.1em',
                                }}>
                                    {icon} {award.award_name.toUpperCase()}
                                </div>

                                {/* Player name — headline */}
                                <div style={{
                                    fontFamily: 'var(--font-display)',
                                    fontSize: '2.1rem',
                                    fontWeight: 700,
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.03em',
                                    color: '#fbbf24',
                                    lineHeight: 1.05,
                                    marginBottom: '0.2rem',
                                    paddingRight: '8rem',
                                }}>
                                    {award.player_name}
                                </div>
                                <div style={{ fontSize: '0.8rem', color: '#94a3b8', marginBottom: '1.25rem' }}>
                                    {award.club_name}
                                </div>

                                {/* Stats chips */}
                                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                    {award.extra_stats ? (
                                        <>
                                            <div style={{ background: '#1e293b', borderRadius: '6px', padding: '0.4rem 0.75rem', textAlign: 'center' }}>
                                                <div style={{ fontSize: '1.1rem', fontWeight: 800, color: color }}>{award.extra_stats.throw_elims}</div>
                                                <div style={{ fontSize: '0.6rem', color: '#475569', letterSpacing: '0.06em' }}>THROW ELIMS</div>
                                            </div>
                                            <div style={{ background: '#1e293b', borderRadius: '6px', padding: '0.4rem 0.75rem', textAlign: 'center' }}>
                                                <div style={{ fontSize: '1.1rem', fontWeight: 800, color: color }}>{award.extra_stats.catches}</div>
                                                <div style={{ fontSize: '0.6rem', color: '#475569', letterSpacing: '0.06em' }}>CATCHES</div>
                                            </div>
                                            <div style={{ background: '#1e293b', borderRadius: '6px', padding: '0.4rem 0.75rem', textAlign: 'center' }}>
                                                <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#ef4444' }}>{award.extra_stats.times_eliminated}</div>
                                                <div style={{ fontSize: '0.6rem', color: '#475569', letterSpacing: '0.06em' }}>TIMES OUT</div>
                                            </div>
                                        </>
                                    ) : (
                                        <div style={{ background: '#1e293b', borderRadius: '6px', padding: '0.4rem 0.75rem', textAlign: 'center' }}>
                                            <div style={{ fontSize: '1.1rem', fontWeight: 800, color: color }}>{award.season_stat}</div>
                                            <div style={{ fontSize: '0.6rem', color: '#475569', letterSpacing: '0.06em' }}>SEASON ELIMS</div>
                                        </div>
                                    )}
                                    <div style={{ background: '#1e293b', borderRadius: '6px', padding: '0.4rem 0.75rem', textAlign: 'center' }}>
                                        <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#94a3b8' }}>{award.ovr}</div>
                                        <div style={{ fontSize: '0.6rem', color: '#475569', letterSpacing: '0.06em' }}>OVR</div>
                                    </div>
                                    <div style={{ background: '#1e293b', borderRadius: '6px', padding: '0.4rem 0.75rem', textAlign: 'center' }}>
                                        <div style={{ fontSize: '1.1rem', fontWeight: 800, color: '#64748b' }}>{award.career_stat}</div>
                                        <div style={{ fontSize: '0.6rem', color: '#475569', letterSpacing: '0.06em' }}>CAREER ELIMS</div>
                                    </div>
                                </div>
                            </div>
                        );
                    })()}

                    {/* Supporting awards — grid, revealed one per stage */}
                    {stage >= 2 && orderedAwards.length > 1 && (
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: `repeat(${Math.min(supportingAwards.length, 3)}, 1fr)`,
                            gap: '0.5rem',
                        }}>
                            {orderedAwards.slice(1, stage).map((award: OffseasonAward, i: number) => {
                                const color = AWARD_COLOR[award.award_type] ?? '#64748b';
                                const icon = AWARD_ICON[award.award_type] ?? '🏅';
                                return (
                                    <div
                                        key={i}
                                        className="fade-in"
                                        style={{
                                            border: `1px solid ${color}55`,
                                            borderRadius: '8px',
                                            padding: '0.75rem',
                                            background: '#0f172a',
                                        }}
                                    >
                                        <div style={{ fontSize: '1.25rem', marginBottom: '0.3rem' }}>{icon}</div>
                                        <div style={{ fontSize: '0.6rem', color, fontWeight: 700, letterSpacing: '0.08em', marginBottom: '0.2rem' }}>
                                            {award.award_name.toUpperCase()}
                                        </div>
                                        <div style={{ fontSize: '0.9rem', fontWeight: 700, color: '#e2e8f0', marginBottom: '0.1rem' }}>
                                            {award.player_name}
                                        </div>
                                        <div style={{ fontSize: '0.7rem', color: '#64748b', marginBottom: '0.3rem' }}>
                                            {award.club_name}
                                        </div>
                                        <div style={{ fontSize: '0.7rem', color: color, fontWeight: 600 }}>
                                            {award.season_stat_label}
                                        </div>
                                    </div>
                                );
                            })}
                        </div>
                    )}
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
                beatIndex={beat.beat_index}
                totalBeats={beat.total_beats}
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
                beatIndex={beat.beat_index}
                totalBeats={beat.total_beats}
      title={beat.title}
      eyebrow="Graduation"
      description="Saying goodbye to departing veterans."
      stages={retirees.length}
      renderStage={(stage) => (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%', maxWidth: '560px', margin: '0 auto' }}>
          {retirees.slice(0, stage).map((r: OffseasonRetiree, i: number) => {
            const isLatest = i === stage - 1;
            const tierColor = TIER_COLOR[r.potential_tier] ?? '#475569';
            return (
              <div
                key={i}
                className={`fade-in farewell-card${isLatest ? ' is-latest' : ''}`}
                style={{ opacity: isLatest ? 1 : 0.6 }}
              >
                <div className="farewell-name">{r.name}</div>
                <div className="farewell-line">
                  {r.ovr_final ? <span>{Math.round(r.ovr_final)} OVR final</span> : null}
                  <span>{r.career_elims} career elims</span>
                  <span>{r.championships} {r.championships === 1 ? 'title' : 'titles'}</span>
                  <span>{r.seasons_played} seasons</span>
                </div>
                <div className="farewell-tier" style={{ color: tierColor }}>
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


type SigningFilter = 'my' | 'rival' | 'surprise';
type SigningKind = SigningCard['outcome_kind'];

// Plain-English tab labels (no internal enum vocabulary). Brief 4.1 §5.3.
const FILTER_LABELS: Record<SigningFilter, string> = {
  my: 'Your Picks',
  rival: 'Rival Picks',
  surprise: 'Surprises',
};

const FILTER_EMPTY: Record<SigningFilter, string> = {
  my: "You didn't sign anyone this class.",
  rival: 'No rival signings on the board.',
  surprise: 'No surprises this signing day.',
};

const FILTER_TO_KIND: Record<SigningFilter, SigningKind> = {
  my: 'my_signing',
  rival: 'rival_signing',
  surprise: 'surprise',
};

// Per-kind visual treatment: your picks = cyan/primary, rivals = orange/competitive,
// surprises = violet/distinct-but-lower-urgency. Brief 4.1 design vision.
const KIND_META: Record<SigningKind, { accent: string; bg: string; badge: string }> = {
  my_signing: { accent: '#22d3ee', bg: '#083344', badge: 'My Signing' },
  rival_signing: { accent: '#f97316', bg: '#1f1305', badge: 'Rival Signing' },
  surprise: { accent: '#8b5cf6', bg: '#1e1b3a', badge: 'Surprise' },
};

function countSigningsByKind(signings: SigningCard[]): Record<SigningFilter, number> {
  return {
    my: signings.filter((c) => c.outcome_kind === 'my_signing').length,
    rival: signings.filter((c) => c.outcome_kind === 'rival_signing').length,
    surprise: signings.filter((c) => c.outcome_kind === 'surprise').length,
  };
}

function filterSignings(signings: SigningCard[], filter: SigningFilter): SigningCard[] {
  return signings
    .filter((c) => c.outcome_kind === FILTER_TO_KIND[filter])
    .sort((a, b) => b.ovr - a.ovr);
}

// Top OVR over a list, guarding the empty case (Math.max() === -Infinity).
function topOvr(cards: { ovr: number }[]): number | null {
  return cards.length ? cards.reduce((max, c) => (c.ovr > max ? c.ovr : max), cards[0].ovr) : null;
}

function topCard<T extends { ovr: number }>(cards: T[]): T | null {
  return cards.length ? cards.reduce((best, c) => (c.ovr > best.ovr ? c : best), cards[0]) : null;
}

function MetricTile({ label, value, accent = '#e2e8f0' }: { label: string; value: React.ReactNode; accent?: string }) {
  return (
    <div
      style={{
        flex: '1 1 120px',
        minWidth: 0,
        border: '1px solid #1e293b',
        borderRadius: '8px',
        background: '#0f172a',
        padding: '0.6rem 0.75rem',
      }}
    >
      <div style={{ fontSize: '1.4rem', fontWeight: 900, color: accent, lineHeight: 1.1 }}>{value}</div>
      <div style={{ fontSize: '0.6rem', letterSpacing: '0.08em', textTransform: 'uppercase', color: '#64748b', marginTop: '0.2rem' }}>
        {label}
      </div>
    </div>
  );
}

function GlanceRow({ label, value, accent = '#cbd5e1' }: { label: string; value: React.ReactNode; accent?: string }) {
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'space-between',
        gap: '0.75rem',
        padding: '0.5rem 0',
        borderTop: '1px solid #1e293b',
        minWidth: 0,
      }}
    >
      <span style={{ fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.06em', color: '#64748b', minWidth: 0 }}>
        {label}
      </span>
      <span style={{ fontSize: '0.8rem', fontWeight: 700, color: accent, textAlign: 'right', minWidth: 0 }}>{value}</span>
    </div>
  );
}

function GlancePanel({ children }: { children: React.ReactNode }) {
  return (
    <section
      aria-labelledby="class-glance-heading"
      style={{
        flex: '1 1 240px',
        minWidth: 0,
        border: '1px solid #1e293b',
        borderRadius: '10px',
        background: 'linear-gradient(160deg, #0b1f2b 0%, #0f172a 70%)',
        padding: '1.1rem 1.15rem',
      }}
    >
      <h3
        id="class-glance-heading"
        style={{ fontSize: '0.65rem', color: '#22d3ee', fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', margin: 0 }}
      >
        Your Class at a Glance
      </h3>
      {children}
    </section>
  );
}

function SigningCardView({ card }: { card: SigningCard }) {
  const { accent, bg, badge } = KIND_META[card.outcome_kind];
  return (
    <div
      className="fade-in"
      style={{
        border: `2px solid ${accent}`,
        borderRadius: '8px',
        padding: '1rem 1.1rem',
        background: bg,
        boxShadow: `0 0 18px ${accent}1f`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.75rem' }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ fontSize: '1.05rem', fontWeight: 800, color: '#e2e8f0' }}>{card.name}</div>
          <div style={{ fontSize: '0.75rem', color: '#94a3b8', marginTop: '0.15rem' }}>
            <span style={{ color: '#cbd5e1', fontWeight: 600 }}>{card.club_name}</span>
            {card.role ? <span> &middot; {card.role}</span> : null}
          </div>
        </div>
        <div
          style={{
            fontSize: '0.75rem',
            fontWeight: 900,
            color: accent,
            border: `1px solid ${accent}`,
            borderRadius: '6px',
            padding: '0.25rem 0.55rem',
            letterSpacing: '0.04em',
            whiteSpace: 'nowrap',
          }}
        >
          OVR {card.ovr}
        </div>
      </div>
      <div style={{ marginTop: '0.5rem' }}>
        <span
          style={{
            fontSize: '0.55rem',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            fontWeight: 700,
            color: accent,
            border: `1px solid ${accent}66`,
            background: `${accent}14`,
            borderRadius: '999px',
            padding: '0.15rem 0.5rem',
          }}
        >
          {badge}
        </span>
      </div>
      <div style={{ fontSize: '0.8rem', color: '#cbd5e1', marginTop: '0.55rem', lineHeight: 1.4 }}>
        {card.reason}
      </div>
    </div>
  );
}

// Legacy fallback (older saves without the `signings` card array): rebuild the same
// primary/secondary hierarchy from player_signing + other_signings, not a text blob.
function LegacyClassReport({
  playerSigning,
  otherSignings,
  signedCount,
  signingLimit,
  body,
}: {
  playerSigning: OffseasonSigning | null;
  otherSignings: OffseasonSigning[];
  signedCount: number;
  signingLimit: number;
  body: unknown;
}) {
  const otherCount = otherSignings.length;
  // Your contribution to the class is signedCount (the authoritative count), not
  // a hardcoded 1-if-any — otherwise "Total Rookies" undercounts a 2+ signing
  // class and disagrees with "You signed N". (BUG #5)
  const totalClass = signedCount + otherCount;
  const prose = typeof body === 'string' && body.trim() ? body.trim() : '';
  // Right column shows the structured league list when we have one; otherwise it
  // surfaces the engine's prose as a readable brief (never crammed into the glance).
  const showBrief = otherCount === 0 && prose.length > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%', maxWidth: '1040px', margin: '0 auto' }}>
      <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
        <MetricTile label="Your Signings" value={`${signedCount}/${signingLimit}`} accent="#22d3ee" />
        <MetricTile label="Others Joined" value={otherCount} accent="#f97316" />
        <MetricTile label="Total Rookies" value={totalClass} />
      </div>

      <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'stretch' }}>
        <GlancePanel>
          <div style={{ fontSize: '1.7rem', fontWeight: 900, color: '#e2e8f0', marginTop: '0.6rem', lineHeight: 1.1 }}>
            {/* BUG #5 / ADR 0002: the headline count was hardcoded to "1"
                whenever any signing existed, so it read "You signed 1." while
                the tile beside it read "2/3 used" — the exact contradiction the
                playtest hit. Drive it from signedCount (the authoritative
                roster-delta counter) so every "how many you signed" number on
                this card agrees. */}
            {signedCount > 0 ? `You signed ${signedCount}.` : "You didn't sign anyone."}
          </div>
          <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '0.3rem', lineHeight: 1.4 }}>
            {signedCount > 0
              ? `${otherCount} other${otherCount !== 1 ? 's' : ''} joined the league.`
              : otherCount > 0
                ? `${otherCount} rookie${otherCount !== 1 ? 's' : ''} joined the league.`
                : 'No prospects committed to your program this offseason.'}
          </div>
          <div style={{ fontSize: '0.7rem', color: '#22d3ee', fontWeight: 700, marginTop: '0.6rem' }}>
            {signedCount}/{signingLimit} slots used
          </div>
          {playerSigning && (
            <div style={{ marginTop: '0.85rem' }}>
              <GlanceRow
                // Only the last signee is carried in player_signing, so when you
                // signed more than one this is the "latest", not the sole pick —
                // label it honestly rather than implying it was your only signing.
                label={signedCount > 1 ? 'Latest signing' : 'Your signing'}
                value={`${playerSigning.name} · OVR ${playerSigning.ovr}`}
                accent="#22d3ee"
              />
              {playerSigning.role ? <GlanceRow label="Role" value={playerSigning.role} /> : null}
              {playerSigning.age ? <GlanceRow label="Age" value={playerSigning.age} /> : null}
            </div>
          )}
        </GlancePanel>

        <div style={{ flex: '2 1 360px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          <div style={{ fontSize: '0.65rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 700 }}>
            {showBrief ? 'Class Brief' : 'Around the League'}
          </div>
          {showBrief ? (
            <div
              style={{
                flex: 1,
                border: '1px solid #1e293b',
                borderLeft: '3px solid #22d3ee',
                borderRadius: '8px',
                padding: '1.1rem 1.25rem',
                background: '#0f172a',
                color: '#cbd5e1',
                fontSize: '0.9rem',
                lineHeight: 1.65,
                minWidth: 0,
              }}
            >
              <BriefProse text={prose} />
            </div>
          ) : otherCount === 0 ? (
            <div
              style={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                border: '1px dashed #334155',
                borderRadius: '8px',
                padding: '1.5rem',
                color: '#64748b',
                textAlign: 'center',
                fontSize: '0.85rem',
              }}
            >
              No other signings to report.
            </div>
          ) : (
            <ul role="list" style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              {otherSignings.map((s: OffseasonSigning, i: number) => (
                <li
                  key={i}
                  className="fade-in"
                  style={{
                    border: '1px solid #334155',
                    borderRadius: '6px',
                    padding: '0.6rem 0.85rem',
                    background: '#0f172a',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    gap: '0.75rem',
                  }}
                >
                  <span style={{ minWidth: 0 }}>
                    <span style={{ color: '#e2e8f0', fontWeight: 600 }}>{s.name}</span>
                    {s.club_name ? (
                      <span style={{ color: '#64748b', fontSize: '0.75rem', marginLeft: '0.5rem' }}>to {s.club_name}</span>
                    ) : null}
                  </span>
                  <span style={{ color: '#94a3b8', fontSize: '0.75rem', whiteSpace: 'nowrap' }}>OVR {s.ovr}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

export function SigningDay({ beat, onComplete, acting }: { beat: RecruitmentBeat; onComplete: () => void; acting?: boolean }) {
  const playerSigning = beat.payload.player_signing;
  const otherSignings = beat.payload.other_signings ?? [];
  const signedCount = beat.payload.signed_count ?? 0;
  const signingLimit = beat.payload.signing_limit ?? 3;
  const signings: SigningCard[] = beat.payload.signings ?? [];

  const [filter, setFilter] = useState<SigningFilter>('my');

  const hasCards = signings.length > 0;
  const counts = countSigningsByKind(signings);
  const visible = filterSignings(signings, filter);

  // BUG #5 / ADR 0002 — single source of truth for "how many YOU signed".
  // signed_count is the authoritative roster-delta counter the backend keeps
  // (it equals the players actually added this offseason). Since V16, contested
  // prospect picks DO write recruitment_signing rows (cards), but free-agent
  // signings still don't — so counts.my can legitimately undercount. Every
  // player-facing NUMBER meaning "how many you signed" therefore reads
  // signedCount: the hero tile, the headline, the slots-used line, AND the
  // "Your Picks" tab badge. The card LIST stays honest — we never fabricate
  // cards to match the number.
  const myCount = signedCount;
  const tabCounts = { ...counts, my: signedCount };

  // League + own-class derivations (all from existing payload arrays).
  const classSize = signings.length;
  const rivalCount = counts.rival;
  // Rookies who joined the league besides your signings. Clamp at 0 so a class
  // with no recorded cards can't render a negative count against signedCount.
  const othersJoined = Math.max(0, classSize - counts.my);
  const mySignings = signings.filter((c) => c.outcome_kind === 'my_signing');
  const topMine = topCard(mySignings);
  const topClass = topCard(signings);
  const classTopOvr = topOvr(signings);
  const scoutedCount = signings.filter((c) => c.user_interaction.scouted).length;
  const deepCount = signings.filter((c) => c.ovr >= 68).length;

  return (
    <CeremonyShell
                beatIndex={beat.beat_index}
                totalBeats={beat.total_beats}
      title="Class Report"
      eyebrow="Signing Day Update"
      description="Here's how the rookie class shook out."
      stages={0}
      renderStage={() =>
        hasCards ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', width: '100%', maxWidth: '1040px', margin: '0 auto' }}>
            {/* Hero metric strip — league + own-class summary visible without switching tabs */}
            <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
              <MetricTile label="Your Signings" value={`${signedCount}/${signingLimit}`} accent="#22d3ee" />
              <MetricTile label="Rival Signings" value={rivalCount} accent="#f97316" />
              <MetricTile label="Total Rookies" value={classSize} />
              {classTopOvr != null && <MetricTile label="Top OVR in Class" value={classTopOvr} accent="#8b5cf6" />}
            </div>

            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-start' }}>
              {/* Primary: the player's own outcome */}
              <GlancePanel>
                <div style={{ fontSize: '1.7rem', fontWeight: 900, color: '#e2e8f0', marginTop: '0.6rem', lineHeight: 1.1 }}>
                  {myCount > 0 ? `You signed ${myCount}.` : "You didn't sign anyone."}
                </div>
                <div style={{ fontSize: '0.85rem', color: '#94a3b8', marginTop: '0.25rem' }}>
                  {othersJoined} other{othersJoined !== 1 ? 's' : ''} joined the league.
                </div>
                <div style={{ fontSize: '0.7rem', color: '#22d3ee', fontWeight: 700, marginTop: '0.5rem' }}>
                  {signedCount}/{signingLimit} slots used
                </div>

                <div style={{ marginTop: '0.75rem' }}>
                  {topMine ? (
                    <GlanceRow label="Top signing" value={`${topMine.name} · OVR ${topMine.ovr}`} accent="#22d3ee" />
                  ) : playerSigning ? (
                    // No per-pick card on file (the offseason signing flow records
                    // a roster add + the latest signee, not a recruitment_signing
                    // row), so surface the last signee the backend DID persist
                    // rather than a phantom card. Keeps the panel consistent with
                    // signedCount instead of inventing a list. (BUG #5)
                    <GlanceRow label="Latest signing" value={`${playerSigning.name} · OVR ${playerSigning.ovr}`} accent="#22d3ee" />
                  ) : topClass ? (
                    <GlanceRow label="Top OVR in class" value={`${topClass.name} (${topClass.ovr})`} />
                  ) : null}
                  {deepCount > 0 && <GlanceRow label="Deep class" value={`${deepCount} rated 68+ OVR`} />}
                  {scoutedCount > 0 && (
                    <GlanceRow label="You scouted" value={`${scoutedCount} prospect${scoutedCount !== 1 ? 's' : ''}`} />
                  )}
                </div>
              </GlancePanel>

              {/* Secondary: tab-filtered signing cards */}
              <div style={{ flex: '2 1 320px', minWidth: 0, display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <div role="tablist" aria-label="Filter signings" style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                  {(['my', 'rival', 'surprise'] as SigningFilter[]).map((f) => {
                    const active = filter === f;
                    return (
                      <button
                        key={f}
                        role="tab"
                        aria-selected={active}
                        onClick={() => setFilter(f)}
                        style={{
                          background: active ? '#22d3ee' : 'transparent',
                          color: active ? '#0f172a' : '#94a3b8',
                          border: `1px solid ${active ? '#22d3ee' : '#334155'}`,
                          borderRadius: '999px',
                          padding: '0.3rem 0.75rem',
                          fontSize: '0.75rem',
                          fontWeight: 700,
                          letterSpacing: '0.04em',
                          cursor: 'pointer',
                        }}
                      >
                        {FILTER_LABELS[f]} <span style={{ opacity: 0.7 }}>({tabCounts[f]})</span>
                      </button>
                    );
                  })}
                </div>

                <div style={{ fontSize: '0.7rem', color: '#64748b' }}>
                  {FILTER_LABELS[filter]} &middot; sorted by OVR
                </div>

                {visible.length === 0 ? (
                  <div
                    style={{
                      border: '1px dashed #334155',
                      borderRadius: '8px',
                      padding: '1.5rem',
                      color: '#64748b',
                      textAlign: 'center',
                      fontSize: '0.85rem',
                    }}
                  >
                    {/* BUG #5: when you signed players this offseason but no
                        per-pick card was recorded (free-agent signings don't
                        write contested-round cards), don't claim "you didn't
                        sign anyone" — name the real count instead. */}
                    {filter === 'my' && signedCount > 0
                      ? `You signed ${signedCount} this offseason${playerSigning ? ` (latest: ${playerSigning.name}).` : '.'} Free-agent signings don't get contested-round cards.`
                      : FILTER_EMPTY[filter]}
                  </div>
                ) : (
                  <ul role="list" style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
                    {visible.map((card) => (
                      <li key={card.player_id}>
                        <SigningCardView card={card} />
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </div>
        ) : (
          <LegacyClassReport
            playerSigning={playerSigning}
            otherSignings={otherSignings}
            signedCount={signedCount}
            signingLimit={signingLimit}
            body={beat.body}
          />
        )
      }
      onComplete={onComplete}
      actionDescription="Class Report complete — continue the offseason sequence."
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
                beatIndex={beat.beat_index}
                totalBeats={beat.total_beats}
            title={beat.title}
            eyebrow={seasonLabel ? `Season ${seasonLabel} · Schedule Reveal` : 'New Season'}
            description="A new chapter begins."
            stages={2}
            renderStage={(stage) => (
                <div style={{ width: '100%', maxWidth: '640px', margin: '0 auto' }}>
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
                                                {f.home && f.away ? `${f.home} vs ${f.away}` : 'Bye Week'}
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
