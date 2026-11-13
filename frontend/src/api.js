const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

export async function askQuestion(question, signal) {
  let response
  try {
    response = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
      signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error('Cannot reach the server. Is the backend running on ' + API_URL + '?', {
      cause: error,
    })
  }

  if (!response.ok) {
    let detail = 'Something went wrong. Please try again.'
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (response.status === 422) detail = 'Please enter a question between 3 and 500 characters.'
    } catch {
      /* keep default message */
    }
    throw new Error(detail)
  }

  return response.json() // { answer, sources: [{ title, publisher, published_at, url, score }] }
}
