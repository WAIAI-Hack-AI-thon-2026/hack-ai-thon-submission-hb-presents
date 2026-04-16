import { useState } from 'react'

const ROLE_LABELS = {
  comment_deepdive:      { text: 'About your review',        color: '#00355F', bg: '#E8F0FE' },
  information_gap:       { text: 'Help us learn more',        color: '#7C5C00', bg: '#FFF8E1' },
  conflict_resolution:   { text: 'Has this changed?',         color: '#7C2D12', bg: '#FFF1F2' },
}

export default function FollowUpCards({ property, questions, onComplete }) {
  const [current,  setCurrent]  = useState(0)
  const [selected, setSelected] = useState([])   // multi-select array
  const [otherText, setOtherText] = useState('')  // text for "Other"
  const [answers,  setAnswers]  = useState({})

  const q      = questions[current]
  const isLast = current === questions.length - 1
  const roleInfo = ROLE_LABELS[q?.role] || null
  const showOtherInput = selected.includes('Other')
  const hasAnswer = selected.length > 0 && (!showOtherInput || otherText.trim())

  function toggleOption(opt) {
    setSelected((prev) =>
      prev.includes(opt) ? prev.filter((o) => o !== opt) : [...prev, opt]
    )
    if (opt === 'Other' && selected.includes('Other')) setOtherText('')
  }

  function handleNext() {
    let value = selected
    if (showOtherInput && otherText.trim()) {
      value = selected.map((o) => o === 'Other' ? `Other: ${otherText.trim()}` : o)
    }
    const updated = { ...answers, [q.id]: value }
    setAnswers(updated)

    // If this was a conflict_resolution question, resolve it in the backend
    if (q.role === 'conflict_resolution' && property?.id) {
      fetch('/api/resolve-conflict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          propertyId: property.id,
          topic: q.aspect || '',
          answer: value.join(', '),
        }),
      }).catch(() => {})  // best-effort
    }

    setSelected([])
    setOtherText('')
    if (isLast) onComplete({ answers: updated, questions: allQuestions })
    else setCurrent((c) => c + 1)
  }

  return (
    <>
      {/* Hotel context strip */}
      <div className="hotel-strip">
        <div style={{ maxWidth: 640, margin: '0 auto', padding: '0 20px',
                      display: 'flex', alignItems: 'center', gap: 8 }}>
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
          {/* Role badge */}
          <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
            {roleInfo ? (
              <span style={{
                display: 'inline-block',
                background: roleInfo.bg, color: roleInfo.color,
                fontSize: 12, fontWeight: 700,
                padding: '4px 12px', borderRadius: 999,
                letterSpacing: '0.02em',
              }}>
                {roleInfo.text}
              </span>
            ) : (
              <span style={{
                display: 'inline-block',
                background: '#FFC72C', color: '#00355F',
                fontSize: 12, fontWeight: 700,
                padding: '4px 12px', borderRadius: 999,
                letterSpacing: '0.02em',
              }}>
                Help future travelers
              </span>
            )}
          </div>

          {/* Question text */}
          <p style={{
            fontSize: 19, fontWeight: 700, color: '#1a2638',
            lineHeight: 1.4, marginBottom: 20,
          }}>
            {q.text}
          </p>

          {/* Pill options — multi-select */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: showOtherInput ? 12 : 28 }}>
            {q.options.map((opt) => (
              <button
                key={opt}
                className={`pill-btn ${selected.includes(opt) ? 'selected' : ''}`}
                onClick={() => toggleOption(opt)}
              >
                {selected.includes(opt) ? '✓ ' : '+ '}
                {opt}
              </button>
            ))}
          </div>
          <p style={{ fontSize: 12, color: '#94a3b8', marginTop: -4, marginBottom: showOtherInput ? 12 : 20 }}>
            Select all that apply
          </p>

          {/* Other text input */}
          {showOtherInput && (
            <div style={{ marginBottom: 28 }}>
              <textarea
                rows={2}
                value={otherText}
                onChange={(e) => setOtherText(e.target.value)}
                placeholder="Please tell us more..."
                style={{
                  width: '100%', boxSizing: 'border-box',
                  borderRadius: 12, border: '1.5px solid #e2e8f0',
                  padding: '10px 14px', fontSize: 14,
                  fontFamily: 'inherit', resize: 'none',
                  outline: 'none',
                }}
                onFocus={(e) => e.target.style.borderColor = '#00355F'}
                onBlur={(e) => e.target.style.borderColor = '#e2e8f0'}
              />
            </div>
          )}

          {/* Next / Submit */}
          <button
            className="btn-primary"
            onClick={handleNext}
            disabled={!hasAnswer}
            style={{ marginBottom: 12 }}
          >
            {isLast ? 'Submit & Finish' : 'Next →'}
          </button>

          {/* Skip */}
          <div style={{ textAlign: 'center' }}>
            <button
              onClick={() => onComplete({ answers, questions: allQuestions })}
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
