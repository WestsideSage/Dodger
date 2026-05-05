import type { KeyboardEvent, ReactNode } from 'react';

export type Tone = 'neutral' | 'accent' | 'success' | 'warning' | 'danger' | 'info';

const toneClasses: Record<Tone, string> = {
  neutral: 'bg-[var(--color-paper)] text-[var(--color-charcoal)] border-[var(--color-border)]',
  accent: 'bg-[var(--color-brick)] text-[var(--color-paper)] border-[var(--color-border)]',
  success: 'bg-[var(--color-sage)] text-[var(--color-paper)] border-[var(--color-border)]',
  warning: 'bg-[var(--color-mustard)] text-[var(--color-charcoal)] border-[var(--color-border)]',
  danger: 'bg-[var(--color-danger)] text-[var(--color-paper)] border-[var(--color-border)]',
  info: 'bg-[var(--color-gym)] text-[var(--color-paper)] border-[var(--color-border)]',
};

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <section className={`bg-[var(--color-paper)] border border-[var(--color-border)] rounded-md shadow-[var(--shadow-panel)] ${className}`}>
      {children}
    </section>
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
    <div className="dashboard-header">
      <div className="min-w-0">
        {eyebrow && (
          <div className="font-display uppercase tracking-[0.18em] text-[11px] text-[var(--color-brick)] mb-1">
            {eyebrow}
          </div>
        )}
        <h2 className="text-2xl md:text-3xl font-display uppercase tracking-widest text-[var(--color-charcoal)]">
          {title}
        </h2>
        {description && <p className="text-sm text-[var(--color-muted)] max-w-2xl mt-1">{description}</p>}
      </div>
      {(actions || stats) && (
        <div className="flex flex-wrap items-end justify-start md:justify-end gap-2">
          {stats}
          {actions}
        </div>
      )}
    </div>
  );
}

