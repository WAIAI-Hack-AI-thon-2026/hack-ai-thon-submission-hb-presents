import { useState } from 'react'

const STAR_LABELS = { 1: 'Terrible', 2: 'Poor', 3: 'Okay', 4: 'Good', 5: 'Excellent' }

function StarPicker({ value, onChange }) {
  const [hovered, setHovered] = useState(0)
  const active = hovered || value

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
      <div
        style={{ display: 'flex', gap: 2 }}
        onMouseLeave={() => setHovered(0)}
      >
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            className={`star-btn ${n <= active ? 'lit' : ''}`}
            onMouseEnter={() => setHovered(n)}
            onClick={() => onChange(n)}
            aria-label={`${n} star${n > 1 ? 's' : ''}`}
          >
            ★
          </button>
        ))}
      </div>
      {value > 0 && (
        <span style={{ fontSize: 15, fontWeight: 600, color: '#00355F' }}>
          {STAR_LABELS[value]}
        </span>
      )}
    </div>
  )
}

export default function ReviewForm({ property, onSubmit }) {
  const [rating, setRating]           = useState(0)
  const [reviewText, setReviewText]   = useState('')
  const [isSubmitting, setSubmitting] = useState(false)

  const canSubmit = rating > 0 && reviewText.trim().length > 0 && !isSubmitting

  async function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit) return
    setSubmitting(true)
    try {
      await onSubmit({ rating, reviewText })
    } finally {
      setSubmitting(false)
    }
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

      <div className="fade-in" style={{ maxWidth: 640, margin: '0 auto', padding: '28px 20px 48px' }}>
        <div className="card" style={{ padding: '28px 24px' }}>
          <h2 style={{ fontSize: 20, fontWeight: 700, color: '#1a2638', marginBottom: 4 }}>
            How was your stay?
          </h2>
          <p style={{ fontSize: 14, color: '#64748b', marginBottom: 28 }}>
            Your honest review helps other travelers make better decisions.
          </p>

          <form onSubmit={handleSubmit}>
            {/* Star rating */}
            <div style={{ marginBottom: 28 }}>
              <label style={{
                display: 'block', fontSize: 12, fontWeight: 700,
                color: '#64748b', textTransform: 'uppercase',
                letterSpacing: '0.06em', marginBottom: 12,
              }}>
                Overall rating
              </label>
              <StarPicker value={rating} onChange={setRating} />
            </div>

            {/* Text area */}
            <div style={{ marginBottom: 28 }}>
              <label style={{
                display: 'block', fontSize: 12, fontWeight: 700,
                color: '#64748b', textTransform: 'uppercase',
                letterSpacing: '0.06em', marginBottom: 12,
              }}>
                Your review
              </label>
              <textarea
                className="review-textarea"
                rows={6}
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value)}
                placeholder="Tell future travelers what your stay was like..."
                disabled={isSubmitting}
              />
              <p style={{
                textAlign: 'right', fontSize: 12,
                color: '#94a3b8', marginTop: 4,
              }}>
                {reviewText.length} characters
              </p>
            </div>

            {/* Submit */}
            <button type="submit" className="btn-primary" disabled={!canSubmit}>
              {isSubmitting ? (
                <>
                  <span className="spinner" />
                  Analyzing your review...
                </>
              ) : (
                'Submit Review'
              )}
            </button>
          </form>
        </div>
      </div>
    </>
  )
}
