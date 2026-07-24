/* Hallmark · pre-emit critique: P4 H5 E4 S5 R4 V5 */
/* Hallmark · genre: atmospheric · macrostructure: Signal Feed · theme: custom Night Garden */

import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Filter, GitPullRequest, Loader2, Search } from 'lucide-react'

function LoadingSkeleton() {
  return (
    <div className="page-frame" style={{ display: 'grid', gap: 'var(--space-md)' }}>
      <div className="skeleton" style={{ height: 160 }} />
      {[...Array(5)].map((_, i) => <div key={i} className="skeleton" style={{ height: 98 }} />)}
    </div>
  )
}

function ReviewBadge({ review }) {
  if (!review) {
    return <span className="mono" style={{ color: 'var(--color-ink-4)', fontSize: 'var(--text-xs)' }}>unscanned</span>
  }
  if (review.status === 'running') {
    return (
      <span className="mono" style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2xs)', color: 'var(--color-accent)', background: 'var(--color-accent-bg)', borderRadius: 'var(--radius-full)', padding: '0.35rem 0.65rem', fontSize: 'var(--text-xs)', fontWeight: 800 }}>
        <Loader2 className="w-3 h-3" style={{ animation: 'orbit-turn 1.2s linear infinite' }} />
        scanning
      </span>
    )
  }
  if (review.status === 'failed') {
    return <span className="mono" style={{ color: 'var(--color-danger)', background: 'var(--color-danger-bg)', borderRadius: 'var(--radius-full)', padding: '0.35rem 0.65rem', fontSize: 'var(--text-xs)', fontWeight: 800 }}>failed</span>
  }
  const map = {
    approve: ['clear', 'var(--color-success)', 'var(--color-success-bg)'],
    request_changes: ['mutate', 'var(--color-danger)', 'var(--color-danger-bg)'],
    comment: ['observe', 'var(--color-warning)', 'var(--color-warning-bg)'],
  }
  const [label, fg, bg] = map[review.recommendation] || [review.recommendation || 'reviewed', 'var(--color-ink-3)', 'var(--color-paper-3)']
  return <span className="mono" style={{ color: fg, background: bg, borderRadius: 'var(--radius-full)', padding: '0.35rem 0.65rem', fontSize: 'var(--text-xs)', fontWeight: 800 }}>{label}</span>
}

