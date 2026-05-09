export function ProgramStatusStrip() {
  return (
    <div className="dm-panel" style={{ flex: 4 }}>
      <h3>Program Status</h3>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
        <a href="?tab=roster">View Roster</a>
        <a href="?tab=facilities">View Facilities</a>
        <a href="?tab=standings">View Standings</a>
      </div>
    </div>
  );
}