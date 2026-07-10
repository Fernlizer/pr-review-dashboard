import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import {
  GitPullRequest, FileSearch, AlertTriangle, Flame,
  CheckCircle, XCircle, MessageSquare, ArrowUpRight, Loader2
} from 'lucide-react'

function LoadingSkeleton() {
  return (
    <div className="p-8 space-y-6 animate-fade-in">
      <div className="space-y-2">
        <div className="skeleton h-7 w-48" />
        <div className="skeleton h-4 w-72" />
      </div>
      <div className="grid grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-surface border border-surface-border rounded-xl p-5">
            <div className="skeleton h-4 w-20 mb-3" />
            <div className="skeleton h-8 w-16" />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="bg-surface border border-surface-border rounded-xl p-5">
            <div className="skeleton h-4 w-24 mb-3" />
            <div className="skeleton h-8 w-12" />
          </div>
        ))}
      </div>
    </div>
  )
}

function StatCard({ label, value, icon: Icon, color, subtext }) {
  const colorMap = {
    emerald: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', ring: 'ring-emerald-500/20' },
    blue: { bg: 'bg-blue-500/10', text: 'text-blue-400', ring: 'ring-blue-500/20' },
    violet: { bg: 'bg-violet-500/10', text: 'text-violet-400', ring: 'ring-violet-500/20' },
    amber: { bg: 'bg-amber-500/10', text: 'text-amber-400', ring: 'ring-amber-500/20' },
    red: { bg: 'bg-red-500/10', text: 'text-red-400', ring: 'ring-red-500/20' },
  }
  const c = colorMap[color] || colorMap.emerald

  return (
    <div className="bg-surface border border-surface-border rounded-xl p-5 hover:border-dark-600 transition-colors duration-200 group">
      <div className="flex items-center justify-between mb-3">
        <span className="text-[13px] text-dark-400 font-medium">{label}</span>
        <div className={`w-8 h-8 rounded-lg ${c.bg} flex items-center justify-center`}>
          <Icon className={`w-4 h-4 ${c.text}`} />
        </div>
      </div>
      <p className="text-[28px] font-bold text-dark-50 tracking-tight leading-none">
        {value}
      </p>
      {subtext && <p className="text-[12px] text-dark-500 mt-1">{subtext}</p>}
    </div>
  )
}

function RecommendationCard({ label, value, icon: Icon, color }) {
  const colorMap = {
    emerald: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20' },
    red: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20' },
    amber: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20' },
  }
  const c = colorMap[color] || colorMap.emerald

  return (
    <div className="bg-surface border border-surface-border rounded-xl p-4 flex items-center gap-4 hover:border-dark-600 transition-colors duration-200">
      <div className={`w-10 h-10 rounded-xl ${c.bg} flex items-center justify-center flex-shrink-0`}>
        <Icon className={`w-5 h-5 ${c.text}`} />
      </div>
      <div>
        <p className="text-xl font-bold text-dark-50 leading-none">{value}</p>
        <p className="text-[12px] text-dark-500 mt-1">{label}</p>
      </div>
    </div>
  )
}

function SeverityBar({ label, count, total, color }) {
  const pct = total > 0 ? (count / total) * 100 : 0
  const colorMap = {
    red: 'bg-red-500',
    amber: 'bg-amber-500',
    blue: 'bg-blue-500',
  }

  return (
    <div className="flex items-center gap-3">
      <span className="text-[12px] text-dark-400 w-16 flex-shrink-0">{label}</span>
      <div className="flex-1 bg-dark-800 rounded-full h-2 overflow-hidden">
        <div
          className={`h-full rounded-full ${colorMap[color]} transition-all duration-700 ease-out`}
          style={{ width: `${Math.max(pct, count > 0 ? 8 : 0)}%` }}
        />
      </div>
      <span className="text-[13px] text-dark-300 font-medium w-8 text-right">{count}</span>
    </div>
  )
}

