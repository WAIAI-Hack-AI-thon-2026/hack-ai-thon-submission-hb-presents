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
        padding: '64px 24px 56px',
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', textAlign: 'center',
      }}
    >
      {/* Checkmark circle — animated */}
      <div
        className="check-circle"
        style={{
          position: 'relative',
          width: 88, height: 88, borderRadius: '50%',
          background: '#FFC72C',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginBottom: 28,
        }}
      >
        <svg width="40" height="40" viewBox="0 0 40 40" fill="none">
          <path
            className="check-mark"
            d="M8 20l9 9L32 11"
            stroke="#00355F" strokeWidth="3.5"
            strokeLinecap="round" strokeLinejoin="round"
          />
        </svg>
      </div>

      {/* Title */}
      <h2 style={{
        fontSize: 32, fontWeight: 700, color: '#222222',
        marginBottom: 12, letterSpacing: '-0.5px',
      }}>
        Review submitted!
      </h2>
      <p style={{
        fontSize: 16, color: '#6a6a6a',
        marginBottom: 40, maxWidth: 340, lineHeight: 1.55,
      }}>
        Thank you — your feedback helps future travelers choose with confidence.
      </p>

      {/* Stats pills */}
      <div style={{
        display: 'flex', flexWrap: 'wrap',
        gap: 10, justifyContent: 'center',
        marginBottom: 44,
      }}>
        {STATS.map((s) => (
          <span key={s} className="stat-pill">{s}</span>
        ))}
      </div>

      {/* CTA */}
      <button
        className="btn-primary"
        onClick={onReset}
        style={{ maxWidth: 320 }}
      >
        Write Another Review
      </button>
    </div>
  )
}
