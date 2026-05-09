export function RecruitReactions({ reactions }: { reactions: any[] }) {
  return (
    <div className="dm-panel">
      <p className="dm-kicker">Recruit Reactions</p>
      {reactions.length === 0 ? (
        <p>No prospect interest changes reported.</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0 }}>
          {reactions.map((r, i) => (
            <li key={i} style={{ marginBottom: '0.5rem' }}>
              <b>{r.prospect_name}:</b> {r.evidence} (<span style={{ color: '#10b981' }}>{r.interest_delta}</span>)
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
