// Only allow http(s) links - article URLs come from external feeds.
function isSafeUrl(url) {
  return typeof url === 'string' && /^https?:\/\//i.test(url)
}

function renderAnswer(text, sources) {
  return text.split(/(\[\d+\])/g).map((part, index) => {
    const match = part.match(/^\[(\d+)\]$/)
    if (!match) return part

    const source = sources?.[Number(match[1]) - 1]
    if (!source) return part

    const label = source.publisher || source.title || `Source ${match[1]}`
    if (!isSafeUrl(source.url)) {
      return <span key={index} title={source.title}>{`[${label}]`}</span>
    }

    return (
      <a
        key={index}
        className="font-semibold text-[var(--accent)] underline decoration-[var(--accent)]/40 underline-offset-2 hover:decoration-[var(--accent)]"
        href={source.url}
        target="_blank"
        rel="noopener noreferrer"
        title={source.title}
      >
        [{label}]
      </a>
    )
  })
}

export default function Message({ message }) {
  const { role, text, sources, isError } = message
  const isUser = role === 'user'
  const hasCitations = sources?.some((_, index) => text.includes(`[${index + 1}]`))

  return (
    <div className={`flex items-start gap-3 ${isUser ? 'justify-end' : ''}`}>
      {!isUser && (
        <div className="grid size-[34px] shrink-0 place-items-center rounded-[10px] border border-[var(--border)] bg-[var(--surface)] text-[var(--accent)] shadow-[0_1px_3px_rgba(28,32,44,0.04)]" aria-hidden="true">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M5 3h14v18H5zM9 7h6M9 11h6M9 15h3" /></svg>
        </div>
      )}
      <div className={`max-w-[78%] rounded-xl border px-4 py-[13px] leading-[1.65] shadow-[0_1px_2px_rgba(20,24,40,0.025)] max-[760px]:max-w-[88%] ${isUser ? 'rounded-br-[4px] border-[var(--accent)] bg-[var(--accent)] text-white shadow-[0_8px_20px_var(--accent-shadow)]' : `rounded-tl-[4px] ${isError ? 'border-[var(--error-border)] bg-[var(--error-bg)] text-[var(--error)]' : 'border-[var(--border)] bg-[var(--message-bg)]'}`}`}>
        <div className="whitespace-pre-wrap [overflow-wrap:anywhere]">{renderAnswer(text, sources)}</div>
        {!hasCitations && sources?.length > 0 && (
          <div className="mt-2 text-[12px] text-[var(--muted)]">
            Related articles:{' '}
            {sources.map((source, index) => {
              const label = source.publisher || source.title || `Source ${index + 1}`
              return (
                <span key={`${source.url ?? source.title}-${index}`}>
                  {index > 0 && ', '}
                  {isSafeUrl(source.url) ? (
                    <a
                      className="font-semibold text-[var(--accent)] underline underline-offset-2"
                      href={source.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={source.title}
                    >
                      {label}
                    </a>
                  ) : label}
                </span>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
