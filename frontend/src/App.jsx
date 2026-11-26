import { useEffect, useRef, useState } from 'react'
import { askQuestionStream, deleteConversation, getConversation, getConversations } from './api'
import Message from './components/Message'
import ChatInput from './components/ChatInput'
import NewsPanel from './components/NewsPanel'

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

function Icon({ name, size = 18 }) {
  const paths = {
    plus: <path d="M12 5v14M5 12h14" />,
    menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
    close: <path d="m6 6 12 12M18 6 6 18" />,
    sun: <><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M4.93 4.93l1.42 1.42M17.65 17.65l1.42 1.42M2 12h2M20 12h2M4.93 19.07l1.42-1.42M17.65 6.35l1.42-1.42" /></>,
    moon: <path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5 8.5 8.5 0 1 0 20.5 14.2Z" />,
    chat: <path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4Z" />,
    news: <path d="M4 5h13a2 2 0 0 1 2 2v12H6a2 2 0 0 1-2-2V5ZM19 9h1a1 1 0 0 1 1 1v7a2 2 0 0 1-2 2M8 9h7M8 13h7M8 16h4" />,
    trash: <><path d="M3 6h18M8 6V3h8v3M19 6l-1 15H6L5 6M10 10v7M14 10v7" /></>,
  }
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      {paths[name]}
    </svg>
  )
}