function PRList() {
  const [prs, setPrs] = useState([])
  const [total, setTotal] = useState(0)
  const [repo, setRepo] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)

  const loadPrs = ({ quiet = false } = {}) => {
    if (!quiet) setLoading(true)
    const params = new URLSearchParams()
    if (repo) params.set('repo', repo)
    if (status) params.set('status', status)
    fetch(`/api/prs?${params}`)
      .then(r => r.json())
      .then(d => { setPrs(d.prs || []); setTotal(d.total || 0) })
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadPrs()
  }, [repo, status])

  useEffect(() => {
    if (!prs.some(pr => pr.latest_review?.status === 'running')) return
    const timer = setInterval(() => loadPrs({ quiet: true }), 3000)
    return () => clearInterval(timer)
  }, [prs, repo, status])

  const activeCount = useMemo(() => prs.filter(pr => pr.status === 'active').length, [prs])
  const runningCount = useMemo(() => prs.filter(pr => pr.latest_review?.status === 'running').length, [prs])

  if (loading) return <LoadingSkeleton />

  return (
    <div className="page-frame" style={{ display: 'grid', gap: 'var(--space-lg)' }}>
      <section className="panel panel-live reveal" style={{ padding: 'var(--space-xl)' }}>
        <div className="flex items-start justify-between gap-lg flex-wrap">
          <div>
            <p className="kicker">signal feed</p>
            <h1 className="display-title" style={{ marginTop: 'var(--space-sm)' }}>
              Pull requests as living signals.
            </h1>
            <p style={{ maxWidth: '62ch', marginTop: 'var(--space-md)', color: 'var(--color-ink-2)', fontSize: 'var(--text-md)', lineHeight: 1.75 }}>
              Filter the orbit, watch active scans breathe, and jump into the PR detail chamber when a signal needs attention.
            </p>
          </div>
          <div className="panel-soft" style={{ padding: 'var(--space-md)', minWidth: 220 }}>
            <p className="mono" style={{ color: 'var(--color-ink-4)', fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>visible field</p>
            <p className="mono" style={{ color: 'var(--color-ink)', fontSize: 'var(--text-3xl)', fontWeight: 800, lineHeight: 1, marginTop: 'var(--space-md)' }}>{total}</p>
            <p style={{ color: 'var(--color-ink-3)', marginTop: 'var(--space-xs)' }}>{activeCount} active · {runningCount} scanning</p>
          </div>
        </div>
      </section>

      <section className="panel reveal" style={{ padding: 'var(--space-md)' }}>
        <div className="flex items-center gap-md flex-wrap">
          <div className="flex items-center gap-xs" style={{ color: 'var(--color-ink-3)' }}>
            <Filter className="w-4 h-4" />
            <span className="mono" style={{ fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>controls</span>
          </div>
          <select value={repo} onChange={e => setRepo(e.target.value)} style={selectStyle}>
            <option value="">all repositories</option>
            <option value="purchase">purchase</option>
            <option value="usermgt">usermgt</option>
            <option value="coop">coop</option>
            <option value="backoffice">backoffice</option>
          </select>
          <select value={status} onChange={e => setStatus(e.target.value)} style={selectStyle}>
            <option value="">all states</option>
            <option value="active">active</option>
            <option value="completed">completed</option>
            <option value="abandoned">abandoned</option>
          </select>
        </div>
      </section>

      <section style={{ display: 'grid', gap: 'var(--space-sm)' }}>
        {prs.length === 0 ? (
          <div className="panel" style={{ padding: 'var(--space-3xl)', textAlign: 'center' }}>
            <Search className="w-8 h-8 mx-auto" style={{ color: 'var(--color-ink-4)' }} />
            <p style={{ marginTop: 'var(--space-md)', color: 'var(--color-ink)', fontWeight: 800 }}>No signals in this orbit</p>
            <p style={{ color: 'var(--color-ink-3)', marginTop: 'var(--space-2xs)' }}>Try another repository or PR state.</p>
          </div>
        ) : prs.map((pr, index) => (
          <Link
            key={pr.id}
            to={`/prs/${pr.id}`}
            className={`panel ${pr.latest_review?.status === 'running' ? 'panel-live' : ''} reveal`}
            style={{
              '--i': index % 8,
              display: 'grid',
              gridTemplateColumns: 'auto minmax(0, 1fr) auto',
              gap: 'var(--space-md)',
              alignItems: 'center',
              padding: 'var(--space-md)',
              color: 'inherit',
              textDecoration: 'none',
              transition: `border-color var(--dur-short) var(--ease-out), transform var(--dur-short) var(--ease-out)`,
            }}
          >
            <div className="living-orb" style={{ width: 58, height: 58 }}>
              <GitPullRequest className="w-5 h-5" style={{ color: 'var(--color-accent-ink)' }} />
            </div>

            <div className="min-w-0">
              <div className="flex items-center gap-xs flex-wrap">
                <span className="mono" style={{ color: 'var(--color-info)', fontSize: 'var(--text-xs)', fontWeight: 800 }}>{pr.repo}</span>
                <span className="mono" style={{ color: 'var(--color-ink-4)', fontSize: 'var(--text-xs)' }}>#{pr.azure_pr_id}</span>
                <ReviewBadge review={pr.latest_review} />
                {pr.is_reviewer_required === 'yes' && <span className="mono" style={{ color: 'var(--color-danger)', background: 'var(--color-danger-bg)', borderRadius: 'var(--radius-full)', padding: '0.35rem 0.65rem', fontSize: 'var(--text-xs)', fontWeight: 800 }}>required</span>}
              </div>
              <h2 style={{ marginTop: 'var(--space-xs)', color: 'var(--color-ink)', fontSize: 'var(--text-lg)', fontWeight: 800, letterSpacing: '-0.04em', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {pr.title}
              </h2>
              <p style={{ marginTop: 'var(--space-2xs)', color: 'var(--color-ink-3)', fontSize: 'var(--text-sm)' }}>
                {pr.author || 'Unknown author'} · {pr.source_branch} → {pr.target_branch}
              </p>
            </div>

            <div className="flex items-center gap-xs">
              <span className={`signal-dot ${pr.latest_review?.status === 'running' ? 'is-running' : ''}`} aria-hidden="true" />
              <ArrowUpRight className="w-4 h-4" style={{ color: 'var(--color-ink-4)' }} />
            </div>
          </Link>
        ))}
      </section>
    </div>
  )
}

const selectStyle = {
  minHeight: 44,
  minWidth: 160,
  border: '1px solid var(--color-rule)',
  borderRadius: 'var(--radius-input)',
  background: 'var(--color-paper-2)',
  color: 'var(--color-ink)',
  padding: '0 var(--space-md)',
  fontFamily: 'var(--font-mono)',
  fontSize: 'var(--text-sm)',
}

export default PRList
