import { useState } from 'react';
import { CeremonyShell } from './CeremonyShell';
import { Truncate } from '../../ui';
import type {
  OffseasonAward,
  OffseasonBeat,
  OffseasonFixture,
  OffseasonRetiree,
  OffseasonSigning,
  SigningCard,
} from '../../types';
import styles from './Ceremonies.module.css';
import cer from './ceremony.module.css';

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

// Award-type accent → module-class keys (token-driven; no inline hex).
const AWARD_ACCENT: Record<string, string> = {
  mvp: 'Mvp',
  best_thrower: 'Thrower',
  best_catcher: 'Catcher',
  best_newcomer: 'Newcomer',
};
function awardAccent(type: string): string {
  return AWARD_ACCENT[type] ?? 'Default';
}

// Potential-tier → farewell-card text class.
const TIER_CLASS: Record<string, string> = {
  Elite: styles.tierElite,
  High: styles.tierHigh,
  Solid: styles.tierSolid,
  Limited: styles.tierLimited,
  Unknown: styles.tierUnknown,
};

// The ceremony engine emits multi-line briefs ("Current roster sizes:" plus
// indented club rows, "Label: value" facts, blank-line section breaks). A bare
// {prose} render collapses all of it onto one run-on line — this keeps the
// backend's structure: section labels, indented rows, and fact rows stay rows.
function BriefProse({ text }: { text: string }) {
  const lines = text.split('\n');
  return (
    <div className={styles.brief}>
      {lines.map((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <div key={index} aria-hidden="true" className={styles.briefGap} />;
        }
        const indented = line.startsWith('  ') || trimmed.startsWith('- ');
        const content = trimmed.startsWith('- ') ? trimmed.slice(2) : trimmed;
        if (!indented && trimmed.endsWith(':')) {
          return (
            <p key={index} className={styles.briefSection}>
              {trimmed.slice(0, -1)}
            </p>
          );
        }
        const kv = /^([^:]{2,42}):\s+(.+)$/.exec(content);
        if (kv) {
          return (
            <p key={index} className={`${styles.briefLine} ${indented ? styles.briefIndent : ''}`}>
              <span className={styles.briefKey}>{kv[1]}</span>
              <span className={styles.briefSep}>{' · '}</span>
              <span className={styles.briefVal}>{kv[2]}</span>
            </p>
          );
        }
        return (
          <p key={index} className={`${styles.briefLine} ${indented ? styles.briefIndent : ''}`}>
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
                    <div className={styles.emptyCenter}>
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
                <div className={styles.awardsWrap}>
                    {/* MVP Hero Card — revealed at stage 1 */}
                    {stage >= 1 && orderedAwards[0] && (() => {
                        const award = orderedAwards[0];
                        const accent = awardAccent(award.award_type);
                        const icon = AWARD_ICON[award.award_type] ?? '🏅';
                        return (
                            <div className={`fade-in ${styles.mvpCard} ${styles[`accent${accent}`]}`}>
                                {/* Award badge - top right */}
                                <div className={`${styles.mvpBadge} ${styles[`badgeBg${accent}`]}`}>
                                    {icon} {award.award_name.toUpperCase()}
                                </div>

                                {/* Player name — headline */}
                                <Truncate className={styles.mvpName}>
                                    {award.player_name}
                                </Truncate>
                                <div className={styles.mvpClub}>
                                    {award.club_name}
                                </div>

                                {/* Stats chips */}
                                <div className={styles.chips}>
                                    {award.extra_stats ? (
                                        <>
                                            <div className={styles.chip}>
                                                <div className={`${styles.chipNum} ${styles[`chipNumAccent${accent}`]}`}>{award.extra_stats.throw_elims}</div>
                                                <div className={styles.chipLabel}>THROW ELIMS</div>
                                            </div>
                                            <div className={styles.chip}>
                                                <div className={`${styles.chipNum} ${styles[`chipNumAccent${accent}`]}`}>{award.extra_stats.catches}</div>
                                                <div className={styles.chipLabel}>CATCHES</div>
                                            </div>
                                            <div className={styles.chip}>
                                                <div className={`${styles.chipNum} ${styles.chipNumDanger}`}>{award.extra_stats.times_eliminated}</div>
                                                <div className={styles.chipLabel}>TIMES OUT</div>
                                            </div>
                                        </>
                                    ) : (
                                        <div className={styles.chip}>
                                            <div className={`${styles.chipNum} ${styles[`chipNumAccent${accent}`]}`}>{award.season_stat}</div>
                                            <div className={styles.chipLabel}>SEASON ELIMS</div>
                                        </div>
                                    )}
                                    <div className={styles.chip}>
                                        <div className={`${styles.chipNum} ${styles.chipNumNeutral}`}>{award.ovr}</div>
                                        <div className={styles.chipLabel}>OVR</div>
                                    </div>
                                    <div className={styles.chip}>
                                        <div className={`${styles.chipNum} ${styles.chipNumMuted}`}>{award.career_stat}</div>
                                        <div className={styles.chipLabel}>CAREER ELIMS</div>
                                    </div>
                                </div>
                            </div>
                        );
                    })()}

                    {/* Supporting awards — grid, revealed one per stage */}
                    {stage >= 2 && orderedAwards.length > 1 && (
                        <div
                            className={styles.supportGrid}
                            style={{ gridTemplateColumns: `repeat(${Math.min(supportingAwards.length, 3)}, minmax(0, 1fr))` }}
                        >
                            {orderedAwards.slice(1, stage).map((award: OffseasonAward, i: number) => {
                                const accent = awardAccent(award.award_type);
                                const icon = AWARD_ICON[award.award_type] ?? '🏅';
                                return (
                                    <div key={i} className={`fade-in ${styles.supportCard} ${styles[`supportCard${accent}`]}`}>
                                        <div className={styles.supportIcon}>{icon}</div>
                                        <div className={`${styles.supportName2} ${styles[`accentText${accent}`]}`}>
                                            {award.award_name.toUpperCase()}
                                        </div>
                                        <div className={styles.supportPlayer}>
                                            {award.player_name}
                                        </div>
                                        <div className={styles.supportClub}>
                                            {award.club_name}
                                        </div>
                                        <div className={`${styles.supportStat} ${styles[`accentText${accent}`]}`}>
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
          <div className={styles.emptyCenter}>
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
        <div className={styles.farewellList}>
          {retirees.slice(0, stage).map((r: OffseasonRetiree, i: number) => {
            const isLatest = i === stage - 1;
            const tierClass = TIER_CLASS[r.potential_tier] ?? styles.tierUnknown;
            return (
              <div
                key={i}
                className={`fade-in ${cer['farewell-card']}${isLatest ? ` ${cer['is-latest']}` : ''}`}
                style={{ opacity: isLatest ? 1 : 0.6 }}
              >
                <div className={cer['farewell-name']}>{r.name}</div>
                <div className={cer['farewell-line']}>
                  {r.ovr_final ? <span>{Math.round(r.ovr_final)} OVR final</span> : null}
                  <span>{r.career_elims} career elims</span>
                  <span>{r.championships} {r.championships === 1 ? 'title' : 'titles'}</span>
                  {/* Playtest 3 F-10: career length includes pre-league seasons
                      seeded for curated veterans — "3 seasons" on a 33-year-old
                      farewell card read as a mislabel. */}
                  <span>{r.career_seasons ?? r.seasons_played} seasons</span>
                </div>
                <div className={`${cer['farewell-tier']} ${tierClass}`}>
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
const KIND_BADGE: Record<SigningKind, string> = {
  my_signing: 'My Signing',
  rival_signing: 'Rival Signing',
  surprise: 'Surprise',
};
// Per-kind module-class suffix (token-driven; no inline hex).
const KIND_SUFFIX: Record<SigningKind, string> = {
  my_signing: 'Mine',
  rival_signing: 'Rival',
  surprise: 'Surprise',
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

function MetricTile({ label, value, accentClass = styles.accentNeutral }: { label: string; value: React.ReactNode; accentClass?: string }) {
  return (
    <div className={styles.metricTile}>
      <div className={`${styles.metricValue} ${accentClass}`}>{value}</div>
      <div className={styles.metricLabel}>
        {label}
      </div>
    </div>
  );
}

function GlanceRow({ label, value, accentClass }: { label: string; value: React.ReactNode; accentClass?: string }) {
  return (
    <div className={styles.glanceRow}>
      <span className={styles.glanceRowLabel}>
        {label}
      </span>
      <span className={`${styles.glanceRowValue} ${accentClass ?? ''}`}>{value}</span>
    </div>
  );
}

function GlancePanel({ children }: { children: React.ReactNode }) {
  return (
    <section aria-labelledby="class-glance-heading" className={styles.glancePanel}>
      <h3 id="class-glance-heading" className={styles.glanceHeading}>
        Your Class at a Glance
      </h3>
      {children}
    </section>
  );
}

function SigningCardView({ card }: { card: SigningCard }) {
  const suffix = KIND_SUFFIX[card.outcome_kind];
  const badge = KIND_BADGE[card.outcome_kind];
  return (
    <div className={`fade-in ${styles.signingCard} ${styles[`kind${suffix}`]}`}>
      <div className={styles.signingTop}>
        <div style={{ minWidth: 0 }}>
          <div className={styles.signingName}>{card.name}</div>
          <div className={styles.signingClubLine}>
            <span className={styles.signingClub}>{card.club_name}</span>
            {card.role ? <span> &middot; {card.role}</span> : null}
          </div>
        </div>
        <div className={`${styles.ovrPill} ${styles[`ovrPill${suffix}`]}`}>
          OVR {card.ovr}
        </div>
      </div>
      <div className={styles.kindBadgeWrap}>
        <span className={`${styles.kindBadge} ${styles[`kindBadge${suffix}`]}`}>
          {badge}
        </span>
      </div>
      <div className={styles.signingReason}>
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
    <div className={styles.report}>
      <div className={styles.metricRow}>
        <MetricTile label="Your Signings" value={`${signedCount}/${signingLimit}`} accentClass={styles.accentVolt} />
        <MetricTile label="Others Joined" value={otherCount} accentClass={styles.accentGold} />
        <MetricTile label="Total Rookies" value={totalClass} />
      </div>

      <div className={styles.columnsStretch}>
        <GlancePanel>
          <div className={styles.glanceHeadline}>
            {/* BUG #5 / ADR 0002: the headline count was hardcoded to "1"
                whenever any signing existed, so it read "You signed 1." while
                the tile beside it read "2/3 used" — the exact contradiction the
                playtest hit. Drive it from signedCount (the authoritative
                roster-delta counter) so every "how many you signed" number on
                this card agrees. */}
            {signedCount > 0 ? `You signed ${signedCount}.` : "You didn't sign anyone."}
          </div>
          <div className={styles.glanceSub}>
            {signedCount > 0
              ? `${otherCount} other${otherCount !== 1 ? 's' : ''} joined the league.`
              : otherCount > 0
                ? `${otherCount} rookie${otherCount !== 1 ? 's' : ''} joined the league.`
                : 'No prospects committed to your program this offseason.'}
          </div>
          <div className={styles.glanceSlots}>
            {signedCount}/{signingLimit} slots used
          </div>
          {playerSigning && (
            <div className={styles.glanceRows}>
              <GlanceRow
                // Only the last signee is carried in player_signing, so when you
                // signed more than one this is the "latest", not the sole pick —
                // label it honestly rather than implying it was your only signing.
                label={signedCount > 1 ? 'Latest signing' : 'Your signing'}
                value={`${playerSigning.name} · OVR ${playerSigning.ovr}`}
                accentClass={styles.glanceRowValueVolt}
              />
              {playerSigning.role ? <GlanceRow label="Role" value={playerSigning.role} /> : null}
              {playerSigning.age ? <GlanceRow label="Age" value={playerSigning.age} /> : null}
            </div>
          )}
        </GlancePanel>

        <div className={styles.briefCol}>
          <div className={styles.briefLabel}>
            {showBrief ? 'Class Brief' : 'Around the League'}
          </div>
          {showBrief ? (
            <div className={styles.briefBox}>
              <BriefProse text={prose} />
            </div>
          ) : otherCount === 0 ? (
            <div className={styles.briefEmpty}>
              No other signings to report.
            </div>
          ) : (
            <ul role="list" className={styles.otherList}>
              {otherSignings.map((s: OffseasonSigning, i: number) => (
                <li key={i} className={`fade-in ${styles.otherRow}`}>
                  <span style={{ minWidth: 0 }}>
                    <span className={styles.otherName}>{s.name}</span>
                    {s.club_name ? (
                      <span className={styles.otherClub}>to {s.club_name}</span>
                    ) : null}
                  </span>
                  <span className={styles.otherOvr}>OVR {s.ovr}</span>
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
          <div className={styles.report}>
            {/* Hero metric strip — league + own-class summary visible without switching tabs */}
            {/* PT5: tile 1 is player-scoped (your slots); tiles 2-3 are LEAGUE-wide
                (every club's signings / the whole rookie class) — label them so the
                big numbers can't be misread as your own program beside the body's
                "You signed N". */}
            <div className={styles.metricRow}>
              <MetricTile label="Your Signings" value={`${signedCount}/${signingLimit}`} accentClass={styles.accentVolt} />
              <MetricTile label="Rival Signings (League)" value={rivalCount} accentClass={styles.accentGold} />
              <MetricTile label="Rookies (League)" value={classSize} />
              {classTopOvr != null && <MetricTile label="Top OVR in Class" value={classTopOvr} accentClass={styles.accentGold} />}
            </div>

            <div className={styles.columns}>
              {/* Primary: the player's own outcome */}
              <GlancePanel>
                <div className={styles.glanceHeadline}>
                  {myCount > 0 ? `You signed ${myCount}.` : "You didn't sign anyone."}
                </div>
                <div className={styles.glanceSub}>
                  {othersJoined} other{othersJoined !== 1 ? 's' : ''} joined the league.
                </div>
                <div className={styles.glanceSlots}>
                  {signedCount}/{signingLimit} slots used
                </div>

                <div className={styles.glanceRows}>
                  {topMine ? (
                    <GlanceRow label="Top signing" value={`${topMine.name} · OVR ${topMine.ovr}`} accentClass={styles.glanceRowValueVolt} />
                  ) : playerSigning ? (
                    // No per-pick card on file (the offseason signing flow records
                    // a roster add + the latest signee, not a recruitment_signing
                    // row), so surface the last signee the backend DID persist
                    // rather than a phantom card. Keeps the panel consistent with
                    // signedCount instead of inventing a list. (BUG #5)
                    <GlanceRow label="Latest signing" value={`${playerSigning.name} · OVR ${playerSigning.ovr}`} accentClass={styles.glanceRowValueVolt} />
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
              <div className={styles.cardsCol}>
                <div role="tablist" aria-label="Filter signings" className={styles.tabRow}>
                  {(['my', 'rival', 'surprise'] as SigningFilter[]).map((f) => {
                    const active = filter === f;
                    return (
                      <button
                        key={f}
                        role="tab"
                        aria-selected={active}
                        onClick={() => setFilter(f)}
                        className={`${styles.tab} ${active ? styles.tabActive : ''}`}
                      >
                        {FILTER_LABELS[f]} <span className={styles.tabCount}>({tabCounts[f]})</span>
                      </button>
                    );
                  })}
                </div>

                <div className={styles.sortNote}>
                  {FILTER_LABELS[filter]} &middot; sorted by OVR
                </div>

                {visible.length === 0 ? (
                  <div className={styles.emptyCards}>
                    {/* BUG #5: when you signed players this offseason but no
                        per-pick card was recorded (free-agent signings don't
                        write contested-round cards), don't claim "you didn't
                        sign anyone" — name the real count instead. */}
                    {filter === 'my' && signedCount > 0
                      ? `You signed ${signedCount} this offseason${playerSigning ? ` (latest: ${playerSigning.name}).` : '.'} Free-agent signings don't get contested-round cards.`
                      : FILTER_EMPTY[filter]}
                  </div>
                ) : (
                  <ul role="list" className={styles.cardList}>
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
                <div className={styles.scheduleWrap}>
                    {stage >= 1 && (
                        <div className="fade-in" style={{ marginBottom: '1rem' }}>
                            <div className={styles.scheduleHead}>
                                <span className={styles.scheduleCount}>
                                    {showAll ? `All ${fixtures.length} matches` : `Your ${playerFixtures.length} match${playerFixtures.length !== 1 ? 'es' : ''}`}
                                </span>
                                {fixtures.length > playerFixtures.length && (
                                    <button onClick={() => setShowAll(!showAll)} className={styles.scheduleToggle}>
                                        {showAll ? 'My Games' : 'Full Schedule'}
                                    </button>
                                )}
                            </div>

                            {displayedFixtures.length === 0 ? (
                                <div className={styles.scheduleEmpty}>
                                    {typeof beat.body === 'string' ? beat.body : 'Schedule not available.'}
                                </div>
                            ) : (
                                <div className={styles.fixtures}>
                                    {displayedFixtures.map((f: OffseasonFixture, i: number) => (
                                        <div
                                            key={i}
                                            className={`${styles.fixture} ${f.is_player_match ? styles.fixturePlayer : ''}`}
                                        >
                                            <span className={styles.fixtureWeek}>
                                                Wk {f.week}
                                            </span>
                                            <span className={`${styles.fixtureTeams} ${f.is_player_match ? styles.fixtureTeamsPlayer : ''}`}>
                                                {f.home && f.away ? `${f.home} vs ${f.away}` : 'Bye Week'}
                                            </span>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {stage >= 2 && prediction && (
                        <div className={`fade-in ${styles.prediction}`}>
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
