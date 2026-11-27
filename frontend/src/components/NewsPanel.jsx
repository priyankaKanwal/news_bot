import { useEffect, useMemo, useState } from 'react'
import { getArticleCategories, getRecentArticles, runIngestion } from '../api'

const ALL = 'All'
const ALL_FETCH_LIMIT = 30
const PER_SECTION = 4
const PAGE_SIZE = 10

function formatDate(iso) {
  if (!iso) return ''
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(undefined, { day: 'numeric', month: 'short' })
}

function isSafeUrl(url) {
  return typeof url === 'string' && /^https?:\/\//i.test(url)
}

function ArticleCard({ article }) {
  const safe = isSafeUrl(article.url)
  return (
    <a
      className={`group flex flex-col rounded-xl border border-[var(--border)] bg-[var(--surface)] p-3 text-[var(--text)] no-underline transition hover:border-[var(--accent)] hover:shadow-[0_6px_18px_rgba(28,32,44,0.08)] ${safe ? '' : 'pointer-events-none'}`}
      href={safe ? article.url : undefined}
      target={safe ? '_blank' : undefined}
      rel={safe ? 'noopener noreferrer' : undefined}
      aria-label={safe ? `Read ${article.title} from ${article.publisher}` : undefined}
    >
      <span className="line-clamp-3 text-[13px] font-semibold leading-[1.4] group-hover:text-[var(--accent)]">{article.title}</span>
      <span className="mt-2 flex items-center justify-between gap-2 text-[11px] text-[var(--muted)]">
        <span className="truncate">{article.publisher}</span>
        <span className="shrink-0">{formatDate(article.published_at)}</span>
      </span>
    </a>
  )
}

function SkeletonList() {
  return (
    <div className="flex flex-col gap-2" aria-label="Loading news">
      {[0, 1, 2, 3].map((item) => (
        <div key={item} className="h-[84px] animate-pulse rounded-xl border border-[var(--border)] bg-[var(--message-bg)]" />
      ))}
    </div>
  )
}

