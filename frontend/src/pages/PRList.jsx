import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ExternalLink, Filter } from 'lucide-react'

function PRList() {
  const [prs, setPrs] = useState([])
  const [total, setTotal] = useState(0)
  const [repo, setRepo] = useState('')
  const [status, setStatus] = useState('')

  useEffect(() => {
    const params = new URLSearchParams()
    if (repo) params.set('repo', repo)
    if (status) params.set('status', status)
    fetch(`/api/prs?${params}`)
      .then(r => r.json())
      .then(d => { setPrs(d.prs || []); setTotal(d.total || 0) })
  }, [repo, status])

  const repos = ['', 'purchase', 'usermgt', 'coop']

  return (
    <div className="p-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-dark-50">Pull Requests</h2>
          <p className="text-dark-400 mt-1">{total} PRs tracked</p>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-3">
          <select
            value={repo}
            onChange={e => setRepo(e.target.value)}
            className="bg-dark-800 border border-dark-600 text-dark-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          >
            <option value="">All Repos</option>
            {repos.filter(Boolean).map(r => <option key={r} value={r}>{r}</option>)}
          </select>
          <select
            value={status}
            onChange={e => setStatus(e.target.value)}
            className="bg-dark-800 border border-dark-600 text-dark-200 text-sm rounded-lg px-3 py-2 focus:outline-none focus:ring-1 focus:ring-emerald-500"
          >
            <option value="">All Status</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="abandoned">Abandoned</option>
          </select>
        </div>
      </div>

      {/* PR List */}
      {prs.length === 0 ? (
        <div className="bg-dark-900 border border-dark-700 rounded-xl p-12 text-center">
          <p className="text-dark-400">No PRs found. Polling for new PRs...</p>
        </div>
      ) : (
        <div className="space-y-3">
          {prs.map(pr => (
            <Link
              key={pr.id}
              to={`/prs/${pr.id}`}
              className="block bg-dark-900 hover:bg-dark-850 border border-dark-700 rounded-xl p-5 transition-colors"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs px-2 py-0.5 rounded-md bg-dark-700 text-dark-300 font-mono">
                      {pr.repo}
                    </span>
                    {pr.is_reviewer_required === 'yes' && (
                      <span className="text-xs px-2 py-0.5 rounded-md bg-red-500/20 text-red-400 border border-red-500/30">
                        Required Reviewer
                      </span>
                    )}
                    <span className="text-xs text-dark-500">#{pr.azure_pr_id}</span>
                  </div>
                  <h3 className="text-base font-medium text-dark-100 truncate">{pr.title}</h3>
                  <div className="flex items-center gap-4 mt-2 text-xs text-dark-400">
                    <span>👤 {pr.author}</span>
                    <span className="font-mono">{pr.source_branch} → {pr.target_branch}</span>
                    {pr.discovered_at && (
                      <span>📅 {new Date(pr.discovered_at).toLocaleString('th-TH')}</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3 ml-4">
                  {pr.latest_review && <ReviewBadge review={pr.latest_review} />}
                  <a
                    href={pr.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    onClick={e => e.stopPropagation()}
                    className="text-dark-400 hover:text-emerald-400 transition-colors"
                  >
                    <ExternalLink className="w-4 h-4" />
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

function ReviewBadge({ review }) {
  const styles = {
    approve: 'bg-emerald-500/20 text-emerald-400',
    request_changes: 'bg-red-500/20 text-red-400',
    comment: 'bg-yellow-500/20 text-yellow-400',
  }
  return (
    <span className={`px-3 py-1.5 rounded-lg text-xs font-medium ${styles[review.recommendation] || 'bg-dark-700 text-dark-300'}`}>
      {review.recommendation === 'approve' ? '✅' : review.recommendation === 'request_changes' ? '🚫' : '💬'}
    </span>
  )
}

export default PRList
