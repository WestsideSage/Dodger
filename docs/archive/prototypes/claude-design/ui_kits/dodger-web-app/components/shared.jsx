/* Shared atomic primitives. Exposed on window for cross-script consumption. */

const Kicker = ({ children, color = 'cyan', as: As = 'p', style = {} }) => (
  <As
    className="dm-kicker"
    style={{
      color: color === 'cyan' ? 'var(--dm-cyan)' : color === 'orange' ? 'var(--dm-orange-hover)' : color === 'amber' ? 'var(--dm-amber-bright)' : 'var(--dm-text-muted)',
      ...style,
    }}
  >
    {children}
  </As>
);

const Badge = ({ children, tone = 'slate', style = {} }) => (
  <span className={`dm-badge dm-badge-${tone}`} style={style}>{children}</span>
);

const Button = ({ children, variant = 'secondary', onClick, disabled, style = {} }) => {
  const className = ['dm-btn'];
  if (variant === 'primary') className.push('dm-btn-primary');
  if (variant === 'ghost') className.push('dm-btn-ghost');
  return (
    <button className={className.join(' ')} onClick={onClick} disabled={disabled} style={style}>
      {children}
    </button>
  );
};

const Panel = ({ title, kicker, subtitle, children, accent, style = {}, headerRight }) => {
  const cardStyle = { ...style };
  if (accent === 'cyan')   cardStyle.borderLeft = `2px solid var(--dm-cyan)`;
  if (accent === 'orange') cardStyle.borderLeft = `2px solid var(--dm-orange)`;
  if (accent === 'amber')  cardStyle.borderLeft = `2px solid var(--dm-amber)`;
  return (
    <div className="dm-panel" style={cardStyle}>
      {(title || kicker) && (
        <div className="dm-panel-header" style={{ display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap:'1rem' }}>
          <div>
            {kicker && <Kicker style={{ marginBottom: 4 }}>{kicker}</Kicker>}
            {title && <div className="dm-panel-title">{title}</div>}
            {subtitle && <div className="dm-panel-subtitle" style={{ color: 'var(--dm-text-muted)', fontSize: '0.82rem', marginTop: 4 }}>{subtitle}</div>}
          </div>
          {headerRight}
        </div>
      )}
      {children}
    </div>
  );
};

const StatChip = ({ label, value, tone }) => {
  const valueStyle = {};
  if (tone === 'info')   valueStyle.color = 'var(--dm-cyan)';
  if (tone === 'orange') valueStyle.color = 'var(--dm-orange-hover)';
  return (
    <div className="dm-stat-chip">
      <span className="label">{label}</span>
      <span className="value" style={valueStyle}>{value}</span>
    </div>
  );
};

const ratingTier = (v) => {
  if (v >= 85) return 'elite';
  if (v >= 70) return 'good';
  if (v >= 55) return 'avg';
  return 'poor';
};

const RatingBar = ({ label, value }) => {
  const tier = ratingTier(value);
  return (
    <div className="dm-rating" data-tier={tier === 'avg' ? 'average' : tier === 'good' ? 'good' : tier}>
      <span className="label">{label}</span>
      <span className="value">{value}</span>
      <span className="track"><span className="fill" style={{ width: `${value}%` }}></span></span>
    </div>
  );
};

const PotentialBadge = ({ tier, confidence }) => {
  const glyphs = { Elite: '★', High: '◆', Solid: '»', Limited: '⬡' };
  const colorClass = { Elite: 'gem-elite', High: 'gem-high', Solid: 'gem-solid', Limited: 'gem-limited' }[tier] || 'gem-limited';
  const stars = '★'.repeat(confidence || 0) + '☆'.repeat(Math.max(0, 4 - (confidence || 0)));
  return (
    <div className="potential-cell">
      <span className={`gem ${colorClass}`}>{glyphs[tier] || '·'}</span>
      <div>
        <div className="name" style={{ color: colorClass === 'gem-elite' ? '#facc15' : colorClass === 'gem-high' ? 'var(--dm-cyan)' : colorClass === 'gem-solid' ? '#84cc16' : '#94a3b8' }}>{tier}</div>
        <div className="conf">{stars}</div>
      </div>
    </div>
  );
};

Object.assign(window, { Kicker, Badge, Button, Panel, StatChip, RatingBar, PotentialBadge, ratingTier });
