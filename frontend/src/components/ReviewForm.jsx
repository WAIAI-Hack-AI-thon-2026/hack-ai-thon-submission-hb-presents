import { useState } from 'react'

const DEMO_REVIEWS = [
  {
    label: 'Angry guest (short)',
    text: 'Awful stay. Never again.',
  },
  {
    label: 'Happy guest (detailed)',
    text: 'Great location, 5 minutes walk from the main street. The room was clean and the bed was comfortable. Breakfast had good variety.',
  },
  {
    label: 'Mixed (family trip)',
    text: 'Decent but dated. Room was small for the four of us. The AC barely worked in the summer heat.',
  },
]

export default function ReviewForm({ onSubmit }) {
  const [text, setText] = useState('')

  const canSubmit = text.trim().length > 0

  function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit) return
    onSubmit(text.trim())
  }

  return (
    <div className="space-y-6">
      {/* Quick demo buttons */}
      <div className="card">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Demo scenarios
        </p>
        <div className="flex flex-col gap-2">
          {DEMO_REVIEWS.map((s) => (
            <button
              key={s.label}
              type="button"
              onClick={() => onSubmit(s.text)}
              className="btn-secondary text-left justify-start text-sm"
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Review form */}
      <div className="card">
        <h2 className="text-lg font-bold text-gray-900 mb-1">How was your stay?</h2>
        <p className="text-sm text-gray-500 mb-6">Tell us about your experience at the hotel.</p>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Your review
            </label>
            <textarea
              rows={4}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Share your experience — what stood out, what could be better..."
              className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm
                         focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
                         resize-none placeholder:text-gray-400"
            />
            <p className="mt-1 text-right text-xs text-gray-400">{text.length} chars</p>
          </div>

          <button type="submit" className="btn-primary w-full" disabled={!canSubmit}>
            Submit review
          </button>
        </form>
      </div>
    </div>
  )
}
