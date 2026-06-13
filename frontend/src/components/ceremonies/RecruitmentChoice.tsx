import { useState } from 'react';
import type { OffseasonBeat } from '../../types';
import { KnownValue } from '../../legibility/KnownValue';
import { CeilingGrade } from '../../legibility/CeilingGrade';
import { ActionButton, PageHeader } from '../ui';


type RecruitmentBeat = Extract<OffseasonBeat, { key: 'recruitment' }>;

export function RecruitmentChoice({
  beat,
  onSign,
  acting,
}: {
  beat: RecruitmentBeat;
  onSign: (prospectId: string, releasePlayerId?: string) => void;
  acting: boolean;
}) {
  const prospects = beat.payload.available_prospects ?? [];
  const signedCount = beat.payload.signed_count ?? 0;
  const signingLimit = beat.payload.signing_limit ?? 3;
  const remainingSignings = beat.payload.remaining_signings ?? Math.max(0, signingLimit - signedCount);
  const rosterSize = beat.payload.roster_size ?? 0;
  // Fallback mirrors MAX_USER_ROSTER (12) on the backend — a missing field must
  // not render a stale 9-player cap that contradicts the real recruiting gate.
  const rosterLimit = beat.payload.roster_limit ?? 12;
  const [manualSelectedId, setSelectedId] = useState<string | null>(
    prospects[0]?.prospect_id ?? null,
  );
  const [confirmFinish, setConfirmFinish] = useState(false);
  // Playtest 3 F-8 sign-over-cut: at a full roster the Sign action opens the
  // release picker instead of firing immediately.
  const [releasePickerOpen, setReleasePickerOpen] = useState(false);
  const [releaseId, setReleaseId] = useState<string | null>(null);
  const selectedId = prospects.some(prospect => prospect.prospect_id === manualSelectedId)
    ? manualSelectedId
    : (prospects[0]?.prospect_id ?? null);
  const selected = prospects.find(prospect => prospect.prospect_id === selectedId) ?? null;
  const lastSigning = beat.payload.player_signing;
  const signingOutcome = beat.signing_outcome ?? null;
  const releasedPlayer = beat.released_player ?? null;
  const rosterFull = rosterSize >= rosterLimit;
  const userRoster = beat.payload.user_roster ?? [];
  const releaseChoice = userRoster.find(p => p.id === releaseId) ?? null;
  // PT4-06: every prospect that vanishes from the board mid-day must have a
  // named receipt at the desk, not just in the end-of-day class report.
  const rivalSignings = beat.payload.other_signings ?? [];
  // PT4-11: the backend's roster-floor guard, mirrored into the payload so
  // the skip is DISABLED with the reason instead of firing a 409.
  const canSkip = beat.payload.can_skip ?? true;
  const skipBlockedReason = beat.payload.skip_blocked_reason ?? null;

  return (
    <section className="command-offseason-shell" data-testid="offseason-recruitment-action">
      <PageHeader
        eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats}`}
        title="Signing Day"
        // Codex issue 14: the binding limit is whichever is smaller — class
        // slots or roster space. Say the real capacity up front instead of
        // letting the player plan around three signings with two seats.
        // Playtest 3 F-8: a FULL roster no longer ends recruiting — every
        // pick is a release-to-sign swap, so say that instead of "room for 0".
        description={
          rosterFull
            ? `Roster is full (${rosterSize}/${rosterLimit}) — signing a prospect releases a player you choose. ${remainingSignings} class slot${remainingSignings === 1 ? '' : 's'} remain.`
            : rosterLimit - rosterSize < remainingSignings
            ? `Add up to ${signingLimit} players before next season. ${remainingSignings} class slot${remainingSignings === 1 ? '' : 's'} remain, but your roster is ${rosterSize}/${rosterLimit} — room for ${Math.max(0, rosterLimit - rosterSize)}.`
            : `Add up to ${signingLimit} players before next season. ${remainingSignings} signing${remainingSignings === 1 ? '' : 's'} remain.`
        }
      />

      <article className="dm-panel command-offseason-feature">
        <p className="dm-kicker">Recruitment Desk</p>
        {/* Fog-of-war truth (V16): prospect ratings are SCOUTED RANGES, never
            the hidden true overall. Free agents are league veterans with
            public records, so their OVR is verified. */}
        {prospects.length > 0 && (
          <p
            data-testid="signing-day-ovr-disclosure"
            style={{ margin: '0.35rem 0 0', fontSize: '0.74rem', color: '#94a3b8', lineHeight: 1.45 }}
          >
            Prospect ratings are scouted ranges — the verified OVR is revealed only when they
            sign. Rival clubs bid on prospects too: interest built through scouting, contact
            and visits strengthens your offer. Free agents are league veterans with public
            ratings and sign uncontested. Rivals also sign BETWEEN your picks — a board
            target can be gone by your next slot, so sign your must-haves (especially
            promised players) first.
          </p>
        )}
        {signingOutcome && signingOutcome.kind === 'sniped' && (
          <div
            data-testid="signing-snipe-banner"
            style={{
              margin: '0.6rem 0 0',
              border: '1px solid rgba(249,115,22,0.4)',
              borderLeft: '3px solid #f97316',
              background: 'rgba(249,115,22,0.08)',
              borderRadius: '4px',
              padding: '0.7rem 0.8rem',
            }}
          >
            <p style={{ margin: 0, fontSize: '0.68rem', color: '#fb923c', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Sniped
            </p>
            <p style={{ margin: '0.2rem 0 0', color: '#f8fafc', fontWeight: 700 }}>
              {signingOutcome.winning_club_name} landed {signingOutcome.prospect_name}
            </p>
            <p style={{ margin: '0.15rem 0 0', fontSize: '0.78rem', color: '#cbd5e1' }}>
              {signingOutcome.explanation} Your signing slot was not used — pick from the
              remaining class.
            </p>
          </div>
        )}
        {rivalSignings.length > 0 && (
          <div
            data-testid="signing-rival-board"
            style={{
              margin: '0.6rem 0 0',
              border: '1px solid rgba(148,163,184,0.25)',
              borderLeft: '3px solid #64748b',
              background: 'rgba(148,163,184,0.05)',
              borderRadius: '4px',
              padding: '0.6rem 0.8rem',
            }}
          >
            <p style={{ margin: 0, fontSize: '0.68rem', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Off the board — rival signings so far
            </p>
            <p style={{ margin: '0.25rem 0 0', fontSize: '0.78rem', color: '#cbd5e1', lineHeight: 1.5 }}>
              {rivalSignings.map((s, i) => (
                <span key={`${s.name}-${i}`}>
                  {i > 0 && <span style={{ color: '#475569' }}> · </span>}
                  <strong style={{ color: '#e2e8f0' }}>{s.name}</strong>
                  {s.club_name ? ` → ${s.club_name}` : ''}
                </span>
              ))}
            </p>
          </div>
        )}
        {releasedPlayer && (
          <div
            data-testid="signing-release-banner"
            style={{
              margin: '0.6rem 0 0',
              border: '1px solid rgba(148,163,184,0.35)',
              borderLeft: '3px solid #94a3b8',
              background: 'rgba(148,163,184,0.07)',
              borderRadius: '4px',
              padding: '0.7rem 0.8rem',
            }}
          >
            <p style={{ margin: 0, fontSize: '0.68rem', color: '#cbd5e1', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Released
            </p>
            <p style={{ margin: '0.2rem 0 0', color: '#f8fafc', fontWeight: 700 }}>
              {releasedPlayer.name} ({releasedPlayer.overall} OVR, age {releasedPlayer.age}) is now a free agent.
            </p>
            {beat.released_broken_promise && (
              <p style={{ margin: '0.15rem 0 0', fontSize: '0.78rem', color: '#fb923c' }}>
                Your open promise to them is BROKEN — that costs credibility.
              </p>
            )}
          </div>
        )}
        {signingOutcome && signingOutcome.kind === 'signed' && (
          <div
            data-testid="signing-win-banner"
            style={{
              margin: '0.6rem 0 0',
              border: '1px solid rgba(34,197,94,0.35)',
              borderLeft: '3px solid #22c55e',
              background: 'rgba(34,197,94,0.07)',
              borderRadius: '4px',
              padding: '0.7rem 0.8rem',
            }}
          >
            <p style={{ margin: 0, fontSize: '0.68rem', color: '#4ade80', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              Contested Round Won
            </p>
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.78rem', color: '#cbd5e1' }}>
              {signingOutcome.explanation}
            </p>
            {signingOutcome.reveal && (
              <p
                data-testid="signing-reveal-line"
                style={{ margin: '0.15rem 0 0', fontSize: '0.78rem', color: '#a7f3d0' }}
              >
                {signingOutcome.reveal}
              </p>
            )}
          </div>
        )}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(10rem, 1fr))',
            gap: '0.55rem',
            marginTop: '0.55rem',
            marginBottom: '0.7rem',
          }}
        >
          <div style={{ border: '1px solid #1e293b', borderRadius: '4px', padding: '0.65rem 0.8rem', background: '#08101f' }}>
            <p style={{ margin: 0, fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Signing Progress</p>
            <p style={{ margin: '0.2rem 0 0', color: '#f8fafc', fontSize: '0.95rem', fontWeight: 700 }}>{signedCount} / {signingLimit} added</p>
          </div>
          <div style={{ border: '1px solid #1e293b', borderRadius: '4px', padding: '0.65rem 0.8rem', background: '#08101f' }}>
            <p style={{ margin: 0, fontSize: '0.68rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Roster Size</p>
            <p style={{ margin: '0.2rem 0 0', color: '#f8fafc', fontSize: '0.95rem', fontWeight: 700 }}>{rosterSize} / {rosterLimit}</p>
          </div>
        </div>
        {lastSigning && (
          <div
            style={{
              marginBottom: '0.75rem',
              border: '1px solid rgba(34,211,238,0.28)',
              borderLeft: '3px solid #22d3ee',
              background: 'rgba(34,211,238,0.08)',
              borderRadius: '4px',
              padding: '0.7rem 0.8rem',
            }}
          >
            <p style={{ margin: 0, fontSize: '0.68rem', color: '#67e8f9', textTransform: 'uppercase', letterSpacing: '0.08em' }}>Latest Signing</p>
            <p style={{ margin: '0.2rem 0 0', color: '#f8fafc', fontWeight: 700 }}>{lastSigning.name}</p>
            <p style={{ margin: '0.15rem 0 0', fontSize: '0.78rem', color: '#cbd5e1' }}>
              OVR {lastSigning.ovr}{lastSigning.age ? ` | Age ${lastSigning.age}` : ''}{lastSigning.role ? ` | ${lastSigning.role}` : ''}
            </p>
          </div>
        )}
        {prospects.length === 0 ? (
          <p className="command-offseason-copy">
            No prospects remain in the pool. Continue when you are ready to lock the class.
          </p>
        ) : (
          <div
            style={{
              display: 'grid',
              gap: '0.4rem',
              marginTop: '0.5rem',
              maxHeight: '420px',
              overflowY: 'auto',
            }}
          >
            {prospects.map(prospect => {
              const isSelected = prospect.prospect_id === selectedId;
              return (
                <button
                  key={prospect.prospect_id}
                  type="button"
                  data-testid="recruitment-prospect-row"
                  onClick={() => setSelectedId(prospect.prospect_id)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '0.75rem',
                    width: '100%',
                    textAlign: 'left',
                    padding: '0.6rem 0.85rem',
                    background: isSelected ? 'rgba(34,211,238,0.1)' : '#0a1220',
                    border: '1px solid #1e293b',
                    borderLeft: `3px solid ${isSelected ? '#22d3ee' : '#1e293b'}`,
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <p style={{ margin: 0, color: '#f1f5f9', fontWeight: 700 }}>
                      {prospect.name}
                      {/* Codex issue 13: a target carrying an open promise is
                          flagged so the manager signs them before rivals can. */}
                      {prospect.promised && (
                        <span
                          data-testid="signing-promise-badge"
                          style={{
                            marginLeft: '0.45rem',
                            fontSize: '0.6rem',
                            fontWeight: 700,
                            background: 'rgba(251,191,36,0.18)',
                            color: '#fbbf24',
                            borderRadius: '3px',
                            padding: '1px 5px',
                            textTransform: 'uppercase',
                            letterSpacing: '0.5px',
                          }}
                        >
                          Promise at stake
                        </span>
                      )}
                      {prospect.kind === 'free_agent' && ' '}
                      {prospect.kind === 'free_agent' && (
                        <span
                          style={{
                            marginLeft: '0.45rem',
                            fontSize: '0.6rem',
                            fontWeight: 700,
                            background: '#334155',
                            color: '#cbd5e1',
                            borderRadius: '3px',
                            padding: '1px 5px',
                            textTransform: 'uppercase',
                            letterSpacing: '0.5px',
                          }}
                        >
                          Free Agent
                        </span>
                      )}
                    </p>
                    <p style={{ margin: '0.15rem 0 0', fontSize: '0.74rem', color: '#94a3b8' }}>
                      {prospect.archetype} · {prospect.hometown} · Age {prospect.age}
                    </p>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    {prospect.kind === 'prospect' && prospect.public_ovr_band ? (
                      <>
                        <KnownValue
                          state={prospect.scouted ? 'known' : 'estimated'}
                          label="ovr"
                          value={`${prospect.public_ovr_band[0]}–${prospect.public_ovr_band[1]}`}
                          hint="Scout to narrow"
                        />
                        {typeof prospect.interest === 'number' && (
                          <div style={{ marginTop: '0.2rem', fontSize: '0.62rem', color: '#94a3b8' }}>
                            Interest {prospect.interest}%
                          </div>
                        )}
                        {/* Playtest 3 elite reveal: the same scout-gated
                            growth-arc grade the in-season board shows. */}
                        {prospect.ceiling_label && (
                          <div style={{ marginTop: '0.2rem' }}>
                            <CeilingGrade grade={prospect.ceiling_label} />
                          </div>
                        )}
                      </>
                    ) : (
                      <>
                        <div
                          className="dm-data"
                          style={{ fontSize: '1.15rem', fontWeight: 900, color: '#22d3ee' }}
                        >
                          {prospect.overall}
                        </div>
                        <div style={{ fontSize: '0.58rem', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                          verified ovr
                        </div>
                      </>
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </article>

      {/* Playtest 3 F-8: the sign-over-cut release picker. Shown when the
          roster is full and the player pressed Sign — the pick goes through
          only with a named release, and the release only commits if the
          contested pick lands (a snipe costs nobody). */}
      {releasePickerOpen && selected && rosterFull && (
        <div
          data-testid="signing-release-picker"
          style={{
            margin: '0 0 0.5rem',
            border: '1px solid rgba(34,211,238,0.35)',
            borderLeft: '3px solid #22d3ee',
            background: 'rgba(34,211,238,0.06)',
            borderRadius: '4px',
            padding: '0.7rem 0.9rem',
          }}
        >
          <p style={{ margin: 0, fontWeight: 700, color: '#67e8f9' }}>
            Roster is full — release someone to sign {selected.name}.
          </p>
          <p style={{ margin: '0.2rem 0 0.5rem', fontSize: '0.78rem', color: '#cbd5e1' }}>
            The release happens only if you win the signing; a snipe costs you nobody.
            The released player joins the free-agent pool.
          </p>
          <div style={{ display: 'grid', gap: '0.3rem', maxHeight: '220px', overflowY: 'auto' }}>
            {userRoster.map(p => (
              <label
                key={p.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                  padding: '0.35rem 0.5rem',
                  background: releaseId === p.id ? 'rgba(34,211,238,0.12)' : '#0a1220',
                  border: '1px solid #1e293b',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  fontSize: '0.8rem',
                  color: '#e2e8f0',
                }}
              >
                <input
                  type="radio"
                  name="release-choice"
                  checked={releaseId === p.id}
                  onChange={() => setReleaseId(p.id)}
                />
                <span style={{ fontWeight: 700 }}>{p.name}</span>
                <span style={{ color: '#94a3b8' }}>{p.overall} OVR · age {p.age}</span>
                {p.promised && (
                  <span
                    style={{
                      marginLeft: 'auto',
                      fontSize: '0.6rem',
                      fontWeight: 700,
                      background: 'rgba(249,115,22,0.18)',
                      color: '#fb923c',
                      borderRadius: '3px',
                      padding: '1px 5px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px',
                    }}
                  >
                    Open promise — releasing breaks it
                  </span>
                )}
              </label>
            ))}
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.55rem' }}>
            <button
              type="button"
              disabled={acting || !releaseId}
              onClick={() => {
                if (selectedId && releaseId) {
                  setReleasePickerOpen(false);
                  onSign(selectedId, releaseId);
                }
              }}
              style={{
                background: releaseId ? '#0e7490' : '#1e293b', border: 'none', borderRadius: '4px',
                color: '#fff', fontWeight: 700, padding: '0.4rem 0.9rem',
                cursor: acting || !releaseId ? 'not-allowed' : 'pointer', fontSize: '0.8rem',
              }}
            >
              {releaseChoice
                ? `Release ${releaseChoice.name} & sign ${selected.name}`
                : 'Pick a player to release'}
            </button>
            <button
              type="button"
              onClick={() => { setReleasePickerOpen(false); setReleaseId(null); }}
              style={{
                background: 'none', border: '1px solid #334155', borderRadius: '4px',
                color: '#94a3b8', padding: '0.4rem 0.9rem',
                cursor: 'pointer', fontSize: '0.8rem',
              }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {confirmFinish && remainingSignings > 0 && (
        <div
          style={{
            margin: '0 0 0.5rem',
            border: '1px solid rgba(234,179,8,0.4)',
            borderLeft: '3px solid #eab308',
            background: 'rgba(234,179,8,0.08)',
            borderRadius: '4px',
            padding: '0.7rem 0.9rem',
          }}
        >
          <p style={{ margin: 0, fontWeight: 700, color: '#fbbf24' }}>
            Lock the class with {remainingSignings} slot{remainingSignings === 1 ? '' : 's'} unused?
          </p>
          <p style={{ margin: '0.2rem 0 0.5rem', fontSize: '0.8rem', color: '#cbd5e1' }}>
            Unused signing slots are lost. This cannot be undone.
          </p>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              type="button"
              onClick={() => onSign('skip')}
              disabled={acting}
              style={{
                background: '#b45309', border: 'none', borderRadius: '4px',
                color: '#fff', fontWeight: 700, padding: '0.4rem 0.9rem',
                cursor: acting ? 'not-allowed' : 'pointer', fontSize: '0.8rem',
              }}
            >
              Yes, lock the class
            </button>
            <button
              type="button"
              onClick={() => setConfirmFinish(false)}
              style={{
                background: 'none', border: '1px solid #334155', borderRadius: '4px',
                color: '#94a3b8', padding: '0.4rem 0.9rem',
                cursor: 'pointer', fontSize: '0.8rem',
              }}
            >
              Keep signing
            </button>
          </div>
        </div>
      )}

      <div className="dm-panel command-action-bar">
        <div>
          <p className="dm-kicker">Next action</p>
          <p>
            {remainingSignings > 0
              ? `${remainingSignings} signing slot${remainingSignings === 1 ? '' : 's'} remaining — select a prospect and sign them.`
              : 'All signing slots used. Continue when ready.'}
          </p>
          {!canSkip && skipBlockedReason && (
            <p style={{ margin: '0.2rem 0 0', fontSize: '0.74rem', color: '#fbbf24' }}>
              {skipBlockedReason}
            </p>
          )}
        </div>
        <div className="command-action-buttons">
          <ActionButton
            variant="primary"
            onClick={() => {
              setConfirmFinish(false);
              // Playtest 3 F-8: a full roster routes through the release
              // picker — the pick needs a named release to go through.
              if (rosterFull) {
                setReleasePickerOpen(true);
                return;
              }
              onSign(selected?.prospect_id ?? '');
            }}
            disabled={acting || prospects.length === 0 || !selected}
          >
            {acting
              ? 'Signing...'
              : selected
              ? rosterFull
                ? `Sign ${selected.name} (release someone)`
                : `Sign ${selected.name}`
              : 'Sign Best Available'}
          </ActionButton>
          {remainingSignings > 0 ? (
            <button
              type="button"
              onClick={() => setConfirmFinish(true)}
              disabled={acting || !canSkip}
              title={!canSkip && skipBlockedReason ? skipBlockedReason : undefined}
              style={{
                background: 'none',
                border: '1px solid #334155',
                borderRadius: '4px',
                color: '#64748b',
                padding: '0.4rem 0.9rem',
                cursor: acting || !canSkip ? 'not-allowed' : 'pointer',
                fontSize: '0.8rem',
                whiteSpace: 'nowrap',
                opacity: !canSkip ? 0.5 : 1,
              }}
            >
              {signedCount > 0 ? 'Lock class early' : 'Skip recruiting'}
            </button>
          ) : (
            <ActionButton
              variant="secondary"
              onClick={() => onSign('skip')}
              disabled={acting}
            >
              Continue
            </ActionButton>
          )}
        </div>
      </div>
    </section>
  );
}