export default function NewsPanel({ open, onClose, onAsk }) {
  const [categories, setCategories] = useState([])
  const [active, setActive] = useState(ALL)
  const [articles, setArticles] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [hasMore, setHasMore] = useState(false)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshMessage, setRefreshMessage] = useState('')

  useEffect(() => {
    let cancelled = false
    getArticleCategories()
      .then((data) => { if (!cancelled) setCategories(data) })
      .catch(() => { /* The article request below surfaces connection errors. */ })
    return () => { cancelled = true }
  }, [reloadKey])

  useEffect(() => {
    let cancelled = false
    const isAll = active === ALL
    const limit = isAll ? ALL_FETCH_LIMIT : PAGE_SIZE

    getRecentArticles({ limit, category: isAll ? undefined : active })
      .then((data) => {
        if (cancelled) return
        setArticles(data)
        setHasMore(!isAll && data.length === limit)
      })
      .catch((err) => { if (!cancelled) setError(err.message) })
      .finally(() => { if (!cancelled) setLoading(false) })

    return () => { cancelled = true }
  }, [active, reloadKey])

  function selectTab(category) {
    if (category === active) return
    setLoading(true)
    setError('')
    setActive(category)
  }

  function retry() {
    setLoading(true)
    setError('')
    setReloadKey((key) => key + 1)
  }

  async function refreshFeed() {
    if (refreshing) return
    setRefreshing(true)
    setRefreshMessage('')
    try {
      const report = await runIngestion()
      setLoading(true)
      setError('')
      setReloadKey((key) => key + 1)
      setRefreshMessage(
        report.articles_saved
          ? `${report.articles_saved} new article${report.articles_saved === 1 ? '' : 's'} added`
          : 'Feed is up to date',
      )
    } catch (err) {
      setRefreshMessage(err.message)
    } finally {
      setRefreshing(false)
    }
  }

  async function loadMore() {
    setLoadingMore(true)
    try {
      const data = await getRecentArticles({ limit: PAGE_SIZE, offset: articles.length, category: active })
      setArticles((prev) => [...prev, ...data])
      setHasMore(data.length === PAGE_SIZE)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoadingMore(false)
    }
  }

  const sections = useMemo(() => {
    const groups = new Map()
    for (const article of articles) {
      if (!groups.has(article.category)) groups.set(article.category, [])
      groups.get(article.category).push(article)
    }
    const order = categories.map((item) => item.category)
    return [...groups.entries()].sort(([a], [b]) => {
      const ia = order.indexOf(a)
      const ib = order.indexOf(b)
      return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib)
    })
  }, [articles, categories])

  const tabs = [{ category: ALL }, ...categories]
  const empty = !loading && !error && articles.length === 0

  return (
    <aside
      className={`z-30 flex w-[min(380px,92vw)] shrink-0 flex-col border-l border-[var(--border)] bg-[var(--sidebar)] pb-[env(safe-area-inset-bottom)] shadow-[-18px_0_45px_rgba(20,24,40,0.18)] transition-transform duration-200 max-xl:fixed max-xl:inset-y-0 max-xl:right-0 xl:static xl:w-[340px] xl:translate-x-0 xl:shadow-none 2xl:w-[380px] ${open ? 'max-xl:translate-x-0' : 'max-xl:translate-x-full'}`}
      aria-label="News by category"
    >
      <div className="flex h-16 shrink-0 items-center justify-between border-b border-[var(--border)] px-4 lg:h-[72px]">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-[var(--muted)]">From your news feed</span>
          <h2 className="m-0 text-base font-bold tracking-[-0.02em]">Latest news</h2>
        </div>
        <div className="flex items-center gap-2">
          <button
            className="grid size-[38px] place-items-center rounded-[10px] border border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] transition hover:border-[var(--accent)] hover:text-[var(--text)] disabled:cursor-not-allowed disabled:opacity-50"
            onClick={refreshFeed}
            disabled={refreshing}
            aria-label="Refresh feed"
            title={refreshing ? 'Refreshing feed' : 'Refresh feed'}
          >
            <svg className={refreshing ? 'animate-spin' : ''} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M20 6v5h-5" />
              <path d="M19 11a7 7 0 1 0-2.05 4.95" />
            </svg>
          </button>
          <button className="grid size-[38px] place-items-center rounded-[10px] border border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:text-[var(--text)] xl:hidden" onClick={onClose} aria-label="Close news panel">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
          </button>
        </div>
      </div>

      {refreshMessage && (
        <div className="border-b border-[var(--border)] px-4 py-2 text-xs text-[var(--muted)]" role="status" aria-live="polite">
          {refreshMessage}
        </div>
      )}

      <div className="flex shrink-0 gap-2 overflow-x-auto border-b border-[var(--border)] px-4 py-3 [scrollbar-width:none]" role="tablist" aria-label="News categories">
        {tabs.map((tab) => (
          <button
            key={tab.category}
            role="tab"
            aria-selected={active === tab.category}
            className={`flex min-h-[34px] shrink-0 items-center gap-1.5 whitespace-nowrap rounded-full border px-3 text-xs font-semibold transition ${active === tab.category ? 'border-[var(--accent)] bg-[var(--accent)] text-white' : 'border-[var(--border)] bg-[var(--surface)] text-[var(--muted)] hover:border-[var(--accent)] hover:text-[var(--text)]'}`}
            onClick={() => selectTab(tab.category)}
          >
            {tab.category}
            {tab.count !== undefined && <span className="opacity-70">{tab.count}</span>}
          </button>
        ))}
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4 [scrollbar-color:var(--border)_transparent] [scrollbar-width:thin]">
        {loading && <SkeletonList />}
        {error && (
          <div className="rounded-lg border border-[var(--error-border)] bg-[var(--error-bg)] px-3 py-2 text-sm text-[var(--error)]" role="alert">
            {error}
            <button className="ml-2 font-semibold underline" onClick={retry}>Retry</button>
          </div>
        )}
        {empty && (
          <p className="rounded-lg border border-dashed border-[var(--border)] px-4 py-5 text-center text-sm text-[var(--muted)]">
            No articles in this category yet. Try again after the feeds have been ingested.
          </p>
        )}

        {!loading && active === ALL && sections.map(([category, items]) => (
          <section key={category} className="mb-5" aria-label={category}>
            <div className="mb-2 flex items-center justify-between gap-2">
              <h3 className="m-0 text-[11px] font-bold uppercase tracking-[0.09em] text-[var(--muted)]">{category}</h3>
              <div className="flex gap-3 text-[11px] font-semibold text-[var(--accent)]">
                <button onClick={() => onAsk(`Summarize the latest ${category} news`)}>Ask AI</button>
                <button onClick={() => selectTab(category)}>See all</button>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              {items.slice(0, PER_SECTION).map((article) => <ArticleCard key={article.article_id} article={article} />)}
            </div>
          </section>
        ))}

        {!loading && active !== ALL && articles.length > 0 && (
          <>
            <button className="mb-3 w-full rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-2 text-xs font-semibold text-[var(--accent)] transition hover:border-[var(--accent)]" onClick={() => onAsk(`Summarize the latest ${active} news`)}>
              Ask AI to summarize {active}
            </button>
            <div className="flex flex-col gap-2">
              {articles.map((article) => <ArticleCard key={article.article_id} article={article} />)}
            </div>
            {hasMore && (
              <button className="mt-3 w-full rounded-lg border border-[var(--border)] px-3 py-2 text-xs font-semibold text-[var(--muted)] hover:text-[var(--text)] disabled:opacity-50" onClick={loadMore} disabled={loadingMore}>
                {loadingMore ? 'Loading…' : 'Load more'}
              </button>
            )}
          </>
        )}
      </div>
    </aside>
  )
}
