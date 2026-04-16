import { useState } from 'react'

const STAR_LABELS = { 1: 'Terrible', 2: 'Poor', 3: 'Okay', 4: 'Good', 5: 'Excellent' }
const RATING_FIELDS = [
  ['cleanliness', 'Cleanliness'],
  ['service', 'Staff & Service'],
  ['location', 'Location'],
  ['value', 'Value for Money'],
]

function createInitialRatings() {
  return Object.fromEntries([['overall', 0], ...RATING_FIELDS.map(([key]) => [key, 0])])
}

function StarPicker({ value, onChange, size = 'default' }) {
  const [hovered, setHovered] = useState(0)
  const active = hovered || value
  const fontSize = size === 'large' ? 40 : 28

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <div
        style={{ display: 'flex', gap: size === 'large' ? 4 : 2 }}
        onMouseLeave={() => setHovered(0)}
      >
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            className={`star-btn ${n <= active ? 'lit' : ''}`}
            style={{ fontSize }}
            onMouseEnter={() => setHovered(n)}
            onClick={() => onChange(n)}
            aria-label={`${n} star${n > 1 ? 's' : ''}`}
          >
            ★
          </button>
        ))}
      </div>
      {size === 'large' && value > 0 && (
        <span style={{ fontSize: 16, fontWeight: 600, color: '#222222' }}>
          {STAR_LABELS[value]}
        </span>
      )}
    </div>
  )
}

export default function ReviewForm({ property, onSubmit }) {
  const [ratings, setRatings]       = useState(createInitialRatings)
  const [reviewText, setReviewText] = useState('')
  const [isSubmitting, setSubmitting] = useState(false)
  const [errorMsg, setErrorMsg]     = useState('')

  function setRatingValue(field, value) {
    setRatings((current) => ({ ...current, [field]: value }))
    setErrorMsg('')
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (isSubmitting) return

    if (ratings.overall === 0) {
      setErrorMsg('Please select an overall rating.')
      return
    }
    const missing = RATING_FIELDS.filter(([key]) => ratings[key] === 0).map(([, label]) => label)
    if (missing.length > 0) {
      setErrorMsg(`Please rate: ${missing.join(', ')}`)
      return
    }

    setSubmitting(true)
    try {
      await onSubmit({ rating: ratings, reviewText })
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <div className="hotel-strip">
        <div style={{ maxWidth: 640, margin: '0 auto', padding: '0 24px',
                      display: 'flex', alignItems: 'center', gap: 8 }}>
          <span>{property.city}, {property.country}</span>
        </div>
      </div>

      <div className="fade-in" style={{ maxWidth: 640, margin: '0 auto', padding: '32px 24px 56px' }}>
        <div className="card" style={{ padding: '32px 28px' }}>
          <h2 style={{
            fontSize: 22, fontWeight: 700, color: '#222222',
            marginBottom: 6, letterSpacing: '-0.3px',
          }}>
            How was your stay?
          </h2>
          <p style={{ fontSize: 15, color: '#6a6a6a', marginBottom: 32, lineHeight: 1.5 }}>
            Your honest review helps other travelers make better decisions.
          </p>

          <form onSubmit={handleSubmit}>
            {/* Overall rating */}
            <div style={{ marginBottom: 32 }}>
              <label className="section-label">Overall rating</label>
              <StarPicker
                size="large"
                value={ratings.overall}
                onChange={(value) => setRatingValue('overall', value)}
              />
            </div>

            {/* Category ratings */}
            <div style={{ marginBottom: 32 }}>
              <label className="section-label">Category ratings</label>
              <div style={{ display: 'grid', gap: 10 }}>
                {RATING_FIELDS.map(([field, label]) => (
                  <div key={field} className="rating-row">
                    <div style={{ fontSize: 15, fontWeight: 600, color: '#222222' }}>
                      {label}
                    </div>
                    <StarPicker
                      value={ratings[field]}
                      onChange={(value) => setRatingValue(field, value)}
                    />
                  </div>
                ))}
              </div>
            </div>

            {/* Text area */}
            <div style={{ marginBottom: 32 }}>
              <label className="section-label">Your review (optional)</label>
              <textarea
                className="review-textarea"
                rows={5}
                value={reviewText}
                onChange={(e) => setReviewText(e.target.value)}
                placeholder="Tell future travelers what your stay was like..."
                disabled={isSubmitting}
              />
              <div style={{
                display: 'flex', justifyContent: 'space-between',
                marginTop: 8,
              }}>
                <span style={{ fontSize: 13, color: '#B0B0B0' }}>Optional</span>
                <span style={{ fontSize: 13, color: '#B0B0B0' }}>
                  {reviewText.length} characters
                </span>
              </div>
            </div>

            {/* Submit */}
            <button type="submit" className="btn-primary" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <span className="spinner" />
                  Analyzing your review...
                </>
              ) : (
                'Submit Review'
              )}
            </button>
            {errorMsg && (
              <p style={{
                color: '#C13515', fontSize: 14, fontWeight: 500,
                textAlign: 'center', marginTop: 14,
              }}>
                {errorMsg}
              </p>
            )}
          </form>
        </div>
      </div>
    </>
  )
}
