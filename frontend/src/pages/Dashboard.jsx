import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Shield, AlertTriangle, CheckCircle, Clock, TrendingUp } from 'lucide-react'

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [recentReviews, setRecentReviews] = useState([])

  useEffect(() => {
    fetch('/api/stats').then(r => r.json()).then(setStats)
    fetch('/api/reviews?limit=10').then(r => r.json()).then(d => setRecentReviews(d.reviews || []))
  }, [])

  if (!stats) {
    return <div className="flex items-center justify-center h-full"><Clock className="w-6 h-6 animate-spin text-dark-400" /></div>
  }

  const statCards = [
    { label: 'Total PRs', value: stats.total_prs, icon: '📋', color: 'blue' },
    { label: 'Reviews', value: stats.total_reviews, icon: '🔍', color: 'purple' },
    { label: 'Findings', value: stats.total_findings, icon: '🐛', color: 'yellow' },
    { label: 'HIGH Issues', value: stats.findings_by_severity?.HIGH || 0, icon: '🔴', color: 'red' },
  ]

  const recommendationCards = [
    { label: 'Approved', value: stats.recommendations?.approve || 0, icon: '✅', color: 'emerald' },
    { label: 'Changes Requested', value: stats.recommendations?.request_changes || 0, icon: '🚫', color: 'red' },
    { label: 'Comments', value: stats.recommendations?.comment || 0, icon: '💬', color: 'yellow' },
  ]

  return (
    <div className="p-8 space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-dark-50">Dashboard</h2>
        <p className="text-dark-400 mt-1">Automated PR security review overview</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-4 gap-4">
        {statCards.map(({ label, value, icon, color }) => (
          <div key={label} className="bg-dark-900 border border-dark-700 rounded-xl p-5">
            <div className="flex items-center justify-between">
              <span className="text-2xl">{icon}</span>
              <span className="text-3xl font-bold text-dark-50">{value}</span>
            </div>
            <p className="text-sm text-dark-400 mt-2">{label}</p>
          </div>
        ))}
      </div>

      {/* Recommendation Breakdown */}
      <div className="grid grid-cols-3 gap-4">
        {recommendationCards.map(({ label, value, icon, color }) => (
          <div key={label} className={`bg-dark-900 border border-dark-700 rounded-xl p-5`}>
            <div className="flex items-center gap-3">
              <span className="text-xl">{icon}</span>
              <div>
                <span className="text-2xl font-bold text-dark-50">{value}</span>
                <p className="text-sm text-dark-400">{label}</p>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Poll Status */}
      {stats.poll_states?.length > 0 && (
        <div className="bg-dark-900 border border-dark-700 rounded-xl p-5">
          <h3 className="text-lg font-semibold text-dark-200 mb-3">Poll Status</h3>
          <div className="space-y-2">
            {stats.poll_states.map(ps => (
              <div key={ps.repo} className="flex items-center justify-between text-sm">
                <span className="text-dark-300">{ps.repo}</span>
                <span className="text-dark-400">
                  {ps.last_poll_at ? new Date(ps.last_poll_at).toLocaleString('th-TH') : 'Never'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Reviews */}
      <div className="bg-dark-900 border border-dark-700 rounded-xl p-5">
        <h3 className="text-lg font-semibold text-dark-200 mb-4">Recent Reviews</h3>
        {recentReviews.length === 0 ? (
          <p className="text-dark-500 text-sm">No reviews yet. Waiting for PRs...</p>
        ) : (
          <div className="space-y-3">
            {recentReviews.map(rv => (
              <Link
                key={rv.id}
                to={`/prs/${rv.pr_id}`}
                className="block bg-dark-800 hover:bg-dark-750 border border-dark-700 rounded-lg p-4 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <RecommendationBadge rec={rv.recommendation} />
                    <div>
                      <p className="text-sm font-medium text-dark-100">{rv.pr_title || `PR #${rv.pr_id}`}</p>
                      <p className="text-xs text-dark-400">{rv.pr_repo} • {rv.author}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-dark-400">
                    {rv.high_count > 0 && <span className="text-red-400">🔴 {rv.high_count}</span>}
                    {rv.medium_count > 0 && <span className="text-yellow-400">🟡 {rv.medium_count}</span>}
                    {rv.low_count > 0 && <span className="text-blue-400">🔵 {rv.low_count}</span>}
                    <span>{rv.duration_seconds}s</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function RecommendationBadge({ rec }) {
  const styles = {
    approve: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    request_changes: 'bg-red-500/20 text-red-400 border-red-500/30',
    comment: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  }
  const labels = {
    approve: '✅ Approve',
    request_changes: '🚫 Changes',
    comment: '💬 Comment',
  }
  return (
    <span className={`px-2 py-1 rounded-md text-xs font-medium border ${styles[rec] || 'bg-dark-700 text-dark-300'}`}>
      {labels[rec] || rec}
    </span>
  )
}

export default Dashboard
