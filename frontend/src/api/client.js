const BASE_URL = import.meta.env.VITE_API_URL || ''

/**
 * Call POST /api/decide with a ReviewContext payload.
 * Returns an AgentDecision object.
 */
export async function submitReview(reviewData) {
  const res = await fetch(`${BASE_URL}/api/decide`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(reviewData),
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
export async function submitAnswers(reviewId, answers) {
  // TODO: implement when the answers endpoint is ready
  console.log('[answers]', reviewId, answers)
  return { success: true }
}
