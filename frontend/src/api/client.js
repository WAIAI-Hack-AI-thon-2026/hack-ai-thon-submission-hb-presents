const BASE_URL = import.meta.env.VITE_API_URL || ''

/**
 * Call POST /api/decide with a review text.
 * Returns an AgentDecision object with follow-up questions.
 */
export async function submitReview(reviewText) {
  const res = await fetch(`${BASE_URL}/api/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ review_text: reviewText }),
  })
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}))
    throw new Error(detail?.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

/**
 * Submit collected follow-up answers (placeholder — wire to your DB / webhook).
 */
export async function submitAnswers(answers) {
  console.log('[answers]', answers)
  return { success: true }
}
