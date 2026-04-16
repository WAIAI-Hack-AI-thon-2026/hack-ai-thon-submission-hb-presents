import { useState } from 'react'

const STAR_LABELS = { 1: 'Terrible', 2: 'Poor', 3: 'Okay', 4: 'Good', 5: 'Excellent' }
const RATING_FIELDS = [
  ['roomcleanliness', 'Room cleanliness'],
  ['service', 'Service'],
  ['roomcomfort', 'Room comfort'],
  ['hotelcondition', 'Hotel condition'],
  ['roomquality', 'Room quality'],
  ['convenienceoflocation', 'Convenience of location'],
  ['neighborhoodsatisfaction', 'Neighborhood satisfaction'],
  ['valueformoney', 'Value for money'],
  ['roomamenitiesscore', 'Room amenities'],
  ['communication', 'Communication'],
  ['ecofriendliness', 'Eco-friendliness'],
  ['checkin', 'Check-in'],
  ['onlinelisting', 'Online listing'],
  ['location', 'Location'],
]

function createInitialRatings() {
  return Object.fromEntries([['overall', 0], ...RATING_FIELDS.map(([key]) => [key, 0])])
}

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
  const [ratings, setRatings]         = useState(createInitialRatings)
  const [reviewText, setReviewText]   = useState('')
  const [isSubmitting, setSubmitting] = useState(false)

  const canSubmit = ratings.overall > 0 && reviewText.trim().length > 0 && !isSubmitting

  function setRatingValue(field, value) {
    setRatings((current) => ({ ...current, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit) return
    setSubmitting(true)
    try {
      await onSubmit({ rating: ratings, reviewText })
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
              <StarPicker value={ratings.overall} onChange={(value) => setRatingValue('overall', value)} />
            </div>

            <div style={{ marginBottom: 28 }}>
              <label style={{
                display: 'block', fontSize: 12, fontWeight: 700,
                color: '#64748b', textTransform: 'uppercase',
                letterSpacing: '0.06em', marginBottom: 12,
              }}>
                Category ratings
              </label>
              <div style={{ display: 'grid', gap: 16 }}>
                {RATING_FIELDS.map(([field, label]) => (
                  <div
                    key={field}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: 16,
                      padding: '14px 16px',
                      border: '1px solid #e2e8f0',
                      borderRadius: 14,
                      background: '#fff',
                    }}
                  >
                    <div>
                      <div style={{ fontSize: 14, fontWeight: 600, color: '#1e293b' }}>
                        {label}
                      </div>
                      <div style={{ fontSize: 12, color: '#94a3b8', marginTop: 2 }}>
                        Leave unrated to send `0.0`
                      </div>
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