export function ActionButton({
  children,
  variant = 'secondary',
  className = '',
  ...props
}: {
  children: ReactNode;
  variant?: 'primary' | 'accent' | 'secondary' | 'danger' | 'ghost';
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const variants = {
    primary: 'bg-[var(--color-gym)] text-[var(--color-paper)] hover:bg-[var(--color-teal)]',
    accent: 'bg-[var(--color-brick)] text-[var(--color-paper)] hover:bg-[var(--color-orange)]',
    secondary: 'bg-[var(--color-paper)] text-[var(--color-charcoal)] hover:bg-[var(--color-cream)]',
    danger: 'bg-[var(--color-danger)] text-[var(--color-paper)] hover:bg-[var(--color-brick)]',
    ghost: 'bg-transparent text-[var(--color-charcoal)] hover:bg-[var(--color-line)]',
  };

  return (
    <button
      {...props}
      className={`inline-flex min-h-10 items-center justify-center rounded-md border border-[var(--color-border)] px-4 py-2 font-display uppercase tracking-wider text-xs transition-all duration-150 shadow-[var(--shadow-button)] cursor-pointer disabled:cursor-not-allowed disabled:opacity-45 disabled:hover:bg-[inherit] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--color-brick)] ${variants[variant]} ${className}`}
    >
      {children}
    </button>
  );
}

export function Badge({ children, tone = 'neutral', className = '' }: { children: ReactNode; tone?: Tone; className?: string }) {
  return (
    <span className={`inline-flex items-center rounded-sm border px-2 py-0.5 font-display uppercase tracking-wider text-[10px] leading-4 ${toneClasses[tone]} ${className}`}>
      {children}
    </span>
  );
}

export function StatChip({ label, value, tone = 'neutral' }: { label: string; value: string | number; tone?: Tone }) {
  return (
    <div className={`inline-flex min-w-20 flex-col rounded-md border px-3 py-2 shadow-[var(--shadow-button)] ${toneClasses[tone]}`}>
      <span className="text-[10px] uppercase tracking-wider opacity-75 font-display">{label}</span>
      <span className="text-sm font-bold leading-tight">{value}</span>
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
  const border = tone === 'danger' ? 'border-[var(--color-danger)]' : 'border-[var(--color-border)]';
  return (
    <div className={`rounded-md border ${border} bg-[var(--color-paper)] p-4 shadow-[var(--shadow-panel)]`}>
      <div className="font-display uppercase tracking-widest text-xs text-[var(--color-brick)]">{title}</div>
      {children && <div className="mt-1 text-sm text-[var(--color-muted)]">{children}</div>}
    </div>
  );
}

export function KeyValueRow({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="grid grid-cols-[minmax(96px,0.8fr)_minmax(0,1fr)] gap-3 border-b border-[var(--color-line)] py-2 text-sm last:border-0">
      <span className="font-display uppercase tracking-wider text-[11px] text-[var(--color-muted)]">{label}</span>
      <span className="min-w-0 text-right font-bold text-[var(--color-charcoal)]">{value}</span>
    </div>
  );
}

export function CompactList({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`overflow-hidden rounded-md border border-[var(--color-border)] bg-[var(--color-paper)] shadow-[var(--shadow-panel)] ${className}`}>
      {children}
    </div>
  );
}

export function CompactListRow({ children, highlight = false, className = '' }: { children: ReactNode; highlight?: boolean; className?: string }) {
  return (
    <div className={`border-b border-[var(--color-line)] p-3 last:border-0 ${highlight ? 'bg-[var(--color-cream)]' : 'hover:bg-[var(--color-cream)]'} ${className}`}>
      {children}
    </div>
  );
}

export function DataTable({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <div className={`overflow-x-auto rounded-md border border-[var(--color-border)] bg-[var(--color-paper)] shadow-[var(--shadow-panel)] ${className}`}>
      <table className="w-full border-collapse text-left text-sm">
        {children}
      </table>
    </div>
  );
}

export function TableHeadCell({ children, align = 'left', sticky = false }: { children: ReactNode; align?: 'left' | 'center' | 'right'; sticky?: boolean }) {
  const alignClass = align === 'center' ? 'text-center' : align === 'right' ? 'text-right' : 'text-left';
  return (
    <th className={`border-b border-r border-[var(--color-border)] bg-[var(--color-cream)] p-2 font-display uppercase tracking-wider text-[11px] text-[var(--color-muted)] last:border-r-0 ${alignClass} ${sticky ? 'sticky left-0 z-10' : ''}`}>
      {children}
    </th>
  );
}

export function TableCell({ children, align = 'left', sticky = false, className = '' }: { children: ReactNode; align?: 'left' | 'center' | 'right'; sticky?: boolean; className?: string }) {
  const alignClass = align === 'center' ? 'text-center' : align === 'right' ? 'text-right' : 'text-left';
  return (
    <td className={`border-r border-[var(--color-line)] p-2 last:border-r-0 ${alignClass} ${sticky ? 'sticky left-0 z-10 bg-inherit' : ''} ${className}`}>
      {children}
    </td>
  );
}

export function RatingBar({ rating, max = 100, label, compact = false }: { rating: number; max?: number; label?: string; compact?: boolean }) {
  const percentage = Math.min(100, Math.max(0, (rating / max) * 100));

  let color = 'var(--color-danger)';
  if (percentage >= 80) color = 'var(--color-teal)';
  else if (percentage >= 60) color = 'var(--color-sage)';
  else if (percentage >= 40) color = 'var(--color-mustard)';
  else if (percentage >= 20) color = 'var(--color-orange)';

  return (
    <div className="flex w-full flex-col gap-1">
      {label && (
        <div className="flex justify-between text-xs font-display tracking-wider text-[var(--color-muted)] uppercase">
          <span>{label}</span>
          <span>{Math.round(rating)}</span>
        </div>
      )}
      <div className={`${compact ? 'h-1.5' : 'h-2'} w-full overflow-hidden rounded-full bg-[var(--color-line)]`}>
        <div
          className="h-full rounded-full transition-all duration-300"
          style={{ width: `${percentage}%`, backgroundColor: color }}
        />
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
    <div className="rounded-md border border-[var(--color-border)] bg-[var(--color-paper)] p-4 shadow-[var(--shadow-button)] transition-transform duration-150 hover:-translate-y-0.5">
      <label className="flex justify-between gap-3 items-end">
        <span className="font-display uppercase tracking-widest text-sm text-[var(--color-charcoal)]">{label}</span>
        <span className="rounded-sm bg-[var(--color-cream)] px-2 py-0.5 text-xs font-bold text-[var(--color-muted)]">{percentage}%</span>
      </label>
      {description && <p className="text-xs text-[var(--color-muted)] mt-2 min-h-8">{description}</p>}

      <div className="relative pt-3">
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
          className="tactic-range w-full cursor-pointer"
        />
        <div className="flex justify-between mt-1 text-[10px] uppercase text-[var(--color-muted)] font-display tracking-wider">
          <span>{leftLabel}</span>
          <span>{rightLabel}</span>
        </div>
      </div>
    </div>
  );
}
