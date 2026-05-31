/* App orchestrator. */
const { useState: useStateApp } = React;

function App() {
  const data = window.DodgerData;
  const [activeTab, setActiveTab] = useStateApp('command');
  const [ccMode, setCcMode] = useStateApp('pre-sim');

  const onSimulate = () => setCcMode('post-sim');
  const onAdvance = () => { setCcMode('pre-sim'); };
  const onWatch = () => setActiveTab('replay');

  return (
    <div className="app-shell" data-screen-label={`Dodger / ${activeTab}`}>
      <LeftNav activeTab={activeTab} onSelect={(id) => { setActiveTab(id); if (id !== 'command') setCcMode('pre-sim'); }} seasonYear={data.program.seasonYear} />
      <div className="workspace">
        <BroadcastHeader activeTab={activeTab} seasonYear={data.program.seasonYear} week={data.program.week} />
        <div className="content-area">
          {activeTab === 'command'   && <CommandCenterScreen data={data} mode={ccMode} onSimulate={onSimulate} onAdvance={onAdvance} onWatch={onWatch} />}
          {activeTab === 'roster'    && <RosterScreen data={data} />}
          {activeTab === 'dynasty'   && <DynastyOfficeScreen data={data} />}
          {activeTab === 'standings' && <StandingsScreen data={data} />}
          {activeTab === 'replay'    && <MatchReplayScreen data={data} />}
        </div>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
