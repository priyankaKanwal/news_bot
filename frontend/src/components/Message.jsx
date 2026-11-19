function formatDate(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

// Only allow http(s) links - article URLs come from external feeds.
function isSafeUrl(url) {
  return typeof url === 'string' && /^https?:\/\//i.test(url)
}

export default function Message({ message }) {
  const { role, text, sources, isError } = message
  const isUser = role === 'user'

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className="grid size-[34px] shrink-0 place-items-center rounded-[10px] border border-[var(--border)] bg-[var(--surface)] text-[var(--accent)] shadow-[0_1px_3px_rgba(28,32,44,0.04)]" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M5 3h14v18H5zM9 7h6M9 11h6M9 15h3" /></svg>
        </div>
      )}
      <div className={`max-w-[78%] rounded-xl border px-4 py-[13px] leading-[1.65] shadow-[0_1px_2px_rgba(20,24,40,0.025)] max-[760px]:max-w-[88%] ${isUser ? 'rounded-br-[4px] border-[var(--accent)] bg-[var(--accent)] text-white shadow-[0_8px_20px_var(--accent-shadow)]' : `rounded-tl-[4px] ${isError ? 'border-[var(--error-border)] bg-[var(--error-bg)] text-[var(--error)]' : 'border-[var(--border)] bg-[var(--message-bg)]'}`}`}>
        <div className="whitespace-pre-wrap [overflow-wrap:anywhere]">{text}</div>
        {sources?.length > 0 && (
          <div className="mt-[14px] border-t border-[var(--border)] pt-3">
            <span className="text-[10px] font-extrabold uppercase tracking-[0.1em] text-[var(--muted)]">Sources</span>
            <ul className="mt-2 grid list-none grid-cols-2 gap-2 p-0 max-[760px]:grid-cols-1">
              {sources.map((s) => {
                const date = formatDate(s.published_at)
                return (
                  <li className="flex min-w-0 flex-col gap-1 rounded-[9px] border border-[var(--border)] bg-[var(--surface)] px-[10px] py-[9px]" key={s.url ?? s.title} title={`Relevance score: ${s.score.toFixed(3)}`}>
                    {isSafeUrl(s.url) ? (
                      <a className="text-[13px] font-bold leading-[1.35] text-[var(--text)] no-underline [overflow-wrap:anywhere] hover:text-[var(--accent)]" href={s.url} target="_blank" rel="noopener noreferrer">
                        {s.title}
                      </a>
                    ) : (
                      <span className="text-[13px] font-bold leading-[1.35] text-[var(--text)] [overflow-wrap:anywhere]">{s.title}</span>
                    )}
                    <span className="text-[11px] text-[var(--muted)]">
                      {s.publisher}
                      {date && ` · ${date}`}
                    </span>
                  </li>
                )
              })}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
