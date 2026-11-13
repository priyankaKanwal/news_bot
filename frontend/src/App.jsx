import { useEffect, useRef, useState } from 'react'
import { askQuestion } from './api'
import Message from './components/Message'
import ChatInput from './components/ChatInput'
import './App.css'

const SUGGESTIONS = [
  'What are the latest headlines?',
  'Summarize the top technology news',
  'What is happening in business and markets?',
  'Any major world news today?',
]

let nextId = 1

export default function App() {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const abortRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function send(question) {
    const text = question.trim()
    if (!text || loading) return

    setMessages((prev) => [...prev, { id: nextId++, role: 'user', text }])
    setLoading(true)

    const controller = new AbortController()
    abortRef.current = controller

    try {
      const data = await askQuestion(text, controller.signal)
      setMessages((prev) => [
        ...prev,
        { id: nextId++, role: 'bot', text: data.answer, sources: data.sources },
      ])
    } catch (error) {
      if (error.name === 'AbortError') return
      setMessages((prev) => [
        ...prev,
        { id: nextId++, role: 'bot', text: error.message, isError: true },
      ])
    } finally {
      setLoading(false)
    }
  }

  function clearChat() {
    abortRef.current?.abort()
    setMessages([])
    setLoading(false)
  }

  return (
    <div className="app">
      <header className="header">
        <div className="brand">
          <span className="brand-logo" aria-hidden="true">📰</span>
          <div>
            <h1>AI News Intelligence</h1>
            <p>Ask anything about the news</p>
          </div>
        </div>
        {messages.length > 0 && (
          <button className="ghost-btn" onClick={clearChat}>
            New chat
          </button>
        )}
      </header>

      <main className="chat">
        {messages.length === 0 ? (
          <div className="welcome">
            <h2>What would you like to know?</h2>
            <p>Answers are generated from the news articles in our knowledge base.</p>
            <div className="suggestions">
              {SUGGESTIONS.map((s) => (
                <button key={s} className="chip" onClick={() => send(s)}>
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="messages">
            {messages.map((m) => (
              <Message key={m.id} message={m} />
            ))}
            {loading && (
              <div className="row bot">
                <div className="avatar">AI</div>
                <div className="bubble typing" aria-label="Thinking">
                  <span /><span /><span />
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </main>

      <ChatInput onSend={send} disabled={loading} />
    </div>
  )
}
