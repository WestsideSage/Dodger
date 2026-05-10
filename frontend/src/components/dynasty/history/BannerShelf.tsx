interface BannerEntry {
  type: string;
  season: string;
  label: string;
}

export function BannerShelf({ banners, showNextPlaceholder }: { banners: BannerEntry[]; showNextPlaceholder?: boolean }) {
  if (banners.length === 0 && !showNextPlaceholder) {
    return <p style={{ color: '#475569', fontSize: '0.8rem' }}>No banners yet.</p>;
  }

  return (
    <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'flex-end' }}>
      {banners.map((b, i) => (
        <div key={i} style={{ textAlign: 'center' }}>
          <div style={{ fontSize: b.type === 'championship' ? '2.5rem' : '1.75rem' }}>
            {b.type === 'championship' ? '🏆' : '🏅'}
          </div>
          <div
            style={{
              fontSize: '0.6rem',
              color: b.type === 'championship' ? '#f97316' : '#eab308',
              fontWeight: 600,
              whiteSpace: 'nowrap',
              marginTop: '0.2rem',
            }}
          >
            {b.label}
          </div>
          <div style={{ fontSize: '0.55rem', color: '#475569' }}>{b.season}</div>
        </div>
      ))}

      {showNextPlaceholder && (
        <div
          style={{
            width: '48px',
            height: '56px',
            border: '1px dashed #1e293b',
            borderRadius: '4px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <span style={{ color: '#334155', fontSize: '1rem' }}>+</span>
        </div>
      )}
    </div>
  );
}
