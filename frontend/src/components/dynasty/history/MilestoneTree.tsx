interface TimelineEvent {
  season: string;
  week: number | null;
  event_type: string;
  label: string;
  weight: string;
}

interface MilestoneTreeProps {
  timeline: TimelineEvent[];
}

const WEIGHT_RADIUS: Record<string, number> = {
  championship: 16,
  hof: 12,
  award: 10,
  record: 9,
  milestone: 8,
  standard: 6,
};

interface EventColors {
  fill: string;
  stroke: string;
  branch: string;
  gradientId?: string;
}

const EVENT_COLORS: Record<string, EventColors> = {
  championship: { fill: '#c2410c', stroke: '#fb923c', branch: '#f97316', gradientId: 'champGrad' },
  hof: { fill: '#065f46', stroke: '#34d399', branch: '#10b981' },
  award: { fill: '#d97706', stroke: '#fbbf24', branch: '#eab308' },
  record: { fill: '#0369a1', stroke: '#38bdf8', branch: '#0ea5e9' },
  milestone: { fill: '#7c3aed', stroke: '#a78bfa', branch: '#8b5cf6' },
  standard: { fill: '#3b82f6', stroke: '#60a5fa', branch: '#3b82f6' },
};

const TRUNK_X = 90;
const ROW_HEIGHT = 68;
const V_PAD = 24;
const FIRST_DOT_GAP = 12;
const DOT_PITCH = 56;

