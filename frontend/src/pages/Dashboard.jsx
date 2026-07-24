/* Hallmark · pre-emit critique: P5 H5 E4 S5 R4 V5 */
/* Hallmark · genre: atmospheric · macrostructure: Living Orbit Workbench · theme: custom Night Garden · audience: single operator */

import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowUpRight,
  CheckCircle,
  FileSearch,
  Flame,
  GitPullRequest,
  Loader2,
  MessageSquare,
  Radar,
  Search,
  ShieldCheck,
  Sparkles,
  XCircle,
} from 'lucide-react'

const badgeTone = {
  approve: { label: 'clear', bg: 'var(--color-success-bg)', fg: 'var(--color-success)', Icon: CheckCircle },
  request_changes: { label: 'mutate', bg: 'var(--color-danger-bg)', fg: 'var(--color-danger)', Icon: XCircle },
  comment: { label: 'observe', bg: 'var(--color-warning-bg)', fg: 'var(--color-warning)', Icon: MessageSquare },
}

function LoadingSkeleton() {
  return (
    <div className="page-frame" style={{ display: 'grid', gap: 'var(--space-lg)' }}>
      <div className="skeleton" style={{ height: 220 }} />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-md">
        <div className="skeleton" style={{ height: 240 }} />
        <div className="skeleton lg:col-span-2" style={{ height: 240 }} />
      </div>
    </div>
  )
}

function SignalBadge({ review }) {
  if (review?.status === 'running') {
    return (
      <span className="mono" style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2xs)', padding: '0.35rem 0.65rem', borderRadius: 'var(--radius-full)', background: 'var(--color-accent-bg)', color: 'var(--color-accent)', fontSize: 'var(--text-xs)', fontWeight: 700 }}>
        <Loader2 className="w-3 h-3" style={{ animation: 'orbit-turn 1.2s linear infinite' }} />
        scanning
      </span>
    )
  }

  if (review?.status === 'failed') {
    return (
      <span className="mono" style={{ padding: '0.35rem 0.65rem', borderRadius: 'var(--radius-full)', background: 'var(--color-danger-bg)', color: 'var(--color-danger)', fontSize: 'var(--text-xs)', fontWeight: 700 }}>
        failed
      </span>
    )
  }

  const tone = badgeTone[review?.recommendation] || { label: review?.recommendation || 'quiet', bg: 'var(--color-paper-3)', fg: 'var(--color-ink-3)', Icon: MessageSquare }
  return (
    <span className="mono" style={{ display: 'inline-flex', alignItems: 'center', gap: 'var(--space-2xs)', padding: '0.35rem 0.65rem', borderRadius: 'var(--radius-full)', background: tone.bg, color: tone.fg, fontSize: 'var(--text-xs)', fontWeight: 700 }}>
      <tone.Icon className="w-3 h-3" />
      {tone.label}
    </span>
  )
}

