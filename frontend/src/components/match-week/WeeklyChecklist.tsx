import { useState } from 'react';
import { ActionButton } from '../ui';

export function WeeklyChecklist({ plan: _plan, onAcceptPlan }: { plan: any, onAcceptPlan: () => void }) {
  const [toast, setToast] = useState<string | null>(null);

  const handleAccept = () => {
    // Basic diff logic for Wave 2
    const diff = ["Tactic updated", "Lineup optimized"];
    setToast(`Plan accepted: ${diff.join(', ')}`);
    onAcceptPlan();
    setTimeout(() => setToast(null), 3000);
  };

  return (
    <div className="dm-panel" style={{ flex: 6 }}>
      <h3>Weekly Checklist</h3>
      {toast && <div style={{ padding: '0.5rem', background: '#10b981', color: 'white', marginBottom: '1rem' }}>{toast}</div>}
      <ActionButton onClick={handleAccept}>Accept Recommended Plan</ActionButton>
      {/* Checklist items here */}
    </div>
  );
}