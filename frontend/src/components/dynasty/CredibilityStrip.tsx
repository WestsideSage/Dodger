import type { DynastyOfficeResponse } from '../../types';

type RecruitingCredibility = DynastyOfficeResponse['recruiting']['credibility'];
type RecruitingBudget = DynastyOfficeResponse['recruiting']['budget'];

function remaining([used, total]: [number, number]) {
  return Math.max(0, total - used);
}

export function CredibilityStrip({
  credibility,
  budget,
  prospectCount,
  week,
}: {
  credibility: RecruitingCredibility;
  budget: RecruitingBudget;
  prospectCount: number;
  week: number;
}) {
  const score = credibility.score;
  const progress = Math.min(100, Math.max(0, ((score - 40) / (75 - 40)) * 100));
  const scoutRemaining = remaining(budget.scout);
  const contactRemaining = remaining(budget.contact);
  const visitRemaining = remaining(budget.visit);

  return (
    <div className="do-cred">
      <div className="do-cred-letter">
        <span className="tier">{credibility.grade}</span>
        <div className="halo" />
      </div>

      <div className="do-cred-main">
        <span className="dm-kicker">Program Credibility</span>
        <h2 className="do-cred-title">Tier {credibility.grade} · Regional</h2>
        <p className="do-cred-blurb">Recruit quality rises with the program. This board reflects your live week, current score, and open recruiting pressure.</p>

        <div className="do-cred-progress">
          <div className="do-cred-progress-head">
            <span className="lbl">Toward Tier B</span>
            <span className="val mono"><b>{score}</b> <span className="dim">/ 75</span></span>
          </div>
          <div className="do-cred-track">
            <div className="do-cred-fill" style={{ width: `${progress}%` }}>
              <span className="do-cred-marker" />
            </div>
            <span className="do-cred-tick" style={{ left: '0%' }}><span className="lbl">D</span></span>
            <span className="do-cred-tick" style={{ left: '33%' }}><span className="lbl">C</span></span>
            <span className="do-cred-tick" style={{ left: '66%' }}><span className="lbl">B</span></span>
            <span className="do-cred-tick" style={{ left: '100%' }}><span className="lbl">A</span></span>
          </div>
        </div>

        <div className="do-cred-evidence">
          {credibility.evidence.map((item, index) => (
            <div key={`${index}-${item}`} className="item">
              <span className="ix">{String(index + 1).padStart(2, '0')}</span>
              <span className="copy">{item}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="do-cred-side">
        <div className="do-cred-rank">
          <span className="lbl">Board Size</span>
          <div className="val"><b>{prospectCount}</b> <span>live targets</span></div>
          <span className="trend dim">Week {String(week).padStart(2, '0')} recruiting board</span>
        </div>
        <div className="do-cred-rank">
          <span className="lbl">Reach Remaining</span>
          <div className="val"><b>{scoutRemaining + contactRemaining}</b> <span>scout + contact</span></div>
          <span className="trend dim">{scoutRemaining} scout / {contactRemaining} contact still open</span>
        </div>
        <div className="do-cred-rank danger">
          <span className="lbl">Visit Window</span>
          <div className="val"><b>{visitRemaining}</b> <span>visit slots</span></div>
          <span className={`trend ${visitRemaining > 0 ? 'dim' : 'warn'}`}>
            {visitRemaining > 0 ? 'Use visits on top-fit closes' : 'Visit budget exhausted this week'}
          </span>
        </div>
      </div>
    </div>
  );
}
