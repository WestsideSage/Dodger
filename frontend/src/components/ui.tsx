import { useEffect, useRef, useState } from 'react';
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

export function ActionButton({
  children,
  variant = 'secondary',
  className = '',
  style,
  type,
  ...props
}: {
  children: ReactNode;
  variant?: 'primary' | 'accent' | 'secondary' | 'danger' | 'ghost';
  className?: string;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  // Visual treatment (palette, hover, active, disabled) lives in the
  // .dm-action / .dm-action-<variant> CSS so every button gets real
  // interaction feedback; `style` remains a layout-override escape hatch.
  return (
    <button
      {...props}
      type={type ?? 'button'}
      className={`dm-action dm-action-${variant} ${className}`.trim()}
      style={style}
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
  role,
}: {
  title: string;
  children?: ReactNode;
  tone?: Tone;
  // WT-21: announce status/errors to assistive tech. When omitted, the role is
  // derived from tone so existing call sites get a sensible default without an
  // API change — danger/warning blockers are asserted (role="alert"), and the
  // calmer states (loading, info) are announced politely (role="status").
  role?: 'status' | 'alert';
}) {
  const resolvedRole: 'status' | 'alert' =
    role ?? (tone === 'danger' || tone === 'warning' ? 'alert' : 'status');
  // role="alert" already implies aria-live="assertive"; role="status" implies
  // "polite". We set aria-live explicitly so screen readers that don't map the
  // role to a live region still announce the message.
  const ariaLive: 'assertive' | 'polite' = resolvedRole === 'alert' ? 'assertive' : 'polite';
  return (
    <div
      role={resolvedRole}
      aria-live={ariaLive}
      style={{
        background: '#0f172a',
        border: `1px solid ${toneBorderColor[tone]}`,
        borderRadius: '4px',
        padding: '1rem',
      }}
    >
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
      className="kv-row"
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

export function RatingBar({ rating, max = 100, label, compact = false, explanation }: { rating: number; max?: number; label?: string; compact?: boolean; explanation?: string }) {
  const percentage = Math.min(100, Math.max(0, (rating / max) * 100));
  const [showInfo, setShowInfo] = useState(false);

  let color = '#f43f5e'; // rose — poor
  if (percentage >= 80) color = '#22d3ee'; // cyan — elite
  else if (percentage >= 60) color = '#10b981'; // emerald — good
  else if (percentage >= 40) color = '#f59e0b'; // amber — average

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', width: '100%' }}>
      {label && (
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', fontFamily: 'var(--font-display)', letterSpacing: '0.075em', color: '#64748b', textTransform: 'uppercase' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem' }}>
            {label}
            {explanation && (
              <span
                data-testid="rating-explanation"
                data-explanation-label={label}
                role="button"
                tabIndex={0}
                aria-label={`${label} explanation: ${explanation}`}
                aria-expanded={showInfo}
                title={explanation}
                onMouseEnter={() => setShowInfo(true)}
                onMouseLeave={() => setShowInfo(false)}
                onFocus={() => setShowInfo(true)}
                onBlur={() => setShowInfo(false)}
                onClick={() => setShowInfo((v) => !v)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    setShowInfo((v) => !v);
                  } else if (e.key === 'Escape') {
                    setShowInfo(false);
                  }
                }}
                style={{
                  position: 'relative',
                  display: 'inline-flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  width: '0.9rem',
                  height: '0.9rem',
                  borderRadius: '50%',
                  border: '1px solid #334155',
                  color: '#94a3b8',
                  fontSize: '0.6rem',
                  lineHeight: 1,
                  cursor: 'help',
                  textTransform: 'none',
                  userSelect: 'none',
                }}
              >
                ?
                {showInfo && (
                  <span
                    role="tooltip"
                    style={{
                      position: 'absolute',
                      bottom: 'calc(100% + 6px)',
                      left: 0,
                      zIndex: 20,
                      width: '15rem',
                      padding: '0.5rem 0.6rem',
                      background: '#020617',
                      border: '1px solid #334155',
                      borderRadius: '4px',
                      color: '#cbd5e1',
                      fontSize: '0.7rem',
                      fontFamily: 'var(--font-body, sans-serif)',
                      letterSpacing: 'normal',
                      textTransform: 'none',
                      lineHeight: 1.45,
                      fontWeight: 400,
                      boxShadow: '0 6px 18px rgba(0,0,0,0.5)',
                    }}
                  >
                    {explanation}
                  </span>
                )}
              </span>
            )}
          </span>
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

// WT-21 shared accessible primitives.
// ---------------------------------------------------------------------------
// Selector for the focusable descendants inside a Dialog. Kept module-local
// (not exported) so this file's only exports remain components/types and the
// react-refresh/only-export-components lint rule stays satisfied.
const FOCUSABLE_SELECTOR =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

/**
 * Dialog — the shared modal primitive (WT-21).
 *
 * Behaviour, extracted from the proven FastForwardDialog implementation so
 * every modal gets the same guarantees:
 *   - role="dialog" + aria-modal="true"
 *   - labelled by an existing heading id (`labelledBy`) or a fallback
 *     aria-label (`label`)
 *   - focus moves INTO the dialog on open (a provided `initialFocusRef`, else
 *     the first focusable child, else the dialog container)
 *   - Tab / Shift+Tab are TRAPPED within the dialog
 *   - Escape closes it
 *   - focus is RESTORED to the triggering element on close
 *   - clicking the backdrop closes it (the panel stops propagation)
 *
 * Migrate by WRAPPING: pass the existing header/body/footer through as
 * `children`. The primitive only owns the overlay shell + focus management;
 * it does not restructure inner DOM, so existing testids/roles are preserved.
 */
export function Dialog({
  onClose,
  children,
  label,
  labelledBy,
  describedBy,
  initialFocusRef,
  className,
  panelClassName,
  panelStyle,
  overlayStyle,
  'data-testid': dataTestId,
}: {
  onClose: () => void;
  children: ReactNode;
  /** aria-label fallback when there is no visible heading id to point at. */
  label?: string;
  /** id of the visible heading that titles the dialog (preferred). */
  labelledBy?: string;
  /** id of descriptive copy inside the dialog. */
  describedBy?: string;
  /** focusable element to receive focus on open; defaults to first focusable. */
  initialFocusRef?: React.RefObject<HTMLElement | null>;
  className?: string;
  panelClassName?: string;
  panelStyle?: React.CSSProperties;
  overlayStyle?: React.CSSProperties;
  'data-testid'?: string;
}) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const previouslyFocused = useRef<HTMLElement | null>(null);

  useEffect(() => {
    previouslyFocused.current = document.activeElement as HTMLElement | null;
    // Move focus into the dialog on open: caller-specified target first, then
    // the first focusable child, then the dialog container itself.
    const target =
      initialFocusRef?.current ??
      dialogRef.current?.querySelector<HTMLElement>(FOCUSABLE_SELECTOR) ??
      dialogRef.current;
    target?.focus?.();
    return () => {
      // Restore focus to the trigger when the dialog unmounts/closes.
      previouslyFocused.current?.focus?.();
    };
    // Intentionally run once on mount; the dialog instance owns one open/close
    // lifecycle and re-running on ref identity would steal focus mid-session.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = dialogRef.current?.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    if (!focusable || focusable.length === 0) {
      // Nothing focusable inside — keep focus on the container.
      event.preventDefault();
      dialogRef.current?.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = document.activeElement;
    if (event.shiftKey && active === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && active === last) {
      event.preventDefault();
      first.focus();
    }
  };

  return (
    <div
      className={className}
      role="presentation"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(2, 6, 23, 0.85)',
        backdropFilter: 'blur(4px)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem',
        ...overlayStyle,
      }}
      data-testid={dataTestId}
    >
      <div
        ref={dialogRef}
        className={panelClassName}
        role="dialog"
        aria-modal="true"
        aria-label={labelledBy ? undefined : label}
        aria-labelledby={labelledBy}
        aria-describedby={describedBy}
        tabIndex={-1}
        onClick={(event) => event.stopPropagation()}
        onKeyDown={handleKeyDown}
        style={panelStyle}
      >
        {children}
      </div>
    </div>
  );
}

export type RadioGroupOption<T extends string> = {
  value: T;
  /** What the screen reader announces for this option. */
  label: string;
  /** Visible content for the option control (defaults to `label`). */
  children?: ReactNode;
  disabled?: boolean;
  'data-testid'?: string;
};

/**
 * RadioGroup — the shared single-select primitive (WT-21).
 *
 * Mirrors the proven PolicyEditor radiogroup semantics:
 *   - role="radiogroup" on the container, role="radio" + aria-checked on items
 *   - roving tabindex (only the selected item is tabbable; if none selected,
 *     the first item is tabbable)
 *   - Arrow keys move selection and focus (wrapping); Home/End jump to ends
 *
 * Accepts arbitrary per-option `children` so rich rows (e.g. a club name +
 * tagline) can be selected from the keyboard, not just plain labels. The
 * caller owns rendering each option via `renderOption`, receiving the option
 * plus its selected/focusable state and the props that MUST be spread onto the
 * focusable element. This keeps styling in the consumer while the primitive
 * owns the a11y contract.
 */
export function RadioGroup<T extends string>({
  value,
  onChange,
  options,
  label,
  labelledBy,
  orientation = 'vertical',
  className,
  style,
  renderOption,
}: {
  value: T;
  onChange: (next: T) => void;
  options: ReadonlyArray<RadioGroupOption<T>>;
  label?: string;
  labelledBy?: string;
  orientation?: 'vertical' | 'horizontal';
  className?: string;
  style?: React.CSSProperties;
  renderOption: (args: {
    option: RadioGroupOption<T>;
    selected: boolean;
    radioProps: {
      role: 'radio';
      'aria-checked': boolean;
      tabIndex: number;
      disabled?: boolean;
      onClick: () => void;
      'data-testid'?: string;
    };
  }) => ReactNode;
}) {
  // A single ref on the group container. Focus is moved by querying the
  // semantic radio descendants in DOM order (which matches option order). The
  // ref is only read inside moveTo — an event-handler path, never during
  // render — so the react-hooks/refs rule is honoured without per-item refs.
  const groupRef = useRef<HTMLDivElement>(null);
  const selectedIndex = options.findIndex((o) => o.value === value);
  // If nothing is selected yet, the first option is the tab stop so the group
  // is still reachable by keyboard.
  const tabbableIndex = selectedIndex >= 0 ? selectedIndex : 0;

  // Selecting + focusing the option at an index. Lives inside handleKeyDown
  // (a handler attached directly to the container) so the groupRef read is not
  // inside a render-time closure — it runs only on a real key event.
  const handleKeyDown = (event: KeyboardEvent<HTMLDivElement>) => {
    const count = options.length;
    if (count === 0) return;
    const forwardKeys =
      orientation === 'horizontal' ? ['ArrowRight', 'ArrowDown'] : ['ArrowDown', 'ArrowRight'];
    const backwardKeys =
      orientation === 'horizontal' ? ['ArrowLeft', 'ArrowUp'] : ['ArrowUp', 'ArrowLeft'];
    const current = selectedIndex >= 0 ? selectedIndex : 0;
    let nextIndex: number | null = null;
    if (forwardKeys.includes(event.key)) nextIndex = (current + 1) % count;
    else if (backwardKeys.includes(event.key)) nextIndex = (current - 1 + count) % count;
    else if (event.key === 'Home') nextIndex = 0;
    else if (event.key === 'End') nextIndex = count - 1;
    if (nextIndex === null) return;
    const option = options[nextIndex];
    if (!option || option.disabled) return;
    event.preventDefault();
    onChange(option.value);
    const radios = groupRef.current?.querySelectorAll<HTMLElement>('[role="radio"]');
    radios?.[nextIndex]?.focus();
  };

  return (
    <div
      ref={groupRef}
      role="radiogroup"
      aria-label={labelledBy ? undefined : label}
      aria-labelledby={labelledBy}
      className={className}
      style={style}
      onKeyDown={handleKeyDown}
    >
      {options.map((option, index) => {
        const selected = option.value === value;
        return (
          <div key={option.value} style={{ display: 'contents' }}>
            {renderOption({
              option,
              selected,
              radioProps: {
                role: 'radio',
                'aria-checked': selected,
                tabIndex: index === tabbableIndex ? 0 : -1,
                disabled: option.disabled,
                // Click selects only; the browser focuses the clicked element
                // natively, so no ref access is needed in this render-time
                // closure (keeps react-hooks/refs satisfied).
                onClick: () => { if (!option.disabled) onChange(option.value); },
                'data-testid': option['data-testid'],
              },
            })}
          </div>
        );
      })}
    </div>
  );
}
