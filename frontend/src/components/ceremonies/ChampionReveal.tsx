import type { OffseasonBeat, PlayoffBracketResponse } from '../../types';
import { ActionButton, PageHeader } from '../../ui';
import { useApiResource } from '../../hooks/useApiResource';
import { PlayoffBracket } from '../standings/PlayoffBracket';
import styles from './ChampionReveal.module.css';

type ChampionBeat = Extract<OffseasonBeat, { key: 'champion' }>;

export function ChampionReveal({
    beat,
    onComplete,
    acting,
}: {
    beat: ChampionBeat;
    onComplete: () => void;
    acting?: boolean;
}) {
    const champion = beat.payload.champion;
    const { data: bracket } = useApiResource<PlayoffBracketResponse>('/api/playoffs/bracket');

    return (
        <section className="command-offseason-shell" data-testid="offseason-champion">
            <PageHeader
                eyebrow={`Offseason Beat ${beat.beat_index + 1}/${beat.total_beats} · Postseason`}
                title={beat.title}
                description="The bracket is decided. The banner goes up tonight."
                stats={
                    <div className="command-offseason-progress" aria-label="Offseason beat progress">
                        {Array.from({ length: beat.total_beats }).map((_, index) => (
                            <span
                                key={index}
                                className={
                                    index <= beat.beat_index
                                        ? 'command-offseason-progress-step command-offseason-progress-step-active'
                                        : 'command-offseason-progress-step'
                                }
                            />
                        ))}
                    </div>
                }
            />
            <div className="champion-stage">
                <p className="champion-kicker">Season Champion</p>
                {champion ? (
                    <>
                        <h2 className="champion-name">{champion.club_name}</h2>
                        <p className="champion-sub">Won the championship final to claim the title.</p>
                        <div className="champion-stats">
                            <div>
                                <div className="num">
                                    {champion.wins}-{champion.losses}-{champion.draws}
                                </div>
                                <div className="cap">Regular Season</div>
                            </div>
                            <div>
                                <div className="num gold">{champion.title_count}</div>
                                <div className="cap">
                                    {champion.title_count === 1 ? 'Title' : 'Titles'}
                                </div>
                            </div>
                        </div>
                    </>
                ) : (
                    <p className={styles.fallback}>
                        {typeof beat.body === 'string' ? beat.body : 'No champion determined this season.'}
                    </p>
                )}
            </div>

            {bracket && (
                <div className={styles.bracketWrap}>
                    <PlayoffBracket data={bracket} />
                </div>
            )}

            <div className="dm-panel command-action-bar">
                <div>
                    <p className="dm-kicker">Ceremony Control</p>
                    <p>Continue to the next offseason beat.</p>
                </div>
                <div className="command-action-buttons">
                    <ActionButton
                        variant="primary"
                        onClick={onComplete}
                        disabled={acting}
                    >
                        {acting ? 'Continuing...' : 'Continue'}
                    </ActionButton>
                </div>
            </div>
        </section>
    );
}
