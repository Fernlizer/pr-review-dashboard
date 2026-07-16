/* Hallmark · genre: atmospheric · macrostructure: Workbench · design-system: design.md · designed-as-app */

import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ArrowUpRight, Filter, Search } from 'lucide-react'

/* ── Loading skeleton ────────────────────────────────────────────── */

function LoadingSkeleton() {
  return (
    <div className="p-lg space-y-md animate-fade-in">
      <div className="space-y-2xs">
        <div className="skeleton" style={{ height: 28, width: 180 }} />
        <div className="skeleton" style={{ height: 16, width: 120 }} />
      </div>
      <div className="space-y-xs" style={{ marginTop: 'var(--space-lg)' }}>
        {[...Array(5)].map((_, i) => (
          <div
            key={i}
            style={{
              background: 'var(--color-paper-2)',
              border: '1px solid var(--color-rule)',
              borderRadius: 'var(--radius-lg)',
              padding: 'var(--space-md)',
            }}
          >
            <div className="flex items-start justify-between">
              <div className="space-y-2xs flex-1">
                <div className="flex gap-2xs">
                  <div className="skeleton" style={{ height: 20, width: 72 }} />
                  <div className="skeleton" style={{ height: 20, width: 40 }} />
                </div>
                <div className="skeleton" style={{ height: 18, width: '75%' }} />
                <div className="flex gap-sm mt-xs">
                  <div className="skeleton" style={{ height: 14, width: 80 }} />
                  <div className="skeleton" style={{ height: 14, width: 160 }} />
                </div>
              </div>
              <div className="skeleton" style={{ height: 28, width: 72 }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ── Status badge ────────────────────────────────────────────────── */

function StatusBadge({ status }) {
  const config = {
    active: { bg: 'var(--color-success-bg)', text: 'var(--color-success)', dot: 'var(--color-success)' },
    completed: { bg: 'var(--color-paper-3)', text: 'var(--color-ink-3)', dot: 'var(--color-ink-4)' },
    abandoned: { bg: 'var(--color-paper-3)', text: 'var(--color-ink-4)', dot: 'var(--color-ink-4)' },
  }
  const c = config[status] || config.active

  return (
    <span
      className="inline-flex items-center font-mono"
      style={{
        gap: 6,
        fontSize: 'var(--text-xs)',
        padding: '3px 8px',
        borderRadius: 'var(--radius-sm)',
        background: c.bg,
        color: c.text,
      }}
    >
      <span className="rounded-full flex-shrink-0" style={{ width: 5, height: 5, background: c.dot }} />
      {status}
    </span>
  )
}

/* ── Review badge ────────────────────────────────────────────────── */

function ReviewBadge({ review }) {
  const config = {
    approve: { bg: 'var(--color-success-bg)', text: 'var(--color-success)', label: 'Approved' },
    request_changes: { bg: 'var(--color-danger-bg)', text: 'var(--color-danger)', label: 'Changes' },
    comment: { bg: 'var(--color-warning-bg)', text: 'var(--color-warning)', label: 'Comment' },
  }
  const c = config[review.recommendation] || { bg: 'var(--color-paper-3)', text: 'var(--color-ink-2)', label: review.recommendation }

  return (
    <span
      className="font-medium font-mono"
      style={{
        fontSize: 'var(--text-xs)',
        padding: '4px 10px',
        borderRadius: 'var(--radius-sm)',
        background: c.bg,
        color: c.text,
      }}
    >
      {c.label}
    </span>
  )
}

/* ── PR List ─────────────────────────────────────────────────────── */

function PRList() {
  const [prs, setPrs] = useState([])
  const [total, setTotal] = useState(0)
  const [repo, setRepo] = useState('')
  const [status, setStatus] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    const params = new URLSearchParams()
    if (repo) params.set('repo', repo)
    if (status) params.set('status', status)
    fetch(`/api/prs?${params}`)
      .then(r => r.json())
      .then(d => { setPrs(d.prs || []); setTotal(d.total || 0) })
      .finally(() => setLoading(false))
  }, [repo, status])

  const repos = ['', 'purchase', 'usermgt', 'coop']

  const selectStyle = {
    background: 'var(--color-paper-2)',
    border: '1px solid var(--color-rule)',
    color: 'var(--color-ink-2)',
    fontSize: 'var(--text-sm)',
    borderRadius: 'var(--radius-md)',
    padding: '6px 12px',
    outline: 'none',
    cursor: 'pointer',
    appearance: 'none',
    fontFamily: 'var(--font-body)',
  }

  return (
    <div className="p-lg space-y-md animate-fade-in" style={{ maxWidth: 1200 }}>
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-sm">
        <div>
          <h2 className="font-semibold tracking-tight" style={{ fontSize: 'var(--text-xl)', color: 'var(--color-ink)', letterSpacing: '-0.025em' }}>
            Pull Requests
          </h2>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-3)', marginTop: 4 }}>
            {total} PR{total !== 1 ? 's' : ''} tracked
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2xs">
          <Filter className="w-4 h-4" style={{ color: 'var(--color-ink-4)' }} />
          <select
            value={repo}
            onChange={e => setRepo(e.target.value)}
            style={selectStyle}
          >
            <option value="">All Repos</option>
            {repos.filter(Boolean).map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <select
            value={status}
            onChange={e => setStatus(e.target.value)}
            style={selectStyle}
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="abandoned">Abandoned</option>
          </select>
        </div>
      </div>

      {/* PR List */}
      {loading ? (
        <LoadingSkeleton />
      ) : prs.length === 0 ? (
        <div
          style={{
            background: 'var(--color-paper-2)',
            border: '1px solid var(--color-rule)',
            borderRadius: 'var(--radius-lg)',
          }}
        >
          <div className="flex flex-col items-center justify-center" style={{ padding: 'var(--space-3xl) var(--space-lg)' }}>
            <div
              className="rounded-lg flex items-center justify-center"
              style={{ width: 48, height: 48, background: 'var(--color-paper-3)', marginBottom: 'var(--space-md)' }}
            >
              <Search className="w-5 h-5" style={{ color: 'var(--color-ink-4)' }} />
            </div>
            <p className="font-medium" style={{ fontSize: 'var(--text-base)', color: 'var(--color-ink-2)' }}>
              No pull requests found
            </p>
            <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-3)', marginTop: 4, textAlign: 'center', maxWidth: 320 }}>
              {repo || status
                ? 'Try adjusting your filters to see more results.'
                : 'PRs will appear here once the scanner discovers them.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-2xs">
          {prs.map((pr) => (
            <Link
              key={pr.id}
              to={`/prs/${pr.id}`}
              className="block group"
              style={{
                background: 'var(--color-paper-2)',
                border: '1px solid var(--color-rule)',
                borderRadius: 'var(--radius-lg)',
                padding: 'var(--space-sm) var(--space-md)',
                textDecoration: 'none',
                transition: `border-color var(--dur-micro) var(--ease-out), background var(--dur-micro) var(--ease-out)`,
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = 'var(--color-paper-4)'
                e.currentTarget.style.background = 'var(--color-paper-3)'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'var(--color-rule)'
                e.currentTarget.style.background = 'var(--color-paper-2)'
              }}
            >
              <div className="flex items-start justify-between gap-md">
                <div className="flex-1 min-w-0">
                  {/* Tags row */}
                  <div className="flex items-center gap-2xs" style={{ marginBottom: 8 }}>
                    <span
                      className="font-mono"
                      style={{
                        fontSize: 'var(--text-xs)',
                        padding: '2px 8px',
                        borderRadius: 'var(--radius-sm)',
                        background: 'var(--color-paper-3)',
                        color: 'var(--color-ink-3)',
                        border: '1px solid var(--color-rule)',
                      }}
                    >
                      {pr.repo}
                    </span>
                    <span className="font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-4)' }}>
                      #{pr.azure_pr_id}
                    </span>
                    {pr.is_reviewer_required === 'yes' && (
                      <span
                        className="font-medium"
                        style={{ fontSize: 'var(--text-xs)', padding: '2px 8px', borderRadius: 'var(--radius-sm)', background: 'var(--color-danger-bg)', color: 'var(--color-danger)' }}
                      >
                        Required Reviewer
                      </span>
                    )}
                    <StatusBadge status={pr.status} />
                  </div>

                  {/* Title */}
                  <h3 className="font-medium truncate leading-snug" style={{ fontSize: 'var(--text-base)', color: 'var(--color-ink)' }}>
                    {pr.title}
                  </h3>

                  {/* Meta */}
                  <div className="flex items-center gap-sm flex-wrap" style={{ marginTop: 8, fontSize: 'var(--text-xs)', color: 'var(--color-ink-4)' }}>
                    <span>{pr.author}</span>
                    <span style={{ color: 'var(--color-ink-4)' }}>·</span>
                    <span className="font-mono" style={{ color: 'var(--color-ink-3)' }}>
                      {pr.source_branch} → {pr.target_branch}
                    </span>
                    {pr.discovered_at && (
                      <>
                        <span style={{ color: 'var(--color-ink-4)' }}>·</span>
                        <span>{new Date(pr.discovered_at).toLocaleString('th-TH')}</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Right side */}
                <div className="flex items-center gap-sm flex-shrink-0">
                  {pr.latest_review && <ReviewBadge review={pr.latest_review} />}
                  <a
                    href={pr.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={e => e.stopPropagation()}
                    className="flex items-center justify-center"
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--color-rule)',
                      color: 'var(--color-ink-4)',
                      transition: `all var(--dur-micro) var(--ease-out)`,
                      opacity: 0,
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.color = 'var(--color-accent)'
                      e.currentTarget.style.borderColor = 'var(--color-accent)'
                      e.currentTarget.style.opacity = '1'
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.color = 'var(--color-ink-4)'
                      e.currentTarget.style.borderColor = 'var(--color-rule)'
                    }}
                  >
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  </a>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}

export default PRList
