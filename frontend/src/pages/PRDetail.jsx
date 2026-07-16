/* Hallmark · genre: atmospheric · macrostructure: Workbench · design-system: design.md · designed-as-app */

import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import {
  ArrowLeft, ExternalLink, Clock, Shield, AlertTriangle,
  CheckCircle, XCircle, MessageSquare, FileCode, Wrench,
  Loader2, Play
} from 'lucide-react'

/* ── Card base ───────────────────────────────────────────────────── */

const cardStyle = {
  background: 'var(--color-paper-2)',
  border: '1px solid var(--color-rule)',
  borderRadius: 'var(--radius-lg)',
}

const sectionLabel = {
  fontSize: 'var(--text-xs)',
  fontWeight: 600,
  color: 'var(--color-ink-3)',
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
  fontFamily: 'var(--font-mono)',
}

/* ── Loading skeleton ────────────────────────────────────────────── */

function LoadingSkeleton() {
  return (
    <div className="p-lg space-y-md animate-fade-in">
      <div className="flex items-center gap-md">
        <div className="skeleton" style={{ width: 36, height: 36, borderRadius: 'var(--radius-md)' }} />
        <div className="space-y-2xs flex-1">
          <div className="skeleton" style={{ height: 18, width: 120 }} />
          <div className="skeleton" style={{ height: 24, width: 380 }} />
          <div className="skeleton" style={{ height: 14, width: 240 }} />
        </div>
      </div>
      <div style={{ ...cardStyle, padding: 'var(--space-lg)' }}>
        <div className="skeleton" style={{ height: 240 }} />
      </div>
    </div>
  )
}

/* ── Score ring ──────────────────────────────────────────────────── */

function ScoreCard({ label, score }) {
  const pct = score != null ? (score / 10) * 100 : 0
  const circumference = 2 * Math.PI * 20
  const offset = circumference - (pct / 100) * circumference

  let color = 'var(--color-danger)'
  if (score >= 8) color = 'var(--color-success)'
  else if (score >= 5) color = 'var(--color-warning)'

  return (
    <div className="flex flex-col items-center" style={{ gap: 8, padding: 'var(--space-xs) 0' }}>
      <div className="relative" style={{ width: 52, height: 52 }}>
        <svg style={{ width: 52, height: 52, transform: 'rotate(-90deg)' }} viewBox="0 0 48 48">
          <circle cx="24" cy="24" r="20" fill="none" stroke="var(--color-paper-3)" strokeWidth="3" />
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
          <span
            className="font-bold font-mono"
            style={{ fontSize: 'var(--text-md)', color: 'var(--color-ink)' }}
          >
            {score ?? '–'}
          </span>
        </div>
      </div>
      <span className="font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-3)' }}>
        {label}
      </span>
    </div>
  )
}

/* ── Finding card ────────────────────────────────────────────────── */

