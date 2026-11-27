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

export async function askQuestionStream(question, conversationId, onEvent) {
  let response
  try {
    response = await fetch(`${API_URL}/api/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question, conversation_id: conversationId }),
    })
  } catch (error) {
    if (error.name === 'AbortError') throw error
    throw new Error(`Cannot reach the server. Is the backend running on ${API_URL}?`, { cause: error })
  }

  if (!response.ok) {
    let detail = 'Something went wrong. Please try again.'
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      // Use the generic message when FastAPI does not return JSON.
    }
    const error = new Error(detail)
    error.conversationId = response.headers.get('X-Conversation-ID')
    throw error
  }

  const conversationIdHeader = response.headers.get('X-Conversation-ID')
  const reader = response.body?.getReader()
  if (!reader) throw new Error('Streaming is not supported by this server response.')

  const decoder = new TextDecoder()
  let buffer = ''
  let result = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const chunks = buffer.split('\n\n')
    buffer = chunks.pop() ?? ''

    for (const chunk of chunks) {
      const line = chunk.split('\n').find((item) => item.startsWith('data: '))
      if (!line) continue

      const event = JSON.parse(line.slice(6))
      onEvent(event)
      if (event.type === 'done' || event.type === 'error') result = event
    }
  }

  if (!result) throw new Error('The answer stream ended before completion.')
  if (result.type === 'error') throw new Error(result.message)

  return {
    conversation_id: conversationIdHeader,
    answer: result.answer,
    sources: result.sources,
  }
}

export function getConversations() {
  return request('/api/conversations')
}

export function getRecentArticles({ limit = 6, offset = 0, category } = {}) {
  const params = new URLSearchParams({ limit, offset })
  if (category) params.set('category', category)
  return request(`/api/articles/recent?${params}`)
}

export function getArticleCategories() {
  return request('/api/articles/categories')
}

export function getConversation(conversationId) {
  return request(`/api/conversations/${conversationId}`)
}

export function deleteConversation(conversationId) {
  return request(`/api/conversations/${conversationId}`, { method: 'DELETE' })
}

export function runIngestion() {
  return request('/api/ingestion/run', { method: 'POST' })
}
