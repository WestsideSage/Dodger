import type { HTMLAttributes, KeyboardEvent, ReactNode } from 'react';

export type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

// Maps Tone to dm-badge modifier classes
const toneBadgeClass: Record<Tone, string> = {
  neutral: '',
  accent: 'dm-badge-cyan',
  success: 'dm-badge-emerald',
  warning: 'dm-badge-amber',
  danger: 'dm-badge-rose',
  info: 'dm-badge-violet',
};

// Maps Tone to border color for StatusMessage
const toneBorderColor: Record<Tone, string> = {
  neutral: '#1e293b',
  accent: 'rgba(34,211,238,0.3)',
  success: 'rgba(16,185,129,0.3)',
  warning: 'rgba(245,158,11,0.3)',
  danger: 'rgba(244,63,94,0.4)',
  info: 'rgba(139,92,246,0.3)',
};

const toneKickerColor: Record<Tone, string> = {
  neutral: '#64748b',
  accent: '#22d3ee',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#f43f5e',
  info: '#8b5cf6',
};

export function Card({ children, className = '', ...props }: { children: ReactNode; className?: string } & HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={`dm-panel ${className}`}>{children}</div>;
}

export function Tile({ children, className = '', style, as: Component = 'div', ...rest }: { children: ReactNode; className?: string; style?: React.CSSProperties; as?: React.ElementType; disabled?: boolean } & React.HTMLAttributes<HTMLElement>) {
  return (
    <Component
      className={className}
      style={{
        borderRadius: '4px',
        border: '1px solid #1e293b',
        background: '#0f172a',
        padding: '0.75rem',
        ...style,
      }}
      {...rest}
    >
      {children}
    </Component>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
  stats,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  stats?: ReactNode;
}) {
  return (
    <div className="dm-panel-header" style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {eyebrow && <p className="dm-kicker">{eyebrow}</p>}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
        <div>
          <h2 className="dm-panel-title">{title}</h2>
          {description && <p className="dm-panel-subtitle">{description}</p>}
        </div>
        {actions && (
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>{actions}</div>
        )}
      </div>
      {stats && (
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', marginTop: '0.25rem' }}>{stats}</div>
      )}
    </div>
  );
}

const variantStyles: Record<string, React.CSSProperties> = {
  primary: {
    background: '#f97316',
    color: '#fff',
    border: '1px solid #ea6c0a',
    fontFamily: 'var(--font-display)',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  accent: {
    background: 'rgba(34,211,238,0.10)',
    color: '#22d3ee',
    border: '1px solid rgba(34,211,238,0.3)',
    fontFamily: 'var(--font-mono-data)',
  },
  secondary: {
    background: '#1e293b',
    color: '#cbd5e1',
    border: '1px solid #334155',
    fontFamily: 'var(--font-body)',
  },
  danger: {
    background: 'rgba(244,63,94,0.10)',
    color: '#f43f5e',
    border: '1px solid rgba(244,63,94,0.3)',
    fontFamily: 'var(--font-body)',
  },
  ghost: {
    background: 'transparent',
    color: '#94a3b8',
    border: '1px solid transparent',
    fontFamily: 'var(--font-body)',
  },
};

export function ActionButton({
  children,
  variant = 'secondary',
  className = '',
  style,
  ...props
}: {
  children: ReactNode;
  variant?: 'primary' | 'accent' | 'secondary' | 'danger' | 'ghost';
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    minHeight: '2.5rem',
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: '4px',
    padding: '0.375rem 1rem',
    fontSize: '0.6875rem',
    letterSpacing: '0.075em',
    cursor: 'pointer',
    transition: 'all 0.15s',
    textTransform: 'uppercase',
    fontWeight: 600,
    ...variantStyles[variant],
    ...style,
  };

  return (
    <button
      {...props}
      className={className}
      style={baseStyle}
    >
      {children}
    </button>
  );
}

export function Badge({ children, tone = 'neutral', className = '' }: { children: ReactNode; tone?: Tone; className?: string }) {
  const modifier = toneBadgeClass[tone];
  return (
    <span className={`dm-badge ${modifier} ${className}`.trim()}>
      {children}
    </span>
  );
}

export function StatChip({ label, value, tone = 'neutral' }: { label: string; value: string | number; tone?: Tone }) {
  // tone is accepted for API compatibility; value color uses white for all tones
  void tone;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.125rem' }}>
      <span className="dm-data" style={{ fontSize: '1rem', fontWeight: 600, color: '#fff' }}>{value}</span>
      <span style={{ fontSize: '0.625rem', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#64748b', fontFamily: 'var(--font-display)' }}>{label}</span>
    </div>
  );
}

export function StatusMessage({
  title,
  children,
  tone = 'info',
}: {
  title: string;
  children?: ReactNode;
  tone?: Tone;
}) {
  return (
    <div style={{
      background: '#0f172a',
      border: `1px solid ${toneBorderColor[tone]}`,
      borderRadius: '4px',
      padding: '1rem',
    }}>
      <div className="dm-kicker" style={{ color: toneKickerColor[tone] }}>{title}</div>
      {children && (
        <div style={{ marginTop: '0.25rem', fontSize: '0.875rem', color: '#94a3b8', fontFamily: 'var(--font-body)' }}>
          {children}
        </div>
      )}
    </div>
  );
}

export function KeyValueRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'minmax(96px, 0.8fr) minmax(0, 1fr)',
      gap: '0.75rem',
      borderBottom: '1px solid #1e293b',
      padding: '0.5rem 0',
      fontSize: '0.875rem',
    }}
      className="last:border-0"
    >
      <span style={{ fontFamily: 'var(--font-display)', fontSize: '0.6875rem', textTransform: 'uppercase', letterSpacing: '0.075em', color: '#64748b' }}>{label}</span>
      <span style={{ minWidth: 0, textAlign: 'right', fontWeight: 700, color: '#e2e8f0' }}>{value}</span>
    </div>
  );
}

