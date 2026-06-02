import { MyProgramView } from './MyProgramView';
import { Dialog } from '../../ui';

interface ProgramModalProps {
  clubId: string;
  clubName: string;
  onClose: () => void;
}

export function ProgramModal({ clubId, clubName, onClose }: ProgramModalProps) {
  // Escape, focus-trap and focus-restore are now provided by the shared Dialog
  // primitive (WT-21), replacing the prior window-level Escape listener that
  // neither trapped focus nor restored it to the trigger.
  return (
    <Dialog
      label={`${clubName} — Program Archive`}
      labelledBy="program-modal-title"
      onClose={onClose}
      className="command-policy-overlay"
      panelClassName="command-policy-overlay-body do-hist-modal-body"
      overlayStyle={{ backgroundColor: undefined, backdropFilter: undefined, padding: undefined }}
      panelStyle={{}}
    >
        <button className="command-policy-overlay-close" onClick={onClose} type="button">
          Close
        </button>
        <div className="do-hist-modal-header">
          <span className="dm-kicker">League Archive</span>
          <h2 id="program-modal-title" className="do-hist-modal-title">{clubName}</h2>
          <p className="do-hist-card-note">
            Viewing {clubName}'s program archive — titles, alumni, and milestones logged across their history.
          </p>
        </div>
        <MyProgramView clubId={clubId} isSelf={false} />
    </Dialog>
  );
}
