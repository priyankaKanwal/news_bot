function formatDate(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

function isSafeUrl(url) {
  return typeof url === 'string' && /^https?:\/\//i.test(url)
}

export default function RecentNews({ articles, loading, error }) {
  return (
    <section className="mt-10 w-full max-w-[720px] text-left" aria-label="Recent news">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted)]">From your news feed</span>
          <h3 className="mb-0 mt-1 text-base font-bold tracking-[-0.02em]">Recent stories</h3>
        </div>
        <span className="text-right text-[11px] text-[var(--muted)]">Latest indexed articles</span>
      </div>

      {loading && <p className="py-4 text-center text-sm text-[var(--muted)]">Loading recent stories…</p>}
      {error && <p className="rounded-lg border border-[var(--error-border)] bg-[var(--error-bg)] px-3 py-2 text-sm text-[var(--error)]" role="alert">{error}</p>}
      {!loading && !error && articles.length === 0 && (
        <p className="rounded-lg border border-dashed border-[var(--border)] px-4 py-5 text-center text-sm text-[var(--muted)]">
          No recent articles are available yet. Try again after the news feeds have been ingested.
        </p>
      )}

      {articles.length > 0 && (
        <ul className="grid list-none grid-cols-1 gap-2 p-0 min-[540px]:grid-cols-2">
          {articles.map((article) => {
            const date = formatDate(article.published_at)
            return (
              <li key={article.article_id}>
                <a
                  className={`group flex h-full min-h-[112px] flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3.5 text-[var(--text)] no-underline shadow-[0_1px_2px_rgba(20,24,40,0.02)] transition hover:-translate-y-0.5 hover:border-[var(--accent)] hover:shadow-[0_8px_24px_rgba(28,32,44,0.08)] ${isSafeUrl(article.url) ? '' : 'pointer-events-none'}`}
                  href={isSafeUrl(article.url) ? article.url : undefined}
                  target={isSafeUrl(article.url) ? '_blank' : undefined}
                  rel={isSafeUrl(article.url) ? 'noopener noreferrer' : undefined}
                  aria-label={isSafeUrl(article.url) ? `Read ${article.title} from ${article.publisher}` : undefined}
                >
                  <span className="mb-2 flex items-center justify-between gap-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--muted)]">
                    <span className="truncate">{article.category || article.publisher}</span>
                    <span className="shrink-0">{date}</span>
                  </span>
                  <span className="line-clamp-2 text-left text-[13px] font-semibold leading-[1.4] group-hover:text-[var(--accent)]">{article.title}</span>
                  <span className="mt-auto flex items-center justify-between gap-2 pt-3 text-[11px] text-[var(--muted)]">
                    <span className="truncate">{article.publisher}</span>
                    <span className="shrink-0 text-[var(--accent)]" aria-hidden="true">↗</span>
                  </span>
                </a>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
