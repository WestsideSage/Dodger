/* Left nav + broadcast (top) header. */

const NAV_TABS = [
  { id: 'command',   label: 'Command Center', kicker: 'WAR ROOM' },
  { id: 'roster',    label: 'Roster',         kicker: 'ROSTER LAB' },
  { id: 'dynasty',   label: 'Dynasty Office', kicker: 'FRONT OFFICE' },
  { id: 'standings', label: 'Standings',      kicker: 'LEAGUE OFFICE' },
  { id: 'replay',    label: 'Match Replay',   kicker: 'MATCH DAY' },
];

const LeftNav = ({ activeTab, onSelect, seasonYear }) => (
  <aside className="left-nav">
    <div className="left-nav-logo">
      <p className="dm-kicker" style={{ fontSize: '0.62rem' }}>Dodgeball Manager</p>
      <p style={{
        fontFamily: 'var(--font-display)', fontSize: '1.125rem', fontWeight: 700,
        textTransform: 'uppercase', letterSpacing: '0.05em', color: '#fff', margin: '2px 0 0'
      }}>{seasonYear}</p>
    </div>
    <nav className="left-nav-items" aria-label="Primary">
      {NAV_TABS.map(t => (
        <button
          key={t.id}
          className={`nav-item ${activeTab === t.id ? 'active' : ''}`}
          onClick={() => onSelect(t.id)}
        >
          <span className="dot"></span>
          {t.label}
        </button>
      ))}
    </nav>
    <div className="left-nav-footer">
      <button className="nav-item" disabled><span className="dot"></span>Settings</button>
      <button className="nav-item" disabled><span className="dot"></span>Menu</button>
    </div>
  </aside>
);

const BroadcastHeader = ({ activeTab, seasonYear, week }) => {
  const tab = NAV_TABS.find(t => t.id === activeTab) || NAV_TABS[0];
  return (
    <header className="broadcast-header">
      <div>
        <Kicker>{tab.kicker}</Kicker>
        <h1>{tab.label}</h1>
      </div>
      <span className="meta">Season {seasonYear} -- Week {String(week).padStart(2, '0')}</span>
    </header>
  );
};

Object.assign(window, { LeftNav, BroadcastHeader, NAV_TABS });
