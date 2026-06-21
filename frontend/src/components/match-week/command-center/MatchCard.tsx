import { useMemo, useState } from 'react';
import type { LineupPlayer } from '../../../types';
import styles from './MatchCard.module.css';

interface MatchCardProps {
  yourPlayers: LineupPlayer[];
  oppPlayers: LineupPlayer[];
  yourTeamName: string;
  oppTeamName: string;
  compact?: boolean;
  maxVisibleRows?: number;
}

type Mode = 'ovr' | 'sta';

function teamAbbr(name: string): string {
  const words = name.trim().split(/\s+/);
  return (words.at(-1) ?? name).slice(0, 4).toUpperCase();
}

export function MatchCard({
  yourPlayers,
  oppPlayers,
  yourTeamName,
  oppTeamName,
  compact = false,
  maxVisibleRows = 4,
}: MatchCardProps) {
  const [mode, setMode] = useState<Mode>('ovr');
  const [showAll, setShowAll] = useState(false);

  const youAbbr = teamAbbr(yourTeamName);
  const oppAbbr = teamAbbr(oppTeamName);
  const hasOpp = oppPlayers.length > 0;

  const slots = useMemo(() => {
    return yourPlayers.slice(0, 6).map((you, i) => {
      const opp = oppPlayers[i];
      const ovrGap = opp ? Math.round(you.overall) - Math.round(opp.overall) : 0;
      const staGap = opp && you.stamina !== undefined && opp.stamina !== undefined
        ? Math.round(you.stamina) - Math.round(opp.stamina)
        : 0;
      return { you, opp, ovrGap, staGap };
    });
  }, [yourPlayers, oppPlayers]);

  const sorted = useMemo(
    () => [...slots].sort((a, b) => {
      const ag = Math.abs(mode === 'ovr' ? a.ovrGap : a.staGap);
      const bg = Math.abs(mode === 'ovr' ? b.ovrGap : b.staGap);
      return bg - ag;
    }),
    [slots, mode],
  );

  const maxGap = Math.max(...sorted.map(s => Math.abs(mode === 'ovr' ? s.ovrGap : s.staGap)), 1);

  const netOvr = slots.reduce((sum, s) => sum + s.ovrGap, 0);
  const netSta = slots.reduce((sum, s) => sum + s.staGap, 0);
  const net = mode === 'ovr' ? netOvr : netSta;
  const netLeader = net >= 0 ? yourTeamName : oppTeamName;
  const edgeLabel = mode === 'ovr' ? 'OVERALL EDGE' : 'STAMINA EDGE';

  const advantages = sorted.filter(s => (mode === 'ovr' ? s.ovrGap : s.staGap) > 0).length;
  const disadvantages = sorted.filter(s => (mode === 'ovr' ? s.ovrGap : s.staGap) < 0).length;
  const visibleRows = showAll || !compact ? sorted : sorted.slice(0, maxVisibleRows);

  return (
    <div className={`command-match-card${compact ? ' is-compact' : ''} ${styles.card}`}>
      {/* Header — hidden in compact mode */}
      {!compact && (
        <div className={styles.header}>
          <span className={styles.teamYou} title={yourTeamName}>
            {yourTeamName.toUpperCase()}
          </span>

          <div className={styles.headerCenter}>
            <span className={styles.vsLabel}>VS</span>
            <div className={styles.modeRow}>
              <button
                type="button"
                className={`${styles.modeBtn}${mode === 'ovr' ? ` ${styles.active}` : ''}`}
                onClick={() => setMode('ovr')}
              >
                OVR
              </button>
              <button
                type="button"
                className={`${styles.modeBtn}${mode === 'sta' ? ` ${styles.active}` : ''}`}
                onClick={() => setMode('sta')}
              >
                STA
              </button>
            </div>
          </div>

          <span className={styles.teamOpp} title={oppTeamName}>
            {oppTeamName.toUpperCase()}
          </span>
        </div>
      )}

      {/* Net summary strip — hidden in compact mode */}
      {hasOpp && !compact && (
        <div className={styles.netStrip}>
          <span className={styles.netLabel}>{edgeLabel}</span>
          <span className={`${styles.netValue}${net >= 0 ? ` ${styles.netYou}` : ` ${styles.netOpp}`}`}>
            {netLeader} {net >= 0 ? `+${net}` : `+${Math.abs(net)}`} net {mode.toUpperCase()}
          </span>
        </div>
      )}

      {/* Legend */}
      {hasOpp && !compact && (
        <div className={styles.legend}>
          <span className={styles.legendYou}>◀ {youAbbr} ADVANTAGE</span>
          <span className={styles.legendMid}>Longer bar = larger {mode.toUpperCase()} edge</span>
          <span className={styles.legendOpp}>{oppAbbr} ADVANTAGE ▶</span>
        </div>
      )}

      {/* Rows */}
      {visibleRows.map((slot, i) => {
        const gap = mode === 'ovr' ? slot.ovrGap : slot.staGap;
        const barWidth = (Math.abs(gap) / maxGap) * 50;
        const youWin = gap > 0;
        const youVal = mode === 'ovr'
          ? Math.round(slot.you.overall)
          : (slot.you.stamina !== undefined ? Math.round(slot.you.stamina) : '—');
        const oppVal = slot.opp
          ? (mode === 'ovr'
            ? Math.round(slot.opp.overall)
            : (slot.opp.stamina !== undefined ? Math.round(slot.opp.stamina) : '—'))
          : '—';

        const statValClass = !hasOpp
          ? styles.statValNoOpp
          : gap === 0
            ? styles.statValEven
            : youWin
              ? styles.statValYouWin
              : styles.statValOppWin;

        const oppStatValClass = !hasOpp
          ? styles.statValNoOpp
          : gap === 0
            ? styles.statValEven
            : youWin
              ? styles.statValOppWin
              : styles.statValYouWin;

        const nameClass = `${styles.playerName} ${compact ? styles.playerNameSm : styles.playerNameMd}`;

        const isLast = i === visibleRows.length - 1;

        return (
          <div
            key={slot.you.id}
            className={styles.matchupRow}
            style={isLast ? { borderBottom: 'none' } : undefined}
          >
            {/* Your side */}
            <div className={styles.yourSide}>
              <div className={styles.statBadge}>
                <span className={styles.statKey}>{mode === 'ovr' ? 'OVR' : 'STA'}</span>
                <span className={statValClass}>{youVal}</span>
              </div>
              <span title={slot.you.name} className={nameClass}>
                {slot.you.name}
              </span>
            </div>

            {/* Center: gap label + bar */}
            <div className={styles.center}>
              {hasOpp ? (
                <>
                  <span className={`${styles.gapLabel} ${gap === 0 ? styles.gapLabelEven : youWin ? styles.gapLabelYou : styles.gapLabelOpp}`}>
                    {gap === 0 ? 'EVEN' : youWin ? `◀ ${youAbbr} +${Math.abs(gap)}` : `−${Math.abs(gap)} ▶`}
                  </span>
                  <div className={styles.barTrack}>
                    <div className={styles.barDivider} />
                    {gap !== 0 && (
                      <div
                        className={youWin ? styles.barFillYou : styles.barFillOpp}
                        style={{ width: `${barWidth}%` }}
                      />
                    )}
                  </div>
                </>
              ) : (
                <span className={styles.noDash}>—</span>
              )}
            </div>

            {/* Opponent side */}
            <div className={styles.oppSide}>
              {slot.opp ? (
                <>
                  <span title={slot.opp.name} className={nameClass}>
                    {slot.opp.name}
                  </span>
                  <div className={styles.statBadge}>
                    <span className={styles.statKey}>{mode === 'ovr' ? 'OVR' : 'STA'}</span>
                    <span className={oppStatValClass}>{oppVal}</span>
                  </div>
                </>
              ) : (
                <span className={styles.unavailable}>Unavailable</span>
              )}
            </div>
          </div>
        );
      })}

      {/* Fallback message if no opp data */}
      {!hasOpp && (
        <p className={styles.noOpp}>Opponent lineup unavailable</p>
      )}

      {/* Tally */}
      {hasOpp && !compact && (
        <div className={styles.tally}>
          <span><span className={styles.tallyAdv}>{advantages}</span> slot advantages</span>
          <span><span className={styles.tallyDisadv}>{disadvantages}</span> slot disadvantages</span>
        </div>
      )}

      {compact && sorted.length > maxVisibleRows && (
        <button
          type="button"
          className={`command-inline-toggle ${styles.expandBtn}`}
          onClick={() => setShowAll(prev => !prev)}
        >
          {showAll ? 'Collapse details' : `Expand all ${sorted.length} matchups`}
        </button>
      )}
    </div>
  );
}