export function MilestoneTree({ timeline }: MilestoneTreeProps) {
  // Group events by season
  const seasonMap = new Map<string, TimelineEvent[]>();
  for (const ev of timeline) {
    if (!seasonMap.has(ev.season)) seasonMap.set(ev.season, []);
    seasonMap.get(ev.season)!.push(ev);
  }
  const seasons = Array.from(seasonMap.keys()).sort();

  if (seasons.length === 0) {
    return (
      <div style={{ color: '#475569', fontSize: '0.8rem', padding: '1rem 0' }}>
        No milestones yet.
      </div>
    );
  }

  const totalHeight = seasons.length * ROW_HEIGHT + V_PAD * 2;
  const svgWidth = 460;

  // Precompute dot positions
  type DotInfo = {
    cx: number;
    cy: number;
    r: number;
    colors: EventColors;
    label: string;
    event_type: string;
  };

  const seasonDots: Map<string, DotInfo[]> = new Map();
  const seasonCy: Map<string, number> = new Map();

  seasons.forEach((season, si) => {
    const cy = V_PAD + si * ROW_HEIGHT;
    seasonCy.set(season, cy);
    const events = seasonMap.get(season) ?? [];
    const isChamp = events.some((e) => e.weight === 'championship');
    const trunkR = isChamp ? 8 : 6;

    const dots: DotInfo[] = events.map((ev, di) => {
      const r = WEIGHT_RADIUS[ev.weight] ?? 6;
      const colors = EVENT_COLORS[ev.event_type] ?? EVENT_COLORS.standard;
      const firstDotCx = TRUNK_X + trunkR + FIRST_DOT_GAP + (WEIGHT_RADIUS[events[0]?.weight ?? 'standard'] ?? 6);
      const cx = firstDotCx + di * DOT_PITCH;
      return { cx, cy, r, colors, label: ev.label, event_type: ev.event_type };
    });
    seasonDots.set(season, dots);
  });

  return (
    <div style={{ position: 'relative', width: svgWidth, overflowX: 'auto' }}>
      <svg
        width={svgWidth}
        height={totalHeight}
        style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible' }}
      >
        <defs>
          <radialGradient id="champGrad" cx="40%" cy="35%">
            <stop offset="0%" stopColor="#f97316" />
            <stop offset="100%" stopColor="#9a3412" />
          </radialGradient>
          <filter id="glowOrange" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glowGreen" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="2.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Trunk */}
        <line
          x1={TRUNK_X} y1={V_PAD}
          x2={TRUNK_X} y2={totalHeight - V_PAD}
          stroke="#475569"
          strokeWidth={3}
          strokeLinecap="round"
        />

        {seasons.map((season) => {
          const cy = seasonCy.get(season)!;
          const events = seasonMap.get(season) ?? [];
          const isEmpty = events.length === 0;
          const isChamp = events.some((e) => e.weight === 'championship');
          const trunkR = isChamp ? 8 : isEmpty ? 5 : 6;
          const dots = seasonDots.get(season) ?? [];

          return (
            <g key={season}>
              {/* Championship background band */}
              {isChamp && (
                <rect
                  x={0}
                  y={cy - 20}
                  width={svgWidth}
                  height={40}
                  fill="#f9731608"
                  rx={4}
                />
              )}

              {/* Trunk node */}
              {isEmpty ? (
                <circle
                  cx={TRUNK_X} cy={cy} r={trunkR}
                  fill="#0f172a"
                  stroke="#334155"
                  strokeWidth={1.5}
                  strokeDasharray="3 2"
                />
              ) : isChamp ? (
                <circle
                  cx={TRUNK_X} cy={cy} r={trunkR}
                  fill="#c2410c"
                  stroke="#fb923c"
                  strokeWidth={2.5}
                  filter="url(#glowOrange)"
                />
              ) : (
                <circle
                  cx={TRUNK_X} cy={cy} r={trunkR}
                  fill="#1e293b"
                  stroke="#475569"
                  strokeWidth={2}
                />
              )}

              {/* Empty season stub */}
              {isEmpty && (
                <line
                  x1={TRUNK_X + trunkR} y1={cy}
                  x2={TRUNK_X + trunkR + 20} y2={cy}
                  stroke="#1e293b"
                  strokeWidth={1.5}
                  strokeDasharray="3 2"
                />
              )}

              {/* Branch lines between dots */}
              {dots.map((dot, di) => {
                const branchColor = dot.colors.branch;
                const isChampDot = dot.event_type === 'championship';
                const strokeW = isChampDot ? 2 : 1.5;

                if (di === 0) {
                  // Trunk edge to first dot left edge
                  return (
                    <line
                      key={`branch-${di}`}
                      x1={TRUNK_X + trunkR} y1={cy}
                      x2={dot.cx - dot.r} y2={cy}
                      stroke={branchColor}
                      strokeWidth={strokeW}
                      opacity={0.7}
                    />
                  );
                }
                const prev = dots[di - 1];
                return (
                  <line
                    key={`branch-${di}`}
                    x1={prev.cx + prev.r} y1={cy}
                    x2={dot.cx - dot.r} y2={cy}
                    stroke={branchColor}
                    strokeWidth={strokeW}
                    opacity={0.7}
                  />
                );
              })}

              {/* Milestone dots */}
              {dots.map((dot, di) => {
                const { cx, cy: dotCy, r, colors, event_type } = dot;
                const isChampDot = event_type === 'championship';
                const isHof = event_type === 'hof';
                const glowFilter = isChampDot
                  ? 'url(#glowOrange)'
                  : isHof
                  ? 'url(#glowGreen)'
                  : undefined;
                const fillAttr = isChampDot ? 'url(#champGrad)' : colors.fill;
                return (
                  <circle
                    key={di}
                    cx={cx}
                    cy={dotCy}
                    r={r}
                    fill={fillAttr}
                    stroke={colors.stroke}
                    strokeWidth={isChampDot ? 3 : 2}
                    filter={glowFilter}
                  />
                );
              })}
            </g>
          );
        })}

        {/* Present trailing dot */}
        <circle
          cx={TRUNK_X}
          cy={totalHeight - V_PAD + 12}
          r={3}
          fill="#334155"
          opacity={0.5}
        />
      </svg>

      {/* HTML label layer */}
      <div style={{ position: 'relative', height: totalHeight }}>
        {seasons.map((season) => {
          const cy = seasonCy.get(season)!;
          const events = seasonMap.get(season) ?? [];
          const isEmpty = events.length === 0;
          const isChamp = events.some((e) => e.weight === 'championship');
          const dots = seasonDots.get(season) ?? [];

          return (
            <div key={season}>
              {/* Season label left of trunk */}
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  width: TRUNK_X - 6,
                  textAlign: 'right',
                  top: cy - 7,
                  fontSize: '0.6rem',
                  color: isChamp ? '#fb923c' : isEmpty ? '#334155' : '#64748b',
                  fontWeight: isChamp ? 700 : 400,
                  fontStyle: isEmpty ? 'italic' : 'normal',
                  whiteSpace: 'nowrap',
                }}
              >
                {season}
              </div>

              {/* Empty season text */}
              {isEmpty && (
                <div
                  style={{
                    position: 'absolute',
                    left: TRUNK_X + 26,
                    top: cy - 7,
                    fontSize: '0.55rem',
                    color: '#334155',
                    fontStyle: 'italic',
                    whiteSpace: 'nowrap',
                  }}
                >
                  — no milestones
                </div>
              )}

              {/* Dot labels */}
              {dots.map((dot, di) => (
                <div
                  key={di}
                  style={{
                    position: 'absolute',
                    left: dot.cx,
                    top: dot.cy + dot.r + 4,
                    transform: 'translateX(-50%)',
                    fontSize: '0.55rem',
                    color: dot.colors.stroke,
                    whiteSpace: 'nowrap',
                    fontWeight: dot.event_type === 'championship' ? 700 : 400,
                    textAlign: 'center',
                  }}
                >
                  {dot.event_type === 'championship' ? '🏆 ' : ''}{dot.label}
                </div>
              ))}
            </div>
          );
        })}

        {/* Present label */}
        <div
          style={{
            position: 'absolute',
            left: TRUNK_X + 12,
            top: totalHeight - V_PAD + 6,
            fontSize: '0.55rem',
            color: '#334155',
            fontStyle: 'italic',
          }}
        >
          Present…
        </div>
      </div>
    </div>
  );
}
