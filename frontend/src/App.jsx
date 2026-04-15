import { useState } from 'react'
import ReviewForm from './components/ReviewForm'
import FollowUpSection from './components/FollowUpSection'
import ThankYou from './components/ThankYou'
import { submitReview } from './api/client'

// step: 'form' | 'loading' | 'followup' | 'done'

export default function App() {
  const [step, setStep] = useState('form')
  const [decision, setDecision] = useState(null)
  const [error, setError] = useState(null)
  const [reviewCtx, setReviewCtx] = useState(null)

  async function handleReviewSubmit(formData) {
    setStep('loading')
    setError(null)
    setReviewCtx(formData)
    try {
      const result = await submitReview(formData)
      setDecision(result)
      setStep(result.questions.length > 0 ? 'followup' : 'done')
    } catch (err) {
      setError(err.message || 'Could not reach the agent. Is the backend running?')
      setStep('form')
    }
  }

  function handleAnswersSubmit() {
    setStep('done')
  }

  function handleReset() {
    setStep('form')
    setDecision(null)
    setError(null)
    setReviewCtx(null)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-brand-50 via-gray-50 to-white">
      {/* Header */}
      <header className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-lg mx-auto px-4 py-4 flex items-center gap-3">
          <span className="text-2xl">🏨</span>
          <div>
            <h1 className="text-base font-bold text-gray-900 leading-tight">Ask What Matters</h1>
            <p className="text-xs text-gray-500">Adaptive AI · HB Presents</p>
          </div>
          {step !== 'form' && (
            <button
              onClick={handleReset}
              className="ml-auto text-xs text-brand-600 hover:text-brand-800 font-medium"
            >
              ← New review
            </button>
          )}
        </div>
      </header>

      {/* Progress bar */}
      <div className="h-1 bg-gray-100">
        <div
          className="h-full bg-brand-500 transition-all duration-500"
          style={{
            width:
              step === 'form'     ? '33%' :
              step === 'loading'  ? '55%' :
              step === 'followup' ? '70%' : '100%',
          }}
        />
      </div>

      <main className="max-w-lg mx-auto px-4 py-8">
        {error && (
          <div className="mb-4 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-sm">
            ⚠️ {error}
          </div>
        )}

        {step === 'form' && (
          <ReviewForm onSubmit={handleReviewSubmit} />
        )}

        {step === 'loading' && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="w-10 h-10 border-4 border-brand-200 border-t-brand-600 rounded-full animate-spin" />
            <p className="text-sm text-gray-500 font-medium">Analyzing your review…</p>
          </div>
        )}

        {step === 'followup' && decision && (
          <FollowUpSection
            decision={decision}
            onSubmit={handleAnswersSubmit}
          />
        )}

        {step === 'done' && (
          <ThankYou onReset={handleReset} />
        )}
      </main>
    </div>
  )
}