export function CompactList({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`dm-panel ${className}`} style={{ overflow: 'hidden' }}>
      {children}
    </div>
  );
}

export function CompactListRow({ children, highlight = false, className = '' }: { children: ReactNode; highlight?: boolean; className?: string }) {
  return (
    <div
      className={className}
      style={{
        borderBottom: '1px solid rgba(30,41,59,0.7)',
        padding: '0.75rem',
        background: highlight ? 'rgba(30,41,59,0.5)' : undefined,
        transition: 'background 0.1s',
      }}
      onMouseEnter={e => { if (!highlight) (e.currentTarget as HTMLDivElement).style.background = 'rgba(30,41,59,0.5)'; }}
      onMouseLeave={e => { if (!highlight) (e.currentTarget as HTMLDivElement).style.background = 'transparent'; }}
    >
      {children}
    </div>
  );
}

export function DataTable({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className={`dm-table ${className}`.trim()}>{children}</table>
    </div>
  );
}

export function TableHeadCell({ children, align = 'left', sticky = false }: { children: ReactNode; align?: 'left' | 'center' | 'right'; sticky?: boolean }) {
  return (
    <th
      style={{
        textAlign: align,
        position: sticky ? 'sticky' : undefined,
        left: sticky ? 0 : undefined,
        background: sticky ? '#020617' : undefined,
        zIndex: sticky ? 10 : undefined,
      }}
    >
      {children}
    </th>
  );
}

export function TableCell({ children, align = 'left', sticky = false, className = '' }: { children: ReactNode; align?: 'left' | 'center' | 'right'; sticky?: boolean; className?: string }) {
  return (
    <td
      className={className}
      style={{
        textAlign: align,
        position: sticky ? 'sticky' : undefined,
        left: sticky ? 0 : undefined,
        background: sticky ? '#0f172a' : undefined,
        fontWeight: sticky ? 600 : undefined,
        color: sticky ? '#fff' : '#cbd5e1',
        zIndex: sticky ? 10 : undefined,
      }}
    >
      {children}
    </td>
  );
}

export function RatingBar({ rating, max = 100, label, compact = false }: { rating: number; max?: number; label?: string; compact?: boolean }) {
  const percentage = Math.min(100, Math.max(0, (rating / max) * 100));

  let color = '#f43f5e'; // rose — poor
  if (percentage >= 80) color = '#22d3ee'; // cyan — elite
  else if (percentage >= 60) color = '#10b981'; // emerald — good
  else if (percentage >= 40) color = '#f59e0b'; // amber — average

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', width: '100%' }}>
      {label && (
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontFamily: 'var(--font-display)', letterSpacing: '0.075em', color: '#64748b', textTransform: 'uppercase' }}>
          <span>{label}</span>
          <span>{Math.round(rating)}</span>
        </div>
      )}
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        {!label && (
          <span className="dm-data" style={{ fontSize: '0.875rem', color: '#e2e8f0', minWidth: '1.75rem', textAlign: 'right', flexShrink: 0 }}>{Math.round(rating)}</span>
        )}
        <div
          className="dm-stat-bar-track"
          style={{ flex: 1, height: compact ? '0.375rem' : '0.5rem' }}
        >
          <div style={{ height: '100%', width: `${percentage}%`, background: color, transition: 'width 0.3s' }} />
        </div>
      </div>
    </div>
  );
}

export function TendencySlider({
  label,
  value,
  onChange,
  leftLabel = 'Low',
  rightLabel = 'High',
  description
}: {
  label: string;
  value: number;
  onChange: (val: number) => void;
  leftLabel?: string;
  rightLabel?: string;
  description?: string;
}) {
  const percentage = Math.round(value * 100);
  const setClampedValue = (nextValue: number) => onChange(Math.min(1, Math.max(0, nextValue)));
  const handleChange = (nextValue: string) => setClampedValue(parseFloat(nextValue));
  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    const step = event.shiftKey ? 0.1 : 0.01;
    if (event.key === 'ArrowRight' || event.key === 'ArrowUp') {
      event.preventDefault();
      setClampedValue(value + step);
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') {
      event.preventDefault();
      setClampedValue(value - step);
    } else if (event.key === 'Home') {
      event.preventDefault();
      setClampedValue(0);
    } else if (event.key === 'End') {
      event.preventDefault();
      setClampedValue(1);
    }
  };

  return (
    <div className="dm-tactic-slider">
      <label style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'flex-end' }}>
        <span style={{ fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.1em', fontSize: '0.875rem', color: '#e2e8f0' }}>{label}</span>
        <span className="dm-badge dm-badge-slate">{percentage}%</span>
      </label>
      {description && (
        <p style={{ fontSize: '0.75rem', color: '#64748b', marginTop: '0.5rem', minHeight: '2rem', fontFamily: 'var(--font-body)' }}>{description}</p>
      )}
      <div style={{ position: 'relative', paddingTop: '0.75rem' }}>
        <input
          aria-label={label}
          data-testid={`tactic-${label.toLowerCase().replaceAll(' ', '-')}`}
          type="range"
          min="0"
          max="1"
          step="0.01"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          onInput={(e) => handleChange(e.currentTarget.value)}
          onKeyDown={handleKeyDown}
          className="tactic-range"
          style={{ width: '100%', cursor: 'pointer' }}
        />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.25rem', fontSize: '0.625rem', textTransform: 'uppercase', color: '#475569', fontFamily: 'var(--font-display)', letterSpacing: '0.1em' }}>
          <span>{leftLabel}</span>
          <span>{rightLabel}</span>
        </div>
      </div>
    </div>
  );
}
