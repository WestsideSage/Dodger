import { MyProgramView } from './MyProgramView';
import { Dialog } from '../../ui';
import styles from './ProgramModal.module.css';

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
      panelClassName={`command-policy-overlay-body ${styles.body}`}
      overlayStyle={{ backgroundColor: undefined, backdropFilter: undefined, padding: undefined }}
      panelStyle={{}}
    >
        <button className={styles.close} onClick={onClose} type="button">
          Close
        </button>
        <div className={styles.header}>
          <span className={styles.kicker}>League Archive</span>
          <h2 id="program-modal-title" className={styles.title}>{clubName}</h2>
          <p className={styles.note}>
            Viewing {clubName}'s program archive — titles, alumni, and milestones logged across their history.
          </p>
        </div>
        <MyProgramView clubId={clubId} isSelf={false} />
    </Dialog>
  );
}
