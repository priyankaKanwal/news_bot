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
    <div className={`row ${role}`}>
      {!isUser && <div className="avatar">AI</div>}
      <div className={`bubble${isError ? ' error' : ''}`}>
        <div className="text">{text}</div>
        {sources?.length > 0 && (
          <div className="sources">
            <span className="sources-label">Sources</span>
            <ul>
              {sources.map((s) => {
                const date = formatDate(s.published_at)
                return (
                  <li key={s.url ?? s.title} title={`Relevance score: ${s.score.toFixed(3)}`}>
                    {isSafeUrl(s.url) ? (
                      <a className="source-title" href={s.url} target="_blank" rel="noopener noreferrer">
                        {s.title}
                      </a>
                    ) : (
                      <span className="source-title">{s.title}</span>
                    )}
                    <span className="source-meta">
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