function FindingCard({ finding, index }) {
  const severityConfig = {
    HIGH: {
      border: 'var(--color-danger)',
      bg: 'var(--color-danger-bg)',
      badge: { bg: 'var(--color-danger-bg)', text: 'var(--color-danger)' },
    },
    MEDIUM: {
      border: 'var(--color-warning)',
      bg: 'var(--color-warning-bg)',
      badge: { bg: 'var(--color-warning-bg)', text: 'var(--color-warning)' },
    },
    LOW: {
      border: 'var(--color-info)',
      bg: 'var(--color-info-bg)',
      badge: { bg: 'var(--color-info-bg)', text: 'var(--color-info)' },
    },
  }
  const sev = severityConfig[finding.severity] || severityConfig.LOW

  return (
    <div
      className="reveal"
      style={{
        border: `1px solid ${sev.border}`,
        background: sev.bg,
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-md)',
        '--i': index,
      }}
    >
      {/* Header */}
      <div className="flex items-center gap-2xs flex-wrap" style={{ marginBottom: 'var(--space-sm)' }}>
        <span
          className="font-bold uppercase font-mono"
          style={{
            fontSize: 'var(--text-xs)',
            padding: '2px 8px',
            borderRadius: 'var(--radius-sm)',
            background: sev.badge.bg,
            color: sev.badge.text,
            letterSpacing: '0.05em',
          }}
        >
          {finding.severity}
        </span>
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
          {finding.category}
        </span>
        {finding.owasp_tag && (
          <span className="font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-4)' }}>
            {finding.owasp_tag}
          </span>
        )}
        {finding.is_automated && (
          <span
            className="font-medium"
            style={{ fontSize: 'var(--text-xs)', padding: '2px 8px', borderRadius: 'var(--radius-sm)', background: 'var(--color-accent-bg)', color: 'var(--color-accent)' }}
          >
            Auto
          </span>
        )}
      </div>

      {/* File path */}
      <div className="flex items-center gap-2xs" style={{ marginBottom: 8 }}>
        <FileCode className="w-3.5 h-3.5 flex-shrink-0" style={{ color: 'var(--color-ink-4)' }} />
        <span className="font-mono truncate" style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-2)' }}>
          {finding.file_path}:{finding.line_number}
        </span>
      </div>

      {/* Description */}
      {finding.description && (
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-2)', lineHeight: 1.6, marginBottom: 'var(--space-sm)' }}>
          {finding.description}
        </p>
      )}

      {/* Code snippet */}
      {finding.code_snippet && (
        <div
          className="overflow-x-auto"
          style={{
            background: 'var(--color-paper)',
            border: '1px solid var(--color-rule)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-xs) var(--space-sm)',
            marginBottom: 'var(--space-sm)',
          }}
        >
          <code className="font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)', lineHeight: 1.7 }}>
            {finding.code_snippet}
          </code>
        </div>
      )}

      {/* Fix suggestion */}
      {finding.fix_suggestion && (
        <div
          style={{
            background: 'var(--color-success-bg)',
            border: '1px solid var(--color-success)',
            borderRadius: 'var(--radius-md)',
            padding: 'var(--space-xs) var(--space-sm)',
          }}
        >
          <div className="flex items-center gap-2xs" style={{ marginBottom: 6 }}>
            <Wrench className="w-3.5 h-3.5" style={{ color: 'var(--color-success)' }} />
            <span className="font-semibold uppercase font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-success)', letterSpacing: '0.06em' }}>
              Fix Suggestion
            </span>
          </div>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink)', lineHeight: 1.6 }}>
            {finding.fix_suggestion}
          </p>
        </div>
      )}
    </div>
  )
}

/* ── Recommendation badge ────────────────────────────────────────── */

function RecommendationBadge({ rec }) {
  const config = {
    approve: { bg: 'var(--color-success-bg)', text: 'var(--color-success)', icon: CheckCircle, label: 'Approve' },
    request_changes: { bg: 'var(--color-danger-bg)', text: 'var(--color-danger)', icon: XCircle, label: 'Request Changes' },
    comment: { bg: 'var(--color-warning-bg)', text: 'var(--color-warning)', icon: MessageSquare, label: 'Comment' },
  }
  const c = config[rec] || { bg: 'var(--color-paper-3)', text: 'var(--color-ink-2)', icon: MessageSquare, label: rec }
  const Icon = c.icon

  return (
    <span
      className="inline-flex items-center gap-2xs font-medium"
      style={{
        fontSize: 'var(--text-sm)',
        padding: '6px 14px',
        borderRadius: 'var(--radius-md)',
        background: c.bg,
        color: c.text,
      }}
    >
      <Icon className="w-3.5 h-3.5" />
      {c.label}
    </span>
  )
}

/* ── PR Detail ───────────────────────────────────────────────────── */

