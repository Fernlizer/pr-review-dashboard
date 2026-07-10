import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ExternalLink, Filter, GitPullRequest, ArrowUpRight, Loader2, Search } from 'lucide-react'

function LoadingSkeleton() {
  return (
    <div className="p-8 space-y-4 animate-fade-in">
      <div className="skeleton h-7 w-48 mb-2" />
      <div className="skeleton h-4 w-32" />
      <div className="space-y-3 mt-6">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="bg-surface border border-surface-border rounded-xl p-5">
            <div className="flex items-start justify-between">
              <div className="space-y-2 flex-1">
                <div className="flex gap-2">
                  <div className="skeleton h-5 w-20" />
                  <div className="skeleton h-5 w-24" />
                </div>
                <div className="skeleton h-5 w-3/4" />
                <div className="flex gap-3 mt-1">
                  <div className="skeleton h-4 w-24" />
                  <div className="skeleton h-4 w-40" />
                </div>
              </div>
              <div className="skeleton h-7 w-20" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

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

  return (
    <div className="p-8 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-dark-50 tracking-tight">Pull Requests</h2>
          <p className="text-[13px] text-dark-400 mt-1">
            {total} PR{total !== 1 ? 's' : ''} tracked
          </p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-dark-500" />
          <select
            value={repo}
            onChange={e => setRepo(e.target.value)}
            className="bg-surface border border-surface-border text-dark-200 text-[13px] rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 transition-colors appearance-none cursor-pointer"
          >
            <option value="">All Repos</option>
            {repos.filter(Boolean).map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <select
            value={status}
            onChange={e => setStatus(e.target.value)}
            className="bg-surface border border-surface-border text-dark-200 text-[13px] rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-emerald-500 focus:border-emerald-500 transition-colors appearance-none cursor-pointer"
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
        <div className="bg-surface border border-surface-border rounded-xl">
          <div className="flex flex-col items-center justify-center py-20 px-8">
            <div className="w-14 h-14 rounded-2xl bg-dark-800 flex items-center justify-center mb-4">
              <Search className="w-6 h-6 text-dark-500" />
            </div>
            <p className="text-dark-300 font-medium text-sm">No pull requests found</p>
            <p className="text-dark-500 text-[13px] mt-1 text-center max-w-xs">
              {repo || status
                ? 'Try adjusting your filters to see more results.'
                : 'PRs will appear here once the scanner discovers them.'}
            </p>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {prs.map((pr, i) => (
            <Link
              key={pr.id}
              to={`/prs/${pr.id}`}
              className="block bg-surface border border-surface-border rounded-xl p-4 hover:border-dark-600 hover:bg-surface-secondary transition-all duration-150 group"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  {/* Tags row */}
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-[11px] px-2 py-0.5 rounded-md bg-dark-800 text-dark-400 font-mono border border-surface-border">
                      {pr.repo}
                    </span>
                    <span className="text-[11px] text-dark-500 font-mono">
                      #{pr.azure_pr_id}
                    </span>
                    {pr.is_reviewer_required === 'yes' && (
                      <span className="text-[11px] px-2 py-0.5 rounded-md bg-red-500/10 text-red-400 font-medium">
                        Required Reviewer
                      </span>
                    )}
                    <StatusBadge status={pr.status} />
                  </div>

                  {/* Title */}
                  <h3 className="text-[14px] font-medium text-dark-100 truncate leading-snug">
                    {pr.title}
                  </h3>

                  {/* Meta */}
                  <div className="flex items-center gap-3 mt-2 text-[12px] text-dark-500">
                    <span>{pr.author}</span>
                    <span className="text-dark-700">·</span>
                    <span className="font-mono text-dark-400">
                      {pr.source_branch} → {pr.target_branch}
                    </span>
                    {pr.discovered_at && (
                      <>
                        <span className="text-dark-700">·</span>
                        <span>{new Date(pr.discovered_at).toLocaleString('th-TH')}</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Right side */}
                <div className="flex items-center gap-3 flex-shrink-0">
                  {pr.latest_review && <ReviewBadge review={pr.latest_review} />}
                  <a
                    href={pr.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={e => e.stopPropagation()}
                    className="w-8 h-8 rounded-lg border border-surface-border flex items-center justify-center text-dark-500 hover:text-emerald-400 hover:border-emerald-500/30 transition-all duration-150 opacity-0 group-hover:opacity-100"
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

function StatusBadge({ status }) {
  const config = {
    active: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', dot: 'bg-emerald-400' },
    completed: { bg: 'bg-dark-700', text: 'text-dark-400', dot: 'bg-dark-400' },
    abandoned: { bg: 'bg-dark-700', text: 'text-dark-500', dot: 'bg-dark-500' },
  }
  const c = config[status] || config.active

  return (
    <span className={`inline-flex items-center gap-1.5 text-[11px] px-2 py-0.5 rounded-md ${c.bg} ${c.text}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
      {status}
    </span>
  )
}

function ReviewBadge({ review }) {
  const config = {
    approve: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', label: 'Approved' },
    request_changes: { bg: 'bg-red-500/15', text: 'text-red-400', label: 'Changes' },
    comment: { bg: 'bg-amber-500/15', text: 'text-amber-400', label: 'Comment' },
  }
  const c = config[review.recommendation] || { bg: 'bg-dark-700', text: 'text-dark-300', label: review.recommendation }

  return (
    <span className={`px-2.5 py-1 rounded-md text-[11px] font-medium ${c.bg} ${c.text}`}>
      {c.label}
    </span>
  )
}

export default PRList
