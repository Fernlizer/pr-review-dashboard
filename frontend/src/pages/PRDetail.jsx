/* Hallmark · pre-emit critique: P5 H5 E4 S5 R4 V5 */
/* Hallmark · genre: atmospheric · macrostructure: Scan Chamber · theme: custom Night Garden */

import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle,
  Clock,
  FileCode,
  GitBranch,
  Loader2,
  MessageSquare,
  ExternalLink,
  Radio,
  RefreshCw,
  Shield,
  Wrench,
  XCircle,
} from 'lucide-react'

function LoadingSkeleton() {
  return (
    <div className="page-frame" style={{ display: 'grid', gap: 'var(--space-md)' }}>
      <div className="skeleton" style={{ height: 220 }} />
      <div className="skeleton" style={{ height: 420 }} />
    </div>
  )
}

function RecommendationBadge({ review }) {
  if (!review) return null
  if (review.status === 'running') {
    return (
      <span className="mono" style={badgeStyle('var(--color-accent-bg)', 'var(--color-accent)')}>
        <Loader2 className="w-4 h-4" style={{ animation: 'orbit-turn 1.2s linear infinite' }} />
        scanning
      </span>
    )
  }
  if (review.status === 'failed') {
    return <span className="mono" style={badgeStyle('var(--color-danger-bg)', 'var(--color-danger)')}><XCircle className="w-4 h-4" />failed</span>
  }
  const config = {
    approve: ['clear', 'var(--color-success-bg)', 'var(--color-success)', CheckCircle],
    request_changes: ['mutate', 'var(--color-danger-bg)', 'var(--color-danger)', XCircle],
    comment: ['observe', 'var(--color-warning-bg)', 'var(--color-warning)', MessageSquare],
  }
  const [label, bg, fg, Icon] = config[review.recommendation] || [review.recommendation || 'reviewed', 'var(--color-paper-3)', 'var(--color-ink-3)', MessageSquare]
  return <span className="mono" style={badgeStyle(bg, fg)}><Icon className="w-4 h-4" />{label}</span>
}

