import { useEffect, useRef, useState } from 'react'

const MIN = 3
const MAX = 500

export default function ChatInput({ onSend, disabled }) {
  const [value, setValue] = useState('')
  const ref = useRef(null)

  // Grow the textarea with its content.
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
    <form className="mx-auto w-full max-w-[920px] shrink-0 bg-[var(--surface)] px-4 pb-3 pt-2 min-[761px]:px-8 min-[761px]:pb-4" onSubmit={submit}>
      <div className="flex items-end gap-2 rounded-[14px] border border-[var(--border)] bg-[var(--surface)] p-[7px_7px_7px_16px] shadow-[0_8px_24px_rgba(28,32,44,0.08)] transition focus-within:border-[var(--accent)] focus-within:shadow-[0_0_0_3px_var(--focus),0_8px_24px_rgba(28,32,44,0.08)]">
        <textarea
          ref={ref}
          rows={1}
          value={value}
          maxLength={MAX}
          placeholder="Ask about the news…"
          className="min-h-[38px] max-h-40 flex-1 resize-none border-0 bg-transparent py-2 outline-none [line-height:1.55] text-[var(--text)] placeholder:text-[var(--muted)]"
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={onKeyDown}
        />
        <button type="submit" className="grid size-10 shrink-0 place-items-center rounded-[10px] bg-[var(--accent)] text-white shadow-[0_7px_16px_var(--accent-shadow)] transition hover:-translate-y-px disabled:cursor-not-allowed disabled:opacity-35 disabled:shadow-none" disabled={!valid || disabled} aria-label="Send">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <path d="m5 12 14-7-5 14-3-5-6-2Z" />
          </svg>
        </button>
      </div>
      <div className="mt-[7px] flex justify-between px-[3px] text-[11px] text-[var(--muted)] max-[460px]:justify-end">
        <span className="max-[460px]:hidden">Enter to send · Shift+Enter for new line</span>
        <span>{value.length}/{MAX}</span>
      </div>
    </form>
  )
}
