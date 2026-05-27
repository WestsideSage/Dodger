import { useEffect } from 'react';
import { MyProgramView } from './MyProgramView';

interface ProgramModalProps {
  clubId: string;
  clubName: string;
  onClose: () => void;
}

export function ProgramModal({ clubId, clubName, onClose }: ProgramModalProps) {
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  return (
    <div className="command-policy-overlay" onClick={onClose}>
      <div
        className="command-policy-overlay-body do-hist-modal-body"
        onClick={(event) => event.stopPropagation()}
      >
        <button className="command-policy-overlay-close" onClick={onClose} type="button">
          Close
        </button>
        <div className="do-hist-modal-header">
          <span className="dm-kicker">League Archive</span>
          <h2 className="do-hist-modal-title">{clubName}</h2>
          <p className="do-hist-card-note">Cross-program archive view from the league history board.</p>
        </div>
        <MyProgramView clubId={clubId} isSelf={false} />
      </div>
    </div>
  );
}
