import { ActionButton } from '../ui';

const COLOR_PRESETS = [
  { label: 'Ocean', primary: '#22d3ee', secondary: '#0f172a' },
  { label: 'Fire',  primary: '#f97316', secondary: '#1e293b' },
  { label: 'Emerald', primary: '#10b981', secondary: '#0f172a' },
  { label: 'Violet', primary: '#8b5cf6', secondary: '#1e293b' },
  { label: 'Rose', primary: '#f43f5e', secondary: '#0f172a' },
  { label: 'Amber', primary: '#f59e0b', secondary: '#1e293b' },
];

type ProgramIdentity = {
  save_name: string;
  club_name: string;
  city: string;
  colors: string;
};

function colorsToValue(primary: string, secondary: string) {
  return `${primary},${secondary}`;
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: '0.6875rem', fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.1em', color: '#64748b', marginBottom: '0.375rem' }}>
        {label}
      </label>
      {children}
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  width: '100%',
  boxSizing: 'border-box',
  background: '#0f172a',
  border: '1px solid #334155',
  borderRadius: '4px',
  padding: '0.5rem 0.75rem',
  color: '#e2e8f0',
  fontSize: '0.875rem',
};

export function IdentityStep({
  identity,
  setIdentity,
  onNext,
}: {
  identity: ProgramIdentity;
  setIdentity: (v: ProgramIdentity) => void;
  onNext: () => void;
}) {
  const currentPrimary = identity.colors?.split(',')[0] ?? '#22d3ee';
  const currentSecondary = identity.colors?.split(',')[1] ?? '#0f172a';
  const selectedPreset = COLOR_PRESETS.find(
    preset => identity.colors === colorsToValue(preset.primary, preset.secondary)
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div>
        <p className="dm-kicker" style={{ marginBottom: '0.25rem' }}>Step 1 of 3</p>
        <h2 style={{ fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.05em', color: '#fff', margin: 0, fontSize: '1.25rem' }}>
          Program Identity
        </h2>
      </div>

      <Field label="Save Name">
        <input
          type="text"
          placeholder="My Career"
          value={identity.save_name}
          onChange={e => setIdentity({ ...identity, save_name: e.target.value })}
          style={inputStyle}
        />
      </Field>

      <Field label="Club Name">
        <input
          type="text"
          placeholder="e.g. Iron Hawks"
          value={identity.club_name}
          onChange={e => setIdentity({ ...identity, club_name: e.target.value })}
          style={inputStyle}
        />
      </Field>

      <Field label="City">
        <input
          type="text"
          placeholder="e.g. Northwood"
          value={identity.city}
          onChange={e => setIdentity({ ...identity, city: e.target.value })}
          style={inputStyle}
        />
      </Field>

      {/* Color picker */}
      <Field label="Club Colors">
        <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
          {COLOR_PRESETS.map(preset => {
            const isSelected = identity.colors === colorsToValue(preset.primary, preset.secondary);
            return (
              <button
                key={preset.label}
                type="button"
                title={preset.label}
                onClick={() => setIdentity({ ...identity, colors: colorsToValue(preset.primary, preset.secondary) })}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.375rem',
                  padding: '0.375rem 0.625rem',
                  background: isSelected ? 'rgba(255,255,255,0.08)' : '#0f172a',
                  border: isSelected ? '1px solid #fff' : '1px solid #334155',
                  borderRadius: '4px',
                  cursor: 'pointer',
                  transition: 'border-color 0.15s',
                }}
              >
                <span style={{ display: 'inline-flex', gap: '2px' }}>
                  <span style={{ width: '12px', height: '12px', borderRadius: '2px', background: preset.primary, display: 'inline-block' }} />
                  <span style={{ width: '12px', height: '12px', borderRadius: '2px', background: preset.secondary, display: 'inline-block', border: '1px solid #1e293b' }} />
                </span>
                <span style={{ fontSize: '0.6875rem', color: isSelected ? '#fff' : '#94a3b8', fontFamily: 'var(--font-display)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  {preset.label}
                </span>
              </button>
            );
          })}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', color: '#94a3b8', fontSize: '0.75rem' }}>
          <div style={{ display: 'flex', borderRadius: '4px', overflow: 'hidden', width: '48px', height: '24px', flexShrink: 0 }}>
            <div style={{ flex: 1, background: currentPrimary }} />
            <div style={{ flex: 1, background: currentSecondary }} />
          </div>
          <span>
            {selectedPreset
              ? `${selectedPreset.label} kit selected`
              : 'Custom kit selected'}
          </span>
        </div>
      </Field>

      {/* Identity preview */}
      {(identity.club_name || identity.city) && (
        <div style={{ background: currentSecondary, border: `1px solid ${currentPrimary}44`, borderLeft: `3px solid ${currentPrimary}`, borderRadius: '4px', padding: '0.75rem 1rem' }}>
          <p className="dm-kicker" style={{ color: currentPrimary, marginBottom: '0.125rem' }}>Preview</p>
          <p style={{ margin: 0, fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: '1rem', color: '#fff', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            {identity.city && <span style={{ color: '#94a3b8', fontSize: '0.75rem', display: 'block', marginBottom: '0.125rem' }}>{identity.city}</span>}
            {identity.club_name || '—'}
          </p>
        </div>
      )}

      <ActionButton
        variant="primary"
        onClick={onNext}
        disabled={!identity.save_name || !identity.club_name || !identity.city}
      >
        Next: Coach Profile
      </ActionButton>
    </div>
  );
}
