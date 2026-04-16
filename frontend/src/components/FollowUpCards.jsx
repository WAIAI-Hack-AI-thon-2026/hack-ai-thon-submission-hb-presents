import { useState } from 'react'

export default function FollowUpCards({ property, questions, onComplete }) {
  const [current,  setCurrent]  = useState(0)
  const [selected, setSelected] = useState(null)
  const [answers,  setAnswers]  = useState({})

  const q      = questions[current]
  const isLast = current === questions.length - 1

  function handleNext() {
    const updated = { ...answers, [q.id]: selected }
    setAnswers(updated)
    setSelected(null)
    if (isLast) onComplete(updated)
    else setCurrent((c) => c + 1)
  }

  return (
    <>
      {/* Hotel context strip */}
      <div className="hotel-strip">
        <div style={{ maxWidth: 640, margin: '0 auto', padding: '0 20px',
                      display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>{property.flag}</span>
          <span>{property.city}, {property.country}</span>
        </div>
      </div>

      <div className="fade-in" style={{ maxWidth: 640, margin: '0 auto', padding: '32px 20px 48px' }}>
        {/* Page title */}
        <h2 style={{ fontSize: 22, fontWeight: 700, color: '#1a2638', marginBottom: 6 }}>
          One more thing
        </h2>

        {/* Progress dots */}
        {questions.length > 1 && (
          <div style={{ display: 'flex', gap: 6, marginBottom: 20 }}>
            {questions.map((_, i) => (
              <div
                key={i}
                className={`dot ${i === current ? 'active' : ''}`}
                style={{ width: i === current ? 22 : 8 }}
              />
            ))}
          </div>
        )}

        {/* Question card */}
        <div className="card" style={{ padding: '24px' }}>
          {/* Badge */}
          <div style={{ marginBottom: 16 }}>
            <span style={{
              display: 'inline-block',
              background: '#FFC72C', color: '#00355F',
              fontSize: 12, fontWeight: 700,
              padding: '4px 12px', borderRadius: 999,
              letterSpacing: '0.02em',
            }}>
              Help future travelers
            </span>
          </div>

          {/* Question text */}
          <p style={{
            fontSize: 19, fontWeight: 700, color: '#1a2638',
            lineHeight: 1.4, marginBottom: 20,
          }}>
            {q.text}
          </p>

          {/* Pill options */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: 28 }}>
            {q.options.map((opt) => (
              <button
                key={opt}
                className={`pill-btn ${selected === opt ? 'selected' : ''}`}
                onClick={() => setSelected(opt)}
              >
                {selected === opt && '✓ '}
                {opt}
              </button>
            ))}
          </div>

          {/* Next / Submit */}
          <button
            className="btn-primary"
            onClick={handleNext}
            disabled={!selected}
            style={{ marginBottom: 12 }}
          >
            {isLast ? 'Submit & Finish' : 'Next →'}
          </button>

          {/* Skip */}
          <div style={{ textAlign: 'center' }}>
            <button
              onClick={() => onComplete(answers)}
              style={{
                background: 'none', border: 'none',
                color: '#94a3b8', fontSize: 13,
                fontFamily: 'inherit', cursor: 'pointer',
                padding: '4px 8px',
              }}
            >
              Skip
            </button>
          </div>
        </div>

        {/* Footer note */}
        <p style={{
          marginTop: 16, fontSize: 12, color: '#94a3b8',
          textAlign: 'center', lineHeight: 1.5,
        }}>
          Your answer helps keep property info current for future guests
        </p>
      </div>
    </>
  )
}