function ScoreCell({ label, value }) {
  const score = Number(value || 0)
  const tone = score >= 8 ? 'var(--color-success)' : score >= 5 ? 'var(--color-warning)' : 'var(--color-danger)'
  return (
    <div className="panel-soft" style={{ padding: 'var(--space-md)' }}>
      <p className="mono" style={{ color: 'var(--color-ink-4)', fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>{label}</p>
      <p className="mono" style={{ marginTop: 'var(--space-sm)', color: tone, fontSize: 'var(--text-2xl)', fontWeight: 800, lineHeight: 1 }}>{score.toFixed(1)}</p>
    </div>
  )
}

function FindingCard({ finding, selected, onSelect }) {
  const tone = finding.severity === 'HIGH'
    ? ['var(--color-danger)', 'var(--color-danger-bg)']
    : finding.severity === 'MEDIUM'
      ? ['var(--color-warning)', 'var(--color-warning-bg)']
      : ['var(--color-info)', 'var(--color-info-bg)']

  return (
    <article className="panel-soft" style={{ padding: 'var(--space-md)', borderColor: tone[0] }}>
      <div className="flex items-start gap-sm">
        <input
          type="checkbox"
          checked={selected}
          onChange={onSelect}
          style={{ width: 18, height: 18, marginTop: 2, accentColor: tone[0] }}
          aria-label={`Select finding ${finding.id}`}
        />
        <div className="min-w-0" style={{ flex: 1 }}>
          <div className="flex items-center gap-xs flex-wrap">
            <span className="mono" style={{ color: tone[0], background: tone[1], borderRadius: 'var(--radius-full)', padding: '0.35rem 0.65rem', fontSize: 'var(--text-xs)', fontWeight: 800 }}>
              {finding.severity}
            </span>
            <span className="mono" style={{ color: 'var(--color-ink-4)', fontSize: 'var(--text-xs)' }}>{finding.category}</span>
            {finding.owasp_tag && <span className="mono" style={{ color: 'var(--color-ink-4)', fontSize: 'var(--text-xs)' }}>{finding.owasp_tag}</span>}
          </div>
          <p style={{ marginTop: 'var(--space-sm)', color: 'var(--color-ink)', lineHeight: 1.65 }}>{finding.description}</p>
          <div className="panel" style={{ marginTop: 'var(--space-sm)', padding: 'var(--space-sm)', borderRadius: 'var(--radius-md)', boxShadow: 'none' }}>
            <p className="mono" style={{ color: 'var(--color-info)', fontSize: 'var(--text-xs)' }}>
              {finding.file_path}:{finding.line_number}
            </p>
            {finding.code_snippet && (
              <pre className="mono" style={{ marginTop: 'var(--space-xs)', color: 'var(--color-ink-2)', fontSize: 'var(--text-xs)', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
                {finding.code_snippet}
              </pre>
            )}
          </div>
          {finding.fix_suggestion && (
            <div style={{ display: 'flex', gap: 'var(--space-xs)', marginTop: 'var(--space-sm)', color: 'var(--color-success)' }}>
              <Wrench className="w-4 h-4 flex-shrink-0" />
              <p style={{ color: 'var(--color-ink-2)', lineHeight: 1.6 }}>{finding.fix_suggestion}</p>
            </div>
          )}
        </div>
      </div>
    </article>
  )
}

function PRDetail() {
  const { id } = useParams()
  const [pr, setPr] = useState(null)
  const [activeTab, setActiveTab] = useState('findings')
  const [selectedFindings, setSelectedFindings] = useState(new Set())
  const [commenting, setCommenting] = useState(false)
  const [commentResult, setCommentResult] = useState(null)
  const [reviewing, setReviewing] = useState(false)

  const fetchPr = () => {
    fetch(`/api/prs/${id}`).then(r => r.json()).then(setPr)
  }

  useEffect(() => {
    fetchPr()
  }, [id])

  const review = pr?.reviews?.[0]

  useEffect(() => {
    if (review?.status !== 'running') return
    const timer = setInterval(fetchPr, 3000)
    return () => clearInterval(timer)
  }, [review?.status, id])

  const findings = review?.findings || []
  const counts = useMemo(() => ({
    high: findings.filter(f => f.severity === 'HIGH').length,
    medium: findings.filter(f => f.severity === 'MEDIUM').length,
    low: findings.filter(f => f.severity === 'LOW').length,
  }), [findings])

  const commentableIds = useMemo(() => findings.filter(f => ['HIGH', 'MEDIUM'].includes(f.severity)).map(f => f.id), [findings])

  if (!pr) return <LoadingSkeleton />

  const toggleFinding = (findingId) => {
    setSelectedFindings(prev => {
      const next = new Set(prev)
      if (next.has(findingId)) next.delete(findingId)
      else next.add(findingId)
      return next
    })
  }

  const selectCommentable = () => {
    setSelectedFindings(new Set(commentableIds))
  }

  const commentSelected = async () => {
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
      setCommentResult(resp.ok ? data : { errors: [data.detail || 'Failed to post comments'] })
    } catch (e) {
      setCommentResult({ errors: [e.message] })
    } finally {
      setCommenting(false)
    }
  }

  const runReview = async () => {
    setReviewing(true)
    try {
      const resp = await fetch(`/api/prs/${id}/review`, { method: 'POST' })
      const data = await resp.json()
      if (data.status === 'started') setTimeout(fetchPr, 500)
    } finally {
      setReviewing(false)
    }
  }

  return (
    <div className="page-frame" style={{ display: 'grid', gap: 'var(--space-lg)' }}>
      <Link to="/prs" className="mono" style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-xs)', color: 'var(--color-ink-3)', textDecoration: 'none', width: 'fit-content', whiteSpace: 'nowrap' }}>
        <ArrowLeft className="w-4 h-4" />
        back to signals
      </Link>

      <section className={`panel ${review?.status === 'running' ? 'panel-live' : ''} reveal`} style={{ padding: 'var(--space-xl)' }}>
        <div className="flex items-start justify-between gap-lg flex-wrap">
          <div className="min-w-0" style={{ flex: '1 1 34rem' }}>
            <div className="flex items-center gap-xs flex-wrap">
              <p className="kicker">scan chamber</p>
              <RecommendationBadge review={review} />
            </div>
            <h1 className="display-title" style={{ marginTop: 'var(--space-sm)', fontSize: 'clamp(2rem, 4vw, 4rem)' }}>
              {pr.title}
            </h1>
            <div className="flex items-center gap-sm flex-wrap" style={{ marginTop: 'var(--space-md)', color: 'var(--color-ink-3)' }}>
              <span className="mono">{pr.repo} #{pr.azure_pr_id}</span>
              <span>·</span>
              <span>{pr.author || 'Unknown author'}</span>
              <span>·</span>
              <span className="flex items-center gap-2xs"><GitBranch className="w-4 h-4" /> {pr.source_branch} → {pr.target_branch}</span>
            </div>
          </div>
          <div className="flex items-center gap-sm flex-wrap">
            {pr.url && (
              <a
                href={pr.url}
                target="_blank"
                rel="noopener noreferrer"
                style={externalButton}
                aria-label={`Open Azure DevOps PR #${pr.azure_pr_id} in a new tab`}
              >
                <ExternalLink className="w-4 h-4" />
                Open PR
              </a>
            )}
            <button
              onClick={runReview}
              disabled={reviewing || review?.status === 'running'}
              style={primaryButton}
            >
              {reviewing || review?.status === 'running' ? <Loader2 className="w-4 h-4" style={{ animation: 'orbit-turn 1.2s linear infinite' }} /> : <RefreshCw className="w-4 h-4" />}
              {review?.status === 'running' ? 'Scanning' : 'Run review'}
            </button>
          </div>
        </div>

        {review && (
          <div className="grid grid-cols-2 md:grid-cols-5 gap-sm" style={{ marginTop: 'var(--space-xl)' }}>
            <ScoreCell label="logic" value={review.score_logic} />
            <ScoreCell label="security" value={review.score_security} />
            <ScoreCell label="tests" value={review.score_tests} />
            <ScoreCell label="style" value={review.score_style} />
            <ScoreCell label="arch" value={review.score_architecture} />
          </div>
        )}
      </section>

      {review ? (
        <>
          <section className="grid grid-cols-1 xl:grid-cols-[0.9fr_1.1fr] gap-md">
            <div className="panel reveal" style={{ padding: 'var(--space-lg)' }}>
              <p className="kicker">summary signal</p>
              <p style={{ marginTop: 'var(--space-md)', color: 'var(--color-ink-2)', fontSize: 'var(--text-md)', lineHeight: 1.75 }}>
                {review.summary || (review.status === 'running' ? 'Review is running...' : 'No summary available.')}
              </p>
              <div className="grid grid-cols-3 gap-sm" style={{ marginTop: 'var(--space-lg)' }}>
                <RiskPill label="high" value={counts.high} color="var(--color-danger)" />
                <RiskPill label="medium" value={counts.medium} color="var(--color-warning)" />
                <RiskPill label="low" value={counts.low} color="var(--color-info)" />
              </div>
            </div>

            <div className="panel reveal" style={{ padding: 'var(--space-lg)' }}>
              <p className="kicker">comment operation</p>
              <p style={{ marginTop: 'var(--space-md)', color: 'var(--color-ink-3)', lineHeight: 1.65 }}>
                Select HIGH/MEDIUM findings and post inline comments to the reviewed Azure iteration. Dedup remains backend-controlled.
              </p>
              <div className="flex items-center gap-sm flex-wrap" style={{ marginTop: 'var(--space-lg)' }}>
                <button onClick={selectCommentable} disabled={!commentableIds.length} style={secondaryButton}>
                  select risky lines
                </button>
                <button onClick={commentSelected} disabled={commenting || selectedFindings.size === 0} style={primaryButton}>
                  {commenting ? <Loader2 className="w-4 h-4" style={{ animation: 'orbit-turn 1.2s linear infinite' }} /> : <MessageSquare className="w-4 h-4" />}
                  comment {selectedFindings.size || ''}
                </button>
              </div>
              {commentResult && (
                <div className="panel-soft" style={{ marginTop: 'var(--space-md)', padding: 'var(--space-sm)' }}>
                  <p style={{ color: commentResult.errors?.length ? 'var(--color-warning)' : 'var(--color-accent)' }}>
                    Posted {commentResult.posted || 0}, skipped {commentResult.skipped || 0}
                  </p>
                  {commentResult.errors?.map((err, i) => <p key={i} style={{ color: 'var(--color-danger)', marginTop: 'var(--space-2xs)' }}>{err}</p>)}
                </div>
              )}
            </div>
          </section>

          <section className="panel reveal" style={{ overflow: 'hidden' }}>
            <div className="flex items-center gap-xs flex-wrap" style={{ padding: 'var(--space-md)', borderBottom: '1px solid var(--color-rule)' }}>
              {[
                ['findings', 'Anomalies', AlertTriangle],
                ['diff', 'Raw diff', FileCode],
              ].map(([key, label, Icon]) => (
                <button
                  key={key}
                  onClick={() => setActiveTab(key)}
                  style={{
                    minHeight: 40,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 'var(--space-xs)',
                    border: '1px solid var(--color-rule)',
                    borderRadius: 'var(--radius-full)',
                    background: activeTab === key ? 'var(--color-accent-bg)' : 'transparent',
                    color: activeTab === key ? 'var(--color-accent)' : 'var(--color-ink-3)',
                    padding: '0 var(--space-md)',
                    whiteSpace: 'nowrap',
                  }}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>

            {activeTab === 'findings' ? (
              <div style={{ padding: 'var(--space-md)', display: 'grid', gap: 'var(--space-sm)' }}>
                {findings.length ? findings.map(f => (
                  <FindingCard key={f.id} finding={f} selected={selectedFindings.has(f.id)} onSelect={() => toggleFinding(f.id)} />
                )) : (
                  <div style={{ padding: 'var(--space-3xl)', textAlign: 'center' }}>
                    <Shield className="w-8 h-8 mx-auto" style={{ color: 'var(--color-success)' }} />
                    <p style={{ marginTop: 'var(--space-md)', color: 'var(--color-ink)', fontWeight: 800 }}>
                      {review.status === 'running' ? 'The scan is still breathing.' : 'No changed-line anomalies found.'}
                    </p>
                    <p style={{ color: 'var(--color-ink-3)', marginTop: 'var(--space-2xs)' }}>
                      {review.status === 'running' ? 'Findings will appear here when scanners finish.' : 'This review did not produce findings.'}
                    </p>
                  </div>
                )}
              </div>
            ) : (
              <pre className="mono" style={{ margin: 0, padding: 'var(--space-md)', color: 'var(--color-ink-2)', fontSize: 'var(--text-xs)', lineHeight: 1.75, maxHeight: 620, overflow: 'auto', whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
                {review.raw_diff || 'No raw diff stored for this review.'}
              </pre>
            )}
          </section>
        </>
      ) : (
        <section className="panel" style={{ padding: 'var(--space-3xl)', textAlign: 'center' }}>
          <Clock className="w-8 h-8 mx-auto" style={{ color: 'var(--color-ink-4)' }} />
          <p style={{ marginTop: 'var(--space-md)', color: 'var(--color-ink)', fontWeight: 800 }}>This PR has not been reviewed yet.</p>
          <p style={{ color: 'var(--color-ink-3)', marginTop: 'var(--space-2xs)' }}>Run review to open a scan chamber.</p>
        </section>
      )}
    </div>
  )
}

function RiskPill({ label, value, color }) {
  return (
    <div className="panel-soft" style={{ padding: 'var(--space-sm)' }}>
      <p className="mono" style={{ color, fontSize: 'var(--text-xl)', fontWeight: 800, lineHeight: 1 }}>{value}</p>
      <p className="mono" style={{ color: 'var(--color-ink-4)', fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: '0.12em', marginTop: 'var(--space-xs)' }}>{label}</p>
    </div>
  )
}

const badgeStyle = (bg, fg) => ({
  display: 'inline-flex',
  alignItems: 'center',
  gap: 'var(--space-2xs)',
  padding: '0.45rem 0.75rem',
  borderRadius: 'var(--radius-full)',
  background: bg,
  color: fg,
  fontSize: 'var(--text-xs)',
  fontWeight: 800,
  textTransform: 'uppercase',
  letterSpacing: '0.08em',
})

const primaryButton = {
  minHeight: 44,
  display: 'flex',
  alignItems: 'center',
  gap: 'var(--space-xs)',
  border: 0,
  borderRadius: 'var(--radius-input)',
  background: 'var(--color-accent)',
  color: 'var(--color-accent-ink)',
  padding: '0 var(--space-md)',
  fontWeight: 800,
  whiteSpace: 'nowrap',
}

const secondaryButton = {
  ...primaryButton,
  border: '1px solid var(--color-rule)',
  background: 'var(--color-paper-3)',
  color: 'var(--color-ink-2)',
}

const externalButton = {
  ...primaryButton,
  border: '1px solid var(--color-rule-living)',
  background: 'var(--color-accent-bg)',
  color: 'var(--color-accent)',
  textDecoration: 'none',
}

export default PRDetail