function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-8">
      <div className="w-14 h-14 rounded-2xl bg-dark-800 flex items-center justify-center mb-4">
        <Icon className="w-6 h-6 text-dark-500" />
      </div>
      <p className="text-dark-300 font-medium text-sm">{title}</p>
      <p className="text-dark-500 text-[13px] mt-1 text-center max-w-xs">{description}</p>
    </div>
  )
}

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [recentReviews, setRecentReviews] = useState([])

  useEffect(() => {
    fetch('/api/stats').then(r => r.json()).then(setStats)
    fetch('/api/reviews?limit=10').then(r => r.json()).then(d => setRecentReviews(d.reviews || []))
  }, [])

  if (!stats) return <LoadingSkeleton />

  const totalFindings = stats.total_findings || 0
  const highCount = stats.findings_by_severity?.HIGH || 0
  const medCount = stats.findings_by_severity?.MEDIUM || 0
  const lowCount = stats.findings_by_severity?.LOW || 0

  return (
    <div className="p-8 space-y-8 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="text-xl font-semibold text-dark-50 tracking-tight">Dashboard</h2>
        <p className="text-[13px] text-dark-400 mt-1">Automated PR security review overview</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-4 gap-4">
        <StatCard label="Total PRs" value={stats.total_prs} icon={GitPullRequest} color="blue" />
        <StatCard label="Reviews" value={stats.total_reviews} icon={FileSearch} color="violet" />
        <StatCard label="Findings" value={totalFindings} icon={AlertTriangle} color="amber" />
        <StatCard label="Critical" value={highCount} icon={Flame} color="red" />
      </div>

      {/* Recommendation + Severity row */}
      <div className="grid grid-cols-5 gap-4">
        <div className="col-span-3 bg-surface border border-surface-border rounded-xl p-5">
          <h3 className="text-[13px] font-semibold text-dark-300 mb-4 uppercase tracking-wider">Recommendations</h3>
          <div className="grid grid-cols-3 gap-3">
            <RecommendationCard
              label="Approved"
              value={stats.recommendations?.approve || 0}
              icon={CheckCircle}
              color="emerald"
            />
            <RecommendationCard
              label="Changes Requested"
              value={stats.recommendations?.request_changes || 0}
              icon={XCircle}
              color="red"
            />
            <RecommendationCard
              label="Comments"
              value={stats.recommendations?.comment || 0}
              icon={MessageSquare}
              color="amber"
            />
          </div>
        </div>

        <div className="col-span-2 bg-surface border border-surface-border rounded-xl p-5">
          <h3 className="text-[13px] font-semibold text-dark-300 mb-4 uppercase tracking-wider">Findings by Severity</h3>
          <div className="space-y-3">
            <SeverityBar label="HIGH" count={highCount} total={totalFindings} color="red" />
            <SeverityBar label="MEDIUM" count={medCount} total={totalFindings} color="amber" />
            <SeverityBar label="LOW" count={lowCount} total={totalFindings} color="blue" />
          </div>
        </div>
      </div>

      {/* Poll Status */}
      {stats.poll_states?.length > 0 && (
        <div className="bg-surface border border-surface-border rounded-xl p-5">
          <h3 className="text-[13px] font-semibold text-dark-300 mb-4 uppercase tracking-wider">Poll Status</h3>
          <div className="space-y-2">
            {stats.poll_states.map(ps => (
              <div key={ps.repo} className="flex items-center justify-between py-2 border-b border-surface-border last:border-0">
                <div className="flex items-center gap-2">
                  <div className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span className="text-[13px] text-dark-200 font-mono">{ps.repo}</span>
                </div>
                <span className="text-[12px] text-dark-500">
                  {ps.last_poll_at ? new Date(ps.last_poll_at).toLocaleString('th-TH') : 'Never'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Reviews */}
      <div className="bg-surface border border-surface-border rounded-xl">
        <div className="px-5 py-4 border-b border-surface-border">
          <h3 className="text-[13px] font-semibold text-dark-300 uppercase tracking-wider">Recent Reviews</h3>
        </div>
        {recentReviews.length === 0 ? (
          <EmptyState
            icon={FileSearch}
            title="No reviews yet"
            description="Reviews will appear here once PRs are scanned by the security scanner."
          />
        ) : (
          <div className="divide-y divide-surface-border">
            {recentReviews.map((rv, i) => (
              <Link
                key={rv.id}
                to={`/prs/${rv.pr_id}`}
                className="flex items-center justify-between px-5 py-3.5 hover:bg-dark-800/40 transition-colors duration-150 group"
                style={{ animationDelay: `${i * 30}ms` }}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <RecommendationBadge rec={rv.recommendation} />
                  <div className="min-w-0">
                    <p className="text-[13px] font-medium text-dark-100 truncate max-w-md">
                      {rv.pr_title || `PR #${rv.pr_id}`}
                    </p>
                    <p className="text-[11px] text-dark-500 mt-0.5">
                      {rv.pr_repo} · {rv.author}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-4 flex-shrink-0 ml-4">
                  <div className="flex items-center gap-2">
                    {rv.high_count > 0 && (
                      <span className="text-[11px] font-medium text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded">
                        {rv.high_count}H
                      </span>
                    )}
                    {rv.medium_count > 0 && (
                      <span className="text-[11px] font-medium text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded">
                        {rv.medium_count}M
                      </span>
                    )}
                    {rv.low_count > 0 && (
                      <span className="text-[11px] font-medium text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">
                        {rv.low_count}L
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] text-dark-500">{rv.duration_seconds}s</span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-dark-600 group-hover:text-dark-400 transition-colors" />
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
  const config = {
    approve: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', label: 'Approve' },
    request_changes: { bg: 'bg-red-500/15', text: 'text-red-400', label: 'Changes' },
    comment: { bg: 'bg-amber-500/15', text: 'text-amber-400', label: 'Comment' },
  }
  const c = config[rec] || { bg: 'bg-dark-700', text: 'text-dark-300', label: rec }

  return (
    <span className={`inline-flex items-center px-2 py-1 rounded-md text-[11px] font-medium ${c.bg} ${c.text} flex-shrink-0`}>
      {c.label}
    </span>
  )
}

export default Dashboard
