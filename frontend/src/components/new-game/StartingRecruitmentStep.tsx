import { useState, useEffect, useMemo } from 'react';
import { ActionButton } from '../ui';
import { formatOverall, formatPlayerName, formatRole } from '../roster/playerDisplay';

interface ProspectOption {
  player_id: string;
  name: string;
  hometown: string;
  public_archetype: string;
  public_ovr_band: [number, number];
}

// Soft roster-balance guidance for the build-from-scratch starting draft.
type RoleTrack = 'throwing' | 'catching' | 'survival';

interface RoleInfo {
  label: string;
  roles: RoleTrack[];
}

const ARCHETYPE_ROLES: Record<string, RoleInfo> = {
  'Sharpshooter': { label: 'Thrower', roles: ['throwing'] },
  'Skirmisher': { label: 'Thrower / Survivor', roles: ['throwing', 'survival'] },
  'Net Specialist': { label: 'Catcher', roles: ['catching'] },
  'Iron Anchor': { label: 'Survivor', roles: ['survival'] },
  'Possession Specialist': { label: 'Catcher / Survivor', roles: ['catching', 'survival'] },
  'Ball Hawk': { label: 'Survivor', roles: ['survival'] },
  'Two-Way Threat': { label: 'Thrower / Catcher', roles: ['throwing', 'catching'] },
  'Hit-and-Run': { label: 'Survivor', roles: ['survival'] },
};

const RECOMMENDED: Record<RoleTrack, { min: number; label: string; tip: string }> = {
  throwing: { min: 2, label: 'Throwing', tip: 'Players who can reliably pressure opponents.' },
  catching: { min: 2, label: 'Catching', tip: 'Players who can punish bad throws and protect rallies.' },
  survival: { min: 1, label: 'Survival', tip: 'Players who keep points alive through dodging, stamina, or ball control.' },
};

const ROLE_ORDER: RoleTrack[] = ['throwing', 'catching', 'survival'];

