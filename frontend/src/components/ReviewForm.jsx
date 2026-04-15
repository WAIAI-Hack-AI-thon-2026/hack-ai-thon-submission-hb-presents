import { useState } from 'react'
import StarRating from './StarRating'

const DEMO_SCENARIOS = [
  {
    label: '😠 Angry guest (short review)',
    data: {
      review_id: 'r_0001',
      property_id: 'hotel_rome_01',
      overall_rating: 2,
      review_text: 'Awful stay. Never again.',
      review_text_en: 'Awful stay. Never again.',
      sub_ratings: { roomcleanliness: null, roomamenitiesscore: null },
      stay_nights: 2,
      stay_month: 8,
      property_has_elevator: true,
      property_age_years: 20,
      is_first_time_guest: true,
      party_size: 1,
    },
  },
  {
    label: '😊 Happy guest (rich text)',
    data: {
      review_id: 'r_0002',
      property_id: 'hotel_bangkok_07',
      overall_rating: 5,
      review_text_en:
        'Great location, 5 minutes walk from the main street. The room was clean and the bed was comfortable. Breakfast had good variety.',
      review_text:
        'Great location, 5 minutes walk from the main street. The room was clean and the bed was comfortable. Breakfast had good variety.',
      aspects_mentioned: ['location', 'cleanliness', 'bed'],
      sub_ratings: { convenienceoflocation: 5, roomcleanliness: 5 },
      stay_nights: 3,
      stay_month: 5,
      property_has_elevator: true,
      property_age_years: 6,
      party_size: 2,
    },
  },
  {
    label: '👨‍👩‍👧‍👦 Family trip (mixed rating)',
    data: {
      review_id: 'r_0003',
      property_id: 'hotel_lisbon_03',
      overall_rating: 3.5,
      review_text_en: 'Decent but dated. Room was small for the four of us.',
      review_text: 'Decent but dated. Room was small for the four of us.',
      sub_ratings: { roomcleanliness: 4 },
      stay_nights: 4,
      stay_month: 7,
      party_size: 4,
      property_has_elevator: false,
      property_age_years: 35,
      is_street_facing_room: true,
    },
  },
]

export default function ReviewForm({ onSubmit }) {
  const [rating, setRating] = useState(null)
  const [text, setText] = useState('')
  const [nights, setNights] = useState(1)
  const [partySize, setPartySize] = useState(1)
  const [month, setMonth] = useState(new Date().getMonth() + 1)

  const canSubmit = rating !== null && text.trim().length > 0

  function handleSubmit(e) {
    e.preventDefault()
    if (!canSubmit) return
    onSubmit({
      review_id: `r_${Date.now()}`,
      property_id: 'hotel_demo',
      overall_rating: rating,
      review_text: text,
      review_text_en: text,
      sub_ratings: {},
      stay_nights: nights,
      stay_month: month,
      party_size: partySize,
      is_first_time_guest: true,
    })
  }

  function loadScenario(scenario) {
    onSubmit(scenario.data)
  }

  return (
    <div className="space-y-6">
      {/* Quick demo buttons */}
      <div className="card">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Demo scenarios
        </p>
        <div className="flex flex-col gap-2">
          {DEMO_SCENARIOS.map((s) => (
            <button
              key={s.label}
              type="button"
              onClick={() => loadScenario(s)}
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
          {/* Star rating */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Overall rating
            </label>
            <StarRating value={rating} onChange={setRating} />
            {rating && (
              <p className="mt-1 text-xs text-gray-500">
                {['', 'Terrible', 'Poor', 'Average', 'Good', 'Excellent'][rating]}
              </p>
            )}
          </div>

          {/* Review text */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Your review
            </label>
            <textarea
              rows={4}
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Share your experience — what stood out, what could be better…"
              className="w-full rounded-xl border border-gray-200 px-4 py-3 text-sm
                         focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
                         resize-none placeholder:text-gray-400"
            />
            <p className="mt-1 text-right text-xs text-gray-400">{text.length} chars</p>
          </div>

          {/* Stay details */}
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Nights</label>
              <input
                type="number"
                min={1}
                max={30}
                value={nights}
                onChange={(e) => setNights(Number(e.target.value))}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm
                           focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Guests</label>
              <input
                type="number"
                min={1}
                max={10}
                value={partySize}
                onChange={(e) => setPartySize(Number(e.target.value))}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm
                           focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">Month</label>
              <input
                type="number"
                min={1}
                max={12}
                value={month}
                onChange={(e) => setMonth(Number(e.target.value))}
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm
                           focus:outline-none focus:ring-2 focus:ring-brand-500"
              />
            </div>
          </div>

          <button type="submit" className="btn-primary w-full" disabled={!canSubmit}>
            Submit review →
          </button>
        </form>
      </div>
    </div>
  )
}
