import { MyProgramView } from './MyProgramView';
import { Modal } from '../../../ui';
import styles from './ProgramModal.module.css';
import chrome from '../../chrome.module.css';

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
    <Modal
      label={`${clubName} — Program Archive`}
      labelledBy="program-modal-title"
      onClose={onClose}
      className={chrome.policyOverlay}
      panelClassName={`${chrome.policyOverlayBody} ${styles.body}`}
      data-testid="program-archive-modal"
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
    </Modal>
  );
}
