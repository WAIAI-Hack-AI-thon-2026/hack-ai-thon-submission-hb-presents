import { useState } from 'react'
import PropertySelect from './components/PropertySelect'
import ReviewForm     from './components/ReviewForm'
import FollowUpCards  from './components/FollowUpCards'
import ThankYou       from './components/ThankYou'
import { PROPERTIES } from './propertyIntel'

// ── Fallback questions (demo-safe) ──────────────────────────────────────────
const FALLBACK_QUESTIONS = [
  {
    id: 'q_bathroom',
    text: 'How was the bathroom during your stay?',
    options: ['Spotless', 'Average', 'Cleanliness issue', 'Something broken'],
  },
  {
    id: 'q_billing',
    text: 'Were there any surprises on your bill or deposit?',
    options: ['No issues', 'Minor confusion', 'Unexpected charge', 'Still unresolved'],
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
    if (!Array.isArray(data.questions) || data.questions.length === 0)
      throw new Error('Empty questions')
    return data.questions
  } catch (err) {
    console.warn('[/api/analyze] failed, using fallback:', err.message)
    return FALLBACK_QUESTIONS
  }
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
  const [property, setProperty] = useState(null)
  const [questions, setQuestions] = useState([])

  async function handleReviewSubmit({ rating, reviewText }) {
    // button already shows loading state; this resolves when done
    const qs = await analyzeReview({
      propertyId:  property.id,
      city:        property.city,
      country:     property.country,
      rating,
      reviewText,
    })
    setQuestions(qs)
    setStep('followup')
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f8fafc' }}>
      <Header
        showBack={step === 'review'}
        onBack={() => setStep('select')}
      />

      {step === 'select'  && (
        <PropertySelect
          properties={PROPERTIES}
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
          onComplete={() => setStep('done')}
        />
      )}
      {step === 'done' && (
        <ThankYou onReset={() => setStep('select')} />
      )}
    </div>
  )
}
