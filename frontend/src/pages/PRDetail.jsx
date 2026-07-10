import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, ExternalLink, Clock, Shield, AlertTriangle,
  CheckCircle, XCircle, MessageSquare, FileCode, Wrench,
  Loader2, Play
} from 'lucide-react'

function LoadingSkeleton() {
  return (
    <div className="p-8 space-y-6 animate-fade-in">
      <div className="flex items-center gap-4">
        <div className="skeleton h-9 w-9 rounded-lg" />
        <div className="space-y-2 flex-1">
          <div className="skeleton h-5 w-32" />
          <div className="skeleton h-7 w-96" />
          <div className="skeleton h-4 w-64" />
        </div>
      </div>
      <div className="bg-surface border border-surface-border rounded-xl p-6">
        <div className="skeleton h-64 w-full" />
      </div>
    </div>
  )
}

function PRDetail() {
  const { id } = useParams()
  const [pr, setPr] = useState(null)
  const [activeTab, setActiveTab] = useState('findings')
  const [runningReview, setRunningReview] = useState(false)

  useEffect(() => {
    fetch(`/api/prs/${id}`).then(r => r.json()).then(setPr)
  }, [id])

  if (!pr) return <LoadingSkeleton />

  const review = pr.reviews?.[0]
  const findings = review?.findings || []
  const highFindings = findings.filter(f => f.severity === 'HIGH')
  const mediumFindings = findings.filter(f => f.severity === 'MEDIUM')
  const lowFindings = findings.filter(f => f.severity === 'LOW')

  const handleRunReview = async () => {
    setRunningReview(true)
    try {
      const resp = await fetch(`/api/prs/${id}/review`, { method: 'POST' })
      const data = await resp.json()
      if (data.status === 'completed') window.location.reload()
    } catch (e) {
      console.error(e)
    } finally {
      setRunningReview(false)
    }
  }

  return (
    <div className="p-8 space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-start gap-4">
        <Link
          to="/prs"
          className="mt-1 w-9 h-9 rounded-lg border border-surface-border flex items-center justify-center text-dark-400 hover:text-dark-200 hover:border-dark-600 transition-all duration-150 flex-shrink-0"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-[11px] px-2 py-0.5 rounded-md bg-dark-800 text-dark-400 font-mono border border-surface-border">
              {pr.repo}
            </span>
            <span className="text-[11px] text-dark-500 font-mono">#{pr.azure_pr_id}</span>
            {pr.is_reviewer_required === 'yes' && (
              <span className="text-[11px] px-2 py-0.5 rounded-md bg-red-500/10 text-red-400 font-medium">
                Required Reviewer
              </span>
            )}
          </div>
          <h2 className="text-lg font-semibold text-dark-50 tracking-tight leading-snug">
            {pr.title}
          </h2>
          <div className="flex items-center gap-3 mt-1.5 text-[13px] text-dark-400">
            <span>{pr.author}</span>
            <span className="text-dark-700">·</span>
            <span className="font-mono">{pr.source_branch} → {pr.target_branch}</span>
          </div>
        </div>
        <a
          href={pr.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2 bg-surface hover:bg-surface-secondary border border-surface-border rounded-lg text-[13px] text-dark-300 hover:text-dark-100 transition-all duration-150 flex-shrink-0"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Azure DevOps
        </a>
      </div>

      {/* Review Summary */}
      {review && (
        <div className="bg-surface border border-surface-border rounded-xl p-6 animate-slide-up">
          {/* Top bar */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <RecommendationBadge rec={review.recommendation} />
              <span className="text-[12px] text-dark-500">
                {review.duration_seconds}s · {findings.length} finding{findings.length !== 1 ? 's' : ''}
              </span>
            </div>
            <div className="flex items-center gap-2">
              {highFindings.length > 0 && (
                <span className="text-[11px] font-medium text-red-400 bg-red-500/10 px-2 py-1 rounded-md">
                  {highFindings.length} HIGH
                </span>
              )}
              {mediumFindings.length > 0 && (
                <span className="text-[11px] font-medium text-amber-400 bg-amber-500/10 px-2 py-1 rounded-md">
                  {mediumFindings.length} MED
                </span>
              )}
              {lowFindings.length > 0 && (
                <span className="text-[11px] font-medium text-blue-400 bg-blue-500/10 px-2 py-1 rounded-md">
                  {lowFindings.length} LOW
                </span>
              )}
            </div>
          </div>

          {/* Score Cards */}
          <div className="grid grid-cols-5 gap-3 mb-5">
            {[
              { label: 'Logic', score: review.score_logic },
              { label: 'Security', score: review.score_security },
              { label: 'Tests', score: review.score_tests },
              { label: 'Style', score: review.score_style },
              { label: 'Architecture', score: review.score_architecture },
            ].map(({ label, score }) => (
              <ScoreCard key={label} label={label} score={score} />
            ))}
          </div>

          {/* Summary */}
          {review.summary && (
            <div className="bg-dark-800/50 border border-surface-border rounded-lg p-4">
              <p className="text-[13px] text-dark-300 leading-relaxed">{review.summary}</p>
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-surface border border-surface-border rounded-lg p-1 w-fit">
        {[
          { id: 'findings', label: `Findings (${findings.length})` },
          { id: 'diff', label: 'Diff' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-2 rounded-md text-[13px] font-medium transition-all duration-150 ${
              activeTab === tab.id
                ? 'bg-dark-800 text-dark-100 shadow-sm'
                : 'text-dark-400 hover:text-dark-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Findings Tab */}
      {activeTab === 'findings' && (
        <div className="space-y-3">
          {findings.length === 0 && review?.status === 'completed' ? (
            <div className="bg-surface border border-surface-border rounded-xl">
              <div className="flex flex-col items-center justify-center py-16 px-8">
                <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 flex items-center justify-center mb-4">
                  <Shield className="w-6 h-6 text-emerald-400" />
                </div>
                <p className="text-dark-200 font-medium text-sm">No findings — clean review</p>
                <p className="text-dark-500 text-[13px] mt-1">This PR passed all security checks.</p>
              </div>
            </div>
          ) : findings.length === 0 ? (
            <div className="bg-surface border border-surface-border rounded-xl">
              <div className="flex flex-col items-center justify-center py-16 px-8">
                <div className="w-14 h-14 rounded-2xl bg-dark-800 flex items-center justify-center mb-4">
                  <Clock className="w-6 h-6 text-dark-500" />
                </div>
                <p className="text-dark-300 font-medium text-sm">Not yet reviewed</p>
                <p className="text-dark-500 text-[13px] mt-1 mb-5 text-center max-w-xs">
                  This PR was recorded without a review (old PR).
                </p>
                <button
                  onClick={handleRunReview}
                  disabled={runningReview}
                  className="flex items-center gap-2 px-5 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg text-[13px] font-medium transition-all duration-150 active:scale-[0.98]"
                >
                  {runningReview ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Running review...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Run Review
                    </>
                  )}
                </button>
              </div>
            </div>
          ) : (
            findings.map((f, i) => <FindingCard key={f.id} finding={f} index={i} />)
          )}
        </div>
      )}

      {/* Diff Tab */}
      {activeTab === 'diff' && review?.raw_diff && (
        <div className="bg-surface border border-surface-border rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-surface-border flex items-center gap-2">
            <FileCode className="w-4 h-4 text-dark-500" />
            <span className="text-[12px] text-dark-400 font-medium">Raw Diff</span>
          </div>
          <div className="p-4 overflow-auto max-h-[600px]">
            <pre className="text-[12px] font-mono text-dark-300 whitespace-pre-wrap leading-5">
              {review.raw_diff.split('\n').map((line, i) => {
                let cls = 'text-dark-400'
                if (line.startsWith('+')) cls = 'text-emerald-400 bg-emerald-500/5'
                else if (line.startsWith('-')) cls = 'text-red-400 bg-red-500/5'
                else if (line.startsWith('@@')) cls = 'text-blue-400'
                else if (line.startsWith('===')) cls = 'text-yellow-400 font-bold'
                return <div key={i} className={`px-2 -mx-2 ${cls}`}>{line}</div>
              })}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

function ScoreCard({ label, score }) {
  const pct = score != null ? (score / 10) * 100 : 0
  const circumference = 2 * Math.PI * 20
  const offset = circumference - (pct / 100) * circumference

  let color = '#ef4444' // red
  if (score >= 8) color = '#10b981' // emerald
  else if (score >= 5) color = '#f59e0b' // amber

  return (
    <div className="flex flex-col items-center gap-2 py-2">
      <div className="relative w-14 h-14">
        <svg className="w-14 h-14 -rotate-90" viewBox="0 0 48 48">
          <circle cx="24" cy="24" r="20" fill="none" stroke="#1e293b" strokeWidth="3" />
          <circle
            cx="24" cy="24" r="20" fill="none"
            stroke={color}
            strokeWidth="3"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            className="score-ring"
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-[15px] font-bold text-dark-100">
            {score ?? '–'}
          </span>
        </div>
      </div>
      <span className="text-[11px] text-dark-500 font-medium">{label}</span>
    </div>
  )
}

function FindingCard({ finding, index }) {
  const severityConfig = {
    HIGH: {
      border: 'border-red-500/30',
      bg: 'bg-red-500/5',
      badge: 'bg-red-500/15 text-red-400',
      icon: AlertTriangle,
    },
    MEDIUM: {
      border: 'border-amber-500/30',
      bg: 'bg-amber-500/5',
      badge: 'bg-amber-500/15 text-amber-400',
      icon: AlertTriangle,
    },
    LOW: {
      border: 'border-blue-500/30',
      bg: 'bg-blue-500/5',
      badge: 'bg-blue-500/15 text-blue-400',
      icon: AlertTriangle,
    },
  }
  const sev = severityConfig[finding.severity] || severityConfig.LOW

  return (
    <div
      className={`border ${sev.border} ${sev.bg} rounded-xl p-5 animate-slide-up`}
      style={{ animationDelay: `${index * 50}ms` }}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <span className={`px-2 py-0.5 rounded-md text-[11px] font-bold uppercase tracking-wide ${sev.badge}`}>
          {finding.severity}
        </span>
        <span className="text-[11px] px-2 py-0.5 rounded-md bg-dark-800 text-dark-400 border border-surface-border">
          {finding.category}
        </span>
        {finding.owasp_tag && (
          <span className="text-[11px] text-dark-500 font-mono">{finding.owasp_tag}</span>
        )}
        {finding.is_automated && (
          <span className="text-[11px] px-2 py-0.5 rounded-md bg-violet-500/15 text-violet-400 font-medium">
            Auto
          </span>
        )}
      </div>

      {/* File path */}
      <div className="flex items-center gap-2 text-[13px] text-dark-300 mb-2 font-mono">
        <FileCode className="w-3.5 h-3.5 text-dark-500 flex-shrink-0" />
        <span className="truncate">{finding.file_path}:{finding.line_number}</span>
      </div>

      {/* Description */}
      {finding.description && (
        <p className="text-[13px] text-dark-300 mb-3 leading-relaxed">{finding.description}</p>
      )}

      {/* Code snippet */}
      {finding.code_snippet && (
        <div className="bg-dark-950 border border-surface-border rounded-lg p-3 mb-3 overflow-x-auto">
          <code className="text-[12px] text-dark-200 font-mono leading-5">{finding.code_snippet}</code>
        </div>
      )}

      {/* Fix suggestion */}
      {finding.fix_suggestion && (
        <div className="bg-emerald-500/5 border border-emerald-500/20 rounded-lg p-3">
          <div className="flex items-center gap-2 mb-1.5">
            <Wrench className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wide">Fix Suggestion</span>
          </div>
          <p className="text-[13px] text-dark-200 leading-relaxed">{finding.fix_suggestion}</p>
        </div>
      )}
    </div>
  )
}

function RecommendationBadge({ rec }) {
  const config = {
    approve: { bg: 'bg-emerald-500/15', text: 'text-emerald-400', icon: CheckCircle, label: 'Approve' },
    request_changes: { bg: 'bg-red-500/15', text: 'text-red-400', icon: XCircle, label: 'Request Changes' },
    comment: { bg: 'bg-amber-500/15', text: 'text-amber-400', icon: MessageSquare, label: 'Comment' },
  }
  const c = config[rec] || { bg: 'bg-dark-700', text: 'text-dark-300', icon: MessageSquare, label: rec }
  const Icon = c.icon

  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[13px] font-medium ${c.bg} ${c.text}`}>
      <Icon className="w-3.5 h-3.5" />
      {c.label}
    </span>
  )
}

export default PRDetail
