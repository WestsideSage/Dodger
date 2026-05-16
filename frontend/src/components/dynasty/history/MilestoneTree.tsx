import { formatSeasonLabel, formatTimelineLabel } from './formatters';

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
const ROW_HEIGHT = 80;
const V_PAD = 24;
const FIRST_DOT_GAP = 12;
const DOT_PITCH = 60;

export function MilestoneTree({ timeline }: MilestoneTreeProps) {
  const seasonMap = new Map<string, TimelineEvent[]>();
  for (const event of timeline) {
    if (!seasonMap.has(event.season)) {
      seasonMap.set(event.season, []);
    }
    seasonMap.get(event.season)!.push(event);
  }

  const seasons = Array.from(seasonMap.keys()).sort();
  if (seasons.length === 0) {
    return <div style={{ color: '#475569', fontSize: '0.8rem', padding: '1rem 0' }}>No milestones yet.</div>;
  }

  const totalHeight = seasons.length * ROW_HEIGHT + V_PAD * 2;
  const svgWidth = 460;

  type DotInfo = {
    cx: number;
    cy: number;
    r: number;
    colors: EventColors;
    label: string;
    event_type: string;
  };

  const seasonDots = new Map<string, DotInfo[]>();
  const seasonCy = new Map<string, number>();

  seasons.forEach((season, seasonIndex) => {
    const cy = V_PAD + seasonIndex * ROW_HEIGHT;
    seasonCy.set(season, cy);

    const events = seasonMap.get(season) ?? [];
    const isChampionshipSeason = events.some((event) => event.weight === 'championship');
    const trunkRadius = isChampionshipSeason ? 8 : 6;
    const firstDotCx =
      TRUNK_X +
      trunkRadius +
      FIRST_DOT_GAP +
      (WEIGHT_RADIUS[events[0]?.weight ?? 'standard'] ?? 6);

    const dots = events.map((event, dotIndex) => {
      const r = WEIGHT_RADIUS[event.weight] ?? 6;
      const colors = EVENT_COLORS[event.event_type] ?? EVENT_COLORS.standard;
      return {
        cx: firstDotCx + dotIndex * DOT_PITCH,
        cy,
        r,
        colors,
        label: event.label,
        event_type: event.event_type,
      };
    });

    seasonDots.set(season, dots);
  });

  return (
    <div style={{ position: 'relative', width: svgWidth, overflowX: 'auto' }}>
      <svg width={svgWidth} height={totalHeight} style={{ position: 'absolute', left: 0, top: 0, overflow: 'visible' }}>
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

        <line x1={TRUNK_X} y1={V_PAD} x2={TRUNK_X} y2={totalHeight - V_PAD} stroke="#475569" strokeWidth={3} strokeLinecap="round" />

        {seasons.map((season) => {
          const cy = seasonCy.get(season)!;
          const events = seasonMap.get(season) ?? [];
          const isEmpty = events.length === 0;
          const isChampionshipSeason = events.some((event) => event.weight === 'championship');
          const trunkRadius = isChampionshipSeason ? 8 : isEmpty ? 5 : 6;
          const dots = seasonDots.get(season) ?? [];

          return (
            <g key={season}>
              {isChampionshipSeason && <rect x={0} y={cy - 20} width={svgWidth} height={40} fill="#f9731608" rx={4} />}

              {isEmpty ? (
                <circle cx={TRUNK_X} cy={cy} r={trunkRadius} fill="#0f172a" stroke="#334155" strokeWidth={1.5} strokeDasharray="3 2" />
              ) : isChampionshipSeason ? (
                <circle cx={TRUNK_X} cy={cy} r={trunkRadius} fill="#c2410c" stroke="#fb923c" strokeWidth={2.5} filter="url(#glowOrange)" />
              ) : (
                <circle cx={TRUNK_X} cy={cy} r={trunkRadius} fill="#1e293b" stroke="#475569" strokeWidth={2} />
              )}

              {isEmpty && (
                <line x1={TRUNK_X + trunkRadius} y1={cy} x2={TRUNK_X + trunkRadius + 20} y2={cy} stroke="#1e293b" strokeWidth={1.5} strokeDasharray="3 2" />
              )}

              {dots.map((dot, dotIndex) => {
                const strokeWidth = dot.event_type === 'championship' ? 2 : 1.5;
                const x1 = dotIndex === 0 ? TRUNK_X + trunkRadius : dots[dotIndex - 1].cx + dots[dotIndex - 1].r;
                const x2 = dot.cx - dot.r;
                return <line key={`branch-${season}-${dotIndex}`} x1={x1} y1={cy} x2={x2} y2={cy} stroke={dot.colors.branch} strokeWidth={strokeWidth} opacity={0.7} />;
              })}

              {dots.map((dot, dotIndex) => {
                const isChampionshipDot = dot.event_type === 'championship';
                const isHallOfFameDot = dot.event_type === 'hof';
                return (
                  <circle
                    key={`dot-${season}-${dotIndex}`}
                    cx={dot.cx}
                    cy={dot.cy}
                    r={dot.r}
                    fill={isChampionshipDot ? 'url(#champGrad)' : dot.colors.fill}
                    stroke={dot.colors.stroke}
                    strokeWidth={isChampionshipDot ? 3 : 2}
                    filter={isChampionshipDot ? 'url(#glowOrange)' : isHallOfFameDot ? 'url(#glowGreen)' : undefined}
                  />
                );
              })}
            </g>
          );
        })}

        <circle cx={TRUNK_X} cy={totalHeight - V_PAD + 12} r={3} fill="#334155" opacity={0.5} />
      </svg>

      <div style={{ position: 'relative', height: totalHeight }}>
        {seasons.map((season) => {
          const cy = seasonCy.get(season)!;
          const events = seasonMap.get(season) ?? [];
          const isEmpty = events.length === 0;
          const isChampionshipSeason = events.some((event) => event.weight === 'championship');
          const dots = seasonDots.get(season) ?? [];

          return (
            <div key={`labels-${season}`}>
              <div
                style={{
                  position: 'absolute',
                  left: 0,
                  width: TRUNK_X - 6,
                  textAlign: 'right',
                  top: cy - 7,
                  fontSize: '0.6rem',
                  color: isChampionshipSeason ? '#fb923c' : isEmpty ? '#334155' : '#64748b',
                  fontWeight: isChampionshipSeason ? 700 : 400,
                  fontStyle: isEmpty ? 'italic' : 'normal',
                  whiteSpace: 'nowrap',
                }}
              >
                {formatSeasonLabel(season)}
              </div>

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
                  No milestones
                </div>
              )}

              {dots.map((dot, dotIndex) => (
                <div
                  key={`text-${season}-${dotIndex}`}
                  style={{
                    position: 'absolute',
                    left: dot.cx,
                    top: dot.cy + dot.r + 4,
                    transform: 'translateX(-50%)',
                    fontSize: '0.55rem',
                    color: dot.colors.stroke,
                    whiteSpace: 'normal',
                    wordBreak: 'break-word',
                    width: `${DOT_PITCH}px`,
                    fontWeight: dot.event_type === 'championship' ? 700 : 400,
                    textAlign: 'center',
                    lineHeight: 1.2,
                  }}
                >
                  {formatTimelineLabel(dot.label)}
                </div>
              ))}
            </div>
          );
        })}

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
          Present
        </div>
      </div>
    </div>
  );
}
