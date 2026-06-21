import type { OffseasonBeat } from '../../types';
import { CeremonyShell } from './CeremonyShell';
import styles from './WorldsCrowning.module.css';

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
                <p className={`champion-kicker ${styles.gold}`}>The World Stage</p>
                <p className={styles.muted}>One club stands above every tier…</p>
            </div>
        );
    }
    if (stage === 1) {
        return (
            <div className="champion-stage" data-testid="worlds-crown-stage-1">
                <p className={`champion-kicker ${styles.gold}`}>The World Stage</p>
                <p className={styles.lede}>
                    The summit of the pyramid is decided.
                </p>
            </div>
        );
    }
    if (stage === 2) {
        return (
            <div className="champion-stage" data-testid="worlds-crown-stage-2">
                <p className={`champion-kicker ${styles.gold}`}>Worlds Champions</p>
                <h2 className={`champion-name ${styles.gold}`}>{championName}</h2>
            </div>
        );
    }
    return (
        <div className="champion-stage" data-testid="worlds-crown-stage-3">
            <p className={`champion-kicker ${styles.gold}`}>Worlds Champions</p>
            <h2 className={`champion-name ${styles.gold}`}>{championName}</h2>
            <p className="champion-sub">The first Worlds title. The banner goes up tonight.</p>
            <p className={styles.season}>{seasonId}</p>
        </div>
    );
}
