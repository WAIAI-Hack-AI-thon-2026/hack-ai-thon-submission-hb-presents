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
  return properties.map((property) => {
    if (property.id !== propertyId) return property
    return {
      ...property,
      starRating: profile.overall_rating_avg ?? property.starRating,
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
    }}>
      <div style={{
        maxWidth: 640, margin: '0 auto',
        padding: '0 20px',
        display: 'flex', alignItems: 'center',
        height: 58, gap: 12,
      }}>
        {showBack ? (
          <button
            onClick={onBack}
            style={{
              background: 'none', border: 'none',
              color: 'rgba(255,255,255,0.85)',
              fontSize: 15, fontWeight: 500,
              fontFamily: 'inherit', cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '6px 0',
            }}
          >
            {/* Left arrow SVG */}
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M10 3L5 8l5 5" stroke="currentColor" strokeWidth="2"
                    strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
            Back
          </button>
        ) : (
          /* Logo */
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            {/* Yellow circle with navy lines */}
            <svg width="34" height="34" viewBox="0 0 34 34" fill="none">
              <circle cx="17" cy="17" r="17" fill="#FFC72C"/>
              <rect x="9"  y="11.5" width="16" height="2.5" rx="1.25" fill="#00355F"/>
              <rect x="9"  y="16"   width="11" height="2.5" rx="1.25" fill="#00355F"/>
              <rect x="9"  y="20.5" width="13" height="2.5" rx="1.25" fill="#00355F"/>
            </svg>
            <span style={{
              color: '#fff', fontWeight: 700, fontSize: 17,
              letterSpacing: '-0.3px',
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
        starRating: data.profileUpdate.profile.overall_rating_avg ?? current.starRating,
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
    <div style={{ minHeight: '100vh', background: '#f8fafc' }}>
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