function PRDetail() {
  const { id } = useParams()
  const [pr, setPr] = useState(null)
  const [activeTab, setActiveTab] = useState('findings')
  const [runningReview, setRunningReview] = useState(false)
  const [selectedFindings, setSelectedFindings] = useState(new Set())
  const [commenting, setCommenting] = useState(false)
  const [commentResult, setCommentResult] = useState(null)

  useEffect(() => {
    fetch(`/api/prs/${id}`).then(r => r.json()).then(setPr)
  }, [id])

  if (!pr) return <LoadingSkeleton />

  const review = pr.reviews?.[0]
  const findings = review?.findings || []
  const highFindings = findings.filter(f => f.severity === 'HIGH')
  const mediumFindings = findings.filter(f => f.severity === 'MEDIUM')
  const lowFindings = findings.filter(f => f.severity === 'LOW')

  const toggleFinding = (findingId) => {
    setSelectedFindings(prev => {
      const next = new Set(prev)
      if (next.has(findingId)) next.delete(findingId)
      else next.add(findingId)
      return next
    })
  }

  const toggleAll = () => {
    if (selectedFindings.size === findings.length) {
      setSelectedFindings(new Set())
    } else {
      setSelectedFindings(new Set(findings.map(f => f.id)))
    }
  }

  const handleCommentSelected = async () => {
    if (!review || selectedFindings.size === 0) return
    setCommenting(true)
    setCommentResult(null)
    try {
      const resp = await fetch(`/api/reviews/${review.id}/comment-selected`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ finding_ids: Array.from(selectedFindings) }),
      })
      const data = await resp.json()
      setCommentResult(data)
      setSelectedFindings(new Set())
    } catch (e) {
      setCommentResult({ error: e.message })
    } finally {
      setCommenting(false)
    }
  }

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

  const tabBase = {
    padding: '8px 16px',
    borderRadius: 'var(--radius-md)',
    fontSize: 'var(--text-sm)',
    fontWeight: 500,
    cursor: 'pointer',
    border: 'none',
    fontFamily: 'var(--font-body)',
    transition: `all var(--dur-micro) var(--ease-out)`,
  }

  const btnPrimary = {
    background: 'var(--color-accent)',
    color: 'var(--color-accent-ink)',
    border: 'none',
    borderRadius: 'var(--radius-md)',
    padding: '10px 20px',
    fontSize: 'var(--text-sm)',
    fontWeight: 600,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    fontFamily: 'var(--font-body)',
    transition: `all var(--dur-short) var(--ease-out)`,
  }

  return (
    <div className="p-lg space-y-md animate-fade-in" style={{ maxWidth: 1200 }}>
      {/* Header */}
      <div className="flex items-start gap-md">
        <Link
          to="/prs"
          className="flex items-center justify-center flex-shrink-0"
          style={{
            width: 36,
            height: 36,
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--color-rule)',
            color: 'var(--color-ink-3)',
            textDecoration: 'none',
            marginTop: 2,
            transition: `all var(--dur-micro) var(--ease-out)`,
          }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = 'var(--color-paper-4)'
            e.currentTarget.style.color = 'var(--color-ink)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = 'var(--color-rule)'
            e.currentTarget.style.color = 'var(--color-ink-3)'
          }}
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2xs" style={{ marginBottom: 6 }}>
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
              <span className="font-medium" style={{ fontSize: 'var(--text-xs)', padding: '2px 8px', borderRadius: 'var(--radius-sm)', background: 'var(--color-danger-bg)', color: 'var(--color-danger)' }}>
                Required Reviewer
              </span>
            )}
          </div>
          <h2 className="font-semibold tracking-tight leading-snug" style={{ fontSize: 'var(--text-lg)', color: 'var(--color-ink)', letterSpacing: '-0.02em' }}>
            {pr.title}
          </h2>
          <div className="flex items-center gap-sm flex-wrap" style={{ marginTop: 6, fontSize: 'var(--text-sm)', color: 'var(--color-ink-3)' }}>
            <span>{pr.author}</span>
            <span style={{ color: 'var(--color-ink-4)' }}>·</span>
            <span className="font-mono">{pr.source_branch} → {pr.target_branch}</span>
          </div>
        </div>
        <a
          href={pr.url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2xs flex-shrink-0"
          style={{
            padding: '8px 16px',
            background: 'var(--color-paper-2)',
            border: '1px solid var(--color-rule)',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--text-sm)',
            color: 'var(--color-ink-2)',
            textDecoration: 'none',
            transition: `all var(--dur-micro) var(--ease-out)`,
          }}
          onMouseEnter={e => {
            e.currentTarget.style.borderColor = 'var(--color-paper-4)'
            e.currentTarget.style.color = 'var(--color-ink)'
          }}
          onMouseLeave={e => {
            e.currentTarget.style.borderColor = 'var(--color-rule)'
            e.currentTarget.style.color = 'var(--color-ink-2)'
          }}
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Azure DevOps
        </a>
      </div>

      {/* Review Summary */}
      {review && (
        <div className="reveal" style={{ ...cardStyle, padding: 'var(--space-lg)' }}>
          {/* Top bar */}
          <div className="flex items-center justify-between flex-wrap gap-sm" style={{ marginBottom: 'var(--space-lg)' }}>
            <div className="flex items-center gap-sm">
              <RecommendationBadge rec={review.recommendation} />
              <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-4)' }}>
                {review.duration_seconds}s · {findings.length} finding{findings.length !== 1 ? 's' : ''}
              </span>
            </div>
            <div className="flex items-center gap-2xs">
              {highFindings.length > 0 && (
                <span className="font-mono font-medium" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-danger)', background: 'var(--color-danger-bg)', padding: '4px 8px', borderRadius: 'var(--radius-sm)' }}>
                  {highFindings.length} HIGH
                </span>
              )}
              {mediumFindings.length > 0 && (
                <span className="font-mono font-medium" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-warning)', background: 'var(--color-warning-bg)', padding: '4px 8px', borderRadius: 'var(--radius-sm)' }}>
                  {mediumFindings.length} MED
                </span>
              )}
              {lowFindings.length > 0 && (
                <span className="font-mono font-medium" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-info)', background: 'var(--color-info-bg)', padding: '4px 8px', borderRadius: 'var(--radius-sm)' }}>
                  {lowFindings.length} LOW
                </span>
              )}
            </div>
          </div>

          {/* Score Cards */}
          <div className="grid grid-cols-5 gap-xs" style={{ marginBottom: 'var(--space-md)' }}>
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
            <div
              style={{
                background: 'var(--color-paper-3)',
                border: '1px solid var(--color-rule)',
                borderRadius: 'var(--radius-md)',
                padding: 'var(--space-sm) var(--space-md)',
              }}
            >
              <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-2)', lineHeight: 1.6 }}>
                {review.summary}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Tabs */}
      <div
        className="flex"
        style={{
          gap: 4,
          background: 'var(--color-paper-2)',
          border: '1px solid var(--color-rule)',
          borderRadius: 'var(--radius-md)',
          padding: 4,
          width: 'fit-content',
        }}
      >
        {[
          { id: 'findings', label: `Findings (${findings.length})` },
          { id: 'diff', label: 'Diff' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              ...tabBase,
              background: activeTab === tab.id ? 'var(--color-paper-3)' : 'transparent',
              color: activeTab === tab.id ? 'var(--color-ink)' : 'var(--color-ink-3)',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Findings Tab */}
      {activeTab === 'findings' && (
        <div className="space-y-xs">
          {findings.length === 0 && review?.status === 'completed' ? (
            <div style={cardStyle}>
              <div className="flex flex-col items-center justify-center" style={{ padding: 'var(--space-3xl) var(--space-lg)' }}>
                <div
                  className="rounded-lg flex items-center justify-center"
                  style={{ width: 48, height: 48, background: 'var(--color-success-bg)', marginBottom: 'var(--space-md)' }}
                >
                  <Shield className="w-5 h-5" style={{ color: 'var(--color-success)' }} />
                </div>
                <p className="font-medium" style={{ fontSize: 'var(--text-base)', color: 'var(--color-ink-2)' }}>
                  No findings — clean review
                </p>
                <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-3)', marginTop: 4 }}>
                  This PR passed all security checks.
                </p>
              </div>
            </div>
          ) : findings.length === 0 ? (
            <div style={cardStyle}>
              <div className="flex flex-col items-center justify-center" style={{ padding: 'var(--space-3xl) var(--space-lg)' }}>
                <div
                  className="rounded-lg flex items-center justify-center"
                  style={{ width: 48, height: 48, background: 'var(--color-paper-3)', marginBottom: 'var(--space-md)' }}
                >
                  <Clock className="w-5 h-5" style={{ color: 'var(--color-ink-4)' }} />
                </div>
                <p className="font-medium" style={{ fontSize: 'var(--text-base)', color: 'var(--color-ink-2)' }}>
                  Not yet reviewed
                </p>
                <p style={{ fontSize: 'var(--text-sm)', color: 'var(--color-ink-3)', marginTop: 4, marginBottom: 'var(--space-md)', textAlign: 'center', maxWidth: 320 }}>
                  This PR was recorded without a review (old PR).
                </p>
                <button
                  onClick={handleRunReview}
                  disabled={runningReview}
                  style={{
                    ...btnPrimary,
                    opacity: runningReview ? 0.6 : 1,
                    cursor: runningReview ? 'not-allowed' : 'pointer',
                  }}
                >
                  {runningReview ? (
                    <>
                      <Loader2 className="w-4 h-4" style={{ animation: 'spin 1s linear infinite' }} />
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
            <>
              {/* Select All + Comment Selected bar */}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 'var(--space-sm)' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2xs)', cursor: 'pointer', fontSize: 'var(--text-sm)', color: 'var(--color-ink-2)' }}>
                  <input
                    type="checkbox"
                    checked={selectedFindings.size === findings.length && findings.length > 0}
                    onChange={toggleAll}
                    style={{ accentColor: 'var(--color-accent)', width: 16, height: 16 }}
                  />
                  Select All ({selectedFindings.size}/{findings.length})
                </label>

                {selectedFindings.size > 0 && (
                  <button
                    onClick={handleCommentSelected}
                    disabled={commenting}
                    style={{
                      display: 'flex', alignItems: 'center', gap: 'var(--space-2xs)',
                      padding: 'var(--space-2xs) var(--space-md)',
                      background: 'var(--color-accent)', color: 'var(--color-accent-ink)',
                      border: 'none', borderRadius: 'var(--radius-input)',
                      fontSize: 'var(--text-sm)', fontWeight: 600, cursor: 'pointer',
                      opacity: commenting ? 0.6 : 1,
                    }}
                  >
                    {commenting ? (
                      <><Loader2 className="w-4 h-4" style={{ animation: 'spin 1s linear infinite' }} /> Posting...</>
                    ) : (
                      <><MessageSquare className="w-4 h-4" /> Comment Selected ({selectedFindings.size})</>
                    )}
                  </button>
                )}
              </div>

              {/* Comment result */}
              {commentResult && (
                <div style={{
                  padding: 'var(--space-sm)', borderRadius: 'var(--radius-card)',
                  marginBottom: 'var(--space-sm)',
                  background: commentResult.error ? 'rgba(255,80,80,0.1)' : 'rgba(80,200,120,0.1)',
                  border: `1px solid ${commentResult.error ? 'rgba(255,80,80,0.2)' : 'rgba(80,200,120,0.2)'}`,
                  fontSize: 'var(--text-sm)', color: 'var(--color-ink)',
                }}>
                  {commentResult.error
                    ? `❌ Error: ${commentResult.error}`
                    : `✅ Posted: ${commentResult.posted} | Skipped: ${commentResult.skipped}${commentResult.errors?.length ? ` | Errors: ${commentResult.errors.length}` : ''}`
                  }
                </div>
              )}

              {findings.map((f, i) => (
                <div key={f.id} style={{ display: 'flex', gap: 'var(--space-sm)', alignItems: 'flex-start' }}>
                  <input
                    type="checkbox"
                    checked={selectedFindings.has(f.id)}
                    onChange={() => toggleFinding(f.id)}
                    style={{
                      accentColor: 'var(--color-accent)', width: 16, height: 16,
                      marginTop: 'var(--space-sm)', flexShrink: 0,
                    }}
                  />
                  <div style={{ flex: 1 }}>
                    <FindingCard finding={f} index={i} />
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      )}

      {/* Diff Tab */}
      {activeTab === 'diff' && review?.raw_diff && (
        <div style={{ ...cardStyle, overflow: 'hidden' }}>
          <div
            className="flex items-center gap-2xs"
            style={{ padding: '10px var(--space-md)', borderBottom: '1px solid var(--color-rule)' }}
          >
            <FileCode className="w-4 h-4" style={{ color: 'var(--color-ink-4)' }} />
            <span className="font-medium" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-3)' }}>Raw Diff</span>
          </div>
          <div className="overflow-auto" style={{ padding: 'var(--space-md)', maxHeight: 600 }}>
            <pre className="font-mono" style={{ fontSize: 'var(--text-xs)', color: 'var(--color-ink-2)', whiteSpace: 'pre-wrap', lineHeight: 1.7 }}>
              {review.raw_diff.split('\n').map((line, i) => {
                let color = 'var(--color-ink-3)'
                let bg = 'transparent'
                if (line.startsWith('+')) { color = 'var(--color-success)'; bg = 'var(--color-success-bg)' }
                else if (line.startsWith('-')) { color = 'var(--color-danger)'; bg = 'var(--color-danger-bg)' }
                else if (line.startsWith('@@')) { color = 'var(--color-info)' }
                else if (line.startsWith('===')) { color = 'var(--color-warning)' }
                return (
                  <div key={i} style={{ padding: '0 var(--space-xs)', margin: '0 calc(var(--space-xs) * -1)', color, background: bg }}>
                    {line}
                  </div>
                )
              })}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

export default PRDetail
