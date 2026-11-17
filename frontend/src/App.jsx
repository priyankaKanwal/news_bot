import { useEffect, useRef, useState } from 'react'
import { askQuestion, deleteConversation, getConversation, getConversations } from './api'
import Message from './components/Message'
import ChatInput from './components/ChatInput'
import './App.css'

const SUGGESTIONS = [
  'What are the latest headlines?',
  'Summarize the top technology news',
  'What is happening in business and markets?',
  'Any major world news today?',
]

function toUiMessage(message) {
 return {
   id: message.id,
   role: message.role === 'assistant' ? 'bot' : 'user',
   text: message.content,
   sources: message.sources,
 }
}

export default function App() {
 const [conversations, setConversations] = useState([])
 const [activeConversationId, setActiveConversationId] = useState(null)
 const [messages, setMessages] = useState([])
 const [loading, setLoading] = useState(false)
 const [historyLoading, setHistoryLoading] = useState(true)
 const [historyError, setHistoryError] = useState('')
 const bottomRef = useRef(null)
 const activeConversationRef = useRef(null)
 const selectionVersionRef = useRef(0)

 useEffect(() => {
   bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
 }, [messages, loading])

 useEffect(() => {
   let cancelled = false

   async function loadInitialHistory() {
     try {
       const history = await getConversations()
       if (cancelled) return

       setConversations(history)

       if (history.length > 0) {
         const conversation = await getConversation(history[0].id)
         if (cancelled) return

         activeConversationRef.current = conversation.id
         setActiveConversationId(conversation.id)
         setMessages(conversation.messages.map(toUiMessage))
       }
     } catch (error) {
       if (!cancelled) setHistoryError(error.message)
     } finally {
       if (!cancelled) setHistoryLoading(false)
     }
   }

   loadInitialHistory()
   return () => {
     cancelled = true
   }
 }, [])

 async function refreshHistory() {
   try {
     setConversations(await getConversations())
   } catch (error) {
     setHistoryError(error.message)
   }
 }

 async function selectConversation(conversationId) {
   const selectionVersion = ++selectionVersionRef.current
   activeConversationRef.current = conversationId
   setActiveConversationId(conversationId)
   setMessages([])
   setHistoryError('')

   try {
     const conversation = await getConversation(conversationId)
     if (selectionVersion !== selectionVersionRef.current) return
     setMessages(conversation.messages.map(toUiMessage))
   } catch (error) {
     if (selectionVersion === selectionVersionRef.current) {
       setHistoryError(error.message)
     }
   }
 }

 function startNewChat() {
   selectionVersionRef.current += 1
   activeConversationRef.current = null
   setActiveConversationId(null)
   setMessages([])
   setHistoryError('')
 }

 async function send(question) {
   const text = question.trim()
   if (!text || loading) return

   const selectionVersion = selectionVersionRef.current
   const conversationId = activeConversationRef.current
   const messageId = `pending-${Date.now()}`
   setMessages((prev) => [...prev, { id: messageId, role: 'user', text }])
   setLoading(true)

   try {
     const data = await askQuestion(text, conversationId)
     const savedConversationId = data.conversation_id
     await refreshHistory()

     if (selectionVersion === selectionVersionRef.current) {
       activeConversationRef.current = savedConversationId
       setActiveConversationId(savedConversationId)
       const conversation = await getConversation(savedConversationId)
       if (selectionVersion === selectionVersionRef.current) {
         setMessages(conversation.messages.map(toUiMessage))
       }
     }
   } catch (error) {
     if (error.conversationId) {
       await refreshHistory()
       if (selectionVersion === selectionVersionRef.current) {
         activeConversationRef.current = error.conversationId
         setActiveConversationId(error.conversationId)
       }
     }
     if (selectionVersion === selectionVersionRef.current) {
       setMessages((prev) => [
         ...prev,
         { id: `error-${Date.now()}`, role: 'bot', text: error.message, isError: true },
       ])
     }
   } finally {
     setLoading(false)
   }
 }

 async function removeConversation(event, conversationId) {
   event.stopPropagation()
   if (loading) return

   try {
     await deleteConversation(conversationId)
     const remaining = conversations.filter((item) => item.id !== conversationId)
     setConversations(remaining)

     if (activeConversationRef.current === conversationId) {
       if (remaining.length > 0) {
         await selectConversation(remaining[0].id)
       } else {
         startNewChat()
       }
     }
   } catch (error) {
     setHistoryError(error.message)
   }
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
      </header>

      <div className="workspace">
        <aside className="history" aria-label="Chat history">
          <button className="new-chat-btn" onClick={startNewChat}>+ New chat</button>
          <h2>Recent chats</h2>
          {historyLoading && <p className="history-status">Loading history…</p>}
          {!historyLoading && conversations.length === 0 && (
            <p className="history-status">Your saved chats will appear here.</p>
          )}
          <nav className="history-list">
            {conversations.map((conversation) => (
              <div
                className={`history-item${conversation.id === activeConversationId ? ' active' : ''}`}
                key={conversation.id}
              >
                <button
                  className="history-select"
                  onClick={() => selectConversation(conversation.id)}
                  title={conversation.title}
                >
                  {conversation.title}
                </button>
                <button
                  className="history-delete"
                  onClick={(event) => removeConversation(event, conversation.id)}
                  disabled={loading}
                  aria-label={`Delete ${conversation.title}`}
                  title="Delete chat"
                >
                  ×
                </button>
              </div>
            ))}
          </nav>
        </aside>

        <section className="chat-panel">
          {historyError && <div className="history-error" role="alert">{historyError}</div>}
          <main className="chat">
            {messages.length === 0 ? (
              <div className="welcome">
                <h2>What would you like to know?</h2>
                <p>Answers are generated from the news articles in our knowledge base.</p>
                <div className="suggestions">
                  {SUGGESTIONS.map((suggestion) => (
                    <button key={suggestion} className="chip" onClick={() => send(suggestion)}>
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="messages">
                {messages.map((message) => (
                  <Message key={message.id} message={message} />
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
        </section>
      </div>
    </div>
  )
}
