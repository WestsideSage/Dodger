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

  it('keeps the SHARED command-action-bar global (P8-only deletion) and renders the stage', () => {
    const { container } = mount();
    expect(container.querySelector('.command-action-bar')).not.toBeNull();
    expect(screen.getByTestId('stage-body')).toBeInTheDocument();
  });

  it('renders the shared offseason progress pip strip from beatIndex/totalBeats', () => {
    const { container } = mount();
    const strip = container.querySelector('.command-offseason-progress');
    expect(strip).not.toBeNull();
    // 5 pips, first 3 (indices 0..beatIndex=2) active
    expect(strip!.querySelectorAll('.command-offseason-progress-step').length).toBe(5);
    expect(strip!.querySelectorAll('.command-offseason-progress-step-active').length).toBe(3);
  });

  it('announces the action-available transition via role=status (kept non-visual a11y hook)', () => {
    mount({ stages: 0, actionDescription: 'Continue to the next offseason beat.' });
    expect(screen.getByRole('status')).toHaveTextContent('Continue to the next offseason beat.');
  });
});
