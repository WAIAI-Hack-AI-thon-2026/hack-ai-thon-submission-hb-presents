function Stars({ count }) {
  const full = Math.floor(count)
  const half = count % 1 >= 0.5
  const empty = 5 - full - (half ? 1 : 0)
  return (
    <span style={{ fontSize: 13, letterSpacing: 1.5 }}>
      <span style={{ color: '#FFC72C' }}>{'★'.repeat(full)}</span>
      {half && <span style={{ color: '#FFC72C' }}>½</span>}
      <span style={{ color: '#E0E0E0' }}>{'★'.repeat(empty)}</span>
    </span>
  )
}

export default function PropertySelect({ properties, onSelect }) {
  return (
    <div className="fade-in" style={{ maxWidth: 640, margin: '0 auto', padding: '40px 24px 56px' }}>
      <h1 style={{
        fontSize: 28, fontWeight: 700, color: '#222222',
        marginBottom: 8, letterSpacing: '-0.4px',
      }}>
        Where did you stay?
      </h1>
      <p style={{ fontSize: 15, color: '#6a6a6a', marginBottom: 32, lineHeight: 1.5 }}>
        Select a property to leave a review
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
        {properties.map((p) => (
          <button key={p.id} className="property-card" onClick={() => onSelect(p)}>
            {/* Landmark thumbnail */}
            <div style={{
              width: 64, height: 64, borderRadius: 12, overflow: 'hidden',
              flexShrink: 0, background: '#F0F0F0',
            }}>
              {p.image ? (
                <img
                  src={p.image}
                  alt={p.landmark || p.city}
                  style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                  loading="lazy"
                />
              ) : (
                <div style={{
                  width: '100%', height: '100%',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: 'linear-gradient(135deg, #00355F 0%, #005A9E 100%)',
                  color: '#fff', fontSize: 22, fontWeight: 700,
                }}>
                  {p.city.charAt(0)}
                </div>
              )}
            </div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontWeight: 700, fontSize: 16, color: '#222222',
                marginBottom: 4,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {p.city}
              </div>
              <div style={{
                fontSize: 14, color: '#6a6a6a',
                display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
              }}>
                <span>{p.country}</span>
                {p.starRating != null && (
                  <>
                    <span style={{ color: '#DDDDDD' }}>·</span>
                    <Stars count={p.starRating} />
                  </>
                )}
              </div>
              <div style={{
                marginTop: 10,
                display: 'flex', alignItems: 'center',
                gap: 8, flexWrap: 'wrap',
              }}>
                {typeof p.totalReviews === 'number' && (
                  <span style={{ fontSize: 13, color: '#717171', fontWeight: 500 }}>
                    {p.totalReviews} reviews
                  </span>
                )}
                {Array.isArray(p.topGaps) && p.topGaps.length > 0 && (
                  <span style={{
                    display: 'inline-block',
                    fontSize: 11, fontWeight: 700,
                    padding: '3px 10px',
                    borderRadius: 999,
                    background: 'rgba(255, 199, 44, 0.15)',
                    color: '#7C5C00',
                  }}>
                    {p.topGaps.length} data gaps
                  </span>
                )}
                {typeof p.staleCount === 'number' && p.staleCount > 0 && (
                  <span style={{
                    display: 'inline-block',
                    fontSize: 11, fontWeight: 700,
                    padding: '3px 10px',
                    borderRadius: 999,
                    background: '#FFF1F2',
                    color: '#7C2D12',
                  }}>
                    {p.staleCount} need refresh
                  </span>
                )}
              </div>
            </div>

            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" style={{ flexShrink: 0 }}>
              <path d="M7 4l6 6-6 6" stroke="#B0B0B0" strokeWidth="2"
                    strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        ))}
      </div>
    </div>
  )
}
