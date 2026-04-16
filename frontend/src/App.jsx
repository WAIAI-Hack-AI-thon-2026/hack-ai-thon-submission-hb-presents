import { useEffect, useState } from 'react'
import PropertySelect from './components/PropertySelect'
import ReviewForm     from './components/ReviewForm'
import FollowUpCards  from './components/FollowUpCards'
import ThankYou       from './components/ThankYou'

// ── Fallback questions (demo-safe) ──────────────────────────────────────────
const FALLBACK_QUESTIONS = [
  {
    id: 'q_bathroom',
    text: 'How was the bathroom during your stay?',
    options: ['Spotless', 'Average', 'Cleanliness issue', 'Something broken'],
    aspect: 'bathroom_quality',
    role: 'information_gap',
  },
  {
    id: 'q_billing',
    text: 'Were there any surprises on your bill or deposit?',
    options: ['No issues', 'Minor confusion', 'Unexpected charge', 'Still unresolved'],
    aspect: 'value_price',
    role: 'information_gap',
  },
]

// ── API call ────────────────────────────────────────────────────────────────
async function analyzeReview(payload) {
  try {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 25000)
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })
    clearTimeout(timer)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    console.log('[/api/analyze] profile update:', data.profileUpdate)
    if (!Array.isArray(data.questions) || data.questions.length === 0)
      throw new Error('Empty questions')
    return data.questions
  } catch (err) {
    console.warn('[/api/analyze] failed, using fallback:', err.message)
    return FALLBACK_QUESTIONS
  }
}

async function loadProperties() {
  const res = await fetch('/api/properties')
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  const data = await res.json()
  return Array.isArray(data.properties) ? data.properties : []
}

function applyProfileToProperties(properties, propertyId, profile) {
  if (!profile || !propertyId) return properties
  const nextStarRating = profile.star_rating != null && profile.star_rating !== ''
    ? Number(profile.star_rating)
    : null
  return properties.map((property) => {
    if (property.id !== propertyId) return property
    return {
      ...property,
      starRating: nextStarRating ?? property.starRating,
      totalReviews: typeof profile.total_reviews === 'number' ? profile.total_reviews : property.totalReviews,
    }
  })
}

// ── Header ──────────────────────────────────────────────────────────────────
function Header({ showBack, onBack }) {
  return (
    <header style={{
      background: '#00355F',
      position: 'sticky', top: 0, zIndex: 50,
      boxShadow: '0 2px 8px rgba(0,0,0,0.12)',
    }}>
      <div style={{
        maxWidth: 640, margin: '0 auto',
        padding: '0 24px',
        display: 'flex', alignItems: 'center',
        height: 64, gap: 14,
      }}>
        {showBack ? (
          <button
            onClick={onBack}
            style={{
              background: 'rgba(255,255,255,0.1)', border: 'none',
              color: '#fff',
              fontSize: 14, fontWeight: 600,
              fontFamily: 'inherit', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '8px 14px', borderRadius: 8,
              transition: 'background 0.15s ease',
            }}
            onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.18)'}
            onMouseLeave={(e) => e.currentTarget.style.background = 'rgba(255,255,255,0.1)'}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="2"
                    strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Back
          </button>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
              <circle cx="18" cy="18" r="18" fill="#FFC72C"/>
              <rect x="10" y="12" width="16" height="2.5" rx="1.25" fill="#00355F"/>
              <rect x="10" y="17" width="11" height="2.5" rx="1.25" fill="#00355F"/>
              <rect x="10" y="22" width="13" height="2.5" rx="1.25" fill="#00355F"/>
            </svg>
            <span style={{
              color: '#fff', fontWeight: 700, fontSize: 18,
              letterSpacing: '-0.4px',
            }}>
              Ask What Matters
            </span>
          </div>
        )}
      </div>
    </header>
  )
}

// ── App ─────────────────────────────────────────────────────────────────────
export default function App() {
  const [step,     setStep]     = useState('select')   // select|review|followup|done
  const [properties, setProperties] = useState([])
  const [property, setProperty] = useState(null)
  const [questions, setQuestions] = useState([])
  const [reviewText, setReviewText] = useState('')

  useEffect(() => {
    loadProperties()
      .then(setProperties)
      .catch((err) => console.warn('[/api/properties] failed:', err.message))
  }, [])

  async function handleReviewSubmit({ rating, reviewText }) {
    // button already shows loading state; this resolves when done
    setReviewText(reviewText)
    const submissionId = globalThis.crypto?.randomUUID?.() || `review-${Date.now()}-${Math.random().toString(36).slice(2)}`
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), 25000)
    const res = await fetch('/api/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        propertyId:  property.id,
        city:        property.city,
        country:     property.country,
        rating,
        reviewText,
        submissionId,
      }),
      signal: controller.signal,
    })
    clearTimeout(timer)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const data = await res.json()
    console.log('[/api/analyze] profile update:', data.profileUpdate)
    const qs = Array.isArray(data.questions) && data.questions.length > 0
      ? data.questions
      : FALLBACK_QUESTIONS
    if (data.profileUpdate?.profile) {
      setProperties((current) => applyProfileToProperties(current, property.id, data.profileUpdate.profile))
      setProperty((current) => current ? {
        ...current,
        starRating: data.profileUpdate.profile.star_rating != null && data.profileUpdate.profile.star_rating !== ''
          ? Number(data.profileUpdate.profile.star_rating)
          : current.starRating,
        totalReviews: typeof data.profileUpdate.profile.total_reviews === 'number'
          ? data.profileUpdate.profile.total_reviews
          : current.totalReviews,
      } : current)
    }
    setQuestions(qs)
    setStep('followup')
  }

  async function handleFollowUpComplete({ answers = {}, questions: askedQuestions = [] } = {}) {
    try {
      const res = await fetch('/api/submit-followups', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          propertyId: property?.id || '',
          questions: askedQuestions,
          answers,
        }),
      })
      const data = await res.json().catch(() => null)
      console.log('[submit-followups] updated profile response:', data)
      if (data?.profile) {
        setProperties((current) => applyProfileToProperties(current, property?.id, data.profile))
        setProperty((current) => current ? {
          ...current,
          totalReviews: typeof data.profile.total_reviews === 'number'
            ? data.profile.total_reviews
            : current.totalReviews,
        } : current)
      }
      if (!res.ok) {
        console.warn('[/api/submit-followups] request failed:', data || res.status)
      }
    } catch (err) {
      console.warn('[/api/submit-followups] failed:', err.message)
    }
    setStep('done')
  }

  return (
    <div style={{ minHeight: '100vh', background: '#ffffff' }}>
      <Header
        showBack={step === 'review'}
        onBack={() => setStep('select')}
      />

      {step === 'select'  && (
        <PropertySelect
          properties={properties}
          onSelect={(p) => { setProperty(p); setStep('review') }}
        />
      )}
      {step === 'review'  && (
        <ReviewForm
          property={property}
          onSubmit={handleReviewSubmit}
        />
      )}
      {step === 'followup' && (
        <FollowUpCards
          property={property}
          questions={questions}
          reviewText={reviewText}
          onComplete={handleFollowUpComplete}
        />
      )}
      {step === 'done' && (
        <ThankYou onReset={() => setStep('select')} />
      )}
    </div>
  )
}