export function StartingRecruitmentStep({
  onCommit,
  onBack,
  creating,
}: {
  onCommit: (ids: string[]) => void;
  onBack: () => void;
  creating: boolean;
}) {
  const [prospects, setProspects] = useState<ProspectOption[]>([]);
  const [rosterIds, setRosterIds] = useState<Set<string>>(new Set());
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/saves/starting-prospects')
      .then(r => {
        if (!r.ok) throw new Error('Failed to load prospects');
        return r.json();
      })
      .then(d => setProspects(d.prospects ?? []))
      .catch(err => setLoadError(err.message));
  }, []);

  const toggleProspect = (id: string) => {
    setRosterIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 10) next.add(id);
      return next;
    });
  };

  // Count role coverage, not unique players: hybrids can help in multiple lanes.
  const compositionTally = useMemo(() => {
    const counts: Record<RoleTrack, number> = { throwing: 0, catching: 0, survival: 0 };
    for (const id of rosterIds) {
      const prospect = prospects.find(p => p.player_id === id);
      const roleInfo = prospect ? ARCHETYPE_ROLES[prospect.public_archetype] : undefined;
      if (roleInfo) {
        for (const role of roleInfo.roles) counts[role] += 1;
      }
    }
    return counts;
  }, [rosterIds, prospects]);

  const hasImbalance = useMemo(() => {
    if (rosterIds.size < 6) return false;
    return ROLE_ORDER.some(role => compositionTally[role] < RECOMMENDED[role].min);
  }, [compositionTally, rosterIds.size]);

  const needed = 6 - rosterIds.size;
  const rosterReady = rosterIds.size >= 6;
  const rosterFull = rosterIds.size >= 10;
  const rosterHelp = rosterReady
    ? rosterFull
      ? 'Roster ready. Remove one player if you want to swap a selection before committing.'
      : 'Roster ready. You can commit now or keep scouting up to 10 players.'
    : rosterIds.size === 0
    ? 'Choose between 6 and 10 players to continue.'
    : `Add ${needed} more player${needed === 1 ? '' : 's'} to continue.`;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div>
        <p className="dm-kicker" style={{ marginBottom: '0.25rem' }}>Step 3 of 3</p>
        <h2 style={{ fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#fff', margin: 0, fontSize: '1.25rem' }}>
          Recruit Roster
        </h2>
        <p style={{ margin: '0.375rem 0 0', fontSize: '0.8125rem', color: '#64748b' }}>
          Select at least 6 players (max 10). {rosterIds.size > 0 && `${rosterIds.size} selected.`}
        </p>
        <p style={{ fontSize: '0.75rem', opacity: 0.7, color: '#94a3b8', marginTop: '0.375rem', marginBottom: '0.5rem' }}>
          Each prospect shows their current <strong>OVR</strong> and archetype — the same values their roster row will show after you commit.
        </p>
      </div>

      <div
        id="composition-guide"
        style={{
          background: 'rgba(15,23,42,0.6)',
          border: '1px solid #1e293b',
          borderRadius: '6px',
          padding: '0.625rem 0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', marginBottom: '0.375rem' }}>
          <span style={{ fontSize: '0.6875rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: '#94a3b8' }}>
            Suggested Foundation
          </span>
          {rosterIds.size > 0 && (
            <span style={{ fontSize: '0.625rem', color: '#475569', fontWeight: 500 }}>
              - {rosterIds.size} selected
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
          {ROLE_ORDER.map(role => {
            const rec = RECOMMENDED[role];
            const count = compositionTally[role];
            const met = count >= rec.min;
            const active = rosterIds.size > 0;
            return (
              <div
                key={role}
                title={rec.tip}
                style={{
                  flex: '1 1 0',
                  minWidth: '100px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.1875rem',
                  padding: '0.375rem 0.5rem',
                  borderRadius: '4px',
                  background: active
                    ? met ? 'rgba(34,197,94,0.06)' : 'rgba(251,191,36,0.06)'
                    : 'rgba(30,41,59,0.4)',
                  border: active
                    ? met ? '1px solid rgba(34,197,94,0.2)' : '1px solid rgba(251,191,36,0.2)'
                    : '1px solid transparent',
                  transition: 'background 0.15s, border-color 0.15s',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '0.75rem', fontWeight: 600, color: '#e2e8f0' }}>
                    {rec.label}
                  </span>
                  <span
                    style={{
                      fontSize: '0.75rem',
                      fontWeight: 800,
                      fontVariantNumeric: 'tabular-nums',
                      color: active
                        ? met ? '#4ade80' : '#fbbf24'
                        : '#475569',
                    }}
                  >
                    {count}/{rec.min}+
                  </span>
                </div>
                <div style={{ fontSize: '0.625rem', color: '#64748b', lineHeight: 1.3 }}>
                  {rec.tip}
                </div>
              </div>
            );
          })}
        </div>
        {hasImbalance && (
          <p
            id="composition-warning"
            style={{
              margin: '0.375rem 0 0',
              fontSize: '0.6875rem',
              color: '#fbbf24',
              display: 'flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
          >
            Your roster is light in one or more areas. You can still commit, but a balanced first six is easier to manage.
          </p>
        )}
      </div>

      {loadError && (
        <div style={{ padding: '0.75rem', background: 'rgba(244,63,94,0.1)', border: '1px solid rgba(244,63,94,0.3)', borderRadius: '4px', color: '#fb7185', fontSize: '0.875rem' }}>
          {loadError}
        </div>
      )}

      {prospects.length === 0 && !loadError && (
        <p style={{ color: '#64748b', fontSize: '0.875rem' }}>Loading prospects...</p>
      )}

      <div style={{ maxHeight: '360px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.375rem', paddingRight: '0.25rem' }}>
        {prospects.map(p => {
          const selected = rosterIds.has(p.player_id);
          const canSelect = selected || rosterIds.size < 10;
          const displayName = formatPlayerName(p);
          const displayRole = formatRole(p);
          const displayOverall = formatOverall(p);
          const roleInfo = ARCHETYPE_ROLES[p.public_archetype];
          return (
            <button
              key={p.player_id}
              type="button"
              role="checkbox"
              aria-checked={selected}
              aria-label={`${displayName}, ${p.hometown}, ${displayRole}, overall ${displayOverall}`}
              onClick={() => {
                if (canSelect) toggleProspect(p.player_id);
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '0.625rem 0.875rem',
                background: selected ? 'rgba(34,211,238,0.06)' : '#0f172a',
                border: selected ? '1px solid rgba(34,211,238,0.4)' : '1px solid #1e293b',
                borderRadius: '4px',
                cursor: canSelect ? 'pointer' : 'not-allowed',
                opacity: canSelect ? 1 : 0.55,
                transition: 'border-color 0.12s, background 0.12s',
                flexShrink: 0,
                textAlign: 'left',
              }}
            >
              <div style={{ minWidth: 0 }}>
                <div style={{ fontWeight: 700, fontSize: '0.9375rem', color: selected ? '#67e8f9' : '#e2e8f0', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {displayName}
                </div>
                <div style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.125rem' }}>
                  {displayRole && (
                    <span style={{ color: '#475569' }}>
                      {' | '}
                      {displayRole}
                      {roleInfo && <span style={{ color: '#64748b' }}> ({roleInfo.label})</span>}
                    </span>
                  )}
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0, marginLeft: '1rem' }}>
                <div style={{ textAlign: 'right' }}>
                  <div className="dm-data" style={{ fontWeight: 800, color: selected ? '#22d3ee' : '#94a3b8', fontSize: '0.875rem' }} title="Current overall rating">
                    <strong>{displayOverall}</strong>
                    <span style={{ fontSize: '0.5625rem', opacity: 0.6, marginLeft: '0.25rem' }}>
                      OVR
                    </span>
                  </div>
                </div>
                <div style={{ width: '18px', height: '18px', borderRadius: '9999px', border: selected ? '2px solid #22d3ee' : '2px solid #334155', background: selected ? 'rgba(34,211,238,0.15)' : 'transparent', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  {selected && <span style={{ color: '#22d3ee', fontSize: '0.625rem', lineHeight: 1 }}>OK</span>}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', flexWrap: 'wrap' }}>
          <ActionButton variant="secondary" onClick={onBack} disabled={creating}>Back</ActionButton>
          <ActionButton
            variant="primary"
            onClick={() => onCommit(Array.from(rosterIds))}
            disabled={rosterIds.size < 6 || creating}
            aria-describedby="starting-roster-help"
          >
            {creating ? 'Creating...' : `Commit Roster (${rosterIds.size}/10)`}
          </ActionButton>
        </div>
        <p
          id="starting-roster-help"
          className={`dm-helper-copy ${rosterReady ? '' : 'dm-helper-copy-warning'}`.trim()}
          style={{ margin: 0 }}
        >
          {rosterHelp}
        </p>
      </div>
    </div>
  );
}
