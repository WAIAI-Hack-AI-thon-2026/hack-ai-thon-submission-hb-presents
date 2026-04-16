import { useState } from 'react'

const ROLE_LABELS = {
  comment_deepdive:      { text: 'About your review',  color: '#00355F', bg: '#E8F0FE' },
  information_gap:       { text: 'Help us learn more',  color: '#7C5C00', bg: 'rgba(255, 199, 44, 0.15)' },
  conflict_resolution:   { text: 'Has this changed?',   color: '#7C2D12', bg: '#FFF1F2' },
}

export default function FollowUpCards({ property, questions, onComplete }) {
  const [current,  setCurrent]  = useState(0)
  const [selected, setSelected] = useState([])
  const [otherText, setOtherText] = useState('')
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

    if (q.role === 'conflict_resolution' && property?.id) {
      fetch('/api/resolve-conflict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          propertyId: property.id,
          topic: q.aspect || '',
          answer: value.join(', '),
        }),
      }).catch(() => {})
    }

    setSelected([])
    setOtherText('')
    if (isLast) onComplete({ answers: updated, questions })
    else setCurrent((c) => c + 1)
  }

  return (
    <>
      <div className="hotel-strip">
        <div style={{ maxWidth: 640, margin: '0 auto', padding: '0 24px',
                      display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>{property.city}, {property.country}</span>
        </div>
      </div>

      <div className="fade-in" style={{ maxWidth: 640, margin: '0 auto', padding: '40px 24px 56px' }}>
        <h2 style={{
          fontSize: 24, fontWeight: 700, color: '#222222',
          marginBottom: 8, letterSpacing: '-0.3px',
        }}>
          One more thing
        </h2>

        {/* Progress bar */}
        {questions.length > 1 && (
          <div style={{ marginBottom: 28 }}>
            <div style={{
              display: 'flex', justifyContent: 'space-between',
              alignItems: 'baseline', marginBottom: 8,
            }}>
              <span style={{ fontSize: 14, fontWeight: 600, color: '#222222' }}>
                Question {current + 1}
                <span style={{ fontWeight: 400, color: '#6a6a6a' }}> of {questions.length}</span>
              </span>
              <span style={{ fontSize: 13, fontWeight: 500, color: '#6a6a6a' }}>
                {Math.round(((current + 1) / questions.length) * 100)}%
              </span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{ width: `${((current + 1) / questions.length) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Question card */}
        <div className="card" style={{ padding: '28px' }}>
          {/* Role badge */}
          <div style={{ marginBottom: 18 }}>
            {roleInfo ? (
              <span className="role-badge" style={{
                background: roleInfo.bg, color: roleInfo.color,
              }}>
                {roleInfo.text}
              </span>
            ) : (
              <span className="role-badge" style={{
                background: 'rgba(255, 199, 44, 0.15)', color: '#00355F',
              }}>
                Help future travelers
              </span>
            )}
          </div>

          {/* Question text */}
          <p style={{
            fontSize: 20, fontWeight: 700, color: '#222222',
            lineHeight: 1.4, marginBottom: 24, letterSpacing: '-0.2px',
          }}>
            {q.text}
          </p>

          {/* Pill options */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginBottom: showOtherInput ? 14 : 24 }}>
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
          <p style={{ fontSize: 13, color: '#B0B0B0', marginTop: -4, marginBottom: showOtherInput ? 14 : 24 }}>
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
                className="review-textarea"
                style={{ fontSize: 14 }}
              />
            </div>
          )}

          {/* Next / Submit */}
          <button
            className="btn-primary"
            onClick={handleNext}
            disabled={!hasAnswer}
            style={{ marginBottom: 14 }}
          >
            {isLast ? 'Submit & Finish' : 'Next'}
          </button>

          {/* Skip */}
          <div style={{ textAlign: 'center' }}>
            <button
              className="skip-btn"
              onClick={() => onComplete({ answers, questions })}
            >
              Skip
            </button>
          </div>
        </div>

        {/* Footer note */}
        <p style={{
          marginTop: 20, fontSize: 13, color: '#B0B0B0',
          textAlign: 'center', lineHeight: 1.5,
        }}>
          Your answer helps keep property info current for future guests
        </p>
      </div>
    </>
  )
}
