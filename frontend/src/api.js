const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function request(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_URL}${path}`, options)
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error(`Cannot reach the server. Is the backend running on ${API_URL}?`, { cause: error })
  }

  if (!response.ok) {
    let detail = 'Something went wrong. Please try again.'
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
      else if (response.status === 422) detail = 'Please enter a question between 3 and 500 characters.'
    } catch {
      // Use the generic message if the response is not JSON.
    }
    const error = new Error(detail)
    error.conversationId = response.headers.get('X-Conversation-ID')
    throw error
  }

  if (response.status === 204) return null
  return response.json()
}

export function askQuestion(question, conversationId) {
  return request('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, conversation_id: conversationId }),
  })
}

export function getConversations() {
  return request('/api/conversations')
}

export function getRecentArticles() {
  return request('/api/articles/recent?limit=6')
}

export function getConversation(conversationId) {
  return request(`/api/conversations/${conversationId}`)
}

export function deleteConversation(conversationId) {
  return request(`/api/conversations/${conversationId}`, { method: 'DELETE' })
}
