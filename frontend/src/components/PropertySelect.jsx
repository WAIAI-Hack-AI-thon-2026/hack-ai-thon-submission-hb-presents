// ── Star display (read-only, supports half stars) ────────────────────────────
function Stars({ count }) {
  const full = Math.floor(count)
  const half = count % 1 >= 0.5
  const empty = 5 - full - (half ? 1 : 0)
  return (
    <span style={{ fontSize: 13, letterSpacing: 1 }}>
      <span style={{ color: '#FFC72C' }}>{'★'.repeat(full)}</span>
      {half && <span style={{ color: '#FFC72C' }}>½</span>}
      <span style={{ color: '#e2e8f0' }}>{'★'.repeat(empty)}</span>
    </span>
  )
}

export default function PropertySelect({ properties, onSelect }) {
  return (
    <div className="fade-in" style={{ maxWidth: 640, margin: '0 auto', padding: '32px 20px 48px' }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, color: '#1a2638', marginBottom: 6 }}>
        Where did you stay?
      </h1>
      <p style={{ fontSize: 14, color: '#64748b', marginBottom: 24 }}>
        Select a property to leave a review
      </p>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {properties.map((p) => (
          <button key={p.id} className="property-card" onClick={() => onSelect(p)}>
            {/* Flag */}
            <span style={{ fontSize: 30, lineHeight: 1, flexShrink: 0 }}>{p.flag}</span>

            {/* Info */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{
                fontWeight: 700, fontSize: 15, color: '#1a2638',
                marginBottom: 3,
                overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {p.city}
              </div>
              <div style={{
                fontSize: 13, color: '#64748b',
                display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap',
              }}>
                <span>{p.country}</span>
                <span style={{ color: '#e2e8f0' }}>·</span>
                <Stars count={p.stars} />
                {p.score && (
                  <>
                    <span style={{ color: '#e2e8f0' }}>·</span>
                    <span style={{
                      background: '#00355F', color: '#fff',
                      fontSize: 11, fontWeight: 700,
                      padding: '2px 7px', borderRadius: 6,
                    }}>
                      {p.score}
                    </span>
                  </>
                )}
              </div>
            </div>

            {/* Arrow */}
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" style={{ flexShrink: 0 }}>
              <path d="M6 4l5 5-5 5" stroke="#94a3b8" strokeWidth="2"
                    strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        ))}
      </div>
    </div>
  )
}
