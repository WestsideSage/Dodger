export function Headline({ text }: { text: string }) {
  return (
    <div className="dm-panel" style={{ textAlign: 'center', padding: '2rem' }}>
      <h1 className="dm-headline" style={{ fontSize: '2.5rem', margin: 0 }}>{text}</h1>
    </div>
  );
}
