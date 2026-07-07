import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, ExternalLink, Clock, Shield, AlertTriangle } from 'lucide-react'

function PRDetail() {
  const { id } = useParams()
  const [pr, setPr] = useState(null)
  const [activeTab, setActiveTab] = useState('findings')
  const [showDiff, setShowDiff] = useState(false)
  const [runningReview, setRunningReview] = useState(false)

  useEffect(() => {
    fetch(`/api/prs/${id}`).then(r => r.json()).then(setPr)
  }, [id])

  if (!pr) {
    return <div className="flex items-center justify-center h-full"><Clock className="w-6 h-6 animate-spin text-dark-400" /></div>
  }

  const review = pr.reviews?.[0]
  const findings = review?.findings || []
  const highFindings = findings.filter(f => f.severity === 'HIGH')
  const mediumFindings = findings.filter(f => f.severity === 'MEDIUM')
  const lowFindings = findings.filter(f => f.severity === 'LOW')

  return (
    <div className="p-8 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link to="/prs" className="text-dark-400 hover:text-dark-200 transition-colors">
          <ArrowLeft className="w-5 h-5" />
        </Link>
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-xs px-2 py-0.5 rounded-md bg-dark-700 text-dark-300 font-mono">{pr.repo}</span>
            {pr.is_reviewer_required === 'yes' && (
              <span className="text-xs px-2 py-0.5 rounded-md bg-red-500/20 text-red-400 border border-red-500/30">
                Required Reviewer
              </span>
            )}
          </div>
          <h2 className="text-xl font-bold text-dark-50">{pr.title}</h2>
          <div className="flex items-center gap-4 mt-1 text-sm text-dark-400">
            <span>👤 {pr.author}</span>
            <span className="font-mono">{pr.source_branch} → {pr.target_branch}</span>
          </div>
        </div>
        <a
          href={pr.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2 bg-dark-800 hover:bg-dark-700 border border-dark-600 rounded-lg text-sm text-dark-200 transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
          Open in Azure DevOps
        </a>
      </div>

      {/* Review Summary */}
      {review && (
        <div className="bg-dark-900 border border-dark-700 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <RecommendationBadge rec={review.recommendation} />
              <span className="text-dark-400 text-sm">
                {review.duration_seconds}s • {findings.length} findings
              </span>
            </div>
            <div className="flex items-center gap-4">
              {highFindings.length > 0 && <span className="text-sm text-red-400">🔴 {highFindings.length} HIGH</span>}
              {mediumFindings.length > 0 && <span className="text-sm text-yellow-400">🟡 {mediumFindings.length} MED</span>}
              {lowFindings.length > 0 && <span className="text-sm text-blue-400">🔵 {lowFindings.length} LOW</span>}
            </div>
          </div>

          {/* Score Table */}
          <div className="grid grid-cols-5 gap-3 mb-4">
            {[
              { label: 'Logic', score: review.score_logic },
              { label: 'Security', score: review.score_security },
              { label: 'Tests', score: review.score_tests },
              { label: 'Style', score: review.score_style },
              { label: 'Architecture', score: review.score_architecture },
            ].map(({ label, score }) => (
              <div key={label} className="text-center">
                <ScoreCircle score={score} />
                <p className="text-xs text-dark-400 mt-1">{label}</p>
              </div>
            ))}
          </div>

          {review.summary && (
            <p className="text-sm text-dark-300 bg-dark-800 rounded-lg p-3">{review.summary}</p>
          )}
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-dark-900 rounded-lg p-1 w-fit">
        {['findings', 'diff'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab ? 'bg-dark-700 text-dark-100' : 'text-dark-400 hover:text-dark-200'
            }`}
          >
            {tab === 'findings' ? `Findings (${findings.length})` : 'Diff'}
          </button>
        ))}
      </div>

      {/* Findings Tab */}
      {activeTab === 'findings' && (
        <div className="space-y-4">
          {findings.length === 0 && review?.status === 'completed' ? (
            <div className="bg-dark-900 border border-dark-700 rounded-xl p-12 text-center">
              <Shield className="w-12 h-12 text-emerald-400 mx-auto mb-3" />
              <p className="text-dark-300">No findings — clean review!</p>
            </div>
          ) : findings.length === 0 ? (
            <div className="bg-dark-900 border border-dark-700 rounded-xl p-12 text-center">
              <Clock className="w-12 h-12 text-dark-500 mx-auto mb-3" />
              <p className="text-dark-300 mb-2">ยังไม่ได้ review</p>
              <p className="text-dark-500 text-sm mb-4">PR นี้ถูกบันทึกโดยไม่ review (PR เก่า)</p>
              <button
                onClick={async () => {
                  setRunningReview(true)
                  try {
                    const resp = await fetch(`/api/prs/${id}/review`, { method: 'POST' })
                    const data = await resp.json()
                    if (data.status === 'completed') {
                      window.location.reload()
                    }
                  } catch (e) {
                    console.error(e)
                  } finally {
                    setRunningReview(false)
                  }
                }}
                disabled={runningReview}
                className="px-6 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
              >
                {runningReview ? '⏳ กำลัง review...' : '🔍 Run Review'}
              </button>
            </div>
          ) : (
            findings.map(f => <FindingCard key={f.id} finding={f} />)
          )}
        </div>
      )}

      {/* Diff Tab */}
      {activeTab === 'diff' && review?.raw_diff && (
        <div className="bg-dark-900 border border-dark-700 rounded-xl p-4 overflow-auto max-h-[600px]">
          <pre className="text-xs font-mono text-dark-300 whitespace-pre-wrap">
            {review.raw_diff.split('\n').map((line, i) => {
              let color = 'text-dark-300'
              if (line.startsWith('+')) color = 'text-emerald-400'
              else if (line.startsWith('-')) color = 'text-red-400'
              else if (line.startsWith('@@')) color = 'text-blue-400'
              else if (line.startsWith('===')) color = 'text-yellow-400 font-bold'
              return <div key={i} className={color}>{line}</div>
            })}
          </pre>
        </div>
      )}
    </div>
  )
}

function FindingCard({ finding }) {
  const severityStyles = {
    HIGH: 'border-red-500/50 bg-red-500/5',
    MEDIUM: 'border-yellow-500/50 bg-yellow-500/5',
    LOW: 'border-blue-500/50 bg-blue-500/5',
  }
  const severityBadge = {
    HIGH: 'bg-red-500/20 text-red-400',
    MEDIUM: 'bg-yellow-500/20 text-yellow-400',
    LOW: 'bg-blue-500/20 text-blue-400',
  }

  return (
    <div className={`border rounded-xl p-5 ${severityStyles[finding.severity] || 'border-dark-700'}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded-md text-xs font-bold ${severityBadge[finding.severity]}`}>
            {finding.severity}
          </span>
          <span className="text-xs px-2 py-0.5 rounded-md bg-dark-700 text-dark-300">{finding.category}</span>
          {finding.owasp_tag && (
            <span className="text-xs text-dark-400">{finding.owasp_tag}</span>
          )}
          {finding.is_automated && (
            <span className="text-xs px-2 py-0.5 rounded-md bg-purple-500/20 text-purple-400">Auto</span>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 text-sm text-dark-300 mb-2 font-mono">
        📄 {finding.file_path}:{finding.line_number}
      </div>

      {finding.description && (
        <p className="text-sm text-dark-300 mb-3">{finding.description}</p>
      )}

      {finding.code_snippet && (
        <div className="bg-dark-950 rounded-lg p-3 mb-3 overflow-x-auto">
          <code className="text-xs text-dark-200 font-mono">{finding.code_snippet}</code>
        </div>
      )}

      {finding.fix_suggestion && (
        <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-3">
          <p className="text-xs font-medium text-emerald-400 mb-1">💡 Fix Suggestion</p>
          <p className="text-sm text-dark-200">{finding.fix_suggestion}</p>
        </div>
      )}
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
    request_changes: '🚫 Request Changes',
    comment: '💬 Comment',
  }
  return (
    <span className={`px-3 py-1.5 rounded-lg text-sm font-medium border ${styles[rec] || 'bg-dark-700 text-dark-300'}`}>
      {labels[rec] || rec}
    </span>
  )
}

function ScoreCircle({ score }) {
  const color = score >= 8 ? 'text-emerald-400' : score >= 5 ? 'text-yellow-400' : 'text-red-400'
  return (
    <span className={`text-2xl font-bold ${color}`}>{score ?? '-'}</span>
  )
}

export default PRDetail
