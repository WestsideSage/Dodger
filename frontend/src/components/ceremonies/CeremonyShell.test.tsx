import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { CeremonyShell } from './CeremonyShell';

describe('CeremonyShell (shared offseason chrome — anti-strip)', () => {
  function mount(extra?: Partial<Parameters<typeof CeremonyShell>[0]>) {
    return render(
      <CeremonyShell
        title="Awards Night"
        eyebrow="Awards Night"
        description="The league gathers."
        stages={0}
        renderStage={() => <div data-testid="stage-body">body</div>}
        onComplete={() => {}}
        beatIndex={2}
        totalBeats={5}
        {...extra}
      />,
    );
  }

  it('renders the shared offseason action bar (now a CSS Module) and the stage', () => {
    const { container } = mount();
    // The action bar moved from the global `command-action-bar` class to
    // components/chrome.module.css; CSS-Modules hash keeps the name as a substring.
    expect(container.querySelector('[class*="actionBar"]')).not.toBeNull();
    expect(screen.getByTestId('stage-body')).toBeInTheDocument();
  });

  it('renders the shared offseason progress pip strip from beatIndex/totalBeats', () => {
    const { container } = mount();
    const strip = container.querySelector('[aria-label="Offseason beat progress"]');
    expect(strip).not.toBeNull();
    // 5 pips, first 3 (indices 0..beatIndex=2) active
    expect(strip!.querySelectorAll('[class*="offseasonProgressStep"]').length).toBe(5);
    expect(strip!.querySelectorAll('[class*="offseasonProgressStepActive"]').length).toBe(3);
  });

  it('announces the action-available transition via role=status (kept non-visual a11y hook)', () => {
    mount({ stages: 0, actionDescription: 'Continue to the next offseason beat.' });
    expect(screen.getByRole('status')).toHaveTextContent('Continue to the next offseason beat.');
  });
});
