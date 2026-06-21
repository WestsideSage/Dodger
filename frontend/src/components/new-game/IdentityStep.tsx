import type { CSSProperties } from 'react';
import { ActionButton } from '../../ui';
import styles from './IdentityStep.module.css';

// token-gate: COLOR_PRESETS is kit DATA, not theme
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

function Field({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className={styles.fieldLabel}>
        {label}
      </label>
      {children}
    </div>
  );
}

export function IdentityStep({
  identity,
  setIdentity,
  onNext,
  onBack,
  takenNames = [],
}: {
  identity: ProgramIdentity;
  setIdentity: (v: ProgramIdentity) => void;
  onNext: () => void;
  onBack: () => void;
  /** Existing save names; used to block a duplicate up front (2.7). */
  takenNames?: string[];
}) {
  const currentPrimary = identity.colors?.split(',')[0] ?? COLOR_PRESETS[0].primary;
  const currentSecondary = identity.colors?.split(',')[1] ?? COLOR_PRESETS[0].secondary;
  const missingFields: string[] = [];
  if (!identity.save_name.trim()) missingFields.push('save name');
  if (!identity.club_name.trim()) missingFields.push('club name');
  if (!identity.city.trim()) missingFields.push('city');
  // 2.7: validate save-name uniqueness on Step 1 so the collision surfaces
  // here with a visible banner — not silently at Commit on the final step.
  const trimmedName = identity.save_name.trim().toLowerCase();
  const nameTaken =
    trimmedName.length > 0 &&
    takenNames.some(n => n.trim().toLowerCase() === trimmedName);
  const canContinue = missingFields.length === 0 && !nameTaken;
  const selectedPreset = COLOR_PRESETS.find(
    preset => identity.colors === colorsToValue(preset.primary, preset.secondary)
  );

  // The chosen kit colors are user DATA painted into the chrome — carried as
  // custom properties (not raw style literals) and consumed by the module CSS.
  const previewKitVars = {
    ['--kit-primary' as string]: currentPrimary,
    ['--kit-secondary' as string]: currentSecondary,
  } as CSSProperties;

  return (
    <div className={styles.wrap}>
      <div className={styles.header}>
        <p className={styles.kicker}>Step 1 of 4</p>
        <h2 className={styles.title}>Program Identity</h2>
      </div>

      <Field label="Save Name" htmlFor="identity-save-name">
        <input
          id="identity-save-name"
          type="text"
          placeholder="My Career"
          value={identity.save_name}
          onChange={e => setIdentity({ ...identity, save_name: e.target.value })}
          aria-invalid={nameTaken}
          aria-describedby={nameTaken ? 'identity-save-name-error' : undefined}
          className={`${styles.input} ${nameTaken ? styles.inputInvalid : ''}`.trim()}
        />
        {nameTaken && (
          <div
            id="identity-save-name-error"
            role="alert"
            data-testid="save-name-collision-banner"
            className={styles.collisionBanner}
          >
            A save named “{identity.save_name.trim()}” already exists. Choose a different name to continue.
          </div>
        )}
      </Field>

      <Field label="Club Name" htmlFor="identity-club-name">
        <input
          id="identity-club-name"
          type="text"
          placeholder="e.g. Iron Hawks"
          value={identity.club_name}
          onChange={e => setIdentity({ ...identity, club_name: e.target.value })}
          className={styles.input}
        />
      </Field>

      <Field label="City" htmlFor="identity-city">
        <input
          id="identity-city"
          type="text"
          placeholder="e.g. Northwood"
          value={identity.city}
          onChange={e => setIdentity({ ...identity, city: e.target.value })}
          className={styles.input}
        />
      </Field>

      <fieldset className={styles.fieldset}>
        <legend className={styles.legend}>Club Colors</legend>
        <div className={styles.presetRow}>
          {COLOR_PRESETS.map(preset => {
            const isSelected = identity.colors === colorsToValue(preset.primary, preset.secondary);
            return (
              <button
                key={preset.label}
                type="button"
                aria-pressed={isSelected}
                title={preset.label}
                onClick={() => setIdentity({ ...identity, colors: colorsToValue(preset.primary, preset.secondary) })}
                className={`${styles.presetBtn} ${isSelected ? styles.presetBtnSelected : ''}`.trim()}
              >
                <span className={styles.swatchPair}>
                  <span
                    className={`${styles.swatch} ${styles.swatchPrimary}`}
                    style={{ ['--kit-primary' as string]: preset.primary } as CSSProperties}
                  />
                  <span
                    className={`${styles.swatch} ${styles.swatchSecondary}`}
                    style={{ ['--kit-secondary' as string]: preset.secondary } as CSSProperties}
                  />
                </span>
                <span className={`${styles.presetLabel} ${isSelected ? styles.presetLabelSelected : ''}`.trim()}>
                  {preset.label}
                </span>
              </button>
            );
          })}
        </div>

        <div className={styles.kitPreview}>
          <div className={styles.kitChip} style={previewKitVars}>
            <div className={styles.kitChipPrimary} />
            <div className={styles.kitChipSecondary} />
          </div>
          <span>
            {selectedPreset
              ? `${selectedPreset.label} kit selected`
              : 'Custom kit selected'}
          </span>
        </div>
      </fieldset>

      {(identity.club_name || identity.city) && (
        <div className={styles.previewCard} data-testid="identity-preview" style={previewKitVars}>
          <p className={styles.previewKicker}>Preview</p>
          <p className={styles.previewName}>
            {identity.city && <span className={styles.previewCity}>{identity.city}</span>}
            {identity.club_name || '-'}
          </p>
        </div>
      )}

      <div className={styles.actions}>
        <div className={styles.actionRow}>
          <ActionButton variant="secondary" onClick={onBack}>Back</ActionButton>
          <ActionButton
            variant="primary"
            onClick={onNext}
            disabled={!canContinue}
            aria-describedby="identity-step-help"
          >
            Next: Coach Profile
          </ActionButton>
        </div>
        {missingFields.length > 0 && (
          <p id="identity-step-help" className={styles.helperWarning}>
            Add a {missingFields.join(', ').replace(/, ([^,]*)$/, ' and $1')} to continue.
          </p>
        )}
      </div>
    </div>
  );
}
