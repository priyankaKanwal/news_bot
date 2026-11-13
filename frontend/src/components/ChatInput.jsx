import { useEffect, useRef, useState } from 'react'

const MIN = 3
const MAX = 500

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('')
  const ref = useRef(null)

  // auto-grow textarea
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 160) + 'px'
  }, [value])

  useEffect(() => {
    if (!disabled) ref.current?.focus()
  }, [disabled])

  const valid = value.trim().length >= MIN

  function submit(e) {
    e?.preventDefault()
    if (!valid || disabled) return
    onSend(value)
    setValue('')
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) submit(e)
  }

  return (
    <form className="input-bar" onSubmit={submit}>
      <div className="input-wrap">
        <textarea
          ref={ref}
          rows={1}
          value={value}
          maxLength={MAX}
          placeholder="Ask about the news…"
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button type="submit" className="send-btn" disabled={!valid || disabled} aria-label="Send">
          ➤
        </button>
      </div>
      <div className="hint">
        <span>Enter to send · Shift+Enter for new line</span>
        <span>{value.length}/{MAX}</span>
      </div>
    </form>
  )
}
