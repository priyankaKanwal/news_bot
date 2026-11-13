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
              {sources.map((s) => (
                <li key={s.name} title={`Relevance score: ${s.score.toFixed(3)}`}>
                  <span className="source-name">{s.name}</span>
                  <span className="source-score">{s.score.toFixed(2)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
