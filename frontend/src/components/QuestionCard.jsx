import { useState } from 'react'

const ASPECT_EMOJI = {
  bathroom:    '🚿',
  billing:     '💳',
  smell:       '👃',
  amenities:   '📺',
  elevator:    '🛗',
  noise:       '🔊',
  ac_heat:     '❄️',
  pests:       '🐛',
  checkin:     '🔑',
  bed:         '🛏️',
  value:       '💰',
  location:    '📍',
  staff:       '👤',
  cleanliness: '🧹',
  family:      '👨‍👩‍👧',
  renovation:  '🔨',
  catch_all:   '💬',
}

export default function QuestionCard({ question, index, onChange }) {
  const [selected, setSelected] = useState(
    question.response_type === 'multi_select' ? [] : null
  )
  const [text, setText] = useState('')

  function handlePillClick(option) {
    if (question.response_type === 'multi_select') {
      const next = selected.includes(option)
        ? selected.filter((o) => o !== option)
        : [...selected, option]
      setSelected(next)
      onChange({ qid: question.qid, value: next })
    } else {
      setSelected(option)
      onChange({ qid: question.qid, value: option })
    }
  }

  function handleTextChange(e) {
    setText(e.target.value)
    onChange({ qid: question.qid, value: e.target.value })
  }

  const isSelected = (option) =>
    question.response_type === 'multi_select'
      ? selected.includes(option)
      : selected === option

  return (
    <div className={`card space-y-4 ${question.private ? 'border-amber-200 bg-amber-50/30' : ''}`}>
      {/* Header */}
      <div className="flex items-start gap-3">
        <span className="text-2xl mt-0.5 leading-none">
          {ASPECT_EMOJI[question.aspect] || '💬'}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="text-xs font-semibold text-gray-400 tabular-nums">
              Q{index + 1}
            </span>
            <span className="aspect-badge">{question.aspect.replace('_', ' ')}</span>
            {question.private && (
              <span className="inline-flex items-center gap-1 text-xs text-amber-700 font-medium">
                🔒 Private
              </span>
            )}
          </div>
          <p className="text-base font-semibold text-gray-900">{question.text_en}</p>
        </div>
      </div>

      {/* Private notice */}
      {question.private && (
        <div className="private-banner">
          🔒 Your answer goes directly to the property — it won't appear publicly.
        </div>
      )}

      {/* Response area */}
      {(question.response_type === 'quick_tap' ||
        question.response_type === 'yes_no' ||
        question.response_type === 'multi_select') &&
        question.options.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {question.options.map((opt) => (
              <button
                key={opt}
                type="button"
                onClick={() => handlePillClick(opt)}
                className={`pill-option ${
                  isSelected(opt) ? 'pill-option-selected' : 'pill-option-idle'
                }`}
              >
                {question.response_type === 'multi_select' && (
                  <span className="mr-1">{isSelected(opt) ? '✓' : '+'}</span>
                )}
                {opt}
              </button>
            ))}
          </div>
        )}

      {(question.response_type === 'free_text' ||
        question.response_type === 'private_text' ||
        question.response_type === 'voice') && (
        <textarea
          rows={3}
          value={text}
          onChange={handleTextChange}
          placeholder={
            question.response_type === 'private_text'
              ? 'Your private feedback (only seen by the property)…'
              : 'Type your answer…'
          }
          className={`w-full rounded-xl border px-4 py-3 text-sm resize-none
                       focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
                       placeholder:text-gray-400
                       ${question.private
                         ? 'border-amber-200 bg-amber-50'
                         : 'border-gray-200 bg-white'}`}
        />
      )}

      {question.response_type === 'multi_select' && (
        <p className="text-xs text-gray-400">Select all that apply</p>
      )}
    </div>
  )
}
