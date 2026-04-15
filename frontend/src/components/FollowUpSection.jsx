import { useState } from 'react'
import QuestionCard from './QuestionCard'

export default function FollowUpSection({ decision, onSubmit }) {
  const [answers, setAnswers] = useState({})
  const [showRationale, setShowRationale] = useState(false)

  function hasAnswer(value) {
    if (Array.isArray(value)) {
      return value.length > 0
    }
    if (value && typeof value === 'object') {
      const selected = value.selected
      const otherText = value.other_text?.trim() || ''
      if (Array.isArray(selected)) {
        return selected.length > 0 || otherText.length > 0
      }
      return Boolean(selected) || otherText.length > 0
    }
    return Boolean(value && value.toString().trim().length > 0)
  }

  function handleChange({ qid, value }) {
    setAnswers((prev) => ({ ...prev, [qid]: value }))
  }

  function handleSubmit(e) {
    e.preventDefault()
    onSubmit(answers)
  }

  const answered = Object.keys(answers).filter((qid) => {
    return hasAnswer(answers[qid])
  }).length

  return (
    <div className="space-y-6">
      {/* Intro */}
      <div className="text-center space-y-1">
        <p className="text-2xl">🙏</p>
        <h2 className="text-xl font-bold text-gray-900">Thank you for your review!</h2>
        <p className="text-sm text-gray-500">
          A few quick follow-ups to help the property improve.
          <br />
          <span className="text-xs text-gray-400">All questions are optional.</span>
        </p>
      </div>

      {/* Progress */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 rounded-full bg-gray-100 overflow-hidden">
          <div
            className="h-full bg-brand-500 rounded-full transition-all duration-300"
            style={{ width: `${(answered / decision.questions.length) * 100}%` }}
          />
        </div>
        <span className="text-xs font-medium text-gray-500 whitespace-nowrap">
          {answered} / {decision.questions.length}
        </span>
      </div>

      {/* Question cards */}
      <form onSubmit={handleSubmit} className="space-y-4">
        {decision.questions.map((q, i) => (
          <QuestionCard
            key={q.qid}
            question={q}
            index={i}
            onChange={handleChange}
          />
        ))}

        <button type="submit" className="btn-primary w-full">
          Submit answers →
        </button>

        <button
          type="button"
          onClick={() => onSubmit({})}
          className="w-full text-sm text-gray-400 hover:text-gray-600 py-2 transition-colors"
        >
          Skip all
        </button>
      </form>

      {/* Debug: rationale toggle */}
      <div className="border-t border-gray-100 pt-4">
        <button
          type="button"
          onClick={() => setShowRationale((v) => !v)}
          className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
        >
          {showRationale ? '▲ Hide' : '▼ Show'} agent rationale (debug)
        </button>

        {showRationale && (
          <div className="mt-3 rounded-xl bg-gray-900 text-gray-100 text-xs p-4 overflow-auto font-mono space-y-2">
            <p className="text-gray-400 font-semibold uppercase tracking-wider text-[10px]">
              Chosen — rationale
            </p>
            {Object.entries(decision.rationale).map(([qid, reason]) => (
              <div key={qid}>
                <span className="text-brand-400">{qid}</span>
                <br />
                <span className="text-gray-300 ml-2">{reason}</span>
              </div>
            ))}
            {decision.skipped.length > 0 && (
              <>
                <p className="text-gray-400 font-semibold uppercase tracking-wider text-[10px] mt-3">
                  Skipped ({decision.skipped.length})
                </p>
                {decision.skipped.map((s, i) => (
                  <div key={i}>
                    <span className="text-gray-500">{s.qid}</span>
                    {' — '}
                    <span className="text-gray-400">{s.reason}</span>
                  </div>
                ))}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
