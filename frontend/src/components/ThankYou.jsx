const STATS = [
  '4,162 reviews analyzed',
  '7 languages',
  '13 properties',
]

export default function ThankYou({ onReset }) {
  return (
    <div
      className="fade-in"
      style={{
        maxWidth: 640, margin: '0 auto',
        padding: '56px 20px 48px',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', textAlign: 'center',
      }}
    >
      {/* Yellow circle + checkmark */}
      <div style={{
        width: 80, height: 80, borderRadius: '50%',
        background: '#FFC72C',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        marginBottom: 24,
        boxShadow: '0 4px 20px rgba(255,199,44,0.40)',
      }}>
        <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
          <path
            d="M7 18l8 8L29 10"
            stroke="#00355F" strokeWidth="3.5"
            strokeLinecap="round" strokeLinejoin="round"
          />
        </svg>
      </div>

      {/* Title */}
      <h2 style={{
        fontSize: 28, fontWeight: 700, color: '#1a2638',
        marginBottom: 10, letterSpacing: '-0.4px',
      }}>
        Review submitted!
      </h2>
      <p style={{
        fontSize: 15, color: '#64748b',
        marginBottom: 36, maxWidth: 300, lineHeight: 1.55,
      }}>
        Thank you — your feedback helps future travelers choose with confidence.
      </p>

      {/* Stats pills */}
      <div style={{
        display: 'flex', flexWrap: 'wrap',
        gap: 10, justifyContent: 'center',
        marginBottom: 40,
      }}>
        {STATS.map((s) => (
          <span key={s} className="stat-pill">{s}</span>
        ))}
      </div>

      {/* CTA */}
      <button
        className="btn-primary"
        onClick={onReset}
        style={{ maxWidth: 300 }}
      >
        Write Another Review
      </button>
    </div>
  )
}