export default function App() {
 const [conversations, setConversations] = useState([])
 const [activeConversationId, setActiveConversationId] = useState(null)
 const [messages, setMessages] = useState([])
 const [loading, setLoading] = useState(false)
 const [historyLoading, setHistoryLoading] = useState(true)
 const [historyError, setHistoryError] = useState('')
 const [sidebarOpen, setSidebarOpen] = useState(false)
 const [newsOpen, setNewsOpen] = useState(false)
 const [theme, setTheme] = useState(() => localStorage.getItem('news-theme') || 'light')
 const bottomRef = useRef(null)
 const activeConversationRef = useRef(null)
 const selectionVersionRef = useRef(0)

 useEffect(() => {
   document.documentElement.dataset.theme = theme
   localStorage.setItem('news-theme', theme)
 }, [theme])

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
   setSidebarOpen(false)

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
   setSidebarOpen(false)
 }

 async function send(question) {
   const text = question.trim()
   if (!text || loading) return

   const selectionVersion = selectionVersionRef.current
   const conversationId = activeConversationRef.current
   const messageId = `pending-${Date.now()}`
   setMessages((prev) => [...prev, { id: messageId, role: 'user', text }])
   const botMessageId = `streaming-${Date.now()}`
   setMessages((prev) => [
     ...prev,
     { id: botMessageId, role: 'bot', text: '' },
   ])
   setLoading(true)

   try {
     const data = await askQuestionStream(text, conversationId, (event) => {
       if (selectionVersion !== selectionVersionRef.current) return

       if (event.type === 'token') {
         setMessages((prev) => prev.map((message) =>
           message.id === botMessageId
             ? { ...message, text: message.text + event.text }
             : message
         ))
       } else if (event.type === 'done') {
         setMessages((prev) => prev.map((message) =>
           message.id === botMessageId
             ? { ...message, sources: event.sources }
             : message
         ))
       }
     })
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
         ...prev.filter((message) => message.id !== botMessageId),
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
   <div className="flex h-full bg-[var(--bg)] text-[var(--text)]">
      <aside className={`z-30 flex w-[278px] shrink-0 flex-col border-r border-[var(--border)] bg-[var(--sidebar)] transition-transform duration-200 max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:w-[min(278px,86vw)] max-lg:shadow-[18px_0_45px_rgba(20,24,40,0.18)] ${sidebarOpen ? 'max-lg:translate-x-0' : 'max-lg:-translate-x-full'}`} aria-label="Chat history">
        <div className="flex h-[72px] items-center justify-between border-b border-[var(--border)] px-[18px]">
          <div className="flex items-center gap-[10px]">
            <span className="grid size-[38px] place-items-center rounded-[11px] bg-[var(--accent)] text-white shadow-[0_8px_18px_var(--accent-shadow)]" aria-hidden="true">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 5h16v14H4zM8 9h8M8 13h5M8 16h8" /></svg>
            </span>
            <div className="flex flex-col">
              <strong className="text-sm tracking-[-0.01em]">News Intelligence</strong>
              <span className="mt-0.5 text-[11px] text-[var(--muted)]">AI Assistant</span>
            </div>
          </div>
          <button className="hidden size-[38px] place-items-center rounded-[10px] border border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--text)] max-lg:grid" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar"><Icon name="close" /></button>
        </div>

        <button className="m-[14px] flex h-[46px] items-center gap-[10px] rounded-[10px] border border-[var(--border)] bg-[var(--surface)] px-3 font-semibold shadow-[0_1px_3px_rgba(28,32,44,0.04)] transition hover:-translate-y-px hover:border-[var(--accent)]" onClick={startNewChat}>
          <Icon name="plus" />
          <span>New conversation</span>
          <kbd className="ml-auto rounded-[5px] border border-[var(--border)] bg-[var(--bg)] px-1.5 py-[3px] font-sans text-[10px] text-[var(--muted)]">⌘ N</kbd>
        </button>

        <div className="min-h-0 flex-1 overflow-y-auto px-[10px] pb-4 pt-1">
          <h2 className="mx-2 mb-2 mt-3 text-[11px] font-bold uppercase tracking-[0.09em] text-[var(--muted)]">Recent</h2>
          {historyLoading && <p className="p-2 text-[13px] text-[var(--muted)]">Loading history…</p>}
          {!historyLoading && conversations.length === 0 && (
            <p className="p-2 text-[13px] text-[var(--muted)]">No conversations yet.</p>
          )}
          <nav className="flex flex-col gap-[3px]">
            {conversations.map((conversation) => (
              <div
                className={`group flex min-h-[42px] items-center rounded-[9px] border p-[3px_5px_3px_7px] transition ${conversation.id === activeConversationId ? 'border-[var(--active-border)] bg-[var(--active)]' : 'border-transparent hover:bg-[var(--hover)]'}`}
                key={conversation.id}
              >
                <button
                  className="flex min-w-0 flex-1 items-center gap-[9px] overflow-hidden border-0 bg-transparent px-1 py-2 text-left text-[13px] text-[var(--text)]"
                  onClick={() => selectConversation(conversation.id)}
                  title={conversation.title}
                >
                  <span className="shrink-0 text-[var(--muted)]"><Icon name="chat" size={16} /></span>
                  <span className="overflow-hidden text-ellipsis whitespace-nowrap">{conversation.title}</span>
                </button>
                <button
                  className="grid size-[30px] shrink-0 place-items-center rounded-[7px] bg-transparent text-[var(--muted)] opacity-0 transition group-hover:opacity-100 hover:bg-[var(--error-bg)] hover:text-[var(--error)] disabled:cursor-not-allowed disabled:opacity-40 max-lg:opacity-100"
                  onClick={(event) => removeConversation(event, conversation.id)}
                  disabled={loading}
                  aria-label={`Delete ${conversation.title}`}
                  title="Delete chat"
                >
                  <Icon name="trash" size={15} />
                </button>
              </div>
            ))}
          </nav>
        </div>
      </aside>
      {sidebarOpen && <button className="fixed inset-0 z-20 border-0 bg-[rgba(18,22,35,0.35)] backdrop-blur-[2px] lg:hidden" onClick={() => setSidebarOpen(false)} aria-label="Close sidebar" />}

      <section className="flex min-w-0 flex-1 flex-col">
        <header className="relative flex h-16 shrink-0 items-center justify-between border-b border-[var(--border)] bg-[var(--surface)] px-3.5 lg:h-[72px] lg:px-6">
          <button className="hidden size-[38px] place-items-center rounded-[10px] border border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--text)] max-lg:grid" onClick={() => setSidebarOpen(true)} aria-label="Open sidebar"><Icon name="menu" /></button>
          <div className="flex items-center gap-2 text-[13px] font-semibold max-lg:absolute max-lg:left-1/2 max-lg:-translate-x-1/2">
            <span className="size-[7px] rounded-full bg-[#36a269] shadow-[0_0_0_3px_rgba(54,162,105,0.12)] max-[460px]:size-2" />
            <span className="max-[460px]:hidden">{activeConversationId ? 'News conversation' : 'New conversation'}</span>
          </div>
          <div className="flex items-center gap-2">
            <button
              className="grid size-[38px] place-items-center rounded-[10px] border border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] transition hover:border-[var(--muted)] hover:text-[var(--text)] xl:hidden"
              onClick={() => setNewsOpen(true)}
              aria-label="Open news by category"
            >
              <Icon name="news" />
            </button>
            <button
              className="grid size-[38px] place-items-center rounded-[10px] border border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] transition hover:border-[var(--muted)] hover:text-[var(--text)]"
              onClick={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')}
              aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
            >
              <Icon name={theme === 'dark' ? 'sun' : 'moon'} />
            </button>
          </div>
        </header>

        <div className="flex min-h-0 flex-1 flex-col bg-[var(--surface)]">
          {historyError && <div className="shrink-0 bg-[var(--error-bg)] px-4 py-[9px] text-[13px] text-[var(--error)]" role="alert">{historyError}</div>}
          <main className="mx-auto min-h-0 w-full max-w-[920px] flex-1 overflow-y-auto px-4 py-5 [scrollbar-color:var(--border)_transparent] [scrollbar-width:thin] lg:px-8 lg:py-7">
            {messages.length === 0 ? (
              <div className="flex min-h-full flex-col items-center justify-center px-0 py-6 text-center max-lg:justify-start max-lg:pt-[8vh]">
                <div className="mb-[18px] grid size-[52px] place-items-center rounded-2xl border border-[var(--border)] bg-[var(--surface)] text-[var(--accent)] shadow-[0_8px_24px_rgba(28,32,44,0.08)] max-[460px]:mb-[14px] max-[460px]:size-[46px]">
                  <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M5 3h14v18H5zM9 7h6M9 11h6M9 15h3" /></svg>
                </div>
                <span className="mb-2 text-[11px] font-extrabold uppercase tracking-[0.12em] text-[var(--accent)]">Your news briefing</span>
                <h2 className="m-0 text-[28px] leading-[1.12] tracking-[-0.035em] lg:text-[clamp(28px,4vw,40px)]">What would you like to know?</h2>
                <p className="mb-5 mt-3 max-w-[520px] text-sm text-[var(--muted)] min-[461px]:mb-7 min-[461px]:text-[15px]">Explore recent stories and get clear answers grounded in trusted sources.</p>
                <div className="grid w-full max-w-[720px] grid-cols-1 gap-[10px] min-[461px]:grid-cols-2 max-lg:max-w-[520px]">
                  {SUGGESTIONS.map((suggestion, index) => (
                    <button key={suggestion} className="group grid min-h-[68px] grid-cols-[32px_1fr_20px] items-center gap-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] p-[14px] text-left text-sm text-[var(--text)] shadow-[0_1px_2px_rgba(20,24,40,0.02)] transition hover:-translate-y-0.5 hover:border-[var(--accent)] hover:shadow-[0_8px_24px_rgba(28,32,44,0.08)] lg:min-h-[82px]" onClick={() => send(suggestion)}>
                      <span className="text-[11px] font-extrabold text-[var(--muted)]">0{index + 1}</span>
                      <span>{suggestion}</span>
                      <span className="translate-x-[-4px] text-lg text-[var(--accent)] opacity-0 transition group-hover:translate-x-0 group-hover:opacity-100">→</span>
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="flex flex-col gap-[22px]">
                {messages.map((message) => (
                  <Message key={message.id} message={message} />
                ))}
                {loading && (
                  <div className="flex items-start gap-3">
                    <div className="grid size-[34px] shrink-0 place-items-center rounded-[10px] border border-[var(--border)] bg-[var(--surface)] text-[var(--accent)] shadow-[0_1px_3px_rgba(28,32,44,0.04)]" aria-hidden="true"><Icon name="chat" size={16} /></div>
                    <div className="flex gap-[5px] rounded-xl border border-[var(--border)] bg-[var(--message-bg)] p-4" aria-label="Thinking">
                      <span className="size-1.5 animate-[bounce_1.2s_infinite_ease-in-out] rounded-full bg-[var(--muted)]" /><span className="size-1.5 animate-[bounce_1.2s_infinite_ease-in-out] rounded-full bg-[var(--muted)] [animation-delay:150ms]" /><span className="size-1.5 animate-[bounce_1.2s_infinite_ease-in-out] rounded-full bg-[var(--muted)] [animation-delay:300ms]" />
                    </div>
                  </div>
                )}
                <div ref={bottomRef} />
              </div>
            )}
          </main>
          <ChatInput onSend={send} disabled={loading} />
        </div>
      </section>

      {newsOpen && <button className="fixed inset-0 z-20 border-0 bg-[rgba(18,22,35,0.35)] backdrop-blur-[2px] xl:hidden" onClick={() => setNewsOpen(false)} aria-label="Close news panel" />}
      <NewsPanel
        open={newsOpen}
        onClose={() => setNewsOpen(false)}
        onAsk={(question) => {
          setNewsOpen(false)
          send(question)
        }}
      />
    </div>
  )
}
