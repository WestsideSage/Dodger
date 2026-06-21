import { useMemo } from 'react';
import styles from './LiveCourtCanvas.module.css';

interface PlayerInfo {
  id: string;
  name: string;
  label: string;
  clubId: string;
}

interface LiveCourtCanvasProps {
  homeIds: string[];
  awayIds: string[];
  playerRegistry: Map<string, PlayerInfo>;
  eliminatedIds: Set<string>;
  throwerId: string | null;
  targetId: string | null;
  activeResolution: string | null;
}

// Geometry (SVG coordinate space — not px/css units, exempt from the token gate).
const VB_W = 600;
const VB_H = 320;
const TOKEN_R = 14;

interface Pt {
  x: number;
  y: number;
}

// Deterministic <=2-column formation that scales to ANY side count (no
// 6-player assumption — Pattern 6). Home fills the left half, away the right.
function formation(ids: string[], side: 'left' | 'right'): Map<string, Pt> {
  const map = new Map<string, Pt>();
  const n = ids.length;
  if (n === 0) return map;
  const cols = n <= 1 ? 1 : 2;
  const rows = Math.ceil(n / cols);
  const halfW = VB_W / 2;
  // Column x-positions within the side's half.
  const colXs =
    side === 'left'
      ? cols === 1
        ? [halfW / 2]
        : [halfW * 0.32, halfW * 0.72]
      : cols === 1
        ? [halfW + halfW / 2]
        : [halfW + halfW * 0.28, halfW + halfW * 0.68];
  const rowGap = VB_H / (rows + 1);
  ids.forEach((id, i) => {
    const col = i % cols;
    const row = Math.floor(i / cols);
    map.set(id, { x: colXs[col], y: rowGap * (row + 1) });
  });
  return map;
}

const isCatch = (r: string | null) => r === 'caught' || r === 'catch';

export function LiveCourtCanvas({
  homeIds,
  awayIds,
  playerRegistry,
  eliminatedIds,
  throwerId,
  targetId,
  activeResolution,
}: LiveCourtCanvasProps) {
  const positions = useMemo(() => {
    const map = new Map<string, Pt>();
    formation(homeIds, 'left').forEach((v, k) => map.set(k, v));
    formation(awayIds, 'right').forEach((v, k) => map.set(k, v));
    return map;
  }, [homeIds, awayIds]);

  const all = [...homeIds, ...awayIds];
  if (all.length === 0) {
    return (
      <div className={styles.noData} data-testid="live-court-nodata">
        No live court for this match.
      </div>
    );
  }

  const throwerPos = throwerId ? positions.get(throwerId) : null;
  const targetPos = targetId ? positions.get(targetId) : null;
  const hasThrow = Boolean(throwerPos && targetPos);
  const catchThrow = isCatch(activeResolution);
  const outcome = activeResolution
    ? activeResolution === 'eliminated' || activeResolution === 'hit' || activeResolution === 'failed_catch'
      ? 'OUT'
      : catchThrow
        ? 'CATCH'
        : activeResolution === 'dodged'
          ? 'DODGE'
          : ''
    : '';

  const midX = hasThrow ? (throwerPos!.x + targetPos!.x) / 2 : 0;
  const midY = hasThrow ? Math.min(throwerPos!.y, targetPos!.y) - 30 : 0;

  return (
    <svg
      viewBox="0 0 600 320"
      xmlns="http://www.w3.org/2000/svg"
      className={styles.court}
      aria-label="Live dodgeball court"
    >
      {/* court markings */}
      <line className={styles.midline} x1={VB_W / 2} y1={0} x2={VB_W / 2} y2={VB_H} strokeWidth="2" strokeDasharray="6 6" />
      <circle className={styles.centerCircle} cx={VB_W / 2} cy={VB_H / 2} r="30" strokeWidth="2" strokeDasharray="4 4" />
      <text className={styles.zoneLabel} x="16" y="22" fontSize="11" letterSpacing="2">HOME</text>
      <text className={styles.zoneLabel} x={VB_W - 60} y="22" fontSize="11" letterSpacing="2">AWAY</text>

      {/* throw arc — only when both ends are present */}
      {hasThrow && (
        <path
          data-throw-arc
          className={`${styles.arc}${catchThrow ? ` ${styles.arcCatch}` : ''}`}
          d={`M ${throwerPos!.x} ${throwerPos!.y} Q ${midX} ${midY} ${targetPos!.x} ${targetPos!.y}`}
        />
      )}
      {hasThrow && outcome && (
        <text
          className={`${styles.outcomeLabel}${catchThrow ? ` ${styles.outcomeLabelCatch}` : ''}`}
          x={midX}
          y={midY + 14}
          textAnchor="middle"
          fontSize="13"
          fontWeight="700"
          letterSpacing="2"
        >
          {outcome}
        </text>
      )}

      {/* player tokens */}
      {all.map((pid) => {
        const pos = positions.get(pid);
        if (!pos) return null;
        const info = playerRegistry.get(pid);
        const isHome = homeIds.includes(pid);
        const elim = eliminatedIds.has(pid);
        return (
          <g
            key={pid}
            data-player-token={pid}
            data-extinguished={elim ? 'true' : 'false'}
            className={elim ? styles.extinguished : undefined}
          >
            <circle
              className={`${styles.token} ${isHome ? styles.tokenHome : styles.tokenAway}`}
              cx={pos.x}
              cy={pos.y}
              r={TOKEN_R}
            />
            <text className={styles.tokenLabel + ' ' + (isHome ? styles.tokenLabelHome : styles.tokenLabelAway)} x={pos.x} y={pos.y + 28} textAnchor="middle" fontSize="9.5" fontWeight="600">
              {info?.label ?? ''}
            </text>
            {elim && (
              <line
                className={`${styles.extinctMark} ${isHome ? styles.extinctMarkHome : styles.extinctMarkAway}`}
                x1={pos.x - 14}
                y1={pos.y - 14}
                x2={pos.x + 14}
                y2={pos.y + 14}
              />
            )}
          </g>
        );
      })}
    </svg>
  );
}
