import type { OffseasonBeat } from '../../types';
import { CeremonyShell } from './CeremonyShell';

type WorldsChampionBeat = Extract<OffseasonBeat, { key: 'worlds_champion' }>;

// V27 Phase 6: the Worlds crowning ceremony. The save's FIRST Worlds title gets
// the elevated credits-roll treatment (staged reveal via CeremonyShell); later
// crowns render as a quieter defending-champion beat. Presentation only — the
// vision law forbids any post-summit ratchet/NG+ field, so this component never
// reads or implies one. The crowning is a moment, not a power-up.
export function WorldsCrowning({
    beat,
    onComplete,
    acting,
}: {
    beat: WorldsChampionBeat;
    onComplete: () => void;
    acting?: boolean;
}) {
    const { champion_name, is_first, season_id } = beat.payload;

    if (is_first) {
        // Credits-roll energy: a staged reveal that builds to the name, then the
        // title. Four stages so the moment lands without dragging.
        return (
            <CeremonyShell
                title="Worlds Champions"
                eyebrow="The World Stage"
                description="The summit of the pyramid. One club stands above every tier."
                stages={4}
                beatIndex={beat.beat_index}
                totalBeats={beat.total_beats}
                renderStage={(stage) => <FirstCrownStage stage={stage} championName={champion_name} seasonId={season_id} />}
                onComplete={onComplete}
                actionLabel="Continue"
                actionDescription="The banner is raised. Continue to the next offseason beat."
                isActing={acting}
            />
        );
    }

    // Defending champion: a single quiet stage — the crown is retained, not won.
    return (
        <CeremonyShell
            title="Defending Worlds Champions"
            eyebrow="The World Stage"
            description="The crown is retained. The dynasty defends its place at the summit."
            stages={1}
            beatIndex={beat.beat_index}
            totalBeats={beat.total_beats}
            renderStage={() => (
                <div className="champion-stage" data-testid="worlds-defending-stage">
                    <p className="champion-kicker">Worlds Champions</p>
                    <h2 className="champion-name">{champion_name}</h2>
                    <p className="champion-sub">Retained the Worlds title.</p>
                </div>
            )}
            onComplete={onComplete}
            actionLabel="Continue"
            actionDescription="Continue to the next offseason beat."
            isActing={acting}
        />
    );
}

function FirstCrownStage({
    stage,
    championName,
    seasonId,
}: {
    stage: number;
    championName: string;
    seasonId: string;
}) {
    // Stages: 0 teaser → 1 the stage is set → 2 the name → 3 the title + season.
    if (stage <= 0) {
        return (
            <div className="champion-stage" data-testid="worlds-crown-stage-0">
                <p className="champion-kicker" style={{ color: '#fbbf24' }}>The World Stage</p>
                <p style={{ color: '#94a3b8', margin: 0 }}>One club stands above every tier…</p>
            </div>
        );
    }
    if (stage === 1) {
        return (
            <div className="champion-stage" data-testid="worlds-crown-stage-1">
                <p className="champion-kicker" style={{ color: '#fbbf24' }}>The World Stage</p>
                <p style={{ color: '#e2e8f0', margin: 0, fontWeight: 600 }}>
                    The summit of the pyramid is decided.
                </p>
            </div>
        );
    }
    if (stage === 2) {
        return (
            <div className="champion-stage" data-testid="worlds-crown-stage-2">
                <p className="champion-kicker" style={{ color: '#fbbf24' }}>Worlds Champions</p>
                <h2 className="champion-name" style={{ color: '#fbbf24' }}>{championName}</h2>
            </div>
        );
    }
    return (
        <div className="champion-stage" data-testid="worlds-crown-stage-3">
            <p className="champion-kicker" style={{ color: '#fbbf24' }}>Worlds Champions</p>
            <h2 className="champion-name" style={{ color: '#fbbf24' }}>{championName}</h2>
            <p className="champion-sub">The first Worlds title. The banner goes up tonight.</p>
            <p style={{ color: '#64748b', fontSize: '0.78rem', margin: '0.4rem 0 0' }}>{seasonId}</p>
        </div>
    );
}