function Metric({ label, value, helper, icon: Icon, tone = 'var(--color-accent)' }) {
  return (
    <div className="panel-soft reveal" style={{ padding: 'var(--space-md)', minHeight: 130 }}>
      <div className="flex items-start justify-between gap-md">
        <p className="mono" style={{ color: 'var(--color-ink-4)', fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>{label}</p>
        <Icon className="w-4 h-4" style={{ color: tone }} />
      </div>
      <p className="mono" style={{ marginTop: 'var(--space-lg)', color: 'var(--color-ink)', fontSize: 'var(--text-3xl)', fontWeight: 700, letterSpacing: '-0.06em', lineHeight: 1 }}>
        {value}
      </p>
      <p style={{ marginTop: 'var(--space-xs)', color: 'var(--color-ink-3)', fontSize: 'var(--text-sm)' }}>{helper}</p>
    </div>
  )
}

function SeverityOrbit({ high, medium, low }) {
  const total = Math.max(high + medium + low, 1)
  const segments = [
    { label: 'HIGH', value: high, color: 'var(--color-danger)' },
    { label: 'MED', value: medium, color: 'var(--color-warning)' },
    { label: 'LOW', value: low, color: 'var(--color-info)' },
  ]

  return (
    <div className="panel panel-live reveal" style={{ padding: 'var(--space-lg)', display: 'grid', gap: 'var(--space-lg)' }}>
      <div>
        <p className="kicker">risk organism</p>
        <h2 style={{ color: 'var(--color-ink)', fontSize: 'var(--text-xl)', fontWeight: 800, letterSpacing: '-0.04em', marginTop: 'var(--space-xs)' }}>
          Finding metabolism
        </h2>
      </div>

      <div style={{ display: 'grid', placeItems: 'center', minHeight: 210 }}>
        <div className="living-orb" style={{ width: 176, height: 176 }} aria-label={`${total} findings`}>
          <div style={{ textAlign: 'center' }}>
            <p className="mono" style={{ color: 'var(--color-ink)', fontSize: 'var(--text-3xl)', fontWeight: 800, lineHeight: 1 }}>{high + medium + low}</p>
            <p className="mono" style={{ color: 'var(--color-ink-3)', fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>findings</p>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gap: 'var(--space-sm)' }}>
        {segments.map((s) => (
          <div key={s.label}>
            <div className="flex items-center justify-between">
              <span className="mono" style={{ color: 'var(--color-ink-3)', fontSize: 'var(--text-xs)' }}>{s.label}</span>
              <span className="mono" style={{ color: s.color, fontSize: 'var(--text-xs)', fontWeight: 700 }}>{s.value}</span>
            </div>
            <div style={{ height: 7, marginTop: 'var(--space-2xs)', borderRadius: 'var(--radius-full)', background: 'var(--color-paper-3)', overflow: 'hidden' }}>
              <div style={{ width: `${Math.max((s.value / total) * 100, s.value ? 8 : 0)}%`, height: '100%', borderRadius: 'var(--radius-full)', background: s.color, transition: `width var(--dur-long) var(--ease-out)` }} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function PollConstellation({ states = [] }) {
  return (
    <div className="panel reveal" style={{ padding: 'var(--space-lg)' }}>
      <div className="flex items-center justify-between gap-md">
        <div>
          <p className="kicker">polling field</p>
          <h2 style={{ color: 'var(--color-ink)', fontSize: 'var(--text-xl)', fontWeight: 800, letterSpacing: '-0.04em', marginTop: 'var(--space-xs)' }}>
            Repository orbit
          </h2>
        </div>
        <Radar className="w-5 h-5" style={{ color: 'var(--color-accent)' }} />
      </div>

      <div style={{ display: 'grid', gap: 'var(--space-sm)', marginTop: 'var(--space-lg)' }}>
        {states.length === 0 ? (
          <p style={{ color: 'var(--color-ink-3)', fontSize: 'var(--text-sm)' }}>No poll states yet.</p>
        ) : states.map((ps) => (
          <div key={ps.repo} className="panel-soft" style={{ padding: 'var(--space-sm)' }}>
            <div className="flex items-center justify-between gap-sm">
              <div className="flex items-center gap-xs">
                <span className="signal-dot" aria-hidden="true" />
                <span className="mono" style={{ color: 'var(--color-ink)', fontWeight: 700 }}>{ps.repo}</span>
              </div>
              <span className="mono" style={{ color: 'var(--color-ink-4)', fontSize: 'var(--text-xs)' }}>
                {ps.last_poll_at ? new Date(ps.last_poll_at).toLocaleString('th-TH') : 'never'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ReviewStream({ reviews }) {
  if (!reviews.length) {
    return (
      <div className="panel reveal" style={{ padding: 'var(--space-2xl)', textAlign: 'center' }}>
        <FileSearch className="w-8 h-8 mx-auto" style={{ color: 'var(--color-ink-4)' }} />
        <p style={{ marginTop: 'var(--space-md)', color: 'var(--color-ink)', fontWeight: 700 }}>No review signals yet</p>
        <p style={{ marginTop: 'var(--space-2xs)', color: 'var(--color-ink-3)' }}>Submit a PR URL or wait for the next poll.</p>
      </div>
    )
  }

  return (
    <div className="panel reveal" style={{ overflow: 'hidden' }}>
      <div style={{ padding: 'var(--space-lg)', borderBottom: '1px solid var(--color-rule)' }}>
        <p className="kicker">recent signals</p>
      </div>
      <div>
        {reviews.map((rv) => (
          <Link
            key={rv.id}
            to={`/prs/${rv.pr_id}`}
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 1fr) auto',
              gap: 'var(--space-md)',
              alignItems: 'center',
              padding: 'var(--space-md) var(--space-lg)',
              borderBottom: '1px solid var(--color-rule)',
              color: 'inherit',
              textDecoration: 'none',
              transition: `background var(--dur-short) var(--ease-out)`,
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'var(--color-paper-3)'}
            onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
          >
            <div className="min-w-0">
              <div className="flex items-center gap-xs flex-wrap">
                <SignalBadge review={rv} />
                <span className="mono" style={{ color: 'var(--color-ink-4)', fontSize: 'var(--text-xs)' }}>{rv.pr_repo}</span>
              </div>
              <p style={{ marginTop: 'var(--space-xs)', color: 'var(--color-ink)', fontWeight: 700, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {rv.pr_title || `PR #${rv.pr_id}`}
              </p>
              <p style={{ color: 'var(--color-ink-3)', fontSize: 'var(--text-sm)', marginTop: 'var(--space-2xs)' }}>
                {rv.pr_author || 'Unknown author'} · {rv.status === 'running' ? 'review in progress' : `${rv.duration_seconds ?? 0}s`}
              </p>
            </div>
            <div className="flex items-center gap-xs">
              {rv.high_count > 0 && <span className="mono" style={{ color: 'var(--color-danger)', background: 'var(--color-danger-bg)', padding: '0.25rem 0.45rem', borderRadius: 'var(--radius-sm)', fontSize: 'var(--text-xs)', fontWeight: 700 }}>{rv.high_count}H</span>}
              {rv.medium_count > 0 && <span className="mono" style={{ color: 'var(--color-warning)', background: 'var(--color-warning-bg)', padding: '0.25rem 0.45rem', borderRadius: 'var(--radius-sm)', fontSize: 'var(--text-xs)', fontWeight: 700 }}>{rv.medium_count}M</span>}
              <ArrowUpRight className="w-4 h-4" style={{ color: 'var(--color-ink-4)' }} />
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

function Dashboard() {
  const [stats, setStats] = useState(null)
  const [recentReviews, setRecentReviews] = useState([])
  const [prUrl, setPrUrl] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitResult, setSubmitResult] = useState(null)

  const refreshDashboard = () => {
    fetch('/api/stats').then(r => r.json()).then(setStats)
    fetch('/api/reviews?limit=8').then(r => r.json()).then(d => setRecentReviews(d.reviews || []))
  }

  useEffect(() => {
    refreshDashboard()
  }, [])

  useEffect(() => {
    if (!recentReviews.some(rv => rv.status === 'running')) return
    const timer = setInterval(refreshDashboard, 3000)
    return () => clearInterval(timer)
  }, [recentReviews])

  const handleSubmitUrl = async () => {
    if (!prUrl.trim()) return
    setSubmitting(true)
    setSubmitResult(null)
    try {
      const resp = await fetch('/api/prs/submit-url', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: prUrl.trim() }),
      })
      const data = await resp.json()
      if (!resp.ok) setSubmitResult({ error: data.detail || 'Failed to submit PR' })
      else {
        setSubmitResult(data)
        setPrUrl('')
        refreshDashboard()
        setTimeout(refreshDashboard, 1500)
      }
    } catch (e) {
      setSubmitResult({ error: e.message })
    } finally {
      setSubmitting(false)
    }
  }

  const systemMood = useMemo(() => {
    const running = recentReviews.filter(rv => rv.status === 'running').length
    const high = stats?.findings_by_severity?.HIGH || 0
    if (running) return { label: `${running} scan${running > 1 ? 's' : ''} breathing`, tone: 'var(--color-accent)' }
    if (high) return { label: `${high} high-risk anomaly`, tone: 'var(--color-danger)' }
    return { label: 'habitat stable', tone: 'var(--color-success)' }
  }, [recentReviews, stats])

  if (!stats) return <LoadingSkeleton />

  const high = stats.findings_by_severity?.HIGH || 0
  const medium = stats.findings_by_severity?.MEDIUM || 0
  const low = stats.findings_by_severity?.LOW || 0

  return (
    <div className="page-frame" style={{ display: 'grid', gap: 'var(--space-lg)' }}>
      <section className="panel panel-live reveal" style={{ '--i': 0, padding: 'var(--space-xl)', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 22rem), 1fr))', gap: 'var(--space-xl)', alignItems: 'center' }}>
        <div className="min-w-0">
          <p className="kicker">living orbit</p>
          <h1 className="display-title hero-title" style={{ marginTop: 'var(--space-sm)' }}>
            Review system, awake and breathing.
          </h1>
          <p style={{ maxWidth: '62ch', marginTop: 'var(--space-md)', color: 'var(--color-ink-2)', fontSize: 'var(--text-md)', lineHeight: 1.75 }}>
            Your private mission control for PR polling, changed-line review, scanner signals, LLM judgment, and Azure DevOps comments.
          </p>

          <div style={{ marginTop: 'var(--space-xl)', display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 'var(--space-xs)' }}>
            <input
              type="url"
              value={prUrl}
              onChange={e => setPrUrl(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmitUrl()}
              placeholder="Paste Azure DevOps PR URL"
              style={{
                minHeight: 48,
                minWidth: 0,
                border: '1px solid var(--color-rule)',
                borderRadius: 'var(--radius-input)',
                background: 'var(--color-paper)',
                color: 'var(--color-ink)',
                padding: '0 var(--space-md)',
                fontFamily: 'var(--font-mono)',
                fontSize: 'var(--text-sm)',
              }}
            />
            <button
              onClick={handleSubmitUrl}
              disabled={submitting || !prUrl.trim()}
              style={{
                minHeight: 48,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 'var(--space-xs)',
                padding: '0 var(--space-lg)',
                border: 0,
                borderRadius: 'var(--radius-input)',
                background: 'var(--color-accent)',
                color: 'var(--color-accent-ink)',
                fontWeight: 800,
                whiteSpace: 'nowrap',
              }}
            >
              {submitting ? <Loader2 className="w-4 h-4" style={{ animation: 'orbit-turn 1.2s linear infinite' }} /> : <Search className="w-4 h-4" />}
              Review
            </button>
          </div>

          {submitResult && (
            <div className="panel-soft" style={{ marginTop: 'var(--space-sm)', padding: 'var(--space-sm)', borderColor: submitResult.error ? 'var(--color-danger)' : 'var(--color-rule-living)' }}>
              <p style={{ color: submitResult.error ? 'var(--color-danger)' : 'var(--color-accent)', fontSize: 'var(--text-sm)' }}>
                {submitResult.error ? submitResult.error : `${submitResult.message} · ${submitResult.repo || 'repo'} #${submitResult.azure_pr_id || submitResult.pr_id}`}
              </p>
            </div>
          )}
        </div>

        <div style={{ display: 'grid', placeItems: 'center' }}>
          <div className="living-orb" style={{ width: 260, height: 260 }}>
            <div style={{ textAlign: 'center' }}>
              <Sparkles className="w-7 h-7 mx-auto" style={{ color: systemMood.tone }} />
              <p className="mono" style={{ marginTop: 'var(--space-md)', color: systemMood.tone, fontSize: 'var(--text-xs)', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '0.12em' }}>
                {systemMood.label}
              </p>
              <p className="mono" style={{ marginTop: 'var(--space-xs)', color: 'var(--color-ink)', fontSize: 'var(--text-3xl)', fontWeight: 800 }}>{stats.total_reviews || 0}</p>
              <p className="mono" style={{ color: 'var(--color-ink-4)', fontSize: 'var(--text-xs)' }}>reviews logged</p>
            </div>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-md">
        <Metric label="pull requests" value={stats.total_prs || 0} helper="known in local habitat" icon={GitPullRequest} tone="var(--color-info)" />
        <Metric label="reviews" value={stats.total_reviews || 0} helper="completed or running" icon={FileSearch} tone="var(--color-accent)" />
        <Metric label="findings" value={stats.total_findings || 0} helper="changed-line signals" icon={AlertTriangle} tone="var(--color-warning)" />
        <Metric label="critical" value={high} helper="needs first attention" icon={Flame} tone="var(--color-danger)" />
      </section>

      <section className="grid grid-cols-1 xl:grid-cols-[0.82fr_1.18fr] gap-md">
        <SeverityOrbit high={high} medium={medium} low={low} />
        <ReviewStream reviews={recentReviews} />
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-[1fr_1.2fr] gap-md">
        <PollConstellation states={stats.poll_states || []} />
        <div className="panel reveal" style={{ padding: 'var(--space-lg)' }}>
          <p className="kicker">recommendation ecology</p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-sm" style={{ marginTop: 'var(--space-lg)' }}>
            {[
              { label: 'clear', value: stats.recommendations?.approve || 0, Icon: ShieldCheck, color: 'var(--color-success)' },
              { label: 'mutate', value: stats.recommendations?.request_changes || 0, Icon: XCircle, color: 'var(--color-danger)' },
              { label: 'observe', value: stats.recommendations?.comment || 0, Icon: MessageSquare, color: 'var(--color-warning)' },
            ].map(({ label, value, Icon, color }) => (
              <div key={label} className="panel-soft" style={{ padding: 'var(--space-md)' }}>
                <Icon className="w-5 h-5" style={{ color }} />
                <p className="mono" style={{ color: 'var(--color-ink)', fontSize: 'var(--text-2xl)', fontWeight: 800, marginTop: 'var(--space-md)', lineHeight: 1 }}>{value}</p>
                <p className="mono" style={{ color: 'var(--color-ink-3)', fontSize: 'var(--text-xs)', textTransform: 'uppercase', letterSpacing: '0.12em', marginTop: 'var(--space-xs)' }}>{label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  )
}

export default Dashboard
